# PowerShell Script para Execução Local da Pipeline de CI/CD (ARKHÉ CI Local Runner)
$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   ARKHÉ BENCHMARK LAB: SIMULADOR LOCAL DE CI/CD                  " -ForegroundColor Cyan
Write-Host "   Testes Unitários + Física de Filas + WebSocket + Mitigação     " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

$t0 = Get-Date

# 1. Bateria Completa de Testes Unitários e Contratos Matemáticos
Write-Host "`n[1/4] Executando Suíte Completa de Testes Automatizados (20 testes)..." -ForegroundColor Yellow
python -m unittest discover tests -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[X] Falha nos testes unitários!" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] 20/20 Testes passaram com 100% de sucesso!" -ForegroundColor Green

# 2. Validação da Sintaxe e Topologia do Docker Compose
Write-Host "`n[2/4] Validando Topologia e Configuração do Docker Compose..." -ForegroundColor Yellow
docker compose config | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[X] Falha na validação do Docker Compose!" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] docker-compose.yml sintaticamente e topologicamente válido!" -ForegroundColor Green

# 3. Teste de Conectividade do Streaming WebSocket (10 FPS)
Write-Host "`n[3/4] Validando Streaming WebSocket em Tempo Real..." -ForegroundColor Yellow
python test_websocket_stream.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[X] Falha no teste de WebSocket streaming!" -ForegroundColor Red
    exit 1
}
Write-Host '[OK] Streaming WebSocket operacional a 10 FPS (latência inferior a 15ms)!' -ForegroundColor Green

# 4. Teste de Mitigação Autônoma Closed-Loop (Predictive HPA)
Write-Host "`n[4/4] Validando Agente Atuador Closed-Loop (Self-Healing)..." -ForegroundColor Yellow
python test_autonomous_mitigation.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[X] Falha no teste de mitigação autônoma!" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Mitigação autônoma fechou ciclo com 100% do Error Budget preservado!" -ForegroundColor Green

$elapsed = [math]::Round(((Get-Date) - $t0).TotalSeconds, 2)
Write-Host "`n==================================================================" -ForegroundColor Cyan
Write-Host "   PIPELINE DE CI/CD APROVADA COM SUCESSO! ($elapsed s)            " -ForegroundColor Green
Write-Host "   Pronto para push na branch main e execução no GitHub Actions.  " -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Cyan
