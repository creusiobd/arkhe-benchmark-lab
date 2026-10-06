# Proposta de piloto — avaliação defensiva de agentes financeiros

**Proponente:** Creúsio, idealizador do ARKHÉ. **Organização participante:** [PENDENTE]. **Dono do fluxo:** [PENDENTE]. **Versão do pacote/commit:** [PENDENTE]. **Período e orçamento:** [A ACORDAR].

## Problema e hipótese

Um agente pode solicitar ferramenta ou recurso fora de seu escopo, executar uma ação sem aprovação válida ou tratar conteúdo de ferramenta como autoridade. Queremos verificar se eventos confiáveis do host, políticas explícitas e histórico auditável tornam esses desvios visíveis com ruído e custo aceitáveis em **um fluxo específico**. A hipótese será testada; não se promete detectar toda injeção de prompt.

## Escopo inicial proposto

Agente de conciliação em ambiente de laboratório: leitura de registros sintéticos autorizados, tentativa de leitura fora do escopo e preparação de alteração que exige aprovação humana vinculada à ação. Operações financeiras reais ficam fora do laboratório. O fluxo exato, ferramentas e recursos serão definidos pelo participante.

O SDK defensivo opera em **observe**: recebe propostas e conclusões, confronta a política ativa e emite decisões com evidências. Não autentica produtores, não executa ferramentas e não concede autorização financeira. Controles existentes do host permanecem responsáveis pela execução.

## Entrega

Mapa do fluxo e das fronteiras; adaptador de eventos do host; política versionada; casos benignos e de violação com rótulos independentes; replay reproduzível; medições de cobertura, falsos alertas, detecção e custo; relatório das falhas e critérios de avanço. Demonstração MCP usa recursos sintéticos e valida somente a integração implementada pelo host, sem certificar todo o protocolo/ecossistema.

## Etapas e decisão

1. Laboratório local autorizado: dados sintéticos, sem destinos externos, sem credenciais reais.
2. Avaliação congelada: política, baseline e conjunto de teste registrados antes de medir.
3. Shadow opcional: somente após aceite do laboratório e autorização escrita do dono do ambiente para coleta saneada. Não altera decisões nem executa mitigação financeira.
4. Revisão conjunta: avançar, corrigir e repetir ou encerrar segundo critérios previamente acordados.

Não há compromisso de shadow, prazo fixo ou contratação implícita. A entrada de dados reais exige novo escopo e autorização. Validação externa, ganhos econômicos e redução de incidentes permanecem por demonstrar.
