"""Regression tests for the v0.6 Cybersecurity Grant submission package."""

import os
import re
import unittest


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EN_PATH = os.path.join(BASE_DIR, "proposal", "form_answers_EN.md")
PT_PATH = os.path.join(BASE_DIR, "proposal", "form_answers_PT.md")


class TestProposalConsistency(unittest.TestCase):
    def setUp(self):
        with open(EN_PATH, encoding="utf-8") as source:
            self.en_text = source.read()
        with open(PT_PATH, encoding="utf-8") as source:
            self.pt_text = source.read()

    def test_submission_files_and_briefs_exist(self):
        self.assertGreater(len(self.en_text), 5_000)
        self.assertGreater(len(self.pt_text), 5_000)
        for relative_path in (
            "proposal/ARKHE_CYBERSECURITY_GRANT_v0.6_EN.md",
            "proposal/ARKHE_CYBERSECURITY_GRANT_v0.6_PT.md",
        ):
            self.assertTrue(os.path.exists(os.path.join(BASE_DIR, relative_path)))

    def test_problem_statements_respect_200_word_limit(self):
        match_en = re.search(
            r"## Field 3: Problem Statement\n\n(.*?)\n\n\*\(Word count:",
            self.en_text,
            re.DOTALL,
        )
        match_pt = re.search(
            r"## Campo 3: Descrição do Problema\n\n(.*?)\n\n\*\(Contagem de palavras:",
            self.pt_text,
            re.DOTALL,
        )
        self.assertIsNotNone(match_en)
        self.assertIsNotNone(match_pt)
        self.assertLessEqual(len(match_en.group(1).split()), 200)
        self.assertLessEqual(len(match_pt.group(1).split()), 200)

    def test_complete_proposals_respect_3000_word_limit(self):
        match_en = re.search(
            r"## Field 4: Complete Project Proposal\n\n(.*?)\n\n## Field 5:",
            self.en_text,
            re.DOTALL,
        )
        match_pt = re.search(
            r"## Campo 4: Proposta Completa\n\n(.*?)\n\n## Campo 5:",
            self.pt_text,
            re.DOTALL,
        )
        self.assertIsNotNone(match_en)
        self.assertIsNotNone(match_pt)
        self.assertLessEqual(len(match_en.group(1).split()), 3_000)
        self.assertLessEqual(len(match_pt.group(1).split()), 3_000)

    def test_v06_scope_is_aligned_across_languages(self):
        shared_tokens = (
            "200",
            "persistent_memory_poisoning",
            "cross_agent_delegation_confusion",
            "skill_mcp_supply_chain_compromise",
            "authorization_identity_drift",
            "gpt-6.1-sol",
            "gpt-6-astra",
            "15",
            "10,000",
        )
        for token in shared_tokens:
            self.assertIn(token, self.en_text)
        for token in shared_tokens[:-1] + ("10.000",):
            self.assertIn(token, self.pt_text)

    def test_budget_is_balanced_and_independence_is_funded(self):
        for token in ("5,700", "3,000", "300", "1,000"):
            self.assertIn(token, self.en_text)
        for token in ("5.700", "3.000", "300", "1.000"):
            self.assertIn(token, self.pt_text)
        self.assertIn("independent case author/test custodian", self.en_text.lower())
        self.assertIn("autor independente", self.pt_text.lower())

    def test_evidence_boundary_is_explicit(self):
        for text in (self.en_text, self.pt_text):
            self.assertIn("reproducibility_only", text)
            self.assertIn("claim_eligibility: none", text)
            self.assertIn("confirmatory_claims_allowed: false", text)
            self.assertIn("268", text)
        self.assertIn("did not establish comparative effectiveness", self.en_text)
        self.assertIn("não eficácia comparativa", self.pt_text)

    def test_v06_is_described_as_planned_not_completed(self):
        self.assertIn("No v0.6 dataset", self.en_text)
        self.assertIn("Não existem dataset", self.pt_text)
        self.assertIn("currently individual", self.en_text)
        self.assertIn("atualmente individual", self.pt_text)

    def test_v06_uses_a_sealed_external_test_without_test_calibration(self):
        self.assertIn("one sealed external test set", self.en_text)
        self.assertIn("no v0.6 case, label, or prediction is used for calibration", self.en_text)
        self.assertIn("um único conjunto de teste externo selado", self.pt_text)
        self.assertIn("nenhum caso, rótulo ou predição da v0.6 será usado para calibração", self.pt_text)
        self.assertNotIn("leave-one-family-out", self.en_text)
        self.assertNotIn("quatro folds leave-one-family-out", self.pt_text)

    def test_sample_size_is_powered_and_not_outcome_adaptive(self):
        self.assertIn("200 independently authored synthetic trajectories", self.en_text)
        self.assertIn("200 trajetórias sintéticas produzidas independentemente", self.pt_text)
        self.assertIn("83.64% power", self.en_text)
        self.assertIn("poder de 83,64%", self.pt_text)
        self.assertIn("no outcome-driven sample expansion", self.en_text)
        self.assertIn("Não haverá expansão da amostra orientada pelos resultados", self.pt_text)
        self.assertNotIn("pre-specified recall target", self.en_text)
        self.assertNotIn("meta de recall pré-especificada", self.pt_text)

    def test_timeline_seals_manifest_after_case_authoring(self):
        self.assertLess(self.en_text.index("before test authoring"), self.en_text.index("signed test-manifest hash"))
        self.assertLess(self.pt_text.index("antes da autoria dos testes"), self.pt_text.index("hash do manifesto assinado"))

    def test_current_models_replace_stale_primary_models(self):
        self.assertNotIn("gpt-4o-mini-2024-07-18", self.en_text)
        self.assertNotIn("gpt-4o-mini-2024-07-18", self.pt_text)
        self.assertIn("Structured Outputs", self.en_text)
        self.assertIn("Structured Outputs", self.pt_text)

    def test_timeline_is_eight_weeks(self):
        self.assertIn("Week 8", self.en_text)
        self.assertIn("Semana 8", self.pt_text)
        self.assertNotIn("6 Months", self.en_text)
        self.assertNotIn("6 Meses", self.pt_text)
        self.assertIn("Weeks 3–5", self.en_text)
        self.assertIn("Semanas 3–5", self.pt_text)

    def test_prohibited_claims_are_absent(self):
        prohibited = (
            "endorsed by openai",
            "official partnership with openai",
            "production proof",
            "proven in production",
            "zero label leakage",
            "guaranteed peer review",
            "apoiado pela openai",
            "parceria oficial com a openai",
            "provada em produção",
            "vazamento zero de rótulos",
            "revisão por pares garantida",
        )
        combined = (self.en_text + "\n" + self.pt_text).lower()
        for phrase in prohibited:
            self.assertNotIn(phrase, combined)

    def test_submission_requires_human_approval(self):
        self.assertIn("Not submitted", self.en_text)
        self.assertIn("Não submetido", self.pt_text)
        self.assertIn("applicant approves", self.en_text)
        self.assertIn("aprovação final do proponente", self.pt_text)


if __name__ == "__main__":
    unittest.main()
