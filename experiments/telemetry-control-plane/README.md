# ARKHÉ Telemetry & Shadow Control Plane (APM Lab)

> **Contexto Experimental:** Este diretório isola o laboratório de observabilidade em tempo real, simulação estocástica de tráfego (M/M/c/K) e mitigação autônoma em malha fechada (Closed-Loop Autonomous Self-Healing) baseado em física de filas (Lei de Little, Razão $W_q/W_s$) e controle por bacia de estabilidade de Lyapunov.
> 
> Esta frente de engenharia é mantida como um caso de uso experimental complementar e prova de valor (PoV) para sistemas distribuídos de alta vazão, enquanto o escopo principal do repositório é o **ARKHÉ Agent Boundary Defense Benchmark**.

---

## 1. Visão Geral da Arquitetura

O laboratório de telemetria simula um ecossistema de autorização de pagamentos com cartão estruturado em 6 nós arquiteturais:

```
[Gateway Ingress] ──> [HSM & Limites] ──> [Semáforo Little] ──> [Pool Antifraude] ──> [Adquirente Externa] ──> [Ledger Contábil]
```

### Componentes Chave:
- **Simulador Fisiológico M/M/c/K (`app.py`):** Modela o tempo de serviço e fila por processo markoviano com capacidade de buffer finita $K$.
- **Gerador de Carga Contínua (`load_gen.py`):** Injeta transações sintéticas (Poisson puro ou pacing uniforme) sincronizado dinamicamente via WebSocket/HTTP.
- **Operador Kubernetes & CRDs (`k8s/` e `helm/`):** Implementa o reconciliador do Custom Resource Definition `ArkheStabilityBasin` para autoscaling preditivo antes do estouro de SLO/SLA.
- **Cockpit e Visualizador Reativo (`templates/index.html`, `static/`, `dashboard-angular/`):** Streaming a 20 FPS (50ms por tick) via canal WebSocket bidirecional.

---

## 2. Cenários de Caos e Degradação

O ambiente expõe endpoints administrativos em `/admin/chaos` para injeção controlada de vetores de degradação:

1. **Operação Nominal:** $\lambda = 120\text{ TPS}$, $W_s = 45\text{ ms}$, ocupação do pool em regime laminar (~10-15%).
2. **Drift Silencioso:** Latência do antifraude sobe para $255\text{ ms}$, ocupação sobe para ~68% com zero timeouts aparentes no monitor estático.
3. **Ruptura de Concorrência:** Latência sobe para $420\text{ ms}$, ultrapassando a capacidade do pool ($L > c=30$) gerando filas exponenciais.
4. **Degradação HSM:** Contenção de CPU por criptografia EMV ($+120\text{ ms}$).
5. **Flapping de Adquirente:** Queda transiente de 35% com retries em cascata.
6. **Jitter Assimétrico (P99 Outlier):** Cauda longa de latência ($> 1200\text{ ms}$).

---

## 3. Scripts de Teste e Validação

Os seguintes roteiros automatizados validam o comportamento do sistema sob carga:

- `run_test1_nominal_baseline.py`: Coleta 120 frames sob regime laminar e confirma $P95 < 150\text{ ms}$ e zero erros.
- `run_test2_silent_drift.py`: Demonstra a antecipação temporal do Sentinel sobre o monitor SRE tradicional durante drift silencioso.
- `run_test3_closed_loop_mitigation.py`: Comprova o fechamento de ciclo autônomo (expansão preditiva para 60 slots e fast-path de 12ms).
- `run_test4_time_machine_audit.py`: Reconstitui a linha do tempo do evento de falha com causalidade física auditável.

---

## 4. Como Executar Localmente

### Modo Direto (Python):
```bash
# Iniciar o servidor de telemetria
python -m uvicorn app:app --port 8080

# Em outro terminal, iniciar a carga contínua
python load_gen.py
```

### Modo Docker Compose:
```bash
docker compose up -d
```
Acesse a Torre de Controle em: `http://localhost:8080/`
Apresentação Executiva: `http://localhost:8080/presentation`
Laudo de Prova de Valor: `http://localhost:8080/pov`
