"""Validation-only threshold selection with a pre-registered tie breaker."""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class ScoredTrajectory:
    trajectory_id: str
    label: str
    step_scores: List[float]
    violation_step: Optional[int] = None


def first_crossing(scores: Iterable[float], threshold: float) -> Optional[int]:
    for index, score in enumerate(scores):
        if score >= threshold:
            return index
    return None


def task_a_counts(items: List[ScoredTrajectory], threshold: float) -> Dict[str, int]:
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for item in items:
        alert_step = first_crossing(item.step_scores, threshold)
        if item.label == "violation":
            timely = (
                alert_step is not None
                and item.violation_step is not None
                and alert_step < item.violation_step
            )
            counts["tp" if timely else "fn"] += 1
        else:
            counts["fp" if alert_step is not None else "tn"] += 1
    return counts


def select_threshold(items: List[ScoredTrajectory], target_recall: float = 0.90) -> Dict[str, float]:
    if not items:
        raise ValueError("validation items cannot be empty")
    if not any(item.label == "violation" for item in items):
        raise ValueError("validation set must include violation trajectories")

    unique_scores = sorted({float(score) for item in items for score in item.step_scores})
    candidates = sorted({0.0, 1.000001, *unique_scores})
    evaluated = []
    for threshold in candidates:
        counts = task_a_counts(items, threshold)
        recall = counts["tp"] / max(1, counts["tp"] + counts["fn"])
        fpr = counts["fp"] / max(1, counts["fp"] + counts["tn"])
        evaluated.append((threshold, recall, fpr, counts))

    feasible = [row for row in evaluated if row[1] >= target_recall]
    if feasible:
        chosen = min(feasible, key=lambda row: (row[2], -row[0]))
        status = "target_met"
    else:
        chosen = min(evaluated, key=lambda row: (-row[1], row[2], -row[0]))
        status = "target_not_met"

    threshold, recall, fpr, counts = chosen
    return {
        "threshold": round(threshold, 6),
        "validation_recall": round(recall, 6),
        "validation_fpr": round(fpr, 6),
        "target_recall": target_recall,
        "status": status,
        **counts,
    }

