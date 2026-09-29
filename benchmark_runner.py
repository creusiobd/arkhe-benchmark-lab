import asyncio
import json
import os
import sys
import time
from typing import List

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
from coi_engine import COIEngine, COIParameters
from report_generator import generate_html_report

LAB_HOST = os.getenv("LAB_HOST", "http://localhost:8080")
TELEMETRY_URL = f"{LAB_HOST}/telemetry/as_of"
CHAOS_URL = f"{LAB_HOST}/admin/chaos"

class BenchmarkOrchestrator:
    def __init__(self, time_scale: float = 10.0, target_rounds: int = 5):
        """
        :param time_scale: Fator de aceleração da linha do tempo.
                           1.0 = Tempo Real (15 min/rodada)
                           10.0 = Acelerado (~90s por rodada, ideal para validação local)
        """
        self.time_scale = time_scale
        self.target_rounds = target_rounds
        self.coi_engine = COIEngine()

    async def wait_for_service(self, client: httpx.AsyncClient, max_retries: int = 15):
        for _ in range(max_retries):
            try:
                res = await client.get(TELEMETRY_URL, timeout=1.5)
                if res.status_code == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(1.0)
        raise RuntimeError(f"Serviço {LAB_HOST} indisponível.")

    async def run_single_round(self, round_num: int) -> dict:
        print(f"\n{'='*25} BATERIA {round_num}/{self.target_rounds} {'='*25}")
        
        arkhe_engine = ArkheTrajectoryEngine()
        traditional_monitor = TraditionalSREMonitor(sustained_checks_required=2)
        
        async with httpx.AsyncClient(timeout=3.0) as client:
            await self.wait_for_service(client)
            await client.post(f"{CHAOS_URL}/reset")
            print("[✓] Ambiente resetado para estado nominal (45ms).")
            print("[*] Estabilizando tráfego nominal de baseline (3s)...")
            await asyncio.sleep(3.0)

            # Escala de tempo:
            # Nominal -> Drift aos 120s/scale -> Ruptura aos 360s/scale
            t_drift_start = 120.0 / self.time_scale
            t_rupture_start = 360.0 / self.time_scale
            
            t0 = time.time()
            drift_injected = False
            rupture_injected = False
            
            t_arkhe_alert = None
            arkhe_details = None
            t_traditional_alert = None
            traditional_details = None
            
            snapshots_collected = []

            print(f"[*] Monitoramento cego iniciado (Escala {self.time_scale}x). Aguardando convergência de tráfego...")

            while True:
                now = time.time()
                elapsed = now - t0
                
                # Injeção de anomalia de acordo com a cronologia
                if elapsed >= t_drift_start and not drift_injected:
                    await client.post(f"{CHAOS_URL}/set_drift?antifraud_latency_ms=255.0&jitter_ms=20.0")
                    drift_injected = True
                    print(f"\n[⚡ CAOS] Injeção de Drift aos {elapsed:.1f}s: Latência base subiu para 255ms (Pool esperado ~68%)")

                if elapsed >= t_rupture_start and not rupture_injected:
                    await client.post(f"{CHAOS_URL}/set_drift?antifraud_latency_ms=420.0&jitter_ms=30.0")
                    rupture_injected = True
                    print(f"\n[🔥 CAOS] Injeção de Ruptura aos {elapsed:.1f}s: Latência base subiu para 420ms (Demanda > Capacidade 30 slots)")

                try:
                    res = await client.get(TELEMETRY_URL)
                    snap = res.json()
                    snapshots_collected.append(snap)
                except Exception as e:
                    print(f"[!] Erro de leitura de telemetria: {e}")
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
                        print(f"\n>>> [ALERTA TRADICIONAL DISPARADO] SRE Baseline aos {elapsed:.1f}s!")
                        print(f"    Regra violada: {trad_res.trigger_rule}")
                        print(f"    P95: {trad_res.p95_ms:.1f}ms | Erros: {trad_res.error_rate*100:.1f}%")

                # Condição de encerramento da rodada
                if t_traditional_alert is not None:
                    # Coleta mais alguns segundos para fechamento
                    await asyncio.sleep(2.0)
                    break

                # Timeout de segurança se o sistema não colapsar após a ruptura
                if elapsed > (t_rupture_start + (90.0 / max(0.5, self.time_scale / 10.0))):
                    print("[!] Limite de segurança de tempo atingido para a rodada.")
                    break

                await asyncio.sleep(max(0.2, 1.0 / (self.time_scale / 5.0)))

            # Cálculos comparativos
            t_ark = t_arkhe_alert if t_arkhe_alert is not None else elapsed
            t_tra = t_traditional_alert if t_traditional_alert is not None else elapsed
            real_delta_t = t_tra - t_ark
            
            # Normalização para a escala real em produção (minutos equivalentes)
            equiv_delta_t_sec = real_delta_t * self.time_scale
            equiv_delta_t_min = equiv_delta_t_sec / 60.0

            # Transações perdidas por falha técnica acumuladas
            last_snap = snapshots_collected[-1]
            lost_txs = last_snap["outcomes"]["technical_timeouts"] + last_snap["outcomes"]["pool_exhaustion_errors"]
            coi_report = self.coi_engine.calculate(
                delta_t_seconds=equiv_delta_t_sec,
                lost_unique_txs=max(10, lost_txs)
            )

            str_arkhe = f"{t_arkhe_alert:.1f}s" if t_arkhe_alert is not None else "Não detectado"
            str_trad = f"{t_traditional_alert:.1f}s" if t_traditional_alert is not None else f"Não disparou (fim aos {elapsed:.1f}s)"

            print(f"\n[★] RESULTADOS DA BATERIA {round_num}:")
            print(f"    Tempo disparo ARKHÉ:       {str_arkhe}")
            print(f"    Tempo disparo Tradicional: {str_trad}")
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

    async def execute_all(self):
        print(f"================================================================")
        print(f"   ARKHÉ VALIDATION PROTOCOL: BENCHMARK CEGO vs SRE BASELINE    ")
        print(f"================================================================")
        print(f"Parâmetros: {self.target_rounds} baterias | Aceleração temporal: {self.time_scale}x")
        
        results = []
        for r in range(1, self.target_rounds + 1):
            res = await self.run_single_round(r)
            results.append(res)
            await asyncio.sleep(2.0)

        # Análise Estatística
        deltas = [r["delta_t_prod_minutes"] for r in results]
        mean_delta = np.mean(deltas)
        median_delta = np.median(deltas)
        std_delta = np.std(deltas)
        
        # Teste de Hipótese Unilateral: H0: Delta_t < 5.0 minutos vs H1: Delta_t >= 5.0 minutos
        # t-test one-sample
        t_stat, p_val_two_sided = stats.ttest_1samp(deltas, popmean=5.0)
        p_val = (p_val_two_sided / 2.0) if t_stat > 0 else 1.0 - (p_val_two_sided / 2.0)

        print(f"\n================================================================")
        print(f"                  RELATÓRIO ESTATÍSTICO FINAL                  ")
        print(f"================================================================")
        print(f"Amostras:                 {len(deltas)} rodadas")
        print(f"Média de Antecedência:    {mean_delta:.2f} minutos")
        print(f"Mediana de Antecedência:  {median_delta:.2f} minutos")
        print(f"Desvio Padrão:            {std_delta:.2f} minutos")
        print(f"Faixa Observada:          [{min(deltas):.2f}m - {max(deltas):.2f}m]")
        print(f"Teste de Hipótese (Δt ≥ 5m): t = {t_stat:.3f}, p-value = {p_val:.4e}")
        
        if p_val < 0.05:
            print(f"[✓ SUCESSO] A hipótese de antecedência do ARKHÉ foi COMPROVADA estatisticamente (p < 0.05)!")
        else:
            print(f"[!] A hipótese necessita de mais amostras ou ajuste de limiares.")

        # Salva resultado em JSON para relatórios
        summary_payload = {
            "rounds_count": len(deltas),
            "mean_delta_t_minutes": round(float(mean_delta), 2),
            "median_delta_t_minutes": round(float(median_delta), 2),
            "std_delta_t_minutes": round(float(std_delta), 2),
            "min_delta_t_minutes": round(float(min(deltas)), 2),
            "max_delta_t_minutes": round(float(max(deltas)), 2),
            "p_value": float(p_val),
            "hypothesis_confirmed": bool(p_val < 0.05),
            "rounds": [
                {
                    "round": r["round"],
                    "delta_t_minutes": round(r["delta_t_prod_minutes"], 2),
                    "direct_margin_loss_brl": r["coi"].direct_margin_loss_brl,
                    "total_gmv_loss_brl": r["coi"].total_gmv_loss_brl
                }
                for r in results
            ]
        }

        # Write to both working dir and artifacts dir if mounted in Docker
        target_dirs = ["."]
        if os.path.isdir("artifacts"):
            target_dirs.append("artifacts")

        for tdir in target_dirs:
            out_json = os.path.join(tdir, "benchmark_results.json")
            out_html = os.path.join(tdir, "arkhe_benchmark_report.html")
            try:
                with open(out_json, "w", encoding="utf-8") as f:
                    json.dump(summary_payload, f, indent=2, ensure_ascii=False)
                print(f"\n[✓] Relatório salvo com sucesso em '{out_json}'")
                generate_html_report(out_json, out_html)
                print(f"[✓] Dossiê HTML interativo gerado em '{out_html}'")
            except Exception as e:
                print(f"[!] Erro ao salvar artefatos em '{tdir}': {e}")

if __name__ == "__main__":
    scale = float(os.getenv("BENCHMARK_SCALE", sys.argv[1] if len(sys.argv) > 1 else 8.0))
    rounds = int(os.getenv("BENCHMARK_ROUNDS", sys.argv[2] if len(sys.argv) > 2 else 5))
    runner = BenchmarkOrchestrator(time_scale=scale, target_rounds=rounds)
    asyncio.run(runner.execute_all())
