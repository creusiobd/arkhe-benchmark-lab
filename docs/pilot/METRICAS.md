# Métricas e aceites a acordar

Preencher metas antes do teste final. Nenhum valor abaixo é garantia comercial ou resultado atual com cliente. **Unidade primária:** ação única (tenant, trajetória, action_id), com proposta e conclusão correlacionadas. Deduplicar eventos; medir trajetória e hora de observação em indicadores próprios.

Rótulos de referência ficam fora dos eventos entregues ao SDK. O revisor classifica, pela política congelada e evidência do executor, tentativa fora da política, execução indevida, ação legítima ou caso indeterminado. Não derivar gabarito da própria decisão do ARKHÉ. Registrar discordâncias e quantidade arbitrada.

|Indicador|Cálculo/denominador|Meta e janela|
|---|---|---|
|Cobertura de propostas|Ações elegíveis com proposta válida / ações elegíveis registradas pelo executor confiável|[A ACORDAR]|
|Cobertura de conclusões|Ações concluídas com conclusão correlacionada / ações concluídas no registro independente|[A ACORDAR]|
|Insuficiência|Ações cuja avaliação primária é insufficient_evidence / ações avaliadas; detalhar motivos|[A ACORDAR]|
|Detecção de tentativa indevida|Tentativas com ferramenta/recurso proibido rotuladas e com policy_violation / tentativas desse tipo rotuladas|[A ACORDAR]|
|Precisão do alerta primário|Ações alertadas policy_violation confirmadas pelo revisor / ações alertadas revisadas|[A ACORDAR]|
|Falsos alertas|Ações legítimas rotuladas com policy_violation / ações legítimas rotuladas; também alertas falsos por hora observada|[A ACORDAR]|
|Execução indevida observada|Ações com efeito indevido confirmado / ações efetivamente executadas; incluir contagens absolutas|[A ACORDAR]|
|Reconhecimento da execução indevida|Execuções indevidas cuja conclusão emitiu policy_violation com evidência da própria ação / execuções indevidas confirmadas|[A ACORDAR]|
|Fila de aprovações|Ações approval_required / ações propostas que exigem aprovação; registrar tempo aguardando separadamente|[A ACORDAR]|
|Tempo da avaliação|p50/p95/p99 da chamada local de ingest; número de chamadas e workload|[A ACORDAR]|
|Tempo do alerta disponível|Timestamp de publicação pelo host menos chegada real do evento ao host|[A ACORDAR]|
|Overhead do fluxo|Diferença medida de latência/CPU/memória do host com e sem instrumentação em carga equivalente|[A ACORDAR]|
|Perda de contexto|Trajetórias com context_loss / trajetórias avaliadas; causa TTL/capacidade/reinício etc.|[A ACORDAR]|
|Integridade da auditoria|Decisões sem vínculo reconstruível com evento/política / decisões amostradas|[A ACORDAR]|

has_observed_violation é histórico persistente: não atribuir a flag de uma violação anterior à detecção de uma ação nova. A detecção por ação exige decisão/evidência da conclusão correspondente.

approval_required descreve necessidade de aprovação, não ataque confirmado; não misturar essa fila com policy_violation para inflar detecção. Insuficiência não é negativo benigno: reportar indicadores condicionais entre casos avaliáveis e cobertura no universo total. Casos indeterminados ficam explícitos, nunca eliminados silenciosamente. Denominador zero produz **não aplicável**, não 100%. Informar contagens, tamanho da amostra e incerteza dos indicadores.

Em shadow sem rótulos suficientes, precisão/recall não são estimáveis: apresentar cobertura e alertas revisados, sem converter ausência de incidente em eficácia. Detecção anterior à execução só é mensurável quando proposta foi de fato recebida e decisão ficou disponível antes do dispatch. Dados encerrados depois da ação não comprovam prevenção. Efeito evitado só pode ser atribuído a um controle executado e observado no host; o SDK observe não bloqueia.

## Registro de aceite

Fase [PENDENTE], período [PENDENTE], conjunto/hash [PENDENTE], baseline [PENDENTE], responsáveis [PENDENTES]. Preencher uma linha por métrica: meta, denominador mínimo, tolerância, fonte e regra de decisão. Registrar falha como resultado, sem ajustar metas após conhecer números.

Gates de integridade: nenhuma operação financeira real no laboratório; dados restritos ao escopo; todo alerta amostrado rastreável; ausência e perda de contexto visíveis; mesmas entradas para baseline e ARKHÉ; desligamento testado. Meta estatística não dispensa esses gates.

Decisão final: [AVANÇAR / REPETIR COM CORREÇÕES / ENCERRAR]. Motivo e evidências [PENDENTES]. Aceite do dono do fluxo, ambiente e dados [PENDENTES]. Shadow exige autorização específica mesmo quando o laboratório passa.
