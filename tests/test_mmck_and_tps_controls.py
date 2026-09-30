"""
tests/test_mmck_and_tps_controls.py - Bateria de testes para Simulação Estocástica M/M/c/K e Controle Contínuo de TPS
Valida a física teórica de filas (solução exata em forma fechada), os endpoints REST de controle de carga e o payload de telemetria.
"""

import asyncio
import unittest
from fastapi.testclient import TestClient

from app import app, sim_env, calculate_mmck_metrics, build_telemetry_payload, antifraud_pool


class TestMMcKAndTpsControls(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Reseta sim_env para parâmetros base
        sim_env.target_tps = 120.0
        sim_env.stochastic_mode = True
        sim_env.system_capacity_k = 60
        sim_env.antifraud_latency_base_ms = 45.0
        antifraud_pool.reset_capacity(30)

    def test_mmck_theoretical_solver_nominal(self):
        """Valida que o cálculo analítico M/M/c/K produz métricas coerentes em regime nominal."""
        arrival_rate = 120.0  # lambda = 120 TPS
        service_rate = 1000.0 / 45.0  # mu = ~22.22 req/s por servidor
        c = 30  # c = 30 servidores
        K = 60  # K = 60 capacidade total

        metrics = calculate_mmck_metrics(arrival_rate, service_rate, c, K)

        self.assertEqual(metrics["arrival_rate_tps"], 120.0)
        self.assertEqual(metrics["servers_c"], 30)
        self.assertEqual(metrics["capacity_k"], 60)
        
        # rho = lambda / (c * mu) = 120 / (30 * 22.222) = 120 / 666.67 = ~0.18 (18%)
        self.assertAlmostEqual(metrics["traffic_intensity_rho"], 0.18, places=2)
        
        # Em regime nominal leve (rho = 18%), probabilidade de perda em buffer K=60 deve ser praticamente 0
        self.assertLess(metrics["p_loss_ratio"], 0.001)
        self.assertLess(metrics["p_loss_pct"], 0.1)
        
        # Espera na fila e tamanho médio de fila devem ser pequenos e finitos
        self.assertGreaterEqual(metrics["l_q_expected"], 0.0)
        self.assertGreaterEqual(metrics["w_q_ms_expected"], 0.0)
        self.assertLess(metrics["w_q_ms_expected"], 10.0)

    def test_mmck_theoretical_solver_saturation(self):
        """Valida que o cálculo analítico M/M/c/K lida corretamente com sobrecarga e saturação."""
        arrival_rate = 400.0  # lambda alto
        service_rate = 1000.0 / 255.0  # mu lento = 3.92 req/s por servidor
        c = 30  # c = 30
        K = 40  # K pequeno para forçar bloqueio

        metrics = calculate_mmck_metrics(arrival_rate, service_rate, c, K)

        # Sobrecarga: rho > 1
        self.assertGreater(metrics["traffic_intensity_rho"], 1.0)
        # Com buffer finito e sobrecarga, probabilidade de perda P_loss deve ser positiva e expressiva
        self.assertGreater(metrics["p_loss_pct"], 0.0)
        self.assertLessEqual(metrics["p_loss_pct"], 100.0)
        # Taxa efetiva deve ser menor que a taxa de chegada
        self.assertLess(metrics["lambda_effective_tps"], arrival_rate)

    def test_mmck_edge_cases(self):
        """Valida casos de borda do solucionador M/M/c/K."""
        m_zero = calculate_mmck_metrics(0.0, 20.0, 30, 60)
        self.assertEqual(m_zero["traffic_intensity_rho"], 0.0)
        self.assertEqual(m_zero["p_loss_pct"], 0.0)

        m_invalid = calculate_mmck_metrics(-10.0, -5.0, 30, 20)
        self.assertEqual(m_invalid["traffic_intensity_rho"], 0.0)

    def test_get_load_config_endpoint(self):
        """Valida GET /admin/load/config retornando a configuração e métricas M/M/c/K."""
        res = self.client.get("/admin/load/config")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertIn("target_tps", data)
        self.assertIn("stochastic_mode", data)
        self.assertIn("system_capacity_k", data)
        self.assertIn("servers_c", data)
        self.assertIn("mmck_metrics", data)
        
        self.assertEqual(data["target_tps"], 120.0)
        self.assertTrue(data["stochastic_mode"])
        self.assertEqual(data["servers_c"], 30)
        self.assertEqual(data["system_capacity_k"], 60)
        self.assertIn("traffic_intensity_rho", data["mmck_metrics"])

    def test_set_target_tps_endpoint(self):
        """Valida POST /admin/load/tps definindo novo TPS com clamping correto."""
        # Define 200 TPS
        res = self.client.post("/admin/load/tps?tps=200")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["target_tps"], 200.0)
        self.assertEqual(sim_env.target_tps, 200.0)

        # Clamping superior (máx 500 TPS)
        res_high = self.client.post("/admin/load/tps?tps=9999")
        self.assertEqual(res_high.status_code, 200)
        self.assertEqual(res_high.json()["target_tps"], 500.0)

        # Clamping inferior (mín 10 TPS)
        res_low = self.client.post("/admin/load/tps?tps=-50")
        self.assertEqual(res_low.status_code, 200)
        self.assertEqual(res_low.json()["target_tps"], 10.0)

    def test_adjust_target_tps_endpoint(self):
        """Valida POST /admin/load/adjust somando/subtraindo delta do TPS."""
        sim_env.target_tps = 120.0
        
        # Aumenta 50
        res_inc = self.client.post("/admin/load/adjust?delta=50")
        self.assertEqual(res_inc.status_code, 200)
        self.assertEqual(res_inc.json()["target_tps"], 170.0)

        # Reduz 30
        res_dec = self.client.post("/admin/load/adjust?delta=-30")
        self.assertEqual(res_dec.status_code, 200)
        self.assertEqual(res_dec.json()["target_tps"], 140.0)

    def test_toggle_stochastic_mode_endpoint(self):
        """Valida alternância entre Simulação Estocástica M/M/c/K e Determinística."""
        sim_env.stochastic_mode = True
        
        res1 = self.client.post("/admin/load/toggle_stochastic")
        self.assertEqual(res1.status_code, 200)
        self.assertFalse(res1.json()["stochastic_mode"])
        self.assertFalse(sim_env.stochastic_mode)

        res2 = self.client.post("/admin/load/toggle_stochastic")
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.json()["stochastic_mode"])
        self.assertTrue(sim_env.stochastic_mode)

    def test_telemetry_payload_contains_load_config(self):
        """Valida que o payload gerado por build_telemetry_payload inclui load_config e mmck_metrics."""
        async def run_test():
            sim_env.target_tps = 180.0
            sim_env.stochastic_mode = True
            payload = await build_telemetry_payload()
            
            self.assertIn("load_config", payload)
            lc = payload["load_config"]
            self.assertEqual(lc["target_tps"], 180.0)
            self.assertTrue(lc["stochastic_mode"])
            self.assertIn("M/M/c/K", lc["mode_label"])
            self.assertIn("mmck_metrics", lc)
            
            # Valida que o grafo topológico reflete o target TPS dinâmico
            topo = payload["topology"]
            gw_node = next(n for n in topo["nodes"] if n["id"] == "gateway")
            self.assertEqual(gw_node["load"], "180 TPS")
            self.assertEqual(topo["edges"][0]["tps"], 180)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
