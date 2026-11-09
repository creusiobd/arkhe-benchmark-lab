# Registro de continuidade — validação externa

Atualizado em: 2026-11-09  
Branch ativa: `feat/g1-prospective-pipeline`

## 1. Problema

O ARKHÉ possui evidência de engenharia em ambiente controlado, mas ainda não possui validação independente nem evidência operacional externa.

> A análise de trajetória identifica violações de fronteira antes de detectores de eventos isolados, com falsos positivos aceitáveis, quando aplicada a um fluxo não criado pelo projeto?

## 2. O que já foi testado

- geração determinística e separação entre observações e ground truth;
- comparação experimental com baselines de evento isolado;
- integração exploratória com API real;
- SDKs alpha, replay durável, contratos de política e demonstração MCP;
- protocolo v0.5, kit de piloto e gates de validação.

## 3. Resultado atual

- Código e contratos demonstram consistência de engenharia em laboratório.
- Artefatos sintéticos permitem reprodução interna.
- MCP prova integração controlada, não eficácia em produção.
- v0.4 é exploratório e não sustenta ganho confirmatório.
- v0.5 foi inspecionado durante o desenvolvimento; é somente integração e reprodutibilidade.
- Não existe cliente, shadow autorizado ou execução independente.

Classificação: protótipo alpha; maturidade experimental intermediária; operação pré-piloto; comercial não validada.

## 4. Hipótese ativa

> Em um incidente encerrado, reproduzido offline com eventos saneados e verdade independente, o ARKHÉ antecipa violação ou pressão de fronteira em relação ao baseline congelado sem exceder a tolerância de falsos alertas definida antes da execução.

## 5. Próxima ação

1. Fazer a CI reproduzir v0.5 em checkout limpo.
2. Revisar o pacote e preservar falhas.
3. Preparar v0.6 como estudo prospectivo com teste não inspecionado.
4. Solicitar reprodução independente.
5. Selecionar fluxo retrospectivo sem dados pessoais, credenciais ou ações de produção.
6. Buscar piloto retrospectivo somente após os gates anteriores.

## 6. Regra de continuidade

Registrar problema, hipótese, testes, resultado, limitações, arquivos/commits, próxima hipótese e próximo comando ou decisão.

## Histórico

| Data | Problema | Teste | Resultado | Próxima hipótese |
|---|---|---|---|---|
| 2026-11-09 | Ausência de validação externa | Auditoria de branches e evidências | SDK atual na `main`; v0.5 divergente; sem prova externa | Construir gates a partir da `main` |
| 2026-11-09 | v0.5 fora da linha principal | Integração seletiva sem resultados históricos | Código, corpus, protocolo, testes e CI preparados; v0.5 limitado a `integration_only` | Validar checkout limpo e revisar G1 |
