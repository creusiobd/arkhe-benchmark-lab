# Continuidade — candidatura OpenAI Cybersecurity Grant v0.6

## Problema em resolução

Transformar o pacote de candidatura, antes baseado na v0.5 planejada, em uma
proposta coerente com o estado atual do repositório: v0.5 limitada a
reprodutibilidade e v0.6 ainda em desenho, sem evidência confirmatória.

## O que foi testado

- alinhamento das versões em inglês e português;
- limite de 200 palavras da descrição do problema;
- coerência entre protocolo v0.6, modelo, amostra, famílias e orçamento;
- ausência de alegações de produção, parceria ou resultado confirmatório;
- bloqueio do freeze enquanto custodiante, manifesto selado e aprovador estiverem
  ausentes.

## Resultado atual

- quatro famílias inéditas e 200 trajetórias planejadas em um teste externo selado;
- comparador primário `gpt-6.1-sol`;
- efeito mínimo relevante de 15 pontos percentuais;
- regras de ausência e parada registradas;
- candidatura EN/PT atualizada para solicitar US$ 10.000;
- protocolo permanece corretamente em `stage: design` e não pode congelar.

## Endurecimento pós-PR #14

- distribuição contratual: 50 casos por família;
- classes contratuais por família: 20 benignos, 15 quase violações e 15 violações;
- SHA-256 do manifesto aceita somente 64 caracteres hexadecimais minúsculos;
- gate de freeze confere o manifesto privado, sua composição, IDs únicos e hashes de
  conteúdo sem publicar os rótulos;
- manifesto vinculado ao ID e à versão do protocolo, com conteúdos duplicados
  rejeitados;
- hipótese exploratória H2 alinhada às quatro famílias da v0.6.

## Sensibilidade prospectiva

- método: poder exato incondicional para McNemar bicaudal;
- efeito mínimo: 15 pontos percentuais; `alpha = 0,05`; poder-alvo de 80%;
- cenário de desenho: 50% de discordância total;
- `n = 200`: poder de 83,64%; mínimo exato de 183;
- cenário de 60%: poder de 76,11%, mantido como limitação explícita;
- orçamento realocado: US$ 5.700 para engenharia e US$ 3.000 para autoria,
  custódia e revisão, sem alterar o total de US$ 10.000.

## Próxima hipótese e ação

**Hipótese:** uma candidatura que financia custódia independente e um teste v0.6
pré-registrado é mais defensável do que uma candidatura que tenta promover os
resultados internos v0.5.

**Próximas ações:** revisar a sensibilidade da amostra; reconfirmar modelo e preços;
obter aprovação humana do texto; publicar a branch em PR sem merge e sem submeter o
formulário. Depois de eventual financiamento, bloquear detector e análise antes da
autoria independente, selar o manifesto somente após a criação dos casos e então
congelar o protocolo para execução.
