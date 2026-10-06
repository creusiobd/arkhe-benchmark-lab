"""Export sanitized local release evidence; no credentials, host paths or candidacy data."""
import json
import argparse
from pathlib import Path
import platform
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / '.review-build/reconciliation'

def read(name):
    return json.loads((INPUT / name).read_text(encoding='utf-8-sig'))

def summarize(demo_dir=None):
    suite = ET.parse(INPUT / 'regression-final.xml').getroot().find('testsuite')
    if int(suite.attrib['errors']) or int(suite.attrib['failures']):
        raise ValueError('Cannot export passing evidence for failed regression')
    transcript = (INPUT / 'regression-final.txt').read_text(encoding='utf-8-sig')
    passed = int(re.search(r'(\d+) passed', transcript).group(1))
    subtests = int(re.search(r'(\d+) subtests passed', transcript).group(1))
    demo = json.loads(((demo_dir or ROOT / 'results/local-pilot-demo') / 'demo.json').read_text(encoding='utf-8'))['summary']
    skipped = [{'test': node.attrib['classname'] + '.' + node.attrib['name'],
                'reason': node.find('skipped').attrib.get('message', '')}
               for node in suite.findall('testcase') if node.find('skipped') is not None]
    packages = []
    for namespace in ('defense', 'trajectory'):
        artifacts = read(namespace + '-artifact-verification.json')
        installed = read(namespace + '-fresh-verification.json')
        if not artifacts['verified'] or not installed['verified']:
            raise ValueError('Unverified SDK evidence')
        packages.append({key: artifacts[key] for key in ('distribution', 'version', 'source_count', 'artifacts', 'license_verified', 'archive_paths_safe', 'sdist_rebuild')})
        packages[-1]['fresh_install_verified'] = installed['isolated_smoke']['installed']
        packages[-1]['journal_imported'] = installed['isolated_smoke']['journal_imported']
        packages[-1]['cli_verified'] = sorted(installed['isolated_smoke']['cli'])
    freeze = read('frozen-checkout.json')
    return {'date': '2026-10-06', 'base_commit': read('import-manifest.json')['base_commit'],
            'python': platform.python_version(), 'platform': platform.system(),
            'regression': {'passed': passed, 'subtests_passed': subtests,
                           'errors': int(suite.attrib['errors']), 'failures': int(suite.attrib['failures']),
                           'skipped': skipped, 'seconds': float(suite.attrib['time']),
                           'warning': 'Legacy Starlette/httpx deprecation'},
            'packages': packages, 'pip_check': (INPUT / 'fresh-pip-check.txt').read_text().strip(),
            'demo': {'executed': demo['executed'], 'blocked': demo['blocked'],
                     'private_resource_dispatched': demo['private_resource_dispatched'],
                     'agent': 'scripted_without_llm', 'transport': 'real_local_stdio'},
            'frozen_dataset': {'canonical_blobs_match_existing_hashes': freeze['canonical_matches_freeze'],
                               'exact_git_bytes_restored': freeze['restored_exact_git_bytes'],
                               'file_count': len(freeze['files'])},
            'limitations': ['Local validation only; remote CI matrix pending',
                            'No external partner or customer validation',
                            'No LLM efficacy or comparative gain demonstrated',
                            'No PyPI publication or production deployment']}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo-dir', type=Path)
    target = ROOT / 'reports/sdk-release/validation.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summarize(parser.parse_args().demo_dir), ensure_ascii=False, indent=2), encoding='utf-8')
    print(target)
