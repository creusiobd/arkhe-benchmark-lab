"""
Tests for Contract Separation and Import Isolation
===================================================
Verifies via AST parsing that no detector or observable contract imports ground-truth modules.
"""

import os
import ast
import unittest


class TestContractSeparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.detectors_dir = os.path.join(cls.root_dir, "detectors")
        cls.contracts_dir = os.path.join(cls.root_dir, "contracts")

    def _extract_imported_modules(self, filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports

    def test_no_detector_imports_ground_truth(self):
        detector_files = [
            os.path.join(self.detectors_dir, f)
            for f in os.listdir(self.detectors_dir)
            if f.endswith(".py") and not f.startswith("__")
        ]
        self.assertGreater(len(detector_files), 0, "No detector files found to audit")

        for fpath in detector_files:
            imports = self._extract_imported_modules(fpath)
            for imp in imports:
                self.assertNotIn(
                    "ground_truth", imp,
                    f"Forbidden ground truth import found in detector '{os.path.basename(fpath)}': {imp}"
                )

    def test_observation_contract_does_not_import_ground_truth(self):
        obs_file = os.path.join(self.contracts_dir, "observation.py")
        imports = self._extract_imported_modules(obs_file)
        for imp in imports:
            self.assertNotIn("ground_truth", imp)

    def test_prediction_contract_does_not_import_ground_truth(self):
        pred_file = os.path.join(self.contracts_dir, "prediction.py")
        imports = self._extract_imported_modules(pred_file)
        for imp in imports:
            self.assertNotIn("ground_truth", imp)


if __name__ == "__main__":
    unittest.main()
