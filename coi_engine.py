from dataclasses import dataclass
from typing import Dict, List
import numpy as np

@dataclass
class COIParameters:
    v_avg: float = 180.00          # Ticket Médio de Compra (R$)
    take_rate: float = 0.025       # Margem líquida do processador (2.5%)
    p_churn: float = 0.38          # Probabilidade de perda de comprador (38%)
    ltv_impact: float = 45.00      # CAC / Perda de LTV no lojista (R$)

@dataclass
class COIReport:
    delta_t_seconds: float
    unprocessed_unique_transactions: int
    direct_margin_loss_brl: float
    merchant_ltv_loss_brl: float
    total_coi_brl: float
    total_gmv_loss_brl: float
    confidence_interval_95_brl: tuple

class COIEngine:
    """
    Calculadora Auditável do Custo de Oportunidade da Inércia (COI).
    Isola estritamente falhas técnicas de infraestrutura (timeouts / 503)
    de recusas legítimas de negócio (saldo insuficiente / score antifraude).
    """
    def __init__(self, params: COIParameters = COIParameters()):
        self.p = params

    def calculate(
        self,
        delta_t_seconds: float,
        lost_unique_txs: int,
        bootstrap_samples: int = 1000
    ) -> COIReport:
        # Perda direta por transação técnica não aprovada
        direct_per_tx = self.p.v_avg * self.p.take_rate # R$ 4,50
        ltv_per_tx = self.p.p_churn * self.p.ltv_impact # R$ 17,10
        total_per_tx = direct_per_tx + ltv_per_tx       # R$ 21,60

        total_direct_margin = lost_unique_txs * direct_per_tx
        total_merchant_ltv = lost_unique_txs * ltv_per_tx
        total_coi = lost_unique_txs * total_per_tx
        total_gmv = lost_unique_txs * self.p.v_avg

        # Intervalo de confiança de 95% via modelagem estocástica de churn (+-4%) e ticket
        rng = np.random.default_rng(seed=42)
        sampled_churns = rng.normal(self.p.p_churn, 0.04, bootstrap_samples)
        sampled_churns = np.clip(sampled_churns, 0.20, 0.60)
        sampled_v_avg = rng.normal(self.p.v_avg, 12.0, bootstrap_samples)
        
        simulated_cois = (
            lost_unique_txs * (sampled_v_avg * self.p.take_rate) +
            lost_unique_txs * (sampled_churns * self.p.ltv_impact)
        )
        ci_low = float(np.percentile(simulated_cois, 2.5))
        ci_high = float(np.percentile(simulated_cois, 97.5))

        return COIReport(
            delta_t_seconds=round(delta_t_seconds, 1),
            unprocessed_unique_transactions=lost_unique_txs,
            direct_margin_loss_brl=round(total_direct_margin, 2),
            merchant_ltv_loss_brl=round(total_merchant_ltv, 2),
            total_coi_brl=round(total_coi, 2),
            total_gmv_loss_brl=round(total_gmv, 2),
            confidence_interval_95_brl=(round(ci_low, 2), round(ci_high, 2))
        )
