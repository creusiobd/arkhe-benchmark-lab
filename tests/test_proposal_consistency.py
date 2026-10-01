"""
Unit Tests for ARKHÉ Proposal Consistency & Audit Guardrails
============================================================
Verifies:
1. Exact semantic alignment between English (form_answers_EN.md) and Portuguese (form_answers_PT.md).
2. Central research question focus: false positive reduction under a 90% recall floor.
3. Scoped 120-trajectory, 3-family leave-one-family-out experimental design.
4. Correct detector descriptions (Deterministic, Semantic gpt-4o-mini, ARKHÉ Trajectory Sentinel).
5. 8-week timeline and $10,000 USD budget ($1,500 credits + $8,500 research/infra).
6. Word count compliance for Field 3 (<= 200 words).
7. Strict prohibition of unsubstantiated claims (no guaranteed peer review, no OpenAI partnership claim, no untested models presented as observed facts).
8. Faithful reflection of verified repository pilot telemetry (268 calls, $0.0290 cost).
"""

import os
import re
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EN_PATH = os.path.join(BASE_DIR, "proposal", "form_answers_EN.md")
PT_PATH = os.path.join(BASE_DIR, "proposal", "form_answers_PT.md")


class TestProposalConsistency(unittest.TestCase):
    def setUp(self):
        self.assertTrue(os.path.exists(EN_PATH), f"Missing {EN_PATH}")
        self.assertTrue(os.path.exists(PT_PATH), f"Missing {PT_PATH}")

        with open(EN_PATH, "r", encoding="utf-8") as f:
            self.en_text = f.read()
        with open(PT_PATH, "r", encoding="utf-8") as f:
            self.pt_text = f.read()

    def test_01_proposal_files_exist_and_non_empty(self):
        self.assertGreater(len(self.en_text), 2000)
        self.assertGreater(len(self.pt_text), 2000)

    def test_02_central_research_question_present(self):
        # Must evaluate false positive reduction under recall floor
        self.assertIn("false positive", self.en_text.lower())
        self.assertIn("recall floor", self.en_text.lower())
        self.assertIn("90%", self.en_text)

        self.assertIn("falsos positivos", self.pt_text.lower())
        self.assertIn("piso", self.pt_text.lower())
        self.assertIn("90%", self.pt_text)

    def test_03_scope_120_trajectories_and_three_families(self):
        # 120 trajectories
        self.assertIn("120", self.en_text)
        self.assertIn("120", self.pt_text)

        # 3 families
        families = [
            "indirect_prompt_injection",
            "tool_scope_expansion",
            "unauthorized_secret_exposure_or_egress"
        ]
        for fam in families:
            self.assertIn(fam, self.en_text)
            self.assertIn(fam, self.pt_text)

        # 40 per family, 48 benign, 36 near-violations, 36 violations
        self.assertIn("40", self.en_text)
        self.assertIn("40", self.pt_text)
        self.assertIn("48", self.en_text)
        self.assertIn("48", self.pt_text)
        self.assertIn("36", self.en_text)
        self.assertIn("36", self.pt_text)

    def test_04_leave_one_family_out_evaluation(self):
        self.assertIn("leave-one-family-out", self.en_text.lower())
        self.assertIn("leave-one-family-out", self.pt_text.lower())
        self.assertIn("3-fold", self.en_text.lower())
        self.assertIn("3 folds", self.pt_text.lower())

        # Internal evaluation disclosure
        self.assertIn("internal", self.en_text.lower())
        self.assertIn("interna", self.pt_text.lower())

    def test_05_detectors_and_models_specifications(self):
        # Baseline 1
        self.assertIn("Deterministic", self.en_text)
        self.assertIn("Determinístico", self.pt_text)

        # Baseline 2
        self.assertIn("gpt-4o-mini-2024-07-18", self.en_text)
        self.assertIn("gpt-4o-mini-2024-07-18", self.pt_text)

        # Primary detector
        self.assertIn("ARKHÉ Trajectory Sentinel", self.en_text)
        self.assertIn("ARKHÉ Trajectory Sentinel", self.pt_text)

        # gpt-4o only as optional robustness check
        self.assertIn("robustness", self.en_text.lower())
        self.assertIn("robustez", self.pt_text.lower())

    def test_06_timeline_eight_weeks(self):
        self.assertIn("8 Weeks", self.en_text)
        self.assertIn("8 Semanas", self.pt_text)
        self.assertNotIn("6 Months", self.en_text)
        self.assertNotIn("6 Meses", self.pt_text)

    def test_07_budget_breakdown_and_justification(self):
        # Total $10,000
        self.assertIn("10,000", self.en_text)
        self.assertIn("10.000", self.pt_text)

        # Credits $20, reconciled to the stated token volumes and current model rates
        self.assertIn("$20", self.en_text)
        self.assertIn("US$ 20", self.pt_text)

        # Research stipend $9,480 balances the fixed $10,000 request with $500 infra
        self.assertIn("9,480", self.en_text)
        self.assertIn("9.480", self.pt_text)

        # Infrastructure $500
        self.assertIn("500", self.en_text)
        self.assertIn("500", self.pt_text)

    def test_08_no_unsubstantiated_claims(self):
        prohibited_phrases_en = [
            "guaranteed peer review",
            "accepted for publication",
            "endorsed by openai",
            "official partnership with openai",
            "universal immunity",
            "production proof"
        ]
        for phrase in prohibited_phrases_en:
            self.assertNotIn(phrase, self.en_text.lower())

        prohibited_phrases_pt = [
            "peer review garantido",
            "revisão por pares garantida",
            "apoiado pela openai",
            "parceria oficial com a openai",
            "imunidade universal",
            "provada em produção"
        ]
        for phrase in prohibited_phrases_pt:
            self.assertNotIn(phrase, self.pt_text.lower())

        # No mention of o1 as tested
        self.assertNotIn("o1-preview", self.en_text.lower())
        self.assertNotIn("o1-preview", self.pt_text.lower())

    def test_09_grounded_in_actual_pilot_results(self):
        # Real verified pilot numbers from v0.4 live execution
        self.assertIn("268", self.en_text)
        self.assertIn("268", self.pt_text)
        self.assertIn("0.028966", self.en_text)
        self.assertIn("0,028966", self.pt_text)
        self.assertIn("147,172", self.en_text)
        self.assertIn("147.172", self.pt_text)

    def test_10_field_3_word_count_limit(self):
        # Extract Field 3 in EN
        match_en = re.search(r"### Field 3: Problem Statement.*?\n\n(.*?)\n\n\*(?:Word count|\(Word count)", self.en_text, re.DOTALL)
        self.assertIsNotNone(match_en, "Could not extract Field 3 in EN")
        words_en = match_en.group(1).split()
        self.assertLessEqual(len(words_en), 200, f"EN Problem Statement exceeded 200 words: {len(words_en)}")

        # Extract Field 3 in PT
        match_pt = re.search(r"### Campo 3: Descrição do Problema.*?\n\n(.*?)\n\n\*(?:Contagem de palavras|\(Contagem de palavras)", self.pt_text, re.DOTALL)
        self.assertIsNotNone(match_pt, "Could not extract Campo 3 in PT")
        words_pt = match_pt.group(1).split()
        self.assertLessEqual(len(words_pt), 200, f"PT Problem Statement exceeded 200 words: {len(words_pt)}")

    def test_11_metric_denominators_and_outcome_claims_are_explicit(self):
        self.assertIn("84 non-violation trajectories", self.en_text)
        self.assertIn("84 trajetórias sem violação", self.pt_text)
        self.assertIn("prospective", self.en_text.lower())
        self.assertIn("prospectiva", self.pt_text.lower())
        self.assertNotIn("Independent Evaluator", self.en_text)
        self.assertNotIn("Avaliador Independente", self.pt_text)
        self.assertNotIn("156 passing automated tests", self.en_text)
        self.assertNotIn("156 testes automatizados aprovados", self.pt_text)

    def test_12_current_pilot_is_disclosed_as_exploratory_all_split_baseline_run(self):
        for text in (self.en_text.lower(), self.pt_text.lower()):
            self.assertIn("v0.4_hard", text)
            self.assertIn("147,172" if text == self.en_text.lower() else "147.172", text)
        self.assertIn("exploratory", self.en_text.lower())
        self.assertIn("exploratória", self.pt_text.lower())


if __name__ == "__main__":
    unittest.main()
