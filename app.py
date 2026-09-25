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

# Estado global da simulação
class SimulationEnvironment:
    def __init__(self):
        # Controle de Caos interno (GROUND TRUTH)
        self.antifraud_latency_base_ms: float = 45.0
        self.antifraud_jitter_ms: float = 10.0
        self.network_error_rate: float = 0.001
        
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
            if use_fast_path:
                # FAST-PATH AUTÔNOMO: validação em cache rápido (12ms) em vez de 255ms/420ms
                latency = 0.012
                risk_score = (int(intent.card_token[-2:], 16) % 100) if len(intent.card_token) >= 2 else 15
                sim_env.prevented_failures_count += 1
            else:
                latency = np.random.normal(
                    sim_env.antifraud_latency_base_ms,
                    sim_env.antifraud_jitter_ms
                )
                latency = max(5.0, latency) / 1000.0
                risk_score = (int(intent.card_token[-2:], 16) % 100) if len(intent.card_token) >= 2 else 15
            
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
    if sim_env.t_sentinel_alert is not None:
        if sim_env.t_sre_alert is None:
            lead_time_sec = now - sim_env.t_sentinel_alert
        else:
            lead_time_sec = sim_env.t_sre_alert - sim_env.t_sentinel_alert
    else:
        lead_time_sec = 0.0

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

    if arkhe_res.triggered:
        score = max(70.0, arkhe_res.confidence_score * 100.0)
    else:
        rho = obs["resources"]["antifraud_pool_utilization_ratio"]
        score = max(0.0, min(100.0, rho * 45.0))

    level = "healthy"
    if score >= 85: level = "critical"
    elif score >= 70: level = "high"
    elif score >= 50: level = "unstable"
    elif score >= 30: level = "attention"

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
                "load": "120 TPS",
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
            {"from": "gateway", "to": "hsm_limits", "tps": 120, "status": "normal"},
            {"from": "hsm_limits", "to": "semaphore", "tps": 120, "status": "degraded" if hsm_status != "healthy" else "normal"},
            {"from": "semaphore", "to": "antifraud", "tps": 120 if sem_status == "healthy" else 60, "status": "congested" if sem_status != "healthy" else "normal"},
            {"from": "antifraud", "to": "acquirer", "tps": 120 if af_status != "critical" else 40, "status": "congested" if af_status == "critical" else "normal"},
            {"from": "acquirer", "to": "ledger", "tps": int(120 * (1.0 - sim_env.acquirer_flapping_rate)), "status": "congested" if acq_status != "healthy" else "normal"}
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
            "triggered": arkhe_res.triggered,
            "trigger_reason": arkhe_res.trigger_reason,
            "vector": arkhe_res.vector,
            "lead_time_seconds": round(lead_time_sec, 1),
            "lead_time_minutes": round(lead_time_sec / 60.0, 2)
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
        "stream_meta": {
            "timestamp": now,
            "protocol": "websocket_v1",
            "frequency_hz": 20
        }
    }

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
            elif data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        stream_manager.disconnect(websocket)
    except Exception:
        stream_manager.disconnect(websocket)

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
    
    if scenario_name == "nominal":
        sim_env.antifraud_latency_base_ms = 45.0
        sim_env.antifraud_jitter_ms = 10.0
        sim_env.hsm_extra_delay_ms = 0.0
        sim_env.acquirer_flapping_rate = 0.0
        sim_env.network_jitter_p99_active = False
        sim_env.scenario_description = "1. Operação Nominal (45ms, Pool ~10%)"
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
        sim_env.antifraud_latency_base_ms = 45.0
        sim_env.antifraud_jitter_ms = 10.0
        sim_env.hsm_extra_delay_ms = 0.0
        sim_env.acquirer_flapping_rate = 0.0
        sim_env.network_jitter_p99_active = False
        sim_env.scenario_description = "4. Autocura / Restauração do Sistema (45ms)"
        sim_env.t_sentinel_alert = None
        sim_env.t_sre_alert = None
        sim_env.technical_timeouts_total = 0
        sim_env.pool_exhausted_total = 0
        sim_env.mitigation_active = False
        sim_env.mitigation_fast_path_active = False
        antifraud_pool.scale_to(30)
        sim_env.add_log("Sistema restaurado para estado saudável de fábrica.", "success")

    elif scenario_name == "hsm_saturation":
        sim_env.hsm_extra_delay_ms = 120.0
        sim_env.scenario_description = "5. Gargalo de HSM / Criptografia (120ms CPU Contention)"
        sim_env.add_log("Caos Injetado: Gargalo de HSM / Criptografia (120ms).", "danger")

    elif scenario_name == "acquirer_flapping":
        sim_env.acquirer_flapping_rate = 0.35
        sim_env.scenario_description = "6. Flapping na Adquirente Externa (35% Falhas / Flapping)"
        sim_env.add_log("Caos Injetado: Flapping na Adquirente Externa (35%).", "warning")

    elif scenario_name == "network_jitter":
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
    sim_env.add_log("Reset geral executado com sucesso.", "info")
    return {"message": "State reset to factory nominal"}

# --- TORRE DE CONTROLE MESTRE UNIFICADA (VISÃO 1 + VISÃO 2 + AGENTE ATUADOR + ESPAÇO DE FASE + WEBSOCKETS 20 FPS) ---

@app.get("/", response_class=HTMLResponse)
async def serve_cockpit():
    html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ARKHÉ SENTINEL — Cockpit Mestre: Trajetória, SRE & Mitigação Autônoma (20 FPS WS)</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg: #090d16;
            --panel: #111827;
            --panel-border: #1f293d;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --arkhe-blue: #388bfd;
            --arkhe-cyan: #58a6ff;
            --green: #238636;
            --green-glow: #3fb950;
            --yellow: #d29922;
            --red: #da3633;
            --red-glow: #f85149;
            --purple: #8b5cf6;
        }
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
        }
        .container { max-width: 1440px; margin: 0 auto; }
        
        /* Header */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--panel-border);
            padding-bottom: 18px;
            margin-bottom: 20px;
        }
        .brand { display: flex; align-items: center; gap: 14px; }
        .brand-logo {
            width: 44px; height: 44px;
            background: linear-gradient(135deg, #2563eb, #7c3aed);
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 22px; font-weight: 800;
        }
        .header-actions { display: flex; align-items: center; gap: 12px; }
        
        /* Badge WebSocket Streaming */
        .ws-badge {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 6px 14px; border-radius: 20px;
            font-size: 11px; font-weight: 700;
            letter-spacing: 0.5px;
            transition: all 0.3s ease;
        }
        .ws-active {
            background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.5);
            color: #34d399;
        }
        .ws-polling {
            background: rgba(210, 153, 34, 0.15); border: 1px solid rgba(210, 153, 34, 0.5);
            color: #fbbf24;
        }
        .pulse-dot-ws {
            width: 8px; height: 8px; border-radius: 50%;
            background: #34d399; box-shadow: 0 0 10px #34d399;
            animation: pulse-ws 1.0s infinite;
        }
        @keyframes pulse-ws { 0% { opacity: 0.3; } 50% { opacity: 1; } 100% { opacity: 0.3; } }

        .live-badge {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 6px 14px; border-radius: 20px;
            background: rgba(56, 139, 253, 0.12); border: 1px solid rgba(56, 139, 253, 0.35);
            color: #93c5fd; font-size: 12px; font-weight: 600;
        }

        /* Botão Interruptor de Mitigação Autônoma */
        .btn-mitigation-toggle {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 8px 18px; border-radius: 20px;
            font-size: 13px; font-weight: 700; cursor: pointer;
            transition: all 0.25s ease;
            border: 1px solid #3b82f6;
            background: rgba(59, 130, 246, 0.15);
            color: #93c5fd;
        }
        .btn-mitigation-toggle:hover {
            transform: scale(1.03);
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.4);
        }
        .btn-mitigation-toggle.enabled {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.25), rgba(59, 130, 246, 0.25));
            border-color: var(--green-glow);
            color: var(--green-glow);
            box-shadow: 0 0 15px rgba(63, 185, 80, 0.3);
        }

        /* Scenario Control Deck */
        .deck {
            background: var(--panel);
            border: 1px solid var(--panel-border);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 20px;
        }
        .deck-title {
            font-size: 12px; text-transform: uppercase; letter-spacing: 1px;
            color: var(--text-muted); margin-bottom: 12px;
        }
        .scenario-buttons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
        }
        .btn-scenario {
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid #30363d;
            background: #1c2128;
            color: #c9d1d9;
            font-size: 13px; font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            text-align: left;
            display: flex; flex-direction: column; gap: 4px;
        }
        .btn-scenario:hover {
            transform: translateY(-2px);
            border-color: var(--arkhe-blue);
        }
        .btn-scenario.active {
            border-color: var(--arkhe-cyan);
            background: rgba(56, 139, 253, 0.15);
            box-shadow: 0 0 15px rgba(56, 139, 253, 0.3);
        }
        .btn-scenario span.sub { font-size: 11px; color: var(--text-muted); font-weight: normal; }

        /* Banner de Antecedência Operacional */
        .lead-banner {
            background: linear-gradient(135deg, rgba(30, 58, 138, 0.4), rgba(88, 28, 135, 0.4));
            border: 1px solid rgba(56, 139, 253, 0.4);
            border-radius: 10px;
            padding: 18px 22px;
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 20px;
        }
        .lead-time-val { font-size: 40px; font-weight: 800; color: #60a5fa; }
        .lead-title { font-size: 13px; text-transform: uppercase; color: #93c5fd; letter-spacing: 0.5px; }

        /* Card do Agente de Mitigação Autônoma (Closed-Loop) */
        .mitigation-panel {
            background: linear-gradient(135deg, #0e1e38 0%, #13172e 100%);
            border: 1px solid rgba(56, 139, 253, 0.35);
            border-radius: 12px;
            padding: 18px 22px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }
        .mitigation-header {
            display: flex; justify-content: space-between; align-items: center;
            border-bottom: 1px solid rgba(56, 139, 253, 0.2);
            padding-bottom: 12px; margin-bottom: 14px;
        }
        .mitigation-grid {
            display: grid;
            grid-template-columns: 1.2fr 1fr 1fr;
            gap: 16px;
        }
        .mit-stat-box {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(56, 139, 253, 0.2);
            border-radius: 8px;
            padding: 12px 14px;
        }
        .mit-badge {
            display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700;
        }

        /* SRE Error Budget Deck */
        .sre-deck {
            background: linear-gradient(180deg, #111827 0%, #0c121e 100%);
            border: 1px solid #233044;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .sre-deck-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 14px; border-bottom: 1px solid #1f2937; padding-bottom: 10px;
        }
        .sre-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
        }
        .sre-card {
            background: #172030;
            border: 1px solid #26354a;
            border-radius: 8px;
            padding: 16px;
        }
        .sre-label { font-size: 11px; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px; }
        .sre-val { font-size: 26px; font-weight: 800; margin: 6px 0; }
        .burn-badge {
            display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;
        }

        /* KPI Grid: Física de Filas & Lei de Little */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }
        .kpi-card {
            background: var(--panel);
            border: 1px solid var(--panel-border);
            border-radius: 10px;
            padding: 18px;
        }
        .kpi-title { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
        .kpi-metric { font-size: 28px; font-weight: 700; margin: 6px 0; }
        .progress-bar-bg {
            width: 100%; height: 8px; background: #21262d; border-radius: 4px; overflow: hidden; margin-top: 8px;
        }
        .progress-bar-fill { height: 100%; transition: width 0.2s ease, background 0.2s ease; }

        /* Gráficos ao Vivo + Espaço de Fase 2D */
        .charts-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 18px;
            margin-bottom: 20px;
        }
        .chart-box {
            background: var(--panel);
            border: 1px solid var(--panel-border);
            border-radius: 10px;
            padding: 16px;
        }

        /* Comparação ARKHÉ vs SRE */
        .audit-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px;
            margin-bottom: 20px;
        }
        .status-badge {
            display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700;
        }
        .badge-healthy { background: rgba(35, 134, 54, 0.2); color: var(--green-glow); border: 1px solid var(--green-glow); }
        .badge-danger { background: rgba(218, 54, 51, 0.2); color: var(--red-glow); border: 1px solid var(--red-glow); }
        .badge-warning { background: rgba(210, 153, 34, 0.2); color: var(--yellow); border: 1px solid var(--yellow); }

        /* Waterfall Stream Section */
        .waterfall-section {
            background: var(--panel);
            border: 1px solid var(--panel-border);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .journey-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        .journey-table th {
            text-align: left; padding: 10px 12px;
            background: #182234; color: var(--text-muted); font-size: 11px; text-transform: uppercase;
            border-bottom: 1px solid var(--panel-border);
        }
        .journey-table td {
            padding: 10px 12px; border-bottom: 1px solid #1a2333;
            vertical-align: middle;
        }
        .journey-row:hover { background: #151f30; }
        .status-pill {
            display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700;
        }
        .pill-authorized { background: rgba(35, 134, 54, 0.25); color: var(--green-glow); border: 1px solid var(--green); }
        .pill-business { background: rgba(56, 139, 253, 0.2); color: #93c5fd; border: 1px solid var(--arkhe-blue); }
        .pill-timeout { background: rgba(218, 54, 51, 0.25); color: var(--red-glow); border: 1px solid var(--red); }
        
        .waterfall-track {
            display: flex; height: 18px; width: 100%; border-radius: 4px; overflow: hidden; background: #1e293b;
        }
        .w-stage {
            height: 100%; display: flex; align-items: center; justify-content: center;
            font-size: 10px; color: #fff; font-weight: bold; overflow: hidden;
            transition: width 0.15s;
        }
        .w-ingest { background: #3b82f6; }
        .w-limits { background: #06b6d4; }
        .w-queue { background: #eab308; }
        .w-antifraud { background: #10b981; }
        .w-authorizer { background: #8b5cf6; }
        .w-ledger { background: #64748b; }
        .w-failed { background: #ef4444 !important; }

        /* Event Log */
        .logs-box {
            background: var(--panel);
            border: 1px solid var(--panel-border);
            border-radius: 10px;
            padding: 16px 20px;
            max-height: 200px;
            overflow-y: auto;
        }
        .log-item {
            padding: 6px 10px;
            border-bottom: 1px solid #1f2937;
            font-size: 13px;
            display: flex; gap: 12px;
        }
        .log-time { color: var(--text-muted); font-family: monospace; }

        /* --- GRAFO TOPOLÓGICO INTERATIVO DOS 6 HOPS --- */
        .topology-deck {
            background: linear-gradient(180deg, #111827 0%, #0d131f 100%);
            border: 1px solid #1f293d;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            position: relative;
            overflow: hidden;
        }
        .topology-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 16px; border-bottom: 1px solid #1f2937; padding-bottom: 12px;
        }
        .topo-legend { display: flex; gap: 14px; align-items: center; font-size: 11px; }
        .topo-leg-item { display: inline-flex; align-items: center; gap: 6px; color: #94a3b8; }
        .topo-indicator { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
        .ind-healthy { background: #3fb950; box-shadow: 0 0 6px #3fb950; }
        .ind-warning { background: #d29922; box-shadow: 0 0 6px #d29922; }
        .ind-critical { background: #f85149; box-shadow: 0 0 8px #f85149; }
        .ind-mitigated { background: #38bdf8; box-shadow: 0 0 8px #38bdf8; }

        .topo-flow-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            position: relative;
            overflow-x: auto;
            padding: 10px 4px 14px 4px;
        }
        .topo-node {
            flex: 1;
            min-width: 175px;
            background: rgba(23, 32, 48, 0.9);
            border: 1px solid #26354a;
            border-radius: 10px;
            padding: 14px;
            cursor: pointer;
            transition: all 0.25s ease;
            position: relative;
            user-select: none;
        }
        .topo-node:hover {
            transform: translateY(-3px);
            border-color: var(--arkhe-blue);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
        }
        .topo-node.active-selected {
            border-color: #38bdf8 !important;
            box-shadow: 0 0 16px rgba(56, 189, 248, 0.4) !important;
        }
        .node-healthy { border-color: rgba(63, 185, 80, 0.6); box-shadow: 0 0 10px rgba(35, 134, 54, 0.15); }
        .node-warning { border-color: rgba(210, 153, 34, 0.8); box-shadow: 0 0 14px rgba(210, 153, 34, 0.25); }
        .node-critical { border-color: rgba(248, 81, 73, 0.9); box-shadow: 0 0 20px rgba(218, 54, 51, 0.4); animation: pulse-critical 1.5s infinite; }
        .node-mitigated { border-color: rgba(56, 189, 248, 0.9); box-shadow: 0 0 18px rgba(56, 189, 248, 0.35); }

        @keyframes pulse-critical {
            0% { box-shadow: 0 0 10px rgba(248, 81, 73, 0.3); }
            50% { box-shadow: 0 0 22px rgba(248, 81, 73, 0.7); }
            100% { box-shadow: 0 0 10px rgba(248, 81, 73, 0.3); }
        }

        .topo-node-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;
        }
        .node-step-tag {
            font-size: 10px; font-weight: 800; color: #94a3b8; background: #0f172a; padding: 2px 6px; border-radius: 4px;
        }
        .node-status-pill {
            font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 4px; text-transform: uppercase;
        }
        .pill-healthy { background: rgba(35, 134, 54, 0.25); color: #4ade80; }
        .pill-warning { background: rgba(210, 153, 34, 0.25); color: #fbbf24; }
        .pill-critical { background: rgba(218, 54, 51, 0.25); color: #f87171; }
        .pill-mitigated { background: rgba(56, 189, 248, 0.25); color: #38bdf8; }

        .topo-node-title { font-size: 13px; font-weight: 700; color: #f1f5f9; display: flex; align-items: center; gap: 6px; }
        .topo-node-role { font-size: 11px; color: #94a3b8; margin-top: 2px; }
        .topo-node-metrics {
            margin-top: 10px; display: flex; justify-content: space-between; font-size: 11px; background: rgba(15, 23, 42, 0.6); padding: 6px 8px; border-radius: 6px;
        }
        .node-m-val { font-weight: 700; color: #e2e8f0; }

        /* Conector e link com partículas de fluxo */
        .topo-edge {
            display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 44px; position: relative;
        }
        .edge-arrow {
            width: 100%; height: 2px; background: #334155; position: relative; overflow: visible;
        }
        .edge-flow-dot {
            width: 6px; height: 6px; border-radius: 50%; background: #38bdf8; position: absolute; top: -2px; left: 0;
            box-shadow: 0 0 8px #38bdf8;
            animation: flow-particle 1.2s infinite linear;
        }
        .edge-congested .edge-flow-dot {
            background: #f87171; box-shadow: 0 0 8px #f87171; animation-duration: 2.2s;
        }
        .edge-degraded .edge-flow-dot {
            background: #fbbf24; box-shadow: 0 0 8px #fbbf24; animation-duration: 1.8s;
        }
        @keyframes flow-particle {
            0% { left: 0%; opacity: 0; }
            20% { opacity: 1; }
            80% { opacity: 1; }
            100% { left: 100%; opacity: 0; }
        }
        .edge-tps-badge {
            font-size: 9px; font-weight: 700; color: #64748b; margin-top: 4px; white-space: nowrap;
        }

        .topo-inspector-bar {
            margin-top: 12px; background: #0b1120; border: 1px solid #1e293b; border-radius: 8px; padding: 10px 14px;
            font-size: 12px; color: #cbd5e1; display: flex; align-items: center; justify-content: space-between;
        }

        /* --- VISIBILIDADE DA TRAJETÓRIA ANTECIPADA (FORWARD HORIZON & CONE) --- */
        .horizon-deck {
            background: linear-gradient(180deg, #0e172a 0%, #0a0f1d 100%);
            border: 1px solid #233044;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .horizon-header {
            display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; border-bottom: 1px solid #1e293b; padding-bottom: 12px;
        }
        .horizon-stats-row {
            display: flex; gap: 16px; align-items: center;
        }
        .horizon-kpi-chip {
            background: #172033; border: 1px solid #28374d; border-radius: 8px; padding: 6px 12px; display: flex; align-items: center; gap: 8px;
        }
        .hz-kpi-lbl { font-size: 10px; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px; }
        .hz-kpi-val { font-size: 13px; font-weight: 800; }
        .horizon-chart-box {
            position: relative; width: 100%; height: 180px; margin-bottom: 12px;
        }
        .horizon-legend {
            display: flex; flex-wrap: wrap; gap: 18px; font-size: 11px; color: #94a3b8; justify-content: center; border-top: 1px solid #1e293b; padding-top: 10px;
        }
        .hz-legend-dot { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; vertical-align: middle; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <div class="brand-logo">A</div>
                <div>
                    <h1 style="margin:0; font-size: 22px;">ARKHÉ SENTINEL — Cockpit Mestre em Tempo Real</h1>
                    <span style="font-size: 13px; color: var(--text-muted);">
                        Física de Filas (Lei de Little), Diagnóstico Antecipado e Agente Atuador Closed-Loop
                    </span>
                </div>
            </div>
            <div class="header-actions">
                <div id="ws-badge" class="ws-badge ws-active">
                    <span class="pulse-dot-ws"></span>
                    <span id="ws-text">WEBSOCKET 20 FPS (STREAM AO VIVO ULTRA-RÁPIDO)</span>
                </div>
                <button id="btn-toggle-mitigation" class="btn-mitigation-toggle" onclick="toggleMitigation()">
                    ⚡ Mitigação Autônoma: DESATIVADA
                </button>
                <div class="live-badge">
                    <span>120 TPS CONTÍNUOS</span>
                </div>
            </div>
        </header>

        <!-- 1. Controle de Injeção de Cenários em Tempo Real -->
        <div class="deck">
            <div class="deck-title">Controle de Injeção de Cenários (Altere a física do sistema com 1 clique)</div>
            <div class="scenario-buttons">
                <button class="btn-scenario active" id="btn-nominal" onclick="setScenario('nominal')">
                    🟢 1. Operação Nominal
                    <span class="sub">45ms antifraude • Pool ~10% • Error Budget 100% Intacto</span>
                </button>
                <button class="btn-scenario" id="btn-drift" onclick="setScenario('drift')">
                    🟡 2. Injetar Drift Silencioso
                    <span class="sub">255ms antifraude • Pool sobe para 68% • SRE ainda em silêncio</span>
                </button>
                <button class="btn-scenario" id="btn-rupture" onclick="setScenario('rupture')">
                    🔴 3. Ruptura de Concorrência
                    <span class="sub">420ms antifraude • Pool estoura (100%) • Queima acelerada de Budget</span>
                </button>
                <button class="btn-scenario" id="btn-recover" onclick="setScenario('recover')">
                    🔄 4. Restaurar / Autocura
                    <span class="sub">Volta para 45ms nominais • Estabiliza Burn Rate</span>
                </button>
                <button class="btn-scenario" id="btn-hsm_saturation" onclick="setScenario('hsm_saturation')">
                    ⚡ 5. Gargalo de HSM / Cripto
                    <span class="sub">+120ms na validação EMV • Contenção de CPU • Fila no Gateway</span>
                </button>
                <button class="btn-scenario" id="btn-acquirer_flapping" onclick="setScenario('acquirer_flapping')">
                    🌪️ 6. Flapping na Adquirente
                    <span class="sub">35% erros 503 intermitentes • Tempestade de Retries</span>
                </button>
                <button class="btn-scenario" id="btn-network_jitter" onclick="setScenario('network_jitter')">
                    🌊 7. Jitter de Rede (P99 Outlier)
                    <span class="sub">10% com atraso de 1200ms • Saturação de conexões</span>
                </button>
            </div>
        </div>

        <!-- 2. Banner de Antecedência Operacional -->
        <div class="lead-banner">
            <div>
                <div class="lead-title">Antecedência Operacional do ARKHÉ SENTINEL sobre o Alarme SRE Clássico</div>
                <div style="font-size: 14px; color: #cbd5e1; margin-top: 4px;" id="lead-status-desc">
                    Aguardando convergência de sinais de trajetória...
                </div>
            </div>
            <div style="text-align: right;">
                <div class="lead-time-val" id="lead-time-counter">+0.0s</div>
                <span style="font-size: 11px; color: #93c5fd;">TEMPO DE ANTECEDÊNCIA GANHO</span>
            </div>
        </div>

        <!-- 3. PAINEL DO AGENTE ATUADOR AUTÔNOMO (CLOSED-LOOP REMEDIATION) -->
        <div class="mitigation-panel">
            <div class="mitigation-header">
                <div>
                    <span style="font-weight: 800; font-size: 14px; letter-spacing: 0.5px; color: #93c5fd;">
                        ⚡ AGENTE ATUADOR ARKHÉ (CLOSED-LOOP SELF-HEALING)
                    </span>
                    <span style="font-size: 12px; color: var(--text-muted); margin-left: 12px;">
                        Atuação em tempo real no minuto 0 do Drift, neutralizando o colapso antes do impacto no cliente
                    </span>
                </div>
                <span id="mitigation-status-badge" class="mit-badge" style="background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid #475569;">
                    STANDBY (AGUARDANDO SINAIS)
                </span>
            </div>

            <div class="mitigation-grid">
                <div class="mit-stat-box">
                    <div style="font-size: 11px; text-transform: uppercase; color: #93c5fd;">Ações Preventivas em Execução</div>
                    <div id="mitigation-action-desc" style="font-size: 13px; font-weight: 600; margin-top: 6px; color: #e2e8f0;">
                        Nenhuma ação necessária no momento.
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">
                        Capacidade do Pool: <strong id="mit-pool-cap" style="color: #60a5fa;">30 slots</strong> (HPA Adaptativo)
                    </div>
                </div>

                <div class="mit-stat-box">
                    <div style="font-size: 11px; text-transform: uppercase; color: #93c5fd;">Falhas 503/504 Evitadas</div>
                    <div id="mit-prevented-count" style="font-size: 26px; font-weight: 800; color: var(--green-glow); margin: 2px 0;">
                        0 falhas
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted);">
                        Zero clientes impactados por saturação
                    </div>
                </div>

                <div class="mit-stat-box">
                    <div style="font-size: 11px; text-transform: uppercase; color: #93c5fd;">Economia de Confiabilidade</div>
                    <div id="mit-downtime-avoided" style="font-size: 26px; font-weight: 800; color: #38bdf8; margin: 2px 0;">
                        19.5 min
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted);">
                        Tempo de indisponibilidade severa poupado
                    </div>
                </div>
            </div>
        </div>

        <!-- 4. GRAFO TOPOLÓGICO INTERATIVO DE SERVIÇOS (6 HOPS DA ARQUITETURA ARKHÉ) -->
        <div class="topology-deck">
            <div class="topology-header">
                <div>
                    <div style="font-weight: 800; font-size: 14px; letter-spacing: 0.5px; color: #f1f5f9; display: flex; align-items: center; gap: 8px;">
                        <span>🌐 GRAFO TOPOLÓGICO DE CONCORRÊNCIA E FLUXO (6 HOPS ARQUITETURAIS)</span>
                        <span class="status-badge badge-healthy" style="font-size: 10px; padding: 2px 8px;">DAG AO VIVO (20 FPS)</span>
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
                        Visualização e rastreamento topológico de propagação de gargalos, latências e física de filas de Little
                    </div>
                </div>
                <div class="topo-legend">
                    <span class="topo-leg-item"><span class="topo-indicator ind-healthy"></span> Nominal</span>
                    <span class="topo-leg-item"><span class="topo-indicator ind-warning"></span> Drift / Fila</span>
                    <span class="topo-leg-item"><span class="topo-indicator ind-critical"></span> Saturação</span>
                    <span class="topo-leg-item"><span class="topo-indicator ind-mitigated"></span> Auto-Cura Ativa</span>
                </div>
            </div>

            <!-- Fluxo Sequencial com 6 Nós Interativos e 5 Conectores com Partículas de Fluxo -->
            <div class="topo-flow-container">
                <!-- Hop 1: Gateway Ingestão -->
                <div class="topo-node node-healthy" id="node-gateway" onclick="selectTopoNode('gateway')">
                    <div class="topo-node-header">
                        <span class="node-step-tag">[1] INGESTÃO</span>
                        <span class="node-status-pill pill-healthy" id="pill-gateway">NOMINAL</span>
                    </div>
                    <div class="topo-node-title"><span>🌐</span> Gateway Ingestão</div>
                    <div class="topo-node-role">Envoy / API Ingress</div>
                    <div class="topo-node-metrics">
                        <span>Latência: <strong class="node-m-val" id="topo-lat-gateway">8.0 ms</strong></span>
                        <span>Carga: <strong class="node-m-val" id="topo-load-gateway">120 TPS</strong></span>
                    </div>
                </div>

                <!-- Conector 1 -> 2 -->
                <div class="topo-edge" id="edge-0">
                    <div class="edge-arrow"><span class="edge-flow-dot"></span></div>
                    <span class="edge-tps-badge" id="edge-tps-0">120 TPS ➔</span>
                </div>

                <!-- Hop 2: HSM & Limites -->
                <div class="topo-node node-healthy" id="node-hsm_limits" onclick="selectTopoNode('hsm_limits')">
                    <div class="topo-node-header">
                        <span class="node-step-tag">[2] SEGURANÇA</span>
                        <span class="node-status-pill pill-healthy" id="pill-hsm_limits">NOMINAL</span>
                    </div>
                    <div class="topo-node-title"><span>🔐</span> HSM & Limites</div>
                    <div class="topo-node-role">Cripto EMV & Cache</div>
                    <div class="topo-node-metrics">
                        <span>Latência: <strong class="node-m-val" id="topo-lat-hsm_limits">8.0 ms</strong></span>
                        <span>CPU: <strong class="node-m-val" id="topo-load-hsm_limits">Normal</strong></span>
                    </div>
                </div>

                <!-- Conector 2 -> 3 -->
                <div class="topo-edge" id="edge-1">
                    <div class="edge-arrow"><span class="edge-flow-dot"></span></div>
                    <span class="edge-tps-badge" id="edge-tps-1">120 TPS ➔</span>
                </div>

                <!-- Hop 3: Fila Little (Semáforo) -->
                <div class="topo-node node-healthy" id="node-semaphore" onclick="selectTopoNode('semaphore')">
                    <div class="topo-node-header">
                        <span class="node-step-tag">[3] CONCORRÊNCIA</span>
                        <span class="node-status-pill pill-healthy" id="pill-semaphore">NOMINAL</span>
                    </div>
                    <div class="topo-node-title"><span>⏳</span> Fila Little (Semáforo)</div>
                    <div class="topo-node-role">Portão Little: L = λW</div>
                    <div class="topo-node-metrics">
                        <span>Espera: <strong class="node-m-val" id="topo-lat-semaphore">0.0 ms</strong></span>
                        <span>Fila: <strong class="node-m-val" id="topo-load-semaphore">0 waiters</strong></span>
                    </div>
                </div>

                <!-- Conector 3 -> 4 -->
                <div class="topo-edge" id="edge-2">
                    <div class="edge-arrow"><span class="edge-flow-dot"></span></div>
                    <span class="edge-tps-badge" id="edge-tps-2">120 TPS ➔</span>
                </div>

                <!-- Hop 4: Pool Antifraude -->
                <div class="topo-node node-healthy" id="node-antifraud" onclick="selectTopoNode('antifraud')">
                    <div class="topo-node-header">
                        <span class="node-step-tag">[4] INTELIGÊNCIA</span>
                        <span class="node-status-pill pill-healthy" id="pill-antifraud">NOMINAL</span>
                    </div>
                    <div class="topo-node-title"><span>🧠</span> Pool Antifraude</div>
                    <div class="topo-node-role">Cluster IA / Scoring</div>
                    <div class="topo-node-metrics">
                        <span>Serviço: <strong class="node-m-val" id="topo-lat-antifraud">45.0 ms</strong></span>
                        <span>Uso: <strong class="node-m-val" id="topo-load-antifraud">3/30 slots</strong></span>
                    </div>
                </div>

                <!-- Conector 4 -> 5 -->
                <div class="topo-edge" id="edge-3">
                    <div class="edge-arrow"><span class="edge-flow-dot"></span></div>
                    <span class="edge-tps-badge" id="edge-tps-3">120 TPS ➔</span>
                </div>

                <!-- Hop 5: Adquirente Externa -->
                <div class="topo-node node-healthy" id="node-acquirer" onclick="selectTopoNode('acquirer')">
                    <div class="topo-node-header">
                        <span class="node-step-tag">[5] BANDEIRAS</span>
                        <span class="node-status-pill pill-healthy" id="pill-acquirer">NOMINAL</span>
                    </div>
                    <div class="topo-node-title"><span>🏛️</span> Adquirente Externa</div>
                    <div class="topo-node-role">Redes Cielo / Stone</div>
                    <div class="topo-node-metrics">
                        <span>Latência: <strong class="node-m-val" id="topo-lat-acquirer">35.0 ms</strong></span>
                        <span>Flap: <strong class="node-m-val" id="topo-load-acquirer">0%</strong></span>
                    </div>
                </div>

                <!-- Conector 5 -> 6 -->
                <div class="topo-edge" id="edge-4">
                    <div class="edge-arrow"><span class="edge-flow-dot"></span></div>
                    <span class="edge-tps-badge" id="edge-tps-4">120 TPS ➔</span>
                </div>

                <!-- Hop 6: Ledger Contábil -->
                <div class="topo-node node-healthy" id="node-ledger" onclick="selectTopoNode('ledger')">
                    <div class="topo-node-header">
                        <span class="node-step-tag">[6] ASSENTAMENTO</span>
                        <span class="node-status-pill pill-healthy" id="pill-ledger">NOMINAL</span>
                    </div>
                    <div class="topo-node-title"><span>📒</span> Ledger Contábil</div>
                    <div class="topo-node-role">Commit Distribuído ACID</div>
                    <div class="topo-node-metrics">
                        <span>Latência: <strong class="node-m-val" id="topo-lat-ledger">3.0 ms</strong></span>
                        <span>Status: <strong class="node-m-val" id="topo-load-ledger">100% ACID</strong></span>
                    </div>
                </div>
            </div>

            <!-- Barra de Auditoria / Inspeção de Nó Físico -->
            <div class="topo-inspector-bar">
                <div>
                    <strong style="color: #60a5fa;" id="inspector-node-title">ℹ️ Inspetor Topológico:</strong>
                    <span style="margin-left: 8px;" id="inspector-node-desc">Clique em qualquer nó do grafo para visualizar equações de fila, parâmetros operacionais e telemetria interna.</span>
                </div>
                <div style="font-family: monospace; font-size: 11px; color: #94a3b8;" id="inspector-node-formula">
                    Modelo de Rede: Jackson Network Aberta / FIFO M/M/c
                </div>
            </div>
        </div>

        <!-- 5. VISIBILIDADE DA TRAJETÓRIA ANTECIPADA & CONE DE INCERTEZA (FORWARD HORIZON PROJECTION) -->
        <div class="horizon-deck">
            <div class="horizon-header">
                <div>
                    <div style="font-weight: 800; font-size: 14px; letter-spacing: 0.5px; color: #f1f5f9; display: flex; align-items: center; gap: 8px;">
                        <span>📈 VISIBILIDADE DA TRAJETÓRIA ANTECIPADA (FORWARD HORIZON & CONE DE INCERTEZA)</span>
                        <span class="status-badge badge-healthy" style="font-size: 10px; padding: 2px 8px;">EXTRAPOLAÇÃO ESTOCÁSTICA T₀ ➔ T₊₅min</span>
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
                        Projeção matemática contínua da saturação de concorrência com cone de confiança de 95% e ponto de colapso predito
                    </div>
                </div>

                <div class="horizon-stats-row">
                    <div class="horizon-kpi-chip">
                        <span class="hz-kpi-lbl">Tempo até Colapso:</span>
                        <span class="hz-kpi-val" id="hz-collapse-val" style="color: var(--green-glow);">ESTÁVEL (∞)</span>
                    </div>
                    <div class="horizon-kpi-chip">
                        <span class="hz-kpi-lbl">Derivada (dρ/dt):</span>
                        <span class="hz-kpi-val" id="hz-drift-val" style="color: #60a5fa;">+0.00 /min</span>
                    </div>
                    <div class="horizon-kpi-chip">
                        <span class="hz-kpi-lbl">Estado da Trajetória:</span>
                        <span class="hz-kpi-val" id="hz-status-badge" style="color: var(--green-glow);">BACIA ESTÁVEL</span>
                    </div>
                </div>
            </div>

            <!-- Gráfico Panorâmico de Horizonte Futuro com Cone Shaded de 95% -->
            <div class="horizon-chart-box">
                <canvas id="chartForwardHorizon"></canvas>
            </div>

            <!-- Legenda da Projeção Estocástica -->
            <div class="horizon-legend">
                <span><span class="hz-legend-dot" style="background:#388bfd;"></span> <strong>Histórico Observado</strong> (-60s até T₀)</span>
                <span><span class="hz-legend-dot" style="background:#d29922;"></span> <strong>Projeção Mediana Inercial</strong> (T₀ até T₊₅min)</span>
                <span><span class="hz-legend-dot" style="background:rgba(218, 54, 51, 0.3); border:1px solid #da3633;"></span> <strong>Cone de Incerteza Estocástica 95%</strong></span>
                <span><span class="hz-legend-dot" style="background:#3fb950;"></span> <strong>Trajetória Mitigada (Closed-Loop)</strong></span>
                <span><span class="hz-legend-dot" style="background:#da3633;"></span> <strong>Limiar Crítico de Ruptura (ρ = 80%)</strong></span>
            </div>
        </div>

        <!-- 6. Governança SRE: SLA, SLI & Error Budget -->
        <div class="sre-deck">
            <div class="sre-deck-header">
                <div>
                    <span style="font-weight: 700; font-size: 14px; color: #f1f5f9;">GOVERNANÇA SRE: CONTRATOS DE SLA & ORÇAMENTO DE ERRO</span>
                    <span style="font-size: 12px; color: var(--text-muted); margin-left: 10px;">(Padrão Google SRE Book: Apenas falhas de infraestrutura consomem o orçamento)</span>
                </div>
                <div id="burn-rate-badge" class="burn-badge" style="background: rgba(35, 134, 54, 0.2); color: var(--green-glow); border: 1px solid var(--green);">
                    BURN RATE: 0.0x (NORMAL)
                </div>
            </div>

            <div class="sre-grid">
                <div class="sre-card">
                    <div class="sre-label">SLI de Disponibilidade Técnica</div>
                    <div class="sre-val" id="sli-avail" style="color: var(--green-glow);">100.0%</div>
                    <div style="font-size: 11px; color: var(--text-muted);">Meta Contratual SLA: <strong>99.90%</strong></div>
                </div>

                <div class="sre-card">
                    <div class="sre-label">SLI de Latência de Checkout</div>
                    <div class="sre-val" id="sli-latency" style="color: #60a5fa;">100.0%</div>
                    <div style="font-size: 11px; color: var(--text-muted);">Meta Contratual SLA: <strong>99.50%</strong> (<= 1.500ms)</div>
                </div>

                <div class="sre-card">
                    <div class="sre-label">Error Budget Restante</div>
                    <div class="sre-val" id="budget-remaining" style="color: var(--green-glow);">100.0%</div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" id="bar-budget" style="width: 100%; background: var(--green-glow);"></div>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px;" id="budget-fails-text">
                        0 falhas técnicas de 12.4 permitidas
                    </div>
                </div>

                <div class="sre-card">
                    <div class="sre-label">Velocidade de Queima (Burn Rate)</div>
                    <div class="sre-val" id="burn-rate-val" style="color: var(--green-glow);">0.0x</div>
                    <div style="font-size: 11px; color: var(--text-muted);" id="burn-rate-desc">
                        Orçamento seguro. Nenhuma queima ativa.
                    </div>
                </div>
            </div>
        </div>

        <!-- 5. Cards de KPIs: Física de Filas & Concorrência (Lei de Little) -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Sentinel Risk Score</div>
                <div class="kpi-metric" id="kpi-score" style="color: var(--green-glow);">0.0 / 100</div>
                <span class="status-badge badge-healthy" id="badge-sentinel-level">HEALTHY</span>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="bar-score" style="width: 10%; background: var(--green-glow);"></div>
                </div>
            </div>

            <div class="kpi-card">
                <div class="kpi-title">Ocupação do Pool Antifraude (Lei de Little)</div>
                <div class="kpi-metric" id="kpi-pool">0 / 30</div>
                <span style="font-size: 12px; color: var(--text-muted);" id="kpi-pool-sub">10.0% de ocupação</span>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="bar-pool" style="width: 10%; background: var(--arkhe-blue);"></div>
                </div>
            </div>

            <div class="kpi-card">
                <div class="kpi-title">Tráfego de Cartões Simultâneo</div>
                <div class="kpi-metric" id="kpi-traffic">0 tx</div>
                <span style="font-size: 12px; color: var(--text-muted);" id="kpi-traffic-sub">120 TPS nominais</span>
            </div>

            <div class="kpi-card">
                <div class="kpi-title">Latência P95 e Concorrência</div>
                <div class="kpi-metric" id="kpi-p95">0.0 ms</div>
                <span style="font-size: 12px; color: var(--text-muted);" id="kpi-waiters">0 conexões aguardando fila</span>
            </div>
        </div>

        <!-- 6. Gráficos em Tempo Real & Espaço de Fase 2D (Atrator de Lyapunov) -->
        <div class="charts-row">
            <div class="chart-box">
                <h4 style="margin: 0 0 10px 0; font-size: 13px;">Latência P95 Real vs Limiar SRE (1.500 ms)</h4>
                <canvas id="chartLatency" height="130"></canvas>
            </div>
            <div class="chart-box">
                <h4 style="margin: 0 0 10px 0; font-size: 13px;">Saturação do Pool Antifraude vs Capacidade</h4>
                <canvas id="chartPool" height="130"></canvas>
            </div>
            <div class="chart-box">
                <h4 style="margin: 0 0 10px 0; font-size: 13px;">Espaço de Fase 2D: Atrator de Colapso (ρ vs Wq/Ws)</h4>
                <canvas id="canvasPhaseSpace" width="340" height="130" style="background:#0b1120; border-radius:6px; border:1px solid #1f293d; width:100%; height:130px;"></canvas>
            </div>
        </div>

        <!-- 7. Painel Comparativo ARKHÉ vs SRE Clássico -->
        <div class="audit-grid">
            <div class="kpi-card" style="border-top: 3px solid var(--arkhe-blue);">
                <h3>ARKHÉ SENTINEL (Diagnóstico Antecipado)</h3>
                <p><strong>Status:</strong> <span class="status-badge badge-healthy" id="sentinel-det-badge">NOMINAL</span></p>
                <p><strong>Diagnóstico de Trajetória:</strong> <span id="sentinel-reason">Operação estável sem anomalias estruturais.</span></p>
            </div>

            <div class="kpi-card" style="border-top: 3px solid var(--red-glow);">
                <h3>Baseline SRE Tradicional (Prometheus / Datadog)</h3>
                <p><strong>Status:</strong> <span class="status-badge badge-healthy" id="sre-badge">EM SILÊNCIO (0 ALARMES)</span></p>
                <p><strong>Regra:</strong> P95 > 1.500ms ou 5xx > 5% sustentados.</p>
            </div>
        </div>

        <!-- 8. Visão Transacional: Câmara de Trajetórias (Live Waterfall Stream) -->
        <div class="waterfall-section">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                <div>
                    <h3 style="margin: 0; font-size: 16px;">CÂMARA DE TRAJETÓRIAS TRANSACIONAIS AO VIVO (WATERFALL STREAM)</h3>
                    <span style="font-size: 12px; color: var(--text-muted);">
                        Rastreio de cada salto individual: [1. Ingestão] → [2. Limites] → [3. Antifraude / Fila] → [4. Adquirente] → [5. Ledger]
                    </span>
                </div>
                <div style="font-size: 11px; color: var(--text-muted); display: flex; gap: 10px;">
                    <span><span style="color:#3b82f6;">■</span> Ingestão</span>
                    <span><span style="color:#06b6d4;">■</span> Limites</span>
                    <span><span style="color:#eab308;">■</span> Espera em Fila</span>
                    <span><span style="color:#10b981;">■</span> Antifraude</span>
                    <span><span style="color:#8b5cf6;">■</span> Adquirente</span>
                </div>
            </div>

            <table class="journey-table">
                <thead>
                    <tr>
                        <th style="width: 80px;">Hora</th>
                        <th style="width: 160px;">ID Transação</th>
                        <th style="width: 100px;">Valor</th>
                        <th style="width: 130px;">Status</th>
                        <th style="width: 180px;">Impacto no SLA</th>
                        <th style="width: 80px;">Total</th>
                        <th>Cascata Temporal dos 6 Estágios (Waterfall)</th>
                    </tr>
                </thead>
                <tbody id="journey-tbody">
                    <!-- Preenchido via streaming WebSocket a 20 FPS -->
                </tbody>
            </table>
        </div>

        <!-- 9. Linha do Tempo de Auditoria -->
        <div class="logs-box">
            <div style="font-size: 12px; text-transform: uppercase; color: var(--text-muted); margin-bottom: 10px;">
                Linha do Tempo de Auditoria (Eventos, Injeções e Ações de Mitigação)
            </div>
            <div id="logs-container">
                <!-- Preenchido dinamicamente -->
            </div>
        </div>
    </div>

    <script>
        // Inicialização dos Gráficos com Chart.js
        const maxPoints = 25;
        const labels = Array(maxPoints).fill('');
        
        const ctxLatency = document.getElementById('chartLatency').getContext('2d');
        const chartLatency = new Chart(ctxLatency, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'P95 Latência Real (ms)',
                        data: Array(maxPoints).fill(200),
                        borderColor: '#58a6ff',
                        backgroundColor: 'rgba(88, 166, 255, 0.1)',
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Alarme SRE Clássico (1.500 ms)',
                        data: Array(maxPoints).fill(1500),
                        borderColor: '#f85149',
                        borderDash: [5, 5],
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                animation: false,
                scales: { y: { beginAtZero: true, max: 2000 } }
            }
        });

        const ctxPool = document.getElementById('chartPool').getContext('2d');
        const chartPool = new Chart(ctxPool, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Conexões em Uso',
                        data: Array(maxPoints).fill(3),
                        borderColor: '#3fb950',
                        backgroundColor: 'rgba(63, 185, 80, 0.1)',
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Capacidade do Pool',
                        data: Array(maxPoints).fill(30),
                        borderColor: '#d29922',
                        borderDash: [5, 5],
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                animation: false,
                scales: { y: { beginAtZero: true, max: 65 } }
            }
        });

        // Chart.js: Projeção de Trajetória Antecipada com Cone de Incerteza 95%
        const horizonLabels = ['-60s', '-45s', '-30s', '-15s', 'T₀ (Agora)', '+30s', '+1m', '+1.5m', '+2m', '+3m', '+4m', '+5m'];
        const ctxHorizon = document.getElementById('chartForwardHorizon').getContext('2d');
        const chartHorizon = new Chart(ctxHorizon, {
            type: 'line',
            data: {
                labels: horizonLabels,
                datasets: [
                    {
                        label: 'Cone Superior 95%',
                        data: Array(horizonLabels.length).fill(null),
                        borderColor: 'transparent',
                        backgroundColor: 'transparent',
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: 'Cone de Incerteza Estocástica 95%',
                        data: Array(horizonLabels.length).fill(null),
                        borderColor: 'transparent',
                        backgroundColor: 'rgba(218, 54, 51, 0.18)',
                        pointRadius: 0,
                        fill: '-1'
                    },
                    {
                        label: 'Histórico Observado',
                        data: Array(horizonLabels.length).fill(null),
                        borderColor: '#388bfd',
                        backgroundColor: 'rgba(56, 139, 253, 0.2)',
                        borderWidth: 2.5,
                        pointRadius: 3,
                        pointBackgroundColor: '#388bfd',
                        fill: false,
                        tension: 0.2
                    },
                    {
                        label: 'Projeção Mediana Inercial',
                        data: Array(horizonLabels.length).fill(null),
                        borderColor: '#d29922',
                        borderWidth: 2.5,
                        borderDash: [5, 4],
                        pointRadius: 3,
                        pointBackgroundColor: '#d29922',
                        fill: false,
                        tension: 0.3
                    },
                    {
                        label: 'Trajetória com Mitigação Autônoma',
                        data: Array(horizonLabels.length).fill(null),
                        borderColor: '#3fb950',
                        borderWidth: 2.5,
                        borderDash: [4, 4],
                        pointRadius: 3,
                        pointBackgroundColor: '#3fb950',
                        fill: false,
                        tension: 0.3
                    },
                    {
                        label: 'Limiar de Ruptura (80%)',
                        data: Array(horizonLabels.length).fill(0.80),
                        borderColor: 'rgba(218, 54, 51, 0.7)',
                        borderWidth: 1.5,
                        borderDash: [4, 4],
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1.05,
                        grid: { color: 'rgba(255,255,255,0.06)' },
                        ticks: {
                            color: '#94a3b8',
                            callback: function(v) { return (v * 100).toFixed(0) + '%'; }
                        }
                    },
                    x: {
                        grid: { color: 'rgba(255,255,255,0.04)' },
                        ticks: { color: '#94a3b8' }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                if (ctx.raw === null || ctx.raw === undefined) return '';
                                return ctx.dataset.label + ': ' + (ctx.raw * 100).toFixed(1) + '%';
                            }
                        }
                    }
                }
            }
        });

        // Inspetor Interativo do Grafo Topológico
        const nodeDescriptions = {
            "gateway": {
                "title": "🌐 Hop 1: Gateway de Ingestão (Envoy / API Ingress)",
                "desc": "Ponto de entrada único HTTP/2 & gRPC. Executa buffer de requisições, terminação TLS e roteamento não-bloqueante para a malha interna.",
                "formula": "Taxa de Chegada: λ = 120 TPS nominais | Event Loop Lag < 1ms"
            },
            "hsm_limits": {
                "title": "🔐 Hop 2: Validação Criptográfica HSM & Limites de Cartão",
                "desc": "Descriptografia do Pin-Block e validação do CVC/CVV via Hardware Security Module (HSM). Em saturação, gera contenção severa de CPU criptográfica.",
                "formula": "Custo Cripto: T_crypto = 8ms + Contenção CPU HSM | Chaves EMV ZMK/PVK"
            },
            "semaphore": {
                "title": "⏳ Hop 3: Fila Little & Semáforo Físico de Concorrência",
                "desc": "Portão de admissão baseado na Lei de Little. Quando a demanda excede a capacidade do pool, retém conexões e gera fila física exponencial.",
                "formula": "Lei de Little: L_q = λ * W_q | Equação de Kingman: W_q ≈ (ρ / (1 - ρ)) * W_s"
            },
            "antifraud": {
                "title": "🧠 Hop 4: Pool de Inteligência Antifraude (Cluster IA)",
                "desc": "Execução de modelos preditivos de detecção de fraude e risco. O gatilho primário do colapso de Little ocorre quando sua latência de serviço sofre drift silencioso.",
                "formula": "Utilização: ρ = (λ * W_s) / C | Demanda Little: L(t) = λ(t) * W_s(t)"
            },
            "acquirer": {
                "title": "🏛️ Hop 5: Adquirente Externa & Redes de Bandeiras (Cielo / Stone)",
                "desc": "Conexão de rede externa ISO 8583. Sujeita a flapping intermitente (503s), instabilidade de jitter P99 e tempestades de retries descontroladas.",
                "formula": "Amplificação: R_retry = Tentativas / Txs Únicas | Jitter P99 > 1200ms"
            },
            "ledger": {
                "title": "📒 Hop 6: Ledger Contábil Distribuído (Double-Entry Commit)",
                "desc": "Efetivação de crédito/débito e commit distribuído idempotente. Garante consistência financeira estrita sob qualquer condição de tráfego.",
                "formula": "Idempotência Estrita UUIDv4 | Garantia ACID 100%"
            }
        };

        function selectTopoNode(nodeId) {
            document.querySelectorAll('.topo-node').forEach(n => n.classList.remove('active-selected'));
            const nodeEl = document.getElementById('node-' + nodeId);
            if (nodeEl) nodeEl.classList.add('active-selected');

            const info = nodeDescriptions[nodeId];
            if (info) {
                document.getElementById('inspector-node-title').textContent = info.title;
                document.getElementById('inspector-node-desc').textContent = info.desc;
                document.getElementById('inspector-node-formula').textContent = info.formula;
            }
        }

        // Espaço de Fase 2D (Atrator de Lyapunov & Teoria de Filas)
        const phaseCanvas = document.getElementById('canvasPhaseSpace');
        const phaseCtx = phaseCanvas.getContext('2d');
        const phaseTrail = [];

        function drawPhaseSpace(rho, wq_ws, mitigationActive) {
            const w = phaseCanvas.width;
            const h = phaseCanvas.height;
            phaseCtx.clearRect(0, 0, w, h);

            const toX = (val) => Math.max(10, Math.min(w - 10, val * (w - 20) + 10));
            const toY = (val) => Math.max(10, Math.min(h - 10, h - (val / 2.0) * (h - 20) - 10));

            // Bacia de Estabilidade (Verde: rho <= 0.50, wq_ws <= 0.25)
            phaseCtx.fillStyle = 'rgba(35, 134, 54, 0.18)';
            phaseCtx.fillRect(10, toY(0.25), toX(0.50) - 10, h - 10 - toY(0.25));

            // Zona de Drift (Amarelo: 0.50 < rho <= 0.80, wq_ws <= 0.60)
            phaseCtx.fillStyle = 'rgba(210, 153, 34, 0.15)';
            phaseCtx.fillRect(toX(0.50), toY(0.60), toX(0.80) - toX(0.50), h - 10 - toY(0.60));

            // Atrator de Colapso (Vermelho: rho > 0.80 ou wq_ws > 0.60)
            phaseCtx.fillStyle = 'rgba(218, 54, 51, 0.15)';
            phaseCtx.fillRect(toX(0.80), 10, w - 10 - toX(0.80), h - 20);

            // Rótulos de Zonas
            phaseCtx.font = '10px sans-serif';
            phaseCtx.fillStyle = '#3fb950';
            phaseCtx.fillText('Bacia Estável', 16, h - 14);

            phaseCtx.fillStyle = '#d29922';
            phaseCtx.fillText('Drift', toX(0.53), h - 14);

            phaseCtx.fillStyle = '#f85149';
            phaseCtx.fillText('Atrator Ruptura', toX(0.82), 22);

            // Trilha de Pontos Históricos
            phaseTrail.push({ x: toX(rho), y: toY(wq_ws) });
            if (phaseTrail.length > 35) phaseTrail.shift();

            phaseCtx.beginPath();
            phaseCtx.strokeStyle = 'rgba(88, 166, 255, 0.4)';
            phaseCtx.lineWidth = 2;
            for (let i = 0; i < phaseTrail.length; i++) {
                const pt = phaseTrail[i];
                if (i === 0) phaseCtx.moveTo(pt.x, pt.y);
                else phaseCtx.lineTo(pt.x, pt.y);
            }
            phaseCtx.stroke();

            // Ponto Atual
            const curX = toX(rho);
            const curY = toY(wq_ws);
            phaseCtx.beginPath();
            phaseCtx.arc(curX, curY, 6, 0, Math.PI * 2);
            phaseCtx.fillStyle = rho > 0.8 ? '#f85149' : (rho > 0.5 ? '#d29922' : '#38bdf8');
            phaseCtx.fill();
            phaseCtx.strokeStyle = '#ffffff';
            phaseCtx.lineWidth = 1.5;
            phaseCtx.stroke();

            // Vetor de Contramedida (Força de Auto-Cura ARKHÉ)
            if (mitigationActive && rho > 0.35) {
                phaseCtx.beginPath();
                phaseCtx.moveTo(curX, curY);
                const targetX = toX(0.12);
                const targetY = toY(0.02);
                phaseCtx.lineTo(targetX, targetY);
                phaseCtx.strokeStyle = '#22c55e';
                phaseCtx.lineWidth = 2;
                phaseCtx.setLineDash([4, 4]);
                phaseCtx.stroke();
                phaseCtx.setLineDash([]);
                phaseCtx.fillStyle = '#22c55e';
                phaseCtx.fillText('⚡ Vetor de Auto-Cura', targetX + 4, targetY + 12);
            }
        }

        // --- GESTÃO DE WEBSOCKET BIDIRECIONAL COM FALLBACK AUTOMÁTICO ---
        let socket = null;
        let chartCounter = 0;
        let lastRenderedJourneyId = null;

        function connectWebSocket() {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws/telemetry`;
            
            try {
                socket = new WebSocket(wsUrl);
                
                socket.onopen = () => {
                    const badge = document.getElementById('ws-badge');
                    badge.className = 'ws-badge ws-active';
                    document.getElementById('ws-text').textContent = 'WEBSOCKET 20 FPS (STREAM AO VIVO)';
                };

                socket.onmessage = (event) => {
                    try {
                        const d = JSON.parse(event.data);
                        renderTelemetryFrame(d);
                    } catch (e) {
                        console.error('Erro ao processar frame WS:', e);
                    }
                };

                socket.onclose = () => {
                    const badge = document.getElementById('ws-badge');
                    badge.className = 'ws-badge ws-polling';
                    document.getElementById('ws-text').textContent = 'RECONECTANDO WS (MODO HTTP)...';
                    setTimeout(connectWebSocket, 1500);
                };

                socket.onerror = () => {
                    if (socket) socket.close();
                };
            } catch (e) {
                console.error('Falha ao abrir WebSocket:', e);
                setTimeout(connectWebSocket, 2000);
            }
        }

        async function toggleMitigation() {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send('toggle_mitigation');
            } else {
                try {
                    await fetch('/admin/mitigation/toggle', { method: 'POST' });
                } catch (e) {
                    console.error('Falha ao alternar mitigação:', e);
                }
            }
        }

        function updateMitigationButton(enabled) {
            const btn = document.getElementById('btn-toggle-mitigation');
            if (enabled) {
                btn.className = 'btn-mitigation-toggle enabled';
                btn.innerHTML = '⚡ Mitigação Autônoma: ATIVADA';
            } else {
                btn.className = 'btn-mitigation-toggle';
                btn.innerHTML = '⚡ Mitigação Autônoma: DESATIVADA';
            }
        }

        async function setScenario(name) {
            document.querySelectorAll('.btn-scenario').forEach(b => b.classList.remove('active'));
            const btn = document.getElementById('btn-' + name);
            if (btn) btn.classList.add('active');
            
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send('scenario:' + name);
            } else {
                try {
                    await fetch('/admin/chaos/scenario/' + name, { method: 'POST' });
                } catch (e) {
                    console.error('Falha ao acionar cenário:', e);
                }
            }
        }

        // Renderizador de Frame de Alta Frequência (Executado a 20 FPS)
        function renderTelemetryFrame(d) {
            // 1. Botão Ativo & Toggle Mitigação
            const sc = d.scenario.id;
            document.querySelectorAll('.btn-scenario').forEach(b => b.classList.remove('active'));
            const curBtn = document.getElementById('btn-' + sc);
            if (curBtn) curBtn.classList.add('active');

            updateMitigationButton(d.mitigation.enabled);

            // 2. Painel do Agente de Mitigação Autônoma
            const mitBadge = document.getElementById('mitigation-status-badge');
            const mitDesc = document.getElementById('mitigation-action-desc');
            const mitPoolCap = document.getElementById('mit-pool-cap');
            const mitPrevented = document.getElementById('mit-prevented-count');
            const mitDowntime = document.getElementById('mit-downtime-avoided');

            mitPoolCap.textContent = d.mitigation.pool_capacity + ' slots';
            mitPrevented.textContent = d.mitigation.prevented_failures + ' falhas';
            mitDowntime.textContent = d.mitigation.downtime_avoided_min.toFixed(1) + ' min';

            if (d.mitigation.active) {
                mitBadge.className = 'mit-badge';
                mitBadge.style.background = 'rgba(34, 197, 94, 0.25)';
                mitBadge.style.color = '#4ade80';
                mitBadge.style.border = '1px solid #22c55e';
                mitBadge.textContent = '⚡ ATUAÇÃO ATIVA (INCIDENTE NEUTRALIZADO)';
                mitDesc.innerHTML = '<strong>Ações Aplicadas:</strong> Predictive HPA (Pool 60 slots) + Fast-Path Antifraude (12ms) + Throttling de Retries';
            } else if (d.mitigation.enabled) {
                mitBadge.className = 'mit-badge';
                mitBadge.style.background = 'rgba(56, 189, 248, 0.2)';
                mitBadge.style.color = '#38bdf8';
                mitBadge.style.border = '1px solid #0284c7';
                mitBadge.textContent = 'STANDBY (MODO SENTINEL ARMADO)';
                mitDesc.textContent = 'Monitorando derivadas de Little (d_rho/dt). Atuação armada para o minuto 0.';
            } else {
                mitBadge.className = 'mit-badge';
                mitBadge.style.background = 'rgba(148, 163, 184, 0.2)';
                mitBadge.style.color = '#cbd5e1';
                mitBadge.style.border = '1px solid #475569';
                mitBadge.textContent = 'DESATIVADO (SISTEMA EM MODO PASSIVO)';
                mitDesc.textContent = 'Mitigação autônoma desativada. O sistema sofrerá impacto total de incidentes.';
            }

            // 3. Governança SRE (Error Budget & SLIs)
            const gov = d.sre_governance;
            const sliAvailEl = document.getElementById('sli-avail');
            sliAvailEl.textContent = gov.current_sli_availability_pct.toFixed(2) + '%';
            sliAvailEl.style.color = gov.current_sli_availability_pct >= 99.90 ? 'var(--green-glow)' : 'var(--red-glow)';

            document.getElementById('sli-latency').textContent = gov.current_sli_latency_pct.toFixed(2) + '%';
            
            const budgetRemEl = document.getElementById('budget-remaining');
            const barBudget = document.getElementById('bar-budget');
            budgetRemEl.textContent = gov.error_budget_remaining_pct.toFixed(1) + '%';
            barBudget.style.width = gov.error_budget_remaining_pct + '%';

            if (gov.error_budget_remaining_pct > 70) {
                budgetRemEl.style.color = 'var(--green-glow)';
                barBudget.style.background = 'var(--green-glow)';
            } else if (gov.error_budget_remaining_pct > 30) {
                budgetRemEl.style.color = 'var(--yellow)';
                barBudget.style.background = 'var(--yellow)';
            } else {
                budgetRemEl.style.color = 'var(--red-glow)';
                barBudget.style.background = 'var(--red-glow)';
            }

            document.getElementById('budget-fails-text').textContent = 
                `${gov.technical_errors_count} falhas técnicas de ${gov.allowed_errors_count} permitidas`;

            const burnRateVal = document.getElementById('burn-rate-val');
            burnRateVal.textContent = gov.burn_rate.toFixed(1) + 'x';
            const burnBadge = document.getElementById('burn-rate-badge');
            burnBadge.textContent = 'BURN RATE: ' + gov.burn_rate_status;

            if (gov.burn_rate <= 1.0) {
                burnRateVal.style.color = 'var(--green-glow)';
                burnBadge.style.background = 'rgba(35, 134, 54, 0.2)';
                burnBadge.style.color = 'var(--green-glow)';
                burnBadge.style.borderColor = 'var(--green)';
                document.getElementById('burn-rate-desc').textContent = 'Orçamento seguro. Nenhuma queima acelerada.';
            } else if (gov.burn_rate < 14.4) {
                burnRateVal.style.color = 'var(--yellow)';
                burnBadge.style.background = 'rgba(210, 153, 34, 0.2)';
                burnBadge.style.color = 'var(--yellow)';
                burnBadge.style.borderColor = 'var(--yellow)';
                document.getElementById('burn-rate-desc').textContent = 'Consumo acima do normal. Monitorando drift.';
            } else {
                burnRateVal.style.color = 'var(--red-glow)';
                burnBadge.style.background = 'rgba(218, 54, 51, 0.2)';
                burnBadge.style.color = 'var(--red-glow)';
                burnBadge.style.borderColor = 'var(--red)';
                document.getElementById('burn-rate-desc').textContent = 'ALERTA SRE: Esgotamento acelerado do contrato!';
            }

            // 4. Banner de Antecedência
            const leadSec = d.sentinel.lead_time_seconds;
            if (leadSec > 0 && !gov.traditional_alert_triggered) {
                document.getElementById('lead-time-counter').textContent = `+${leadSec.toFixed(1)}s (+${d.sentinel.lead_time_minutes} min)`;
                document.getElementById('lead-status-desc').textContent = 'O ARKHÉ SENTINEL detectou a anomalia estrutural preventivamente! O alarme SRE tradicional ainda não percebeu.';
            } else if (gov.traditional_alert_triggered) {
                document.getElementById('lead-status-desc').textContent = 'O alarme SRE clássico finalmente disparou após quebra do contrato! Antecedência comprovada.';
            } else {
                document.getElementById('lead-time-counter').textContent = '+0.0s';
                document.getElementById('lead-status-desc').textContent = 'Sistema operando normalmente. Injete uma anomalia para testar.';
            }

            // 5. KPIs Físicos (Lei de Little)
            const score = d.sentinel.score;
            const scoreEl = document.getElementById('kpi-score');
            const badgeEl = document.getElementById('badge-sentinel-level');
            const barScore = document.getElementById('bar-score');

            scoreEl.textContent = score.toFixed(1) + ' / 100';
            badgeEl.textContent = d.sentinel.level.toUpperCase();
            barScore.style.width = Math.min(100, score) + '%';

            if (score < 50) {
                scoreEl.style.color = 'var(--green-glow)';
                badgeEl.className = 'status-badge badge-healthy';
                barScore.style.background = 'var(--green-glow)';
            } else if (score < 75) {
                scoreEl.style.color = 'var(--yellow)';
                badgeEl.className = 'status-badge badge-warning';
                barScore.style.background = 'var(--yellow)';
            } else {
                scoreEl.style.color = 'var(--red-glow)';
                badgeEl.className = 'status-badge badge-danger';
                barScore.style.background = 'var(--red-glow)';
            }

            const used = d.telemetry.resources.antifraud_pool_in_use;
            const cap = d.telemetry.resources.antifraud_pool_capacity;
            const pct = (used / cap) * 100;
            document.getElementById('kpi-pool').textContent = `${used} / ${cap}`;
            document.getElementById('kpi-pool-sub').textContent = `${pct.toFixed(1)}% de ocupação`;
            const barPool = document.getElementById('bar-pool');
            barPool.style.width = pct + '%';
            barPool.style.background = pct > 80 ? 'var(--red-glow)' : (pct > 50 ? 'var(--yellow)' : 'var(--arkhe-blue)');

            document.getElementById('kpi-traffic').textContent = `${d.telemetry.traffic.unique_transactions_total} tx`;
            document.getElementById('kpi-traffic-sub').textContent = `${d.telemetry.traffic.attempts_total} tentativas (R_retry: ${d.telemetry.traffic.retry_amplification_ratio})`;

            document.getElementById('kpi-p95').textContent = `${d.telemetry.latency_ms.p95.toFixed(1)} ms`;
            document.getElementById('kpi-waiters').textContent = `${d.telemetry.resources.antifraud_waiters_count} conexões em fila física`;

            // 6. Comparação ARKHÉ vs SRE Clássico
            const detBadge = document.getElementById('sentinel-det-badge');
            if (d.sentinel.triggered) {
                detBadge.className = 'status-badge badge-warning';
                detBadge.textContent = 'ANOMALIA DETECTADA (ANTECIPADO)';
                document.getElementById('sentinel-reason').textContent = d.sentinel.trigger_reason;
            } else {
                detBadge.className = 'status-badge badge-healthy';
                detBadge.textContent = 'NOMINAL';
                document.getElementById('sentinel-reason').textContent = 'Operação estável sem anomalias estruturais.';
            }

            const sreBadge = document.getElementById('sre-badge');
            if (gov.traditional_alert_triggered) {
                sreBadge.className = 'status-badge badge-danger';
                sreBadge.textContent = 'ALARME SRE DISPARADO (PÓS-IMPACTO)';
            } else {
                sreBadge.className = 'status-badge badge-healthy';
                sreBadge.textContent = 'EM SILÊNCIO (0 ALARMES)';
            }

            // 7. Atualização do Grafo Topológico Interativo (6 Hops)
            if (d.topology && d.topology.nodes) {
                d.topology.nodes.forEach(n => {
                    const nodeEl = document.getElementById('node-' + n.id);
                    const pillEl = document.getElementById('pill-' + n.id);
                    const latEl = document.getElementById('topo-lat-' + n.id);
                    const loadEl = document.getElementById('topo-load-' + n.id);

                    if (nodeEl && pillEl && latEl && loadEl) {
                        latEl.textContent = n.latency_ms.toFixed(1) + ' ms';
                        loadEl.textContent = n.load;

                        let borderClass = 'node-healthy';
                        let pillClass = 'pill-healthy';
                        let pillText = 'NOMINAL';

                        if (n.status === 'critical') {
                            borderClass = 'node-critical';
                            pillClass = 'pill-critical';
                            pillText = 'SATURADO';
                        } else if (n.status === 'warning') {
                            borderClass = 'node-warning';
                            pillClass = 'pill-warning';
                            pillText = 'DRIFT / FILA';
                        } else if (n.status === 'mitigated') {
                            borderClass = 'node-mitigated';
                            pillClass = 'pill-mitigated';
                            pillText = 'AUTO-CURA';
                        }

                        const isSel = nodeEl.classList.contains('active-selected');
                        nodeEl.className = 'topo-node ' + borderClass + (isSel ? ' active-selected' : '');
                        pillEl.className = 'node-status-pill ' + pillClass;
                        pillEl.textContent = pillText;
                    }
                });

                if (d.topology.edges) {
                    d.topology.edges.forEach((e, idx) => {
                        const edgeEl = document.getElementById('edge-' + idx);
                        const tpsEl = document.getElementById('edge-tps-' + idx);
                        if (edgeEl && tpsEl) {
                            tpsEl.textContent = e.tps + ' TPS ➔';
                            edgeEl.className = 'topo-edge ' + (e.status === 'congested' ? 'edge-congested' : (e.status === 'degraded' ? 'edge-degraded' : ''));
                        }
                    });
                }
            }

            // 8. Atualização da Visibilidade da Trajetória Antecipada (Forward Horizon & Cone)
            if (d.projection) {
                const proj = d.projection;
                const colValEl = document.getElementById('hz-collapse-val');
                const driftValEl = document.getElementById('hz-drift-val');
                const statBadgeEl = document.getElementById('hz-status-badge');

                if (colValEl && driftValEl && statBadgeEl) {
                    colValEl.textContent = proj.time_to_collapse_display;
                    driftValEl.textContent = (proj.d_rho_dt_per_min >= 0 ? '+' : '') + proj.d_rho_dt_per_min.toFixed(2) + ' /min';

                    if (proj.collapse_status === 'CRITICAL') {
                        colValEl.style.color = 'var(--red-glow)';
                        statBadgeEl.textContent = 'RUPTURA IMINENTE';
                        statBadgeEl.style.color = 'var(--red-glow)';
                    } else if (proj.collapse_status === 'WARNING') {
                        colValEl.style.color = 'var(--yellow)';
                        statBadgeEl.textContent = 'DERIVA ACELERADA';
                        statBadgeEl.style.color = 'var(--yellow)';
                    } else {
                        colValEl.style.color = 'var(--green-glow)';
                        statBadgeEl.textContent = 'BACIA ESTÁVEL';
                        statBadgeEl.style.color = 'var(--green-glow)';
                    }
                }

                // Amostra dados no gráfico de horizonte a cada 10 frames (~500ms a 20 FPS para estabilidade e fluidez)
                if (chartCounter % 10 === 0) {
                    const past = proj.past_trajectory || [];
                    const curRho = proj.current_rho;
                    const pLen = past.length;

                    const p1 = pLen >= 15 ? past[pLen - 15].rho : (pLen >= 1 ? past[0].rho : curRho);
                    const p2 = pLen >= 10 ? past[pLen - 10].rho : (pLen >= 1 ? past[0].rho : curRho);
                    const p3 = pLen >= 6 ? past[pLen - 6].rho : (pLen >= 1 ? past[0].rho : curRho);
                    const p4 = pLen >= 3 ? past[pLen - 3].rho : curRho;

                    const histData = [p1, p2, p3, p4, curRho, null, null, null, null, null, null, null];
                    chartHorizon.data.datasets[2].data = histData;

                    const fut = proj.horizon_points || [];
                    if (fut.length >= 8) {
                        const coneUpper = [null, null, null, null, curRho, fut[1].rho_upper, fut[2].rho_upper, fut[3].rho_upper, fut[4].rho_upper, fut[5].rho_upper, fut[6].rho_upper, fut[7].rho_upper];
                        const coneLower = [null, null, null, null, curRho, fut[1].rho_lower, fut[2].rho_lower, fut[3].rho_lower, fut[4].rho_lower, fut[5].rho_lower, fut[6].rho_lower, fut[7].rho_lower];
                        const projMedian = [null, null, null, null, curRho, fut[1].rho_expected, fut[2].rho_expected, fut[3].rho_expected, fut[4].rho_expected, fut[5].rho_expected, fut[6].rho_expected, fut[7].rho_expected];
                        const projMit = [null, null, null, null, curRho, fut[1].rho_mitigated, fut[2].rho_mitigated, fut[3].rho_mitigated, fut[4].rho_mitigated, fut[5].rho_mitigated, fut[6].rho_mitigated, fut[7].rho_mitigated];

                        chartHorizon.data.datasets[0].data = coneUpper;
                        chartHorizon.data.datasets[1].data = coneLower;
                        chartHorizon.data.datasets[3].data = projMedian;
                        chartHorizon.data.datasets[4].data = projMit;
                    }
                    chartHorizon.update();
                }
            }

            // 7. Amostragem de Gráficos (A cada 10 frames = 500ms a 20 FPS para estabilidade visual)
            chartCounter++;
            if (chartCounter % 10 === 0) {
                chartLatency.data.datasets[0].data.shift();
                chartLatency.data.datasets[0].data.push(d.telemetry.latency_ms.p95);
                chartLatency.update();

                chartPool.data.datasets[0].data.shift();
                chartPool.data.datasets[0].data.push(used);
                chartPool.data.datasets[1].data = Array(maxPoints).fill(cap);
                chartPool.data.datasets[0].borderColor = used > (cap * 0.8) ? '#f85149' : (used > (cap * 0.5) ? '#d29922' : '#3fb950');
                chartPool.update();
            }

            // 8. Espaço de Fase 2D a 20 FPS (Movimento Suave de Lyapunov)
            const rho = d.telemetry.resources.antifraud_pool_utilization_ratio;
            const wq_ws = d.telemetry.queueing.wq_ws_ratio;
            drawPhaseSpace(rho, wq_ws, d.mitigation.active);

            // 9. Trajetórias Transacionais (Waterfall Table)
            const journeys = d.recent_journeys || [];
            if (journeys.length > 0 && journeys[0].tx_id !== lastRenderedJourneyId) {
                lastRenderedJourneyId = journeys[0].tx_id;
                const tbody = document.getElementById('journey-tbody');
                tbody.innerHTML = '';
                
                journeys.forEach(j => {
                    const tr = document.createElement('tr');
                    tr.className = 'journey-row';

                    let pillClass = 'pill-authorized';
                    let slaBadge = '<span style="color:var(--green-glow);">🟢 Neutro (SLA Preservado)</span>';
                    
                    if (j.status === 'TIMEOUT_504' || j.status === 'POOL_SATURATED_503') {
                        pillClass = 'pill-timeout';
                        slaBadge = '<span style="color:var(--red-glow); font-weight:bold;">🔴 Queimou Budget (-1)</span>';
                    } else if (j.status.startsWith('DECLINED')) {
                        pillClass = 'pill-business';
                        slaBadge = '<span style="color:#93c5fd;">🔵 Regra de Negócio (Preservado)</span>';
                    }

                    const st = j.stages;
                    const maxScale = Math.max(250.0, j.total_ms);
                    const pIngest = Math.max(1, (st.ingest_ms / maxScale) * 100);
                    const pLimits = Math.max(1, (st.limits_ms / maxScale) * 100);
                    const pQueue = (st.antifraud_queue_ms / maxScale) * 100;
                    const pAntifraud = Math.max(1, (st.antifraud_service_ms / maxScale) * 100);
                    const pAuth = (st.authorizer_ms / maxScale) * 100;
                    const pLedger = (st.ledger_ms / maxScale) * 100;

                    const isFailing = j.status === 'TIMEOUT_504' || j.status === 'POOL_SATURATED_503';
                    const afColorClass = st.antifraud_service_ms > 200 ? 'background: #eab308;' : 'background: #10b981;';

                    tr.innerHTML = `
                        <td style="color:var(--text-muted); font-family:monospace;">${j.timestamp}</td>
                        <td style="font-family:monospace; font-weight:600;">${j.tx_id.substring(0, 14)}...</td>
                        <td>R$ ${j.amount_brl.toFixed(2)}</td>
                        <td><span class="status-pill ${pillClass}">${j.status}</span></td>
                        <td>${slaBadge}</td>
                        <td style="font-weight:700;">${j.total_ms}ms</td>
                        <td>
                            <div class="waterfall-track" title="Ingest: ${st.ingest_ms}ms | Limites: ${st.limits_ms}ms | Fila: ${st.antifraud_queue_ms}ms | Antifraude: ${st.antifraud_service_ms}ms | Adquirente: ${st.authorizer_ms}ms">
                                <div class="w-stage w-ingest" style="width: ${pIngest}%"></div>
                                <div class="w-stage w-limits" style="width: ${pLimits}%"></div>
                                ${pQueue > 0.5 ? `<div class="w-stage w-queue ${isFailing ? 'w-failed':''}" style="width: ${pQueue}%">${st.antifraud_queue_ms > 50 ? st.antifraud_queue_ms + 'ms' : ''}</div>` : ''}
                                <div class="w-stage" style="width: ${pAntifraud}%; ${afColorClass}">${st.antifraud_service_ms > 50 ? st.antifraud_service_ms + 'ms' : ''}</div>
                                ${pAuth > 0.5 ? `<div class="w-stage w-authorizer" style="width: ${pAuth}%">${st.authorizer_ms}ms</div>` : ''}
                                ${pLedger > 0.5 ? `<div class="w-stage w-ledger" style="width: ${pLedger}%"></div>` : ''}
                            </div>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }

            // 10. Logs
            const logCont = document.getElementById('logs-container');
            logCont.innerHTML = '';
            (d.event_logs || []).slice(0, 8).forEach(l => {
                const div = document.createElement('div');
                div.className = 'log-item';
                div.innerHTML = `<span class="log-time">[${l.timestamp}]</span> <span>${l.message}</span>`;
                logCont.appendChild(div);
            });
        }

        // Fallback HTTP se WebSocket estiver desconectado
        async function fallbackHttpPoll() {
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                try {
                    const res = await fetch('/telemetry/live');
                    if (res.ok) {
                        const d = await res.json();
                        renderTelemetryFrame(d);
                    }
                } catch (e) {}
            }
        }

        // Inicia conexão WebSocket em tempo real e fallback timer
        connectWebSocket();
        setInterval(fallbackHttpPoll, 1000);
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)
