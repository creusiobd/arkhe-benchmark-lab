"""Build the isolated SDK distribution without changing the benchmark package.

Usage: python trajectory-sdk/build.py [--output .review-build/trajectory-0.2.0]
The staging source is retained, including its standalone pyproject and README.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def build(output: Path) -> list[Path]:
    output = output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Build output must be inside this project")
    output.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="source-", dir=output))
    shutil.copytree(ROOT / "arkhe_trajectory", staging / "arkhe_trajectory",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copyfile(ROOT / "trajectory-sdk/pyproject.toml", staging / "pyproject.toml")
    shutil.copyfile(ROOT / "README_TRAJECTORY_SDK.md", staging / "README.md")
    shutil.copyfile(ROOT / "LICENSE", staging / "LICENSE")
    from setuptools import build_meta
    previous = Path.cwd()
    try:
        os.chdir(staging)
        wheel_name = build_meta.build_wheel(str(output))
        sdist_name = build_meta.build_sdist(str(output))
    finally:
        os.chdir(previous)
    artifacts = [output / wheel_name, output / sdist_name]
    manifest = {
        "distribution": "arkhe-trajectory-sdk", "version": "0.2.0",
        "staging": str(staging.relative_to(ROOT)),
        "sources": {str(p.relative_to(staging)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((staging / "arkhe_trajectory").rglob("*")) if p.is_file() and p.suffix in (".py", ".json")},
        "artifacts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts},
    }
    (output / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".review-build/trajectory-0.2.0")
    args = parser.parse_args()
    for artifact in build(args.output):
        print(artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
