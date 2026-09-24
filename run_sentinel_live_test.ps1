# PowerShell Script para Execução do Teste Conjunto:
# ARKHÉ SENTINEL monitorando o Ambiente de Validação sob Tráfego Simultâneo

param(
    [double]$DurationSeconds = 90.0
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   TESTE CONJUNTO: ARKHÉ SENTINEL vs AMBIENTE DE VALIDAÇÃO        " -ForegroundColor Cyan
Write-Host "   Tráfego Simultâneo de Cartões (80 TPS) + Análise de Trajetória " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Verifica se a API do Sentinel na porta 8000 está respondendo
Write-Host "[1/4] Verificando ARKHÉ SENTINEL na porta 8000..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 2
    Write-Host "      -> ARKHÉ SENTINEL ATIVO (Status: $($health.status), Modo: $($health.mode))" -ForegroundColor Green
} catch {
    Write-Host "      -> Sentinel não detectado na porta 8000. Iniciando em background..." -ForegroundColor Gray
    $sentinelPath = "C:\Users\anonimo\Downloads\arkhe-sentinel-trajectory-core-main"
    $sentinelProc = Start-Process python -ArgumentList "-m uvicorn api.main:app --port 8000" -WorkingDirectory $sentinelPath -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# 2. Inicia o Card Authorization Lab na porta 8080
Write-Host "[2/4] Iniciando Servidor de Validação de Cartões na porta 8080..." -ForegroundColor Yellow
$labPath = (Get-Location).Path
$labProc = Start-Process python -ArgumentList "-m uvicorn app:app --port 8080 --host 127.0.0.1" -WorkingDirectory $labPath -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3

# 3. Inicia o Gerador de Carga Simultânea (80 TPS)
Write-Host "[3/4] Iniciando Emissor de Carga (80 transações simultâneas/segundo)..." -ForegroundColor Yellow
$loadProc = Start-Process python -ArgumentList "load_gen.py" -WorkingDirectory $labPath -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2

# Abre o cockpit mestre no navegador padrão
Start-Process "http://localhost:8080"

# 4. Executa o Sentinel Live Monitor na janela principal
Write-Host "[4/4] Conectando ARKHÉ SENTINEL para monitoramento contínuo da fila..." -ForegroundColor Green
Write-Host "      Acompanhe o HUD no console ou a tela no navegador!`n" -ForegroundColor Cyan

try {
    python sentinel_live_monitor.py $DurationSeconds
}
finally {
    Write-Host "`n[*] Encerrando gerador de carga e ambiente de validação..." -ForegroundColor Yellow
    if ($loadProc) { Stop-Process -Id $loadProc.Id -Force -ErrorAction SilentlyContinue }
    if ($labProc) { Stop-Process -Id $labProc.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "[✓] Processos limpos com sucesso. O Sentinel na porta 8000 permanece ativo." -ForegroundColor Green
}
