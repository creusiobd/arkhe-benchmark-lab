# SDKs — não publicado

- Defesa: o avaliador recusa relógio do host que retroceda (`DefenseError`). Antes, uma regressão de relógio permitia que aprovação expirada autorizasse conclusão retroativa.
- Sessão durável de defesa: todo recebimento observado, persistido ou não, passa a ser o piso para detectar regressão de relógio.
- Defesa: ciclo, profundidade excessiva e excesso de pais produzem `insufficient_evidence`, como documentado, em vez de `DefenseError`. O evento não entra no grafo. Antes, um produtor confiável, inclusive o próprio agente observado, podia contaminar e fechar a sessão durável com dois eventos.
- Defesa: excesso de pais é decidido antes de criar ou tocar o estado da trajetória; não despeja mais outra trajetória ativa.

# SDKs — 0.2.0 alpha local

- Limites explícitos de evidências e achados nas avaliações de jornadas, preservando contagem completa e indicação de truncamento.
- Reutilização de cálculos equivalentes por avaliação e cache do hash da configuração.
- Sessões duráveis SQLite por cliente, com recuperação por replay, exclusão de escritor concorrente e orçamento finito de linhas.
- Laboratório MCP por STDIO com servidor sintético, baseline de host forte e rótulos separados.
- Licença no pacote e workflow de validação independente dos SDKs.

Essa versão foi preparada localmente. Publicação, execução remota de CI e validação com parceiro são etapas pendentes. A versão do benchmark permanece independente.
