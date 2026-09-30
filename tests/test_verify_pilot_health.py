import unittest
from unittest.mock import MagicMock
from scripts.verify_pilot_health import run_preflight_checks

class TestVerifyPilotHealth(unittest.TestCase):
    def test_all_checks_pass(self):
        mock_client = MagicMock()
        
        # Mock responses
        res_telemetry = MagicMock(status_code=200)
        res_telemetry.json.return_value = {"observables": {"rho_pool": 0.12}}
        
        res_traces = MagicMock(status_code=200)
        res_metrics = MagicMock(status_code=200, text="arkhe_pool_occupancy_ratio 0.12")
        res_pres = MagicMock(status_code=200)
        
        def mock_get(url):
            if url == "/telemetry/as_of":
                return res_telemetry
            elif url == "/metrics":
                return res_metrics
            elif url == "/presentation":
                return res_pres
            return MagicMock(status_code=404)
            
        mock_client.get.side_effect = mock_get
        mock_client.post.return_value = res_traces
        
        exit_code = run_preflight_checks("http://mock-cluster:8080", client=mock_client)
        self.assertEqual(exit_code, 0)

    def test_checks_fail_on_down_service(self):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client.post.side_effect = Exception("Connection refused")
        
        exit_code = run_preflight_checks("http://mock-cluster:8080", client=mock_client)
        self.assertEqual(exit_code, 1)

if __name__ == "__main__":
    unittest.main()
