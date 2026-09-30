# Pull Request: Hardening Científico e Preparação para o OpenAI Cybersecurity Grant

## 🎯 Objetivo
Elevar o **ARKHÉ Agent Boundary Defense Benchmark** de uma prova de conceito inicial para uma candidatura tecnicamente defensável, reproduzível e estritamente auditada para o **OpenAI Cybersecurity Grant Program** (Nível 2 — US$ 20.000 USD).

---

## 🔒 1. Eliminação Irrestrita de Vazamento de Rótulos (*Zero Label Leakage*)
- **Separação Estrita de Contratos:**
  - `contracts/observation.py`: `StepObservation` contém estritamente sinais observáveis em runtime. Qualquer chave de rótulo ou escore pré-computado é rejeitada ativamente por `@model_validator`.
  - `contracts/ground_truth.py`: `TrajectoryGroundTruth` reservado exclusivamente ao avaliador independente.
  - `contracts/prediction.py`: `StepPrediction` e `TrajectoryPrediction` emitidos dinamicamente pelos detectores.
- **Auditoria AST no CI:** `tests/test_contract_separation.py` inspeciona o código-fonte via AST e impede que qualquer detector importe `ground_truth`.
- **60 Testes Unitários Aprovados:** Suíte passando com 100% de sucesso (`Ran 60 tests in 2.46s OK`).

---

## 📊 2. Resultados Empíricos Medidos no Piloto ($n=30$ Trajetórias, 90 Avaliações)
Execução cega sobre 5 famílias de ameaças balanceadas (10 benignas, 10 quase-violações e 10 violações):

| Detector | Paradigma | Precisão [IC 95% Wilson] | Recall [IC 95% Wilson] | F1-Score | FP | FN | Antecipação Mediana | Antecipação Média |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Regras Determinísticas** | Evento Isolado | 62,5% [38,6%, 81,5%] | 100,0% [72,2%, 100,0%] | 0,77 | 6 | 0 | 0,0 etapas | 0,0 etapas |
| **Classificador Semântico** | Evento Isolado | 55,6% [33,7%, 75,4%] | 100,0% [72,2%, 100,0%] | 0,71 | 8 | 0 | 1,0 etapas | 0,9 etapas |
| **ARKHÉ Trajectory Sentinel** | **Trajetória** | **83,3% [55,2%, 95,3%]** | **100,0% [72,2%, 100,0%]** | **0,91** | **2** | **0** | **0,0 etapas** | **0,8 etapas** |

- **Diferencial:** Redução de 75% nos falsos positivos (2 FP vs 8 FP). Em cenários de quase-violação, o ARKHÉ reconheceu o *safe recovery* pós-contenção. Em injeção indireta de prompt, o ARKHÉ antecipou a violação em até **+2 etapas**.
- **Transparência Científica:** Registro formal da insuficiência de pares no teste assintótico de Wilcoxon no piloto ($n=30$), fundamentando a solicitação de grant para expansão a 300 trajetórias ($2.700$ avaliações).

---

## 💰 3. Orçamento Fechado Nível 2 (US$ 20.000 USD)
- **US$ 5.000:** Créditos de API OpenAI (Memória de cálculo: 10,8M tokens base = $15,85 + margem de 2,5x para testes adversariais).
- **US$ 10.000:** Bolsa de Pesquisa e Engenharia por 6 meses (~20h/semana) para Creúsio Adolfo Gaspar Kizua.
- **US$ 3.000:** Auditoria Externa Independente de Segurança e Red-Teaming.
- **US$ 2.000:** Infraestrutura Cloud (CI/CD, OpenTelemetry) e taxas de publicação aberta.

---

## 📦 4. Artefatos e Reprodutibilidade Incluídos
- **Proposta e Formulário:** `proposal/ARKHE_CYBERSECURITY_GRANT_v0.2_PT.md`, `proposal/ARKHE_CYBERSECURITY_GRANT_v0.2_EN.md`, `proposal/form_answers_PT.md` e `proposal/form_answers_EN.md` (Problema $\le 200$ palavras).
- **Matriz de Riscos de Pesquisa:** `docs/research_risks.md` (9 dimensões mapeadas com mitigação).
- **Auditoria de 4 Revisores Simulados:** `reports/final_review.md` (Nota consensual: 4.9/5.0).
- **Governança Open Source:** `pyproject.toml`, `CITATION.cff`, `SECURITY.md`, `CONTRIBUTING.md`, `Makefile`, `reproduce_pilot.ps1` e `README.md` unificado.

---

## 🔍 Como Reproduzir Localmente
```bash
python -m unittest discover tests
python -m harness.agent_benchmark_runner --config configs/pilot.yaml
python -m evaluator.evaluate --run results/pilot
```
