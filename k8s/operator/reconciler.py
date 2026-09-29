import asyncio
import logging
import time
from typing import Dict, List, Optional
import httpx
import websockets
import json

from .models import (
    ArkheStabilityBasinCR, ArkheStabilityBasinStatus, BasinPhase,
    ArkheMitigationRuleCR, RuleState
)
from .k8s_client import ArkheK8sClient

logger = logging.getLogger("ArkheOperatorReconciler")

class ArkheOperatorReconciler:
    """
    Controlador de Reconciliação do Operador ARKHÉ.
    Monitora a Bacia de Estabilidade de Lyapunov em tempo real e orquestra a remediação nativa no K8s.
    """
    def __init__(self, k8s_client: ArkheK8sClient):
        self.k8s_client = k8s_client
        self.running = False
        self._mitigation_active: Dict[str, bool] = {}
        self._mitigation_activated_at: Dict[str, float] = {}

    async def reconcile_basin(self, basin: ArkheStabilityBasinCR, telemetry_payload: dict) -> ArkheStabilityBasinStatus:
        """
        Executa um ciclo de reconciliação para uma Bacia de Estabilidade específica.
        """
        key = f"{basin.namespace}/{basin.name}"
        spec = basin.spec
        constraints = spec.stability_constraints
        mit_cfg = spec.mitigation
        workload = spec.workload_ref

        # 1. Extração dos Observáveis de Telemetria
        obs = telemetry_payload.get("telemetry", {})
        resources = obs.get("resources", {})
        queueing = obs.get("queueing", {})
        sentinel = telemetry_payload.get("sentinel", {})
        projection = telemetry_payload.get("projection", {})

        current_rho = resources.get("antifraud_pool_utilization_ratio", 0.0)
        wq_ws = queueing.get("wq_ws_ratio", 0.0)
        sentinel_score = sentinel.get("score", 0.0)
        sentinel_triggered = sentinel.get("triggered", False)
        ttc_display = projection.get("time_to_collapse_display", "ESTÁVEL (∞)")
        ttc_sec = projection.get("time_to_collapse_sec")
        d_rho_dt = projection.get("d_rho_dt_per_min", 0.0)

        # 2. Avaliação da Bacia de Estabilidade de Lyapunov
        is_breached = (
            current_rho > constraints.max_rho_basin or
            wq_ws > constraints.max_queue_wait_ratio or
            sentinel_triggered or
            (ttc_sec is not None and ttc_sec <= constraints.critical_time_to_collapse_seconds)
        )

        now = time.time()
        active_mitigations = []
        target_phase = BasinPhase.LAMINAR_HEALTHY

        # 3. Lógica de Transição de Estado e Atuação em Malha Fechada
        if is_breached:
            if not self._mitigation_active.get(key, False):
                logger.warning(
                    f"🚨 [ARKHÉ K8s Controller] Rompimento detectado em {key}! "
                    f"Rho={current_rho:.2f} (Max={constraints.max_rho_basin}), "
                    f"Wq/Ws={wq_ws:.3f}, Sentinel Score={sentinel_score:.1f}, TTC={ttc_display}"
                )
                
                # Executa Ação 1: Predictive HPA (Escala Workload K8s)
                if mit_cfg.predictive_hpa.enabled:
                    current_reps = await self.k8s_client.get_deployment_replicas(basin.namespace, workload.name)
                    target_reps = min(
                        mit_cfg.predictive_hpa.max_replicas,
                        max(mit_cfg.predictive_hpa.min_replicas, int(current_reps * mit_cfg.predictive_hpa.scale_multiplier))
                    )
                    await self.k8s_client.scale_deployment(basin.namespace, workload.name, target_reps)
                    active_mitigations.append(f"PREDICTIVE_HPA_SCALE_TO_{target_reps}")

                # Executa Ação 2: Fast-Path Bypass (Configura Mesh / Cache L2)
                if mit_cfg.fast_path_bypass.enabled:
                    await self.k8s_client.patch_fast_path_bypass(
                        basin.namespace,
                        mit_cfg.fast_path_bypass.target_cache_service,
                        mit_cfg.fast_path_bypass.traffic_bypass_ratio,
                        active=True
                    )
                    active_mitigations.append(f"FAST_PATH_BYPASS_{int(mit_cfg.fast_path_bypass.traffic_bypass_ratio*100)}PCT")

                self._mitigation_active[key] = True
                self._mitigation_activated_at[key] = now
                target_phase = BasinPhase.MITIGATED

                # Dispara regras atômicas ArkheMitigationRule vinculadas
                rules = await self.k8s_client.list_rules_for_basin(basin.namespace, basin.name)
                for r in rules:
                    if r.state == RuleState.ARMED:
                        r.state = RuleState.TRIGGERED
                        r.trigger_count += 1
                        r.last_triggered_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                        logger.info(f"⚡ [Rule Triggered] ArkheMitigationRule {r.name}: {r.action.type}")

            else:
                target_phase = BasinPhase.MITIGATED
                active_mitigations = ["PREDICTIVE_HPA", "FAST_PATH_BYPASS"]

        else:
            # Sistema em regime não rompido
            if self._mitigation_active.get(key, False):
                elapsed = now - self._mitigation_activated_at.get(key, now)
                # Verifica cooldown de segurança antes de rollback
                if elapsed >= mit_cfg.predictive_hpa.cooldown_seconds and current_rho < 0.35:
                    logger.info(f"✅ [ARKHÉ K8s Controller] Estabilidade restabelecida em {key}. Iniciando rollback seguro...")
                    await self.k8s_client.scale_deployment(
                        basin.namespace, workload.name, mit_cfg.predictive_hpa.min_replicas
                    )
                    await self.k8s_client.patch_fast_path_bypass(
                        basin.namespace, mit_cfg.fast_path_bypass.target_cache_service, 0.0, active=False
                    )
                    self._mitigation_active[key] = False
                    target_phase = BasinPhase.RECOVERING
                else:
                    target_phase = BasinPhase.MITIGATED
                    active_mitigations = ["PREDICTIVE_HPA_COOLING_DOWN"]
            else:
                if current_rho > (constraints.max_rho_basin * 0.70):
                    target_phase = BasinPhase.DRIFT_WARNING
                else:
                    target_phase = BasinPhase.LAMINAR_HEALTHY

        # 4. Atualiza Status Subresource da CRD no Kubernetes
        current_reps = await self.k8s_client.get_deployment_replicas(basin.namespace, workload.name)
        new_status = ArkheStabilityBasinStatus(
            phase=target_phase,
            current_rho=round(current_rho, 4),
            current_wq_ws_ratio=round(wq_ws, 4),
            d_rho_dt_per_min=round(d_rho_dt, 3),
            time_to_collapse=ttc_display,
            current_replicas=current_reps,
            active_mitigations=active_mitigations,
            last_actuation_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ") if active_mitigations else basin.status.last_actuation_timestamp,
            observed_generation=basin.status.observed_generation + 1
        )

        await self.k8s_client.update_basin_status(basin.namespace, basin.name, new_status)
        return new_status
