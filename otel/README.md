# 🔭 ARKHÉ OpenTelemetry (OTel) Native Connector & Exporter

O **ARKHÉ OpenTelemetry Connector** viabiliza a adoção corporativa com **Zero-Touch Instrumentation**: microsserviços já instrumentados com OpenTelemetry (Java Agent, Go SDK, Python SDK, .NET) enviam spans e métricas padrão para o ARKHÉ sem que nenhuma linha de código de negócio precise ser alterada.

---

## 🏗️ Arquitetura do Conector OTel

```mermaid
flowchart LR
    subgraph Microservices["Microsserviços de Negócio (Java / Go / Node / Rust)"]
        App1["Payment Gateway<br/>(OTel Auto-Agent)"]
        App2["Antifraud Service<br/>(OTel SDK)"]
        App3["Core Ledger<br/>(OTel SDK)"]
    end

    subgraph OTelCollector["OpenTelemetry Collector Corporativo"]
        Collector["OTel Collector Contrib<br/>(OTLP Receiver)"]
    end

    subgraph ArkhePlatform["ARKHÉ Cybernetic Platform"]
        Receiver["OTLP Ingestion Endpoints<br/>POST /v1/traces<br/>POST /v1/metrics"]
        Adapter["Lyapunov OTel Adapter<br/>• Infere ρ, Wq, Ws, TTC<br/>• Detecta deriva de fase"]
        Kernel["Sentinel AI & Lyapunov Engine"]
        Prom["Prometheus Scraper Endpoint<br/>GET /metrics"]
        Exporter["OTel Enriched Exporter<br/>(Envia métricas upstream)"]

        Receiver --> Adapter
        Adapter --> Kernel
        Kernel --> Prom
        Kernel --> Exporter
    end

    subgraph UpstreamAPM["APMs Corporativos Existentes"]
        Grafana["Prometheus / Grafana"]
        Datadog["Datadog / Dynatrace"]
    end

    App1 --> Collector
    App2 --> Collector
    App3 --> Collector

    Collector -->|OTLP / HTTP| Receiver
    Prom -.->|Scrape /metrics| Grafana
    Exporter -.->|OTLP Metrics| Datadog

    style Microservices fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#f8fafc
    style OTelCollector fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc
    style ArkhePlatform fill:#0f172a,stroke:#8b5cf6,stroke-width:2px,color:#f8fafc
    style UpstreamAPM fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#f8fafc
```

---

## 🔌 Endpoints Disponíveis

| Endpoint | Método | Protocolo | Descrição |
| :--- | :---: | :---: | :--- |
| `/v1/traces` | `POST` | OTLP/HTTP JSON | Recebe lotes de spans padrão OpenTelemetry (`resourceSpans`). |
| `/v1/metrics` | `POST` | OTLP/HTTP JSON | Ingestor de métricas OTLP de infraestrutura. |
| `/metrics` | `GET` | OpenMetrics / Prometheus | Raspagem padrão de métricas enriquecidas com o score ARKHÉ. |
| `/v1/arkhe/metrics` | `GET` | OpenMetrics / Prometheus | Alias compatível para scraping customizado. |

---

## 📊 Métricas Enriquecidas Exportadas pelo ARKHÉ

Quando o Prometheus ou o Datadog Agent raspa o endpoint `/metrics`, o ARKHÉ expõe as variáveis cibernéticas de estabilidade:

| Métrica Prometheus | Tipo | Significado no Negócio |
| :--- | :---: | :--- |
| `arkhe_sentinel_risk_score` | `Gauge` | Score de risco preditivo da IA ARKHÉ ($0$ a $100$). |
| `arkhe_lyapunov_pool_utilization_rho` | `Gauge` | Taxa de ocupação de recursos críticos ($\rho \in [0, 1]$). |
| `arkhe_lyapunov_queue_wait_service_ratio` | `Gauge` | Razão entre tempo de espera e serviço ($W_q / W_s$). |
| `arkhe_lyapunov_d_rho_dt_per_min` | `Gauge` | Velocidade de saturação de fase ($\frac{d\rho}{dt}$ por minuto). |
| `arkhe_predicted_time_to_collapse_seconds` | `Gauge` | Projeção do Tempo até o Colapso ($TTC$). |
| `arkhe_closed_loop_mitigation_active` | `Gauge` | Flag ($0$ ou $1$) indicando auto-mitigação ativa. |
| `arkhe_closed_loop_fast_path_active` | `Gauge` | Flag ($0$ ou $1$) indicando desvio para cache L2. |
| `arkhe_sre_sli_availability_percent` | `Gauge` | SLI de disponibilidade real segundo o Google SRE framework. |
| `arkhe_sre_error_budget_remaining_percent` | `Gauge` | Saldo restante do Error Budget ($100\%$ a $0\%$). |
| `arkhe_sre_burn_rate` | `Gauge` | Velocidade de consumo do Error Budget ($0.0\times$ a $50.0\times$). |

---

## 🛠️ Configuração do OpenTelemetry Collector

Para encaminhar spans do seu OTel Collector corporativo para o ARKHÉ, basta adicionar o exporter OTLP no `otel-collector-config.yaml`:

```yaml
exporters:
  otlphttp/arkhe:
    endpoint: "http://arkhe-card-auth-lab-service:8080"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlphttp/arkhe, otlp/datadog]
```

---

## 🧪 Validação dos Testes

Execução da suite de testes automatizados do conector OTel:
```bash
python -m unittest tests/test_otel_connector.py
```
Resultado:
```
----------------------------------------------------------------------
Ran 5 tests in 0.143s

OK
```
