"""Offline configuration checks and replay; never authenticates arbitrary logs."""
from __future__ import annotations
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import sys

from pydantic import ValidationError
from .config import SDKConfig
from .contracts import RuntimeContext, parse_event
from .errors import DefenseError
from .policy import InMemoryPolicyProvider, PolicySnapshot


def event_digest(event) -> str:
    encoded = json.dumps(event.model_dump(mode="json"), sort_keys=True,
                         separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _configuration(path):
    return SDKConfig.model_validate(_json(path)) if path else SDKConfig()


def _replay(args) -> int:
    from .evaluator import DefenseEvaluator
    from .exporters import JSONLExporter
    config = _configuration(args.config)
    provider = InMemoryPolicyProvider()
    for path in args.policy:
        policy = PolicySnapshot.model_validate(_json(path))
        # Explicit local provisioning by the operator selecting these files.
        # This context is not inferred from any event or used to authenticate it.
        admin = RuntimeContext(tenant_id=policy.tenant_id, principal_id="local-replay-operator",
                               producer_id="local-policy-loader", authority="policy_admin",
                               scopes={"policy:write"})
        provider.register(policy, admin, activate=True)
    sidecar = _json(args.contexts)
    if not isinstance(sidecar, list):
        raise ValueError("contexts file must be a list of event_hash/context records")
    contexts = {}
    for record in sidecar:
        if not isinstance(record, dict) or set(record) != {"event_hash", "context"}:
            raise ValueError("context records require exactly event_hash and context")
        digest = record["event_hash"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("context event_hash must be a SHA-256 hex digest")
        context = RuntimeContext.model_validate(record["context"])
        if digest in contexts and context != contexts[digest]:
            raise ValueError("conflicting contexts for an event digest")
        contexts[digest] = context
    exporter = JSONLExporter(args.output, config.max_payload_bytes) if args.output else None
    evaluator = DefenseEvaluator(provider, config=config, exporter=exporter)
    count = 0
    # Fail visibly on missing authority or tampered input. A sidecar is a trusted
    # operator-provided record, not cryptographic proof of transport identity.
    with args.events.open(encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                continue
            if len(line.encode("utf-8")) > config.max_payload_bytes:
                raise ValueError(f"line {number}: event exceeds payload limit")
            event = parse_event(line)
            context = contexts.get(event_digest(event))
            if context is None:
                raise ValueError(f"line {number}: no trusted context matching the event digest")
            decision = evaluator.ingest(event, context)
            if evaluator.last_export_error:
                raise ValueError(f"line {number}: audit export failed")
            print(json.dumps(decision.model_dump(mode="json"), ensure_ascii=True))
            count += 1
    print(json.dumps({"events_processed": count, "mode": "observe"}), file=sys.stderr)
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-config", help="validate strict local JSON configuration")
    validate.add_argument("config", type=Path)
    validate_policy = commands.add_parser("validate-policy", help="validate a versioned local policy")
    validate_policy.add_argument("policy", type=Path)
    doctor = commands.add_parser("doctor", help="local dependency and configuration diagnostics; no network")
    doctor.add_argument("--config", type=Path)
    replay = commands.add_parser("replay", help="offline replay using a separately trusted context sidecar")
    replay.add_argument("events", type=Path)
    replay.add_argument("--contexts", type=Path, required=True)
    replay.add_argument("--policy", type=Path, action="append", required=True)
    replay.add_argument("--config", type=Path)
    replay.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate-config":
            config = _configuration(args.config)
            print(json.dumps({"valid": True, "configuration": config.model_dump(mode="json")}, ensure_ascii=True))
        elif args.command == "validate-policy":
            policy = PolicySnapshot.model_validate(_json(args.policy))
            print(json.dumps({"valid": True, "tenant_id": policy.tenant_id, "version": policy.version,
                              "policy_hash": policy.policy_hash, "rules": len(policy.rules)}, ensure_ascii=True))
        elif args.command == "doctor":
            import pydantic
            from .evaluator import DefenseEvaluator  # validate actual core import
            config = _configuration(args.config)
            try:
                version = metadata.version("arkhe-defense-sdk")
            except metadata.PackageNotFoundError:
                version = "source-checkout"
            print(json.dumps({"sdk": version, "python": sys.version.split()[0], "pydantic": pydantic.__version__,
                              "mode": config.mode, "network_required": False,
                              "authority_source": "authenticated host; not event payload"}, ensure_ascii=True))
        else:
            return _replay(args)
        return 0
    except ValidationError as error:
        print(json.dumps({"error": "validation_failed", "details": error.errors(
            include_input=False, include_context=False, include_url=False)}, default=str), file=sys.stderr)
        return 2
    except (DefenseError, OSError, ValueError) as error:
        print(json.dumps({"error": type(error).__name__, "message": str(error)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
