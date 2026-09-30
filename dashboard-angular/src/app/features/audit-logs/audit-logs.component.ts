import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TelemetryStore } from '../../core/state/telemetry.store';

@Component({
  selector: 'arkhe-audit-logs',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="logs-deck">
      <div class="logs-header">
        <span class="logs-title">AUDITORIA DE EVENTOS DE MUTAÇÃO & ATUAÇÃO CLOSED-LOOP</span>
        <span class="logs-count">{{ store.eventLogs().length }} eventos</span>
      </div>
      <div class="logs-terminal">
        @for (log of store.eventLogs(); track log.timestamp + log.message) {
          <div class="log-line" [ngClass]="'log-' + log.level">
            <span class="log-time">[{{ log.timestamp }}]</span>
            <span class="log-msg">{{ log.message }}</span>
          </div>
        } @empty {
          <div class="log-line log-info">
            <span class="log-time">[00:00:00]</span>
            <span class="log-msg">Ambiente inicializado e escutando telemetria a 20 FPS...</span>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .logs-deck {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 20px;
    }
    .logs-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .logs-title {
      font-size: 11px;
      font-weight: 800;
      color: var(--text-secondary);
      letter-spacing: 0.5px;
    }
    .logs-count {
      font-size: 10px;
      font-family: var(--font-mono);
      color: var(--text-muted);
    }
    .logs-terminal {
      background: #06080d;
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 6px;
      padding: 12px;
      max-height: 180px;
      overflow-y: auto;
      font-family: var(--font-mono);
      font-size: 11px;
      line-height: 1.6;
    }
    .log-line {
      display: flex;
      gap: 10px;
      margin-bottom: 4px;
    }
    .log-time {
      color: var(--text-muted);
      white-space: nowrap;
    }
    .log-info { color: #94a3b8; }
    .log-success { color: #10b981; }
    .log-warning { color: #f59e0b; }
    .log-danger { color: #ef4444; }
  `]
})
export class AuditLogsComponent {
  public store = inject(TelemetryStore);
}
