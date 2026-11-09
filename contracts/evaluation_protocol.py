"""Machine-readable contract for the prospective v0.5 evaluation protocol."""

from typing import Dict, List, Literal

from pydantic import BaseModel, Field, model_validator


class CorpusPlan(BaseModel):
    total_trajectories: int = Field(..., gt=0)
    families: List[str] = Field(..., min_length=2)
    trajectories_per_family: int = Field(..., gt=0)
    class_counts: Dict[Literal["benign", "near_violation", "violation"], int]
    mechanisms_per_family: int = Field(..., gt=1)
    variants_per_mechanism: int = Field(..., gt=0)

    @model_validator(mode="after")
    def validate_totals(self) -> "CorpusPlan":
        if len(set(self.families)) != len(self.families):
            raise ValueError("families must be unique")
        if len(self.families) * self.trajectories_per_family != self.total_trajectories:
            raise ValueError("family allocation does not equal total_trajectories")
        if sum(self.class_counts.values()) != self.total_trajectories:
            raise ValueError("class_counts do not equal total_trajectories")
        if self.mechanisms_per_family * self.variants_per_mechanism != self.trajectories_per_family:
            raise ValueError("mechanism allocation does not equal trajectories_per_family")
        return self


class SplitPlan(BaseModel):
    strategy: Literal["leave_one_family_out"]
    folds: int = Field(..., gt=1)
    validation_unit: Literal["mechanism"]
    test_unit: Literal["family"]


class TaskDefinition(BaseModel):
    name: str
    positive_classes: List[str]
    negative_classes: List[str]
    alert_timing: Literal["strictly_before_violation", "within_hazard_window"]
    primary: bool = False


class ThresholdPlan(BaseModel):
    source: Literal["validation_only"]
    target_recall: float = Field(..., gt=0.0, le=1.0)
    tie_breaker: Literal["lowest_fpr_then_highest_threshold"]


class StatisticsPlan(BaseModel):
    confidence_level: float = Field(0.95, gt=0.0, lt=1.0)
    proportion_interval: Literal["wilson"]
    paired_binary_test: Literal["exact_mcnemar"]
    repetitions: int = Field(2, ge=1)
    pool_repetitions: bool = False


class EvaluationProtocol(BaseModel):
    protocol_id: str
    version: str
    random_seed: int
    corpus: CorpusPlan
    split: SplitPlan
    tasks: Dict[str, TaskDefinition]
    threshold: ThresholdPlan
    statistics: StatisticsPlan
    detector_order: List[str]

    @model_validator(mode="after")
    def validate_design(self) -> "EvaluationProtocol":
        if self.split.folds != len(self.corpus.families):
            raise ValueError("LOFO folds must equal the number of families")
        primary = [task for task in self.tasks.values() if task.primary]
        if len(primary) != 1:
            raise ValueError("exactly one primary task is required")
        if self.statistics.pool_repetitions:
            raise ValueError("prospective protocol forbids pooling repeated runs")
        return self

