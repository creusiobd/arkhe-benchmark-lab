# Laboratório MCP controlado — implementação e limites

Data: 2026-10-06. Construído em `benchmark/mcp_lab.py`, separado do SDK e do benchmark legado. **Há agora cliente/servidor local com transporte STDIO real e executor sintético controlado. O agente é roteirizado; nenhum LLM foi executado.**

## Escopo protocolar

Subconjunto fixado em MCP **2025-11-25**: processo filho real, JSON-RPC2.0 UTF-8 delimitado por newline, initialize, notifications/initialized, tools/list e tools/call. Correlação de IDs, limite de mensagem64KiB, prazo de resposta e encerramento do processo são explícitos. Uso de ferramentas antes da notificação initialized é rejeitado; métodos desconhecidos e argumentos inválidos retornam erro. Stdout do servidor contém apenas mensagens.

O formato segue as referências oficiais [STDIO](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports), [lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle) e [tools](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/server/tools.mdx). Trata-se de implementação deliberadamente pequena de uma versão fixada, sem certificação de conformidade completa ou claim da versão mais recente. Não implementa HTTP, OAuth, sessões HTTP, recursos/prompts, sampling, paginação, concorrência ou todas as notificações.

## Fronteira do hospedeiro

- Comando do servidor é fixo: mesmo arquivo do laboratório e executável Python. Não aceita comando arbitrário fornecido pelo agente.
- Origem local inclui ID atribuído pelo hospedeiro, transporte, caminho do executável e hash do módulo. Admitir essa origem é uma política local, não autenticação criptográfica de servidor remoto.
- Catálogo esperado é configurado pelo operador, com versão1.0.0 e hash canônico completo. Descriptions/annotations são comparadas ao catálogo aprovado, nunca usadas para conceder autoridade.
- Hospedeiro verifica catálogo antes da proposta e antes do despacho, detectando mudanças no cenário controlado de rebinding.
- Routes, ferramenta, operação e recurso vêm de mapeamento explícito. Todos os argumentos reais, origem e hash/versão do catálogo são vinculados à proposta; conclusão referencia hash da chamada.
- Executor despacha somente decisões permitidas. O SDK permanece em observe; a aplicação hospedeira é quem bloqueia.
- Ferramentas leem/ajustam somente dados sintéticos em memória, sem acessar arquivos financeiros, rede ou infra real. Variáveis de API_KEY são removidas do processo filho e não são exibidas.

Verificação de catálogo tem limite TOCTOU: servidor malicioso pode mentir sobre descritores ou mudar comportamento depois da verificação. O laboratório não demonstra que um servidor arbitrário deixe de executar efeitos ocultos. Isolamento das ferramentas sintéticas torna o experimento seguro e delimita a prova.

## Comparação e cenários

Dois modos executam a mesma política explícita: strong_host (match de regras e aprovação vinculada, sem DefenseEvaluator) e sdk (DefenseEvaluator real mais admissão/execução do hospedeiro). O controle forte compartilha as primitivas de política e hash do SDK, portanto não é avaliador independente desses componentes nem produto concorrente. Evita o falso ganho obtido contra allowlist fraca apenas de nomes.

Nove cenários: leitura benigna, injection no resultado de ferramenta, descriptor poisoning, mudança de catálogo/rebinding, leitura de recurso privado, escrita sem aprovação, escrita aprovada, aprovação expirada e texto de recuperação. Agente roteirizado escolhe ações predefinidas por cenário; não interpreta/decide com LLM se seguirá o texto malicioso. Não há prova de resistência cognitiva a prompt injection.

## Execução e artefatos

Comando: Python bundled `-m benchmark.mcp_lab --outputdir results/mcp-lab-2026-10-06`. O runner recusa sobrescrever diretório existente. Resultado:

| Indicador local sintético | strong_host | sdk |
|---|---:|---:|
| Cenários |9|9|
| Ações executadas |4|4|
| Ações bloqueadas |7|7|
| Chamadas ao recurso privado |0|0|

Os 18 runs corresponderam às contagens de execução esperadas. Isso é conformidade com scripts de laboratório, não precisão/recall populacional, antecipação ou superioridade do SDK.

Artefatos em `results/mcp-lab-2026-10-06`: `transport.jsonl` com mensagens reais de pipes, `runs.jsonl`, `events.jsonl`, `decisions.jsonl`, `summary.json` e `labels.json`. Gabarito fica em arquivo separado e só é usado na avaliação final; não entra em evento/contexto/política do SDK. Summary inclui hash do fonte e limitações. CLI stdout preservado em `tests/audit/mcp-lab-cli.txt`.

Testes: `tests/audit/test_mcp_lab.py`, execução `-m unittest tests.audit.test_mcp_lab -v`; log `tests/audit/mcp-lab-tests.txt`. **13 testes passaram, zero falhas/erros,39,947s**, incluindo comparação de dois replays idênticos. Cobrem processo real/lifecycle, correlação/formato, erros, allowlist de origem, poisoning/rebinding, limites, scope, aprovações, recovery sticky, binding da chamada, separação do gabarito e recusa de sobrescrita.

O checkout local declara distribuição0.2.1 em pyproject.toml. Estes resultados não equivalem a validar um repositório público identificado como0.3.0: versões/fontes/artefatos exigem execução e revisão próprias. O laboratório não publica pacote nem altera release.

Compatibilidade de CI mínimo: executado `tests/audit/minimal_dependency_check.py` usando pytest local, com autoload de plugins desativado e imports scipy/numpy/yaml/FastAPI/httpx/OpenTelemetry/websockets proibidos. **20 testes e10 subtests passaram,43,20s; nenhum extra proibido carregado.** Log `tests/audit/minimal-dependencies.txt`. Posteriormente três testes stdlib do verificador de release também passaram, sem ampliar dependências.

## O que permanece pendente

Agente/modelo real em sandbox, MCP servidor remoto autenticado, catálogos reais versionados, avaliação independente de famílias inéditas, ataques ofuscados e provas de efeitos do executor. A integração aqui pertence a benchmark/lab, não a um adapter de produção instalado no namespace arkhe_defense.

O resultado válido é: políticas e binding foram exercitados através de mensagens MCP STDIO reais em ambiente controlado, com rastreabilidade e comparação forte. Não anunciar solução geral de prompt injection, prevenção independente do hospedeiro, conformidade MCP completa ou ganho de detecção nesta amostra.
