"""Defense release version is single-sourced; no build, installation or network."""
import importlib.util
import tempfile
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

    def test_version_readers_accept_valid_formatting_and_reject_missing_values(self):
        build = defense_build()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'file'
            for toml in ("[project]\nname = 'x'\nversion='0.3.0'\n",
                         '[project]\nversion   =   "0.3.0"   # release\n[tool.x]\nversion = "9"\n'):
                path.write_text(toml, encoding='utf-8')
                self.assertEqual(build.project_version(path), '0.3.0')
            for module in ('__version__ = "0.3.0"\n', "__version__: str = '0.3.0'  # pinned\n",
                           '"""Doc."""\nimport os\n__version__ = (\n    "0.3.0"\n)\n'):
                path.write_text(module, encoding='utf-8')
                self.assertEqual(build.package_version(path), '0.3.0')
            for toml in ('[project]\nname = "x"\n', '[project]\ndynamic = ["version"]\n'):
                path.write_text(toml, encoding='utf-8')
                with self.assertRaises(ValueError):
                    build.project_version(path)
            for module in ('VERSION = "0.3.0"\n', '__version__ = get_version()\n'):
                path.write_text(module, encoding='utf-8')
                with self.assertRaises(ValueError):
                    build.package_version(path)


if __name__ == '__main__':
    unittest.main()
