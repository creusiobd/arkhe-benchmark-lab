# Reconciliação e demonstração — 2026-10-06

Branch local: `codex/sdk-defensive-pilot`. Base pública: `83b3dcc45e36babe5689cf63151c1afe461e7aaf`. O benchmark continua0.3.0; os SDKs são distribuições independentes0.2.0 alpha. Importação seletiva preservou o código, resultados e contratos do benchmark público. Dossiê pessoal, ambientes de teste e logs locais antigos não foram importados.

## Resultado verificável

- Regressão offline: **318 testes e 38 subtestes passaram**. Um teste live OpenAI foi ignorado porque exige opt-in e chave; um aviso Starlette/httpx pertence ao legado. Não houve chamada à API.
- Wheels e sdists dos dois SDKs: inventário, hashes, licença e reconstrução a partir do sdist aprovados.
- Ambiente novo criado do zero: instalação offline dos dois wheels e Pydantic, `pip check`, imports dos journals e CLI `doctor`/`validate-config` passaram fora do checkout via Python isolado.
- Demo MCP STDIO real: duas ações sintéticas executadas, uma tentativa bloqueada pelo host, nenhuma chamada ao recurso privado. Agente roteirizado; não é medida de resistência de LLM ou ganho contra baseline.
- [Evidência saneada](validation.json) registra base, ambiente, resultados, hashes dos artefatos e limites. A matriz remota Windows/Linux ainda depende do CI de revisão.

## Correções de integração

O namespace local antigo `benchmark` importava módulos do harness que não deveriam acompanhar o laboratório. O namespace acrescentado agora contém somente o laboratório controlado, sem importar o benchmark legado.

O checkout Windows alterava finais de linha e quebrava hashes congelados também na base intacta. Os blobs originais conferiram com os hashes existentes; restauração exata e `.gitattributes` preservam esses bytes. Não houve mudança de conteúdo, rótulos, relatório de freeze ou seus hashes.

Os guias agora incluem dependências de build para venv novo. A documentação pública recebeu seções para os SDKs sem substituir a proposta/benchmark existente. CONTRIBUTING usa separação verificável, coerente com o README, em vez de garantia absoluta de ausência de leakage. Segurança dos SDKs permanece experimental, com canal e compromisso de resposta a confirmar pelo responsável.

## Uso e piloto

Siga [quickstart](../../SDK_QUICKSTART.md), [demo](../../examples/defense/README.md) e [kit de piloto](../../docs/pilot/README.md). O piloto defensivo começa no laboratório; observação de ambiente real exige autorização explícita e dados minimizados. Cartões/jornadas operacionais permanecem separados.

Creúsio é apresentado como idealizador independente, sem parceiro confirmado. Nenhuma proposta foi enviada, parceiro contatado, pacote publicado no PyPI ou implantação realizada. A revisão de código não equivale a validação externa de produto.
