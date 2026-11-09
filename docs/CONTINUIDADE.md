# Registro de continuidade — validação externa

Atualizado em: 2026-11-09  
Branch ativa: `feat/v0.6-preregistered-study`

## 1. Problema

O ARKHÉ possui evidência de engenharia reproduzível em ambiente controlado, mas ainda não possui validação independente nem evidência operacional externa.

> A análise de trajetória identifica violações de fronteira antes de detectores de eventos isolados, com falsos positivos aceitáveis, quando aplicada a casos inéditos que não foram usados no desenvolvimento?

## 2. O que já foi testado

- geração determinística e separação entre observações e ground truth;
- comparação experimental com baselines de evento isolado;
- integração exploratória com API real;
- SDKs alpha, replay durável, contratos de política e demonstração MCP;
- pipeline v0.5 reproduzido em checkout limpo com 1.200 previsões;
- cinco pipelines do PR #12 aprovados.

## 3. Resultado atual

- v0.5 está integrado na `main` e permanece limitado a `integration_only`.
- Código e contratos demonstram consistência de engenharia em laboratório.
- A demonstração MCP prova integração controlada, não eficácia em produção.
- Não existe ainda teste confirmatório intocado, cliente, shadow autorizado ou execução independente.
- v0.6 começa na fase de desenho, sem dataset nem resultados.

Classificação: protótipo alpha; maturidade experimental intermediária; operação pré-piloto; comercial não validada.

## 4. Hipótese ativa

> Em casos inéditos sob custódia independente, o ARKHÉ melhora a classificação correta e antecipada de violações em relação a um comparador congelado, sem abrir tolerância posterior para falsos alertas.

## 5. Próxima ação

1. Fechar fonte da evidência e custódia independente.
2. Selecionar pelo menos quatro famílias inéditas.
3. Justificar tamanho da amostra e efeito mínimo relevante.
4. Escolher um único comparador primário e o modelo semântico exato.
5. Definir regras de ausência, parada e desvio.
6. Registrar o hash do manifesto selado.
7. Congelar o protocolo antes de qualquer geração ou inspeção do teste.

## 6. Regra de continuidade

Registrar problema, hipótese, testes, resultado, limitações, arquivos/commits, próxima hipótese e próximo comando ou decisão.

## Histórico

| Data | Problema | Teste | Resultado | Próxima hipótese |
|---|---|---|---|---|
| 2026-11-09 | Ausência de validação externa | Auditoria de branches e evidências | SDK atual na `main`; v0.5 divergente; sem prova externa | Construir gates a partir da `main` |
| 2026-11-09 | v0.5 fora da linha principal | Integração seletiva sem resultados históricos | Código, corpus, protocolo, testes e CI preparados; v0.5 limitado a `integration_only` | Validar checkout limpo e revisar G1 |
| 2026-11-09 | Reprodutibilidade interna | PR #12 e cinco pipelines | Merge concluído; G1 técnico reproduzível; ainda sem confirmação externa | Pré-registrar v0.6 antes de criar dados |
