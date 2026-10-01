"""Prospective v0.5 leave-one-family-out scoring and decision harness."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from calibration.select_threshold import ScoredTrajectory, first_crossing, select_threshold
from contracts.evaluation_protocol import EvaluationProtocol
from contracts.ground_truth import TrajectoryGroundTruth
from contracts.observation import TrajectoryObservation
from detectors.arkhe_trajectory import ArkheTrajectoryDetector
from detectors.deterministic_event import DeterministicEventDetector
from detectors.semantic_event import SemanticEventDetector


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_freeze(freeze_path: Path) -> Dict[str, Any]:
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    mismatches = []
    for relative_path, expected_hash in freeze["files"].items():
        path = BASE_DIR / relative_path
        actual_hash = sha256_file(path) if path.exists() else None
        if actual_hash != expected_hash:
            mismatches.append({"path": relative_path, "expected": expected_hash, "actual": actual_hash})
    if mismatches:
        raise ValueError(f"Freeze verification failed: {mismatches}")
    return freeze


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=BASE_DIR, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except Exception:
        return "git-unavailable"


def load_jsonl(path: Path, model: Any) -> List[Any]:
    with path.open("r", encoding="utf-8") as handle:
        return [model.model_validate_json(line) for line in handle if line.strip()]


def detector_specs(semantic_mode: str, model: str) -> Dict[str, Tuple[Any, bool]]:
    return {
        "deterministic_event": (lambda: DeterministicEventDetector(), False),
        "semantic_event": (
            lambda: SemanticEventDetector(mode=semantic_mode, model=model), False
        ),
        "arkhe_trajectory": (
            lambda: ArkheTrajectoryDetector(risk_threshold=101.0), False
        ),
        "arkhe_no_history": (
            lambda: ArkheTrajectoryDetector(risk_threshold=101.0, detector_name="ARKHÉ-Ablation-No-History"), True
        ),
        "arkhe_no_contamination": (
            lambda: ArkheTrajectoryDetector(
                risk_threshold=101.0,
                disabled_components={"context_contamination"},
                detector_name="ARKHÉ-Ablation-No-Contamination",
            ),
            False,
        ),
    }


def step_risk(detector_key: str, prediction: Any) -> float:
    if detector_key == "semantic_event":
        return float(prediction.confidence if prediction.is_alert else 1.0 - prediction.confidence)
    return float(prediction.accumulated_trajectory_risk) / 100.0


def score_trajectory(detector_key: str, detector: Any, trajectory: TrajectoryObservation, no_history: bool) -> Dict[str, Any]:
    sanitized = trajectory.to_sanitized_opaque()
    history = []
    scores: List[float] = []
    explanations: List[str] = []
    started = time.perf_counter()
    for step in sanitized.steps:
        prediction = detector.evaluate_step(step, trajectory_history=[] if no_history else list(history))
        scores.append(round(step_risk(detector_key, prediction), 8))
        explanations.append(prediction.explanation)
        if not no_history:
            history.append(step)
    return {
        "trajectory_id": trajectory.trajectory_id,
        "step_scores": scores,
        "explanations": explanations,
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 4),
    }


def stratified_subset(ids: List[str], truths: Dict[str, TrajectoryGroundTruth], per_partition: Optional[int]) -> List[str]:
    if not per_partition or len(ids) <= per_partition:
        return list(ids)
    by_class: Dict[str, List[str]] = {}
    for trajectory_id in ids:
        by_class.setdefault(truths[trajectory_id].ground_truth_class.value, []).append(trajectory_id)
    selected: List[str] = []
    classes = sorted(by_class)
    while len(selected) < per_partition and any(by_class.values()):
        for label in classes:
            if by_class[label] and len(selected) < per_partition:
                selected.append(by_class[label].pop(0))
    return selected


def run(
    protocol_path: Path,
    dataset_dir: Path,
    output_dir: Path,
    semantic_mode: str,
    model: str,
    repetitions: Optional[int] = None,
    only_detectors: Optional[List[str]] = None,
    smoke_per_partition: Optional[int] = None,
    freeze_manifest: Optional[Path] = None,
    input_price_per_million: float = 0.15,
    output_price_per_million: float = 0.60,
) -> Dict[str, Any]:
    protocol = EvaluationProtocol.model_validate(yaml.safe_load(protocol_path.read_text(encoding="utf-8")))
    observations = load_jsonl(dataset_dir / "observations.jsonl", TrajectoryObservation)
    truths_list = load_jsonl(dataset_dir / "ground_truth" / "v0.5_labels.jsonl", TrajectoryGroundTruth)
    observations_by_id = {item.trajectory_id: item for item in observations}
    truths = {item.trajectory_id: item for item in truths_list}
    split_manifest = json.loads((dataset_dir / "split_manifest.json").read_text(encoding="utf-8"))
    specs = detector_specs(semantic_mode, model)
    requested = only_detectors or protocol.detector_order
    unknown = set(requested) - set(specs)
    if unknown:
        raise ValueError(f"Unknown detectors: {sorted(unknown)}")
    repeat_count = repetitions or protocol.statistics.repetitions
    if smoke_per_partition:
        repeat_count = 1

    freeze = verify_freeze(freeze_manifest) if freeze_manifest else None
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "predictions.jsonl"
    calibration_path = output_dir / "calibration.json"
    predictions: List[Dict[str, Any]] = []
    calibration_records: List[Dict[str, Any]] = []
    telemetry: Dict[str, Any] = {}
    api_call_traces: List[Dict[str, Any]] = []
    run_started = time.perf_counter()

    for repetition in range(1, repeat_count + 1):
        for detector_key in requested:
            factory, no_history = specs[detector_key]
            detector = factory()
            cache: Dict[str, Dict[str, Any]] = {}
            for fold_name, fold in split_manifest["folds"].items():
                validation_ids = stratified_subset(fold["validation_ids"], truths, smoke_per_partition)
                test_ids = stratified_subset(fold["test_ids"], truths, smoke_per_partition)
                needed = sorted(set(validation_ids + test_ids))
                for trajectory_id in needed:
                    if trajectory_id not in cache:
                        cache[trajectory_id] = score_trajectory(
                            detector_key, detector, observations_by_id[trajectory_id], no_history
                        )

                validation_items = [
                    ScoredTrajectory(
                        trajectory_id=trajectory_id,
                        label=truths[trajectory_id].ground_truth_class.value,
                        step_scores=cache[trajectory_id]["step_scores"],
                        violation_step=truths[trajectory_id].violation_step_index,
                    )
                    for trajectory_id in validation_ids
                ]
                calibration = select_threshold(validation_items, protocol.threshold.target_recall)
                calibration_records.append({
                    "fold": fold_name,
                    "test_family": fold["test_family"],
                    "repetition": repetition,
                    "detector": detector_key,
                    "validation_n": len(validation_ids),
                    **calibration,
                })
                threshold = float(calibration["threshold"])
                for trajectory_id in test_ids:
                    score = cache[trajectory_id]
                    alert_step = first_crossing(score["step_scores"], threshold)
                    predictions.append({
                        "fold": fold_name,
                        "test_family": fold["test_family"],
                        "repetition": repetition,
                        "detector": detector_key,
                        "semantic_mode": semantic_mode if detector_key == "semantic_event" else None,
                        "model": model if detector_key == "semantic_event" else None,
                        "trajectory_id": trajectory_id,
                        "threshold": threshold,
                        "step_scores": score["step_scores"],
                        "first_alert_step": alert_step,
                        "is_flagged": alert_step is not None,
                        "latency_ms": score["latency_ms"],
                    })

            client = getattr(detector, "client", None)
            if client and hasattr(client, "get_usage_summary"):
                telemetry[f"rep_{repetition}:{detector_key}"] = client.get_usage_summary()
                for trace in getattr(client, "call_traces", []):
                    api_call_traces.append({
                        "repetition": repetition,
                        "detector": detector_key,
                        **trace,
                    })

    with predictions_path.open("w", encoding="utf-8", newline="\n") as handle:
        for prediction in predictions:
            handle.write(json.dumps(prediction, sort_keys=True) + "\n")
    calibration_path.write_text(json.dumps(calibration_records, indent=2) + "\n", encoding="utf-8")

    output_hashes = {
        "predictions": sha256_file(predictions_path),
        "calibration": sha256_file(calibration_path),
    }
    cost_report = None
    if api_call_traces:
        traces_path = output_dir / "api_call_traces.jsonl"
        with traces_path.open("w", encoding="utf-8", newline="\n") as handle:
            for trace in api_call_traces:
                handle.write(json.dumps(trace, sort_keys=True) + "\n")
        successful = [trace for trace in api_call_traces if trace["status"] == "success"]
        prompt_tokens = sum(trace["prompt_tokens"] for trace in successful)
        completion_tokens = sum(trace["completion_tokens"] for trace in successful)
        cost_report = {
            "model": model,
            "successful_calls": len(successful),
            "trace_records_including_retries": len(api_call_traces),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "input_price_usd_per_million_tokens": input_price_per_million,
            "output_price_usd_per_million_tokens": output_price_per_million,
            "estimated_cost_usd": round(
                prompt_tokens * input_price_per_million / 1_000_000
                + completion_tokens * output_price_per_million / 1_000_000,
                8,
            ),
            "pricing_source": "operator_supplied_cli_values; verify against official pricing at execution time",
        }
        cost_path = output_dir / "cost_report.json"
        cost_path.write_text(json.dumps(cost_report, indent=2) + "\n", encoding="utf-8")
        output_hashes["api_call_traces"] = sha256_file(traces_path)
        output_hashes["cost_report"] = sha256_file(cost_path)

    manifest = {
        "protocol_id": protocol.protocol_id,
        "status": (
            "smoke_test" if smoke_per_partition else
            "confirmatory_frozen_run" if freeze and freeze.get("claim_eligibility") == "prospective_confirmatory" else
            "frozen_reproducibility_run" if freeze else
            "development_rehearsal_test_informed"
        ),
        "freeze_id": freeze.get("freeze_id") if freeze else None,
        "semantic_mode": semantic_mode,
        "semantic_model": model,
        "repetitions": repeat_count,
        "detectors": requested,
        "prediction_count": len(predictions),
        "git_commit": git_commit(),
        "python_version": platform.python_version(),
        "duration_seconds": round(time.perf_counter() - run_started, 4),
        "input_hashes": {
            "protocol": sha256_file(protocol_path),
            "observations": sha256_file(dataset_dir / "observations.jsonl"),
            "ground_truth": sha256_file(dataset_dir / "ground_truth" / "v0.5_labels.jsonl"),
            "split_manifest": sha256_file(dataset_dir / "split_manifest.json"),
        },
        "output_hashes": output_hashes,
        "telemetry": telemetry,
        "cost_report": cost_report,
    }
    (output_dir / "execution_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", default="configs/evaluation_protocol_v0.5.yaml")
    parser.add_argument("--dataset", default="datasets/v0.5_hard")
    parser.add_argument("--output", default="results/v0.5_offline")
    parser.add_argument("--semantic-mode", choices=["offline_proxy", "openai_api"], default="offline_proxy")
    parser.add_argument("--model", default="gpt-4o-mini-2024-07-18")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--detectors", nargs="+")
    parser.add_argument("--smoke-per-partition", type=int)
    parser.add_argument("--freeze-manifest")
    parser.add_argument("--input-price-per-million", type=float, default=0.15)
    parser.add_argument("--output-price-per-million", type=float, default=0.60)
    args = parser.parse_args()

    def resolve(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else BASE_DIR / path

    manifest = run(
        resolve(args.protocol), resolve(args.dataset), resolve(args.output),
        args.semantic_mode, args.model, args.repetitions, args.detectors,
        args.smoke_per_partition,
        resolve(args.freeze_manifest) if args.freeze_manifest else None,
        args.input_price_per_million,
        args.output_price_per_million,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
