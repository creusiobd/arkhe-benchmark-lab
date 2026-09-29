import asyncio
import unittest
import time

from k8s.operator.models import (
    ArkheStabilityBasinCR, ArkheStabilityBasinSpec, ArkheStabilityBasinStatus,
    WorkloadRef, StabilityConstraints, MitigationConfig, PredictiveHpaConfig,
    FastPathBypassConfig, BasinPhase, ArkheMitigationRuleCR, MitigationTrigger,
    MitigationAction, RuleState
)
from k8s.operator.k8s_client import ArkheK8sClient
from k8s.operator.reconciler import ArkheOperatorReconciler

class TestArkheKubernetesOperator(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.k8s_client = ArkheK8sClient(mock_mode=True)
        self.reconciler = ArkheOperatorReconciler(self.k8s_client)

        self.basin = ArkheStabilityBasinCR(
            name="core-payments-basin",
            namespace="payments-prod",
            spec=ArkheStabilityBasinSpec(
                workload_ref=WorkloadRef(kind="Deployment", name="payment-authorization-service"),
                stability_constraints=StabilityConstraints(
                    target_throughput_tps=120.0,
                    max_rho_basin=0.50,
                    max_queue_wait_ratio=0.25,
                    critical_time_to_collapse_seconds=30
                ),
                mitigation=MitigationConfig(
                    predictive_hpa=PredictiveHpaConfig(
                        enabled=True,
                        min_replicas=3,
                        max_replicas=60,
                        scale_multiplier=2.0,
                        cooldown_seconds=10
                    ),
                    fast_path_bypass=FastPathBypassConfig(
                        enabled=True,
                        traffic_bypass_ratio=0.70,
                        target_cache_service="redis-l2-cache"
                    )
                )
            )
        )
        await self.k8s_client.register_mock_basin(self.basin)

        self.rule = ArkheMitigationRuleCR(
            name="rule-sentinel-scale",
            namespace="payments-prod",
            target_basin_name="core-payments-basin",
            trigger=MitigationTrigger(metric="sentinel_score", operator="Gte", threshold=70.0),
            action=MitigationAction(type="PredictiveScaleOut", parameters={"scaleMultiplier": 2.0})
        )
        await self.k8s_client.register_mock_rule(self.rule)

    def _build_telemetry(self, rho: float, wq_ws: float, score: float, triggered: bool, ttc_sec: float = None):
        return {
            "telemetry": {
                "resources": {
                    "antifraud_pool_utilization_ratio": rho,
                    "antifraud_pool_in_use": int(rho * 30),
                    "antifraud_pool_capacity": 30
                },
                "queueing": {
                    "avg_queue_wait_ms": wq_ws * 45.0,
                    "avg_service_time_ms": 45.0,
                    "wq_ws_ratio": wq_ws
                }
            },
            "sentinel": {
                "score": score,
                "triggered": triggered,
                "trigger_reason": "Vetor de instabilidade de Lyapunov" if triggered else None
            },
            "projection": {
                "time_to_collapse_sec": ttc_sec,
                "time_to_collapse_display": f"{ttc_sec}s" if ttc_sec else "ESTÁVEL (∞)",
                "d_rho_dt_per_min": 15.0 if triggered else 0.01
            }
        }

    async def test_reconcile_nominal_regime(self):
        """Valida que em regime laminar nominal o operador mantém o status saudável e 3 réplicas."""
        payload = self._build_telemetry(rho=0.10, wq_ws=0.005, score=5.0, triggered=False)
        status = await self.reconciler.reconcile_basin(self.basin, payload)

        self.assertEqual(status.phase, BasinPhase.LAMINAR_HEALTHY)
        self.assertEqual(status.current_replicas, 3)
        self.assertEqual(len(status.active_mitigations), 0)

    async def test_reconcile_drift_warning(self):
        """Valida que quando rho se aproxima do limite (ex: 40%), o status transita para DriftWarning."""
        payload = self._build_telemetry(rho=0.40, wq_ws=0.05, score=25.0, triggered=False)
        status = await self.reconciler.reconcile_basin(self.basin, payload)

        self.assertEqual(status.phase, BasinPhase.DRIFT_WARNING)
        self.assertEqual(status.current_replicas, 3)

    async def test_reconcile_critical_breach_and_autonomous_actuation(self):
        """Valida que sob colapso o operador escala o Deployment e ativa o Fast-Path."""
        payload = self._build_telemetry(rho=0.65, wq_ws=0.35, score=85.0, triggered=True, ttc_sec=4.0)
        status = await self.reconciler.reconcile_basin(self.basin, payload)

        # O status deve transitar para Mitigated
        self.assertEqual(status.phase, BasinPhase.MITIGATED)
        # O Deployment deve ter sido escalado de 3 para 6 réplicas (scaleMultiplier = 2.0x)
        reps = await self.k8s_client.get_deployment_replicas("payments-prod", "payment-authorization-service")
        self.assertEqual(reps, 6)
        self.assertEqual(status.current_replicas, 6)
        # Fast-Path deve estar ativo
        self.assertTrue(any("FAST_PATH_BYPASS" in m for m in status.active_mitigations))
        # A regra ArkheMitigationRule deve ter sido acionada
        self.assertEqual(self.rule.state, RuleState.TRIGGERED)
        self.assertEqual(self.rule.trigger_count, 1)

    async def test_cooldown_and_safe_rollback(self):
        """Valida que após o restabelecimento e cooldown o operador realiza rollback para 3 réplicas."""
        # 1. Aciona mitigação
        payload_rupture = self._build_telemetry(rho=0.65, wq_ws=0.35, score=85.0, triggered=True, ttc_sec=4.0)
        await self.reconciler.reconcile_basin(self.basin, payload_rupture)
        self.assertEqual(await self.k8s_client.get_deployment_replicas("payments-prod", "payment-authorization-service"), 6)

        # 2. Simula passagem do tempo de cooldown
        key = f"{self.basin.namespace}/{self.basin.name}"
        self.reconciler._mitigation_activated_at[key] = time.time() - 150.0  # 150s atrás (> 120s cooldown)

        # 3. Reconcilia com telemetria restaurada saudável (rho = 0.08)
        payload_recovered = self._build_telemetry(rho=0.08, wq_ws=0.002, score=4.0, triggered=False)
        status = await self.reconciler.reconcile_basin(self.basin, payload_recovered)

        self.assertEqual(status.phase, BasinPhase.RECOVERING)
        reps = await self.k8s_client.get_deployment_replicas("payments-prod", "payment-authorization-service")
        self.assertEqual(reps, 3)

if __name__ == "__main__":
    unittest.main()
