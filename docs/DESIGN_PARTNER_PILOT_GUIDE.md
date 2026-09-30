# 🛡️ ARKHÉ Design Partner Pilot Playbook (Guia de Implantação do Piloto)
### Resiliência Cibernética Autônoma em Modo Shadow para Ambientes Financeiros de Missão Crítica

---

## 1. Visão Geral do Programa de Piloto (Design Partner)

O **Programa de Piloto ARKHÉ** foi desenhado para instituições financeiras (adquirentes, bancos digitais, iniciadores de pagamento PIX e gateways) que necessitam de **resiliência preditiva sem assumir qualquer risco operacional em produção**.

* **Duração Recomendada:** 30 a 60 dias.
* **Modo de Operação Inicial:** **Shadow Mode (100% Passivo / Somente Leitura)**.
* **Impacto em Produção:** **ZERO.** O ARKHÉ recebe cópias de spans de telemetria via OpenTelemetry existente, calcula o Espaço de Fase de Lyapunov e registra a antecedência de incidentes sem realizar mutações de tráfego ou redimensionamento invasivo na primeira fase.

```mermaid
flowchart LR
    subgraph PartnerEnv["Ambiente do Parceiro (Produção / Staging)"]
        Workload[Payment / PIX Service] -->|Traces & Métricas| OTelCol[OpenTelemetry Collector]
        OTelCol -->|Pipeline Principal| APM[APM Legado: Datadog / Dynatrace]
        OTelCol -.->|Export OTLP HTTP (Shadow)| ArkheEngine[ARKHÉ Cybernetic Engine]
    end

    subgraph ArkhePlatform["Plataforma ARKHÉ (Namespace arkhe-system)"]
        ArkheEngine -->|Cálculo de Lyapunov em tempo real| Operator[ARKHÉ K8s Operator]
        Operator -->|Auditoria de Bacia de Estabilidade| Forensics[Flight Recorder BACEN / PCI]
        Operator -.->|Modo Shadow: Dry-Run Logging| Metrics[Prometheus Scraper / Metrics]
    end

    style PartnerEnv fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#f8fafc
    style ArkhePlatform fill:#0f172a,stroke:#8b5cf6,stroke-width:2px,color:#f8fafc
    style OTelCol fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#f8fafc
```

---

## 2. Requisitos de Infraestrutura

* **Cluster Kubernetes:** 1.26+ (EKS, GKE, AKS, OpenShift ou K3s).
* **Recursos Mínimos Recomendados:**
  * Engine: 1 Pod (0.5 CPU, 512Mi RAM).
  * Operator: 1 Pod (0.2 CPU, 256Mi RAM).
* **Rede:** Acesso interno no cluster entre o OTel Collector e o Service do ARKHÉ na porta `8080`.

---

## 3. Instalação em 3 Passos via Helm 3

### Passo 1: Instalação das CRDs e do Chart com Valores de Shadow Mode
```bash
# Cria o namespace e instala o ARKHÉ em Modo Shadow
helm install arkhe-pilot ./helm/arkhe-benchmark-lab \
  --namespace arkhe-system \
  --create-namespace \
  -f ./helm/arkhe-benchmark-lab/values-shadow.yaml
```

### Passo 2: Verificação do Pré-Voo e Saúde dos Componentes
Execute a ferramenta de diagnóstico automatizada:
```bash
python scripts/verify_pilot_health.py --url http://<ARKHE_SERVICE_IP_OU_HOST>:8080
```
*Saída Esperada:*
```
1. Verificando API de Telemetria e Healthcheck... [OK]
2. Validando Ingestão de Traces OTel... [OK]
3. Validando Exporter Prometheus... [OK]
4. Verificando Cockpit e Apresentação Executiva... [OK]
✓ SUCESSO: Todos os 4/4 testes de pré-voo foram aprovados!
```

### Passo 3: Configuração do OpenTelemetry Collector Existente
Adicione o exporter OTLP ao seu `otel-collector-config.yaml` para espelhar spans para o ARKHÉ:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
      http:

exporters:
  # Seu APM legado continua inalterado:
  datadog:
    api:
      key: ${DD_API_KEY}

  # Exportador seguro para o ARKHÉ em Modo Shadow:
  otlphttp/arkhe:
    endpoint: "http://arkhe-card-auth-lab-service.arkhe-system.svc.cluster.local:8080"
    encoding: json

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [datadog, otlphttp/arkhe] # Envio em paralelo
```

---

## 4. Calibração da Bacia de Estabilidade de Lyapunov (`ArkheStabilityBasin`)

No arquivo [`values-shadow.yaml`](file:///c:/Users/anonimo/OneDrive/Documentos/GitHub/arkhe-benchmark-lab/helm/arkhe-benchmark-lab/values-shadow.yaml), ajuste os parâmetros para a volumetria da sua instituição:

```yaml
stabilityBasin:
  name: "shadow-payment-pipeline"
  targetThroughputTps: 500.0          # Throughput nominal de pico
  maxRhoBasin: 0.65                   # Limite seguro de ocupação (65%)
  maxQueueWaitRatio: 0.30             # W_q / W_s máximo permitido
  criticalTimeToCollapseSeconds: 45   # Alerta emitido se colapso em < 45s
  predictiveHpa:
    dryRun: true                      # Garante que NENHUM pod será escalado em produção
  fastPathBypass:
    dryRun: true                      # Garante que rotas de tráfego NÃO sofrerão desvio
```

---

## 5. Critérios de Sucesso e Scorecard Semanal do Piloto

Durante os 30-60 dias do piloto, o ARKHÉ gerará automaticamente relatórios semanais auditáveis comparando a performance com os sistemas legados:

| Dimensão Avaliada | Métrica de Sucesso (KPI) | Como É Comprovado |
| :--- | :---: | :--- |
| **Antecedência Preditiva** | $T_{lead} \ge +30\text{ segundos}$ | O ARKHÉ emite alerta enquanto o APM tradicional permanece mudo. |
| **Precisão de Alerta** | Taxa de Falsos Positivos $< 1.0\%$ | Correlação estocástica de Lyapunov confirmada pós-análise. |
| **Auditoria Determinística** | $100\%$ de conformidade BACEN / PCI | Bundles de incidentes selados com hash SHA-256 e reproduzíveis bit-a-bit. |
| **Projeção de FinOps** | $25\% \text{ a } 35\%$ de economia | Simulação de desprovisionamento preditivo de pods ociosos sem quebra de SLA. |

---

## 6. Transição Segura: Do Shadow Mode para a Mitigação Ativa

Após a homologação de 30 dias com histórico comprovado de antecedência:
1. **Fase 1 (Semanas 1 a 4):** Shadow Mode Passivo (Dry-Run 100%).
2. **Fase 2 (Semana 5):** Habilitação de Mitigação Ativa em ambiente de **Staging / Homologação**.
3. **Fase 3 (Semana 6):** Habilitação em produção para tráfego **Canário (5% a 10%)**.
4. **Fase 4 (Produção Total):** Ativação completa do controle closed-loop com garantia contratual de SLA.

---

## 7. Contatos de Suporte Técnico & Engenharia
* **Squad de Resiliência ARKHÉ:** `architecture@arkhe.io`
* **Cockpit do Piloto:** `http://arkhe-shadow.internal.bank.com/ng/`
* **Pitch Deck Executivo Incorporado:** `http://arkhe-shadow.internal.bank.com/presentation`
