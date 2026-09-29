#!/usr/bin/env python3
"""
ci/resilience_gate.py
ARKHÉ CI/CD Resilience Gate: Validação Estocástica e Portão de Resiliência de Lyapunov.

Executa testes de estresse estocástico no pipeline de CI/CD para impedir que PRs com
regressão de concorrência ou sensibilidade a filas cheguem à produção.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Dict, List, Optional
import httpx
import websockets

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

class ResilienceGateEvaluator:
    def __init__(
        self,
        base_http: str = "http://127.0.0.1:8080",
        base_ws: str = "ws://127.0.0.1:8080/ws/telemetry",
        max_rho: float = 0.50,
        max_wq_ws: float = 0.25,
        max_p95_ms: float = 1500.0,
        min_lead_time_sec: float = 0.0,
        sample_frames: int = 80
    ):
        self.base_http = base_http
        self.base_ws = base_ws
        self.max_rho = max_rho
        self.max_wq_ws = max_wq_ws
        self.max_p95_ms = max_p95_ms
        self.min_lead_time_sec = min_lead_time_sec
        self.sample_frames = sample_frames

    async def execute_gate(self) -> Dict:
        print("=" * 75)
        print("🛡️ ARKHÉ CI/CD RESILIENCE GATE: AVALIAÇÃO DE ESTABILIDADE DE LYAPUNOV")
        print("=" * 75)
        print(f"Target HTTP: {self.base_http}")
        print(f"Target WS:   {self.base_ws}")
        print(f"Limites de Aceitação: max_rho <= {self.max_rho} | max_wq_ws <= {self.max_wq_ws} | max_p95 <= {self.max_p95_ms}ms")
        print("-" * 75)

        async with httpx.AsyncClient(base_url=self.base_http, timeout=10.0) as client:
            # 1. Reset para fábrica
            print("[1/4] Resetando ambiente para estado nominal...")
            try:
                res = await client.post("/admin/chaos/reset")
                print(f"      Status: {res.json().get('message')}")
            except Exception as e:
                print(f"❌ Falha ao conectar ao servidor ARKHÉ: {e}")
                return {"passed": False, "error": f"Falha de conexão com o cluster: {e}"}

            # 2. Ativar Mitigação Fechada para avaliar se a auto-cura está operacional no novo build
            print("[2/4] Verificando se a auto-mitigação closed-loop está habilitada...")
            live = (await client.get("/telemetry/live")).json()
            if not live.get("mitigation", {}).get("enabled"):
                await client.post("/admin/mitigation/toggle")
            
            # Estabiliza sob carga nominal
            await client.post("/admin/chaos/scenario/nominal")
            await asyncio.sleep(2.0)

            # Injeta perturbação controlada de concorrência
            print("[3/4] Injetando perturbação estocástica controlada (Drift/Ruptura)...")
            await client.post("/admin/chaos/scenario/drift")

        # 3. Amostragem em Alta Frequência via WebSocket
        print(f"[4/4] Coletando {self.sample_frames} frames via WebSocket para cálculo de Lyapunov...")
        collected_frames = []
        async with websockets.connect(self.base_ws) as ws:
            for _ in range(self.sample_frames):
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                frame = json.loads(raw)
                collected_frames.append(frame)

        # Restaura ambiente
        async with httpx.AsyncClient(base_url=self.base_http, timeout=5.0) as client:
            await client.post("/admin/chaos/scenario/recover")

        # 4. Avaliação das Regras de Aceite do Gate
        latest = collected_frames[-1]
        rhos = [f["telemetry"]["resources"]["antifraud_pool_utilization_ratio"] for f in collected_frames]
        wq_ws_ratios = [f["telemetry"]["queueing"]["wq_ws_ratio"] for f in collected_frames]
        p95_lats = [f["telemetry"]["latency_ms"]["p95"] for f in collected_frames]
        p50_lats = [f["telemetry"]["latency_ms"]["p50"] for f in collected_frames]
        err_counts = [f["sre_governance"]["technical_errors_count"] for f in collected_frames]

        avg_rho = sum(rhos) / len(rhos)
        max_rho_observed = max(rhos)
        final_rho = rhos[-1]
        avg_wq_ws = sum(wq_ws_ratios) / len(wq_ws_ratios)
        max_p95 = max(p95_lats)
        final_p95 = p95_lats[-1]
        total_errors = err_counts[-1]
        sli_avail = latest["sre_governance"]["current_sli_availability_pct"]
        budget_rem = latest["sre_governance"]["error_budget_remaining_pct"]

        # Critérios Estritos do Portão de Resiliência:
        check_errors = (total_errors == 0)
        check_p95 = (final_p95 <= self.max_p95_ms)
        check_sli = (sli_avail >= 99.90)
        check_budget = (budget_rem >= 95.0)
        check_wq_ws = (avg_wq_ws <= self.max_wq_ws)
        # O pool final deve estar estabilizado abaixo do limiar graças à mitigação
        check_rho = (final_rho <= self.max_rho or latest["mitigation"]["active"])

        all_passed = all([check_errors, check_p95, check_sli, check_budget, check_wq_ws, check_rho])

        result = {
            "passed": all_passed,
            "metrics": {
                "total_frames": len(collected_frames),
                "final_rho": round(final_rho, 4),
                "max_rho_observed": round(max_rho_observed, 4),
                "avg_wq_ws_ratio": round(avg_wq_ws, 4),
                "final_p95_ms": round(final_p95, 1),
                "max_p95_ms": round(max_p95, 1),
                "technical_errors": total_errors,
                "sli_availability_pct": sli_avail,
                "error_budget_remaining_pct": budget_rem,
                "mitigation_active": latest["mitigation"]["active"]
            },
            "checks": {
                "zero_technical_errors": check_errors,
                "latency_p95_sla_compliant": check_p95,
                "sli_availability_above_threshold": check_sli,
                "error_budget_preserved": check_budget,
                "queue_wait_ratio_acceptable": check_wq_ws,
                "lyapunov_basin_preserved_or_mitigated": check_rho
            }
        }

        return result

    def generate_markdown_report(self, result: Dict) -> str:
        passed = result.get("passed", False)
        status_badge = "✅ **GATE PASSED: DEPLOY AUTHORIZED**" if passed else "❌ **GATE FAILED: DEPLOY BLOCKED (STABILITY REGRESSION)**"
        status_color = "#10b981" if passed else "#ef4444"

        m = result.get("metrics", {})
        c = result.get("checks", {})

        md = f"""# 🛡️ ARKHÉ CI/CD Resilience Gate Report

### Decisão do Portão de Resiliência: {status_badge}

> **Avaliação de Estabilidade Estocástica de Lyapunov e Lei de Little**  
> Data: `{time.strftime("%Y-%m-%d %H:%M:%S UTC")}` | Frames Analisados: `{m.get('total_frames', 0)}` | Mitigação Autônoma Ativa: `{m.get('mitigation_active', False)}`

---

## 📊 Scorecard de Validação de Resiliência

| Critério de Engenharia | Métrica Observada | Limiar / Restrição | Resultado |
| :--- | :---: | :---: | :---: |
| **Erros Técnicos HTTP 5xx** | **`{m.get('technical_errors', 0)}` falhas** | Tolerância Zero (`0`) | {"✅ PASS" if c.get('zero_technical_errors') else "❌ FAIL"} |
| **Latência P95 (Cauda)** | **`{m.get('final_p95_ms', 0)} ms`** (Pico: `{m.get('max_p95_ms', 0)} ms`) | Máximo Admissível: `< 1500 ms` | {"✅ PASS" if c.get('latency_p95_sla_compliant') else "❌ FAIL"} |
| **SLI de Disponibilidade** | **`{m.get('sli_availability_pct', 0):.3f}%`** | Meta Contratual: `≥ 99.90%` | {"✅ PASS" if c.get('sli_availability_above_threshold') else "❌ FAIL"} |
| **Error Budget Preservado** | **`{m.get('error_budget_remaining_pct', 0):.1f}%`** | Mínimo Restante: `≥ 95.0%` | {"✅ PASS" if c.get('error_budget_preserved') else "❌ FAIL"} |
| **Razão Fila/Serviço (Wq/Ws)** | **`{m.get('avg_wq_ws_ratio', 0):.4f}`** | Limite de Fila: `≤ {self.max_wq_ws}` | {"✅ PASS" if c.get('queue_wait_ratio_acceptable') else "❌ FAIL"} |
| **Ocupação do Pool (rho)** | **`{m.get('final_rho', 0)*100:.1f}%`** (Pico: `{m.get('max_rho_observed', 0)*100:.1f}%`) | Bacia de Lyapunov: `≤ {self.max_rho*100:.0f}%` | {"✅ PASS" if c.get('lyapunov_basin_preserved_or_mitigated') else "❌ FAIL"} |

---

### 🧠 Diagnóstico de Engenharia

{"🎉 **Nenhuma regressão de resiliência detectada.** O novo build demonstrou comportamento estável na Bacia de Lyapunov sob estresse estocástico e está homologado para promoção de ambiente." if passed else "🚨 **Regressão de resiliência detectada!** O código do Pull Request causou inflação de filas ou estouro do Error Budget sob carga. O deploy foi bloqueado para proteger os contratos de SLA de produção."}

---
*Relatório gerado automaticamente pelo ARKHÉ CI/CD Resilience Gate.*
"""
        return md

async def main_async():
    parser = argparse.ArgumentParser(description="ARKHÉ CI/CD Resilience Gate Runner")
    parser.add_argument("--base-http", default=os.getenv("ARKHE_HTTP_URL", "http://127.0.0.1:8080"))
    parser.add_argument("--base-ws", default=os.getenv("ARKHE_WS_URL", "ws://127.0.0.1:8080/ws/telemetry"))
    parser.add_argument("--max-rho", type=float, default=0.50)
    parser.add_argument("--max-wq-ws", type=float, default=0.25)
    parser.add_argument("--max-p95-ms", type=float, default=1500.0)
    parser.add_argument("--frames", type=int, default=80)
    parser.add_argument("--output-markdown", default=os.getenv("GITHUB_STEP_SUMMARY"))
    parser.add_argument("--output-json", default="resilience_gate_report.json")

    args = parser.parse_args()

    evaluator = ResilienceGateEvaluator(
        base_http=args.base_http,
        base_ws=args.base_ws,
        max_rho=args.max_rho,
        max_wq_ws=args.max_wq_ws,
        max_p95_ms=args.max_p95_ms,
        sample_frames=args.frames
    )

    result = await evaluator.execute_gate()
    md_report = evaluator.generate_markdown_report(result)

    # Imprime no console
    print("\n" + "=" * 75)
    passed = result.get("passed", False)
    if passed:
        print("✅ ARKHÉ RESILIENCE GATE: APROVADO! (Deploy Autorizado)")
    else:
        print("❌ ARKHÉ RESILIENCE GATE: REPROVADO! (Deploy Bloqueado)")
    print("=" * 75)
    print(f"Erros: {result['metrics']['technical_errors']} | P95: {result['metrics']['final_p95_ms']}ms | SLI: {result['metrics']['sli_availability_pct']}% | Budget: {result['metrics']['error_budget_remaining_pct']}%")

    # Salva relatório JSON
    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"📁 Relatório JSON salvo em: {args.output_json}")

    # Salva relatório Markdown (para GitHub Step Summary ou PR comment)
    if args.output_markdown:
        try:
            with open(args.output_markdown, "a", encoding="utf-8") as f:
                f.write(md_report)
            print(f"📄 Resumo Markdown salvo em: {args.output_markdown}")
        except Exception as e:
            print(f"⚠️ Não foi possível escrever em {args.output_markdown}: {e}")

    # Retorna código de saída estrito para o CI/CD (0 = sucesso, 1 = falha/bloqueio)
    sys.exit(0 if passed else 1)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
