#!/usr/bin/env bash
# ==============================================================================
# ARKHÉ Agent Boundary Defense Benchmark — Deterministic Reproduction Script
# Version: v0.3 (OpenAI Cybersecurity Grant Candidate)
# ==============================================================================
set -euo pipefail

echo "================================================================================"
echo "    ARKHÉ BENCHMARK — DETERMINISTIC REPRODUCTION PIPELINE (v0.3)"
echo "================================================================================"

# Verify Python
PYTHON_BIN="${PYTHON:-python3}"
if ! command -v "$PYTHON_BIN" &> /dev/null; then
    PYTHON_BIN="python"
fi

echo "• Python executable: $($PYTHON_BIN --version)"
echo "• Environment: $(uname -s 2>/dev/null || echo Windows)"

# Step 1: Run complete test suite and anti-leakage contract checks
echo ""
echo "--- [1/4] Running Unit Tests & Anti-Leakage Contract Verification ---"
$PYTHON_BIN -m unittest discover -s tests -v

# Step 2: Ensure v0.3 dataset exists
echo ""
echo "--- [2/4] Verifying v0.3 Dataset Integrity ---"
if [ ! -d "datasets/v0.3/observations" ]; then
    echo "• Dataset v0.3 not found. Generating with seed 20260930..."
    $PYTHON_BIN scripts/generate_v03_dataset.py
else
    echo "• Dataset v0.3 verified: $(ls -1 datasets/v0.3/observations/*.jsonl | wc -l) observation splits."
fi

# Step 3: Run blind benchmark execution harness
echo ""
echo "--- [3/4] Executing Blind Benchmark Runner (configs/grant_candidate_v0.3.yaml) ---"
$PYTHON_BIN -m harness.agent_benchmark_runner --config configs/grant_candidate_v0.3.yaml

# Step 4: Run independent evaluator
echo ""
echo "--- [4/4] Running Independent Statistical Evaluator ---"
$PYTHON_BIN -m evaluator.evaluate \
    --run results/grant_candidate_v0.3 \
    --ground-truth datasets/v0.3/ground_truth

echo ""
echo "================================================================================"
echo "    REPRODUCTION COMPLETE: Artifacts saved to results/grant_candidate_v0.3/"
echo "================================================================================"
