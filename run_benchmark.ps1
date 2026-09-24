# PowerShell Script para Execução Automatizada do Benchmark ARKHÉ
param(
    [switch]$Docker,
    [double]$Scale = 8.0,
    [int]$Rounds = 5
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   ARKHÉ VALIDATION LAB: EXECUTOR AUTOMATIZADO DE BENCHMARK  " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if ($Docker) {
    Write-Host "[*] Iniciando ambiente via Docker Compose..." -ForegroundColor Yellow
    docker compose up --build -d
    
    Write-Host "[*] Aguardando estabilização dos containers..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
} else {
    Write-Host "[*] Verificando dependências Python locais..." -ForegroundColor Gray
    python -m pip install -r requirements.txt -q
    
    Write-Host "[*] Iniciando API Card Authorization Lab em background..." -ForegroundColor Yellow
    $appJob = Start-Job -ScriptBlock {
        param($path)
        Set-Location $path
        python -m uvicorn app:app --port 8080 --host 0.0.0.0
    } -ArgumentList (Get-Location).Path

    Start-Sleep -Seconds 3

    Write-Host "[*] Iniciando Gerador de Carga em background..." -ForegroundColor Yellow
    $loadJob = Start-Job -ScriptBlock {
        param($path)
        Set-Location $path
        python load_gen.py
    } -ArgumentList (Get-Location).Path

    Start-Sleep -Seconds 3
}

try {
    Write-Host "[*] Executando Orchestrador de Teste Cego ($Rounds rodadas, escala ${Scale}x)..." -ForegroundColor Green
    python benchmark_runner.py $Scale $Rounds
    
    Write-Host "[*] Gerando Relatório Visual HTML..." -ForegroundColor Green
    python report_generator.py
}
finally {
    if ($Docker) {
        Write-Host "[*] Desligando containers..." -ForegroundColor Yellow
        docker compose down
    } else {
        Write-Host "[*] Finalizando processos em background..." -ForegroundColor Yellow
        Stop-Job $appJob, $loadJob -ErrorAction SilentlyContinue
        Remove-Job $appJob, $loadJob -ErrorAction SilentlyContinue
    }
}

Write-Host "`n[✓] Execução concluída! Abra 'arkhe_benchmark_report.html' no navegador." -ForegroundColor Green
