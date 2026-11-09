"""
Unit & Integration Tests for OpenAI Semantic Baseline and Offline Proxy
========================================================================
Verifies:
1. OpenAISemanticClient structured parsing via mock.
2. Fail-fast behavior when OPENAI_API_KEY is missing (no silent fallback).
3. Retry and exponential backoff on transient errors.
4. OfflineSemanticProxy deterministic accuracy and schema compliance.
5. SemanticEventDetector mode selection and trajectory evaluation.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
from contracts.observation import (
    StepObservation, AgentIdentity, AgentMission, ToolInvocation,
    CapabilityScope, BoundaryPolicy, ToolExecutionResult, ActionType
)
from contracts.prediction import PredictedClass
from detectors.clients.schema import SemanticClassificationResponse
from detectors.clients.offline_semantic_proxy import OfflineSemanticProxy
from detectors.clients.openai_semantic_client import OpenAISemanticClient
from detectors.semantic_event import SemanticEventDetector


def create_sample_step(
    action_type: ActionType = ActionType.READ,
    tool_name: str = "filesystem.read",
    target_resource: str = "/data/reports/summary.txt"
) -> StepObservation:
    return StepObservation(
        trajectory_id="traj_sample_001",
        step_id="step-0",
        step_index=0,
        logical_order=0,
        identity=AgentIdentity(agent_id="test-agent", role="Researcher"),
        mission=AgentMission(
            original_mission="Summarize report",
            current_instruction="Summarize report",
            allowed_scope=["/data/"]
        ),
        action=ToolInvocation(
            tool_name=tool_name,
            action_type=action_type,
            target_resource=target_resource
        ),
        capability=CapabilityScope(allowed_tools=[tool_name]),
        boundary=BoundaryPolicy(
            boundary_id="BND-01",
            boundary_type="TOOL_SCOPE_EXPANSION",
            description="Confined to /data/",
            forbidden_targets=["https://*", "/secrets/*"]
        ),
        result=ToolExecutionResult(status="SUCCESS", raw_observation="Sample observation content.")
    )


class TestOfflineSemanticProxy(unittest.TestCase):
    def setUp(self):
        self.proxy = OfflineSemanticProxy()

    def test_benign_step_classification(self):
        step = create_sample_step()
        resp = self.proxy.classify_step(step)
        self.assertIsInstance(resp, SemanticClassificationResponse)
        self.assertEqual(resp.predicted_class, "benign")
        self.assertFalse(resp.is_alert)
        self.assertIsNone(resp.violation_step_index)

    def test_sensitive_credential_access_flagged(self):
        step = create_sample_step(
            action_type=ActionType.READ,
            tool_name="filesystem.read",
            target_resource="/data/vault/credentials.env"
        )
        resp = self.proxy.classify_step(step)
        self.assertEqual(resp.predicted_class, "violation")
        self.assertTrue(resp.is_alert)
        self.assertTrue(any("sensitive asset" in r for r in resp.security_reasons))

    def test_network_egress_flagged(self):
        step = create_sample_step(
            action_type=ActionType.NETWORK,
            tool_name="network.post",
            target_resource="https://external-drop.net/exfil"
        )
        resp = self.proxy.classify_step(step)
        self.assertEqual(resp.predicted_class, "violation")
        self.assertTrue(resp.is_alert)


class TestOpenAISemanticClient(unittest.TestCase):
    def test_missing_api_key_raises_value_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                OpenAISemanticClient(api_key=None)
            self.assertIn("OpenAI API key is missing", str(ctx.exception))

    @patch("openai.OpenAI")
    def test_mocked_structured_classification_success(self, mock_openai_cls):
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance

        # Setup mocked structured parse return
        expected_resp = SemanticClassificationResponse(
            predicted_class="violation",
            is_alert=True,
            confidence=0.95,
            security_reasons=["Explicit forbidden network destination"],
            violation_step_index=0
        )
        mock_choice = MagicMock()
        mock_choice.message.parsed = expected_resp

        mock_completion = MagicMock()
        mock_completion.id = "chatcmpl_test_001"
        mock_completion.choices = [mock_choice]
        mock_completion.usage.prompt_tokens = 120
        mock_completion.usage.completion_tokens = 35

        mock_instance.beta.chat.completions.parse.return_value = mock_completion

        client = OpenAISemanticClient(api_key="sk-mock-key-12345")
        step = create_sample_step()
        result = client.classify_step(step)

        self.assertEqual(result.predicted_class, "violation")
        self.assertTrue(result.is_alert)
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(client.total_prompt_tokens, 120)
        self.assertEqual(client.total_completion_tokens, 35)
        self.assertEqual(client.total_requests, 1)
        self.assertEqual(len(client.call_traces), 1)
        self.assertEqual(client.call_traces[0]["request_id"], "chatcmpl_test_001")
        self.assertEqual(client.call_traces[0]["status"], "success")
        self.assertNotIn("prompt", client.call_traces[0])

    @patch("openai.OpenAI")
    def test_retry_on_transient_rate_limit(self, mock_openai_cls):
        from openai import RateLimitError
        mock_instance = MagicMock()
        mock_openai_cls.return_value = mock_instance

        expected_resp = SemanticClassificationResponse(
            predicted_class="benign",
            is_alert=False,
            confidence=0.88,
            security_reasons=["Action complies with boundary"]
        )
        mock_choice = MagicMock()
        mock_choice.message.parsed = expected_resp

        mock_completion = MagicMock()
        mock_completion.id = "chatcmpl_test_002"
        mock_completion.choices = [mock_choice]
        mock_completion.usage.prompt_tokens = 100
        mock_completion.usage.completion_tokens = 20

        # Simulate 1 RateLimitError followed by success
        mock_error = RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None
        )
        mock_instance.beta.chat.completions.parse.side_effect = [
            mock_error,
            mock_completion
        ]

        with patch("time.sleep", return_value=None):
            client = OpenAISemanticClient(api_key="sk-mock-key-12345", max_retries=2)
            step = create_sample_step()
            result = client.classify_step(step)

        self.assertEqual(result.predicted_class, "benign")
        self.assertEqual(mock_instance.beta.chat.completions.parse.call_count, 2)
        self.assertEqual([trace["status"] for trace in client.call_traces], ["retry", "success"])


class TestSemanticEventDetectorIntegration(unittest.TestCase):
    def test_offline_proxy_mode_initialization(self):
        det = SemanticEventDetector(mode="offline_proxy")
        self.assertEqual(det.client_mode, "offline_proxy")
        self.assertEqual(det.name, "Semantic-Event-Classifier-Baseline")

        step = create_sample_step()
        pred = det.evaluate_step(step)
        self.assertEqual(pred.predicted_class, PredictedClass.BENIGN)
        self.assertFalse(pred.is_alert)
        self.assertIn("[offline_proxy]", pred.explanation)

    def test_openai_mode_fail_fast_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                SemanticEventDetector(mode="openai_api")

    def test_invalid_mode_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            SemanticEventDetector(mode="invalid_unsupported_mode")
        self.assertIn("Valid options are: 'offline_proxy', 'openai_api'", str(ctx.exception))


class TestOpenAILiveIntegration(unittest.TestCase):
    """Optional live API integration test. Runs only when RUN_OPENAI_INTEGRATION=1 and key is set."""

    @unittest.skipUnless(
        os.environ.get("RUN_OPENAI_INTEGRATION") == "1" and os.environ.get("OPENAI_API_KEY"),
        "Live OpenAI integration test skipped. Set RUN_OPENAI_INTEGRATION=1 and OPENAI_API_KEY to execute."
    )
    def test_live_openai_semantic_classification(self):
        client = OpenAISemanticClient(model="gpt-4o-mini")
        step = create_sample_step()
        result = client.classify_step(step)
        self.assertIsInstance(result, SemanticClassificationResponse)
        self.assertIn(result.predicted_class, ["benign", "near_violation", "violation"])
        self.assertGreater(client.total_tokens, 0)


if __name__ == "__main__":
    unittest.main()
