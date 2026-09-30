# ==============================================================================
# ARKHÉ Agent Boundary Defense Benchmark — Deterministic Dataset Reproduction
# PowerShell Script (Windows)
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "   ARKHÉ BENCHMARK -- DETERMINISTIC DATASET REPRODUCTION PROTOCOL" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

$PythonBin = "python"
try {
    $ver = & $PythonBin --version 2>&1
    Write-Host "• Python executable: $ver" -ForegroundColor Green
} catch {
    Write-Error "Python not found in PATH. Please install Python 3.10+."
}

# Step 1: Run reproduction unit tests
Write-Host "`n--- [1/2] Running Determinism & Anti-Leakage Unit Tests ---" -ForegroundColor Yellow
& $PythonBin -m unittest tests/test_deterministic_reproduction.py -v
if ($LASTEXITCODE -ne 0) {
    Write-Error "Determinism tests failed with exit code $LASTEXITCODE"
}

# Step 2: Run dual-generation verification verifier with tracked sync check
Write-Host "`n--- [2/2] Running Dual-Run Bitwise Verification and Tracked Hash Check ---" -ForegroundColor Yellow
& $PythonBin scripts/verify_deterministic_dataset_generation.py --config configs/hard_candidate_v0.4.yaml --check-tracked
if ($LASTEXITCODE -ne 0) {
    Write-Error "Dual-run deterministic verification failed with exit code $LASTEXITCODE"
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "    DETERMINISTIC VERIFICATION COMPLETE: 100% Bitwise Match Confirmed." -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
