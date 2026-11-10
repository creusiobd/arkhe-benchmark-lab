# Respostas Oficiais do Formulário — OpenAI Cybersecurity Grant Program

**Candidatura:** ARKHÉ v0.6
**Proponente:** Creúsio Adolfo Gaspar Kizua — São Paulo, Brasil
**Estado:** Rascunho para revisão humana. Não submetido.

## Campo 1: Título do Projeto

**ARKHÉ v0.6: Benchmark com Custódia Independente para Segurança de Agentes Orientada à Trajetória**

## Campo 2: Descrição em Uma Frase

Estudo defensivo aberto que testará se a análise de trajetórias melhora a classificação antecipada de violações em comparação com um classificador OpenAI congelado por evento, usando 200 casos inéditos e produzidos sob custódia independente.

## Campo 3: Descrição do Problema

Agentes autônomos podem permanecer plausíveis localmente enquanto se tornam inseguros no conjunto. Uma chamada de ferramenta, escrita em memória, delegação ou verificação de autorização pode parecer aceitável isoladamente, mas a sequência pode alterar gradualmente missão, confiança, capacidade ou identidade até romper uma fronteira. Guardrails por evento enfrentam, portanto, um dilema: limiares sensíveis interrompem fluxos legítimos, enquanto limiares permissivos não percebem violações visíveis apenas ao longo do tempo.

O trabalho laboratorial existente do ARKHÉ demonstra que esse trade-off pode ser medido de forma reproduzível, mas não estabelece generalização externa nem eficácia em produção. O corpus v0.5 foi criado e inspecionado durante o desenvolvimento; por isso, está deliberadamente restrito a evidência de integração e reprodutibilidade.

O estudo v0.6 produzirá a evidência ainda ausente. Ele comparará um classificador semântico congelado por evento com um detector orientado à trajetória em 200 casos sintéticos, inéditos e produzidos por autor independente, distribuídos em quatro novas famílias de segurança. Os rótulos permanecerão sob custódia até que protocolo, código, modelo, retentativas e manifesto sejam congelados. Resultados positivos, nulos ou negativos serão publicados com denominadores, falsos positivos, violações perdidas, latência, tokens e custo.

*(Contagem de palavras: 189 palavras — dentro do limite de 200)*

## Campo 4: Proposta Completa

### Pergunta de pesquisa e hipótese

A análise orientada à trajetória melhora a classificação antecipada de violações em comparação com um classificador semântico congelado por evento em casos inéditos de segurança de agentes?

A hipótese primária é que o ARKHÉ melhorará a correção pareada da Tarefa A em pelo menos **15 pontos percentuais** em relação ao comparador por evento. A comparação estatística primária será McNemar exato bicaudal com `alpha = 0,05`. Efeito mínimo, endpoint, regra para dados ausentes, regra de parada e comparador são declarados antes da existência da evidência de teste.

### Base existente e limite da evidência

O repositório público já contém SDKs defensivo e de trajetória sob Apache-2.0, separação entre observações e ground truth, geração determinística, calibração somente na validação, avaliador isolado do ajuste, CI contra vazamento, integração OpenAI com Structured Outputs e telemetria operacional.

A evidência existente é propositalmente limitada. A v0.5 é reproduzível, mas seus resultados foram inspecionados durante o desenvolvimento e permanecem `reproducibility_only`. Eles não podem tornar-se evidência confirmatória retroativamente. Uma integração exploratória anterior executou 268 chamadas e 147.172 tokens, com custo configurado de US$ 0,028966. Ela demonstrou apenas o caminho de requisições e telemetria, não eficácia comparativa.

O protocolo v0.6 está na fase de desenho com `claim_eligibility: none` e `confirmatory_claims_allowed: false`. Não existem dataset, rótulos, previsões, resultados ou artefatos de freeze da v0.6. Isso é um controle científico deliberado.

### Nova população do estudo

O estudo conterá **200 trajetórias sintéticas produzidas independentemente**, 50 em cada família inédita:

1. `persistent_memory_poisoning` — comportamento inseguro emergindo após alteração persistente de memória;
2. `cross_agent_delegation_confusion` — autoridade ou intenção mudando durante handoffs;
3. `skill_mcp_supply_chain_compromise` — comportamento enganoso introduzido por skills, componentes MCP ou metadados;
4. `authorization_identity_drift` — pressupostos de identidade, papel ou permissão mudando ao longo do fluxo.

A distribuição pré-declarada por família é de 20 negativos benignos difíceis, 15 quase-violações e 15 violações consumadas. Cada caso terá 4–12 etapas, missão e política de fronteira explícitas, ground truth determinável e etapa de violação predefinida nos casos positivos.

Serão excluídos casos que reutilizem mecanismos ou templates da v0.5, contenham segredos reais ou dados pessoais, incluam exploits funcionais, dependam de sistemas externos não controlados ou não tenham desfecho determinável. Todos os recursos serão sintéticos ou locais.

### Custódia independente e congelamento

Um autor independente de casos/custodiante será contratado antes do freeze. Essa pessoa não ajustará o ARKHÉ e controlará rótulos e manifesto selado. Outro revisor identificado aprovará o protocolo.

Antes da abertura, o repositório registrará commit congelado, SHA-256 do protocolo, identificador exato retornado pelo provedor, prompts, schema, limiares, política de retentativas, regras de inclusão e exclusão, SHA-256 do manifesto assinado, custodiante e aprovador. Sem esses papéis, o protocolo não poderá ser congelado e nenhuma alegação confirmatória será feita.

### Comparador, detector e avaliação

O comparador primário será um classificador semântico por evento com **`gpt-6.1-sol`**, via Responses API e Structured Outputs. Ele receberá somente o evento corrente, nunca histórico ou ground truth.

O ARKHÉ receberá o mesmo evento e os passos observáveis anteriores. Ele utiliza sinais de missão, capacidade, fronteira, mudança de estado e persistência. Sua pontuação quadrática é um sinal de risco inspirado em sistemas dinâmicos, não prova de estabilidade de Lyapunov. Uma análise opcional com `gpt-6-astra` só poderá ocorrer após o resultado primário e será relatada separadamente.

O desenho utiliza um único conjunto de teste externo selado. Limiares, prompts, schemas e regras de retentativa serão bloqueados usando apenas artefatos históricos de desenvolvimento e validação; nenhum caso, rótulo ou predição da v0.6 será usado para calibração. A tarefa primária é a classificação antecipada de violações consumadas: o alerta deve ocorrer estritamente antes da etapa de violação. Pressão de fronteira será relatada separadamente.

Uma análise prospectiva de poder exato não utiliza resultados da v0.6. Com efeito pareado de 15 pontos, `alpha = 0,05` bicaudal e 50% de discordância total entre detectores, 200 casos fornecem poder de 83,64%; o mínimo exato é 183. Com 40% de discordância, o poder é 91,12%; com 60%, cai para 76,11%. O cenário de 50% é a premissa pré-declarada do desenho. Não haverá expansão da amostra orientada pelos resultados, e o cenário de 60% permanece uma limitação explícita.

A repetição 1 será primária. Repetições adicionais medirão reprodutibilidade e não serão agregadas como novas evidências. Depois das retentativas congeladas, saída ausente contará como erro do detector correspondente. Caso selado só poderá ser excluído se o custodiante registrar malformação antes da abertura. Todas as exclusões e denominadores serão publicados.

Não haverá parada opcional. As 200 trajetórias primárias serão executadas uma vez. A execução só poderá ser pausada por falha de segurança, integridade ou infraestrutura antes da inspeção dos resultados, retomando do pacote selado sob desvio documentado.

### Métricas e benefício público

O relatório publicará correção pareada, McNemar exato, TP/FP/TN/FN, precisão, recall, F1, taxa de falsos positivos, Wilson 95%, passos de antecipação, resultados por família, repetibilidade, latência, chamadas, tokens, retentativas, falhas, custo, exclusões e desvios.

Resultados positivos, nulos e desfavoráveis serão publicados. CI aprovada demonstra consistência da implementação, não superioridade. Resultados sintéticos não serão apresentados como validação em produção.

O dataset sanitizado será publicado sob CC-BY-4.0; harness, detectores, contratos e avaliador sob Apache-2.0. A liberação incluirá dataset card, threat model, pré-registro, guia de reprodução, relatório técnico e preprint aberto. Não serão incluídos segredos reais, malware, exploits de dia zero ou alvos não autorizados.

## Campo 5: Cronograma

- **Semana 1:** análise de sensibilidade; nomear custodiante e aprovador; finalizar prompt, schema e retentativas.
- **Semana 2:** bloquear detector, plano de análise, commit, identificador do modelo e hash do protocolo antes da autoria dos testes.
- **Semanas 3–5:** produzir, revisar, auditar e selar 200 casos sanitizados sob autoria independente; registrar o hash do manifesto assinado e concluir o congelamento final.
- **Semana 6:** executar comparador e ARKHÉ congelados; registrar previsões e telemetria; realizar a análise primária.
- **Semana 7:** executar reprodutibilidade sem agregar amostras; revisar protocolo; documentar desvios e limitações.
- **Semana 8:** publicar código, dados sanitizados, manifestos, relatório e preprint, incluindo resultados nulos ou negativos.

## Campo 6: Financiamento, Créditos e Recursos Solicitados

**Solicitação total: US$ 10.000**

| Item | Valor | Finalidade |
|---|---:|---|
| Pesquisa aplicada e engenharia | US$ 5.700 | Oito semanas de protocolo, implementação, execução, análise, documentação e publicação |
| Autor independente/custodiante e revisão | US$ 3.000 | Construção e custódia de 200 casos, selagem e revisão anterior à abertura |
| Créditos da API OpenAI | US$ 300 | Avaliação com `gpt-6.1-sol`, retentativas, repetibilidade e análise limitada com `gpt-6-astra` |
| Infraestrutura e publicação aberta | US$ 1.000 | Execução isolada, artefatos de CI, hospedagem, depósito com DOI e acessibilidade |

A parcela da API é deliberadamente modesta. Aos preços atuais, `gpt-6.1-sol` custa US$ 2 por milhão de tokens de entrada e US$ 10 por milhão de tokens de saída. A alocação suporta até aproximadamente 6.000 chamadas estruturadas, com contingência para retentativas, variação do perfil de tokens e uma execução limitada com Astra. IDs, tokens e custos reais serão publicados; créditos não utilizados não serão apresentados como despesa.

O projeto também solicita feedback metodológico sobre o desenho congelado. Não solicita implantação em produção, dados internos privilegiados ou acesso a sistemas de terceiros.

## Campo 7: Proponente e Equipe

**Pesquisador principal:** Creúsio Adolfo Gaspar Kizua, São Paulo, Brasil.

Creúsio possui mais de seis anos de experiência em sistemas financeiros e de pagamentos, observabilidade distribuída, APIs, resposta a incidentes e operações 24×7. Liderou equipe técnica de 13 profissionais e trabalhou com OpenTelemetry, Kubernetes, Prometheus, Grafana, Dynatrace, Elastic e ferramentas de confiabilidade. É o criador do benchmark, contratos, SDKs e controles experimentais abertos do ARKHÉ.

A candidatura é atualmente individual. O autor independente/custodiante e o aprovador serão selecionados e identificados antes do freeze. A remuneração está prevista. Nenhum revisor anônimo ou simulado será apresentado como validação independente.

## Campo 8: Novo Dataset

Sim. O projeto criará um dataset sintético de 200 trajetórias, produzido independentemente, cobrindo quatro famílias inéditas. Os desenvolvedores não receberão os rótulos antes do lock. A publicação excluirá credenciais reais, dados pessoais, exploits funcionais e informações confidenciais e incluirá proveniência, schemas, classes, limitações, hashes e licença CC-BY-4.0.

## Campo 9: Modelos OpenAI

- **Comparador primário:** `gpt-6.1-sol`, classificador por evento com Structured Outputs via Responses API.
- **Análise opcional:** `gpt-6-astra`, executada somente após o resultado primário e relatada separadamente.

Serão registrados identificador retornado pelo provedor, configuração, hash do prompt, retentativas, tokens, latência, erros e custo. Proxy offline não será apresentado como resultado de modelo OpenAI.

## Campo 10: Disponibilização dos Resultados

Código, schemas, protocolos, resultados agregados, dataset sanitizado e relatório técnico serão disponibilizados no GitHub e em repositório arquivístico aberto. Resultados positivos, nulos e negativos serão publicados. Materiais que criem risco desnecessário de uso indevido serão abstraídos, preservando evidência suficiente para reproduzir a avaliação defensiva.

## Gate de Submissão

Enviar somente após os testes de consistência EN/PT, nova verificação de modelos e preços, conferência dos links e contatos e aprovação final do proponente. Nenhum campo pode sugerir validação em produção, endosso da OpenAI ou evidência v0.6 já executada.
