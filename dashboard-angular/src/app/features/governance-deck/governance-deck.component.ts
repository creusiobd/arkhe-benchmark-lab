import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TelemetryStore } from '../../core/state/telemetry.store';

@Component({
  selector: 'arkhe-governance-deck',
  standalone: true,
  imports: [CommonModule],
  template: `
    <!-- 1. Banner de Antecedência Operacional -->
    <div class="lead-banner">
      <div class="lead-info">
        <div class="lead-title">
          <span class="lead-icon">⏱️</span>
          ANTECEDÊNCIA OPERACIONAL DO ARKHÉ SENTINEL SOBRE O ALARME SRE CLÁSSICO
        </div>
        <div class="lead-desc">
          @if (store.leadTimeStatus() === 'CONSOLIDATED') {
            Antecedência confirmada de <strong>{{ store.leadTimeSeconds() }}s</strong> em relação ao alarme Prometheus/Datadog.
          } @else if (store.leadTimeStatus() === 'OBSERVING_PENDING_BASELINE') {
            <span style="color: #f59e0b;">Detecção antecipada ativa.</span> Monitor convencional SRE ainda mudo (antecipação em curso, aguardando baseline).
          } @else {
            {{ store.leadTimeDescription() }}
          }
        </div>
      </div>
      <div class="lead-metric">
        <div class="lead-val">{{ store.leadTimeDisplay() }}</div>
        <span class="lead-unit">
          @if (store.leadTimeStatus() === 'CONSOLIDATED') {
            TEMPO DE ANTECEDÊNCIA GANHO
          } @else if (store.leadTimeStatus() === 'OBSERVING_PENDING_BASELINE') {
            EM OBSERVAÇÃO PREVENTIVA
          } @else {
            STATUS DE ANTECEDÊNCIA
          }
        </span>
      </div>
    </div>

    <!-- 2. Grid dos 2 Pilares: Agente Atuador Closed-Loop & Governança SRE -->
    <div class="governance-grid">
      <!-- Agente Atuador Autônomo -->
      <div class="gov-card mit-card">
        <div class="gov-header">
          <div class="gov-title">
            <span>⚡ AGENTE ATUADOR AUTÔNOMO (CLOSED-LOOP)</span>
            <span class="gov-sub">Atuação preditiva preventiva no minuto zero da anomalia</span>
          </div>
          <span 
            class="mit-badge" 
            [ngClass]="store.isMitigationActive() ? 'mit-active' : 'mit-standby'">
            {{ store.isMitigationActive() ? 'ATIVO (AUTO-CURA)' : 'STANDBY (ESCUTA)' }}
          </span>
        </div>

        <div class="stats-row">
          <div class="stat-box">
            <span class="stat-label">Falhas Evitadas</span>
            <span class="stat-value text-emerald">
              {{ store.mitigation()?.prevented_failures ?? 0 }}
            </span>
            <span class="stat-desc">Zero 503/504 em cascata</span>
          </div>
          <div class="stat-box">
            <span class="stat-label">Downtime Evitado</span>
            <span class="stat-value text-blue">
              {{ store.mitigation()?.downtime_avoided_min ?? 0 | number:'1.1-1' }}m
            </span>
            <span class="stat-desc">Indisponibilidade neutralizada</span>
          </div>
          <div class="stat-box">
            <span class="stat-label">Capacidade Adaptativa</span>
            <span class="stat-value text-purple">
              {{ store.mitigation()?.pool_capacity ?? 30 }}
            </span>
            <span class="stat-desc">Slots HPA do Semáforo</span>
          </div>
        </div>
      </div>

      <!-- Governança SRE & Error Budget -->
      <div class="gov-card sre-card">
        <div class="gov-header">
          <div class="gov-title">
            <span>🎯 GOVERNANÇA SRE: SLI / SLA & ERROR BUDGET</span>
            <span class="gov-sub">Target: 99.90% Disponibilidade • P95 &lt; 1.500 ms</span>
          </div>
          <span class="burn-badge" [ngClass]="'burn-' + store.burnRateStatus().toLowerCase()">
            BURN RATE: {{ store.burnRate() | number:'1.2-2' }}x
          </span>
        </div>

        <div class="stats-row">
          <div class="stat-box">
            <span class="stat-label">SLI Disponibilidade</span>
            <span class="stat-value" [style.color]="(store.sre()?.current_sli_availability_pct ?? 100) >= 99.9 ? '#10b981' : '#ef4444'">
              {{ store.sre()?.current_sli_availability_pct ?? 100 | number:'1.2-2' }}%
            </span>
            <span class="stat-desc">SLA Contratual: 99.90%</span>
          </div>
          <div class="stat-box">
            <span class="stat-label">Error Budget Restante</span>
            <span class="stat-value" [style.color]="(store.sre()?.error_budget_remaining_pct ?? 100) > 20 ? '#10b981' : '#ef4444'">
              {{ store.sre()?.error_budget_remaining_pct ?? 100 | number:'1.1-1' }}%
            </span>
            <span class="stat-desc">Margem para falhas técnicas</span>
          </div>
          <div class="stat-box">
            <span class="stat-label">Alarmes Clássicos</span>
            <span class="stat-value" [style.color]="store.sre()?.traditional_alert_triggered ? '#ef4444' : '#64748b'">
              {{ store.sre()?.traditional_alert_triggered ? 'DISPARADO' : 'SILÊNCIO' }}
            </span>
            <span class="stat-desc">Prometheus / Datadog</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .lead-banner {
      background: linear-gradient(90deg, rgba(16, 24, 40, 0.9) 0%, rgba(30, 58, 138, 0.4) 100%);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 8px;
      padding: 14px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    .lead-title {
      font-size: 13px;
      font-weight: 700;
      color: #93c5fd;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .lead-desc {
      font-size: 12px;
      color: #cbd5e1;
      margin-top: 4px;
    }
    .lead-metric {
      text-align: right;
    }
    .lead-val {
      font-size: 32px;
      font-weight: 900;
      font-family: var(--font-mono);
      color: #38bdf8;
      text-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
      line-height: 1;
    }
    .lead-unit {
      font-size: 10px;
      font-weight: 700;
      color: #93c5fd;
      letter-spacing: 0.5px;
    }

    .governance-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-bottom: 20px;
    }
    @media (max-width: 900px) {
      .governance-grid {
        grid-template-columns: 1fr;
      }
    }

    .gov-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 16px;
    }
    .mit-card {
      border-left: 3px solid #38bdf8;
    }
    .sre-card {
      border-left: 3px solid #10b981;
    }

    .gov-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 14px;
    }
    .gov-title {
      display: flex;
      flex-direction: column;
      font-size: 13px;
      font-weight: 800;
      color: var(--text-primary);
    }
    .gov-sub {
      font-size: 11px;
      font-weight: 400;
      color: var(--text-muted);
      margin-top: 2px;
    }

    .mit-badge {
      font-size: 10px;
      font-weight: 800;
      padding: 3px 8px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }
    .mit-standby {
      background: rgba(148, 163, 184, 0.15);
      color: #94a3b8;
      border: 1px solid #475569;
    }
    .mit-active {
      background: rgba(16, 185, 129, 0.2);
      color: #10b981;
      border: 1px solid #10b981;
      box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
    }

    .burn-badge {
      font-size: 10px;
      font-weight: 800;
      padding: 3px 8px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }
    .burn-normal {
      background: rgba(16, 185, 129, 0.2);
      color: #10b981;
    }
    .burn-warning {
      background: rgba(245, 158, 11, 0.2);
      color: #f59e0b;
    }
    .burn-critical {
      background: rgba(239, 68, 68, 0.2);
      color: #ef4444;
      animation: pulse 1.5s infinite;
    }

    .stats-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
    }
    .stat-box {
      background: rgba(0, 0, 0, 0.25);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 6px;
      padding: 10px;
      display: flex;
      flex-direction: column;
    }
    .stat-label {
      font-size: 10px;
      text-transform: uppercase;
      color: var(--text-muted);
      font-weight: 600;
    }
    .stat-value {
      font-size: 20px;
      font-weight: 800;
      font-family: var(--font-mono);
      margin: 4px 0;
    }
    .stat-desc {
      font-size: 10px;
      color: var(--text-secondary);
    }

    .text-emerald { color: #10b981; }
    .text-blue { color: #38bdf8; }
    .text-purple { color: #a855f7; }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
  `]
})
export class GovernanceDeckComponent {
  public store = inject(TelemetryStore);
}
