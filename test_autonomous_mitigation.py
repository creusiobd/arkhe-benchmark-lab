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

        # 4. Observar atuação autônoma durante 6 segundos de tráfego
        print("4. Aguardando 6 segundos sob tráfego simultâneo para atuação do Mitigador...")
        for i in range(6):
            time.sleep(1.0)
            res = client.get("/telemetry/live").json()
            mit = res["mitigation"]
            sre = res["sre_governance"]
            sent = res["sentinel"]
            print(f"   [T+{i+1}s] Sentinel Score: {sent['score']} | Mitigação Ativa: {mit['active']} | "
                  f"Pool: {mit['pool_capacity']} slots | Erros: {sre['technical_errors_count']} | "
                  f"Error Budget: {sre['error_budget_remaining_pct']}%")

        # 5. Verificações Finais de Auditoria
        final_res = client.get("/telemetry/live").json()
        final_mit = final_res["mitigation"]
        final_sre = final_res["sre_governance"]

        print("\n" + "=" * 70)
        print("📊 RELATÓRIO DE AUDITORIA DO AGENTE ATUADOR:")
        print(f"   • Sentinel Detectou e Disparou Mitigação: {final_mit['active']}")
        print(f"   • Pool Autoscaling (Predictive HPA): {final_mit['pool_capacity']} slots")
        print(f"   • Erros Técnicos Gerados (503/504): {final_sre['technical_errors_count']}")
        print(f"   • Error Budget Preservado: {final_sre['error_budget_remaining_pct']}%")
        print(f"   • SLI de Disponibilidade: {final_sre['current_sli_availability_pct']}%")
        print(f"   • Alarme SRE Tradicional Acordou?: {final_sre['traditional_alert_triggered']}")
        print("=" * 70)

        assert final_mit["active"] is True, "O agente de mitigação deveria estar ativo!"
        assert final_mit["pool_capacity"] == 60, "O pool deveria ter sofrido autoscaling para 60 slots!"
        assert final_sre["technical_errors_count"] == 0, "Zero erros deveriam ter ocorrido!"
        assert final_sre["error_budget_remaining_pct"] == 100.0, "O Error Budget deveria estar 100% intacto!"
        print("\n✅ SUCESSO: Fechamento de ciclo comprovado matematicamente e operacionalmente!")

if __name__ == "__main__":
    try:
        test_closed_loop()
    except Exception as e:
        print(f"❌ Falha no teste: {e}")
        sys.exit(1)
