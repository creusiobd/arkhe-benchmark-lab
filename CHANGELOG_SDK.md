# SDKs — não publicado

- Trajetória: entrada inválida levanta `EventRejectedError` (nova base de `DuplicateEventError`) antes de alterar estado. A sessão durável recusa essa entrada sem se contaminar; antes, um único evento inválido de qualquer fonte, ou um `check` com tenant errado, encerrava a sessão.
- Trajetória: `event_id` reutilizado com outro conteúdo é recusado antes de tocar a trajetória e não renova mais o TTL.

# arkhe-defense-sdk 0.3.0 alpha — 2026-10-19

Mudanças incompatíveis; revise a integração antes de atualizar:

- Ciclo, profundidade excessiva e excesso de pais produzem `insufficient_evidence`, como o README já documentava, em vez de `DefenseError`. `missing_fields` indica `event_graph_cycle`, `event_graph_depth` ou `parent_count`. O evento não entra no grafo, e descendentes que o citem ficam com pai ausente. Autorreferência continua inválida no contrato.
- Relógio do host que retroceda levanta `DefenseError` no avaliador. Na sessão durável, recebimento anterior a qualquer outro já observado levanta `JournalError` sem contaminar a sessão.
- Conflito de `event_id` e payload acima de `max_payload_bytes` levantam `EventRejectedError`, nova base de `EventConflictError` e subclasse de `DefenseError`, antes de qualquer mudança de estado. Na sessão durável, essas recusas sobem como `EventRejectedError` em vez de `JournalError`, e a sessão continua aberta.

Correções:

- Segurança: uma regressão do relógio do host permitia que aprovação já expirada autorizasse conclusão retroativa (`within_policy` em vez de `policy_violation`).
- Disponibilidade: um produtor confiável, inclusive o próprio agente observado, podia contaminar e fechar a sessão durável com um ciclo, uma cadeia de pais profunda, excesso de pais, reuso de `event_id` ou payload grande.
- Excesso de pais é decidido antes de criar ou tocar o estado e não despeja mais outra trajetória ativa. Reenvio conflitante não renova mais o TTL da trajetória.
- Documentação: os READMEs deixam de afirmar que não há persistência ou recuperação após reinício; ambas existem com as sessões duráveis.

Build e compatibilidade:

- `sdk/build.py` lê a versão de `sdk/pyproject.toml` e interrompe o build se ela divergir de `arkhe_defense.__version__`.
- Formato do diário inalterado: diários gravados pela 0.2.0 reabrem na 0.3.0 com as mesmas decisões.
- Wheel e sdist são gerados por `sdk/build.py` e verificados por `scripts/verify_sdk_release.py`; não há publicação em índice de pacotes.

# SDKs — 0.2.0 alpha local

- Limites explícitos de evidências e achados nas avaliações de jornadas, preservando contagem completa e indicação de truncamento.
- Reutilização de cálculos equivalentes por avaliação e cache do hash da configuração.
- Sessões duráveis SQLite por cliente, com recuperação por replay, exclusão de escritor concorrente e orçamento finito de linhas.
- Laboratório MCP por STDIO com servidor sintético, baseline de host forte e rótulos separados.
- Licença no pacote e workflow de validação independente dos SDKs.

Essa versão foi preparada localmente. Publicação, execução remota de CI e validação com parceiro são etapas pendentes. A versão do benchmark permanece independente.
