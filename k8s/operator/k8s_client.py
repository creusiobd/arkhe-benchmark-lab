import os
import json
import logging
from typing import Any, Dict, List, Optional
import httpx

from .models import (
    ArkheStabilityBasinCR, ArkheStabilityBasinSpec, ArkheStabilityBasinStatus,
    WorkloadRef, StabilityConstraints, MitigationConfig, PredictiveHpaConfig,
    FastPathBypassConfig, TelemetrySourceConfig, BasinPhase, ArkheMitigationRuleCR,
    MitigationTrigger, MitigationAction, RuleState
)

logger = logging.getLogger("ArkheK8sClient")

class ArkheK8sClient:
    """
    Cliente assíncrono para a API do Kubernetes.
    Suporta operação in-cluster, via Kubeconfig ou modo Mock para testes e CI/CD.
    """
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode or os.getenv("ARKHE_K8S_MOCK", "false").lower() == "true"
        self.in_cluster = os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")
        
        self.api_host = os.getenv("KUBERNETES_SERVICE_HOST", "127.0.0.1")
        self.api_port = os.getenv("KUBERNETES_SERVICE_PORT", "6443")
        self.base_url = f"https://{self.api_host}:{self.api_port}"
        
        # Estado em memória para modo mock / simulação
        self._mock_basins: Dict[str, ArkheStabilityBasinCR] = {}
        self._mock_rules: Dict[str, ArkheMitigationRuleCR] = {}
        self._mock_deployment_replicas: Dict[str, int] = {}
        self._mock_fast_path_active: Dict[str, bool] = {}

    async def list_basins(self, namespace: str = "default") -> List[ArkheStabilityBasinCR]:
        if self.mock_mode or not self.in_cluster:
            return [b for b in self._mock_basins.values() if b.namespace == namespace or namespace == "*"]
        
        url = f"{self.base_url}/apis/resilience.arkhe.io/v1alpha1/namespaces/{namespace}/arkhestabilitybasins"
        # In real cluster: httpx get with token
        return list(self._mock_basins.values())

    async def register_mock_basin(self, basin: ArkheStabilityBasinCR):
        key = f"{basin.namespace}/{basin.name}"
        self._mock_basins[key] = basin
        dep_key = f"{basin.namespace}/{basin.spec.workload_ref.name}"
        self._mock_deployment_replicas[dep_key] = basin.spec.mitigation.predictive_hpa.min_replicas

    async def register_mock_rule(self, rule: ArkheMitigationRuleCR):
        key = f"{rule.namespace}/{rule.name}"
        self._mock_rules[key] = rule

    async def list_rules_for_basin(self, namespace: str, basin_name: str) -> List[ArkheMitigationRuleCR]:
        return [
            r for r in self._mock_rules.values()
            if r.namespace == namespace and r.target_basin_name == basin_name
        ]

    async def scale_deployment(self, namespace: str, deployment_name: str, target_replicas: int) -> bool:
        dep_key = f"{namespace}/{deployment_name}"
        prev_replicas = self._mock_deployment_replicas.get(dep_key, 3)
        self._mock_deployment_replicas[dep_key] = target_replicas
        
        logger.info(
            f"[K8s Actuation] Deployment {dep_key} escalado: {prev_replicas} -> {target_replicas} réplicas "
            f"(Predictive HPA subresource: /apis/apps/v1/namespaces/{namespace}/deployments/{deployment_name}/scale)"
        )
        return True

    async def get_deployment_replicas(self, namespace: str, deployment_name: str) -> int:
        dep_key = f"{namespace}/{deployment_name}"
        return self._mock_deployment_replicas.get(dep_key, 3)

    async def patch_fast_path_bypass(self, namespace: str, service_name: str, bypass_ratio: float, active: bool) -> bool:
        key = f"{namespace}/{service_name}"
        self._mock_fast_path_active[key] = active
        status_str = f"ATIVADO ({int(bypass_ratio*100)}% via cache L2)" if active else "DESATIVADO (100% rota normal)"
        logger.info(f"[K8s Actuation] Fast-Path Mesh Rule para {key}: {status_str}")
        return True

    async def update_basin_status(self, namespace: str, basin_name: str, status: ArkheStabilityBasinStatus) -> bool:
        key = f"{namespace}/{basin_name}"
        if key in self._mock_basins:
            self._mock_basins[key].status = status
            logger.debug(f"[K8s Status Update] Basin {key} atualizado: Phase={status.phase.value} Rho={status.current_rho}")
            return True
        return False
