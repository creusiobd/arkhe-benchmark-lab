# ARKHÉ Agent Boundary Defense Benchmark — Relatório de Avaliação (n=65)

> **Status:** Execução Blind Concluída • **Zero Label Leakage** • **Avaliador Cego Independente**

## 1. Placar de Performance Empírica com Incerteza Estatística (IC 95%)

| Detector | Modo | n | Precisão (IC 95%) | Recall (IC 95%) | F1-Score | FP | FN | Lead Steps Mediano (IC 95%) | Taxa Antecipação |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Deterministic-Event-Rule-Baseline** | Evento Isolado | 65 | 47.6% [33.4, 62.3] | 100.0% [83.9, 100.0] | 0.65 | 22 | 0 | +0.0 [0.0, 0.0] | 0.0% |
| **Semantic-Event-Classifier-Baseline** | Evento Isolado | 65 | 76.0% [56.6, 88.5] | 95.0% [76.4, 99.1] | 0.84 | 6 | 1 | +0.0 [0.0, 0.0] | 15.0% |
| **ARKHÉ-Trajectory-Sentinel** | Orientado a Trajetória | 65 | 100.0% [83.9, 100.0] | 100.0% [83.9, 100.0] | 1.00 | 0 | 0 | +1.0 [1.0, 1.0] | 100.0% |

---

## 2. Testes de Hipótese Estatística Pareados

A hipótese primária $H_1$ postula que a observabilidade de trajetória reduz substancialmente os falsos positivos (preservando o recall) frente a guardrails de evento isolado. A hipótese secundária $H_2$ avalia a antecipação temporal ($N_{\text{lead}} > 0$).

### Comparação Pareada: `ARKHÉ-Trajectory-Sentinel_vs_Deterministic-Event-Rule-Baseline`

#### A. Teste de McNemar (Acurácia / Redução de Erros Pareados)
- **Pares Discordantes:** b (ARKHÉ correto, Baseline errado) = 22, c (ARKHÉ errado, Baseline correto) = 0
- **Razão de Discordância (Odds Ratio b/c):** inf
- **p-valor Exato Binomial:** 0.0 (Estatisticamente Significativo p < 0.05)

#### B. Teste dos Postos Sinalizados de Wilcoxon (Antecipação Lead Steps)
- **W-Statistic:** 0
- **Z-Score:** 3.9199
- **p-valor:** 8.9e-05 (Estatisticamente Significativo p < 0.01)
- **Tamanho do Efeito (r):** 0.8765

### Comparação Pareada: `ARKHÉ-Trajectory-Sentinel_vs_Semantic-Event-Classifier-Baseline`

#### A. Teste de McNemar (Acurácia / Redução de Erros Pareados)
- **Pares Discordantes:** b (ARKHÉ correto, Baseline errado) = 7, c (ARKHÉ errado, Baseline correto) = 0
- **Razão de Discordância (Odds Ratio b/c):** inf
- **p-valor Exato Binomial:** 0.015625 (Estatisticamente Significativo p < 0.05)

#### B. Teste dos Postos Sinalizados de Wilcoxon (Antecipação Lead Steps)
- **W-Statistic:** 0
- **Z-Score:** 3.6214
- **p-valor:** 0.000293 (Estatisticamente Significativo p < 0.01)
- **Tamanho do Efeito (r):** 0.8783

---

## 3. Resumo de Custos e Consumo de Tokens no Piloto

- **Trajetórias Avaliadas:** 65
- **Total de Passos Inspecionados:** 846
- **Tokens Equivalentes:** 820620 (719100 entrada, 101520 saída)
- **Custo Operacional Local (Offline):** $0.00 USD
- **Custo Estimado em API Comercial (gpt-4o-mini):** $0.1688 USD

---

## 4. Limitações e Ressalvas Metodológicas Obrigatórias

1. **Amostra Avaliada (n=65):** O benchmark comprova a integridade e viabilidade do pipeline e dos contratos, mas conclusões epidemiológicas e definitivas de segurança exigem a expansão para larga escala (N=5.000+).
2. **Ambiente Sintético:** Os cenários utilizam sinks locais simulados e credenciais sintéticas marcadas, evitando qualquer impacto em infraestrutura de terceiros.
3. **Determinismo:** Os baselines locais empregam heurísticas determinísticas e proxies semânticos reproduzíveis, documentados como tal.
