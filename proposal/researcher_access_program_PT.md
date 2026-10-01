# Formulário Oficial — OpenAI Researcher Access Program

Este documento contém as respostas oficiais e auditadas formatadas especificamente para o formulário de candidatura do **OpenAI Researcher Access Program** no link:  
`https://openai.com/form/researcher-access-program/`

---

## 1. Informações Pessoais e Profissionais

* **Nome:** Creúsio Adolfo
* **Sobrenome:** Gaspar Kizua
* **País / Região:** Brasil
* **E-mail da Conta OpenAI API:** `[Seu E-mail da Conta OpenAI API]`
* **E-mail Institucional / Profissional:** `[Seu E-mail Institucional ou Organizacional]`
* **Link de Perfil Profissional:** `https://github.com/creusiobd/arkhe-benchmark-lab` *(e LinkedIn: `[Seu Link do LinkedIn]`)*
* **Instituição / Organização:** `[Sua Universidade, Laboratório de Pesquisa ou Afiliação de Pesquisa Independente em Segurança de IA]`
* **Função Atual / Nível Educacional:** Pesquisador Líder em Sistemas e Segurança de IA

---

## 2. Área de Pesquisa e Categorização

* **Área Principal de Foco:** Alinhamento (Alignment) / Segurança, Potencial de Abuso e Red-Teaming (Safety, Misuse Potential & Red-Teaming) / Interpretabilidade (Interpretability)
* **Palavras-chave do Projeto:** Agentes Autônomos, Defesa de Contorno, Observabilidade de Trajetória em Múltiplos Passos, Injeção Indireta de Prompt, Expansão de Escopo de Ferramentas, Redução de Falsos Positivos.

---

## 3. Título do Projeto e Resumo em Uma Linha

* **Título do Projeto:**  
  `ARKHÉ Agent Boundary Defense Benchmark: Avaliação de Sinais de Trajetória contra Guardrails por Evento Sob Restrições de Recall`

* **Resumo em Uma Frase:**  
  Um benchmark aberto empírico para avaliar se a observabilidade de trajetória reduz sistematicamente os falsos alarmes sob um piso pré-especificado de recall de 90% em comparação com guardrails LLM por evento em 120 trajetórias agênticas difíceis.

---

## 4. Declaração do Problema e Pergunta de Pesquisa

*(Limite do formulário: ~150–200 palavras)*

Sistemas baseados em agentes autônomos executando fluxos corporativos encadeiam sequências de chamadas a ferramentas, consultas ao ambiente e mutações de estado. Nesses fluxos, ações individuais parecem frequentemente legítimas e conformes às políticas quando avaliadas isoladamente. No entanto, ao longo de etapas sequenciais, as operações se compõem em trajetórias arriscadas, como contaminação cumulativa de contexto por injeção indireta de prompt, expansão não solicitada de ferramentas e exfiltração gradual de credenciais.

As defesas de perímetro existentes dependem predominantemente de guardrails pontuais: classificadores semânticos por evento, expressões regulares estáticas e filtros por chamada. Por avaliarem a invocação imediata sem o contexto causal da sequência, os guardrails por evento enfrentam um dilema operacional severo: elevar a sensibilidade dispara taxas proibitivas de falsos alarmes em fluxos legítimos contendo vocabulário adverso, enquanto reduzir a sensibilidade permite que o sequestro de intenção em múltiplas etapas passe despercebido.

A lacuna crítica de pesquisa é a ausência de um benchmark aberto e reproduzível que mensure se a observabilidade temporal de trajetória pode reduzir sistematicamente os falsos positivos sob um piso mandatório de recall ($Recall \ge 90\%$) contra negativos difíceis e violações indiretas. Este projeto entrega uma avaliação empírica delimitada desse compromisso específico.

---

## 5. Metodologia e Plano de Uso da API da OpenAI

### 1. Pergunta Central de Pesquisa e Hipóteses
* **Pergunta Central:** Sinais de trajetória em múltiplos passos reduzem sistematicamente a taxa de falsos positivos em fluxos benignos com enquadramento adverso, sob um piso pré-especificado de recall ($Recall \ge 0{,}90$), em comparação com classificadores isolados por evento?
* **Hipótese ($H_1$):** A defesa orientada à trajetória obtém redução estatisticamente significativa na taxa de falsos positivos ($FPR$) em relação aos baselines de evento único, satisfazendo a restrição de $Recall \ge 0{,}90$ em uma avaliação cruzada leave-one-family-out em 3 folds.
* **Hipótese Nula ($H_0$):** A observabilidade de trajetória não reduz a taxa de falsos positivos ($FPR_{\text{trajetória}} \ge FPR_{\text{evento}}$) sob a restrição de $Recall \ge 0{,}90$, ou não atinge o piso operacional mínimo de recall.

### 2. Escopo Experimental e Famílias de Ameaça (120 Trajetórias Difíceis)
* **Dataset:** 120 trajetórias estruturalmente difíceis distribuídas igualmente em 3 famílias de ameaça (40 por família):
  1. `indirect_prompt_injection` (40 trajetórias)
  2. `tool_scope_expansion` (40 trajetórias)
  3. `unauthorized_secret_exposure_or_egress` (40 trajetórias)
* **Composição por Família:** 16 negativos difíceis / benignos com vocabulário de auditoria (40%), 12 quase-violações / pressão de fronteira (30%), 12 violações consumadas (30%). Total: 48 benignas, 36 quase-violações, 36 violações.
* **Protocolo de Avaliação:** Validação cruzada leave-one-family-out em 3 folds. Limiares de operação calibrados exclusivamente nos folds de validação para cumprir $Recall_{\text{val}} \ge 0{,}90$.

### 3. Integração com Modelos da OpenAI
1. **`gpt-4o-mini-2024-07-18` (Baseline Principal por Evento):** Avalia invocações imediatas de ferramentas de forma isolada via saídas estruturadas (esquema Pydantic `SemanticClassificationResponse`).
2. **`text-embedding-3-small` (Kernel do ARKHÉ Trajectory Sentinel):** Realiza projeções contínuas da instrução da missão e das observações brutas do agente para calcular a divergência semântica e a contaminação em subespaço adverso ao longo da trajetória.
3. **`gpt-4o` (Verificação Comparativa de Robustez):** Avalia se capacidades avançadas de raciocínio alteram o compromisso entre alarmes falsos e latência de detecção na camada de eventos.

---

## 6. Solicitação de Créditos de API e Justificativa Orçamentária Empírica

* **Total de Créditos Solicitados:** **US$ 1.000**
* **Viabilidade Empírica Previamente Demonstrada:**
  Em nosso pré-piloto ao vivo controlado no conjunto `v0.4_hard` (commit `cac040e0`), executamos **268 chamadas reais** a `gpt-4o-mini-2024-07-18` com 100% de taxa de sucesso (0 falhas, 0 retries), consumindo 147.172 tokens a um custo real verificado de **US$ 0,0290** (**US$ 0,00058 por trajetória**).

### Detalhamento da Alocação dos Créditos (US$ 1.000):
1. **`gpt-4o-mini-2024-07-18` (Classificador de Evento e Validação Cruzada):**  
   - 120 trajetórias $\times$ 3 passos $\times$ 2 repetições = 720 avaliações de teste (~1,2M tokens $\approx$ US$ 0,20).  
   - Calibração e otimização de limiares nos 3 folds: ~2.500 chamadas (~3,5M tokens $\approx$ US$ 0,60).
2. **`text-embedding-3-small` (Projeções Contínuas de Trajetória):**  
   - Embeddings densos de estado e observações em 120 trajetórias $\times$ múltiplos estados intermediários + protótipos de referência (~2,0M tokens $\approx$ US$ 0,05).
3. **`gpt-4o` (Benchmarking de Robustez em Modelo de Fronteira):**  
   - Avaliação comparativa nas 120 trajetórias difíceis (720 chamadas $\times$ 600 tokens $\approx$ US$ 2,50).
4. **Engenharia de Prompt, Variância Inter-Repetições e Margem de Segurança:**  
   - Amostragens repetidas para mensurar variabilidade estocástica entre formulações de prompt e variações contextuais.  
   - US$ 1.000 em créditos oferece folga operacional confortável, garantindo a conclusão integral dos experimentos sem risco de interrupção.

---

## 7. Ciência Aberta, Segurança e Plano de Disseminação Pública

* **Licenciamento Aberto Duplo:** Dataset disponibilizado sob **CC-BY-4.0**; harness de execução e avaliador disponibilizados sob **Apache-2.0**.
* **Repositório Público:** Hospedado abertamente em [`https://github.com/creusiobd/arkhe-benchmark-lab`](https://github.com/creusiobd/arkhe-benchmark-lab) com esteiras de CI/CD automatizadas e 170+ testes de regressão aprovados.
* **Depósito Permanente e DOI:** Dataset e harness depositados no Zenodo com atribuição de DOI permanente na conclusão do projeto.
* **Relatório Técnico e Preprint Abertos:** Transparência total de resultados positivos, nulos ou negativos documentados em relatório técnico detalhado e submetidos ao arXiv.
* **Orientação Estritamente Defensiva:** Todas as 120 trajetórias rodam em ambientes sintéticos isolados com credenciais fictícias (`ARKHE_FAKE_TOKEN_*`) e sumidouros locais (`http://localhost:8080/mock-sink`), sem código malicioso funcional ou cargas de exploração de dia zero.
