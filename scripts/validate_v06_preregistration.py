"""Validate v0.6 design-phase preregistration and blindness guardrails."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from contracts.preregistration import V06Preregistration


FORBIDDEN_DESIGN_GLOBS = (
    "datasets/v0.6*",
    "results/v0.6*",
    "reports/v0.6*",
    "freezes/v0.6*",
)


def find_forbidden_design_artifacts(base_dir: Path = BASE_DIR) -> List[str]:
    found = []
    for pattern in FORBIDDEN_DESIGN_GLOBS:
        found.extend(str(path.relative_to(base_dir)) for path in base_dir.glob(pattern))
    return sorted(set(found))


def validate(protocol_path: Path, require_freezable: bool = False) -> Dict[str, object]:
    protocol = V06Preregistration.model_validate(
        yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    )
    forbidden = find_forbidden_design_artifacts()
    errors = []
    if protocol.stage == "design" and forbidden:
        errors.append("design phase contains forbidden v0.6 data/result artifacts")
    if require_freezable:
        try:
            protocol.assert_freezable()
        except ValueError as exc:
            errors.append(str(exc))
    return {
        "protocol_id": protocol.protocol_id,
        "stage": protocol.stage,
        "claim_eligibility": protocol.claim_eligibility,
        "confirmatory_claims_allowed": protocol.confirmatory_claims_allowed,
        "unresolved_for_freeze": protocol.unresolved_for_freeze(),
        "forbidden_design_artifacts": forbidden,
        "passed": not errors,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", default="configs/evaluation_protocol_v0.6.yaml")
    parser.add_argument("--require-freezable", action="store_true")
    args = parser.parse_args()
    path = Path(args.protocol)
    if not path.is_absolute():
        path = BASE_DIR / path
    report = validate(path, args.require_freezable)
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
