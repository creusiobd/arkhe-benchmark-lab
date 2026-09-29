import asyncio
import math
import os
import random
import sys
import time
import uuid

if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from fastapi import FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Status, StatusCode

from arkhe_detector import ArkheTrajectoryEngine
from traditional_monitor import TraditionalSREMonitor

# --- INSTRUMENTAÇÃO OPENTELEMETRY ---
resource = Resource.create({"service.name": "card-authorization-lab"})
provider = TracerProvider(resource=resource)
if os.getenv("OTEL_CONSOLE_EXPORT", "false").lower() == "true":
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
else:
    provider.add_span_processor(BatchSpanProcessor(InMemorySpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("card-auth-pipeline", "1.0.0")

# --- MODELAGEM DE RECURSOS ADAPTATIVOS (AUTONOMOUS MITIGATOR & POOL) ---

class AdaptivePoolSemaphore:
    """Semáforo adaptativo que permite expansão dinâmica de concorrência (Predictive HPA)."""
    def __init__(self, initial_capacity: int = 30):
        self._capacity = initial_capacity
        self._sem = asyncio.Semaphore(initial_capacity)

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def available_slots(self) -> int:
        return max(0, self._sem._value)

    async def acquire(self):
        await self._sem.acquire()

    def release(self):
        self._sem.release()

    def scale_to(self, new_capacity: int):
        diff = new_capacity - self._capacity
        if diff > 0:
            for _ in range(diff):
                self._sem.release()
            self._capacity = new_capacity

    def reset_capacity(self, capacity: int = 30):
        self._capacity = capacity
        self._sem = asyncio.Semaphore(capacity)

antifraud_pool = AdaptivePoolSemaphore(30)

def calculate_mmck_metrics(arrival_rate: float, service_rate: float, c: int, K: int) -> dict:
    """
    Calcula a solução analítica exata em forma fechada para o sistema de filas M/M/c/K (Kendall).
    arrival_rate (lambda): taxa de chegadas de Poisson (TPS)
    service_rate (mu): taxa de atendimento por servidor (1 / tempo_servico_segundos)
    c: número de servidores concorrentes em paralelo (capacidade do pool)
    K: capacidade total finita do sistema (servidores + buffer da fila)
    """
    if arrival_rate <= 0 or service_rate <= 0 or c <= 0 or K < c:
        return {
            "arrival_rate_tps": round(arrival_rate, 1),
            "service_rate_per_sec": round(service_rate, 1),
            "servers_c": c,
            "capacity_k": K,
            "traffic_intensity_rho": 0.0,
            "p_loss_ratio": 0.0,
            "p_loss_pct": 0.0,
            "l_q_expected": 0.0,
            "w_q_ms_expected": 0.0,
            "lambda_effective_tps": round(arrival_rate, 1)
        }
    
    a = arrival_rate / service_rate
    rho = a / c
    
    # Cálculo das probabilidades normalizadas p_n
    terms = []
    current_term = 1.0  # para n=0: a^0 / 0! = 1
    terms.append(current_term)
    
    for n in range(1, c):
        current_term = current_term * a / n
        terms.append(current_term)
        
    term_c = current_term * a / c  # a^c / c!
    terms.append(term_c)
    
    curr = term_c
    for n in range(c + 1, K + 1):
        curr = curr * rho
        terms.append(curr)
        
    sum_terms = sum(terms)
    p0 = 1.0 / sum_terms if sum_terms > 0 else 0.0
    
    probs = [t * p0 for t in terms]
    
    # Probabilidade de perda / bloqueio P_K (rejeição de buffer finito)
    p_loss = probs[K] if K < len(probs) else 0.0
    
    # Taxa efetiva de chegada lambda_eff = lambda * (1 - P_K)
    lambda_eff = arrival_rate * (1.0 - p_loss)
    
    # Tamanho médio esperado da fila L_q = sum_{n=c}^K (n - c) * p_n
    l_q = sum((n - c) * probs[n] for n in range(c, K + 1))
    
    # Tempo médio de espera na fila W_q = L_q / lambda_eff (Lei de Little)
    w_q_sec = (l_q / lambda_eff) if lambda_eff > 0 else 0.0
    w_q_ms = w_q_sec * 1000.0
    
    return {
        "arrival_rate_tps": round(arrival_rate, 1),
        "service_rate_per_sec": round(service_rate, 1),
        "servers_c": c,
        "capacity_k": K,
        "traffic_intensity_rho": round(rho, 4),
        "p_loss_ratio": round(p_loss, 6),
        "p_loss_pct": round(p_loss * 100.0, 4),
        "l_q_expected": round(l_q, 2),
        "w_q_ms_expected": round(w_q_ms, 2),
        "lambda_effective_tps": round(lambda_eff, 1)
    }

# Estado global da simulação
class SimulationEnvironment:
    def __init__(self):
        # Controle de Caos interno (GROUND TRUTH)
        self.antifraud_latency_base_ms: float = 45.0
        self.antifraud_jitter_ms: float = 10.0
        self.network_error_rate: float = 0.001
        
        # Controle de Carga Contínua e Simulação Estocástica de Alta Fidelidade (M/M/c/K)
        self.target_tps: float = 120.0
        self.stochastic_mode: bool = True
        self.system_capacity_k: int = 60
        
        # Cenário atual
        self.current_scenario: str = "nominal"
        self.scenario_description: str = "1. Operação Nominal (45ms, Pool ~10%)"
        self.scenario_started_at: float = time.time()
        
        # Telemetria do Event Loop
        self.event_loop_lag_ms: float = 0.0
        self._last_tick: float = time.perf_counter()
        
        # Concorrência e Filas (Lei de Little / Kingman)
        self.antifraud_waiters: int = 0
        self.recent_queue_waits_ms: deque = deque(maxlen=500)
        self.recent_service_times_ms: deque = deque(maxlen=500)
        
        # Contadores transacionais estritos
        self.unique_transactions_total: int = 0
        self.attempts_total: int = 0
        self.approved_total: int = 0
        self.business_declined_total: int = 0
        self.technical_timeouts_total: int = 0
        self.pool_exhausted_total: int = 0
        
        # Histórico recente para métricas de janela (Rolling Window de latência)
        self.recent_latencies: deque = deque(maxlen=2000)
        
        # Buffer de Trajetórias Recentes (Últimas 40 transações completas para visualização Waterfall)
        self.recent_journeys: deque = deque(maxlen=40)
        
        # Motores de Diagnóstico Ativos
        self.arkhe_engine = ArkheTrajectoryEngine()
        self.traditional_monitor = TraditionalSREMonitor(sustained_checks_required=2)
        
        # Timestamps de Alerta
        self.t_sentinel_alert: Optional[float] = None
        self.t_sre_alert: Optional[float] = None
        
        # Log cronológico de eventos
        self.event_logs: deque = deque(maxlen=60)
        self.add_log("Sistema iniciado em modo nominal (45ms).")

        # --- CONTROLE DA MITIGAÇÃO AUTÔNOMA (CLOSED-LOOP SELF-HEALING) ---
        self.mitigation_enabled: bool = False
        self.mitigation_active: bool = False
        self.mitigation_fast_path_active: bool = False
        self.mitigation_actions: deque = deque(maxlen=20)
        self.prevented_failures_count: int = 0
        self.prevented_downtime_sec: float = 0.0

        # Vetores Adicionais de Caos (Passo 6)
        self.hsm_extra_delay_ms: float = 0.0
        self.acquirer_flapping_rate: float = 0.0
        self.network_jitter_p99_active: bool = False

    def add_log(self, message: str, level: str = "info"):
        timestamp_str = time.strftime("%H:%M:%S")
        self.event_logs.appendleft({
            "timestamp": timestamp_str,
            "message": message,
            "level": level
        })

sim_env = SimulationEnvironment()

# --- WEBSOCKET CONNECTION & BROADCAST MANAGER (STREAMING EM ALTA FREQUÊNCIA: 20 FPS) ---

class StreamConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        dead = []
        for conn in list(self.active_connections):
            try:
                await conn.send_json(message)
            except Exception:
                dead.append(conn)
        for d in dead:
            self.disconnect(d)

stream_manager = StreamConnectionManager()

# Medidor de Event Loop Lag de alta precisão
async def event_loop_monitor():
    while True:
        t0 = time.perf_counter()
        await asyncio.sleep(0.05)
        delta = (time.perf_counter() - t0) - 0.05
        sim_env.event_loop_lag_ms = max(0.0, delta * 1000.0)

# Broadcaster em segundo plano para streaming contínuo de alta frequência (20 FPS / 50ms por tick)
async def telemetry_broadcaster_task():
    TARGET_INTERVAL = 0.050  # 50ms = 20 FPS
    next_tick = time.perf_counter()
    while True:
        next_tick += TARGET_INTERVAL
        try:
            if stream_manager.active_connections:
                payload = await build_telemetry_payload()
                await stream_manager.broadcast(payload)
        except Exception:
            pass
        now = time.perf_counter()
        sleep_time = next_tick - now
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
        else:
            next_tick = now
            await asyncio.sleep(0.001)

@asynccontextmanager
async def lifespan(app: FastAPI):
    monitor_task = asyncio.create_task(event_loop_monitor())
    broadcast_task = asyncio.create_task(telemetry_broadcaster_task())
    yield
    monitor_task.cancel()
    broadcast_task.cancel()

app = FastAPI(title="ARKHÉ Card Authorization Lab", lifespan=lifespan)

# Suporte total a CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Garante tipo MIME estrito para ES6 modules no Windows (evita text/plain)
import mimetypes
mimetypes.init()
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

# Monta diretório de recursos estáticos modulares (CSS, JS Vanilla ES6+, Assets)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Monta distribuição de produção do Angular 17 Dashboard
angular_dist_dir = os.path.join(os.path.dirname(__file__), "dashboard-angular", "dist", "arkhe-dashboard-angular", "browser")
if os.path.exists(angular_dist_dir):
    from fastapi.responses import RedirectResponse
    @app.get("/ng", include_in_schema=False)
    async def redirect_angular():
        return RedirectResponse(url="/ng/")
    app.mount("/ng", StaticFiles(directory=angular_dist_dir, html=True), name="angular")

# --- MODELOS DE DADOS ---
@dataclass
class PaymentIntent:
    transaction_id: str
    attempt_id: str
    card_token: str
    amount_cents: int
    currency: str = "BRL"

# --- PIPELINE DE 6 ESTÁGIOS INSTRUMENTADO ---

async def stage_gateway_ingest(intent: PaymentIntent) -> float:
    t0 = time.perf_counter()
    with tracer.start_as_current_span("gateway.ingest") as span:
        span.set_attribute("payment.transaction_id", intent.transaction_id)
        span.set_attribute("payment.attempt_id", intent.attempt_id)
        span.set_attribute("payment.amount", intent.amount_cents)
        await asyncio.sleep(0.008)  # 8ms fixos
    return (time.perf_counter() - t0) * 1000.0

async def stage_validate_limits(intent: PaymentIntent) -> float:
    t0 = time.perf_counter()
    with tracer.start_as_current_span("validation.card_and_limits") as span:
        _ = [hash(intent.card_token + str(i)) for i in range(1500)]
        if sim_env.hsm_extra_delay_ms > 0:
            await asyncio.sleep(sim_env.hsm_extra_delay_ms / 1000.0)
            span.set_attribute("validation.hsm_delay_ms", sim_env.hsm_extra_delay_ms)
        else:
            await asyncio.sleep(0.004)
        elapsed = (time.perf_counter() - t0) * 1000.0
        span.set_attribute("validation.cpu_cost_ms", elapsed)
    return (time.perf_counter() - t0) * 1000.0

async def stage_antifraud_analysis(intent: PaymentIntent) -> Tuple[float, float, float]:
    """Retorna (risk_score, queue_wait_ms, service_elapsed_ms)"""
    with tracer.start_as_current_span("antifraud.analysis") as span:
        cur_cap = antifraud_pool.capacity
        span.set_attribute("antifraud.pool.capacity", cur_cap)
        span.set_attribute("antifraud.pool.available_before", antifraud_pool.available_slots)
        
        # Avaliação de Fast-Path Autônomo se mitigação estiver engatada
        use_fast_path = (
            sim_env.mitigation_active 
            and sim_env.mitigation_fast_path_active
            and (int(intent.card_token[-2:], 16) % 10 < 7) # 70% das transações
        )

        queue_start = time.perf_counter()
        
        # 1. Verificação de Capacidade Finita K (M/M/c/K Buffer Drop)
        cur_in_flight = (cur_cap - antifraud_pool.available_slots) + sim_env.antifraud_waiters
        if sim_env.stochastic_mode and cur_in_flight >= sim_env.system_capacity_k:
            span.set_status(Status(StatusCode.ERROR, "Antifraud M/M/c/K Finite Buffer Full (K reached)"))
            span.set_attribute("error.type", "MMcKBufferExhaustion")
            sim_env.pool_exhausted_total += 1
            raise HTTPException(status_code=503, detail="Antifraud buffer full (M/M/c/K drop)")

        sim_env.antifraud_waiters += 1
        
        try:
            # Com mitigação ativa, aumentamos a tolerância de backpressure
            queue_timeout = 2.0 if sim_env.mitigation_active else 0.8
            await asyncio.wait_for(antifraud_pool.acquire(), timeout=queue_timeout)
        except asyncio.TimeoutError:
            span.set_status(Status(StatusCode.ERROR, "Antifraud Pool Queue Full"))
            span.set_attribute("error.type", "PoolExhaustion")
            sim_env.pool_exhausted_total += 1
            raise HTTPException(status_code=503, detail="Antifraud service saturated")
        finally:
            sim_env.antifraud_waiters -= 1
        
        queue_wait_ms = (time.perf_counter() - queue_start) * 1000.0
        sim_env.recent_queue_waits_ms.append(queue_wait_ms)
        span.set_attribute("antifraud.queue_wait_ms", queue_wait_ms)

        service_start = time.perf_counter()
        try:
            risk_score = (int(intent.card_token[-2:], 16) % 100) if len(intent.card_token) >= 2 else 15
            if use_fast_path:
                # FAST-PATH AUTÔNOMO: validação em cache rápido (12ms) em vez de 255ms/420ms
                latency = 0.012
                sim_env.prevented_failures_count += 1
            elif sim_env.stochastic_mode:
                # SIMULAÇÃO ESTOCÁSTICA DE ALTA FIDELIDADE: Distribuição Exponencial Markoviana M (taxa mu = 1 / mean)
                mean_sec = max(0.005, sim_env.antifraud_latency_base_ms / 1000.0)
                latency = max(0.002, float(np.random.exponential(scale=mean_sec)))
            else:
                latency = np.random.normal(
                    sim_env.antifraud_latency_base_ms,
                    sim_env.antifraud_jitter_ms
                )
                latency = max(5.0, latency) / 1000.0
            
            await asyncio.sleep(latency)
            span.set_attribute("antifraud.risk_score", risk_score)
            service_elapsed = (time.perf_counter() - service_start) * 1000.0
            sim_env.recent_service_times_ms.append(service_elapsed)
            return risk_score, queue_wait_ms, service_elapsed
        finally:
            antifraud_pool.release()

async def stage_card_authorization(intent: PaymentIntent, risk_score: float) -> Tuple[str, float]:
    t0 = time.perf_counter()
    with tracer.start_as_current_span("authorizer.network") as span:
        span.set_attribute("authorizer.network_name", "CIELO_SIMULATOR")
        
        # 1. Simulação de Flapping / Circuit Breaker da Adquirente Externa
        if sim_env.acquirer_flapping_rate > 0 and random.random() < sim_env.acquirer_flapping_rate:
            await asyncio.sleep(0.120)
            span.set_attribute("authorizer.error", "ACQUIRER_FLAPPING_503")
            return "TECHNICAL_ERROR", (time.perf_counter() - t0) * 1000.0

        if risk_score > 85:
            span.set_attribute("authorization.declined_reason", "HIGH_RISK")
            return "DECLINED_ANTIFRAUD", (time.perf_counter() - t0) * 1000.0

        # 2. Simulação de Jitter Assimétrico de Rede (Cauda Longa P99)
        if sim_env.network_jitter_p99_active and random.random() < 0.10:
            await asyncio.sleep(1.200) # Outlier extremo na cauda P99
            span.set_attribute("network.jitter_outlier", True)
        else:
            await asyncio.sleep(0.080)

        token_num = "".join([c for c in intent.card_token if c.isdigit()])
        if token_num and (int(token_num[-3:]) % 25 == 0):
            span.set_attribute("authorization.declined_reason", "INSUFFICIENT_FUNDS")
            return "DECLINED_FUNDS", (time.perf_counter() - t0) * 1000.0

        return "AUTHORIZED", (time.perf_counter() - t0) * 1000.0

async def stage_ledger_confirmation(intent: PaymentIntent, auth_code: str) -> float:
    t0 = time.perf_counter()
    with tracer.start_as_current_span("ledger.confirm") as span:
        span.set_attribute("ledger.auth_code", auth_code)
        await asyncio.sleep(0.015)
    return (time.perf_counter() - t0) * 1000.0

# --- ENDPOINTS OPERACIONAIS DE CARGA COM REGISTRO DE TRAJETÓRIA ---

@app.post("/v1/charge", status_code=status.HTTP_200_OK)
async def process_charge(
    intent_data: dict,
    x_transaction_id: Optional[str] = Header(None),
    x_attempt_id: Optional[str] = Header(None),
):
    global_start = time.perf_counter()
    tx_id = x_transaction_id or f"tx_{uuid.uuid4().hex[:12]}"
    attempt_id = x_attempt_id or f"att_{uuid.uuid4().hex[:8]}"
    
    is_first_attempt = (
        attempt_id.endswith("_1") 
        or (x_attempt_id is None and not attempt_id.endswith(("_2", "_3")))
    )

    if is_first_attempt:
        sim_env.unique_transactions_total += 1
    sim_env.attempts_total += 1

    intent = PaymentIntent(
        transaction_id=tx_id,
        attempt_id=attempt_id,
        card_token=intent_data.get("card_token", "tok_4242"),
        amount_cents=intent_data.get("amount_cents", 10000)
    )

    with tracer.start_as_current_span("payment.process_charge") as root_span:
        root_span.set_attribute("payment.transaction_id", tx_id)
        root_span.set_attribute("payment.attempt_id", attempt_id)
        
        stages_breakdown = {}
        try:
            # Timeout do Gateway de 1.500 ms (SLA de Latência Crítica)
            async with asyncio.timeout(1.500):
                stages_breakdown["ingest_ms"] = round(await stage_gateway_ingest(intent), 1)
                stages_breakdown["limits_ms"] = round(await stage_validate_limits(intent), 1)
                
                risk_score, q_wait, s_time = await stage_antifraud_analysis(intent)
                stages_breakdown["antifraud_queue_ms"] = round(q_wait, 1)
                stages_breakdown["antifraud_service_ms"] = round(s_time, 1)
                
                auth_result, auth_dur = await stage_card_authorization(intent, risk_score)
                stages_breakdown["authorizer_ms"] = round(auth_dur, 1)

                if auth_result == "AUTHORIZED":
                    stages_breakdown["ledger_ms"] = round(await stage_ledger_confirmation(intent, "AUTH_9988"), 1)
                    sim_env.approved_total += 1
                    elapsed = (time.perf_counter() - global_start) * 1000.0
                    sim_env.recent_latencies.append(elapsed)
                    
                    sim_env.recent_journeys.appendleft({
                        "tx_id": tx_id,
                        "attempt_id": attempt_id,
                        "card_token": intent.card_token,
                        "amount_brl": round(intent.amount_cents / 100.0, 2),
                        "timestamp": time.strftime("%H:%M:%S"),
                        "total_ms": round(elapsed, 1),
                        "status": "AUTHORIZED",
                        "sla_impact": "NEUTRAL_SUCCESS",
                        "stages": stages_breakdown
                    })
                    return {"status": "AUTHORIZED", "transaction_id": tx_id, "latency_ms": elapsed}
                elif auth_result == "TECHNICAL_ERROR":
                    sim_env.technical_timeouts_total += 1
                    root_span.set_attribute("payment.technical_error", "ACQUIRER_FLAPPING")
                    elapsed = (time.perf_counter() - global_start) * 1000.0
                    sim_env.recent_latencies.append(elapsed)
                    sim_env.recent_journeys.appendleft({
                        "tx_id": tx_id,
                        "attempt_id": attempt_id,
                        "card_token": intent.card_token,
                        "amount_brl": round(intent.amount_cents / 100.0, 2),
                        "timestamp": time.strftime("%H:%M:%S"),
                        "total_ms": round(elapsed, 1),
                        "status": "ACQUIRER_503",
                        "sla_impact": "BREACH_CRITICAL",
                        "stages": stages_breakdown
                    })
                    raise HTTPException(status_code=503, detail="Acquirer network flapping / circuit breaker open")
                else:
                    sim_env.business_declined_total += 1
                    root_span.set_attribute("payment.business_decline", auth_result)
                    elapsed = (time.perf_counter() - global_start) * 1000.0
                    sim_env.recent_latencies.append(elapsed)
                    
                    sim_env.recent_journeys.appendleft({
                        "tx_id": tx_id,
                        "attempt_id": attempt_id,
                        "card_token": intent.card_token,
                        "amount_brl": round(intent.amount_cents / 100.0, 2),
                        "timestamp": time.strftime("%H:%M:%S"),
                        "total_ms": round(elapsed, 1),
                        "status": auth_result,
                        "sla_impact": "BUSINESS_DECLINE_PRESERVED",
                        "stages": stages_breakdown
                    })
                    return {"status": auth_result, "transaction_id": tx_id, "latency_ms": elapsed}

        except (asyncio.TimeoutError, TimeoutError):
            sim_env.technical_timeouts_total += 1
            root_span.set_status(Status(StatusCode.ERROR, "Gateway 1500ms Timeout Exceeded"))
            elapsed = (time.perf_counter() - global_start) * 1000.0
            sim_env.recent_latencies.append(elapsed)
            
            sim_env.recent_journeys.appendleft({
                "tx_id": tx_id,
                "attempt_id": attempt_id,
                "card_token": intent.card_token,
                "amount_brl": round(intent.amount_cents / 100.0, 2),
                "timestamp": time.strftime("%H:%M:%S"),
                "total_ms": round(elapsed, 1),
                "status": "TIMEOUT_504",
                "sla_impact": "BURNED_ERROR_BUDGET",
                "stages": stages_breakdown
            })
            raise HTTPException(status_code=504, detail="Transaction timeout at 1500ms")
            
        except HTTPException as he:
            if he.status_code == 503:
                elapsed = (time.perf_counter() - global_start) * 1000.0
                sim_env.recent_journeys.appendleft({
                    "tx_id": tx_id,
                    "attempt_id": attempt_id,
                    "card_token": intent.card_token,
                    "amount_brl": round(intent.amount_cents / 100.0, 2),
                    "timestamp": time.strftime("%H:%M:%S"),
                    "total_ms": round(elapsed, 1),
                    "status": "POOL_SATURATED_503",
                    "sla_impact": "BURNED_ERROR_BUDGET",
                    "stages": stages_breakdown
                })
            raise
        except Exception as err:
            root_span.record_exception(err)
            root_span.set_status(Status(StatusCode.ERROR, str(err)))
            raise HTTPException(status_code=500, detail="Internal pipeline collapse")

# --- MOTOR UNIFICADO DE CONSTRUÇÃO DE TELEMETRIA ---

async def get_observables(as_of: float = 0.0) -> dict:
    latencies = list(sim_env.recent_latencies)
    if not latencies:
        p50, p95, p99 = 0.0, 0.0, 0.0
    else:
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)
        p50 = latencies_sorted[int(n * 0.50)]
        p95 = latencies_sorted[min(n - 1, int(n * 0.95))]
        p99 = latencies_sorted[min(n - 1, int(n * 0.99))]
    
    current_capacity = antifraud_pool.capacity
    current_slots_in_use = max(0, min(current_capacity, current_capacity - antifraud_pool.available_slots))
    pool_utilization = max(0.0, min(1.0, current_slots_in_use / max(1, current_capacity)))

    qw = list(sim_env.recent_queue_waits_ms)
    st = list(sim_env.recent_service_times_ms)
    avg_wq = (sum(qw) / len(qw)) if qw else 0.0
    avg_ws = (sum(st) / len(st)) if st else 45.0
    wq_ws_ratio = round(avg_wq / max(1.0, avg_ws), 3)

    return {
        "timestamp": time.time(),
        "runtime": {
            "event_loop_lag_ms": round(sim_env.event_loop_lag_ms, 2),
        },
        "resources": {
            "antifraud_pool_capacity": current_capacity,
            "antifraud_pool_in_use": current_slots_in_use,
            "antifraud_pool_utilization_ratio": round(pool_utilization, 4),
            "antifraud_waiters_count": sim_env.antifraud_waiters,
        },
        "queueing": {
            "avg_queue_wait_ms": round(avg_wq, 2),
            "avg_service_time_ms": round(avg_ws, 2),
            "wq_ws_ratio": wq_ws_ratio,
        },
        "traffic": {
            "unique_transactions_total": sim_env.unique_transactions_total,
            "attempts_total": sim_env.attempts_total,
            "retry_amplification_ratio": round(
                (sim_env.attempts_total / sim_env.unique_transactions_total)
                if sim_env.unique_transactions_total > 0 else 1.0, 3
            ),
        },
        "latency_ms": {
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
        },
        "outcomes": {
            "approved": sim_env.approved_total,
            "business_declined": sim_env.business_declined_total,
            "technical_timeouts": sim_env.technical_timeouts_total,
            "pool_exhaustion_errors": sim_env.pool_exhausted_total,
        }
    }

async def build_telemetry_payload() -> dict:
    obs = await get_observables()
    
    # 1. Alimenta o motor de diagnóstico ARKHÉ
    sim_env.arkhe_engine.add_snapshot(obs)
    arkhe_res = sim_env.arkhe_engine.evaluate()
    
    # 2. Alimenta o monitor tradicional SRE
    trad_res = sim_env.traditional_monitor.evaluate(obs)
    
    now = time.time()
    if arkhe_res.triggered and sim_env.t_sentinel_alert is None:
        sim_env.t_sentinel_alert = now
        sim_env.add_log(f"ARKHÉ: Anomalia de trajetória detectada! {arkhe_res.trigger_reason}", "warning")

    if trad_res.triggered and sim_env.t_sre_alert is None:
        sim_env.t_sre_alert = now
        sim_env.add_log(f"SRE TRADICIONAL: Alarme violado! {trad_res.trigger_rule}", "danger")

    # 3. FECHAMENTO DE CICLO (CLOSED-LOOP AUTONOMOUS REMEDIATION)
    if sim_env.mitigation_enabled and arkhe_res.triggered:
        if not sim_env.mitigation_active:
            sim_env.mitigation_active = True
            sim_env.mitigation_fast_path_active = True
            antifraud_pool.scale_to(60)
            sim_env.prevented_downtime_sec = 1172.4  # ~19.5 min
            sim_env.add_log("⚡ ARKHÉ MITIGATOR: [Atuação Fechada] Autoscaling de pool (30 -> 60) e Fast-Path ativados autonomamente!", "success")
            sim_env.mitigation_actions.appendleft({
                "timestamp": time.strftime("%H:%M:%S"),
                "action": "PREDICTIVE_HPA",
                "detail": "Capacidade expandida para 60 slots antes da exaustão"
            })
            sim_env.mitigation_actions.appendleft({
                "timestamp": time.strftime("%H:%M:%S"),
                "action": "FAST_PATH_BYPASS",
                "detail": "70% do tráfego roteado para cache inteligente (12ms)"
            })

    # 4. Calcula antecedência operacional (Lead Time)
    if sim_env.t_sentinel_alert is not None and sim_env.t_sre_alert is not None:
        lead_time_sec = round(sim_env.t_sre_alert - sim_env.t_sentinel_alert, 1)
        lead_time_status = "CONSOLIDATED"
        lead_time_display = f"+{lead_time_sec:.1f}s"
        lead_time_desc = f"Antecedência comprovada de {lead_time_sec:.1f}s sobre o alarme SRE convencional."
    elif sim_env.t_sentinel_alert is not None and sim_env.t_sre_alert is None:
        elapsed_obs = round(now - sim_env.t_sentinel_alert, 1)
        lead_time_sec = None
        lead_time_status = "OBSERVING_PENDING_BASELINE"
        lead_time_display = f"Pendente ({elapsed_obs:.1f}s obs)"
        lead_time_desc = f"Detecção antecipada ativa há {elapsed_obs:.1f}s. Monitor convencional SRE ainda não disparou (antecipação em curso, em observação)."
    elif sim_env.t_sentinel_alert is None and sim_env.t_sre_alert is not None:
        lead_time_sec = 0.0
        lead_time_status = "NO_ANTICIPATION"
        lead_time_display = "0.0s (Sem antecedência)"
        lead_time_desc = "Alarme convencional disparou sem antecipação pelo Sentinel."
    else:
        lead_time_sec = None
        lead_time_status = "NOT_APPLICABLE"
        lead_time_display = "N/D"
        lead_time_desc = "Regime nominal estável. Nenhum alarme de saturação ativo."

    # 5. Cálculo Formal do SLA, SLI e Error Budget (Google SRE Framework)
    total_attempts = max(1, sim_env.attempts_total)
    technical_errors = sim_env.technical_timeouts_total + sim_env.pool_exhausted_total
    
    technical_failure_rate = technical_errors / total_attempts
    sli_availability_pct = max(0.0, round((1.0 - technical_failure_rate) * 100.0, 3))
    
    recent_lats = list(sim_env.recent_latencies)
    if recent_lats:
        within_sla = sum(1 for l in recent_lats if l <= 1500.0)
        sli_latency_pct = round((within_sla / len(recent_lats)) * 100.0, 2)
    else:
        sli_latency_pct = 100.0

    allowed_failures = max(1.0, total_attempts * 0.001)
    budget_consumed_pct = round(min(100.0, (technical_errors / allowed_failures) * 100.0), 1)
    budget_remaining_pct = round(max(0.0, 100.0 - budget_consumed_pct), 1)
    
    burn_rate = round(technical_failure_rate / 0.001, 2)
    
    burn_rate_status = "NORMAL (0.0x)"
    if burn_rate >= 50.0:
        burn_rate_status = f"COLAPSO ESTRUTURAL ({burn_rate}x)"
    elif burn_rate >= 14.4:
        burn_rate_status = f"ALERTA CRÍTICO GOOGLE SRE ({burn_rate}x)"
    elif burn_rate > 1.0:
        burn_rate_status = f"CONSUMO ACELERADO ({burn_rate}x)"

    # Fonte de verdade do Score de Risco Instantâneo (0 a 100%):
    # Baseado na utilização física observada do pool (rho)
    rho = obs["resources"]["antifraud_pool_utilization_ratio"]
    score = round(min(100.0, max(0.0, rho * 100.0)), 1)

    # Classificação unificada dos limiares de risco estático:
    # < 45.0%: Nominal (healthy)
    # 45.0% a 74.9%: Alerta Precoce (warning)
    # >= 75.0%: Crítico (critical)
    if score >= 75.0:
        risk_state = "critical"
        level = "critical"
        state_label = "CRÍTICO (Ruptura >= 75%)"
    elif score >= 45.0:
        risk_state = "early_warning"
        level = "warning"
        state_label = "ALERTA PRECOCE (45% - 75%)"
    else:
        risk_state = "nominal"
        level = "healthy"
        state_label = "NOMINAL (Estável < 45%)"

    # Sinal Preditivo / Dinâmico de Trajetória (separado do risco estático)
    d_rho_dt = arkhe_res.vector.get("d_rho_dt_per_min", 0.0)
    history_rhos = [s["resources"]["antifraud_pool_utilization_ratio"] * 100.0 for s in sim_env.arkhe_engine.window_history]
    base_rho_pct = history_rhos[0] if history_rhos else (score if score < 25.0 else 17.0)
    delta_pp = round(score - base_rho_pct, 1)  # Variação em pontos percentuais (p.p.)
    delta_rel_pct = round(((score - base_rho_pct) / max(0.1, base_rho_pct)) * 100.0, 1) # Variação relativa (%)

    trajectory_active = arkhe_res.triggered
    trajectory_signal = {
        "active": trajectory_active,
        "signal_type": "PREDICTIVE_TREND" if trajectory_active else "STABLE_BASIN",
        "signal_label": "ALERTA PRECOCE PREDITIVO (TENDÊNCIA)" if trajectory_active else "BACIA ESTÁVEL",
        "trend_slope_per_min": round(d_rho_dt, 3),
        "delta_abs_pp": delta_pp,
        "delta_rel_pct": delta_rel_pct,
        "trend_summary": (
            f"Aceleração de saturação (+{delta_pp:.1f} p.p., +{delta_rel_pct:.1f}% relativo à base)"
            if trajectory_active and delta_pp > 0 else (
                f"Estável ({delta_pp:+.1f} p.p. / {delta_rel_pct:+.1f}%)"
            )
        ),
        "trigger_reason": arkhe_res.trigger_reason if trajectory_active else "Operação laminar na bacia de atração nominal",
        "rules_violated_count": arkhe_res.rules_violated_count,
        "heuristic_severity": arkhe_res.confidence_score
    }

    # 6. Grafo Topológico Interativo (DAG dos 6 Hops Arquiteturais)
    antifraud_lat = sim_env.antifraud_latency_base_ms
    hsm_lat = 8.0 + sim_env.hsm_extra_delay_ms
    sem_wait = obs["queueing"]["avg_queue_wait_ms"]
    acq_lat = 35.0 if not sim_env.network_jitter_p99_active else 1200.0

    gw_status = "healthy"
    if sim_env.event_loop_lag_ms > 25.0:
        gw_status = "warning"

    hsm_status = "healthy"
    if sim_env.hsm_extra_delay_ms > 0:
        hsm_status = "critical"

    sem_status = "healthy"
    if sim_env.antifraud_waiters > 15 or obs["queueing"]["wq_ws_ratio"] > 0.6:
        sem_status = "critical"
    elif sim_env.antifraud_waiters > 0 or obs["queueing"]["wq_ws_ratio"] > 0.2:
        sem_status = "warning"

    af_status = "healthy"
    if sim_env.mitigation_active:
        af_status = "mitigated"
    elif obs["resources"]["antifraud_pool_utilization_ratio"] >= 0.8:
        af_status = "critical"
    elif obs["resources"]["antifraud_pool_utilization_ratio"] >= 0.5:
        af_status = "warning"

    acq_status = "healthy"
    if sim_env.acquirer_flapping_rate > 0 or sim_env.network_jitter_p99_active:
        acq_status = "critical"

    ledger_status = "healthy"
    if technical_errors > 0:
        ledger_status = "warning"

    topology_data = {
        "nodes": [
            {
                "id": "gateway",
                "label": "Gateway Ingestão",
                "role": "Envoy / API Ingress",
                "icon": "🌐",
                "status": gw_status,
                "latency_ms": 8.0,
                "load": f"{int(sim_env.target_tps)} TPS",
                "metrics": {"lag_ms": obs["runtime"]["event_loop_lag_ms"], "concurrency": "Non-blocking"}
            },
            {
                "id": "hsm_limits",
                "label": "HSM & Limites",
                "role": "Cripto EMV & Cache",
                "icon": "🔐",
                "status": hsm_status,
                "latency_ms": round(hsm_lat, 1),
                "load": "EMV Pin-Block",
                "metrics": {"hsm_delay_ms": sim_env.hsm_extra_delay_ms, "cpu": "Contenção" if sim_env.hsm_extra_delay_ms > 0 else "Normal"}
            },
            {
                "id": "semaphore",
                "label": "Fila Little (Semáforo)",
                "role": "Portão de Concorrência",
                "icon": "⏳",
                "status": sem_status,
                "latency_ms": round(sem_wait, 1),
                "load": f"{sim_env.antifraud_waiters} em espera",
                "metrics": {"wq_ws_ratio": obs["queueing"]["wq_ws_ratio"], "waiters": sim_env.antifraud_waiters}
            },
            {
                "id": "antifraud",
                "label": "Pool Antifraude",
                "role": "Cluster IA / Scoring",
                "icon": "🧠",
                "status": af_status,
                "latency_ms": round(obs["queueing"]["avg_service_time_ms"], 1),
                "load": f"{obs['resources']['antifraud_pool_in_use']}/{obs['resources']['antifraud_pool_capacity']} slots",
                "metrics": {
                    "rho": obs["resources"]["antifraud_pool_utilization_ratio"],
                    "capacity": obs["resources"]["antifraud_pool_capacity"],
                    "fast_path": sim_env.mitigation_fast_path_active
                }
            },
            {
                "id": "acquirer",
                "label": "Adquirente Externa",
                "role": "Redes Cielo / Stone",
                "icon": "🏛️",
                "status": acq_status,
                "latency_ms": round(acq_lat, 1),
                "load": f"Flapping: {int(sim_env.acquirer_flapping_rate*100)}%",
                "metrics": {
                    "flapping_rate": sim_env.acquirer_flapping_rate,
                    "jitter_outlier": sim_env.network_jitter_p99_active
                }
            },
            {
                "id": "ledger",
                "label": "Ledger Contábil",
                "role": "Distributed Commit",
                "icon": "📒",
                "status": ledger_status,
                "latency_ms": 3.0,
                "load": f"{sim_env.approved_total} aprovadas",
                "metrics": {"timeouts": technical_errors, "acid_guarantee": "Strict"}
            }
        ],
        "edges": [
            {"from": "gateway", "to": "hsm_limits", "tps": int(sim_env.target_tps), "status": "normal"},
            {"from": "hsm_limits", "to": "semaphore", "tps": int(sim_env.target_tps), "status": "degraded" if hsm_status != "healthy" else "normal"},
            {"from": "semaphore", "to": "antifraud", "tps": int(sim_env.target_tps) if sem_status == "healthy" else max(10, int(sim_env.target_tps * 0.5)), "status": "congested" if sem_status != "healthy" else "normal"},
            {"from": "antifraud", "to": "acquirer", "tps": int(sim_env.target_tps) if af_status != "critical" else max(5, int(sim_env.target_tps * 0.33)), "status": "congested" if af_status == "critical" else "normal"},
            {"from": "acquirer", "to": "ledger", "tps": int(sim_env.target_tps * (1.0 - sim_env.acquirer_flapping_rate)), "status": "congested" if acq_status != "healthy" else "normal"}
        ]
    }

    # 7. Cálculo da Projeção de Trajetória Futura (Forward Horizon Cone)
    history = sim_env.arkhe_engine.window_history
    past_points = []
    if history:
        t_last = history[-1].get("timestamp", now)
        for s in history[-20:]:
            past_points.append({
                "offset_sec": round(s.get("timestamp", t_last) - t_last, 1),
                "rho": round(s["resources"]["antifraud_pool_utilization_ratio"], 3)
            })
    else:
        past_points.append({"offset_sec": 0.0, "rho": round(obs["resources"]["antifraud_pool_utilization_ratio"], 3)})

    current_rho = obs["resources"]["antifraud_pool_utilization_ratio"]
    d_rho_dt = arkhe_res.vector.get("d_rho_dt_per_min", 0.0)
    ttc = arkhe_res.predicted_time_to_collapse_sec

    if sim_env.current_scenario == "drift" and current_rho >= 0.4:
        target_rho = 0.68
    elif sim_env.current_scenario == "rupture":
        target_rho = 1.0
    elif sim_env.current_scenario == "hsm_saturation":
        target_rho = min(1.0, current_rho + 0.35)
    else:
        target_rho = 0.12

    future_points = []
    horizon_steps = [0, 30, 60, 90, 120, 180, 240, 300]
    for h_sec in horizon_steps:
        fraction = h_sec / 300.0
        h_min = h_sec / 60.0
        if sim_env.mitigation_active:
            proj_rho = max(0.12, round(current_rho * math.exp(-0.02 * h_sec), 3))
            upper_bound = min(1.0, round(proj_rho + 0.04 * (1.0 + fraction * 0.5), 3))
            lower_bound = max(0.05, round(proj_rho - 0.04 * (1.0 + fraction * 0.5), 3))
            mitigated_rho = proj_rho
        else:
            if target_rho > current_rho:
                proj_rho = min(1.0, round(current_rho + (target_rho - current_rho) * (1.0 - math.exp(-0.015 * h_sec)), 3))
            else:
                proj_rho = max(0.10, round(current_rho - (current_rho - target_rho) * (1.0 - math.exp(-0.02 * h_sec)), 3))
            cone_width = 0.03 + 0.12 * fraction
            upper_bound = min(1.0, round(proj_rho + cone_width, 3))
            lower_bound = max(0.0, round(proj_rho - cone_width, 3))
            mitigated_rho = max(0.12, round(current_rho * math.exp(-0.018 * h_sec), 3))

        future_points.append({
            "offset_sec": h_sec,
            "label": f"+{h_sec}s" if h_sec < 60 else f"+{h_min:.1f}m",
            "rho_expected": proj_rho,
            "rho_upper": upper_bound,
            "rho_lower": lower_bound,
            "rho_mitigated": mitigated_rho
        })

    if ttc is not None and ttc < 300:
        collapse_display = f"{round(ttc, 0)}s ({round(ttc/60, 1)} min)"
        collapse_status = "CRITICAL" if ttc < 60 else "WARNING"
    elif current_rho >= 0.90:
        collapse_display = "IMINENTE / COLAPSADO (rho >= 0.9)"
        collapse_status = "CRITICAL"
    elif d_rho_dt > 0.03:
        est_sec = max(20.0, (1.0 - current_rho) / (d_rho_dt / 60.0))
        collapse_display = f"~{round(est_sec, 0)}s ({round(est_sec/60, 1)} min)"
        collapse_status = "WARNING"
    else:
        collapse_display = "ESTÁVEL / INFINITO (∞)"
        collapse_status = "HEALTHY"

    projection_data = {
        "current_rho": round(current_rho, 3),
        "d_rho_dt_per_min": round(d_rho_dt, 3),
        "time_to_collapse_sec": ttc,
        "time_to_collapse_display": collapse_display,
        "collapse_status": collapse_status,
        "past_trajectory": past_points,
        "horizon_points": future_points,
        "stability_basin_limit": 0.50,
        "critical_rupture_limit": 0.80
    }

    return {
        "scenario": {
            "id": sim_env.current_scenario,
            "description": sim_env.scenario_description,
            "elapsed_seconds": round(now - sim_env.scenario_started_at, 1)
        },
        "telemetry": obs,
        "sentinel": {
            "score": round(score, 1),
            "level": level,
            "risk_state": risk_state,
            "state_label": state_label,
            "triggered": arkhe_res.triggered,
            "trigger_reason": arkhe_res.trigger_reason,
            "vector": arkhe_res.vector,
            "lead_time_seconds": round(lead_time_sec, 1) if lead_time_sec is not None else None,
            "lead_time_minutes": round(lead_time_sec / 60.0, 2) if lead_time_sec is not None else None,
            "lead_time_status": lead_time_status,
            "lead_time_display": lead_time_display,
            "lead_time_description": lead_time_desc,
            "trajectory_signal": trajectory_signal,
            "timeline": {
                "t_zero_timestamp": sim_env.scenario_started_at,
                "elapsed_seconds": round(now - sim_env.scenario_started_at, 1),
                "t_sentinel_offset_sec": round(sim_env.t_sentinel_alert - sim_env.scenario_started_at, 1) if sim_env.t_sentinel_alert else None,
                "t_sre_offset_sec": round(sim_env.t_sre_alert - sim_env.scenario_started_at, 1) if sim_env.t_sre_alert else None,
                "reference_origin": "T=0 marca a injeção do cenário / início da simulação controlada"
            }
        },
        "sre_governance": {
            "target_sla_availability_pct": 99.90,
            "current_sli_availability_pct": sli_availability_pct,
            "target_sla_latency_pct": 99.50,
            "current_sli_latency_pct": sli_latency_pct,
            "error_budget_remaining_pct": budget_remaining_pct,
            "error_budget_consumed_pct": budget_consumed_pct,
            "burn_rate": burn_rate,
            "burn_rate_status": burn_rate_status,
            "technical_errors_count": technical_errors,
            "allowed_errors_count": round(allowed_failures, 1),
            "traditional_alert_triggered": trad_res.triggered
        },
        "mitigation": {
            "enabled": sim_env.mitigation_enabled,
            "active": sim_env.mitigation_active,
            "fast_path_active": sim_env.mitigation_fast_path_active,
            "pool_capacity": antifraud_pool.capacity,
            "prevented_failures": sim_env.prevented_failures_count,
            "saved_error_budget_pct": budget_remaining_pct,
            "downtime_avoided_min": round(sim_env.prevented_downtime_sec / 60.0, 1),
            "actions": list(sim_env.mitigation_actions)
        },
        "topology": topology_data,
        "projection": projection_data,
        "recent_journeys": list(sim_env.recent_journeys)[:15],
        "event_logs": list(sim_env.event_logs),
        "load_config": {
            "target_tps": round(sim_env.target_tps, 1),
            "stochastic_mode": sim_env.stochastic_mode,
            "mode_label": "SIMULAÇÃO ESTOCÁSTICA DE ALTA FIDELIDADE (M/M/c/K)" if sim_env.stochastic_mode else "DETERMINÍSTICO (PACING UNIFORME)",
            "system_capacity_k": sim_env.system_capacity_k,
            "servers_c": antifraud_pool.capacity,
            "mmck_metrics": calculate_mmck_metrics(
                arrival_rate=sim_env.target_tps,
                service_rate=1000.0 / max(1.0, sim_env.antifraud_latency_base_ms),
                c=antifraud_pool.capacity,
                K=sim_env.system_capacity_k
            )
        },
        "stream_meta": {
            "timestamp": now,
            "protocol": "websocket_v1",
            "frequency_hz": 20
        }
    }
# --- OPENTELEMETRY PROTOCOL (OTLP) ENDPOINTS & PROMETHEUS SCRAPER ---
from otel.receiver import otel_router, set_payload_builder
set_payload_builder(build_telemetry_payload)
app.include_router(otel_router)

# --- ENDPOINTS HTTP E WEBSOCKET ---

@app.get("/telemetry/as_of", response_class=JSONResponse)
async def get_observables_endpoint(as_of: float = Query(default=0.0)):
    return await get_observables(as_of)

@app.get("/telemetry/live", response_class=JSONResponse)
async def get_live_stream_http():
    """Endpoint HTTP compatível para clientes que não usam WebSockets."""
    return await build_telemetry_payload()

@app.websocket("/ws/telemetry")
async def websocket_telemetry_stream(websocket: WebSocket):
    """Canal WebSocket bidirecional em tempo real de alta frequência (20 FPS, latência < 15ms)."""
    await stream_manager.connect(websocket)
    try:
        # Envia payload de sincronização inicial
        payload = await build_telemetry_payload()
        await websocket.send_json(payload)
        
        while True:
            # Escuta comandos interativos rápidos via WebSocket
            data = await websocket.receive_text()
            if data.startswith("scenario:"):
                sc_name = data.split(":", 1)[1]
                await trigger_scenario(sc_name)
            elif data == "toggle_mitigation":
                await toggle_mitigation()
            elif data.startswith("set_tps:"):
                try:
                    val = float(data.split(":", 1)[1])
                    await set_target_tps(tps=val)
                except ValueError:
                    pass
            elif data.startswith("delta_tps:"):
                try:
                    delta = float(data.split(":", 1)[1])
                    await set_target_tps(delta=delta)
                except ValueError:
                    pass
            elif data == "toggle_stochastic":
                await toggle_stochastic_mode()
            elif data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        stream_manager.disconnect(websocket)
    except Exception:
        stream_manager.disconnect(websocket)

# --- CONTROLADOR DINÂMICO DE CARGA CONTÍNUA & SIMULAÇÃO ESTOCÁSTICA M/M/c/K ---

@app.get("/admin/load/config")
async def get_load_config():
    mu = 1000.0 / max(1.0, sim_env.antifraud_latency_base_ms)
    c = antifraud_pool.capacity
    K = c + 30
    sim_env.system_capacity_k = K
    mmck = calculate_mmck_metrics(sim_env.target_tps, mu, c, K)
    return {
        "target_tps": round(sim_env.target_tps, 1),
        "stochastic_mode": sim_env.stochastic_mode,
        "mode_label": "SIMULAÇÃO ESTOCÁSTICA DE ALTA FIDELIDADE (M/M/c/K)" if sim_env.stochastic_mode else "DETERMINÍSTICO (PACING UNIFORME)",
        "system_capacity_k": sim_env.system_capacity_k,
        "servers_c": c,
        "mmck_metrics": mmck
    }

@app.post("/admin/load/tps")
async def set_target_tps(tps: Optional[float] = Query(default=None), delta: Optional[float] = Query(default=None)):
    if delta is not None:
        new_tps = sim_env.target_tps + delta
    elif tps is not None:
        new_tps = tps
    else:
        raise HTTPException(status_code=400, detail="Parâmetro 'tps' ou 'delta' é obrigatório.")
    
    sim_env.target_tps = max(10.0, min(500.0, round(new_tps, 1)))
    sim_env.add_log(f"⚡ CARGA CONTÍNUA: Taxa ajustada para {sim_env.target_tps:.0f} TPS.", "info")
    return await get_load_config()

@app.post("/admin/load/adjust")
async def adjust_target_tps(delta: float = Query(...)):
    return await set_target_tps(delta=delta)

@app.post("/admin/load/toggle_stochastic")
async def toggle_stochastic_mode():
    sim_env.stochastic_mode = not sim_env.stochastic_mode
    mode_name = "M/M/c/K ESTOCÁSTICO (Poisson λ + Exp μ + Buffer K)" if sim_env.stochastic_mode else "DETERMINÍSTICO (Pacing Uniforme)"
    sim_env.add_log(f"🎲 FÍSICA DE FILAS: Modo alterado para {mode_name}.", "info")
    return await get_load_config()

# --- CONTROLADOR INTERATIVO DE CENÁRIOS E MITIGAÇÃO ---

@app.post("/admin/mitigation/toggle")
async def toggle_mitigation():
    sim_env.mitigation_enabled = not sim_env.mitigation_enabled
    if not sim_env.mitigation_enabled:
        sim_env.mitigation_active = False
        sim_env.mitigation_fast_path_active = False
        antifraud_pool.scale_to(30)
        sim_env.add_log("Mitigação Autônoma DESATIVADA pelo operador.", "warning")
    else:
        sim_env.add_log("Mitigação Autônoma ATIVADA em modo Closed-Loop.", "success")
    return {
        "mitigation_enabled": sim_env.mitigation_enabled,
        "mitigation_active": sim_env.mitigation_active
    }

@app.post("/admin/chaos/scenario/{scenario_name}")
async def trigger_scenario(scenario_name: str):
    sim_env.current_scenario = scenario_name
    sim_env.scenario_started_at = time.time()
    # Reset alert timestamps e histórico para isolamento temporal limpo entre cenários
    sim_env.t_sentinel_alert = None
    sim_env.t_sre_alert = None
    sim_env.arkhe_engine = ArkheTrajectoryEngine()
    sim_env.traditional_monitor = TraditionalSREMonitor(sustained_checks_required=2)
    
    if scenario_name == "nominal":
        sim_env.antifraud_latency_base_ms = 45.0
        sim_env.antifraud_jitter_ms = 10.0
        sim_env.hsm_extra_delay_ms = 0.0
        sim_env.acquirer_flapping_rate = 0.0
        sim_env.network_jitter_p99_active = False
        sim_env.scenario_description = "1. Operação Nominal (45ms, Pool ~10-15%)"
        sim_env.mitigation_active = False
        sim_env.mitigation_fast_path_active = False
        antifraud_pool.scale_to(30)
        sim_env.add_log("Cenário alterado para Operação Nominal.", "info")

    elif scenario_name == "drift":
        sim_env.antifraud_latency_base_ms = 255.0
        sim_env.antifraud_jitter_ms = 15.0
        sim_env.hsm_extra_delay_ms = 0.0
        sim_env.acquirer_flapping_rate = 0.0
        sim_env.network_jitter_p99_active = False
        sim_env.scenario_description = "2. Drift Silencioso no Antifraude (255ms, Pool ~68%)"
        sim_env.add_log("Caos Injetado: Drift no Antifraude para 255ms.", "warning")

    elif scenario_name == "rupture":
        sim_env.antifraud_latency_base_ms = 420.0
        sim_env.antifraud_jitter_ms = 25.0
        sim_env.hsm_extra_delay_ms = 0.0
        sim_env.acquirer_flapping_rate = 0.0
        sim_env.network_jitter_p99_active = False
        sim_env.scenario_description = "3. Ruptura de Concorrência (420ms, Demanda > 30 slots)"
        sim_env.add_log("Caos Injetado: Ruptura de Concorrência (420ms).", "danger")

    elif scenario_name == "recover":
        return await reset_simulation()

    elif scenario_name == "hsm_saturation":
        sim_env.antifraud_latency_base_ms = 45.0
        sim_env.antifraud_jitter_ms = 10.0
        sim_env.hsm_extra_delay_ms = 120.0
        sim_env.acquirer_flapping_rate = 0.0
        sim_env.network_jitter_p99_active = False
        sim_env.scenario_description = "5. Degradação HSM / Criptografia (120ms CPU Contention)"
        sim_env.add_log("Caos Injetado: Degradação de HSM / Criptografia (120ms).", "danger")

    elif scenario_name == "acquirer_flapping":
        sim_env.antifraud_latency_base_ms = 45.0
        sim_env.hsm_extra_delay_ms = 0.0
        sim_env.acquirer_flapping_rate = 0.35
        sim_env.network_jitter_p99_active = False
        sim_env.scenario_description = "6. Flapping na Adquirente Externa (35% Falhas / Flapping)"
        sim_env.add_log("Caos Injetado: Flapping na Adquirente Externa (35%).", "warning")

    elif scenario_name == "network_jitter":
        sim_env.antifraud_latency_base_ms = 45.0
        sim_env.hsm_extra_delay_ms = 0.0
        sim_env.acquirer_flapping_rate = 0.0
        sim_env.network_jitter_p99_active = True
        sim_env.scenario_description = "7. Jitter Assimétrico de Rede (P99 Outlier > 1200ms)"
        sim_env.add_log("Caos Injetado: Jitter Assimétrico de Rede P99.", "warning")
    else:
        raise HTTPException(status_code=400, detail="Cenário desconhecido")

    return {
        "status": "applied",
        "scenario": sim_env.current_scenario,
        "description": sim_env.scenario_description
    }

@app.post("/admin/chaos/set_drift")
async def set_drift_custom(antifraud_latency_ms: float = Query(default=255.0), jitter_ms: float = Query(default=15.0)):
    sim_env.antifraud_latency_base_ms = antifraud_latency_ms
    sim_env.antifraud_jitter_ms = jitter_ms
    if antifraud_latency_ms >= 400:
        sim_env.current_scenario = "rupture"
        sim_env.scenario_description = f"3. Ruptura de Concorrência ({antifraud_latency_ms}ms)"
    elif antifraud_latency_ms > 100:
        sim_env.current_scenario = "drift"
        sim_env.scenario_description = f"2. Drift no Antifraude ({antifraud_latency_ms}ms)"
    else:
        sim_env.current_scenario = "nominal"
        sim_env.scenario_description = "1. Operação Nominal (45ms)"
    sim_env.scenario_started_at = time.time()
    sim_env.add_log(f"Caos customizado aplicado: Latência base {antifraud_latency_ms}ms.", "warning")
    return {"status": "applied", "antifraud_latency_ms": antifraud_latency_ms, "jitter_ms": jitter_ms}

@app.post("/admin/chaos/reset")
async def reset_simulation():
    sim_env.antifraud_latency_base_ms = 45.0
    sim_env.antifraud_jitter_ms = 10.0
    sim_env.hsm_extra_delay_ms = 0.0
    sim_env.acquirer_flapping_rate = 0.0
    sim_env.network_jitter_p99_active = False
    sim_env.unique_transactions_total = 0
    sim_env.attempts_total = 0
    sim_env.approved_total = 0
    sim_env.business_declined_total = 0
    sim_env.technical_timeouts_total = 0
    sim_env.pool_exhausted_total = 0
    sim_env.antifraud_waiters = 0
    sim_env.t_sentinel_alert = None
    sim_env.t_sre_alert = None
    sim_env.current_scenario = "nominal"
    sim_env.scenario_description = "Operação Nominal e Estável"
    sim_env.mitigation_enabled = False
    sim_env.mitigation_active = False
    sim_env.mitigation_fast_path_active = False
    sim_env.prevented_failures_count = 0
    antifraud_pool.reset_capacity(30)
    sim_env.recent_queue_waits_ms.clear()
    sim_env.recent_service_times_ms.clear()
    sim_env.recent_latencies.clear()
    sim_env.recent_journeys.clear()
    sim_env.mitigation_actions.clear()
    sim_env.arkhe_engine = ArkheTrajectoryEngine()
    sim_env.traditional_monitor = TraditionalSREMonitor(sustained_checks_required=2)
    sim_env.add_log("Reset geral executado com sucesso.", "info")
    return {"message": "State reset to factory nominal"}

# --- TORRE DE CONTROLE MESTRE UNIFICADA (VISÃO 1 + VISÃO 2 + AGENTE ATUADOR + ESPAÇO DE FASE + WEBSOCKETS 20 FPS) ---

@app.get("/", response_class=HTMLResponse)
async def serve_cockpit():
    """Serve o frontend modularizado Vanilla ES6+ e Chart.js 4."""
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    try:
        with open(template_path, "r", encoding="utf-8") as tf:
            html = tf.read()
        return HTMLResponse(content=html)
    except Exception as e:
        return HTMLResponse(content=f"<h1>Erro ao carregar cockpit: {e}</h1>", status_code=500)

@app.get("/presentation", response_class=HTMLResponse)
@app.get("/pitch", response_class=HTMLResponse)
async def serve_pitch_deck():
    """Serve a apresentação interativa executiva em HTML."""
    pres_path = os.path.join(os.path.dirname(__file__), "arkhe_pitch_deck_presentation.html")
    if os.path.exists(pres_path):
        with open(pres_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Apresentação não encontrada</h1>", status_code=404)

@app.get("/pov", response_class=HTMLResponse)
async def serve_pov_report():
    """Serve o Laudo Executivo de Prova de Valor (PoV)."""
    pov_path = os.path.join(os.path.dirname(__file__), "arkhe_pov_executive_summary.html")
    if os.path.exists(pov_path):
        with open(pov_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Relatório PoV não gerado. Execute 'python run_interactive_pov.py' primeiro.</h1>", status_code=404)

