"""
ARKHÉ Agent Boundary Defense Benchmark — Anti-Leakage Contracts Test Aggregator
================================================================================
Combines deep inspection of detector inputs, AST import isolation, and
opaque identifier guarantees to ensure zero label leakage into detectors.
"""

from tests.test_no_label_leakage import TestNoLabelLeakage
from tests.test_contract_separation import TestContractSeparation

__all__ = ["TestNoLabelLeakage", "TestContractSeparation"]

if __name__ == "__main__":
    import unittest
    unittest.main()
