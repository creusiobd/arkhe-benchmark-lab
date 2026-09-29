# Relatório de Auditoria Inicial (Fase 0)
## ARKHÉ Agent Boundary Defense Benchmark — Hardening para OpenAI Cybersecurity Grant

**Data:** 29 de Setembro de 2026  
**Auditor Responsável:** Engenheiro Principal de Segurança de IA & Especialista em Avaliação Experimental  
**Branch de Trabalho:** `feat/cybersecurity-grant-hardening`  
**Commit / Hash de Referência Inicial:** `81775f0` (Head local antes das migrações da Fase 1-17)

---

### 1. Estrutura Encontrada no Repositório

O repositório `arkhe-benchmark-lab` foi inspecionado em sua totalidade, revelando uma arquitetura híbrida decorrente da evolução do projeto:

```text
arkhe-benchmark-lab/
├── contracts/                  # Contratos semânticos Pydantic (agent_trajectory.py)
├── dataset/trajectories/       # Dataset preliminar em arquivos JSON individuais (n=3)
├── detectors/                  # Detectores preliminares (base, rule_based_event, semantic_event, arkhe_trajectory_sentinel)
├── harness/                    # Harness de execução (agent_benchmark_runner.py)
├── docs/                       # Documentação da proposta de grant e laudos preliminares
├── tests/                      # 13 suítes de teste cobrindo tanto o lab de filas quanto o benchmark agêntico
├── scripts/                    # Scripts de auditoria de sanitização e verificação de saúde
├── helm/ & k8s/                # Operador Kubernetes e Helm chart do cockpit de resiliência
├── otel/                       # Conectores OpenTelemetry e exportadores Prometheus
└── app.py & load_gen.py        # Microserviço e emulador da física de filas financeiras (Little's Law)
```

---

### 2. Comandos Executados e Resultados dos Testes Atuais

Todos os comandos foram executados sem modificações no ambiente:

| Comando | Escopo | Resultado | Duração |
| :--- | :--- | :---: | :---: |
| `python -m unittest discover tests` | Suíte completa com 13 arquivos de teste | **45/45 Aprovados (100% OK)** | 0.496s |
| `python harness/agent_benchmark_runner.py` | Avaliação dos 3 detectores sobre as 3 trajetórias canônicas | **Sucesso (Código 0)** | 1.82s |
| `python scripts/audit_sanitization.py` | Auditoria de credenciais, caminhos absolutos e arquivos scratch | **Aprovado (0 segredos / 0 caminhos / 0 scratches)** | 0.25s |

#### Placar de Execução do Harness Atual:
* **Deterministic-Event-Rule-Baseline-v1:** Lead Steps = +0.0 (Reativo), FP = 1, F1 = 0.67
* **Semantic-Event-Classifier-Baseline-v1:** Lead Steps = +1.0, FP = 0, F1 = 1.00
* **ARKHÉ-Trajectory-Sentinel-v1:** Lead Steps = +2.0, FP = 0, F1 = 1.00

---

### 3. Arquivos Inexistentes ou Referências Pendentes Citadas na Documentação

1. **Repositório Público Externo:** A URL `https://github.com/creusiobd/arkhe-benchmark-lab.git` citada nos comandos de reprodução requer verificação de sincronização após o término dos ajustes.
2. **DOI do Zenodo / Repositório HuggingFace:** Citados na proposta como entregáveis futuros do projeto completo ($N=300$). Devem ser explicitamente classificados como **entregáveis da pesquisa**, evitando qualquer insinuação de que já estão publicados.
3. **Divisão de Datasets JSONL (`development.jsonl`, `validation.jsonl`, `test.jsonl`):** Atualmente inexistente; o dataset anterior utilizava apenas 3 arquivos `.json` soltos na pasta `dataset/trajectories/`.

---

### 4. Riscos Metodológicos Identificados

1. **Tamanho Amostral Insuficiente para Afirmações Estatísticas ($n=3$):**  
   O conjunto atual de apenas 3 trajetórias serve como verificação técnica do código (*smoke test* da esteira), mas é estatisticamente frágil para sustentar generalizações de superioridade. É imperativo expandir para o piloto limpo formal de **30 trajetórias** ($5\text{ famílias} \times 3\text{ classes} \times 2\text{ variações}$) e calcular intervalos de confiança bootstrap.
2. **Acoplamento entre Camadas de Dados:**  
   Embora o arquivo `contracts/agent_trajectory.py` já tenha sido separado em `ObservableStep` e `TrajectoryGroundTruth`, as definições ainda residiam no mesmo módulo Python, permitindo que importações acidentais ou detectores mal-intencionados pudessem ter acesso a tipos de avaliação. A separação física em `contracts/observation.py`, `contracts/prediction.py` e `contracts/ground_truth.py` é indispensável.
3. **Circularidade de Features e Risco de Vazamento Léxico:**  
   Em versões anteriores do dataset, campos como `mission_divergence_score: 0.55`, `context_contamination_flag: true`, `accumulated_risk_score: 58.0` e `evidence: "Mission drift detected..."` entregavam o resultado ao detector antes da inferência. Na nova arquitetura, todos esses campos são rigorosamente banidos da observação.
4. **Ausência de Conjunto de Teste Selado (*Sealed Test Set*):**  
   Não havia divisão formal entre dados de calibração (treino/validação) e teste cego. O benchmark precisa separar os cenários por templates estruturais distintos.

---

### 5. Inconsistências entre Código, Proposta e Documentação

1. **README Raiz vs. Escopo de IA Agêntica:**  
   O arquivo `README.md` raiz ainda é dedicado quase exclusivamente à resiliência de filas financeiras e Teoria das Filas (M/M/c / Lei de Little). O projeto do benchmark de segurança de agentes precisa ser integrado e formalizado na raiz com instruções de compilação, instalação e reprodução (`pyproject.toml`, `Makefile`, etc.).
2. **Nomenclatura da Função de Risco:**  
   Textos mais antigos referiam-se a "Lyapunov semântica". Essa terminologia é prematura e vulnerável a críticas de pares acadêmicos antes de uma demonstração formal de estabilidade analítica. Deve ser uniformizada como **"função de risco acumulado da trajetória, inspirada em conceitos de estabilidade de sistemas dinâmicos"**.
3. **Orçamento e Nível 3:**  
   A proposta citava anteriormente uma expansão de US$ 40.000 (Nível 3). Para a submissão ao OpenAI Cybersecurity Grant, o escopo deve ser estritamente focado no **Nível 2 (US$ 20.000)**, com memória de cálculo transparente de tokens e remoção do Nível 3.

---

### 6. Plano de Ação das Próximas Fases

1. **Fase 1:** Preservar `ARKHE_PROPOSAL_v0.1_CONCEPT.md` em `proposal/archive/` e criar a versão de trabalho `proposal/ARKHE_CYBERSECURITY_GRANT_v0.2_PT.md`.
2. **Fase 2:** Criar os contratos estanques `contracts/observation.py`, `contracts/prediction.py`, `contracts/ground_truth.py`.
3. **Fase 3:** Implementar suíte de testes contra label leakage (`tests/test_no_label_leakage.py`, `tests/test_contract_separation.py`, `tests/test_dataset_isolation.py`, `tests/test_detector_inputs.py`).
4. **Fase 4:** Gerar o dataset piloto limpo com 30 trajetórias (5 famílias × 3 classes × 2 variações) divididas por template entre dev, val e test.
5. **Fase 5:** Implementar os 3 detectores formais (`detectors/deterministic_event.py`, `detectors/semantic_event.py`, `detectors/arkhe_trajectory.py`).
6. **Fase 6 & 7:** Implementar `harness/agent_benchmark_runner.py`, `configs/pilot.yaml`, `evaluator/evaluate.py` e `evaluator/statistics.py`.
7. **Fase 8 & 9:** Executar o piloto, gerar artefatos em `results/pilot/`, documentar reprodutibilidade.
8. **Fases 10 a 16:** Modelar custos de API, redigir propostas finais (PT/EN), formulários, registro de riscos e revisão dos 4 papéis de bancada.
