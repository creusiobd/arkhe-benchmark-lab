"""Build the isolated SDK distribution without changing the benchmark package.

Usage: python sdk/build.py [--output .review-build/defense-<version>]
The version comes from sdk/pyproject.toml and must match arkhe_defense.__version__.
The staging source is retained, including its standalone pyproject and README.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def version() -> str:
    """Single release version: pyproject and the package must agree, or the build stops."""
    declared = re.search(r'^version = "([^"]+)"$', (ROOT / "sdk/pyproject.toml").read_text(encoding="utf-8"), re.M)
    package = re.search(r"^__version__ = ['\"]([^'\"]+)['\"]$", (ROOT / "arkhe_defense/__init__.py").read_text(encoding="utf-8"), re.M)
    if not declared or not package or declared.group(1) != package.group(1):
        raise ValueError("sdk/pyproject.toml version and arkhe_defense.__version__ must match")
    return declared.group(1)


def build(output: Path) -> list[Path]:
    output = output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Build output must be inside this project")
    output.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="source-", dir=output))
    shutil.copytree(ROOT / "arkhe_defense", staging / "arkhe_defense",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copyfile(ROOT / "sdk/pyproject.toml", staging / "pyproject.toml")
    shutil.copyfile(ROOT / "README_DEFENSIVE_SDK.md", staging / "README.md")
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
        "distribution": "arkhe-defense-sdk", "version": version(),
        "staging": str(staging.relative_to(ROOT)),
        "sources": {str(p.relative_to(staging)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((staging / "arkhe_defense").rglob("*.py"))},
        "artifacts": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts},
    }
    (output / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / f".review-build/defense-{version()}")
    args = parser.parse_args()
    for artifact in build(args.output):
        print(artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
