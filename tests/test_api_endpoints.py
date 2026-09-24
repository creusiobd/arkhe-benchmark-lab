import unittest
from fastapi.testclient import TestClient
from app import app, sim_env

class TestApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        # Reset de simulação antes de cada teste
        self.client.post("/admin/chaos/reset")

    def test_cockpit_html_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("ARKHÉ", response.text)

    def test_telemetry_as_of_endpoint(self):
        response = self.client.get("/telemetry/as_of")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("timestamp", data)
        self.assertIn("resources", data)
        self.assertIn("queueing", data)
        self.assertIn("traffic", data)
        self.assertIn("latency_ms", data)
        self.assertIn("outcomes", data)
        self.assertEqual(data["resources"]["antifraud_pool_capacity"], 30)

    def test_telemetry_live_endpoint(self):
        response = self.client.get("/telemetry/live")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("telemetry", data)
        self.assertIn("scenario", data)
        self.assertIn("sentinel", data)
        self.assertIn("sre_governance", data)
        self.assertIn("mitigation", data)
        self.assertIn("recent_journeys", data)

    def test_chaos_scenario_trigger_and_reset(self):
        # Aciona cenário drift
        res = self.client.post("/admin/chaos/scenario/drift")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["scenario"], "drift")
        self.assertEqual(sim_env.current_scenario, "drift")

        # Reseta para nominal
        res_reset = self.client.post("/admin/chaos/reset")
        self.assertEqual(res_reset.status_code, 200)
        self.assertEqual(sim_env.current_scenario, "nominal")

    def test_mitigation_toggle(self):
        # Garante estado inicial desativado
        sim_env.mitigation_enabled = False
        
        # Toggle para ativar
        res = self.client.post("/admin/mitigation/toggle")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["mitigation_enabled"])

        # Toggle para desativar
        res2 = self.client.post("/admin/mitigation/toggle")
        self.assertEqual(res2.status_code, 200)
        self.assertFalse(res2.json()["mitigation_enabled"])

if __name__ == "__main__":
    unittest.main()
