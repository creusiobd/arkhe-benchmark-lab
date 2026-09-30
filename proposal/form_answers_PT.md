# Respostas Oficiais para o Formulário de Submissão — OpenAI Cybersecurity Grant Program

Este documento contém as respostas consolidadas e auditadas para os campos do formulário de submissão do **OpenAI Cybersecurity Grant Program**, em português.

---

### Campo 1: Título do Projeto (Project Title)
**ARKHÉ Agent Boundary Defense Benchmark: Avaliação Empírica de Observabilidade de Trajetória contra Violações de Fronteira em Sistemas Multiagente**

---

### Campo 2: Descrição em Uma Frase (One-line Description)
Um benchmark defensivo e open source para avaliar se a observabilidade orientada à trajetória detecta desvio de missão, propagação de prompt injection e violações de fronteira em sistemas multiagente antes de mecanismos baseados em eventos isolados.

---

### Campo 3: Descrição do Problema que Busca Resolver (Problem Statement)
*(Restrição estrita: $\le 200$ palavras)*

Sistemas baseados em agentes autônomos executam tarefas corporativas encadeando dezenas de chamadas a ferramentas, leituras de contexto e comunicações externas. Nesses fluxos, cada ação isolada pode ser perfeitamente legítima e compatível com as políticas de acesso do agente. No entanto, em conjunto e ao longo do tempo, essas ações constroem uma trajetória cumulativa de risco.

Os mecanismos de defesa atuais — como guardrails por chamada, filtros semânticos atômicos e listas de bloqueio estáticas — sofrem de cegueira temporal. Eles avaliam a ferramenta invocada no instante imediato sem considerar a cadeia causal: o desvio silencioso da missão original (*mission drift*), o acúmulo de contexto contaminado por injeções indiretas e a aproximação gradual de fronteiras críticas de segurança.

Essa abordagem pontual gera uma vulnerabilidade estrutural: agentes sofrem sequestro de intenção e escalam privilégios silenciosamente, sendo detectados apenas quando a exfiltração ou a violação de política já foi consumada. O problema central é a ausência de benchmarks científicos abertos que mensurem quantitativamente se a observabilidade de trajetória é capaz de antecipar violações com ganho de etapas e redução de falsos positivos frente a guardrails por evento.

*(Contagem de palavras: 181 palavras — Aprovado sob o limite de 200 palavras)*

---

### Campo 4: Hipótese de Pesquisa e Metodologia (Research Hypothesis & Methodology)
**Hipótese Central:** Sinais fracos distribuídos na execução do agente — contaminação de contexto, mutação da intenção ativa em relação à missão declarada, expansão de ferramentas e persistência comportamental pós-contenção — permitem identificar desvios de segurança pelo menos 1 a 2 etapas antes de uma violação explícita consumada, mantendo taxas de falsos positivos inferiores às de guardrails semânticos isolados.

**Desenho Experimental e Eliminação de Vazamento:**
Para impedir circularidade experimental, o benchmark estabelece duas camadas estritamente isoladas:
1. *Camada Observável (`StepObservation`):* Disponibilizada aos detectores em tempo real contendo apenas identidade, missão declarada, ação sanitizada, capacidades, fronteiras e observações brutas (`raw_observation`). Nenhum rótulo ou escore pré-computado existe nessa camada.
2. *Ground Truth Reservado (`TrajectoryGroundTruth`):* Armazenado separadamente para uso exclusivo do avaliador cego, contendo classe real, passo da violação e justificativa causal humana.

**Escala e Tratamento Estatístico:**
O estudo avaliará 300 trajetórias canônicas equilibradas (120 benignas, 90 quase-violações e 90 violações) através de 5 famílias de ameaças em 3 repetições estocásticas (2.700 execuções totais). As métricas principais incluem o ganho de etapas ($N_{\text{lead}}$), F1-Score, precisão com intervalos de confiança de Wilson (95%) e teste não paramétrico pareado de Wilcoxon ($p < 0.01$) para rejeição da hipótese nula.

---

### Campo 5: Entregáveis e Resultados Esperados (Deliverables & Expected Outcomes)
1. **Dataset Aberto Canônico (300 Trajetórias):** Formato JSONL padronizado, catalogado por famílias de ameaça, licenciado sob CC-BY-4.0 e depositado no Zenodo (com DOI permanente) e HuggingFace.
2. **Harness e Suíte de Avaliação Open Source (Apache-2.0):** Repositório Python modular com separação formal de contratos, testes de não-vazamento por inspeção de AST e suporte a múltiplos backends.
3. **Três Detectores de Referência Auditáveis:** Implementação do baseline determinístico por regex, baseline semântico por chamada única (LLM proxy) e o *ARKHÉ Trajectory Sentinel*.
4. **Artigo Científico e Relatório Técnico Aberto:** Documentação completa da metodologia, formulação matemática da função de risco de Lyapunov agêntica e análise de significância estatística.
5. **Painel Interativo de Reprodutibilidade:** Visualizador web de trajetórias permitindo inspeção passo a passo da propagação de contaminação e divergência.

---

### Campo 6: Por Que Esta Abordagem é Estritamente Defensiva (Defensive Orientation & Safety)
O projeto é concebido e operado com foco exclusivo em segurança defensiva:
* **Dados Estritamente Sintéticos:** Todos os cenários utilizam chaves e tokens falsificados de padrão identificável (`ARKHE_FAKE_TOKEN_DO_NOT_USE_*`) e sumidouros de rede locais (`http://localhost:8080/mock-sink`), sem qualquer credencial ou endpoint de produção.
* **Ausência de Exploits Funcionais:** Os cenários avaliam a estrutura causal e comportamental do desvio de missão em abstração de alto nível, sem distribuir códigos de ataque de dia zero ou payloads armados.
* **Critério Defensivo:** O objetivo prático é capacitar engenheiros de segurança a calibrar guardrails com base em dados empíricos de antecipação temporal e controle de falsos positivos, protegendo ecossistemas multiagente contra injeções indiretas e desvios de intenção.

---

### Campo 7: Plano de Trabalho e Cronograma (Work Plan & Timeline — 6 Meses)
* **Mês 1 (M1 — Expansão e Formalização do Dataset):** Geração sintética e validação das 300 trajetórias canônicas nas 5 famílias com auditoria automatizada de não-vazamento.
* **Mês 2 (M2 — Reforço dos Baselines e Integração de APIs):** Integração com modelos OpenAI (`gpt-4o`, `gpt-4o-mini`) e consolidação dos guardrails por evento.
* **Mês 3 (M3 — Calibração do ARKHÉ Trajectory Sentinel):** Otimização e congelamento dos pesos dinâmicos da função de risco sobre os conjuntos de desenvolvimento e validação.
* **Mês 4 (M4 — Execução Experimental em Larga Escala):** Execução das 2.700 avaliações cegas; processamento estatístico completo (Wilson 95%, Wilcoxon pareado e Bootstrap).
* **Mês 5 (M5 — Auditoria Externa de Red-Teaming):** Revisão de segurança independente por terceiro para validar a robustez dos cenários e a inexistência de vazamento de rótulos.
* **Mês 6 (M6 — Disseminação e Lançamento Open Source):** Depósito do dataset no Zenodo/HuggingFace, publicação do repositório no GitHub sob Apache-2.0 e liberação do preprint técnico.

---

### Campo 8: Orçamento Detalhado e Justificativa (Detailed Budget & Justification)
**Nível Solicitado: Nível 2 — US$ 20.000 USD (Escopo Principal Fechado)**

1. **Créditos de API OpenAI — US$ 5.000 (25%):**
   * Custo analítico direto de execução das 2.700 rodadas e geração de dados: ~10,8 milhões de tokens (~US$ 15,85 aos preços de tabela).
   * O restante dos créditos compõe a margem de contingência essencial para ciclos iterativos de prompt engineering, varreduras adversariais de sensibilidade, calibração de hiperparâmetros e auditorias via LLM-as-a-judge com `gpt-4o`.
2. **Compensação por Pesquisa e Engenharia — US$ 10.000 (50%):**
   * Remuneração do Pesquisador Principal ao longo de 6 meses (~20 horas/semana) para desenvolvimento do harness, formalização matemática, garantia de separação estrita e testes estatísticos.
3. **Auditoria Independente de Segurança e Red-Teaming — US$ 3.000 (15%):**
   * Contratação de especialista externo independente em segurança de IA para auditar a rigidez dos contratos, certificar a inexistência de dados sensíveis reais e desafiar o dataset.
4. **Infraestrutura Cloud e Publicação Aberta — US$ 2.000 (10%):**
   * Ambientes de integração contínua (CI/CD), hospedagem de instâncias de teste com telemetria OpenTelemetry e taxas de publicação em acesso aberto.

---

### Campo 9: Capacidade de Execução e Experiência do Proponente (Applicant Background)
**Pesquisador Principal: Creúsio Adolfo Gaspar Kizua (São Paulo, Brasil)**
* Mais de **6 anos de experiência prática** em engenharia de sistemas de pagamentos de alta disponibilidade, observabilidade de alta escala e infraestrutura de missão crítica.
* **Liderança técnica de equipe de 13 engenheiros** operando ambientes bancários e transacionais em regime contínuo 24×7.
* **Governança técnica e observabilidade de 33 APIs reguladas**, com conformidade rigorosa a padrões de segurança cibernética (Resolução BACEN 85/2021 e PCI-DSS v4.0).
* Domínio aprofundado em telemetria e controle distribuído: OpenTelemetry, Kubernetes, Prometheus, Splunk, Dynatrace e Grafana.
* Criador da metodologia de inteligência de trajetória agêntica, integrando conceitos de física de filas e estabilidade dinâmica à defesa cibernética de agentes de IA.

---

### Campo 10: Reprodutibilidade e Abertura (Open Source Commitment)
* O projeto será distribuído sob licença permissiva **Apache-2.0**.
* O comitê avaliador já pode clonar e reproduzir o piloto funcional de 30 trajetórias com 60 testes unitários passando (`python -m unittest discover tests`, `python -m harness.agent_benchmark_runner --config configs/pilot.yaml`, `python -m evaluator.evaluate --run results/pilot`).
* Todos os artefatos de saída contam com hashes determinísticos SHA-256 e manifestos de execução auditáveis.

---

### Campo 11: Riscos e Mitigações (Risks & Mitigations)
* *Risco de Não-Significância Estatística:* Mitigado pelo escalonamento para 300 trajetórias canônicas com 3 repetições (2.700 avaliações) e teste pareado de Wilcoxon. Caso a hipótese seja refutada em casos específicos, o resultado será publicado com integridade científica.
* *Risco de Sobrecarga de Latência:* Mitigado por cálculo local (<5 ms) de divergência léxica e proximidade de fronteira, reservando verificações de LLM apenas para faixas de risco elevado.
* *Risco de Vazamento de Rótulos:* Mitigado por validadores Pydantic em runtime e testes de CI que inspecionam o código via AST.

---

### Campo 12: Modelos da OpenAI Utilizados e Justificativa (OpenAI Models & Rationale)
* **`gpt-4o` (snapshot `gpt-4o-2024-08-06`):** Utilizado na síntese de cenários adversariais complexos, geração de variações léxicas não vistas e auditoria qualitativa (LLM-as-a-judge).
* **`gpt-4o-mini` (snapshot `gpt-4o-mini-2024-07-18`):** Utilizado como guardrail semântico por evento de referência (baseline competitivo de baixo custo) e no avaliador de trajetória do ARKHÉ.

---

### Campo 13: Links e Artefatos do Projeto (Relevant Links & Artifacts)
* **Repositório GitHub:** `https://github.com/creusiobd/arkhe-benchmark-lab`
* **Branch de Desenvolvimento:** `feat/cybersecurity-grant-hardening`
* **Relatório do Piloto Empírico ($n=30$):** `results/pilot/pilot_report.md`
* **Manifesto de Execução e Hashes SHA-256:** `results/pilot/execution_manifest.json`
* **Matriz de Riscos de Pesquisa:** `docs/research_risks.md`
