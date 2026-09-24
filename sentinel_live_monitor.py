from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os
import sys
import time
from typing import List, Optional

# Configura encoding UTF-8 no console Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Adiciona o Core do Sentinel ao path de execução
SENTINEL_CORE_PATH = os.getenv("SENTINEL_CORE_PATH", r"C:\Users\anonimo\Downloads\arkhe-sentinel-trajectory-core-main")
if SENTINEL_CORE_PATH not in sys.path:
    sys.path.insert(0, SENTINEL_CORE_PATH)

import httpx
from contracts.models import (
    GroundTruth,
    JourneyEvent,
    JourneyStep,
    Scenario,
    SimulationBundle,
    TelemetryWindow,
)
from trajectory_core.analysis import analyze
from report_agent.analyst import create_report

LAB_URL = os.getenv("LAB_URL", "http://localhost:8080")
CORE_URL = os.getenv("CORE_URL", "http://localhost:8000")
TELEMETRY_ENDPOINT = f"{LAB_URL}/telemetry/as_of"
CHAOS_ENDPOINT = f"{LAB_URL}/admin/chaos"

class SentinelLiveCollector:
    """
    Ponte de Monitoramento Ativo entre o Ambiente de Validação de Cartões (8080)
    e o Motor de Inteligência de Trajetória ARKHÉ SENTINEL (8000).
    """
    def __init__(self, window_duration_sec: float = 3.0):
        self.window_duration = window_duration_sec
        self.telemetry_history: List[dict] = []
        self.windows: List[TelemetryWindow] = []
        self.events: List[JourneyEvent] = []
        self.current_minute = 0
        self.run_id = f"live_run_{int(time.time())}"
        self.t_sentinel_alert: Optional[float] = None
        self.t_sre_alert: Optional[float] = None
        self.last_report = None

    def _convert_snapshot_to_window(self, minute: int, snap: dict, prev_snap: dict | None) -> TelemetryWindow:
        p95 = snap["latency_ms"]["p95"]
        attempts = snap["traffic"]["attempts_total"]
        uniques = snap["traffic"]["unique_transactions_total"]
        timeouts = snap["outcomes"]["technical_timeouts"]
        exhaustions = snap["outcomes"]["pool_exhaustion_errors"]
        approved = snap["outcomes"]["approved"]
        waiters = snap["resources"]["antifraud_waiters_count"]
        
        # Variações no intervalo
        if prev_snap:
            d_attempts = attempts - prev_snap["traffic"]["attempts_total"]
            d_uniques = uniques - prev_snap["traffic"]["unique_transactions_total"]
            d_timeouts = (timeouts + exhaustions) - (prev_snap["outcomes"]["technical_timeouts"] + prev_snap["outcomes"]["pool_exhaustion_errors"])
            d_approved = approved - prev_snap["outcomes"]["approved"]
            
            retry_rate = max(0.0, min(1.0, 1.0 - (d_uniques / max(1, d_attempts))))
            timeout_rate = max(0.0, min(1.0, d_timeouts / max(1, d_attempts)))
            approval_rate = max(0.0, min(1.0, d_approved / max(1, d_attempts)))
        else:
            retry_rate = 0.0
            timeout_rate = 0.0
            approval_rate = 1.0

        return TelemetryWindow(
            minute=minute,
            p95_latency_ms=max(10.0, p95),
            retry_rate=round(retry_rate, 4),
            queue_lag=waiters * 50, # Escala de lag de fila
            approval_rate=round(approval_rate, 4),
            timeout_rate=round(timeout_rate, 4)
        )

    def _generate_synthetic_journey_events(self, minute: int, snap: dict) -> List[JourneyEvent]:
        now = datetime.now(timezone.utc)
        p95 = snap["latency_ms"]["p95"]
        is_failing = snap["outcomes"]["technical_timeouts"] > 0 or snap["resources"]["antifraud_pool_utilization_ratio"] > 0.90
        is_degraded = snap["resources"]["antifraud_pool_utilization_ratio"] > 0.50
        
        status = "failed" if is_failing else "degraded" if is_degraded else "ok"
        
        events = []
        steps = [
            JourneyStep.RECEIPT,
            JourneyStep.VALIDATION,
            JourneyStep.FRAUD_CHECK,
            JourneyStep.LIMIT_LOOKUP,
            JourneyStep.AUTHORIZATION,
            JourneyStep.RESPONSE
        ]
        for step in steps:
            events.append(JourneyEvent(
                event_id=f"evt_{self.run_id}_{minute}_{step.value}",
                run_id=self.run_id,
                journey_id=f"jny_{self.run_id}_{minute}",
                scenario=Scenario.PROGRESSIVE if is_degraded else Scenario.NORMAL,
                window_minute=minute,
                occurred_at=now,
                step=step,
                service=f"service.{step.value}",
                status=status if step in (JourneyStep.FRAUD_CHECK, JourneyStep.LIMIT_LOOKUP) else "ok",
                latency_ms=max(5.0, p95 / 4.0),
                retry_count=int(snap["traffic"]["retry_amplification_ratio"] - 1.0),
                queue_lag=snap["resources"]["antifraud_waiters_count"],
                timeout=is_failing,
                approved=not is_failing
            ))
        return events

    async def monitor_live(self, total_duration_sec: float = 60.0):
        print("\n" + "=" * 76)
        print("   ARKHÉ SENTINEL: INTEGRAÇÃO DIRETA COM SENTINEL CORE (PORTA 8000)      ")
        print("=" * 76)
        print(f"[*] Conectando ao Ambiente de Carga (Lab): {LAB_URL}")
        print(f"[*] Conectando ao Sentinel Core Daemon:    {CORE_URL}")
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Valida conectividade com Sentinel Core (8000)
            try:
                r_core = await client.get(f"{CORE_URL}/health")
                core_health = r_core.json()
                print(f"[✓] Sentinel Core Online na porta 8000: {core_health}")
            except Exception as e:
                print(f"[!] Aviso: Sentinel Core na porta 8000 indisponível ({e}). Usando motor local.")

            # 2. Reseta estado inicial do ambiente de validação (8080)
            try:
                await client.post(f"{CHAOS_ENDPOINT}/reset")
                print("[✓] Ambiente de validação (8080) pronto e nominal.")
            except Exception as e:
                print(f"[!] Erro ao conectar ao lab ({e}). Certifique-se de que app.py está rodando na porta 8080.")
                return

            start_time = time.time()
            prev_snap = None
            
            # Linha do tempo de Caos:
            # 0s - 12s: Nominal (45ms)
            # 12s - 25s: Drift Silencioso no Antifraude (255ms)
            # 25s+: Ruptura de Concorrência (420ms)
            drift_injected = False
            rupture_injected = False

            while (time.time() - start_time) < total_duration_sec:
                elapsed = time.time() - start_time
                
                # Injeções de Caos programadas
                if elapsed >= 12.0 and not drift_injected:
                    try:
                        await client.post(f"{CHAOS_ENDPOINT}/scenario/drift")
                        drift_injected = True
                        print("\n" + "!" * 76)
                        print(f"[⚡ CAOS INJETADO aos {elapsed:.1f}s] Antifraude entrou em Drift (45ms -> 255ms)")
                        print("   Aviso: Ocupação do Pool deve subir para ~68% pela Lei de Little.")
                        print("!" * 76)
                    except Exception as err:
                        print(f"[!] Falha ao injetar drift: {err}")

                if elapsed >= 25.0 and not rupture_injected:
                    try:
                        await client.post(f"{CHAOS_ENDPOINT}/scenario/rupture")
                        rupture_injected = True
                        print("\n" + "!" * 76)
                        print(f"[🔥 RUPTURA aos {elapsed:.1f}s] Antifraude atingiu 420ms (Demanda > 30 conexões)")
                        print("   Aviso: Fila física transbordará e timeouts de 1500ms ocorrerão.")
                        print("!" * 76)
                    except Exception as err:
                        print(f"[!] Falha ao injetar ruptura: {err}")

                # Coleta telemetria viva
                try:
                    res = await client.get(TELEMETRY_ENDPOINT)
                    snap = res.json()
                except Exception as e:
                    print(f"[!] Falha na coleta de telemetria: {e}")
                    await asyncio.sleep(1.0)
                    continue

                # Cria janela canônica do Sentinel
                window = self._convert_snapshot_to_window(self.current_minute, snap, prev_snap)
                self.windows.append(window)
                if len(self.windows) > 20:
                    self.windows.pop(0)

                events = self._generate_synthetic_journey_events(self.current_minute, snap)
                self.events.extend(events)
                if len(self.events) > 120:
                    self.events = self.events[-120:]

                # Monta bundle canônico para o Sentinel
                bundle = SimulationBundle(
                    run_id=self.run_id,
                    seed=42,
                    scenario=Scenario.PROGRESSIVE if drift_injected else Scenario.NORMAL,
                    events=self.events,
                    windows=self.windows,
                    ground_truth=GroundTruth(
                        degradation=drift_injected,
                        impact_minute=5 if drift_injected else None
                    )
                )

                # Análise Oficial do ARKHÉ SENTINEL CORE
                trajectory, assessment, elapsed_analysis_ms = analyze(bundle)
                
                # Avaliação do Baseline SRE Tradicional
                p95 = snap["latency_ms"]["p95"]
                total_errors = snap["outcomes"]["technical_timeouts"] + snap["outcomes"]["pool_exhaustion_errors"]
                attempts = snap["traffic"]["attempts_total"]
                err_rate = (total_errors / max(1, attempts))
                sre_triggered = (err_rate >= 0.05 and attempts > 100) or (p95 >= 1490.0)

                if assessment.score >= 50.0 and self.t_sentinel_alert is None:
                    self.t_sentinel_alert = elapsed

                if sre_triggered and self.t_sre_alert is None:
                    self.t_sre_alert = elapsed

                # Renderiza HUD no Console
                self._render_hud(elapsed, snap, trajectory, assessment, sre_triggered, p95, err_rate)
                
                # Salva estado para Dashboard Web em tempo real
                self._save_dashboard_state(snap, trajectory, assessment, sre_triggered, elapsed)

                prev_snap = snap
                self.current_minute += 1
                await asyncio.sleep(self.window_duration)

            # Ao fim da execução, gera o Relatório de RCA via Sentinel Core Report Agent
            print("\n" + "=" * 76)
            print("   GERANDO RELATÓRIO EXECUTIVO DE RCA VIA SENTINEL CORE REPORT AGENT...  ")
            print("=" * 76)
            try:
                report, report_mode = await create_report(trajectory, assessment)
                self.last_report = report
                print(f"[✓] Relatório de Análise de Trajetória Gerado (Modo: {report_mode})")
                print(f"\n📋 SUMÁRIO EXECUTIVO:")
                print(f"   {report.summary}\n")
                print("🔍 EVIDÊNCIAS E RECOMENDAÇÕES DETECTADAS:")
                for claim in report.claims:
                    print(f"   • [{claim.category.value.upper()}] {claim.text}")
                for check in report.recommended_checks:
                    print(f"   • [RECOMENDAÇÃO] {check.text}")
                
                self._save_rca_report_md(report, trajectory, assessment)
            except Exception as e:
                print(f"[!] Erro ao gerar relatório do analyst: {e}")

    def _render_hud(self, elapsed: float, snap: dict, trajectory, assessment, sre_triggered: bool, p95: float, err_rate: float):
        pool_in_use = snap["resources"]["antifraud_pool_in_use"]
        pool_cap = snap["resources"]["antifraud_pool_capacity"]
        pool_pct = snap["resources"]["antifraud_pool_utilization_ratio"] * 100
        waiters = snap["resources"]["antifraud_waiters_count"]
        unique_txs = snap["traffic"]["unique_transactions_total"]
        attempts = snap["traffic"]["attempts_total"]
        retries = snap["traffic"]["retry_amplification_ratio"]

        score_color = "\033[92m" if assessment.score < 50 else ("\033[93m" if assessment.score < 75 else "\033[91m")
        reset_color = "\033[0m"

        print(f"\n[{elapsed:05.1f}s] " + "─" * 68)
        print(f" TRAFEGO VIVO: {unique_txs} transações | {attempts} tentativas | R_retry: {retries:.2f}")
        print(f" POOL ANTIFRAUDE: {pool_in_use}/{pool_cap} slots ({pool_pct:.1f}%) | Espera em Fila: {waiters} conexões")
        print(f" SENTINEL RISK SCORE: {score_color}{assessment.score:.1f} / 100 [{assessment.level.value.upper()}]{reset_color}")
        print(f" ESTADO TRAJETÓRIA:   {trajectory.state} -> Desfecho Provável: {trajectory.probable_outcome}")
        
        # Evidências do Sentinel
        if assessment.evidence:
            top_evidence = assessment.evidence[0]
            print(f" EVIDÊNCIA PRINCIPAL: [{top_evidence.kind}] {top_evidence.title} ({top_evidence.interpretation})")

        # Status Tradicional
        sre_status = "\033[91mDISPAROU ALARME (Pós-Impacto)\033[0m" if sre_triggered else "\033[92mNORMAL (Em Silêncio)\033[0m"
        print(f" SRE BASELINE TRADICIONAL: {sre_status} (P95: {p95:.1f}ms, Erros: {err_rate*100:.1f}%)")

        if self.t_sentinel_alert is not None:
            if self.t_sre_alert is None:
                delta = elapsed - self.t_sentinel_alert
                print(f" \033[96m>>> ANTECEDÊNCIA ACUMULADA DO SENTINEL: +{delta:.1f}s (SRE ainda inerte) <<<\033[0m")
            else:
                delta = self.t_sre_alert - self.t_sentinel_alert
                print(f" \033[92m>>> ANTECEDÊNCIA FINAL COMPROVADA: +{delta:.1f}s ({delta/60:.1f} min) <<<\033[0m")

    def _save_dashboard_state(self, snap: dict, trajectory, assessment, sre_triggered: bool, elapsed: float):
        state_payload = {
            "elapsed_sec": round(elapsed, 1),
            "traffic": snap["traffic"],
            "resources": snap["resources"],
            "latency": snap["latency_ms"],
            "sentinel": {
                "score": assessment.score,
                "level": assessment.level.value,
                "state": trajectory.state,
                "probable_outcome": trajectory.probable_outcome,
                "evidence": [
                    {
                        "kind": e.kind,
                        "title": e.title,
                        "observed": e.observed_value,
                        "interpretation": e.interpretation
                    }
                    for e in assessment.evidence[:3]
                ],
                "lead_time_seconds": round(elapsed - (self.t_sentinel_alert or elapsed), 1)
            },
            "sre_baseline": {
                "triggered": sre_triggered,
                "p95": snap["latency_ms"]["p95"],
                "error_rate": round((snap["outcomes"]["technical_timeouts"] / max(1, snap["traffic"]["attempts_total"])) * 100, 2)
            }
        }
        with open("live_sentinel_state.json", "w", encoding="utf-8") as f:
            json.dump(state_payload, f, indent=2, ensure_ascii=False)

    def _save_rca_report_md(self, report, trajectory, assessment):
        md = f"""# ARKHÉ SENTINEL — Relatório de Análise de Trajetória (RCA)

**Data/Hora:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Run ID:** `{trajectory.run_id}`  
**Estado da Trajetória:** `{trajectory.state}`  
**Desfecho Provável:** `{trajectory.probable_outcome}`  
**Score de Risco Determinado:** **{assessment.score:.1f} / 100** (`{assessment.level.value.upper()}`)  
**Faixa de Confiança:** `{report.confidence_band}`  

---

## 1. Sumário Executivo
> {report.summary}

---

## 2. Evidências e Fatos Observados
"""
        for claim in report.claims:
            md += f"- **[{claim.category.value.upper()}]** {claim.text} *(Evidências: `{', '.join(claim.evidence_ids)}`)*\n"

        md += """
---

## 3. Ações e Verificações Recomendadas pelo Core
"""
        for check in report.recommended_checks:
            md += f"- 🔍 {check.text} *(Ref: `{', '.join(check.evidence_ids)}`)*\n"

        with open("sentinel_rca_report.md", "w", encoding="utf-8") as f:
            f.write(md)
        print("[✓] Arquivo 'sentinel_rca_report.md' salvo com sucesso!")

if __name__ == "__main__":
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 45.0
    collector = SentinelLiveCollector(window_duration_sec=3.0)
    asyncio.run(collector.monitor_live(duration))
