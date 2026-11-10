"""Validate v0.6 design-phase preregistration and blindness guardrails."""

import argparse
from collections import Counter
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

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


def verify_sealed_manifest(
    protocol: V06Preregistration, manifest_path: Optional[Path]
) -> List[str]:
    """Verify a custodian-held manifest without publishing its case labels."""
    if manifest_path is None:
        return ["--manifest is required when --require-freezable is used"]
    if not manifest_path.is_file():
        return [f"sealed manifest does not exist: {manifest_path}"]

    raw = manifest_path.read_bytes()
    actual_digest = hashlib.sha256(raw).hexdigest()
    declared_digest = protocol.blinding.sealed_test_manifest_sha256
    errors = []
    if declared_digest != actual_digest:
        errors.append("sealed manifest SHA-256 does not match the protocol commitment")

    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return errors + ["sealed manifest must be valid UTF-8 JSON"]
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        return errors + ["sealed manifest must contain a cases array"]
    if payload.get("protocol_id") != protocol.protocol_id:
        errors.append("sealed manifest protocol_id does not match the protocol")
    if payload.get("protocol_version") != protocol.version:
        errors.append("sealed manifest protocol_version does not match the protocol")

    cases = payload["cases"]
    expected_total = protocol.population.total_trajectories
    if len(cases) != expected_total:
        errors.append(f"manifest must contain exactly {expected_total} cases")

    case_ids = set()
    content_digests = set()
    family_counts: Counter[str] = Counter()
    class_counts: Counter[tuple[str, str]] = Counter()
    allowed_families = set(protocol.population.families)
    allowed_classes = set(protocol.population.class_counts_per_family)

    for index, case in enumerate(cases):
        prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} must be an object")
            continue
        case_id = case.get("case_id")
        family = case.get("family")
        case_class = case.get("case_class")
        content_digest = case.get("content_sha256")

        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{prefix}.case_id must be a nonempty string")
        elif case_id in case_ids:
            errors.append(f"duplicate case_id: {case_id}")
        else:
            case_ids.add(case_id)

        if family not in allowed_families:
            errors.append(f"{prefix}.family is not declared in the protocol")
        else:
            family_counts[family] += 1

        if case_class not in allowed_classes:
            errors.append(f"{prefix}.case_class is not declared in the protocol")
        elif family in allowed_families:
            class_counts[(family, case_class)] += 1

        if not isinstance(content_digest, str) or re.fullmatch(
            r"[0-9a-f]{64}", content_digest
        ) is None:
            errors.append(f"{prefix}.content_sha256 must be a lowercase SHA-256 digest")
        elif content_digest in content_digests:
            errors.append(f"duplicate content_sha256: {content_digest}")
        else:
            content_digests.add(content_digest)

    for family in protocol.population.families:
        expected_family_total = protocol.population.trajectories_per_family
        if family_counts[family] != expected_family_total:
            errors.append(
                f"family {family} must contain exactly {expected_family_total} cases"
            )
        for case_class, expected_count in protocol.population.class_counts_per_family.items():
            if class_counts[(family, case_class)] != expected_count:
                errors.append(
                    f"family {family} class {case_class} must contain exactly "
                    f"{expected_count} cases"
                )
    return errors


def validate(
    protocol_path: Path,
    require_freezable: bool = False,
    manifest_path: Optional[Path] = None,
    base_dir: Path = BASE_DIR,
) -> Dict[str, object]:
    protocol = V06Preregistration.model_validate(
        yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    )
    forbidden = find_forbidden_design_artifacts(base_dir)
    errors = []
    manifest_verified = None
    if protocol.stage == "design" and forbidden:
        errors.append("design phase contains forbidden v0.6 data/result artifacts")
    if require_freezable:
        try:
            protocol.assert_freezable()
        except ValueError as exc:
            errors.append(str(exc))
        manifest_errors = verify_sealed_manifest(protocol, manifest_path)
        errors.extend(manifest_errors)
        manifest_verified = not manifest_errors
    return {
        "protocol_id": protocol.protocol_id,
        "stage": protocol.stage,
        "claim_eligibility": protocol.claim_eligibility,
        "confirmatory_claims_allowed": protocol.confirmatory_claims_allowed,
        "unresolved_for_freeze": protocol.unresolved_for_freeze(),
        "forbidden_design_artifacts": forbidden,
        "manifest_verified": manifest_verified,
        "passed": not errors,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", default="configs/evaluation_protocol_v0.6.yaml")
    parser.add_argument("--require-freezable", action="store_true")
    parser.add_argument(
        "--manifest",
        help="Path to the private custodian manifest; required with --require-freezable",
    )
    args = parser.parse_args()
    path = Path(args.protocol)
    if not path.is_absolute():
        path = BASE_DIR / path
    manifest_path = Path(args.manifest) if args.manifest else None
    report = validate(path, args.require_freezable, manifest_path)
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
