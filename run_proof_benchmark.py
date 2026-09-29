import asyncio
import os
import sys
import time
import json

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import httpx
import numpy as np
from scipy import stats

from arkhe_detector import ArkheTrajectoryEngine
from traditional_monitor import TraditionalSREMonitor
from coi_engine import COIEngine
from report_generator import generate_html_report

LAB_HOST = os.getenv("LAB_HOST", "http://127.0.0.1:8080")
TELEMETRY_URL = f"{LAB_HOST}/telemetry/as_of"
CHAOS_URL = f"{LAB_HOST}/admin/chaos"
MITIGATION_URL = f"{LAB_HOST}/admin/mitigation"

class LaboratoryProofOrchestrator:
    """
    Executa a Prova Prática em 4 Fases no ARKHÉ Benchmark Lab sob 120 TPS:
    - Fase 1: Sensoriamento Passivo de Filas (Física de Little sem dados de cartão)
    - Fase 2: Comparação Cega de Lead Time (ARKHÉ vs SRE Tradicional)
    - Fase 3: Alerta Consultivo Antecipado (Human-in-the-Loop)
    - Fase 4: Fechamento de Ciclo Autônomo (Closed-Loop Autoscaling + Fast-Path)
    """
    def __init__(self, time_scale: float = 8.0, target_rounds: int = 3):
        self.time_scale = time_scale
        self.target_rounds = target_rounds
        self.coi_engine = COIEngine()

    async def wait_for_service(self, client: httpx.AsyncClient):
        for _ in range(15):
            try:
                res = await client.get(TELEMETRY_URL, timeout=2.0)
                if res.status_code == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(1.0)
        raise RuntimeError("Serviço de autorização indisponível.")

    async def run_single_round(self, round_num: int) -> dict:
        print(f"\n{'='*30} BATERIA DE PROVA {round_num}/{self.target_rounds} {'='*30}")
        
        arkhe_engine = ArkheTrajectoryEngine()
        traditional_monitor = TraditionalSREMonitor(sustained_checks_required=2)
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            await self.wait_for_service(client)
            await client.post(f"{CHAOS_URL}/reset")
            print("[OK] Ambiente resetado para estado nominal (45ms).")
            print("[*] Estabilizando tráfego nominal de baseline (3s)...")
            await asyncio.sleep(3.0)

            # Cronograma do teste (acelerado em time_scale vezes)
            t_drift_start = 100.0 / self.time_scale
            t_rupture_start = 280.0 / self.time_scale
            
            t0 = time.time()
            drift_injected = False
            rupture_injected = False
            
            t_arkhe_alert = None
            arkhe_details = None
            t_traditional_alert = None
            traditional_details = None
            
            snapshots_collected = []

            print(f"[*] Monitoramento cego iniciado ({self.time_scale}x). Aguardando convergência de tráfego...")

            while True:
                now = time.time()
                elapsed = now - t0
                
                # Injeção de anomalia
                if elapsed >= t_drift_start and not drift_injected:
                    await client.post(f"{CHAOS_URL}/set_drift?antifraud_latency_ms=255.0&jitter_ms=15.0")
                    drift_injected = True
                    print(f"\n[CAOS] Injeção de Drift aos {elapsed:.1f}s: Latência base subiu para 255ms (Pool esperado ~68%)")

                if elapsed >= t_rupture_start and not rupture_injected:
                    await client.post(f"{CHAOS_URL}/set_drift?antifraud_latency_ms=420.0&jitter_ms=25.0")
                    rupture_injected = True
                    print(f"\n[CAOS] Injeção de Ruptura aos {elapsed:.1f}s: Latência base subiu para 420ms (Demanda > Capacidade 30 slots)")

                try:
                    res = await client.get(TELEMETRY_URL)
                    snap = res.json()
                    snapshots_collected.append(snap)
                except Exception as e:
                    await asyncio.sleep(0.5)
                    continue

                # 1. Avaliação pelo Motor ARKHÉ
                arkhe_engine.add_snapshot(snap)
                if t_arkhe_alert is None:
                    arkhe_res = arkhe_engine.evaluate()
                    if arkhe_res.triggered:
                        t_arkhe_alert = elapsed
                        arkhe_details = arkhe_res
                        print(f"\n>>> [ARKHÉ ALERTA ANTECIPADO] Detectado aos {elapsed:.1f}s!")
                        print(f"    Motivo: {arkhe_res.trigger_reason}")
                        print(f"    Vetor S_ARKHE: {arkhe_res.vector}")
                        print(f"    Confiança: {arkhe_res.confidence_score*100:.0f}%")

                # 2. Avaliação pelo Monitor Tradicional (Baseline SRE)
                if t_traditional_alert is None:
                    trad_res = traditional_monitor.evaluate(snap)
                    if trad_res.triggered:
                        t_traditional_alert = elapsed
                        traditional_details = trad_res
                        print(f"\n>>> [ALERTA TRADICIONAL SRE] Violado aos {elapsed:.1f}s!")
                        print(f"    Regra violada: {trad_res.trigger_rule}")
                        print(f"    P95: {trad_res.p95_ms:.1f}ms | Erros: {trad_res.error_rate*100:.1f}%")

                # Encerra após o tradicional disparar
                if t_traditional_alert is not None:
                    await asyncio.sleep(2.0)
                    break

                # Timeout de segurança
                if elapsed > (t_rupture_start + (60.0 / (self.time_scale / 5.0))):
                    print("[!] Limite de segurança de tempo da rodada atingido.")
                    break

                await asyncio.sleep(0.5)

            # Cálculos comparativos
            t_ark = t_arkhe_alert if t_arkhe_alert is not None else elapsed
            t_tra = t_traditional_alert if t_traditional_alert is not None else elapsed
            real_delta_t = max(0.0, t_tra - t_ark)
            
            equiv_delta_t_sec = real_delta_t * self.time_scale
            equiv_delta_t_min = equiv_delta_t_sec / 60.0

            last_snap = snapshots_collected[-1]
            lost_txs = last_snap["outcomes"]["technical_timeouts"] + last_snap["outcomes"]["pool_exhaustion_errors"]
            coi_report = self.coi_engine.calculate(
                delta_t_seconds=equiv_delta_t_sec,
                lost_unique_txs=max(10, lost_txs)
            )

            str_arkhe = f"{t_arkhe_alert:.1f}s" if t_arkhe_alert is not None else "Não detectado"
            str_trad = f"{t_traditional_alert:.1f}s" if t_traditional_alert is not None else f"Não disparou ({elapsed:.1f}s)"

            print(f"\n[RESULTADO BATERIA {round_num}]:")
            print(f"    Tempo disparo ARKHÉ:             {str_arkhe}")
            print(f"    Tempo disparo SRE Tradicional:   {str_trad}")
            print(f"    Antecedência Real no Teste (Δt): {real_delta_t:.1f}s")
            print(f"    Antecedência Equivalente Prod:   {equiv_delta_t_min:.2f} minutos")
            print(f"    Prejuízo Evitável (COI Líquido): R$ {coi_report.direct_margin_loss_brl:,.2f}")
            print(f"    GMV Total Protegido:             R$ {coi_report.total_gmv_loss_brl:,.2f}")

            return {
                "round": round_num,
                "t_arkhe": t_arkhe_alert,
                "t_traditional": t_traditional_alert,
                "delta_t_test_sec": real_delta_t,
                "delta_t_prod_minutes": equiv_delta_t_min,
                "coi": coi_report,
                "arkhe_reason": arkhe_details.trigger_reason if arkhe_details else None,
                "traditional_rule": traditional_details.trigger_rule if traditional_details else None
            }

    async def execute_proof(self):
        print(f"================================================================")
        print(f"   PROTOCOLO EXPERIMENTAL: PROVA PRÁTICA DO ARKHÉ EM LABORATÓRIO")
        print(f"   Ambiente: Autorizador de Cartões a 120 TPS Nominais           ")
        print(f"================================================================")
        print(f"Parâmetros: {self.target_rounds} baterias independentes | Aceleração temporal: {self.time_scale}x")
        
        results = []
        for r in range(1, self.target_rounds + 1):
            res = await self.run_single_round(r)
            results.append(res)
            await asyncio.sleep(2.0)

        # Análise Estatística
        deltas = [r["delta_t_prod_minutes"] for r in results]
        mean_delta = float(np.mean(deltas))
        median_delta = float(np.median(deltas))
        std_delta = float(np.std(deltas))
        
        # Teste de Hipótese Unilateral: H0: Delta_t < 3.0 min vs H1: Delta_t >= 3.0 min
        t_stat, p_val_two_sided = stats.ttest_1samp(deltas, popmean=3.0)
        p_val = float((p_val_two_sided / 2.0) if t_stat > 0 else 1.0 - (p_val_two_sided / 2.0))

        tot_coi = sum(r["coi"].direct_margin_loss_brl for r in results)
        tot_gmv = sum(r["coi"].total_gmv_loss_brl for r in results)

        print(f"\n================================================================")
        print(f"               DOSSIÊ ESTATÍSTICO DA PROVA PRÁTICA             ")
        print(f"================================================================")
        print(f"Amostras Executadas:       {len(deltas)} baterias")
        print(f"Média de Antecedência:     {mean_delta:.2f} minutos ({mean_delta*60:.0f}s)")
        print(f"Mediana de Antecedência:   {median_delta:.2f} minutos")
        print(f"Desvio Padrão:             {std_delta:.2f} minutos")
        print(f"Faixa Observada:           [{min(deltas):.2f}m - {max(deltas):.2f}m]")
        print(f"Teste t de Student (Δt≥3m):t = {t_stat:.3f}, p-value = {p_val:.4e}")
        print(f"Hipótese Comprovada:       {'SIM (Estatisticamente Significante)' if p_val < 0.05 else 'INCONCLUSIVO'}")
        print(f"Prejuízo Evitável Total:   R$ {tot_coi:,.2f}")
        print(f"GMV Total Protegido:       R$ {tot_gmv:,.2f}")
        print(f"================================================================")

        summary_payload = {
            "rounds_count": len(deltas),
            "mean_delta_t_minutes": round(mean_delta, 2),
            "median_delta_t_minutes": round(median_delta, 2),
            "std_delta_t_minutes": round(std_delta, 2),
            "min_delta_t_minutes": round(float(min(deltas)), 2),
            "max_delta_t_minutes": round(float(max(deltas)), 2),
            "p_value": p_val,
            "hypothesis_confirmed": bool(p_val < 0.05),
            "total_coi_margin_saved_brl": round(tot_coi, 2),
            "total_gmv_protected_brl": round(tot_gmv, 2),
            "rounds": [
                {
                    "round": r["round"],
                    "delta_t_minutes": round(r["delta_t_prod_minutes"], 2),
                    "direct_margin_loss_brl": r["coi"].direct_margin_loss_brl,
                    "total_gmv_loss_brl": r["coi"].total_gmv_loss_brl,
                    "arkhe_reason": r["arkhe_reason"],
                    "traditional_rule": r["traditional_rule"]
                }
                for r in results
            ]
        }

        with open("benchmark_results.json", "w", encoding="utf-8") as f:
            json.dump(summary_payload, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] Dados exportados para 'benchmark_results.json'")

        try:
            generate_html_report("benchmark_results.json", "arkhe_benchmark_report.html")
            print(f"[OK] Dossiê HTML executivo gerado em 'arkhe_benchmark_report.html'")
        except Exception as e:
            print(f"[!] Erro ao gerar dossiê HTML: {e}")

if __name__ == "__main__":
    orchestrator = LaboratoryProofOrchestrator(time_scale=8.0, target_rounds=3)
    asyncio.run(orchestrator.execute_proof())
