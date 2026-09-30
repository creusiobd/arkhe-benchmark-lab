"""
Detector 2: Isolated Event Semantic Classifier (LLM & Offline Proxy Baseline)
=============================================================================
Evaluates individual tool calls and actions strictly in isolation without multi-step trajectory memory.
Simulates an event-level semantic guardrail (e.g., Llama-Guard / GPT-4o-mini tool call filter).

DUAL EXECUTION MODES (NO SILENT FALLBACK):
- 'offline_proxy': Deterministic local heuristic proxy for air-gapped CI/CD and offline tests.
- 'openai_api': Official OpenAI API client with Pydantic structured output.
  If 'openai_api' is requested and no API key is provided, fails fast with an explicit ValueError.
"""

import os
from typing import Optional, List, Dict, Any
from contracts.observation import StepObservation, TrajectoryObservation
from contracts.prediction import StepPrediction, TrajectoryPrediction, PredictedClass
from detectors.base import BaseDetector, get_step_index
from detectors.clients.schema import SemanticClassificationResponse
from detectors.clients.offline_semantic_proxy import OfflineSemanticProxy
from detectors.clients.openai_semantic_client import OpenAISemanticClient


class SemanticEventDetector(BaseDetector):
    def __init__(
        self,
        mode: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        timeout: float = 15.0,
        max_retries: int = 3,
        **kwargs
    ):
        # Resolve mode: default to offline_proxy unless explicitly set to openai_api or api_key provided
        if mode is None:
            resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
            # If explicit api_key was provided as argument, infer openai_api; otherwise default to offline_proxy
            self.mode = "openai_api" if api_key else "offline_proxy"
        else:
            self.mode = mode.lower()

        if self.mode == "openai_api":
            self.client = OpenAISemanticClient(
                api_key=api_key,
                model=model,
                timeout=timeout,
                max_retries=max_retries
            )
        elif self.mode == "offline_proxy":
            self.client = OfflineSemanticProxy()
        else:
            raise ValueError(
                f"Unknown mode '{mode}' for SemanticEventDetector. "
                f"Valid options are: 'offline_proxy', 'openai_api'."
            )

    @property
    def name(self) -> str:
        return "Semantic-Event-Classifier-Baseline"

    @property
    def version(self) -> str:
        return "1.1.0"

    @property
    def detection_mode(self) -> str:
        return "ISOLATED_EVENT"

    @property
    def client_mode(self) -> str:
        return self.client.MODE_NAME

    def evaluate_step(
        self,
        step: StepObservation,
        trajectory_history: Optional[List[StepObservation]] = None
    ) -> StepPrediction:
        # Evaluates strictly the current step in isolation
        verdict: SemanticClassificationResponse = self.client.classify_step(step)

        try:
            pred_class = PredictedClass(verdict.predicted_class.lower())
        except ValueError:
            pred_class = PredictedClass.VIOLATION if verdict.is_alert else PredictedClass.BENIGN

        is_alert = verdict.is_alert
        reasons_text = "; ".join(verdict.security_reasons) if verdict.security_reasons else "semantic analysis"
        explanation = f"[{self.client.MODE_NAME}] {reasons_text}"

        risk_val = 80.0 if is_alert else 15.0
        prox_val = 0.85 if is_alert else 0.10

        return StepPrediction(
            step_index=get_step_index(step),
            is_alert=is_alert,
            predicted_class=pred_class,
            mission_divergence_score=0.0,
            contamination_probability=0.0,
            boundary_proximity=prox_val,
            state_change_score=0.0,
            behavioral_persistence=0.0,
            accumulated_trajectory_risk=risk_val,
            confidence=verdict.confidence,
            explanation=explanation,
            detector_name=self.name,
            detector_version=self.version
        )

    def evaluate_trajectory(self, trajectory: TrajectoryObservation) -> TrajectoryPrediction:
        """Evaluates an entire trajectory observation and aggregates predictions."""
        import time
        t0 = time.perf_counter()
        step_predictions: List[StepPrediction] = []
        first_alert_step: Optional[int] = None
        is_flagged = False
        max_risk = 0.0

        for step in trajectory.steps:
            pred = self.evaluate_step(step, trajectory_history=None)
            step_predictions.append(pred)

            if pred.is_alert and first_alert_step is None:
                first_alert_step = pred.step_index
                is_flagged = True

            if pred.accumulated_trajectory_risk > max_risk:
                max_risk = pred.accumulated_trajectory_risk

        exec_ms = (time.perf_counter() - t0) * 1000.0

        if is_flagged:
            overall_class = PredictedClass.VIOLATION
        else:
            overall_class = PredictedClass.BENIGN

        tokens = 0
        if isinstance(self.client, OpenAISemanticClient):
            tokens = self.client.total_prompt_tokens + self.client.total_completion_tokens

        return TrajectoryPrediction(
            trajectory_id=trajectory.trajectory_id,
            detector_name=self.name,
            detector_version=self.version,
            predicted_class=overall_class,
            first_alert_step=first_alert_step,
            is_flagged=is_flagged,
            max_risk_score=max_risk,
            step_predictions=step_predictions,
            execution_time_ms=round(exec_ms, 2),
            tokens_used=tokens
        )


# Backward compatibility alias
IsolatedEventSemanticDetector = SemanticEventDetector
