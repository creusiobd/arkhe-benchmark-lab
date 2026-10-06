"""Pre-run sensitivity analysis for the fixed v0.5 sample."""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from contracts.evaluation_protocol import EvaluationProtocol
from evaluator.statistics import mcnemar_test, wilson_score_interval


def exact_mcnemar_minimum_wins(max_discordant: int, alpha: float = 0.05) -> Dict[str, Any]:
    for wins in range(1, max_discordant + 1):
        result = mcnemar_test([[0, wins], [0, 0]])
        if result["p_value"] < alpha:
            return {"wins": wins, "losses": 0, "p_value": result["p_value"]}
    return {"wins": None, "losses": 0, "p_value": None}


def analyze(protocol_path: Path) -> Dict[str, Any]:
    protocol = EvaluationProtocol.model_validate(yaml.safe_load(protocol_path.read_text(encoding="utf-8")))
    positives = protocol.corpus.class_counts["violation"]
    negatives = protocol.corpus.class_counts["benign"] + protocol.corpus.class_counts["near_violation"]
    expected_recall_successes = math.ceil(protocol.threshold.target_recall * positives)
    recall_interval = wilson_score_interval(expected_recall_successes, positives)
    fpr_scenarios = {}
    for rate in (0.05, 0.10, 0.20):
        false_positives = round(rate * negatives)
        fpr_scenarios[str(rate)] = {
            "false_positives": false_positives,
            "denominator": negatives,
            "wilson_95_ci": wilson_score_interval(false_positives, negatives),
        }
    return {
        "status": "pre_run_sensitivity_not_post_hoc_power",
        "task_a": {
            "positive_n": positives,
            "negative_n": negatives,
            "target_recall": protocol.threshold.target_recall,
            "minimum_true_positives_for_target": expected_recall_successes,
            "target_recall_wilson_95_ci": recall_interval,
        },
        "paired_false_positive_comparison": {
            "test": "two-sided exact McNemar",
            "negative_pairs": negatives,
            "minimum_one_direction_discordant_wins_for_p_lt_0_05": exact_mcnemar_minimum_wins(negatives),
            "fpr_precision_scenarios": fpr_scenarios,
        },
        "interpretation_limits": [
            "The design can detect a strongly one-sided paired difference but has limited precision for small effects.",
            "Only three authored families are held out; population-level and external-generalization claims are unsupported.",
            "Repetition 2 measures run repeatability and is not an independent sample.",
        ],
    }


def markdown(report: Dict[str, Any]) -> str:
    task = report["task_a"]
    paired = report["paired_false_positive_comparison"]
    lines = [
        "# v0.5 Pre-run Sensitivity Analysis",
        "",
        "This analysis was specified before confirmatory test outputs were inspected. It is a sensitivity statement, not retrospective observed power.",
        "",
        "## Fixed sample",
        "",
        f"- Task A positives: {task['positive_n']} consummated violations.",
        f"- Task A negatives: {task['negative_n']} trajectories.",
        f"- Target recall: {task['target_recall']:.0%}, requiring at least {task['minimum_true_positives_for_target']} true positives.",
        f"- Wilson 95% interval at that count: {task['target_recall_wilson_95_ci']}.",
        "",
        "## Paired comparison sensitivity",
        "",
        f"With zero discordant losses, {paired['minimum_one_direction_discordant_wins_for_p_lt_0_05']['wins']} discordant wins are the minimum for two-sided exact McNemar p < 0.05.",
        "Small differences should therefore be reported descriptively with raw paired counts and intervals.",
        "",
        "## Limits",
        "",
        *[f"- {item}" for item in report["interpretation_limits"]],
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", default="configs/evaluation_protocol_v0.5.yaml")
    parser.add_argument("--json", default="reports/v0.5_power_analysis.json")
    parser.add_argument("--markdown", default="reports/v0.5_power_analysis.md")
    args = parser.parse_args()
    protocol = Path(args.protocol)
    json_path = Path(args.json)
    markdown_path = Path(args.markdown)
    for name, value in (("protocol", protocol), ("json", json_path), ("markdown", markdown_path)):
        if not value.is_absolute():
            resolved = BASE_DIR / value
            if name == "protocol": protocol = resolved
            elif name == "json": json_path = resolved
            else: markdown_path = resolved
    report = analyze(protocol)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
