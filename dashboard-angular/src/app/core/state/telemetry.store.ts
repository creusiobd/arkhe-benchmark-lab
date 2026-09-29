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

  public readonly leadTimeMinutes = computed(() => 
    this.sentinel()?.lead_time_minutes ?? 0
  );

  public readonly leadTimeSeconds = computed(() => 
    this.sentinel()?.lead_time_seconds ?? 0
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

  public resetSimulation(): void {
    this.api.resetSimulation().subscribe();
  }
}
