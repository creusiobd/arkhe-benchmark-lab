import unittest
from unittest.mock import patch, mock_open
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

    def test_pov_report_route_when_file_exists(self):
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="<html>ARKHÉ CYBERNETIC RESILIENCE</html>")):
                res = self.client.get("/pov")
                self.assertEqual(res.status_code, 200)
                self.assertIn("ARKHÉ CYBERNETIC RESILIENCE", res.text)

    def test_pov_report_route_when_file_not_found(self):
        with patch("os.path.exists", return_value=False):
            res = self.client.get("/pov")
            self.assertEqual(res.status_code, 404)
            self.assertIn("Relatório PoV não gerado", res.text)


if __name__ == "__main__":
    unittest.main()
