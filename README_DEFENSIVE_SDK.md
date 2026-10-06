# ARKHÉ Defensive SDK 0.2.0 alpha

Núcleo Python independente para avaliação defensiva contínua de ações de agentes. Distribuição `arkhe-defense-sdk`; import `arkhe_defense`. Somente Pydantic é dependência de execução. Não importa benchmark, autorização de cartões, FastAPI ou bibliotecas de modelos.

## Fronteira de confiança

A aplicação hospedeira autentica o produtor, resolve cliente, principal, papel, permissões e vínculo da trajetória, e fornece `RuntimeContext` separado do evento. Criar esse objeto não autentica ninguém. Nunca monte o contexto copiando campos de um payload não confiável. O executor deve emitir as conclusões de execução; o agente não pode afirmar que executou uma ação com autoridade de executor.

Políticas são provisionadas por `policy_admin` com `policy:write`, isoladas por cliente e ativadas explicitamente. Uma versão existente não pode receber conteúdo diferente. SHA-256 identifica o conteúdo; não é assinatura digital. O agente não escolhe uma versão antiga para recuperar privilégios. A missão é metadado administrativo: as regras explícitas determinam a avaliação, sem interpretação semântica por LLM.

Aprovações exigem principal distinto do agente e `approvals:write`. Vinculam cliente, trajetória, agente, ação, ferramenta, recurso, parâmetros resumidos e versão da política. Expiração considera relógio do host e revogação é reavaliada na conclusão. O host precisa autenticar o aprovador e proteger relógio, registry e armazenamento.

## Uso

Execute `python examples/defense/reconciliation.py` na árvore fonte. O exemplo provisiona dois clientes, avalia leitura, escrita com aprovação e execução indevida; não executa transações.

```python
from arkhe_defense import DefenseSDK, SDKConfig
sdk = DefenseSDK(policy_provider, config=SDKConfig())
decision = sdk.ingest(event, authenticated_runtime_context)
```

Estados: `within_policy` significa compatível com a política e evidência disponíveis; `approval_required` exige aprovação; `policy_violation` indica desvio; `insufficient_evidence` exige tratamento conservador. Nenhum estado autoriza ou bloqueia ferramentas automaticamente. Uma decisão local favorável não certifica toda a trajetória: confira também `has_observed_violation`, `first_alert_event_id` e `context_loss_reason`.

## Configuração

JSON validado, sem campos desconhecidos:

```json
{"schema_version":"1","mode":"observe","max_payload_bytes":65536,"state_limits":{"ttl_seconds":1800,"max_active_trajectories":10000,"max_events_per_trajectory":1000,"max_parent_ids":16,"max_depth":128}}
```

`PolicySnapshot` contém `tenant_id`, `policy_id`, `version`, `mission` e `rules`. Cada regra declara ferramenta, tipo de ação, recursos permitidos e necessidade de aprovação. Ausência de regra nega por padrão. Recursos admitem igualdade, prefixo de caminho com fronteira ou host exato. Caminhos relativos, travessia, UNC e escapes percentuais são recusados. O executor deve resolver symlinks e o recurso real antes da avaliação. Uma regra de host não restringe porta nem caminho de URL.

Eventos tipados: `ActionProposed`, `ActionCompleted`, `ApprovalRecorded`, `PolicyChanged`, `TrajectoryClosed`. Eventos exigem identidade, cliente, agente, trajetória, produtor e horários com timezone. Campos de avaliação/ground truth são rejeitados inclusive em estruturas aninhadas. Envie parâmetros resumidos e saneados; validação não remove dados pessoais automaticamente.

## Estado e limites

Estado particionado por `(tenant_id, trajectory_id)`. IDs duplicados com conteúdo diferente geram conflito. TTL, capacidade, pais ausentes, ciclos e profundidade excessiva produzem evidência insuficiente. Violações observadas permanecem sinalizadas durante a retenção; fechamento não as apaga. Eventos atrasados não revisam automaticamente decisões anteriores. A perda do registro limitado de evicções é conservadora.

Esta versão é alpha, serial e em memória. Reinício perde contexto: o host deve exigir nova trajetória ou restaurar evidência confiável. Não há persistência, autenticação de transporte, assinatura de políticas, avaliação distribuída, fila durável ou certificação de isolamento de processo. Um processo por cliente pode ser exigido pelo modelo de ameaça. A exportação JSONL é síncrona e registra decisões; falha de exportação fica em `last_export_error` e não muda a avaliação.

## Empacotamento e CLI

Em um ambiente novo, instale as dependências de build: `python -m pip install "setuptools>=77" wheel`. Veja [instalação completa](SDK_QUICKSTART.md).

`python sdk/build.py` gera wheel, sdist e manifesto em `.review-build/defense-0.2.0`. O staging preservado pode ser compilado independente do benchmark. Instale o wheel com pip.

`arkhe-defense doctor`, `validate-config arquivo.json`, `validate-policy politica.json`.

Replay: `arkhe-defense replay eventos.jsonl --contexts contextos.json --policy politica.json --output decisoes.jsonl`. Contextos são registros `{event_hash, context}`, vinculados ao digest canônico do evento por `arkhe_defense.cli.event_digest`. Esse sidecar deve ser controlado pelo operador; ele não fornece autenticação criptográfica e serve para replay local. Em produção, use identidade autenticada pelo transporte e contexto fornecido pela aplicação.
# Sessão durável — 0.2.0 alpha local

`DurableDefenseSession(provider, config, db_path, tenant, clock=None, max_rows=100000)` oferece `ingest(event, context)`, `close()` e context manager. Use um banco e diretório protegido por cliente. Ao reabrir, a sessão reproduz observações com seus horários originais e exige as mesmas políticas históricas e decisões. Configuração e orçamento de linhas ficam vinculados ao diário.

SQLite guarda eventos/contexto em texto claro; autenticação continua no host. Um lock exclui escritores concorrentes. Falha de gravação encerra a sessão; orçamento esgotado rejeita novos registros. Não há compactação automática, operação distribuída nem garantia de execução única de ferramentas externas. Consulte SECURITY.md e reports/team/durable-journals-2026-10-06.md.
