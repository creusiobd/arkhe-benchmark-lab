import unittest
from fastapi.testclient import TestClient
from app import app

class TestPresentationEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_presentation_route(self):
        res = self.client.get("/presentation")
        self.assertEqual(res.status_code, 200)
        self.assertIn("ARKHÉ — Executive Pitch Deck", res.text)
        self.assertIn("lyapunovCanvas", res.text)

    def test_pitch_alias_route(self):
        res = self.client.get("/pitch")
        self.assertEqual(res.status_code, 200)
        self.assertIn("ARKHÉ — Executive Pitch Deck", res.text)

    def test_pov_report_route(self):
        res = self.client.get("/pov")
        # Should be 200 since arkhe_pov_executive_summary.html was generated
        self.assertEqual(res.status_code, 200)
        self.assertIn("ARKHÉ CYBERNETIC RESILIENCE", res.text)

if __name__ == "__main__":
    unittest.main()
