#!/usr/bin/env bash
# ==============================================================================
# ARKHÉ Agent Boundary Defense Benchmark — Deterministic Dataset Reproduction
# Bash Script (Linux / macOS / CI)
# ==============================================================================
set -euo pipefail

echo "================================================================================"
echo "   ARKHÉ BENCHMARK -- DETERMINISTIC DATASET REPRODUCTION PROTOCOL"
echo "================================================================================"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" &>/dev/null; then
    PYTHON_BIN="python"
fi

echo "• Python executable: $($PYTHON_BIN --version)"

# Step 1: Run reproduction unit tests
echo ""
echo "--- [1/2] Running Determinism & Anti-Leakage Unit Tests ---"
"$PYTHON_BIN" -m unittest tests/test_deterministic_reproduction.py -v

# Step 2: Run dual-generation verification verifier with tracked sync check
echo ""
echo "--- [2/2] Running Dual-Run Bitwise Verification and Tracked Hash Check ---"
"$PYTHON_BIN" scripts/verify_deterministic_dataset_generation.py \
    --config configs/hard_candidate_v0.4.yaml \
    --check-tracked

echo ""
echo "================================================================================"
echo "    DETERMINISTIC VERIFICATION COMPLETE: 100% Bitwise Match Confirmed."
echo "================================================================================"
