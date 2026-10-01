# ==============================================================================
# ARKHÉ Agent Boundary Defense Benchmark — Deterministic Reproduction Script
# Version: v0.3 (OpenAI Cybersecurity Grant Candidate) - PowerShell
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "    ARKHE BENCHMARK -- DETERMINISTIC REPRODUCTION PIPELINE (v0.3)" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# Locate Python
$PythonBin = "python"
try {
    $ver = & $PythonBin --version 2>&1
    Write-Host "• Python executable: $ver" -ForegroundColor Green
} catch {
    Write-Error "Python not found in PATH. Please install Python 3.10+."
}

# Step 1: Run complete test suite and anti-leakage contract checks
Write-Host "`n--- [1/4] Running Unit Tests and Anti-Leakage Contract Verification ---" -ForegroundColor Yellow
& $PythonBin -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "Unit tests failed with exit code $LASTEXITCODE"
}

# Step 2: Ensure v0.3 dataset exists
Write-Host "`n--- [2/4] Verifying v0.3 Dataset Integrity ---" -ForegroundColor Yellow
if (-not (Test-Path "datasets/v0.3/observations")) {
    Write-Host "• Dataset v0.3 not found. Generating with seed 20260930..." -ForegroundColor Cyan
    & $PythonBin scripts/generate_v03_dataset.py
} else {
    $obsCount = (Get-ChildItem "datasets/v0.3/observations/*.jsonl").Count
    Write-Host "• Dataset v0.3 verified: $obsCount observation splits." -ForegroundColor Green
}

# Step 3: Run blind benchmark execution harness
Write-Host "`n--- [3/4] Executing Blind Benchmark Runner (configs/grant_candidate_v0.3.yaml) ---" -ForegroundColor Yellow
& $PythonBin -m harness.agent_benchmark_runner --config configs/grant_candidate_v0.3.yaml
if ($LASTEXITCODE -ne 0) {
    Write-Error "Benchmark runner failed with exit code $LASTEXITCODE"
}

# Step 4: Run independent evaluator
Write-Host "`n--- [4/4] Running Independent Statistical Evaluator ---" -ForegroundColor Yellow
& $PythonBin -m evaluator.evaluate --run results/grant_candidate_v0.3 --ground-truth datasets/v0.3/ground_truth
if ($LASTEXITCODE -ne 0) {
    Write-Error "Evaluator failed with exit code $LASTEXITCODE"
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "    REPRODUCTION COMPLETE: Artifacts saved to results/grant_candidate_v0.3/" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
