# ARKHÉ Benchmark Dataset v0.3 — Relatório de Diversidade e Isolamento

- **Versão do Dataset:** v0.3.0
- **Total de Trajetórias:** 65
- **Total de Passos Operacionais:** 282
- **Vocabulário Único:** 340 termos
- **Razão Tipo-Token (TTR):** 0.0754
- **Garantia de Desconexão (Holdout Disjointness):** CONFIRMADA (100% templates disjuntos)

## 1. Distribuição por Split

| Split | Trajetórias | Passos | Benign | Near-Violation | Violation | Famílias Cobertas |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **development** | 20 | 87 | 7 | 7 | 6 | 5/5 |
| **validation** | 10 | 43 | 4 | 3 | 3 | 5/5 |
| **test** | 20 | 87 | 7 | 7 | 6 | 5/5 |
| **blind_holdout** | 15 | 65 | 5 | 5 | 5 | 5/5 |

## 2. Garantia Anti-Leakage de Identificadores

Todos os identificadores de trajetória seguem estritamente a máscara hexadecimal opaca `traj_<16_hex_chars>`. Nenhuma sigla heurística (`BEN`, `NEA`, `VIO`) ou sufixo semântico está presente nos arquivos observáveis ou nos identificadores de ground truth.
