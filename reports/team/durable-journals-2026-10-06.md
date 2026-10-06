# Journals locais duráveis — 2026-10-06

Implementados wrappers opt-in `arkhe_defense.DurableDefenseSession(provider, config, db_path, tenant, clock=None, max_rows=100000)` e `arkhe_trajectory.DurableJourneySession(config, db_path, clock=None, max_rows=100000)`. O primeiro expõe ingest(event, context); o segundo ingest(event) e check(tenant, trajectory, as_of=None). Ambos expõem close e context manager. Os motores em memória continuam disponíveis; esta persistência só existe quando o wrapper é utilizado.

## Semântica

SQLite com synchronous FULL, ledger e metadados na mesma transação por operação. Ownership exclusivo usa transação BEGIN IMMEDIATE em banco sidecar `.lock` por toda a sessão; o banco de dados de observações tem conexão distinta para commits. Segunda sessão cooperante no mesmo caminho é recusada. Serialidade e afinidade de thread da conexão permanecem; não há serviço distribuído ou replicação. Não remover/renomear o sidecar enquanto há sessão ativa. O diretório e os dois arquivos devem ser controlados pelo host, em filesystem com semântica de locking confiável; network shares não foram validados.

No defense, persistem evento, contexto recebido do host, receipt clock, versão/hash de política e decisão. Replay exige provider com todas as versões históricas inalteradas, avaliando cada linha com a política e relógio originais. A decisão recuperada deve coincidir com a registrada. A política corrente e relógio atual voltam a reger novas ações, portanto aprovação expirada não volta a valer. Contextos sem autoridade e eventos futuros não entram no ledger. Ausência de política para novo append falha fechada. A troca de política durante avaliação é evitada fixando o snapshot do append.

No trajectory, toda operação bem-sucedida de ingest/check, inclusive duplicatas, é registrada e reavaliada com receipt original. Checks precisam ser registrados porque alteram expiração/estado. Hash de configuração é vinculante; configuração diferente é recusada. Schema de configuração é revalidado antes de criar o motor. Both wrappers verificam sequência, contagem e cauda de cadeia de hashes, detectando alterações e exclusões acidentais; hashes não autenticam o arquivo nem impedem adulteração por quem controla armazenamento.

Após erro de avaliação/escrita/commit no caminho mutável, a sessão é tainted e fechada, impedindo continuação com estado em memória divergente do ledger. Reabrir reconstrói apenas operações comprometidas. Crash após commit mas antes de resposta deixa linha comprometida recuperável. Não existe garantia exactly-once para ferramentas externas, pagamentos ou entrega de alertas, e estes wrappers não executam ações financeiras.

## Limites

- Armazenamento plaintext: evento/parameters_summary/effects_summary e contexto podem conter dados sensíveis. Host sanitiza antes de ingestão, protege ACLs e define retenção; não há criptografia, anonimização automática ou assinatura.
- Budget `max_rows` é explícito e vinculado ao banco; saturação fecha a sessão. Não há descarte automático, compactação ou migração de configuração. Operador precisa de procedimento controlado de arquivamento e nova sessão/jornada.
- Recovery lê uma linha por sequência e refaz avaliação serial; não materializa o ledger completo em RAM. O estado do motor continua limitado pela configuração. Budget de linhas não é orçamento de bytes, memória ou tempo de recovery comprovado. Testes de carga, grandes históricos e filesystem remoto pendentes.
- Dependências externas inexistentes para SQLite; defense mantém Pydantic existente. trajectory não importa defense.
- Estado subjacente continua limitado por TTL/capacidade. Replay preserva perdas e incompletudes observadas, não ressuscita histórico que o núcleo descartou.

## Evidência executada

Runtime Python bundled, comando `python -m unittest tests.defense.test_journal tests.trajectory.test_journal -v`: **18 testes aprovados**, 10.980s, exit 0. Testes: recovery equivalente, bloqueio segunda sessão, contexto/futuro sem persistência, tenant/config binding, capacidade fail closed, adulteração de linha, exclusão cauda, política histórica ausente, aprovação expirada no novo receipt, falha de escrita fecha/tainta e restart sem estado não comprometido, replay de ingest duplicado e check de TTL.

Uma execução intermediária falhou ao limpar tempfile Windows porque a conexão usada pelo próprio teste de adulteração permanecia aberta; teste corrigido com close explícito e replay cursor materializado/fechado. Não foi demonstrado kill abrupto de processo, perda de energia, commit ambíguo real ou crash injection no filesystem. O teste `query_only` cobre falha de escrita transacional, não falha de energia em commit. Suíte completa e distribuição instalada ficam a cargo da integração; resultados acima são testes focados de fonte.

## Revisão adversarial interna posterior

Esta revisão foi feita pelo autor do wrapper e não constitui auditoria independente. Encontrou e corrigiu dois problemas concretos: recovery `fetchall` duplicava o ledger completo em RAM; passou a consulta por sequência, uma linha de cada vez. No defense, metadados de binding ausentes com ledger existente podiam ser recriados; agora recuperação recusa esse estado. Configuração defense já instanciada também é reconstruída para executar validação real.

Acrescentados testes de metadados apagados, política ativa trocada seguida de duplicata e TTL, e check histórico seguido de clock regression. Comando focado repetido: **21 testes aprovados**, 16.705s, exit 0. Preservados exports e versões públicas 0.2.0. Persistem fronteiras: host pode adulterar arquivo e hashes, budget de disco em bytes não é explicitamente configurado, contextos podem conter dados sensíveis, tempo de recovery não medido. Replay streaming remove cópia proporcional ao ledger em memória; não prova consumo constante do motor ou filesystem.

Regressão integrada posterior `python -m pytest tests -q --junitxml=reports/sdk-hardening/regression.xml` com bundled Python, dependências locais previamente instaladas, modo offline e sem chave OpenAI: **278 aprovados, 46 subtestes aprovados, 1 warning**, 92.26s, exit 0. Warning legado: `StarletteDeprecationWarning` no wrapper FastAPI testclient sobre uso de httpx. Logs em `reports/sdk-hardening/regression.txt` e XML no caminho acima. Esse gate cobre fonte atual; validação de wheels reconstruídos é gate separado da coordenação.
