# ARKHÉ v0.6 — Resumo da Candidatura ao OpenAI Cybersecurity Grant

**Estado da submissão:** Enviada em 10/11/2026; recebimento confirmado por e-mail da OpenAI; análise pendente.
**Limite do registro:** Este resumo é a referência versionada da proposta no repositório, não uma exportação literal verificada do formulário externo.
**Respostas canônicas:** [`form_answers_PT.md`](form_answers_PT.md)
**Versão em inglês:** [`form_answers_EN.md`](form_answers_EN.md)

## Objetivo

Solicitar US$ 10.000 para executar um estudo defensivo pré-registrado, com custódia
independente, sobre controles de segurança de agentes orientados à trajetória.

## Evidência atual

- O repositório contém SDKs, contratos, geração determinística, avaliação isolada,
  integração OpenAI, telemetria, CI e infraestrutura v0.5 reproduzível.
- A v0.5 foi inspecionada durante o desenvolvimento e permanece
  `reproducibility_only`.
- Não se afirma eficácia em produção, generalização externa ou superioridade
  confirmatória.
- A v0.6 não possui dataset ou resultados. O contrato de desenho proíbe linguagem
  confirmatória antes do congelamento do protocolo e do manifesto selado.

## Estudo financiado

- 200 trajetórias sintéticas produzidas por autor independente, 50 por família;
- quatro famílias inéditas: envenenamento de memória persistente, confusão de
  delegação entre agentes, comprometimento da cadeia de skills/MCP e deriva de
  autorização/identidade;
- comparador primário: `gpt-6.1-sol` por evento com Structured Outputs;
- endpoint primário: correção pareada da classificação antecipada;
- efeito mínimo relevante de 15 pontos percentuais;
- poder exato de 83,64% no cenário de desenho pré-declarado com 50% de discordância;
- McNemar exato, intervalos de Wilson e telemetria completa;
- publicação de resultados positivos, nulos e negativos.

## Gate de independência

Antes do freeze, o projeto deve nomear autor independente/custodiante e aprovador,
concluir a análise de sensibilidade e registrar o SHA-256 do manifesto selado. Sem
esses requisitos, nenhuma execução confirmatória ocorrerá.

## Orçamento

| Item | Valor |
|---|---:|
| Pesquisa aplicada e engenharia | US$ 5.700 |
| Autor independente/custodiante e revisão | US$ 3.000 |
| Créditos da API OpenAI | US$ 300 |
| Infraestrutura e publicação aberta | US$ 1.000 |
| **Total** | **US$ 10.000** |

## Registro de submissão

A candidatura v0.6 foi enviada em 10/11/2026. A OpenAI confirmou o recebimento por
e-mail na mesma data e informou que as propostas são analisadas de forma contínua.
Nenhum número de candidatura foi fornecido. O recebimento não implica seleção,
financiamento, endosso ou parceria. Não enviar candidatura duplicada, salvo se a
OpenAI solicitar ou se houver correção material, versionada e expressamente justificada.
