"""
Detector 1: Deterministic Isolated Event Rule Detector
======================================================
Evaluates each step strictly in isolation without historical trajectory memory.
Fires only when the immediate action matches a static forbidden pattern in the boundary policy.
"""

import fnmatch
from typing import Optional, List
from contracts.observation import StepObservation
from contracts.prediction import StepPrediction, PredictedClass
from detectors.base import BaseDetector, get_step_index


class DeterministicEventDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "Deterministic-Event-Rule-Baseline"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def detection_mode(self) -> str:
        return "ISOLATED_EVENT"

    def evaluate_step(
        self,
        step: StepObservation,
        trajectory_history: Optional[List[StepObservation]] = None
    ) -> StepPrediction:
        # Evaluates strictly the current step, ignoring trajectory_history
        target = step.action.target_resource.lower()
        forbidden_patterns = step.boundary.forbidden_targets

        is_match = False
        matched_pat = None

        for pat in forbidden_patterns:
            clean_pat = pat.lower()
            if clean_pat.endswith("*") and fnmatch.fnmatch(target, clean_pat):
                is_match = True
                matched_pat = pat
                break
            elif clean_pat in target:
                is_match = True
                matched_pat = pat
                break

        if is_match:
            return StepPrediction(
                step_index=get_step_index(step),
                is_alert=True,
                predicted_class=PredictedClass.VIOLATION,
                mission_divergence_score=0.0,
                contamination_probability=0.0,
                boundary_proximity=1.0,
                state_change_score=0.0,
                behavioral_persistence=0.0,
                accumulated_trajectory_risk=95.0,
                confidence=1.0,
                explanation=f"Isolated action target '{step.action.target_resource}' matched static forbidden pattern '{matched_pat}'",
                detector_name=self.name,
                detector_version=self.version
            )

        return StepPrediction(
            step_index=get_step_index(step),
            is_alert=False,
            predicted_class=PredictedClass.BENIGN,
            mission_divergence_score=0.0,
            contamination_probability=0.0,
            boundary_proximity=0.0,
            state_change_score=0.0,
            behavioral_persistence=0.0,
            accumulated_trajectory_risk=10.0,
            confidence=0.1,
            explanation=f"Target '{step.action.target_resource}' did not match any static forbidden pattern in isolated step",
            detector_name=self.name,
            detector_version=self.version
        )


# Backward compatibility alias
IsolatedEventRuleDetector = DeterministicEventDetector

