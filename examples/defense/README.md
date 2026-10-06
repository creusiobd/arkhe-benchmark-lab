# Demonstração defensiva controlada

Execute na raiz do checkout com Python3.10+ e Pydantic2 instalado:

```powershell
python -m examples.defense.pilot_demo --output-dir results/defense-pilot-demo
```

Abra `results/defense-pilot-demo/index.html` no navegador. O arquivo é independente, sem CDN, JavaScript, frontend ou servidor web obrigatório. O comando recusa sobrescrever diretório existente; para repetir, escolha outro caminho.

A sequência contém leitura permitida, resultado com instrução maliciosa e tentativa de escrita indevida bloqueada. Transporte MCP STDIO usa processo e pipes reais; dados/ferramentas são sintéticos. O agente é roteirizado e a próxima ação já está definida: não há LLM, chave de API, transação financeira real ou teste de resistência cognitiva a prompt injection.

Saídas: HTML, JSON completo, mensagens de transporte, eventos, decisões, gabarito em arquivo separado e manifesto SHA-256 dos fontes/artefatos. Hashes ajudam a reconstruir a execução; não são assinatura criptográfica de origem. O SDK observa as ações; o executor do hospedeiro bloqueia chamadas fora da política. A demo não certifica conformidade completa com MCP nem superioridade de detecção.

Teste relevante:

```powershell
python -m unittest tests.audit.test_pilot_demo -v
```

O exemplo anterior `reconciliation.py` permanece como referência de uso direto do SDK. Para comparar a integração com um controle forte do hospedeiro, use `python -m benchmark.mcp_lab --outputdir results/mcp-comparison` em diretório novo.
