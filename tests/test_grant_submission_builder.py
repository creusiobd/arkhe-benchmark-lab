import unittest
from pathlib import Path

from scripts.build_openai_grant_submission import build_submission, normalize_linkedin

BASE_DIR = Path(__file__).resolve().parents[1]
SOURCE = (BASE_DIR / "proposal" / "form_answers_EN.md").read_text(encoding="utf-8")


class TestGrantSubmissionBuilder(unittest.TestCase):
    def test_builds_form_ordered_private_packet(self):
        packet = build_submission(
            source=SOURCE,
            first_name="Test",
            last_name="Applicant",
            email="test@example.org",
            linkedin="www.linkedin.com/in/test-applicant",
            role="Independent Researcher",
        )
        self.assertIn("PRIVATE", packet)
        self.assertIn("Email: test@example.org", packet)
        self.assertIn("https://www.linkedin.com/in/test-applicant", packet)
        self.assertIn("ARKHÉ v0.6", packet)
        self.assertIn("USD 5,000 direct funding plus USD 300", packet)
        self.assertIn("Submission requires the applicant's explicit approval", packet)

    def test_rejects_invalid_contact_values(self):
        with self.assertRaises(ValueError):
            build_submission(
                source=SOURCE,
                first_name="Test",
                last_name="Applicant",
                email="invalid",
                linkedin="www.linkedin.com/in/test-applicant",
                role="Researcher",
            )
        with self.assertRaises(ValueError):
            normalize_linkedin("https://example.org/profile")


if __name__ == "__main__":
    unittest.main()
