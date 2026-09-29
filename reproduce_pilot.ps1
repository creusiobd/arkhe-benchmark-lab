# ARKHÉ Agent Benchmark — Pilot Reproduction Script (PowerShell)
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ARKHÉ AGENT BOUNDARY DEFENSE BENCHMARK — PILOT REPRODUCTION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Write-Host "`n[1/3] Running automated unit tests and anti-leakage suites..." -ForegroundColor Yellow
python -m unittest discover tests
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Tests failed! Halting reproduction." -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/3] Running blind benchmark harness across 30 trajectories..." -ForegroundColor Yellow
python -m harness.agent_benchmark_runner --config configs/pilot.yaml
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Harness execution failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[3/3] Running independent evaluator and computing statistical metrics..." -ForegroundColor Yellow
python -m evaluator.evaluate --run results/pilot
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Evaluation failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`nSUCCESS: Pilot reproduction completed successfully!" -ForegroundColor Green
Write-Host "Artifacts generated in results/pilot/:" -ForegroundColor Green
Write-Host " - predictions.jsonl"
Write-Host " - execution_manifest.json"
Write-Host " - metrics.json"
Write-Host " - confidence_intervals.json"
Write-Host " - confusion_matrices.json"
Write-Host " - pilot_report.md"
