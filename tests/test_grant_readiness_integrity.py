"""Regression tests for grant-readiness provenance, metrics, and prediction contracts.

All observations constructed here are synthetic fixtures; these tests are not
empirical benchmark results.
"""

import hashlib
import json
import os
import re
import unittest

from pydantic import ValidationError

from contracts.observation import (
    ActionType,
    AgentIdentity,
    AgentMission,
    BoundaryPolicy,
    CapabilityScope,
    StepObservation,
    ToolExecutionResult,
    ToolInvocation,
    TrajectoryObservation,
)
from contracts.prediction import (
    AlertEmitted,
    AlertSeverity,
    PredictedClass,
    StepPrediction,
    TrajectoryPrediction,
)
from scripts.run_live_openai_pilot import LiveOpenAIExecutor


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def synthetic_trajectory() -> TrajectoryObservation:
    """Build a synthetic, label-free observation used only by this test."""
    trajectory_id = "semantic-fixture-opaque-source"
    steps = []
    for index in range(2):
        steps.append(
            StepObservation(
                trajectory_id=trajectory_id,
                step_id=f"step_{index}",
                step_index=index,
                logical_order=index,
                timestamp_iso=None,
                identity=AgentIdentity(agent_id="synthetic_agent", role="metrics_reader"),
                mission=AgentMission(
                    original_mission="collect synthetic metrics",
                    current_instruction="read local metrics",
                ),
                action=ToolInvocation(
                    tool_name="metrics_reader",
                    action_type=ActionType.READ,
                    target_resource="/synthetic/metrics",
                ),
                capability=CapabilityScope(allowed_tools=["metrics_reader"]),
                boundary=BoundaryPolicy(
                    boundary_id="synthetic_boundary",
                    boundary_type="SYNTHETIC_TEST",
                    description="synthetic fixture only",
                ),
                result=ToolExecutionResult(
                    status="SUCCESS", raw_observation="synthetic result"
                ),
            )
        )
    return TrajectoryObservation(trajectory_id=trajectory_id, steps=steps)


class StubLiveExecutor(LiveOpenAIExecutor):
    """API-free executor stub for testing prediction aggregation."""

    def execute_step_call(self, step, trajectory_id, split, repetition, traces_file):
        risk = 80.0 if step.step_index == 0 else 32.0
        flagged = step.step_index == 0
        prediction = StepPrediction(
            step_index=step.step_index,
            is_alert=flagged,
            predicted_class=PredictedClass.VIOLATION if flagged else PredictedClass.BENIGN,
            accumulated_trajectory_risk=risk,
            confidence=0.9,
            explanation="synthetic unit-test fixture",
            detector_name="Semantic-Event-Classifier-Baseline",
            detector_version="test",
        )
        trace = {
            "latency_ms": 12.0 if step.step_index == 0 else 7.0,
            "attempt_latencies_ms": [10.0, 12.0] if step.step_index == 0 else [7.0],
            "total_tokens": 15 if step.step_index == 0 else 11,
        }
        return prediction, trace


class TestGrantReadinessIntegrity(unittest.TestCase):
    def test_v04_hashes_match_files_report_and_freeze_policy(self):
        report_path = os.path.join(ROOT, "reports", "dataset_diversity_report_v0.4.json")
        policy_path = os.path.join(ROOT, "docs", "test_split_freeze_policy.md")
        with open(report_path, encoding="utf-8") as source:
            report = json.load(source)
        with open(policy_path, encoding="utf-8") as source:
            policy = source.read()

        rows = re.findall(
            r"\|\s*`(datasets/v0\.4_hard/[^`]+)`\s*\|\s*`([a-f0-9]{64})`",
            policy,
        )
        policy_hashes = dict(rows)
        self.assertEqual(len(policy_hashes), 6, "Freeze policy must list all six data files")

        for relative_path, policy_hash in policy_hashes.items():
            with open(os.path.join(ROOT, relative_path), "rb") as source:
                actual_hash = hashlib.sha256(source.read()).hexdigest()
            report_key = relative_path.replace("datasets/v0.4_hard/", "")
            report_hash = report["dataset_file_hashes"][report_key]
            self.assertEqual(actual_hash, report_hash, relative_path)
            self.assertEqual(actual_hash, policy_hash, relative_path)

    def test_v04_policy_discloses_test_exposure_and_internal_scope(self):
        path = os.path.join(ROOT, "docs", "test_split_freeze_policy.md")
        with open(path, encoding="utf-8") as source:
            text = source.read().lower()
        self.assertIn("exploratory", text)
        self.assertIn("test-split", text)
        self.assertIn("not an independent external", text)
        self.assertNotIn("n=5,000+", text)

    def test_trajectory_prediction_rejects_alert_from_another_trajectory(self):
        alert = AlertEmitted(
            alert_id="alert_fixture",
            trajectory_id="traj_other",
            detector_name="unit-test",
            detector_version="1.0.0",
            step_index=0,
            risk_score=80.0,
            threshold=50.0,
            severity=AlertSeverity.HIGH,
            explanation="synthetic fixture",
        )
        with self.assertRaises(ValidationError):
            TrajectoryPrediction(
                trajectory_id="traj_owner",
                detector_name="unit-test",
                detector_version="1.0.0",
                predicted_class=PredictedClass.VIOLATION,
                is_flagged=True,
                alerts=[alert],
            )

    def test_live_pilot_prediction_uses_opaque_id_and_real_aggregates(self):
        executor = object.__new__(StubLiveExecutor)
        prediction = executor.evaluate_trajectory(
            synthetic_trajectory(), "development", 1, None
        )

        self.assertNotEqual(prediction.trajectory_id, "semantic-fixture-opaque-source")
        self.assertTrue(prediction.alerts)
        self.assertTrue(
            all(event.trajectory_id == prediction.trajectory_id for event in prediction.alerts)
        )
        self.assertEqual(prediction.max_risk_score, 80.0)
        self.assertEqual(prediction.execution_time_ms, 29.0)
        self.assertEqual(prediction.tokens_used, 26)
        self.assertEqual(prediction.final_outcome, "violation_consummated")
        self.assertNotIn("ground_truth_class", prediction.model_dump())

    def test_proposal_protocol_uses_the_declared_primary_denominator(self):
        for relative_path, expected in (
            ("proposal/form_answers_EN.md", "84 non-violation trajectories"),
            ("proposal/form_answers_PT.md", "84 trajetórias sem violação"),
        ):
            with open(os.path.join(ROOT, relative_path), encoding="utf-8") as source:
                text = source.read()
            self.assertIn(expected, text)
            self.assertIn("docs/evaluation_protocol_v0.5.md", text)


if __name__ == "__main__":
    unittest.main()
