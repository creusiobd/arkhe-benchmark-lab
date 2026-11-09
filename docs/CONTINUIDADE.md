# Registro de continuidade — validação externa

Atualizado em: 2026-11-09  
Branch ativa: `feat/external-validation-readiness`

## 1. Problema que estamos tentando resolver

O ARKHÉ possui evidência de engenharia em ambiente controlado, mas ainda não possui validação independente nem evidência operacional externa.

A pergunta ativa é:

> A análise de trajetória identifica violações de fronteira antes de detectores baseados em eventos isolados, com uma taxa de falsos positivos aceitável, quando aplicada a um fluxo que não foi criado pelo próprio projeto?

## 2. O que já foi testado

- geração determinística e separação entre observações e ground truth;
- comparação experimental com baselines de evento isolado;
- integração exploratória com API real;
- SDKs alpha de defesa e trajetória;
- replay durável, contratos de política e demonstração MCP controlada;
- protocolo prospectivo v0.5 definido;
- kit de piloto documentado.

## 3. Resultado atual

### Evidência existente

- O código e os contratos demonstram consistência de engenharia em laboratório.
- Os artefatos sintéticos permitem reprodução interna.
- A demonstração MCP prova integração controlada, não eficácia em produção.
- O piloto v0.4 é exploratório e não sustenta ganho comparativo confirmatório.
- O protocolo v0.5 existe, mas a implementação prospectiva permanece em branch divergente e não deve ser tratada como resultado confirmado.
- Não existe ainda cliente, ambiente shadow aprovado ou execução independente por terceiro.

### Classificação honesta

- Maturidade técnica: protótipo funcional alpha.
- Maturidade experimental: intermediária.
- Maturidade operacional: pré-piloto.
- Maturidade comercial: não validada.

## 4. Próxima hipótese

> Em um incidente encerrado, reproduzido offline com eventos saneados e fonte de verdade independente, o ARKHÉ consegue antecipar a violação ou pressão de fronteira em relação ao baseline congelado, sem exceder a tolerância de falsos alertas acordada antes da execução.

## 5. Próxima ação

1. Congelar os gates de validação.
2. Padronizar o pacote de evidências por execução.
3. Selecionar um fluxo retrospectivo sem dados pessoais, credenciais ou ações de produção.
4. Definir baseline, métricas, denominadores e critérios de parada antes do resultado.
5. Executar primeiro como ensaio interno.
6. Solicitar reprodução independente.
7. Buscar piloto retrospectivo com parceiro somente após G1.

## 6. Regra de continuidade

Ao encerrar cada sessão, registrar:

- problema investigado;
- hipótese;
- testes executados;
- resultado observado;
- limitações;
- arquivos ou commits produzidos;
- próxima hipótese;
- próximo comando ou decisão.

## Histórico

| Data | Problema | Teste | Resultado | Próxima hipótese |
|---|---|---|---|---|
| 2026-11-09 | Ausência de validação externa | Auditoria do estado das branches e evidências | A `main` contém o SDK atual; a implementação v0.5 está divergente; não há prova operacional externa | Construir gates e protocolo retrospectivo a partir da `main` |
