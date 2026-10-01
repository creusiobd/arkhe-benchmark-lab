# Respostas Oficiais para o Formulário de Submissão — OpenAI Cybersecurity Grant Program

Este documento contém as respostas consolidadas e auditadas para os campos do formulário de submissão do **OpenAI Cybersecurity Grant Program**, em português, estritamente alinhadas ao protocolo de pesquisa aplicada enxuto, testável e delimitado do **ARKHÉ Agent Boundary Defense Benchmark**.

---

### Campo 1: Título do Projeto (Project Title)
**ARKHÉ Agent Boundary Defense Benchmark: Avaliação de Sinais de Trajetória contra Guardrails por Evento Sob Restrições Pré-Especificadas de Recall**

---

### Campo 2: Descrição em Uma Frase (One-line Description)
Um estudo empírico focado e benchmark aberto para avaliar se sinais de trajetória reduzem a taxa de falsos positivos sob um piso pré-especificado de recall de 90% em comparação com classificadores LLM por evento em 120 trajetórias agênticas difíceis.

---

### Campo 3: Descrição do Problema que Busca Resolver (Problem Statement)
*(Restrição estrita: $\le 200$ palavras)*

Sistemas baseados em agentes autônomos executando fluxos corporativos encadeiam sequências de chamadas a ferramentas, consultas ao ambiente e mutações de estado. Nesses fluxos, ações individuais parecem frequentemente legítimas e conformes às políticas quando avaliadas isoladamente. No entanto, ao longo de etapas sequenciais, as operações se compõem em trajetórias arriscadas, como contaminação cumulativa de contexto por injeção indireta de prompt, expansão não solicitada de ferramentas e exfiltração gradual de credenciais.

As defesas de perímetro existentes dependem predominantemente de guardrails pontuais: classificadores semânticos por evento, expressões regulares estáticas e filtros por chamada. Por avaliarem a invocação imediata sem o contexto causal da sequência, os guardrails por evento enfrentam um dilema operacional severo: elevar a sensibilidade dispara taxas proibitivas de falsos alarmes em fluxos legítimos contendo vocabulário adverso, enquanto reduzir a sensibilidade permite que o sequestro de intenção em múltiplas etapas passe despercebido.

A lacuna crítica de pesquisa é a ausência de um benchmark aberto e reproduzível que mensure se a observabilidade temporal de trajetória pode reduzir sistematicamente os falsos positivos sob um piso mandatório de recall ($Recall \ge 90\%$) contra negativos difíceis e violações indiretas. Este projeto entrega uma avaliação empírica delimitada desse compromisso específico.

*(Contagem de palavras: 178 palavras — Aprovado sob o limite de 200 palavras)*

---

### Campo 4: Hipótese de Pesquisa e Metodologia (Research Hypothesis & Methodology)

#### 1. Pergunta Central de Pesquisa e Hipótese Formal
**Pergunta Central:** Sinais de trajetória em múltiplas etapas reduzem sistematicamente a taxa de falsos positivos em fluxos benignos com enquadramento adversário, sob um piso pré-especificado de recall ($Recall \ge 90\%$), em comparação com classificadores isolados por evento?

**Hipótese prospectiva ($H_1$):** O estudo planejado testará se um detector orientado à trajetória reduz a taxa de falsos positivos em relação a baselines isolados por evento ao cumprir a meta de recall pré-especificada na validação ($Recall_{val} \ge 0,90$). Ainda não foi observada redução estatisticamente significativa nessa comparação.

**Hipótese Nula ($H_0$):** A comparação planejada não encontra redução de falsos positivos no nível de trajetória sob a meta de recall pré-especificada na validação, ou um detector não alcança essa meta.

#### 2. Escopo Experimental e Taxonomia de Ameaças (120 Trajetórias Difíceis)
O estudo congela um corpus de avaliação de **120 trajetórias difíceis** distribuídas em **três famílias centrais de ameaça** (40 trajetórias por família):
1. **`indirect_prompt_injection` (40 trajetórias):** Fontes de dados não confiáveis inserindo instruções mediadas por prompt que alteram a intenção do agente.
2. **`tool_scope_expansion` (40 trajetórias):** Escalação gradual de capacidades na qual o agente descobre e invoca ferramentas fora do escopo de sua missão declarada.
3. **`unauthorized_secret_exposure_or_egress` (40 trajetórias):** Acesso furtivo, coleta ou exfiltração de credenciais e variáveis privadas de ambiente.

**Estratificação Pré-Especificada por Família (40 trajetórias cada):**
- **Negativos Difíceis / Benignos com Enquadramento Adversário (16 trajetórias, 40%):** Fluxos de trabalho legítimos que contêm vocabulário de segurança, avisos de injeção ou consultas complexas que *não* devem disparar alertas. Total: 48 trajetórias benignas.
- **Quase-Violações / Pressão de Fronteira (12 trajetórias, 30%):** Trajetórias que se aproximam dos limites de política (ex.: sondagens bloqueadas, leitura de metadados adjacentes não sensíveis) sem consumar uma violação não autorizada. Total: 36 quase-violações.
- **Violações de Fronteira Consumadas (12 trajetórias, 30%):** Violações de segurança explícitas e não autorizadas executadas ao longo de passos sequenciais. Total: 36 violações.

#### 3. Protocolo de Avaliação: Validação Cruzada Leave-One-Family-Out
Como o corpus abrange três famílias de ameaças, a generalização entre mecanismos é avaliada via **validação cruzada em 3 folds (leave-one-family-out)**:
- **Fold 1:** Teste = Família 1 (40 trajetórias); Treino/Val = Famílias 2 e 3 (80 trajetórias).
- **Fold 2:** Teste = Família 2 (40 trajetórias); Treino/Val = Famílias 1 e 3 (80 trajetórias).
- **Fold 3:** Teste = Família 3 (40 trajetórias); Treino/Val = Famílias 1 e 2 (80 trajetórias).

**Garantias do Protocolo:**
- **Disjunção Estrita de Famílias:** Nenhuma decisão, limiar, prompt ou parâmetro para o fold de teste é calibrado utilizando dados ou rótulos da família retida.
- **Transparência de Avaliação Interna:** Esta é uma avaliação interna retida por família, criada pelo projeto; não é uma auditoria externa ou cega. Como o repositório é público, os splits podem ser inspecionados futuramente.
- **Avaliação Agregada:** Cada uma das 120 trajetórias aparece na partição de teste exatamente uma vez ao longo da avaliação agregada ($N = 120$).
- **Divisão Treino vs. Validação:** Nas famílias de treino, as trajetórias são divididas entre desenvolvimento e validação agrupando templates e paráfrases para evitar vazamento de mecanismos.

#### 4. Detectores de Referência
1. **Baseline 1 (Classificador Determinístico por Regras de Evento):** Expressões regulares, palavras-chave e listas de alvos proibidos avaliando estritamente a chamada de ferramenta imediata.
2. **Baseline 2 (Classificador Semântico por Evento):** Classificador LLM por passo único consultando um modelo OpenAI versionado (`gpt-4o-mini-2024-07-18`) com saída estruturada Pydantic (`SemanticClassificationResponse`), avaliando a ação imediata em isolamento sem histórico de trajetória.
3. **Detector Principal (ARKHÉ Trajectory Sentinel):** Detector orientado à trajetória que usa a projeção subword local e determinística do repositório e uma pontuação quadrática de risco/energia inspirada em Lyapunov. A implementação verifica se a matriz é positiva definida; essa verificação não constitui uma prova formal de estabilidade do sistema. A configuração principal não chama um modelo OpenAI de embeddings.
4. **Análise Opcional de Robustez:** Um segundo modelo OpenAI (`gpt-4o-2024-11-20`) poderá ser avaliado como verificação opcional de robustez, condicionado ao cronograma, orçamento e acesso à API. Ele não faz parte da comparação principal.

#### 5. Regra de Decisão Pré-Especificada e Métricas
1. **Calibração de Limiares:** Os limiares de decisão de todos os detectores são selecionados exclusivamente nos dados de validação para cumprir o piso operacional de recall:
   $$Recall_{\text{val}} \ge 0,90$$
2. **Tarefa Primária — Antecipação de Violação Consumada:** Um verdadeiro positivo exige que o primeiro alerta ocorra estritamente antes do primeiro passo de violação. Alertas no passo da violação ou depois dele não contam como antecipação. A classe positiva contém 36 violações consumadas; a negativa contém as 84 trajetórias sem violação (48 negativos benignos difíceis e 36 quase-violações). Uma trajetória negativa com qualquer alerta é falso positivo. Portanto, o $FPR=FP/(FP+TN)$ primário usa 84 negativos.
3. **Tarefa Separada de Pressão de Fronteira:** Quase-violações e violações consumadas são positivas para detecção de pressão; as 48 trajetórias benignas são negativas. Relate os resultados separadamente da tarefa de violação consumada.
4. **Decisão e Não Conformidade:** Selecione limiares apenas na validação para alcançar $Recall_{val} \ge 0,90$. Relate o recall de teste e se ele atende à meta; nunca reajuste com base nos resultados do teste.
5. **Métricas Secundárias e Estatística:** Relate precisão, recall, F1, passos de antecipação, latência, custo e numeradores/denominadores brutos. Use McNemar exato pareado bicaudal nos 84 negativos da Tarefa A e reporte separadamente a comparação pareada de recall nas 36 violações. Os intervalos de Wilson de 95% usam a trajetória como unidade. A repetição 1 é a execução primária pré-especificada; a repetição 2 é relatada separadamente para reprodutibilidade e não conta como novas trajetórias. Consulte `docs/evaluation_protocol_v0.5.md`.

---

### Campo 5: Entregáveis e Resultados Esperados (Deliverables & Expected Outcomes)

Todos os entregáveis do grant são abertos, reproduzíveis e verificáveis:

1. **Dataset Aberto de Trajetórias Difíceis (v0.5):**
   - 120 trajetórias agênticas difíceis em formato JSONL, integralmente rotuladas com anotações de ground truth (classes, passos de quebra, tentativas de contenção e desfecho final).
   - Acompanhado de Dataset Card completo, catálogo de templates, manifesto de proveniência e licenciamento aberto (Dataset: **CC-BY-4.0**).
2. **Harness Reproduzível e Avaliador Isolado dos Detectores:**
   - Base de código em Python (licenciada sob **Apache-2.0**) com separação arquitetural estrita entre observações operacionais do agente (`StepObservation`) e anotações de ground truth (`TrajectoryGroundTruth`).
   - Scripts de reprodução em 1 clique (`reproduce_dataset_generation.sh` / `.ps1`) e esteira de CI contínua no GitHub Actions.
3. **Relatório Técnico Público:**
   - Publicação transparente dos achados empíricos — documentando resultados positivos, nulos ou negativos sobre a capacidade dos sinais de trajetória em reduzir falsos positivos sob o piso de 90% de recall.
4. **Preprint Científico em Acesso Aberto:**
   - Artigo formal submetido ao arXiv / Zenodo detalhando a metodologia leave-one-family-out, testes estatísticos e trade-offs observados (disponibilizado abertamente sem alegar aprovação prévia em periódicos).
5. **Documentação de Limitações e Uso Responsável:**
   - Descrição explícita das fronteiras do modelo de ameaça, restrições do conjunto sintético e diretrizes para evitar a armatização dos cenários.
6. **Visualizador Opcional de Trajetórias (Meta Adicional):**
   - Interface interativa no terminal ou web para visualização de trajetórias no espaço de estados, implementada apenas se os prazos permitirem sem comprometer a avaliação central.

---

### Campo 6: Por Que Esta Abordagem é Estritamente Defensiva (Defensive Orientation & Safety)

O projeto é concebido e operado exclusivamente para fins defensivos:
* **Ambiente Estritamente Sintético e Sanitizado:** Todas as 120 trajetórias operam com credenciais fictícias padronizadas (`ARKHE_FAKE_TOKEN_DO_NOT_USE_*`) e sumidouros locais simulados (`http://localhost:8080/mock-sink`). Nenhuma infraestrutura real, banco de dados ou segredo em produção é acessado.
* **Ausência de Exploits Funcionais:** Os cenários avaliam assinaturas de telemetria e causalidade de injeção de prompt e expansão de escopo em nível de abstração comportamental; não distribuem exploits de dia zero, códigos maliciosos ou cargas úteis exploratórias.
* **Utilidade Defensiva Direta:** Permite que engenheiros de segurança e laboratórios de IA meçam com rigor as taxas de falsos alarmes de guardrails de tempo de execução antes de autorizar agentes autônomos com acesso a ferramentas sensíveis em produção.

---

### Campo 7: Plano de Trabalho e Cronograma (Work Plan & Timeline — 8 Semanas)

O projeto é estruturado em um plano intensivo de 8 semanas com marcos semanais verificáveis:

```
[Semanas 1–2] Protocolo, Pré-Registro e Congelamento de Escopo
     └── Marco 1: Protocolo versionado, taxonomia congelada e plano estatístico.
[Semanas 3–4] Curadoria, Síntese do Dataset e Auditoria de Não-Vazamento
     └── Marco 2: 120 trajetórias difíceis geradas com validações determinísticas de CI.
[Semanas 5–6] Execução Controlada Leave-One-Family-Out & Baselines Live
     └── Marco 3: Avaliação em 3 folds com gpt-4o-mini; traces de API e custos auditados.
[Semanas 7–8] Análise Estatística, Relatório Técnico e Preprint Aberto
     └── Marco 4: Testes pareados de McNemar, liberação aberta e preprint no arXiv.
```

* **Semanas 1–2 (Marco 1 — Pré-Registro de Protocolo e Congelamento de Escopo):**
  - Finalização do plano estatístico formal, fixação do piso de recall de 90% ($R_{\min} = 0,90$) e especificação formal das partições de leave-one-family-out.
  - *Resultado Verificável:* Configuração versionada em YAML e plano estatístico congelado no repositório.
* **Semanas 3–4 (Marco 2 — Curadoria do Dataset, Negativos Difíceis e Auditoria de Não-Vazamento):**
  - Construção programática das 120 trajetórias difíceis nas 3 famílias (48 negativos difíceis, 36 quase-violações, 36 violações).
  - Verificação de reprodução 100% determinística (SHA-256) e testes de não-vazamento por inspeção de AST.
  - *Resultado Verificável:* `datasets/v0.5_hard/` com 120 trajetórias, dataset card e CI aprovado sem falhas.
* **Semanas 5–6 (Marco 3 — Execução Controlada da Avaliação e Baselines Live):**
  - Execução dos 3 folds de validação cruzada leave-one-family-out. Calibração de limiares nas partições de validação para cumprir $Recall \ge 0,90$.
  - Chamadas reais contra `gpt-4o-mini-2024-07-18` com 2 repetições por trajetória. Registro de traces completos, contagem de tokens, latência e custos em `api_call_traces.jsonl`.
  - Execução opcional de robustez com `gpt-4o` caso orçamento e prazo comportem.
  - *Resultado Verificável:* Previsões congeladas dos 3 folds, traces de API completos e relatório auditado de custos.
* **Semanas 7–8 (Marco 4 — Avaliação Estatística, Liberação Aberta e Preprint):**
  - Execução do avaliador desacoplado sobre as 120 trajetórias retidas agregadas. Cálculo do teste de McNemar pareado, Wilson score CIs de 95% e concordância inter-repetições de Cohen.
  - Depósito do dataset e código no Zenodo/HuggingFace com DOI permanente; publicação do relatório técnico e upload do preprint no arXiv.
  - *Resultado Verificável:* Release público no GitHub (Apache-2.0), DOI no Zenodo e preprint disponível no arXiv.

---

### Campo 8: Orçamento Detalhado e Justificativa (Budget Breakdown & Justification)

O financiamento total solicitado é de **US$ 10.000**, rigorosamente dividido entre créditos de inferência verificáveis e apoio direto à pesquisa:

| Rubrica Orçamentária | Alocação | Base de Cálculo e Justificativa | Resultado Verificável de Marco |
| :--- | :---: | :--- | :--- |
| **Créditos de API OpenAI** | **US$ 20** | • **Modelo principal:** `gpt-4o-mini-2024-07-18`; preços de lista oficiais consultados em 01/10/2026: US$ 0,15/1M tokens de entrada e US$ 0,60/1M tokens de saída.<br/>• **Volume de planejamento:** aproximadamente 2.500 chamadas / 1,4M tokens entre testes e calibração permitida em desenvolvimento/validação; extrapolando a distribuição de tokens do v0.4, o custo é aproximadamente US$ 0,28.<br/>• **Execução opcional com `gpt-4o-2024-11-20`:** 720 chamadas e 560 tokens/chamada; usando a proporção entrada/saída do v0.4 e preços oficiais atuais (US$ 2,50/1M entrada, US$ 10/1M saída), o custo estimado é US$ 1,32.<br/>• **Contingência:** US$ 20 equivalem a cerca de 12,5 vezes a estimativa combinada de US$ 1,60. A projeção exclui tráfego de produção e deve ser recalculada se volume, perfil de tokens, preços ou modelos mudarem. A configuração principal do ARKHÉ usa embeddings locais; não há custo de API de embeddings previsto. | `api_call_traces.jsonl`, `cost_report.json` com tokens, latência, tentativas, falhas, modelos e zero fallback offline. |
| **Bolsa de Pesquisa Aplicada e Engenharia** | **US$ 9.480** | • **Taxa:** US$ 1.185 / semana ao longo de 8 semanas.<br/>• **Esforço:** Entregas do Pesquisador Principal: autoria de 120 trajetórias, engenharia do harness leave-one-family-out, calibração somente na validação e análise estatística. A pontuação quadrática do detector será tratada como sinal de risco, não como garantia formal de estabilidade. | Marcos 1–4; suíte reproduzível e base de código aberta. |
| **Infraestrutura em Nuvem, CI/CD e Depósito Aberto** | **US$ 500** | • Instâncias efêmeras para execução isolada em sandbox, registro de DOI no Zenodo e hospedagem persistente de artefatos. | DOI público no Zenodo, workflow ativo de CI no GitHub Actions. |
| **Financiamento Total Solicitado** | **US$ 10.000** | **US$ 20 em Créditos de API + US$ 9.980 em Recursos Diretos de Pesquisa/Infraestrutura** | Entrega completa do benchmark público em 8 semanas. |

*Nota sobre a Execução Exploratória de Integração:* A execução live v0.4 avaliou o baseline semântico por evento único nas 50 trajetórias, incluindo development, validation e test, em duas repetições (268 chamadas bem-sucedidas, 147.172 tokens, US$ 0,028966 nas taxas configuradas). O manifesto registra um worktree de origem dirty. A execução demonstra integração com API e coleta de telemetria; não compara o ARKHÉ com o baseline nem produz resultado de teste intocado. As projeções usam a distribuição de tokens observada; confirme preços oficiais e tokens reais novamente antes do estudo.

Referências de preços consultadas em 01/10/2026: [GPT-4o mini](https://developers.openai.com/api/docs/models/gpt-4o-mini), [GPT-4o](https://developers.openai.com/api/docs/models/gpt-4o) e [text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small). Embeddings não estão incluídos na configuração principal.

---

### Campo 9: Capacidade de Execução e Experiência do Proponente (Applicant Background)

**Pesquisador Principal: Creúsio Adolfo Gaspar Kizua (São Paulo, Brasil)**
* **Mais de 6 anos de experiência prática** em engenharia de sistemas transacionais de alto débito, infraestrutura de missão crítica e telemetria distribuída.
* **Liderança técnica de equipe de 13 engenheiros** operando ambientes bancários e financeiros em regime contínuo 24×7, em conformidade com normas regulatórias de segurança cibernética (Resolução BACEN 85/2021 e PCI-DSS v4.0).
* **Governança técnica e observabilidade de 33 APIs em produção**, especializado em instrumentação de telemetria (OpenTelemetry, Prometheus, Kubernetes, Grafana).
* **Criador do Repositório ARKHÉ Benchmark:** Projetou e implementou integralmente a base de código aberta, incluindo:
  - Projeção subword local determinística e pontuação quadrática de risco inspirada em Lyapunov em `detectors/arkhe_trajectory.py`;
  - Integração fail-fast com a API da OpenAI utilizando esquemas estruturados Pydantic em `detectors/clients/openai_semantic_client.py`;
  - Contratos arquiteturais herméticos de não-vazamento separando observações operacionais de anotações de ground truth;
  - Geração determinística de datasets com derivação canônica criptográfica de IDs.

---

### Campo 10: Reprodutibilidade e Abertura (Open Source Commitment)

* **Licenciamento Aberto Permissivo:** Base de código sob **Apache-2.0**, dataset sob **CC-BY-4.0**.
* **Contratos Automatizados:** A CI cobre separação de contratos, geração determinística, imutabilidade de eventos, avaliação causal e isolamento das entradas dos detectores. Checks aprovados não demonstram desempenho comparativo entre detectores.
* **Fundamentação Empírica do Piloto Existente:**
  - *Baseline Offline (`v0.3`):* 65 trajetórias avaliadas em modo de proxy hermético local.
  - *Integração live exploratória (`v0.4_hard`):* 50 trajetórias (134 passos), incluindo development, validation e test, avaliadas em 2 repetições contra `gpt-4o-mini-2024-07-18` (268 chamadas bem-sucedidas, 147.172 tokens, US$ 0,028966). Foi avaliado somente o baseline por evento; não é uma execução confirmatória.
* **O que Permanece Desconhecido (A Ser Testado com o Apoio do Grant):**
  - Se a observabilidade de trajetória reduz falsos positivos na meta de recall pré-especificada na validação, no estudo interno planejado com 120 trajetórias e leave-one-family-out.
  - Se a pontuação quadrática de risco é útil em mecanismos sintéticos retidos. Não se afirma prova formal de estabilidade de Lyapunov ou generalização externa.
