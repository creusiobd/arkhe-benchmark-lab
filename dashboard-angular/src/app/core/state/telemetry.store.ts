import { Injectable, inject, computed, effect } from '@angular/core';
import { WebsocketTelemetryService } from '../services/websocket-telemetry.service';
import { ChaosApiService } from '../services/chaos-api.service';
import { TimeMachineService } from '../services/time-machine.service';

@Injectable({
  providedIn: 'root'
})
export class TelemetryStore {
  private ws = inject(WebsocketTelemetryService);
  private api = inject(ChaosApiService);
  public timeMachine = inject(TimeMachineService);

  constructor() {
    effect(() => {
      const payload = this.ws.latestPayload();
      if (payload) {
        this.timeMachine.pushSnapshot(payload);
      }
    });
  }

  // Payload dinâmico: se estiver Ao Vivo lê o stream a 20 FPS, se estiver em Rebobinagem lê o snapshot do Scrubber!
  public readonly raw = computed(() => {
    if (this.timeMachine.isLive()) {
      return this.ws.latestPayload();
    }
    return this.timeMachine.currentSnapshot();
  });

  public readonly connectionStatus = this.ws.connectionStatus;
  public readonly fps = this.ws.fpsCount;
  public readonly isConnected = this.ws.isConnected;

  // Sub-estados reativos computados com Signals
  public readonly scenario = computed(() => this.raw()?.scenario);
  public readonly telemetry = computed(() => this.raw()?.telemetry);
  public readonly sentinel = computed(() => this.raw()?.sentinel);
  public readonly sre = computed(() => this.raw()?.sre_governance);
  public readonly mitigation = computed(() => this.raw()?.mitigation);
  public readonly topologyNodes = computed(() => this.raw()?.topology?.nodes || []);
  public readonly projection = computed(() => this.raw()?.projection);
  public readonly recentJourneys = computed(() => this.raw()?.recent_journeys || []);
  public readonly eventLogs = computed(() => this.raw()?.event_logs || []);
  public readonly loadConfig = computed(() => this.raw()?.load_config);
  public readonly targetTps = computed(() => this.loadConfig()?.target_tps ?? 120);
  public readonly isStochasticMode = computed(() => this.loadConfig()?.stochastic_mode ?? true);
  public readonly modeLabel = computed(() => this.loadConfig()?.mode_label ?? 'SIMULAÇÃO ESTOCÁSTICA DE ALTA FIDELIDADE (M/M/c/K)');
  public readonly mmckMetrics = computed(() => this.loadConfig()?.mmck_metrics);

  // KPIs de Alto Nível Computados
  public readonly tpsDisplay = computed(() => {
    const uniques = this.telemetry()?.traffic?.unique_transactions_total ?? 0;
    return `${uniques} txs`;
  });

  public readonly p50Ms = computed(() => this.telemetry()?.latency_ms?.p50 ?? 0);
  public readonly p95Ms = computed(() => this.telemetry()?.latency_ms?.p95 ?? 0);
  public readonly p99Ms = computed(() => this.telemetry()?.latency_ms?.p99 ?? 0);

  public readonly poolUtilizationRatio = computed(() => 
    this.telemetry()?.resources?.antifraud_pool_utilization_ratio ?? 0
  );

  public readonly poolUtilizationPct = computed(() => 
    Math.round(this.poolUtilizationRatio() * 100)
  );

  public readonly poolCapacity = computed(() => 
    this.telemetry()?.resources?.antifraud_pool_capacity ?? 30
  );

  public readonly poolInUse = computed(() => 
    this.telemetry()?.resources?.antifraud_pool_in_use ?? 0
  );

  public readonly wqWsRatio = computed(() => 
    this.telemetry()?.queueing?.wq_ws_ratio ?? 0
  );

  public readonly retryAmplification = computed(() => 
    this.telemetry()?.traffic?.retry_amplification_ratio ?? 1.0
  );

  public readonly sentinelScore = computed(() => 
    this.sentinel()?.score ?? 0
  );

  public readonly sentinelLevel = computed(() => 
    this.sentinel()?.level ?? 'healthy'
  );

  public readonly riskState = computed(() => 
    this.sentinel()?.risk_state ?? (this.sentinelScore() >= 75 ? 'critical' : (this.sentinelScore() >= 45 ? 'early_warning' : 'nominal'))
  );

  public readonly stateLabel = computed(() => 
    this.sentinel()?.state_label ?? (this.sentinelScore() >= 75 ? 'CRÍTICO' : (this.sentinelScore() >= 45 ? 'ALERTA PRECOCE' : 'NOMINAL'))
  );

  public readonly leadTimeMinutes = computed(() => 
    this.sentinel()?.lead_time_minutes ?? null
  );

  public readonly leadTimeSeconds = computed(() => 
    this.sentinel()?.lead_time_seconds ?? null
  );

  public readonly leadTimeStatus = computed(() => 
    this.sentinel()?.lead_time_status ?? 'NOT_APPLICABLE'
  );

  public readonly leadTimeDisplay = computed(() => 
    this.sentinel()?.lead_time_display ?? (this.leadTimeSeconds() !== null ? `+${this.leadTimeSeconds()!.toFixed(1)}s` : 'N/D')
  );

  public readonly leadTimeDescription = computed(() => 
    this.sentinel()?.lead_time_description ?? 'Regime nominal. Nenhum evento de anomalia ativo.'
  );

  public readonly trajectorySignal = computed(() => 
    this.sentinel()?.trajectory_signal
  );

  public readonly isTrajectoryAlert = computed(() => 
    this.sentinel()?.trajectory_signal?.active ?? false
  );

  public readonly burnRate = computed(() => 
    this.sre()?.burn_rate ?? 0
  );

  public readonly burnRateStatus = computed(() => 
    this.sre()?.burn_rate_status ?? 'NORMAL (0.0x)'
  );

  public readonly isMitigationActive = computed(() => 
    this.mitigation()?.active ?? false
  );

  public readonly isMitigationEnabled = computed(() => 
    this.mitigation()?.enabled ?? false
  );

  public readonly timeToCollapseDisplay = computed(() => 
    this.projection()?.time_to_collapse_display ?? 'ESTÁVEL / INFINITO (∞)'
  );

  public readonly collapseStatus = computed(() => 
    this.projection()?.collapse_status ?? 'HEALTHY'
  );

  // Ações do Operador
  public triggerScenario(name: string): void {
    // Tenta via WebSocket para resposta ultrarrápida, com fallback REST
    if (this.isConnected()) {
      this.ws.triggerScenario(name);
    } else {
      this.api.setScenario(name).subscribe();
    }
  }

  public toggleMitigation(): void {
    if (this.isConnected()) {
      this.ws.toggleMitigation();
    } else {
      this.api.toggleMitigation().subscribe();
    }
  }

  public setTps(tps: number): void {
    if (this.isConnected()) {
      this.ws.setTps(tps);
    } else {
      this.api.setTps(tps).subscribe();
    }
  }

  public adjustTps(delta: number): void {
    if (this.isConnected()) {
      this.ws.adjustTps(delta);
    } else {
      this.api.adjustTps(delta).subscribe();
    }
  }

  public toggleStochasticMode(): void {
    if (this.isConnected()) {
      this.ws.toggleStochastic();
    } else {
      this.api.toggleStochastic().subscribe();
    }
  }

  public resetSimulation(): void {
    this.api.resetSimulation().subscribe();
  }
}
