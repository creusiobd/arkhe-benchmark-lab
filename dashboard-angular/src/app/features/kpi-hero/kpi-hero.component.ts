import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TelemetryStore } from '../../core/state/telemetry.store';

@Component({
  selector: 'arkhe-kpi-hero',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="kpi-grid">
      <!-- 1. Score de Risco Instantâneo ARKHÉ -->
      <div class="kpi-card" [ngClass]="'border-' + store.sentinelLevel()">
        <div class="kpi-header">
          <span class="kpi-title">SCORE DE RISCO INSTANTÂNEO</span>
          <span class="status-badge" [ngClass]="'badge-' + store.sentinelLevel()">
            {{ store.stateLabel() }}
          </span>
        </div>
        <div class="kpi-metric" [ngClass]="'text-' + store.sentinelLevel()">
          {{ store.sentinelScore() | number:'1.1-1' }} <span class="kpi-unit">%</span>
        </div>
        <div class="progress-bar-bg">
          <div 
            class="progress-bar-fill" 
            [style.width.%]="store.sentinelScore()"
            [ngClass]="'fill-' + store.sentinelLevel()">
          </div>
        </div>
        <div class="kpi-sub">
          <span>Antecedência: <strong>{{ store.leadTimeDisplay() }}</strong></span>
          @if (store.isTrajectoryAlert()) {
            <span style="color: #f59e0b;">Sinal Trajetória: <strong>Δ +{{ store.trajectorySignal()?.delta_abs_pp }} p.p.</strong></span>
          } @else {
            <span>Razão Wq/Ws: <strong>{{ store.wqWsRatio() | number:'1.2-2' }}</strong></span>
          }
        </div>
      </div>

      <!-- 2. Ocupação do Pool Antifraude -->
      <div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-title">OCUPAÇÃO DO POOL ANTIFRAUDE</span>
          <span class="status-badge" [ngClass]="store.poolUtilizationPct() > 80 ? 'badge-critical' : (store.poolUtilizationPct() > 50 ? 'badge-warning' : 'badge-healthy')">
            {{ store.poolInUse() }} / {{ store.poolCapacity() }} SLOTS
          </span>
        </div>
        <div class="kpi-metric" [style.color]="store.poolUtilizationPct() > 80 ? '#ef4444' : (store.poolUtilizationPct() > 50 ? '#f59e0b' : '#38bdf8')">
          {{ store.poolUtilizationPct() }}%
        </div>
        <div class="progress-bar-bg">
          <div 
            class="progress-bar-fill" 
            [style.width.%]="store.poolUtilizationPct()"
            [style.background]="store.poolUtilizationPct() > 80 ? '#ef4444' : (store.poolUtilizationPct() > 50 ? '#f59e0b' : '#38bdf8')">
          </div>
        </div>
        <div class="kpi-sub">
          <span>HPA: <strong>{{ store.poolCapacity() }} slots</strong></span>
          <span>Fast-Path: <strong>{{ store.mitigation()?.fast_path_active ? 'ATIVO' : 'STANDBY' }}</strong></span>
        </div>
      </div>

      <!-- 3. Tráfego Simultâneo de Cartões -->
      <div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-title">TRÁFEGO CONCORRENTE</span>
          <span class="status-badge badge-nominal">120 TPS</span>
        </div>
        <div class="kpi-metric text-emerald">
          {{ store.tpsDisplay() }}
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill fill-emerald" style="width: 85%;"></div>
        </div>
        <div class="kpi-sub">
          <span>Tentativas: <strong>{{ store.telemetry()?.traffic?.attempts_total ?? 0 }}</strong></span>
          <span>Amplif. Retries: <strong>{{ store.retryAmplification() | number:'1.2-2' }}x</strong></span>
        </div>
      </div>

      <!-- 4. Latência P95 e Concorrência -->
      <div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-title">LATÊNCIA P95 & FILA</span>
          <span class="status-badge" [ngClass]="store.p95Ms() > 1000 ? 'badge-critical' : (store.p95Ms() > 300 ? 'badge-warning' : 'badge-healthy')">
            {{ store.p95Ms() > 1500 ? 'VIOLAÇÃO SRE' : 'CONFORME' }}
          </span>
        </div>
        <div class="kpi-metric" [style.color]="store.p95Ms() > 1000 ? '#ef4444' : (store.p95Ms() > 300 ? '#f59e0b' : '#a855f7')">
          {{ store.p95Ms() | number:'1.1-1' }} <span class="kpi-unit">ms</span>
        </div>
        <div class="progress-bar-bg">
          <div 
            class="progress-bar-fill" 
            [style.width.%]="mathMin(100, (store.p95Ms() / 1500) * 100)"
            [style.background]="store.p95Ms() > 1000 ? '#ef4444' : (store.p95Ms() > 300 ? '#f59e0b' : '#a855f7')">
          </div>
        </div>
        <div class="kpi-sub">
          <span>P50: <strong>{{ store.p50Ms() | number:'1.0-0' }}ms</strong></span>
          <span>P99: <strong>{{ store.p99Ms() | number:'1.0-0' }}ms</strong></span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
      margin-bottom: 20px;
    }
    .kpi-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 16px;
      backdrop-filter: blur(8px);
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover {
      border-color: rgba(56, 139, 253, 0.4);
    }
    .kpi-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .kpi-title {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-secondary);
      letter-spacing: 0.6px;
    }
    .kpi-metric {
      font-size: 28px;
      font-weight: 800;
      font-family: var(--font-mono);
      line-height: 1.1;
      margin: 4px 0 10px 0;
    }
    .kpi-unit {
      font-size: 14px;
      font-weight: 500;
      color: var(--text-muted);
    }
    .progress-bar-bg {
      background: rgba(255, 255, 255, 0.06);
      height: 4px;
      border-radius: 2px;
      overflow: hidden;
      margin-bottom: 10px;
    }
    .progress-bar-fill {
      height: 100%;
      transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .kpi-sub {
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: var(--text-muted);
      border-top: 1px solid rgba(255, 255, 255, 0.04);
      padding-top: 8px;
    }
    .kpi-sub strong {
      color: var(--text-primary);
      font-family: var(--font-mono);
    }

    /* Cores Semânticas */
    .text-healthy { color: var(--accent-emerald); }
    .text-warning { color: var(--accent-amber); }
    .text-critical { color: var(--accent-crimson); }
    .text-emerald { color: var(--accent-emerald); }

    .fill-healthy { background: var(--accent-emerald); }
    .fill-warning { background: var(--accent-amber); }
    .fill-critical { background: var(--accent-crimson); }
    .fill-emerald { background: var(--accent-emerald); }

    .border-healthy { border-top: 2px solid var(--accent-emerald); }
    .border-warning { border-top: 2px solid var(--accent-amber); }
    .border-critical { border-top: 2px solid var(--accent-crimson); }

    .status-badge {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 4px;
      letter-spacing: 0.4px;
    }
    .badge-healthy, .badge-nominal {
      background: rgba(16, 185, 129, 0.15);
      color: var(--accent-emerald);
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-warning {
      background: rgba(245, 158, 11, 0.15);
      color: var(--accent-amber);
      border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .badge-critical {
      background: rgba(239, 68, 68, 0.15);
      color: var(--accent-crimson);
      border: 1px solid rgba(239, 68, 68, 0.3);
    }
  `]
})
export class KpiHeroComponent {
  public store = inject(TelemetryStore);

  public mathMin(a: number, b: number): number {
    return Math.min(a, b);
  }
}
