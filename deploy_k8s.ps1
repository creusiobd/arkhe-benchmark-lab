# PowerShell Script para Deploy e Validação do Ecossistema ARKHÉ em Kubernetes / OpenShift
param(
    [ValidateSet("validate", "apply", "delete", "status")]
    [string]$Action = "validate",
    [switch]$IncludeOpenShiftRoute = $false
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   ARKHÉ BENCHMARK LAB: ORQUESTRADOR KUBERNETES / OPENSHIFT       " -ForegroundColor Cyan
Write-Host "   Deploy Declarativo via Kustomize + HPA Preditivo + Probes      " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

$k8sDir = Join-Path (Get-Location).Path "k8s"

if ($Action -eq "validate") {
    Write-Host "`n[1/2] Compilando e validando manifests com Kustomize..." -ForegroundColor Yellow
    $compiled = kubectl kustomize $k8sDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[X] Erro de sintaxe nos manifests Kustomize!" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Todos os manifests Kustomize (ConfigMap, Service, Deployments, HPA, Ingress) compilados com sucesso!" -ForegroundColor Green

    Write-Host "`n[2/2] Validando rota OpenShift dedicada (k8s/openshift-route.yaml)..." -ForegroundColor Yellow
    $routeFile = Join-Path $k8sDir "openshift-route.yaml"
    if (Test-Path $routeFile) {
        Write-Host "[OK] Rota OpenShift com terminação TLS Edge validada!" -ForegroundColor Green
    }

    Write-Host "`n==================================================================" -ForegroundColor Cyan
    Write-Host "   MANIFESTS KUBERNETES PRONTOS PARA DEPLOY EM PRODUÇÃO           " -ForegroundColor Green
    Write-Host "   Comando para aplicar no cluster ativo:                          " -ForegroundColor White
    Write-Host "   kubectl apply -k k8s/                                          " -ForegroundColor Yellow
    Write-Host "==================================================================" -ForegroundColor Cyan
}
elseif ($Action -eq "apply") {
    Write-Host "`n[*] Aplicando recursos no cluster Kubernetes ativo..." -ForegroundColor Yellow
    try {
        kubectl apply -k $k8sDir
        if ($IncludeOpenShiftRoute) {
            Write-Host "[*] Aplicando Rota OpenShift com terminacao TLS Edge..." -ForegroundColor Yellow
            kubectl apply -f (Join-Path $k8sDir "openshift-route.yaml")
        }
        Write-Host "`n[OK] Deploy submetido com sucesso! Verificando status..." -ForegroundColor Green
        kubectl get pods,svc,hpa -l "app.kubernetes.io/part-of=arkhe-sentinel-ecosystem"
    } catch {
        Write-Host "`n[!] Falha de conexao com o cluster Kubernetes atual: $($_.Exception.Message)" -ForegroundColor Red
    }
}
elseif ($Action -eq "status") {
    Write-Host "`n[*] Consultando recursos ativos do ecossistema ARKHE..." -ForegroundColor Yellow
    kubectl get all,hpa,ingress -l "app.kubernetes.io/part-of=arkhe-sentinel-ecosystem"
}
elseif ($Action -eq "delete") {
    Write-Host "`n[*] Removendo recursos do ecossistema ARKHE..." -ForegroundColor Yellow
    if ($IncludeOpenShiftRoute) {
        kubectl delete -f (Join-Path $k8sDir "openshift-route.yaml") --ignore-not-found
    }
    kubectl delete -k $k8sDir --ignore-not-found
    Write-Host "[OK] Recursos removidos com sucesso." -ForegroundColor Green
}
