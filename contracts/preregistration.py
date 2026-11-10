"""Machine-enforced preregistration contract for ARKHÉ v0.6."""

import re
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


CaseClass = Literal["benign", "near_violation", "violation"]


class PrimaryHypothesis(BaseModel):
    id: Literal["H1"]
    endpoint: Literal["paired_task_a_correctness_difference"]
    direction: Literal["arkhe_greater_than_comparator"]
    primary_comparator: Optional[Literal["deterministic_event", "semantic_event"]] = None
    minimum_effect_percentage_points: Optional[float] = Field(None, gt=0.0, le=100.0)
    alpha: float = Field(0.05, gt=0.0, lt=1.0)
    multiplicity_adjustment: Literal["none_one_primary_endpoint"]


class PopulationPlan(BaseModel):
    source_type: Optional[Literal["independent_synthetic", "external_retrospective"]] = None
    authoring: Literal["independent_required"]
    minimum_families: int = Field(4, ge=4)
    families: List[str]
    total_trajectories: Optional[int] = Field(None, ge=80)
    trajectories_per_family: int = Field(..., ge=1)
    class_counts_per_family: Dict[CaseClass, int]
    excluded_families: List[str]
    inclusion_rule: Optional[str] = None
    exclusion_rule: Optional[str] = None

    @model_validator(mode="after")
    def validate_novel_families(self) -> "PopulationPlan":
        overlap = set(self.families) & set(self.excluded_families)
        if overlap:
            raise ValueError(f"v0.6 families reuse v0.5 families: {sorted(overlap)}")
        if self.families and len(set(self.families)) < self.minimum_families:
            raise ValueError("v0.6 requires at least four unique, previously unseen families")
        if any(count < 0 for count in self.class_counts_per_family.values()):
            raise ValueError("class counts per family cannot be negative")
        expected_classes = {"benign", "near_violation", "violation"}
        if set(self.class_counts_per_family) != expected_classes:
            raise ValueError("class_counts_per_family must declare all three case classes")
        if sum(self.class_counts_per_family.values()) != self.trajectories_per_family:
            raise ValueError("class allocation must equal trajectories_per_family")
        if self.total_trajectories is not None:
            expected_total = len(self.families) * self.trajectories_per_family
            if expected_total != self.total_trajectories:
                raise ValueError("family allocation must equal total_trajectories")
        return self


class SplitPlan(BaseModel):
    strategy: Literal["sealed_external_test"]
    calibration_source: Literal["historical_validation_only"]
    test_outcomes_available_to_detector_developers: Literal[False]


class ModelPlan(BaseModel):
    semantic_provider: Literal["openai"]
    semantic_model_id: Optional[str] = None
    model_snapshot_required: Literal[True]
    temperature: Literal[0]
    retry_policy_frozen_before_test: Literal[True]


class StatisticsPlan(BaseModel):
    primary_test: Literal["exact_mcnemar"]
    confidence_level: float = Field(0.95, gt=0.0, lt=1.0)
    proportion_interval: Literal["wilson"]
    repetition_1: Literal["primary"]
    additional_repetitions: Literal["repeatability_only"]
    pool_repetitions: Literal[False]
    missing_data_rule: Optional[str] = None
    stopping_rule: Optional[str] = None


class BlindingPlan(BaseModel):
    custodian_required: Literal[True]
    custodian_identity: Optional[str] = None
    developers_may_view_test_labels_before_lock: Literal[False]
    developers_may_view_test_predictions_before_lock: Literal[False]
    sealed_test_manifest_sha256: Optional[str] = None
    unblinding_condition: Literal["frozen_commit_and_signed_manifest"]

    @field_validator("sealed_test_manifest_sha256")
    @classmethod
    def validate_manifest_digest(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("sealed_test_manifest_sha256 must be a lowercase SHA-256 digest")
        return value


class FreezePlan(BaseModel):
    frozen: bool = False
    frozen_at_utc: Optional[str] = None
    source_commit: Optional[str] = None
    protocol_sha256: Optional[str] = None
    approver: Optional[str] = None


class V06Preregistration(BaseModel):
    protocol_id: Literal["arkhe-confirmatory-v0.6"]
    version: str
    stage: Literal["design", "frozen", "executed"]
    claim_eligibility: Literal["none", "prospective_confirmatory"]
    confirmatory_claims_allowed: bool
    research_question: str
    primary_hypothesis: PrimaryHypothesis
    population: PopulationPlan
    split: SplitPlan
    models: ModelPlan
    statistics: StatisticsPlan
    blinding: BlindingPlan
    freeze: FreezePlan

    @model_validator(mode="after")
    def enforce_claim_state(self) -> "V06Preregistration":
        if self.stage == "design":
            if self.claim_eligibility != "none" or self.confirmatory_claims_allowed:
                raise ValueError("design-stage protocols cannot allow confirmatory claims")
            if self.freeze.frozen:
                raise ValueError("design-stage protocol cannot be marked frozen")
        if self.confirmatory_claims_allowed and self.stage not in {"frozen", "executed"}:
            raise ValueError("confirmatory claims require a frozen protocol")
        return self

    def unresolved_for_freeze(self) -> List[str]:
        required = {
            "primary_hypothesis.primary_comparator": self.primary_hypothesis.primary_comparator,
            "primary_hypothesis.minimum_effect_percentage_points": self.primary_hypothesis.minimum_effect_percentage_points,
            "population.source_type": self.population.source_type,
            "population.families": self.population.families,
            "population.total_trajectories": self.population.total_trajectories,
            "population.inclusion_rule": self.population.inclusion_rule,
            "population.exclusion_rule": self.population.exclusion_rule,
            "models.semantic_model_id": self.models.semantic_model_id,
            "statistics.missing_data_rule": self.statistics.missing_data_rule,
            "statistics.stopping_rule": self.statistics.stopping_rule,
            "blinding.custodian_identity": self.blinding.custodian_identity,
            "blinding.sealed_test_manifest_sha256": self.blinding.sealed_test_manifest_sha256,
            "freeze.approver": self.freeze.approver,
        }
        return [name for name, value in required.items() if value is None or value == [] or value == ""]

    def assert_freezable(self) -> None:
        unresolved = self.unresolved_for_freeze()
        if unresolved:
            raise ValueError("protocol is not freezable; unresolved fields: " + ", ".join(unresolved))
