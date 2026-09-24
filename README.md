# ARKHÉ Benchmark Lab: Validação Empírica & Física de Filas

Este laboratório comprova matematicamente e empiricamente a **hipótese de antecedência operacional do ARKHÉ** (5 a 8 minutos antes dos alertas tradicionais de mercado) e calcula o **Custo de Oportunidade da Inércia (COI)** auditável.

---

## 1. Fundamentos da Modelagem (Lei de Little & Concorrência Real)

O laboratório rejeita simulações estocásticas arbitrárias. Toda a dinâmica de saturação decorre da **Lei de Little** ($L = \lambda W$) e da física de filas $M/M/c$:

* **Capacidade do Pool ($C_{\max}$):** 30 conexões concorrentes (`asyncio.Semaphore(30)`).
* **Taxa de Chegada Nominal ($\lambda$):** 80 transações por segundo (TPS).
* **Tempo de Serviço Nominal ($W_s$):** 45 ms $\implies L = 80 \times 0.045 = 3.6$ slots em uso (**12% de ocupação**).
* **Drift Inicial ($T_{+3\text{min}}$):** Latência sobe para 255 ms $\implies L = 80 \times 0.255 = 20.4$ slots (**68% de ocupação**, sem timeouts nem alertas clássicos).
* **Ponto de Ruptura ($T_{+10\text{min}}$):** Latência atinge 420 ms $\implies L = 33.6 > 30$ (**saturação total**, formação de fila física e estouro do timeout de 1.500 ms).
* **Tempestade de Retries:** Clientes recebendo 503/504 disparam até 2 retries com backoff curto, elevando a taxa efetiva para >170 TPS.

---

## 2. Estrutura do Ecossistema Containerizado (Passo 3)

```
arkhe-benchmark-lab/
├── app.py                      # API FastAPI: 6 estágios, semáforo adaptativo, WebSocket 10 FPS e Cockpit
├── load_gen.py                 # Emulador de tráfego assíncrono (80 TPS) com retries em cascata
├── arkhe_detector.py           # Motor ARKHÉ: Vetor de aceleração S_ARKHÉ e derivadas de saturação
├── traditional_monitor.py      # Baseline SRE Google/Prometheus (P95 > 1500ms / Erros > 5%)
├── coi_engine.py               # Calculadora Auditável do Custo de Oportunidade da Inércia (COI)
├── sentinel_live_monitor.py    # Ponte canônica de integração contínua com ARKHÉ Sentinel Core
├── test_websocket_stream.py    # Validador de streaming bidirecional a 10 FPS (< 15ms latência)
├── test_autonomous_mitigation.py # Validador de mitigação closed-loop (Predictive HPA)
├── benchmark_runner.py         # Orquestrador cego de testes (baterias automatizadas e teste t)
├── report_generator.py         # Gerador de dossiê visual HTML interativo com Chart.js
├── Dockerfile                  # Imagem slim multi-engine com healthcheck nativo
├── Dockerfile.load             # Imagem ultraleve do gerador de carga (httpx assíncrono)
├── docker-compose.yml          # Topologia com bridge network, healthcheck e perfis
├── .dockerignore               # Otimização de contexto de build
├── run_docker_stack.ps1        # Script 1-click para subir cluster Docker com logs e cockpit
├── run_live_cockpit.ps1        # Script para execução local em background
└── run_sentinel_live_test.ps1  # Script de teste integrado Sentinel Core + Lab
```

---

## 3. Como Executar com Docker & Docker Compose (Passo 3)

### Opção A: Execução 1-Click via PowerShell
Inicia os containers com healthcheck integrado, abre o cockpit unificado no navegador e exibe logs em tempo real:
```powershell
.\run_docker_stack.ps1
```

### Opção B: Execução Manual via Docker CLI
```bash
# Sobe o microserviço e o gerador de carga com verificação de saúde
docker compose up -d

# Visualiza logs em tempo real
docker compose logs -f

# Acessa o Cockpit Interativo
# http://localhost:8080

# Derruba o cluster
docker compose down
```

### Opção C: Executar Bateria de Auditoria Científica Headless no Docker
```bash
# Executa 5 baterias de caos e gera o relatório científico dentro do container
docker compose --profile benchmark run --rm benchmark-runner
```

---

## 4. O Vetor de Aceleração do ARKHÉ

Diferente das ferramentas de monitoramento reativas (Prometheus / Datadog / CloudWatch) que aguardam o estouro de limiares estáticos após os erros ocorrerem, o ARKHÉ monitora o **vetor de aceleração estrutural**:

$$\vec{S}_{\text{ARKHÉ}} = \left( \frac{d}{dt}\rho_{\text{pool}}, \quad \frac{W_q}{W_s}, \quad R_{\text{retry}} \right)$$

1. $\frac{d}{dt}\rho_{\text{pool}}$: Taxa de variação temporal da utilização do semáforo por minuto.
2. $\frac{W_q}{W_s}$: Razão entre o tempo médio de fila ($W_q$) e o tempo intrínseco de serviço ($W_s$).
3. $R_{\text{retry}}$: Fator de amplificação de retries na borda ($\frac{\text{Tentativas Totais}}{\text{Transações Únicas}}$).

---

## 5. Modelo Matemático do COI (Custo de Oportunidade da Inércia)

$$\text{COI}(\Delta t) = \sum_{t \in \Delta t} \lambda_{\text{unique}}(t) \times \Delta A_{\text{tech}}(t) \times \Big( \underbrace{V_{\text{avg}} \times M_{\text{take}}}_{\text{Perda Direta de Margem}} + \underbrace{P_{\text{churn}} \times LTV_{\text{impact}}}_{\text{Desgaste de LTV do Lojista}} \Big)$$

* **Ticket Médio ($V_{\text{avg}}$):** R\$ 180,00
* **Take Rate ($M_{\text{take}}$):** 2,5% (R\$ 4,50/tx)
* **Probabilidade de Churn por Fricção ($P_{\text{churn}}$):** 38%
* **Custo de Aquisição / LTV Impactado ($LTV_{\text{impact}}$):** R\$ 45,00
* **Perda Total por Pedido Frustrado:** R\$ 21,60
