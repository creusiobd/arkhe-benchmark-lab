# Respostas Oficiais para o Formulário de Submissão — OpenAI Cybersecurity Grant Program

Este documento contém as respostas consolidadas e auditadas para os campos do formulário de submissão do **OpenAI Cybersecurity Grant Program**, em português, atualizadas para a versão **v0.3**.

---

### Campo 1: Título do Projeto (Project Title)
**ARKHÉ Agent Boundary Defense Benchmark: Avaliação Empírica de Observabilidade de Trajetória contra Violações de Fronteira em Sistemas de Agentes de IA**

---

### Campo 2: Descrição em Uma Frase (One-line Description)
Um benchmark defensivo e open source para avaliar se a observabilidade orientada à trajetória detecta desvio de missão, propagação de prompt injection e violações de fronteira em agentes de IA antes de mecanismos baseados em eventos atômicos isolados.

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

**Desenho Experimental e Eliminação de Vazamento (Anti-Leakage):**
Para impedir circularidade experimental, o benchmark estabelece duas camadas estritamente isoladas:
1. *Camada Observável (`StepObservation`):* Disponibilizada aos detectores em tempo real contendo apenas identidade ofuscada (`traj_<sha256[:16]>`), missão declarada, ação sanitizada, capacidades, fronteiras e observações brutas. Rótulos reais, índices de quebra e escores pré-computados são proibidos e validados recursivamente em tempo de execução via contratos Pydantic.
2. *Ground Truth Reservado (`TrajectoryGroundTruth`):* Armazenado separadamente para uso exclusivo do avaliador independente, contendo classe real, passo da violação e justificativa causal humana.
3. *Split Blind Holdout Estritamente Disjunto:* O dataset v0.3 incorpora 15 trajetórias em split cego com templates de ataque 100% disjuntos dos conjuntos de desenvolvimento e validação.

**Formalização Matemática e Espaço de Estados:**
O ARKHÉ modela a dinâmica de execução utilizando um kernel contínuo de embeddings subword ($\mathbb{R}^{64}$) e uma função candidata de energia de Lyapunov estritamente definida positiva:
$$V(\mathbf{x}_t) = \mathbf{x}_t^T \mathbf{P} \mathbf{x}_t > 0 \quad (\mathbf{P} \succ 0)$$
rastreando o vetor de estados $\mathbf{x}_t = [d_m(t), c_p(t), b_p(t), \dot{b}_p(t), \mathcal{H}_s(t), \mu_c(t)]^T$, onde o acoplamento cruzado entre divergência de missão ($d_m$) e contaminação de contexto ($c_p$) detecta instabilidade pré-violação etapas antes da execução de chamadas proibidas.

**Escala e Tratamento Estatístico:**
O estudo no release piloto v0.3 avalia 65 trajetórias canônicas equilibradas através de 5 famílias de ameaças (desenvolvimento: 20, validação: 10, teste: 20, blind holdout: 15). O pipeline calcula intervalos de confiança de Wilson (95%) para precisão, recall e acurácia; Bootstrap para mediana e média de $N_{\text{lead}}$; teste pareado de postos sinalizados de Wilcoxon para significância de antecipação; e teste exato bicaudal de McNemar para discordância pareada entre detectores.

---

### Campo 5: Entregáveis e Resultados Esperados (Deliverables & Expected Outcomes)
1. **Dataset Aberto Canônico (v0.3 e Expansão em Larga Escala):** Formato JSONL padronizado, catalogado por famílias de ameaça, licenciado sob CC-BY-4.0 e depositado no Zenodo (com DOI permanente) e HuggingFace.
2. **Harness e Suíte de Avaliação Open Source (Apache-2.0):** Repositório Python modular com separação formal de contratos, testes de não-vazamento por validação profunda e suporte a múltiplos backends (OpenAI API nativa e offline hermético).
3. **Três Detectores de Referência Auditáveis:** Baseline determinístico por regras, baseline semântico por chamada única (integrando cliente estruturado `OpenAISemanticClient` com esquema Pydantic `SemanticClassificationResponse` ou proxy determinístico) e o *ARKHÉ Trajectory Sentinel*.
4. **Artigo Científico e Relatório Técnico Aberto:** Documentação completa da metodologia, formulação matemática da função de risco no espaço de estados e análise de significância estatística.
5. **Automação de Reprodutibilidade:** Scripts de reprodução 1-clique (`scripts/reproduce_grant_pilot.sh` e `.ps1`) e pipeline de CI no GitHub Actions (`grant-benchmark.yml`).

---

### Campo 6: Por Que Esta Abordagem é Estritamente Defensiva (Defensive Orientation & Safety)
O projeto é concebido e operado com foco exclusivo em segurança defensiva:
* **Dados Estritamente Sintéticos e Sanitizados:** Todos os cenários utilizam chaves e tokens fictícios de padrão identificável (`ARKHE_FAKE_TOKEN_DO_NOT_USE_*`) e sumidouros de rede locais (`http://localhost:8080/mock-sink`), sem qualquer credencial ou endpoint de produção real.
* **Ausência de Exploits Funcionais:** Os cenários avaliam a estrutura causal e comportamental do desvio de missão em nível abstrato de telemetria, sem distribuir códigos de ataque funcionais ou cargas úteis exploratórias.
* **Critério Defensivo:** O objetivo prático é capacitar engenheiros de segurança e criadores de agentes a calibrar defesas com base em evidências empíricas de antecipação temporal e controle de falsos positivos, protegendo ecossistemas agênticos contra injeções indiretas e desvios de intenção.

---

### Campo 7: Plano de Trabalho e Cronograma (Work Plan & Timeline — 6 Meses)
* **Mês 1 (M1 — Expansão e Formalização do Dataset):** Expansão do dataset para 1.000+ trajetórias canônicas nas 5 famílias com auditoria automatizada de não-vazamento.
* **Mês 2 (M2 — Reforço dos Baselines e Integração de APIs):** Calibração de baselines semânticos com modelos OpenAI (`gpt-4o`, `gpt-4o-mini`, `o1`) e consolidação de guardrails estruturados.
* **Mês 3 (M3 — Calibração do ARKHÉ Trajectory Sentinel):** Otimização e congelamento dos pesos dinâmicos da função de risco sobre os conjuntos de desenvolvimento e validação.
* **Mês 4 (M4 — Execução Experimental em Larga Escala):** Execução de avaliações cegas em grande escala; processamento estatístico completo (Wilson 95%, Wilcoxon pareado e McNemar exato).
* **Mês 5 (M5 — Auditoria Externa de Red-Teaming):** Revisão de segurança independente por terceiros para validar a robustez dos cenários e desafiar a generalização em ambiente adversário.
* **Mês 6 (M6 — Disseminação e Lançamento Open Source):** Depósito do dataset no Zenodo/HuggingFace, publicação do repositório no GitHub sob Apache-2.0 e liberação do preprint técnico.

---

### Campo 8: Orçamento Detalhado e Justificativa em 3 Níveis (Tiered Budget)

Para proporcionar máxima flexibilidade ao comitê de avaliação da OpenAI, estruturamos a proposta em 3 níveis modulares:

#### Nível A: Apenas Créditos de API OpenAI (US$ 15.000 – US$ 25.000 em Créditos de API)
* **Foco:** Avaliação experimental em larga escala contra modelos de ponta (`gpt-4o`, `gpt-4o-mini`, `o1`).
* **Uso dos Créditos:** Execução de mais de 5.000 trajetórias agênticas com avaliação semântica estruturada passo a passo, testes de robustez a variações de prompt e calibração de guardrails LLM-as-a-judge.
* **Custo Financeiro Direto:** US$ 0 (sem desembolso monetário, apenas créditos de inferência).

#### Nível B: Projeto Integral com Bolsa de Pesquisa (US$ 25.000 em Créditos + US$ 25.000 em Recursos de Pesquisa = US$ 50.000 Total)
* **Créditos de API OpenAI — US$ 25.000 (50%):**
  * Geração sintética em larga escala de trajetórias complexas, inferência de baselines semânticos com `gpt-4o` e modelos de raciocínio `o1` em tarefas multiagente.
* **Bolsa de Pesquisa e Engenharia — US$ 15.000 (30%):**
  * Dedicação técnica do Pesquisador Principal ao longo de 6 meses para desenvolvimento da biblioteca de telemetria, contratos formais e análise estatística.
* **Auditoria Externa de Segurança e Red-Teaming — US$ 6.000 (12%):**
  * Remuneração de especialistas externos para campanhas de red-teaming contra o benchmark, gerando novos ataques adaptativos.
* **Infraestrutura Cloud e Publicação de Acesso Aberto — US$ 4.000 (8%):**
  * Servidores para execução hermética de agentes, pipelines de CI/CD e taxas de publicação acadêmica em acesso aberto.

#### Nível C: Escopo Focado (US$ 10.000 em Créditos de API)
* **Foco:** Calibração dos baselines centrais em 1.000 trajetórias com `gpt-4o-mini` e `gpt-4o`, comparando o custo e latência de inferência por etapa com o sentinel de trajetória.

---

### Campo 9: Capacidade de Execução e Experiência do Proponente (Applicant Background)
**Pesquisador Principal: Creúsio Adolfo Gaspar Kizua (São Paulo, Brasil)**
* Mais de **6 anos de experiência prática** em engenharia de sistemas de pagamentos de alta disponibilidade, observabilidade de alta escala e infraestrutura de missão crítica.
* **Liderança técnica de equipe de 13 engenheiros** operando ambientes bancários e transacionais em regime contínuo 24×7.
* **Governança técnica e observabilidade de 33 APIs reguladas**, com conformidade rigorosa a padrões de segurança cibernética (Resolução BACEN 85/2021 e PCI-DSS v4.0).
* Domínio aprofundado em telemetria e controle distribuído: OpenTelemetry, Kubernetes, Prometheus, Splunk, Dynatrace e Grafana.
* Criador da metodologia de defesa de fronteira agêntica orientada à trajetória, integrando conceitos de estabilidade dinâmica no espaço de estados (métodos de Lyapunov) à segurança cibernética de agentes de IA.

---

### Campo 10: Reprodutibilidade e Abertura (Open Source Commitment)
* O projeto é integralmente open source sob licença permissiva **Apache-2.0** (código) e **CC-BY-4.0** (datasets).
* A suíte conta com **112 testes automatizados** passando (111 aprovados, 1 teste de integração ao vivo skipped), pipeline de reprodução 1-clique (`scripts/reproduce_grant_pilot.sh` e `reproduce_grant_pilot.ps1`) e automação de CI no GitHub Actions (`.github/workflows/grant-benchmark.yml`).
* Todos os artefatos de saída contam com hashes determinísticos SHA-256 e manifestos de execução auditáveis.
