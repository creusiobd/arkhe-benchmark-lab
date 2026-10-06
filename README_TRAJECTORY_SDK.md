# ARKHÉ Trajectory SDK 0.2.0 alpha

Núcleo observacional configurável para inteligência de trajetórias. Cartões é uma aplicação própria, com perfil específico; defesa de agentes permanece no pacote separado `arkhe-defense-sdk`. Distribuição local `arkhe-trajectory-sdk`, import `arkhe_trajectory`, sem dependências de execução além da biblioteca padrão Python 3.10+.

A arquitetura permite mapear telemetria de diferentes fontes ao contrato canônico. Aplicabilidade depende de identidade/correlação, eventos com horários confiáveis, sinais mensuráveis e regras calibradas para a jornada. Não existe garantia de cobertura de qualquer infraestrutura ou previsão universal.

## Começo rápido

Antes do build, instale ``setuptools>=77`` e ``wheel`` no ambiente de desenvolvimento. Veja [instalação completa](SDK_QUICKSTART.md).

Compile: `python trajectory-sdk/build.py`. Instale o wheel gerado em `.review-build/trajectory-0.2.0` usando pip.

```powershell
arkhe-trajectory init --preset cards --tenant meu-banco --output jornada.json
arkhe-trajectory validate-config jornada.json
arkhe-trajectory replay eventos.jsonl --config jornada.json --output avaliacoes.jsonl
arkhe-trajectory doctor
```

Presets instalados: `cards`, `infrastructure`, `fulfillment`. Todos os limiares e baselines são ilustrativos; ajuste com dados reais. `init` e exportação recusam sobrescrever arquivos existentes. JSON desconhecido ou inválido é recusado. Replay é local e não se conecta à infraestrutura. Ele simula o relógio histórico a partir de `ingested_at`; isso não autentica horários. No uso embutido, o relógio padrão é o do host.

Exemplo com os três perfis: `python examples/trajectory/demo.py --output-dir results/trajectory-alpha`. Na árvore fonte, configure `PYTHONPATH` para a raiz do projeto se o pacote não estiver instalado. Eventos e avaliações são exportados separados; toda a demonstração é sintética.

## Integração embutida

```python
import json
from arkhe_trajectory import JourneyConfig, JourneyEngine, TrajectoryEvent
config = JourneyConfig.from_dict(json.load(open('jornada.json')))
engine = JourneyEngine(config)
event = TrajectoryEvent.from_dict(payload_normalizado)
assessment = engine.ingest(event)
# Scheduler da aplicação chama check mesmo sem novos eventos:
assessment = engine.check(config.tenant_id, trajectory_id)
```

O host seleciona a configuração e autentica a fonte. O evento não pode trocar cliente, jornada ou versão da instância. Uma instância opera serialmente com configuração imutável; nova versão exige nova instância/histórico. Hash de configuração aparece nas avaliações para rastreabilidade; não é assinatura, nem há registro distribuído de versões.

`MappingAdapter(mapping, metric_mapping, dimension_mapping)` mapeia caminhos de dicionário, como `body.trace_id` ou `measurements.queue`. Sem scripts ou execução de expressões. É um adaptador local de formato; não é um conector ativo Kafka, OTLP, banco ou cloud. Coletores e transporte pertencem ao host.

## Configuração de jornada

Veja os exemplos completos em `configs/journeys/`. Campos:

| Campo | Uso |
|---|---|
| schema_version | `1`, versão do contrato |
| tenant_id / journey_id / version | Escopo e revisão controlados pelo host |
| steps | IDs livres, próximos passos permitidos e prazo opcional |
| window_seconds | Janela móvel em tempo de evento |
| baseline | Valores de referência manuais por métrica |
| rules | Comparação, agregação, severidade, amostras e persistência |
| max_lateness_seconds | Tolerância atrás do maior tempo de evento recebido |
| ttl_seconds | Retenção por inatividade no relógio do host |
| max_events / max_trajectories / max_payload_bytes | Limites de recursos |

`steps.expected_next` declara alternativas sequenciais permitidas. Não representa fork concorrente de DAG. Repetições consecutivas de um mesmo passo são observações do passo e não reiniciam seu prazo. Passos distintos no mesmo horário são ambíguos, produzindo insuficiência. Atraso ou falta de próximo passo tem evidência própria; ausência não prova falha do serviço. Para detectar ausência, o host deve chamar `check`; o SDK não inicia scheduler.

Regras suportam `gt`, `ge`, `lt`, `le`; agregações `latest`, `mean`, `min`, `max`, `slope`; referência `absolute`, `delta` ou `relative`. `delta = observado - baseline`; `relative = (observado - baseline) / abs(baseline)`, com baseline diferente de zero. Declínio adverso usa operador `lt` com limiar negativo. Para `slope`, a comparação é absoluta em unidades da métrica por segundo; baseline é apenas contexto da evidência, não uma inclinação.

Tendência usa regressão linear da janela com tempos de evento. Requer ao menos dois tempos distintos. `min_samples` controla aquecimento; `persistence` exige violações em prefixos consecutivos de amostras pertinentes. Duplicatas e chamadas a `check` não aumentam persistência. Ela serve para filtrar alertas, não estima probabilidade de incidente ou causalidade. Regra com `step_id` considera somente aquele passo; falta de amostras exigidas permanece explícita.

Não há aprendizagem automática ou reajuste silencioso do baseline. Thresholds absolutos não dependem do baseline; regras delta/relative dependem. Ciclos/regimes comerciais precisam de perfis separados e seleção explícita pelo host. Uma regra não modifica outra: findings conservam severidade, valor, baseline, comparação, limiar, amostras e IDs de evidência.

## Contrato de eventos e significado da avaliação

Evento: `tenant_id`, `journey_id`, `journey_version`, `trajectory_id`, `event_id`, `step_id`, `event_time`, `ingested_at`, `metrics`, `dimensions`, `outcome` opcional e `schema_version`. Horários ISO com timezone; `ingested_at` não precede `event_time`. Métricas numéricas finitas, dimensões escalares limitadas. Campos desconhecidos são rejeitados. Outcome/dimensões são contexto, sem regra semântica implícita.

`trajectory_id` identifica uma instância de fluxo **ou** uma série agregada estável. Nunca misture uma transação de cartão e janelas do canal no mesmo ID. Para dados agregados, o ID deve incluir partição relevante, por exemplo serviço/rota/região. Dimensões não particionam estado automaticamente. Separar jornadas não autentica clientes nem fornece isolamento de processo.

A avaliação inclui `evaluated_at` e `window_end`, distinguindo relógio de avaliação e fim da janela em tempo de evento. Telemetria mais antiga que a janela do relógio do host gera `telemetry_stale`; ela não comprova saúde atual.

Estados:

- `normal`: nenhuma regra desviou na evidência disponível; não certifica completude da jornada nem saúde de tudo o que existe.
- `deviation`: regra configurada ou transição/prazo observado desviou.
- `insufficient_evidence`: métricas/amostras ausentes, prazo de próximo passo sem evidência, ordem ambígua ou histórico perdido. Findings já conhecidos continuam presentes; consumidores devem inspecioná-los mesmo nesse estado.

Dados ausentes nunca recebem defaults saudáveis. Tendências históricas fora da janela não influenciam métricas atuais. Verificação histórica exclui eventos conhecidos apenas depois de `as_of`; não é restauração completa de snapshots. Eventos atrasados dentro da tolerância recalculam a avaliação atual sem revisar resultados anteriores. Atraso além da tolerância, TTL e evicção marcam perda de contexto; a instância/ID não retorna a uma afirmação limpa após essa perda. Duplicata idêntica retorna a decisão original com seu horário histórico; use `check` para estado atual após perda de contexto; mesmo ID com conteúdo diferente é conflito.

## Frente de cartões

O perfil declara receipt → validation → fraud_check → limit_lookup → authorization → response, com prazos próprios. `channel_window` permite observar latência p95, fila, retry, timeout e **recusa técnica**. Recusa comercial não equivale a degradação; não use queda global de aprovação como falha sem classificação adequada. IDs individuais de jornada e IDs de série do canal ficam separados.

p95 e taxas dos presets já são agregados upstream. O motor não calcula p95 por transação nem faz média ponderada por volume; `mean` é média simples das observações. Mantenha denominador, tamanho de janela, unidades e partição estáveis. Não envie PAN, CVV ou dados pessoais: o SDK não faz anonimização automática. Sem chamadas a adquirente/emissor, decisão de crédito, bloqueio ou mudança de autorização.

## Limites e validação

Alpha observacional, estado serial em memória, sem recuperação após reinício, backfill durável, assinatura de configuração, scheduler, exportação assíncrona, alertas enviados ou implantação de infraestrutura. Limites de contagem não são orçamento de performance comprovado; avaliação percorre histórico e regras. Testes de carga e perfil de memória são etapa própria.

Exemplos e testes demonstram comportamento determinístico. Sinais de tendência antes de um threshold absoluto em dados sintéticos não provam antecipação real. Piloto deve medir falsos positivos, incidentes perdidos, lead time, cobertura, qualidade de correlação e regime sazonal com separação temporal entre calibração e validação.


# Retenção e durabilidade — 0.2.0 alpha local

`max_evidence_refs` (padrão32) limita referências por achado; `max_findings` (padrão128) limita achados exportados por avaliação. `evidence_truncated`, `total_findings` e `findings_truncated` tornam o corte explícito. Estatísticas e status usam o conjunto completo antes do corte. Duplicatas preservam avaliações históricas.

`DurableJourneySession(config, db_path, clock=None, max_rows=100000)` oferece `ingest`, `check`, `close` e context manager. Um diário protegido por cliente registra ingestões e checks, inclusive duplicatas, e recupera estado por replay com horários originais. Configuração é imutável por diário; esgotamento do orçamento rejeita novos registros.

O diário SQLite é texto claro, serial e local. Hashes detectam corrupção acidental; não autenticam um arquivo controlado por adversário. Não há compactação automática nem coordenação distribuída. Consulte SECURITY.md e reports/team/durable-journals-2026-10-06.md.
