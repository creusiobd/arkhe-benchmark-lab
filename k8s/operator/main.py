import asyncio
import json
import logging
import os
import signal
import sys
import websockets
import httpx

from .models import (
    ArkheStabilityBasinCR, ArkheStabilityBasinSpec, WorkloadRef,
    StabilityConstraints, MitigationConfig, PredictiveHpaConfig,
    FastPathBypassConfig, ArkheMitigationRuleCR, MitigationTrigger,
    MitigationAction, RuleState
)
from .k8s_client import ArkheK8sClient
from .reconciler import ArkheOperatorReconciler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ArkheOperator")

async def run_operator():
    logger.info("=" * 70)
    logger.info("🚀 INICIANDO ARKHÉ KUBERNETES OPERATOR (v1alpha1)")
    logger.info("   Controle Cibernético Autônomo e Estabilidade de Lyapunov")
    logger.info("=" * 70)

    k8s_client = ArkheK8sClient()
    reconciler = ArkheOperatorReconciler(k8s_client)

    # Criação do Basin Padrão se estiver em modo mock / inicialização
    default_basin = ArkheStabilityBasinCR(
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
                predictive_hpa=PredictiveHpaConfig(enabled=True, min_replicas=3, max_replicas=60, scale_multiplier=2.0),
                fast_path_bypass=FastPathBypassConfig(enabled=True, traffic_bypass_ratio=0.70)
            )
        )
    )
    await k8s_client.register_mock_basin(default_basin)

    rule_hpa = ArkheMitigationRuleCR(
        name="rule-predictive-hpa",
        namespace="payments-prod",
        target_basin_name="core-payments-basin",
        trigger=MitigationTrigger(metric="sentinel_score", operator="Gte", threshold=70.0),
        action=MitigationAction(type="PredictiveScaleOut", parameters={"scaleMultiplier": 2.0})
    )
    await k8s_client.register_mock_rule(rule_hpa)

    logger.info("📋 ArkheStabilityBasin e ArkheMitigationRule carregados com sucesso.")
    telemetry_ws_url = os.getenv("TELEMETRY_WS_URL", "ws://127.0.0.1:8080/ws/telemetry")
    logger.info(f"🔗 Conectando ao canal telemétrico de alta resolução: {telemetry_ws_url} (20 FPS)...")

    reconciler.running = True

    while reconciler.running:
        try:
            async with websockets.connect(telemetry_ws_url, ping_interval=10, ping_timeout=5) as ws:
                logger.info("✅ Conexão WebSocket estabelecida com o pipeline telemétrico.")
                while reconciler.running:
                    raw_msg = await ws.recv()
                    payload = json.loads(raw_msg)
                    
                    basins = await k8s_client.list_basins("payments-prod")
                    for b in basins:
                        status = await reconciler.reconcile_basin(b, payload)

        except (websockets.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            logger.warning(f"⚠️ Conexão telemétrica indisponível ({e}). Tentando reconectar em 3s...")
            await asyncio.sleep(3.0)
        except Exception as e:
            logger.error(f"❌ Erro no loop de reconciliação: {e}", exc_info=True)
            await asyncio.sleep(2.0)

def main():
    try:
        asyncio.run(run_operator())
    except KeyboardInterrupt:
        logger.info("🛑 ARKHÉ Operator finalizado pelo operador.")

if __name__ == "__main__":
    main()
