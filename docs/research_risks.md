# ARKHÉ Agent Benchmark: Matriz de Riscos de Pesquisa

Este documento consolida a análise formal e contramedidas para os 9 riscos metodológicos, técnicos e operacionais do projeto **ARKHÉ Agent Boundary Defense Benchmark**, desenvolvido para o **OpenAI Cybersecurity Grant Program**.

---

## Matriz Resumo de Riscos

| ID | Dimensão do Risco | Probabilidade | Impacto | Severidade Residual | Estratégia de Mitigação Principal |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **R-01** | Não-Significância Estatística ($p \ge 0.01$) | Média | Alto | Baixa | Escalonamento amostral para $N=300$ trajetórias e pareamento não-paramétrico de Wilcoxon. |
| **R-02** | Sobrecarga de Latência / Custo Computacional | Média | Médio | Baixa | Janelamento deslizante dinâmico e ativação de verificação LLM apenas em zonas de risco (>$\Theta_{\text{caution}}$). |
| **R-03** | Falsos Positivos em Tarefas Exploratórias | Média | Alto | Baixa | Mecanismo formal de *Trajectory Recovery* e calibração de persistência comportamental ($w_h$). |
| **R-04** | Evasão por Fragmentação / Diluição Temporal | Baixa | Alto | Baixa | Acumulação estrita de contexto não confiável ($c_p$) e histórico estendido de observações brutas. |
| **R-05** | Sensibilidade / Overfitting a Modelos Específicos | Média | Médio | Baixa | Avaliação cruzada em múltiplos backends (`gpt-4o`, `gpt-4o-mini`, Llama-3-70B). |
| **R-06** | Vazamento de Rótulos em Contribuições Externas | Baixa | Crítico | Nula | Contratos Pydantic imutáveis com validação em tempo de instanciação e CI anti-vazamento. |
| **R-07** | Depreciação de Modelos / Mudanças na API OpenAI | Baixa | Médio | Baixa | Fixação em snapshots de versões versionadas (`gpt-4o-2024-08-06`) e harness agnóstico. |
| **R-08** | Risco de Uso Dual / Cargas Ofensivas | Baixa | Alto | Nula | Dados estritamente sintéticos, credenciais falsificadas e ausência de exploits executáveis. |
| **R-09** | Esgotamento Orçamentário de Tokens de API | Baixa | Médio | Baixa | Modelo analítico fechado (2.700 execuções = \$15,85 base) com margem de segurança de 2,5x e teto de \$5.000. |

---

## Detalhamento das Dimensões de Risco

### R-01: Risco de Não-Significância Estatística
* **Descrição:** Os testes empíricos podem indicar que a observabilidade de trajetória não supera os baselines por evento de forma estatisticamente significante ($p \ge 0.01$) em todas as 5 famílias.
* **Mitigação:** 
  1. O piloto inicial ($n=30$) confirmou a carência de pares no Wilcoxon e demonstrou a necessidade da escala $N=300$ ($k=3$ repetições, totalizando 2.700 avaliações).
  2. Caso a hipótese seja refutada em famílias específicas (ex: regras determinísticas bastando para violações diretas de regex), esse achado será publicado transparentemente como contribuição demarcadora de fronteiras de utilidade defensiva.
* **Protocolo de Monitoramento:** Reavaliação periódica dos $p$-valores de Wilcoxon e intervalos de Wilson nos milestones M2 e M4.

### R-02: Risco de Latência e Sobrecarga em Produção
* **Descrição:** A computação do vetor de aceleração e a inferência semântica de trajetória a cada passo podem introduzir overhead inaceitável para agentes interativos.
* **Mitigação:**
  1. Arquitetura hierárquica em dois níveis: métricas dinâmicas léxicas e de distância de Jaccard são calculadas localmente em $<5\text{ ms}$.
  2. Chamadas de LLM para análise contextual profunda são disparadas exclusivamente quando o escore dinâmico $R_t$ atinge a faixa de cautela ($\ge 35.0$).
* **Protocolo de Monitoramento:** Registro compulsório de `execution_time_ms` em todas as predições do harness (limite aceitável: $<50\text{ ms}$ para detecção local).

### R-03: Falsos Positivos em Agentes Exploratórios e Criativos
* **Descrição:** Agentes encarregados de pesquisa ampla ou depuração de erros realizam ações divergentes da missão nominal, arriscando disparos precoces indevidos.
* **Mitigação:**
  1. Formalização do operador de relaxamento de trajetória (*Safe Trajectory Recovery*): se o agente toca uma fronteira, recebe sinal `BLOCKED` e recua para o escopo nominal sem reincidência, o acumulador $R_t$ dissipa a tensão operacional para a linha de base ($15.0$).
  2. Inclusão de 90 trajetórias de quase-violações (*near-violations*) dedicadas a testar a resiliência a falsos positivos.
* **Protocolo de Monitoramento:** Verificação contínua do F1-Score e FPR específico no split de validação.

### R-04: Evasão Adversarial por Diluição Temporal
* **Descrição:** Um atacante pode instruir o agente a intercalar etapas inofensivas entre passos maliciosos para reduzir a taxa de variação $\frac{d}{dt}R_t$.
* **Mitigação:**
  1. O termo de contaminação de contexto $c_p$ mantém memória cumulativa da presença de diretrizes não confiáveis no histórico de observações brutas, impedindo o reset artificial do escore por preenchimento de ações vazias.
  2. Avaliação de sensibilidade a janelas de diluição de até 12 passos.
* **Protocolo de Monitoramento:** Teste com trajetórias de persistência camuflada na suíte de testes.

### R-05: Sensibilidade e Dependência de Modelos Específicos
* **Descrição:** O benchmark apresentar resultados favoráveis apenas quando executado com modelos OpenAI, perdendo generalização para modelos abertos.
* **Mitigação:**
  1. Avaliação cruzada independente do harness utilizando Llama-3-70B e Mistral-Large como motores de raciocínio de agente nos testes de validação.
  2. O núcleo de cálculo dinâmico do ARKHÉ é desacoplado do modelo que gera a trajetória.
* **Protocolo de Monitoramento:** Execução comparativa multiplataforma no Milestone M4.

### R-06: Vazamento de Rótulos em Contribuições Open Source
* **Descrição:** Contribuidores externos ou novos geradores de cenários injetarem inadvertidamente atributos de ground truth nos dados observáveis.
* **Mitigação:**
  1. O contrato `contracts.observation.StepObservation` utiliza `@model_validator` Pydantic que rejeita ativamente qualquer chave de rótulo ou escore pré-computado.
  2. A suíte automatizada `tests/test_no_label_leakage.py` e `tests/test_contract_separation.py` inspeciona a árvore sintática (AST) no CI antes de qualquer merge.
* **Protocolo de Monitoramento:** Bloqueio automatizado no GitHub Actions para qualquer violação de contrato.

### R-07: Depreciação de Modelos da OpenAI Durante a Pesquisa
* **Descrição:** A descontinuação ou alteração de pesos de endpoints (`gpt-4o`) afetar a reprodutibilidade dos resultados publicados.
* **Mitigação:**
  1. Fixação de snapshots com datas específicas (`gpt-4o-2024-08-06` e `gpt-4o-mini-2024-07-18`).
  2. Armazenamento estático de todas as entradas, saídas e previsões em JSONL imutável com hashes SHA-256 no Zenodo.
* **Protocolo de Monitoramento:** Registro de fingerprints e hashes de modelo em `execution_manifest.json`.

### R-08: Risco de Uso Dual e Cargas Ofensivas
* **Descrição:** O dataset conter comandos maliciosos reais que possam ser extraídos e explorados para ataques cibernéticos contra sistemas em produção.
* **Mitigação:**
  1. Dados 100% sintéticos: todos os segredos são gerados com padrões explícitos como `ARKHE_FAKE_TOKEN_DO_NOT_USE_*`.
  2. Todos os destinos de exfiltração apontam para sumidouros locais mockados (`http://localhost:8080/mock-sink` ou domínios reservados `.test`).
  3. Não inclusão de zero-days ou códigos de exploração funcional.
* **Protocolo de Monitoramento:** Auditoria independente externa de segurança no Milestone M5.

### R-09: Esgotamento Precoce do Orçamento de Tokens
* **Descrição:** Testes iterativos, erros de formatação JSON e repetições consumirem os créditos de API antes do término do projeto.
* **Mitigação:**
  1. Memória de cálculo rigorosa (`tools/estimate_api_cost.py`): o custo analítico bruto das 2.700 execuções é de apenas \$15,85 USD aos preços atuais do GPT-4o-mini e GPT-4o.
  2. A solicitação de \$5.000 em créditos oferece uma margem de contingência superior a 2,5x sobre todas as fases de calibração, permitindo múltiplos ciclos completos de refinamento sem risco de paralisação.
* **Protocolo de Monitoramento:** Alertas de consumo de faturamento semanais e limites de quota configurados na organização OpenAI.
