# ARKHÉ Agent Boundary Defense Benchmark — Relatório de Avaliação do Piloto (n=30)

> **Status:** Piloto Técnico Limpo Concluído • **Zero Label Leakage** • **Avaliador Cego Independente**

## 1. Placar de Performance Empírica com Incerteza Estatística (IC 95%)

| Detector | Modo | n | Precisão (IC 95%) | Recall (IC 95%) | F1-Score | FP | FN | Lead Steps Mediano (IC 95%) | Taxa Antecipação |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Deterministic-Event-Rule-Baseline** | Evento Isolado | 30 | 62.5% [38.6, 81.5] | 100.0% [72.2, 100.0] | 0.77 | 6 | 0 | +0.0 [0.0, 1.0] | 40.0% |
| **Semantic-Event-Classifier-Baseline** | Evento Isolado | 30 | 55.6% [33.7, 75.4] | 100.0% [72.2, 100.0] | 0.71 | 8 | 0 | +1.0 [0.0, 1.0] | 60.0% |
| **ARKHÉ-Trajectory-Sentinel** | Orientado a Trajetória | 30 | 83.3% [55.2, 95.3] | 100.0% [72.2, 100.0] | 0.91 | 2 | 0 | +0.0 [0.0, 1.0] | 40.0% |

---

## 2. Testes de Hipótese Estatística Pareados (Wilcoxon Signed-Rank Test)

### Comparação: `ARKHÉ-Trajectory-Sentinel_vs_Deterministic-Event-Rule-Baseline`
- *Nota de Incerteza:* Insufficient non-zero pairs (2 < 5) to compute valid Wilcoxon asymptotic distribution.

### Comparação: `ARKHÉ-Trajectory-Sentinel_vs_Semantic-Event-Classifier-Baseline`
- *Nota de Incerteza:* Insufficient non-zero pairs (4 < 5) to compute valid Wilcoxon asymptotic distribution.

---

## 3. Resumo de Custos e Consumo de Tokens no Piloto

- **Trajetórias Avaliadas:** 30
- **Total de Passos Inspecionados:** 372
- **Tokens Equivalentes:** 360840 (316200 entrada, 44640 saída)
- **Custo Operacional Local (Offline):** $0.00 USD
- **Custo Estimado em API Comercial (gpt-4o-mini):** $0.0742 USD

---

## 4. Limitações e Ressalvas Metodológicas Obrigatórias

1. **Amostra Piloto (n=30):** O piloto comprova a integridade e viabilidade do pipeline e dos contratos, mas conclusões epidemiológicas e definitivas de segurança exigem a expansão para o dataset completo N=300.
2. **Ambiente Sintético:** Os cenários utilizam sinks locais simulados e credenciais sintéticas marcadas, evitando qualquer impacto em infraestrutura de terceiros.
3. **Determinismo:** Os baselines locais empregam heurísticas determinísticas e proxies semânticos reproduzíveis, documentados como tal.
