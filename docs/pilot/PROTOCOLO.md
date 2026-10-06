# Protocolo executável de piloto

## Preparação e laboratório

Antes de rodar, preencher AUTORIZACAO.md e escolher um fluxo, uma versão de host, um catálogo de ferramentas e quem decide a política. Creúsio prepara o pacote; o dono do ambiente confirma seu direito de autorizar o escopo. Aprovação para laboratório não autoriza produção.

- Inventariar ferramentas, recursos, fronteiras de escrita, ponto de autenticação e aprovações. Definir quem fornece identidade, missão e política oficial.
- Usar dados e credenciais sentinela sintéticos; destinos externos bloqueados no ambiente. Registrar versões e hashes do pacote, configuração e casos.
- Integrar ActionProposed antes da chamada e ActionCompleted após resultado conhecido. Se só houver spans encerrados, declarar cobertura posterior e não alegar defesa preventiva.
- Exercitar leitura legítima, recurso proibido, escrita sem aprovação, aprovação válida/expirada/revogada, tentativa de trocar política, produtor desconhecido, evento ausente/duplicado e perda de contexto.
- Capturar efeitos reais pelo executor do laboratório, separadamente do texto produzido pelo agente. Nenhum resultado narrativo equivale a prova de execução.

A primeira rodada ajusta a instrumentação. Não usar seus casos como teste final cego.

## Avaliação congelada

Separar calibração e teste por famílias de casos. Um revisor não envolvido no ajuste atribui rótulos e arbitra casos ambíguos; se isso não for possível, registrar avaliação interna e sua limitação. Congelar política, baseline explícito do host e versões antes do teste. Mudança necessária invalida a comparação daquela rodada: registrar e repetir com novo conjunto.

Comparar ARKHÉ com política existente do host ou baseline de regras com memória, no mesmo conjunto, sem enfraquecer o baseline. Medir tentativas e sucesso de ações fora da política separadamente. Benchmark sem LLM real não sustenta comparação com modelo semântico real.

O aceite do laboratório depende de evidências rastreáveis, ausência de execução financeira real, visibilidade de insuficiência e metas acordadas em METRICAS.md. Um número bom com cobertura baixa não fecha o gate.

## Shadow autorizado

Gate exclusivo: dono do ambiente, segurança e dono dos dados aprovam coleta, minimização, retenção, destino, acesso e desligamento. [Responsáveis e data: PENDENTES].

Receber cópia saneada dos eventos de um fluxo elegível. SDK permanece observacional; a integração não deve conceder ferramentas/permissões, contornar aprovação ou substituir controles do host. Medir qualquer overhead de instrumentação no fluxo, mesmo quando o avaliador fica fora do caminho de execução. A estratégia de transporte é validada no ambiente, não presumida pelo nome de um adaptador.

Não introduzir cenários adversariais em produção sem autorização distinta, explícita e específica. Para investigar um evento observado, exportar somente o material aprovado; reproduzir em laboratório sempre que possível.

## Encerramento e suspensão

Suspender coleta se aparecer dado fora da allowlist, destino não aprovado, falha de isolamento ou overhead acima do limite acordado. SDK indisponível/perda de contexto é insuficiência, não segurança comprovada. O responsável de plantão [PENDENTE] aciona o procedimento de desligamento [PENDENTE], sem intervenção financeira pelo ARKHÉ.

Entregar relatório com amostra/denominadores, resultados por classe, casos perdidos, falhas de instrumentação, versões, limitações e recomendação. Dono dos dados confirma retenção/descarte e responsável pelo fluxo assina a decisão de avanço. Nenhum contato externo ou publicação de evidências é parte implícita deste protocolo.
