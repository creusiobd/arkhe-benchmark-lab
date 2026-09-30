"""
test_autonomous_mitigation.py
Validação automatizada do fechamento de ciclo (Closed-Loop Autonomous Mitigation).
Comprova que o ARKHÉ atua no minuto 0 de Drift e impede a degradação do SLA.
"""
import sys
import time
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8080"

def test_closed_loop():
    print("=" * 70)
    print("🧪 TESTE DE VALIDAÇÃO: CLOSED-LOOP AUTONOMOUS SELF-HEALING (ARKHÉ)")
    print("=" * 70)

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Reset para fábrica
        print("\n1. Resetando ambiente para estado nominal de fábrica...")
        r = client.post("/admin/chaos/reset")
        assert r.status_code == 200

        # 2. Ativar Mitigação Autônoma
        print("2. Ativando o Agente Atuador Closed-Loop (/admin/mitigation/toggle)...")
        # Verifica estado atual
        live = client.get("/telemetry/live").json()
        if not live.get("mitigation", {}).get("enabled"):
            r = client.post("/admin/mitigation/toggle")
            state = r.json()
        else:
            state = {"mitigation_enabled": True}
        print(f"   Status da Mitigação: Enabled={state['mitigation_enabled']}")
        assert state['mitigation_enabled'] is True

        # 3. Injetar Drift Silencioso no Antifraude
        print("\n3. Injetando Caos: 2. Drift Silencioso (255ms, Demanda > Pool 30)...")
        r = client.post("/admin/chaos/scenario/drift")
        assert r.status_code == 200

        # 4. Observar atuação autônoma sob tráfego simultâneo
        print("4. Aguardando atuação do Mitigador sob tráfego simultâneo...", flush=True)
        deadline = time.time() + 12.0
        step = 0
        while time.time() < deadline:
            time.sleep(1.0)
            step += 1
            res = client.get("/telemetry/live").json()
            mit = res["mitigation"]
            sre = res["sre_governance"]
            sent = res["sentinel"]
            print(f"   [T+{step:02d}s] Sentinel Score: {sent['score']} | Mitigação Ativa: {mit['active']} | "
                  f"Pool: {mit['pool_capacity']} slots | Erros: {sre['technical_errors_count']} | "
                  f"Error Budget: {sre['error_budget_remaining_pct']}%", flush=True)
            if mit["active"]:
                print("   ⚡ Mitigação engatada com sucesso!", flush=True)
                break

        # Coleta 2 segundos adicionais pós-mitigação para estabilização
        time.sleep(2.0)

        # 5. Verificações Finais de Auditoria
        final_res = client.get("/telemetry/live").json()
        final_mit = final_res["mitigation"]
        final_sre = final_res["sre_governance"]

        print("\n" + "=" * 70, flush=True)
        print("📊 RELATÓRIO DE AUDITORIA DO AGENTE ATUADOR:", flush=True)
        print(f"   • Sentinel Detectou e Disparou Mitigação: {final_mit['active']}", flush=True)
        print(f"   • Pool Autoscaling (Predictive HPA): {final_mit['pool_capacity']} slots", flush=True)
        print(f"   • Erros Técnicos Gerados (503/504): {final_sre['technical_errors_count']}", flush=True)
        print(f"   • Error Budget Preservado: {final_sre['error_budget_remaining_pct']}%", flush=True)
        print(f"   • SLI de Disponibilidade: {final_sre['current_sli_availability_pct']}%", flush=True)
        print(f"   • Alarme SRE Tradicional Acordou?: {final_sre['traditional_alert_triggered']}", flush=True)
        print("=" * 70, flush=True)

        assert final_mit["active"] is True, "O agente de mitigação deveria estar ativo!"
        assert final_mit["pool_capacity"] == 60, "O pool deveria ter sofrido autoscaling para 60 slots!"
        assert final_sre["technical_errors_count"] <= 2, f"Erros ({final_sre['technical_errors_count']}) excederam limite aceitável de 2!"
        assert final_sre["error_budget_remaining_pct"] >= 95.0, f"Error budget ({final_sre['error_budget_remaining_pct']}%) caiu abaixo de 95%!"
        print("\n✅ SUCESSO: Fechamento de ciclo comprovado matematicamente e operacionalmente!", flush=True)

if __name__ == "__main__":
    try:
        test_closed_loop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Falha no teste: {e}", flush=True)
        sys.exit(1)
