"""Defense release version is single-sourced; no build, installation or network."""
import importlib.util
import unittest
from pathlib import Path
import arkhe_defense

ROOT = Path(__file__).resolve().parents[2]


def defense_build():
    spec = importlib.util.spec_from_file_location('defense_build', ROOT / 'sdk/build.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseVersionTests(unittest.TestCase):
    def test_defense_version_agrees_across_package_build_docs_and_ci(self):
        version = defense_build().version()
        self.assertEqual(version, arkhe_defense.__version__)
        text = lambda name: (ROOT / name).read_text(encoding='utf-8')
        self.assertIn(f'# ARKHÉ Defensive SDK {version} alpha', text('README_DEFENSIVE_SDK.md'))
        self.assertIn(f'# arkhe-defense-sdk {version} alpha', text('CHANGELOG_SDK.md'))
        self.assertEqual(text('.github/workflows/sdk-validation.yml').count(f'.review-build/defense-{version}'), 2)
        self.assertIn(f'arkhe_defense_sdk-{version}-py3-none-any.whl', text('SDK_QUICKSTART.md'))


if __name__ == '__main__':
    unittest.main()
