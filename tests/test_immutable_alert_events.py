"""
ARKHÉ Agent Boundary Defense Benchmark — Immutable Alert Events Tests
=====================================================================
Comprehensive tests validating the append-only, immutable event contracts:
1. AlertEmitted is strictly frozen (mutation raises ValidationError).
2. AlertResolved and ContainmentAttempted are strictly frozen.
3. Resolution and Containment reference AlertEmitted without mutating it.
4. Stream of alerts up to step t is invariant between full and partial trajectories.
5. Idempotent reprocessing generates deterministic IDs and prevents duplicate alerts.
6. Missing timestamps are strictly preserved as None without artificial defaults.
7. Validation rejects malformed, incomplete, or negative-indexed events.
8. Serialization and deserialization roundtrip preserve frozen semantics and fields.
9. Zero ground truth or editorial labels leak into event contracts.
10. Backward-compatible aliases (AlertEvent, ResolutionEvent, ContainmentEvent) are preserved.
"""

import unittest
import json
from typing import Optional, List, Dict, Any
from pydantic_core import ValidationError

from contracts.observation import (
    StepObservation, TrajectoryObservation, AgentIdentity, AgentMission,
    ToolInvocation, ActionType, CapabilityScope, BoundaryPolicy, ToolExecutionResult
)
from contracts.prediction import (
    AlertEmitted, AlertResolved, ContainmentAttempted,
    AlertEvent, ResolutionEvent, ContainmentEvent,
    AlertSeverity, FinalOutcome, StepPrediction, PredictedClass
)
from detectors.base import BaseDetector


def make_test_step(
    step_index: int,
    action_type: ActionType = ActionType.READ,
    target: str = "/data/vault",
    status: str = "SUCCESS",
    timestamp: Optional[str] = None
) -> StepObservation:
    """Helper creating declared synthetic observable steps for unit testing."""
    return StepObservation(
        trajectory_id="traj_event_immutability_test",
        step_id=f"step_{step_index}",
        step_index=step_index,
        logical_order=step_index,
        timestamp_iso=timestamp,
        identity=AgentIdentity(agent_id="agent_alpha", role="data_collector"),
        mission=AgentMission(original_mission="collect metrics", current_instruction="read data"),
        action=ToolInvocation(tool_name="vault_reader", action_type=action_type, target_resource=target),
        capability=CapabilityScope(allowed_tools=["vault_reader"]),
        boundary=BoundaryPolicy(boundary_id="p1", boundary_type="POLICY", description="strict access"),
        result=ToolExecutionResult(status=status, raw_observation="data retrieved")
    )


class MockDetector(BaseDetector):
    """Programmable mock detector for testing event stream guarantees."""
    def __init__(self, step_verdicts: Dict[int, Dict[str, Any]]):
        self._verdicts = step_verdicts
        self.risk_threshold = 50.0

    @property
    def name(self) -> str:
        return "Mock-Immutable-Event-Detector"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def detection_mode(self) -> str:
        return "TRAJECTORY_AWARE"

    def evaluate_step(
        self,
        step: StepObservation,
        trajectory_history: Optional[List[StepObservation]] = None
    ) -> StepPrediction:
        s_idx = step.step_index
        v = self._verdicts.get(s_idx, {"is_alert": False, "risk": 10.0, "explanation": "nominal"})
        is_alert = v.get("is_alert", False)
        risk = v.get("risk", 10.0)
        expl = v.get("explanation", "nominal")

        return StepPrediction(
            step_index=s_idx,
            is_alert=is_alert,
            predicted_class=PredictedClass.VIOLATION if is_alert else PredictedClass.BENIGN,
            mission_divergence_score=0.2 if is_alert else 0.0,
            contamination_probability=0.1 if is_alert else 0.0,
            boundary_proximity=0.9 if is_alert else 0.1,
            state_change_score=0.3 if is_alert else 0.0,
            behavioral_persistence=0.4 if is_alert else 0.0,
            accumulated_trajectory_risk=risk,
            confidence=0.95 if is_alert else 0.8,
            explanation=expl,
            detector_name=self.name,
            detector_version=self.version
        )


class TestImmutableAlertEvents(unittest.TestCase):

    def test_alert_emitted_is_frozen_and_rejects_mutation(self):
        """1. Setting any attribute on AlertEmitted after creation must raise ValidationError."""
        alert = AlertEmitted(
            alert_id="alert_test_001",
            trajectory_id="traj_001",
            detector_name="MockDetector",
            detector_version="1.0.0",
            step_index=2,
            risk_score=82.5,
            threshold=50.0,
            severity=AlertSeverity.CRITICAL,
            evidence={"proximity": 0.95},
            explanation="Critical boundary approach observed"
        )

        with self.assertRaises(ValidationError):
            alert.risk_score = 10.0

        with self.assertRaises(ValidationError):
            alert.step_index = 0

        with self.assertRaises(ValidationError):
            alert.severity = AlertSeverity.LOW

        with self.assertRaises(ValidationError):
            alert.explanation = "Modified explanation"

    def test_alert_resolved_is_frozen_and_rejects_mutation(self):
        """2. Setting any attribute on AlertResolved must raise ValidationError."""
        res = AlertResolved(
            event_id="res_001",
            alert_id="alert_test_001",
            trajectory_id="traj_001",
            step_index=3,
            resolution_reason="NOMINAL_RECOVERY",
            evidence={"subsided": True}
        )

        with self.assertRaises(ValidationError):
            res.resolution_reason = "TAMPERED"

        with self.assertRaises(ValidationError):
            res.step_index = 1

    def test_containment_attempted_is_frozen_and_rejects_mutation(self):
        """3. Setting any attribute on ContainmentAttempted must raise ValidationError."""
        cnt = ContainmentAttempted(
            event_id="cnt_001",
            alert_id="alert_test_001",
            trajectory_id="traj_001",
            step_index=3,
            containment_attempted=True,
            containment_succeeded=True,
            action_taken="Blocked execution via policy sandbox",
            evidence={"status": "BLOCKED"}
        )

        with self.assertRaises(ValidationError):
            cnt.containment_succeeded = False

        with self.assertRaises(ValidationError):
            cnt.action_taken = "Modified action"

    def test_resolution_references_alert_without_mutating_alert(self):
        """4. Resolution event references alert_id while the original AlertEmitted remains untouched."""
        alert = AlertEmitted(
            alert_id="alert_test_immutable",
            trajectory_id="traj_test",
            detector_name="Mock",
            step_index=1,
            risk_score=75.0,
            threshold=50.0,
            explanation="Initial anomaly"
        )
        initial_dict = alert.model_dump()

        res = AlertResolved(
            event_id="res_001",
            alert_id=alert.alert_id,
            trajectory_id=alert.trajectory_id,
            step_index=2,
            resolution_reason="NOMINAL_RECOVERY"
        )

        self.assertEqual(res.alert_id, alert.alert_id)
        # Ensure AlertEmitted is 100% byte-for-byte identical
        self.assertEqual(alert.model_dump(), initial_dict)

    def test_containment_references_alert_without_mutating_alert(self):
        """5. Containment event references alert_id while the original AlertEmitted remains untouched."""
        alert = AlertEmitted(
            alert_id="alert_test_immutable",
            trajectory_id="traj_test",
            detector_name="Mock",
            step_index=1,
            risk_score=85.0,
            threshold=50.0,
            explanation="Initial anomaly"
        )
        initial_dict = alert.model_dump()

        cnt = ContainmentAttempted(
            event_id="cnt_001",
            alert_id=alert.alert_id,
            trajectory_id=alert.trajectory_id,
            step_index=2,
            action_taken="Containment via tool barrier"
        )

        self.assertEqual(cnt.alert_id, alert.alert_id)
        self.assertEqual(alert.model_dump(), initial_dict)

    def test_stream_invariance_partial_vs_full_execution(self):
        """6. The stream of AlertEmitted events up to step t must be identical in full and partial runs."""
        detector = MockDetector({
            0: {"is_alert": False, "risk": 10.0, "explanation": "nominal step 0"},
            1: {"is_alert": True, "risk": 78.0, "explanation": "boundary breach alert at step 1"},
            2: {"is_alert": True, "risk": 88.0, "explanation": "sustained hazard at step 2"},
            3: {"is_alert": False, "risk": 15.0, "explanation": "TRAJECTORY RECOVERY: nominal retreat"}
        })

        steps_full = [make_test_step(i) for i in range(4)]
        steps_partial_t1 = steps_full[:2]  # steps 0 and 1
        steps_partial_t2 = steps_full[:3]  # steps 0, 1, and 2

        traj_full = TrajectoryObservation(trajectory_id="traj_stream_inv", steps=steps_full)
        traj_t1 = TrajectoryObservation(trajectory_id="traj_stream_inv", steps=steps_partial_t1)
        traj_t2 = TrajectoryObservation(trajectory_id="traj_stream_inv", steps=steps_partial_t2)

        pred_full = detector.evaluate_trajectory(traj_full)
        pred_t1 = detector.evaluate_trajectory(traj_t1)
        pred_t2 = detector.evaluate_trajectory(traj_t2)

        # At t=1: exactly 1 alert
        self.assertEqual(len(pred_t1.alerts), 1)
        self.assertEqual(pred_t1.alerts[0].alert_id, pred_full.alerts[0].alert_id)
        self.assertEqual(pred_t1.alerts[0].step_index, pred_full.alerts[0].step_index)
        self.assertEqual(pred_t1.alerts[0].risk_score, pred_full.alerts[0].risk_score)
        self.assertEqual(pred_t1.alerts[0].explanation, pred_full.alerts[0].explanation)
        self.assertEqual(pred_t1.alerts[0].evidence, pred_full.alerts[0].evidence)

        # At t=2: exactly 2 alerts, matching full trajectory alerts[:2]
        self.assertEqual(len(pred_t2.alerts), 2)
        for i in range(2):
            self.assertEqual(pred_t2.alerts[i].alert_id, pred_full.alerts[i].alert_id)
            self.assertEqual(pred_t2.alerts[i].step_index, pred_full.alerts[i].step_index)
            self.assertEqual(pred_t2.alerts[i].risk_score, pred_full.alerts[i].risk_score)

        # In full run at t=3, recovery happened, but earlier alerts are NOT deleted
        self.assertEqual(len(pred_full.alerts), 2)
        self.assertEqual(len(pred_full.resolutions), 1)

    def test_idempotent_reprocessing_does_not_duplicate_alerts(self):
        """7. Evaluating same trajectory steps does not duplicate alerts in the stream."""
        detector = MockDetector({
            0: {"is_alert": False, "risk": 10.0},
            1: {"is_alert": True, "risk": 80.0, "explanation": "alert"}
        })
        steps = [make_test_step(0), make_test_step(1)]
        traj = TrajectoryObservation(trajectory_id="traj_idempotent", steps=steps)

        # Evaluate first time
        pred1 = detector.evaluate_trajectory(traj)
        self.assertEqual(len(pred1.alerts), 1)
        alert_id_1 = pred1.alerts[0].alert_id

        # Evaluate second time on identical input
        pred2 = detector.evaluate_trajectory(traj)
        self.assertEqual(len(pred2.alerts), 1)
        self.assertEqual(pred2.alerts[0].alert_id, alert_id_1)

    def test_absence_of_timestamp_preserved_as_none(self):
        """8. When timestamp is not provided, it must be None without artificial epoch strings or zeros."""
        alert = AlertEmitted(
            alert_id="alert_no_ts",
            trajectory_id="traj_no_ts",
            detector_name="Det",
            step_index=0,
            timestamp=None,
            risk_score=60.0,
            threshold=50.0
        )
        self.assertIsNone(alert.timestamp)
        dumped = alert.model_dump()
        self.assertIsNone(dumped["timestamp"])

    def test_validation_rejection_of_invalid_events(self):
        """9. Pydantic validation rejects malformed events (negative index, missing fields, etc.)."""
        # Negative step_index
        with self.assertRaises(ValidationError):
            AlertEmitted(
                alert_id="a1",
                trajectory_id="t1",
                detector_name="d1",
                step_index=-1,  # Invalid: ge=0
                risk_score=50.0,
                threshold=50.0
            )

        # Missing required field trajectory_id
        with self.assertRaises(ValidationError):
            AlertEmitted(
                alert_id="a1",
                detector_name="d1",
                step_index=0,
                risk_score=50.0,
                threshold=50.0
            )

        # Negative risk_score
        with self.assertRaises(ValidationError):
            AlertEmitted(
                alert_id="a1",
                trajectory_id="t1",
                detector_name="d1",
                step_index=0,
                risk_score=-5.0,  # Invalid: ge=0.0
                threshold=50.0
            )

    def test_serialization_roundtrip_fidelity(self):
        """10. JSON serialization and deserialization preserves all fields and frozen behavior."""
        alert = AlertEmitted(
            alert_id="alert_roundtrip_001",
            trajectory_id="traj_rt",
            detector_name="ArkheSentinel",
            detector_version="3.0.0",
            step_index=4,
            timestamp="2026-09-30T12:00:00Z",
            risk_score=91.4,
            threshold=50.0,
            severity=AlertSeverity.CRITICAL,
            evidence={"subspace_projection": 0.88, "divergence": 0.75},
            explanation="Critical mission divergence detected"
        )

        json_str = alert.model_dump_json()
        restored = AlertEmitted.model_validate_json(json_str)

        self.assertEqual(restored.event_type, "alert_emitted")
        self.assertEqual(restored.schema_version, "1.0.0")
        self.assertEqual(restored.alert_id, "alert_roundtrip_001")
        self.assertEqual(restored.risk_score, 91.4)
        self.assertEqual(restored.severity, AlertSeverity.CRITICAL)
        self.assertEqual(restored.evidence["divergence"], 0.75)

        # Restored instance is still frozen
        with self.assertRaises(ValidationError):
            restored.risk_score = 20.0

    def test_backward_compatibility_aliases(self):
        """11. Verify AlertEvent, ResolutionEvent, ContainmentEvent aliases operate identically."""
        self.assertIs(AlertEvent, AlertEmitted)
        self.assertIs(ResolutionEvent, AlertResolved)
        self.assertIs(ContainmentEvent, ContainmentAttempted)

        # Creating via legacy name
        legacy_alert = AlertEvent(
            alert_id="legacy_01",
            trajectory_id="t1",
            detector_name="d1",
            step_index=1,
            risk_score=60.0,
            threshold=50.0
        )
        self.assertIsInstance(legacy_alert, AlertEmitted)
        self.assertEqual(legacy_alert.event_type, "alert_emitted")

    def test_zero_ground_truth_in_event_contracts(self):
        """12. Ensure event contracts do not leak ground truth or editorial labels."""
        forbidden_keys = {
            "ground_truth_class", "violation_step_index", "drift_step_index",
            "evaluator_rationale", "is_violation", "is_benign"
        }
        alert = AlertEmitted(
            alert_id="a1",
            trajectory_id="t1",
            detector_name="d1",
            step_index=1,
            risk_score=60.0,
            threshold=50.0
        )
        keys = set(alert.model_dump().keys())
        self.assertTrue(forbidden_keys.isdisjoint(keys), f"Leaked keys found: {forbidden_keys.intersection(keys)}")


if __name__ == "__main__":
    unittest.main()
