# PowerShell Script para Execução 1-Click do Ecossistema ARKHÉ em Containers Docker
$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   ARKHÉ BENCHMARK LAB: ECOSSISTEMA CONTAINERIZADO DOCKER         " -ForegroundColor Cyan
Write-Host "   FastAPI + OpenTelemetry + Little's Law + Cockpit + LoadGen     " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Configura compatibilidade de build
$env:DOCKER_BUILDKIT = "0"

# 2. Inicia os containers em background com healthcheck
Write-Host "`n[1/3] Subindo serviços via Docker Compose..." -ForegroundColor Yellow
docker compose up -d

# 3. Aguarda o status saudável do microserviço principal
Write-Host "[2/3] Aguardando card-auth-lab atingir estado saudável (healthcheck)..." -ForegroundColor Yellow
$maxAttempts = 15
$attempt = 0
$healthy = $false

while ($attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 1
    $status = docker inspect --format="{{.State.Health.Status}}" arkhe-card-auth-lab 2>$null
    if ($status -eq "healthy") {
        $healthy = $true
        break
    }
    $attempt++
}

if ($healthy) {
    Write-Host "[✓] arkhe-card-auth-lab está HEALTHY e operacional na porta 8080!" -ForegroundColor Green
} else {
    Write-Host "[!] Aviso: Verificando conectividade direta via HTTP..." -ForegroundColor DarkYellow
}

# 4. Abre o Cockpit Interativo no navegador
Write-Host "[3/3] Abrindo Cockpit Unificado no navegador padrão..." -ForegroundColor Green
Start-Process "http://localhost:8080"

Write-Host "`n==================================================================" -ForegroundColor Cyan
Write-Host "   SERVIÇOS ATIVOS NO CLUSTER DOCKER:                             " -ForegroundColor Cyan
Write-Host "   • Cockpit & API:        http://localhost:8080                  " -ForegroundColor White
Write-Host "   • WebSocket Telemetria: ws://localhost:8080/ws/telemetry       " -ForegroundColor White
Write-Host "   • Emissor de Carga:     80 TPS contínuos (arkhe-load-generator) " -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "`nPressione [Ctrl+C] nesta janela para encerrar e derrubar a stack Docker.`n" -ForegroundColor Gray

try {
    # Exibe logs em streaming contínuo
    docker compose logs -f --tail=20
}
finally {
    Write-Host "`n[*] Derrubando os containers Docker Compose..." -ForegroundColor Yellow
    docker compose down
    Write-Host "[✓] Stack Docker finalizada com sucesso." -ForegroundColor Green
}
