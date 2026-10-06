"""Compare frozen dataset with canonical Git blobs; optional exact-byte restoration.

Never changes freeze hashes, labels or the committed dataset. Run in repository root.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def verify(restore=False):
    report = json.loads((ROOT / 'reports/dataset_diversity_report_v0.4.json').read_text(encoding='utf-8'))
    records = []
    blobs = []
    for relative, expected in report['dataset_file_hashes'].items():
        path = 'datasets/v0.4_hard/' + relative
        destination = (ROOT / path).resolve()
        if not destination.is_relative_to((ROOT / 'datasets/v0.4_hard').resolve()):
            raise ValueError('Frozen path escapes dataset directory')
        data = subprocess.check_output(['git', '-c', 'safe.directory=' + ROOT.as_posix(), 'show', 'HEAD:' + path], cwd=ROOT)
        canonical = hashlib.sha256(data).hexdigest()
        if canonical != expected:
            raise ValueError('Canonical blob does not match published freeze: ' + path)
        records.append({'path': path, 'canonical_sha256': canonical,
                        'checkout_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
                        'expected_sha256': expected})
        blobs.append((destination, data))
    if restore:
        for destination, data in blobs:
            destination.write_bytes(data)
    return {'canonical_matches_freeze': True, 'restored_exact_git_bytes': restore,
            'files': records}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore-exact-git-bytes', action='store_true')
    print(json.dumps(verify(parser.parse_args().restore_exact_git_bytes), indent=2))
