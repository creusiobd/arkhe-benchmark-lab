"""Selectively stage new SDKs into an existing public checkout; never replace legacy code."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

SOURCE = Path(__file__).resolve().parents[1]
TREES = ['arkhe_defense', 'arkhe_trajectory', 'tests/defense', 'tests/trajectory',
         'tests/audit', 'configs/journeys', 'examples/defense', 'examples/trajectory',
         'docs/pilot']
FILES = ['sdk/build.py', 'sdk/pyproject.toml', 'trajectory-sdk/build.py',
         'trajectory-sdk/pyproject.toml', 'README_DEFENSIVE_SDK.md',
         'README_TRAJECTORY_SDK.md', '.github/workflows/sdk-validation.yml',
         'scripts/verify_sdk_release.py', 'scripts/reconcile_public_sdk.py']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def reconcile(target):
    target = target.resolve()
    workspace = SOURCE.parent.resolve()
    if target == SOURCE or not target.is_relative_to(workspace) or not (target / '.git').is_dir():
        raise ValueError('Target must be a separate Git checkout inside the workspace')
    def git(*args):
        return subprocess.check_output(['git', '-c', 'safe.directory=' + target.as_posix(), *args], cwd=target, text=True).strip()
    base = git('rev-parse', 'HEAD')
    tracked = git('ls-files').splitlines()
    before = {name: sha(target / name) for name in tracked if (target / name).is_file()}
    paths = [SOURCE / name for name in FILES]
    for tree in TREES:
        paths.extend(p for p in (SOURCE / tree).rglob('*') if p.is_file() and p.suffix in {'.py', '.json', '.md'} and '__pycache__' not in p.parts)
    changes = {}
    for source in paths:
        relative = source.relative_to(SOURCE).as_posix()
        destination = target / relative
        if relative in before:
            raise ValueError('Refusing to replace public tracked file: ' + relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        changes[relative] = sha(destination)
    # New lab namespace, deliberately independent of the public harness.
    namespace = target / 'benchmark'
    namespace.mkdir(exist_ok=True)
    for relative in ['benchmark/__init__.py', 'benchmark/mcp_lab.py']:
        if relative in before:
            raise ValueError('Public benchmark namespace collision')
        source = SOURCE / relative
        content = (b'"""Controlled MCP lab, independent of the research harness."""\n'
                   if relative.endswith('__init__.py') else source.read_bytes())
        (target / relative).write_bytes(content)
        changes[relative] = sha(target / relative)
    unchanged = {name: sha(target / name) == digest for name, digest in before.items()}
    if not all(unchanged.values()):
        raise ValueError('Unexpected alteration of public baseline')
    report = {'base_commit': base, 'public_baseline_files': len(before),
              'baseline_unchanged_at_import': True, 'imported_files': changes,
              'excluded': ['legacy benchmark/code/results', 'local environments',
                           'personal candidacy dossier', 'old generated logs']}
    output = target / '.review-build/reconciliation'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'import-manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'base_commit': base, 'imported_files': len(changes), 'baseline_files_preserved': len(before)}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    reconcile(parser.parse_args().target)
