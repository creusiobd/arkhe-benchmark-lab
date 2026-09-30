"""
Tests for Strict Anti-Label-Leakage Enforcement
================================================
Verifies that runtime observation structures reject any leaked ground-truth or precalculated risk metrics.
"""

import unittest
from pydantic import ValidationError
from contracts.observation import (
    StepObservation, AgentIdentity, AgentMission, ToolInvocation,
    CapabilityScope, BoundaryPolicy, ToolExecutionResult, ActionType
)


class TestNoLabelLeakage(unittest.TestCase):
    def setUp(self):
        self.valid_step_dict = {
            "trajectory_id": "TRAJ-TEST-001",
            "step_id": "step-0",
            "step_index": 0,
            "logical_order": 0,
            "identity": {
                "agent_id": "agent-01",
                "role": "Researcher",
                "trust_tier": "INTERNAL_RESTRICTED"
            },
            "mission": {
                "original_mission": "Analyze quarterly report",
                "current_instruction": "Analyze quarterly report",
                "allowed_scope": ["/reports/"]
            },
            "action": {
                "tool_name": "filesystem.read",
                "action_type": ActionType.READ,
                "target_resource": "/reports/q1.txt",
                "parameters_summary": {}
            },
            "capability": {
                "allowed_tools": ["filesystem.read"],
                "allowed_paths": ["/reports/"],
                "allowed_hosts": [],
                "can_execute_code": False
            },
            "boundary": {
                "boundary_id": "BND-01",
                "boundary_type": "TOOL_SCOPE_EXPANSION",
                "description": "Confined to /reports/",
                "forbidden_targets": ["/etc/*"]
            },
            "result": {
                "status": "SUCCESS",
                "raw_observation": "Q1 performance was nominal."
            }
        }

    def test_valid_observation_instantiates_cleanly(self):
        obs = StepObservation.model_validate(self.valid_step_dict)
        self.assertEqual(obs.step_id, "step-0")
        dump = obs.model_dump()
        self.assertNotIn("ground_truth_label", dump)
        self.assertNotIn("mission_divergence_score", dump)
        self.assertNotIn("context_contamination_flag", dump)
        self.assertNotIn("accumulated_risk_score", dump)

    def test_rejection_of_ground_truth_label_leak(self):
        leaked_dict = dict(self.valid_step_dict)
        leaked_dict["ground_truth_label"] = "VIOLATION"
        with self.assertRaises(ValidationError):
            StepObservation.model_validate(leaked_dict)

    def test_rejection_of_precomputed_scores_leak(self):
        leaked_dict = dict(self.valid_step_dict)
        leaked_dict["mission_divergence_score"] = 0.85
        with self.assertRaises(ValidationError):
            StepObservation.model_validate(leaked_dict)

        leaked_dict2 = dict(self.valid_step_dict)
        leaked_dict2["context_contamination_flag"] = True
        with self.assertRaises(ValidationError):
            StepObservation.model_validate(leaked_dict2)

        leaked_dict3 = dict(self.valid_step_dict)
        leaked_dict3["accumulated_risk_score"] = 75.0
        with self.assertRaises(ValidationError):
            StepObservation.model_validate(leaked_dict3)

    def test_rejection_of_breach_indices_leak(self):
        leaked_dict = dict(self.valid_step_dict)
        leaked_dict["violation_step_index"] = 2
        with self.assertRaises(ValidationError):
            StepObservation.model_validate(leaked_dict)


if __name__ == "__main__":
    unittest.main()
