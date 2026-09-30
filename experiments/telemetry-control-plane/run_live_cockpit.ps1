# PowerShell Script para Iniciar a Torre de Controle Interativa em Tempo Real

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   ARKHÉ SENTINEL: TORRE DE CONTROLE INTERATIVA EM TEMPO REAL     " -ForegroundColor Cyan
Write-Host "   Concorrência Física + Injeção de Caos com 1 Clique             " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

$labPath = (Get-Location).Path

# 1. Inicia o Servidor Unificado (API + Cockpit Web) na porta 8080
Write-Host "[1/3] Iniciando Servidor Unificado (Porta 8080)..." -ForegroundColor Yellow
$appProc = Start-Process python -ArgumentList "-m uvicorn app:app --port 8080 --host 0.0.0.0" -WorkingDirectory $labPath -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3

# 2. Inicia o Emissor de Transações Simultâneas (80 TPS)
Write-Host "[2/3] Iniciando Emissor de Carga (80 TPS nominais com retries)..." -ForegroundColor Yellow
$loadProc = Start-Process python -ArgumentList "load_gen.py" -WorkingDirectory $labPath -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2

# 3. Abre o Cockpit Interativo no Navegador
Write-Host "[3/3] Abrindo Cockpit Interativo no navegador padrão..." -ForegroundColor Green
Start-Process "http://localhost:8080"

Write-Host "`n[✓] Cockpit Interativo ATIVO em: http://localhost:8080" -ForegroundColor Green
Write-Host "    Pressione [Ctrl+C] nesta janela para encerrar o teste.`n" -ForegroundColor Gray

try {
    while ($true) {
        Start-Sleep -Seconds 2
    }
}
finally {
    Write-Host "`n[*] Encerrando processos da simulação..." -ForegroundColor Yellow
    if ($loadProc) { Stop-Process -Id $loadProc.Id -Force -ErrorAction SilentlyContinue }
    if ($appProc) { Stop-Process -Id $appProc.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "[✓] Todos os processos foram finalizados com sucesso." -ForegroundColor Green
}
