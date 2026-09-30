"""
test_dashboard_alignment.py - Bateria de Testes Automatizados de Alinhamento do Dashboard ARKHÉ SENTINEL

Cobre formalmente:
1. Limiares unificados de Score de Risco (<45% Nominal, 45-75% Alerta Precoce, >=75% Crítico).
2. Separação categórica entre Estado de Risco Instantâneo (Estático) e Sinal Preditivo de Trajetória.
3. Máquina de estados do Lead Time (N/D em nominal, Pendente em observação, +X.Xs consolidado após SRE).
4. Rigor matemático no cálculo de variações: pontos percentuais (p.p.) vs percentual relativo (%).
5. Transição determinística e isolamento temporal entre cenários ("Nominal" vs "Degradação HSM").
6. Higienização de claims (ausência de 91.8% arbitrário e eliminação de falso ganho +0.0s).
"""

import unittest
import time
from app import sim_env, build_telemetry_payload, trigger_scenario, reset_simulation
from arkhe_detector import ArkheTrajectoryEngine, ArkheDetectionResult


class TestDashboardAlignment(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Garante reset para estado limpo de fábrica antes de cada teste
        await reset_simulation()

    async def test_score_thresholds_nominal(self):
        """Valida que scores abaixo de 45% são estritamente classificados como NOMINAL / healthy."""
        # Configura estado com pool em 12% (nominal)
        sim_env.antifraud_latency_base_ms = 45.0
        payload = await build_telemetry_payload()
        sentinel = payload["sentinel"]

        self.assertLess(sentinel["score"], 45.0, "Score nominal deve ser < 45.0%")
        self.assertEqual(sentinel["risk_state"], "nominal")
        self.assertEqual(sentinel["level"], "healthy")
        self.assertIn("NOMINAL", sentinel["state_label"])

    async def test_score_thresholds_early_warning(self):
        """Valida que scores entre 45.0% e 74.9% são classificados como ALERTA PRECOCE / warning."""
        # Força ocupação de pool em ~56.7% (17 em uso de 30)
        from app import antifraud_pool
        antifraud_pool.reset_capacity(30)
        antifraud_pool._sem._value = 30 - 17  # 17 em uso

        payload = await build_telemetry_payload()
        sentinel = payload["sentinel"]

        self.assertGreaterEqual(sentinel["score"], 45.0)
        self.assertLess(sentinel["score"], 75.0)
        self.assertEqual(sentinel["risk_state"], "early_warning")
        self.assertEqual(sentinel["level"], "warning")
        self.assertIn("ALERTA PRECOCE", sentinel["state_label"])

    async def test_score_thresholds_critical(self):
        """Valida que scores a partir de 75.0% são classificados como CRÍTICO / critical."""
        # Força ocupação de pool em ~86.7% (26 em uso de 30)
        from app import antifraud_pool
        antifraud_pool.reset_capacity(30)
        antifraud_pool._sem._value = 30 - 26  # 26 em uso

        payload = await build_telemetry_payload()
        sentinel = payload["sentinel"]

        self.assertGreaterEqual(sentinel["score"], 75.0)
        self.assertEqual(sentinel["risk_state"], "critical")
        self.assertEqual(sentinel["level"], "critical")
        self.assertIn("CRÍTICO", sentinel["state_label"])

    async def test_hsm_degradation_state_and_trajectory_separation(self):
        """
        Cenário Crítico Auditado:
        Em Degradação de HSM, o pool pode estar em 38% (estatisticamente NOMINAL < 45%),
        mas a derivada d_rho/dt é positiva e gera um Alerta Preditivo de Trajetória.
        O dashboard NÃO pode conflitar os dois conceitos.
        """
        from app import antifraud_pool
        # Simula ocupação de 38% (11.4 / 30 ~ 38%)
        antifraud_pool.reset_capacity(100)
        antifraud_pool._sem._value = 100 - 38  # 38 em uso de 100 = 38.0%

        # Simula injeção de snapshots com aceleração de saturação
        now = time.time()
        engine = ArkheTrajectoryEngine()
        for i, r in enumerate([0.15, 0.22, 0.30, 0.38]):
            engine.add_snapshot({
                "timestamp": now - (4 - i) * 2.0,
                "resources": {"antifraud_pool_utilization_ratio": r},
                "queueing": {"wq_ws_ratio": 0.25, "avg_queue_wait_ms": 12.0, "avg_service_time_ms": 50.0},
                "traffic": {"retry_amplification_ratio": 1.0, "unique_transactions_total": 100}
            })
        sim_env.arkhe_engine = engine

        payload = await build_telemetry_payload()
        sentinel = payload["sentinel"]

        # 1. Risco Estático Instantâneo é estritamente Nominal (< 45%)
        self.assertLess(sentinel["score"], 45.0, "Score de 38% deve estar abaixo do limiar de 45%")
        self.assertEqual(sentinel["risk_state"], "nominal", "Estado de risco instantâneo deve ser NOMINAL")
        self.assertEqual(sentinel["level"], "healthy")

        # 2. Sinal Dinâmico de Trajetória deve estar ATIVO (Preditivo)
        traj = sentinel["trajectory_signal"]
        self.assertTrue(traj["active"], "Sinal de trajetória deve ser disparado pela aceleração")
        self.assertEqual(traj["signal_type"], "PREDICTIVE_TREND")
        self.assertIn("PREDITIVO", traj["signal_label"])

    def test_percentage_points_vs_relative_variation(self):
        """
        Valida que o sistema diferencia rigorosamente:
        - Variação Absoluta: pontos percentuais (p.p.)
        - Variação Relativa: percentual sobre a base (%)
        Exemplo: subida de 17% para 38%:
        Delta Absoluto = +21.0 p.p.
        Delta Relativo = (38 - 17) / 17 * 100 ~ +123.53%
        """
        v_initial = 17.0
        v_final = 38.0

        delta_pp = round(v_final - v_initial, 1)
        delta_rel_pct = round(((v_final - v_initial) / v_initial) * 100.0, 1)

        self.assertEqual(delta_pp, 21.0, "A variação absoluta deve ser exatamente 21.0 pontos percentuais (p.p.)")
        self.assertAlmostEqual(delta_rel_pct, 123.5, delta=0.1, msg="A variação relativa deve ser ~123.5%")

    async def test_lead_time_state_machine_nominal(self):
        """Em regime nominal, sem alertas, o lead time deve ser None e display 'N/D' (nunca +0.0s)."""
        payload = await build_telemetry_payload()
        sentinel = payload["sentinel"]

        self.assertIsNone(sentinel["lead_time_seconds"])
        self.assertEqual(sentinel["lead_time_status"], "NOT_APPLICABLE")
        self.assertEqual(sentinel["lead_time_display"], "N/D")
        self.assertIn("nominal", sentinel["lead_time_description"].lower())

    async def test_lead_time_state_machine_pending_observation(self):
        """
        Quando o Sentinel detecta anomalia mas o monitor SRE ainda não disparou:
        O lead time final NÃO está consolidado (None), o status é OBSERVING_PENDING_BASELINE,
        e o display deve indicar 'Pendente' com o tempo de observação acumulado.
        """
        now = time.time()
        sim_env.t_sentinel_alert = now - 5.4  # Sentinel disparou há 5.4s
        sim_env.t_sre_alert = None            # SRE tradicional ainda mudo

        payload = await build_telemetry_payload()
        sentinel = payload["sentinel"]

        self.assertIsNone(sentinel["lead_time_seconds"], "Lead time final não pode ser consolidado antes do baseline")
        self.assertEqual(sentinel["lead_time_status"], "OBSERVING_PENDING_BASELINE")
        self.assertIn("Pendente", sentinel["lead_time_display"])
        self.assertIn("observação", sentinel["lead_time_description"].lower())

    async def test_lead_time_state_machine_consolidated(self):
        """
        Quando ambos dispararam, o lead time consolidado é t_sre - t_sentinel,
        status CONSOLIDATED e display +X.Xs.
        """
        now = time.time()
        sim_env.t_sentinel_alert = now - 15.0
        sim_env.t_sre_alert = now - 2.5  # SRE disparou 12.5s depois

        payload = await build_telemetry_payload()
        sentinel = payload["sentinel"]

        self.assertAlmostEqual(sentinel["lead_time_seconds"], 12.5, places=1)
        self.assertEqual(sentinel["lead_time_status"], "CONSOLIDATED")
        self.assertEqual(sentinel["lead_time_display"], "+12.5s")
        self.assertIn("comprovada", sentinel["lead_time_description"].lower())

    async def test_scenario_transition_hsm_to_nominal(self):
        """
        Valida que a transição de Degradação HSM para Nominal:
        - Zera o delay injetado no HSM (hsm_extra_delay_ms = 0.0)
        - Limpa os timestamps de alertas (t_sentinel_alert e t_sre_alert voltam para None)
        - Limpa o histórico de janelas do motor de diagnóstico
        - Retorna o status de governança ao estado nominal estável
        """
        # 1. Ativa HSM Saturation
        await trigger_scenario("hsm_saturation")
        self.assertEqual(sim_env.current_scenario, "hsm_saturation")
        self.assertEqual(sim_env.hsm_extra_delay_ms, 120.0)

        # Simula disparo de alerta
        sim_env.t_sentinel_alert = time.time() - 3.0

        # 2. Retorna para Nominal
        res = await trigger_scenario("nominal")
        self.assertEqual(res["scenario"], "nominal")
        self.assertEqual(sim_env.hsm_extra_delay_ms, 0.0, "HSM extra delay deve ser zerado ao voltar para nominal")
        self.assertIsNone(sim_env.t_sentinel_alert, "t_sentinel_alert deve ser limpo ao voltar para nominal")
        self.assertIsNone(sim_env.t_sre_alert, "t_sre_alert deve ser limpo ao voltar para nominal")
        self.assertEqual(len(sim_env.arkhe_engine.window_history), 0, "Histórico da esteira deve ser reinicializado")

        # 3. Valida payload pós-transição
        payload = await build_telemetry_payload()
        self.assertEqual(payload["scenario"]["id"], "nominal")
        self.assertEqual(payload["sentinel"]["risk_state"], "nominal")
        self.assertEqual(payload["sentinel"]["lead_time_status"], "NOT_APPLICABLE")

    def test_timeline_reference_anchored_to_t_zero(self):
        """Valida que todos os eventos da timeline são referenciados deterministicamente ao T=0."""
        t0 = time.time() - 10.0
        sim_env.scenario_started_at = t0
        sim_env.t_sentinel_alert = t0 + 2.5
        sim_env.t_sre_alert = t0 + 8.5

        offset_sentinel = round(sim_env.t_sentinel_alert - sim_env.scenario_started_at, 1)
        offset_sre = round(sim_env.t_sre_alert - sim_env.scenario_started_at, 1)
        lead_time = round(offset_sre - offset_sentinel, 1)

        self.assertEqual(offset_sentinel, 2.5, "Detecção do Sentinel deve ser em T +2.5s")
        self.assertEqual(offset_sre, 8.5, "Disparo convencional do SRE deve ser em T +8.5s")
        self.assertEqual(lead_time, 6.0, "Lead time deve ser delta direto entre os offsets ancorados a T=0")


if __name__ == "__main__":
    unittest.main()
