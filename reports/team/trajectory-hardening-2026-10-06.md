# Otimização de trajetória — 2026-10-06

Implementados limites por configuração: max_evidence_refs=32 e max_findings=128. Ambos exigem inteiro positivo. São tetos de retenção, não orçamento de memória total do processo.

Cada finding conserva as referências mais recentes até o limite, evidencia corte com evidence_truncated e preserva sample_count/elapsed_seconds sobre a amostra integral usada no cálculo. Resultados continuam calculados sobre todos os sinais elegíveis; não se calcula score ou média só sobre o subconjunto exportado. Findings estruturais também respeitam esse limite de referências.

Assessment conserva os últimos max_findings na ordem de produção (regras configuradas primeiro, depois transições/deadlines cronológicos); total_findings e findings_truncated explicitam a perda de detalhe. Status deriva do conjunto completo ANTES do corte. Consequentemente corte de evidências/detalhes não transforma desvio em normal. Ausência, contexto perdido e eventos atrasados continuam insuficientes quando aplicável.

Hash de configuração é computado uma vez por instância sobre o snapshot validado imutável. Amostras, valores e comparações de regras equivalentes, prefixos de persistência e referências são compartilhados dentro de cada avaliação; caches não sobrevivem entre janelas/as_of. Regras com limiares, operadores e mínimos distintos mantêm essas condições separadas. Duplicatas exatas devolvem os snapshots históricos originais, sem trocar suas evidências pelo último resultado.

Validação: **58 testes de trajetória passaram, 12 subtestes**, incluindo 6 novos testes de otimização (4 subtestes). Oracle matemática independente usa statistics.mean/linear_regression, janelas explícitas e persistência; não carrega implementação antiga. Cobre latest/mean/min/max/slope e referências absolutas/delta/relativas; cache hash, compartilhamento seguro, preservação histórica e budget de referências. Jornada estrutural alternada com 99 transições inválidas exporta 8 findings sob limite8, mantém total99/statusdeviation e respeita orçamento N*max_findings*max_evidence_refs. Snapshot antigo permanece apenas como artefato histórico results/sdk-hardening/engine-before.py, sem dependência dos testes.

## Medição local antes/depois

Mesmo workload anterior: 1.000 eventos de prefixo +48 novos, 32 regras, desvio ativo, uma trajetória/tenant, janela3600s e TTL7200s, sem transporte ou LLM. Relógio controlado e nenhum truncamento de eventos/janela. Execuções sem tracer e com tracer separadas; timeout rígido de60s.

|Indicador|Antes|Depois|
|---|---:|---:|
|p50 local ms|26.208|3.767|
|p95 local ms|37.438|7.189|
|p99 local ms|46.639|7.236|
|Eventos/s em laço serial|36.86|239.28|
|Referências lógicas retidas|17,589,632|1,057,280|
|Memória Python live MiB|não medida: profiler timeout60s|11.376|
|Pico Python MiB|não medido: profiler timeout60s|11.773|

Redução de referências lógicas: 93.99%. Tuplas de evidência equivalentes também são compartilhadas entre regras, portanto contagem lógica não é número de slots físicos únicos. Budget de referências métricas agora é <=N*R*max_evidence_refs; budget geral <=N*max_findings*max_evidence_refs. Memória ainda inclui eventos, fingerprints, assessments e objetos de findings.

O profiler agora concluiu, prefixo38.29s, sem confundir custo de tracemalloc com tempo de ingestão normal. Todos1048 resultados foram deviation em ambas execuções após otimização; nenhuma insuficiência contou como capacidade saudável. Amostra48 e host compartilhado tornam as latências ilustração local, não SLO, TPS distribuído ou prova causal isolada de ganho. Tracemalloc não mede RSS total. Fontes/hashes e comandos estão nos JSON novos; auditoria anterior não foi sobrescrita.

Limites restantes: reavaliar histórico/ordenar janelas ainda custa CPU conforme tamanho retido; transições completas são calculadas antes do corte (objetos transitórios podem crescer). Limites de bytes globais/RSS, carga concorrente, durabilidade e transportes não fazem parte desta otimização. Nenhum contrato de defesa de agentes ou código legado foi alterado.

CLI validate-config passou para cards, fulfillment e infrastructure sem alterar JSON antigos; defaults max_evidence_refs32/max_findings128 aplicados. Primeira chamada usou equivocadamente nome validate, rejeitado pelo parser; corrigida para comando real validate-config. JSON novos de assess incluem total_findings/findings_truncated e porfinding evidence_truncated; serializer CLI usa to_dict e os publica automaticamente. Hash engine/config/contracts permaneceu consistente entre medição e relatório; __init__ mudou por atualização coordenada de versão, sem alteração no motor medido.
