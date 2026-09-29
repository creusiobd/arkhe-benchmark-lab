import { 
  Component, 
  ElementRef, 
  ViewChild, 
  AfterViewInit, 
  OnDestroy, 
  inject, 
  effect 
} from '@angular/core';
import { CommonModule } from '@angular/common';
import Chart from 'chart.js/auto';
import { TelemetryStore } from '../../core/state/telemetry.store';
import { ProjectionState } from '../../core/models/telemetry.model';

@Component({
  selector: 'arkhe-horizon-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="horizon-deck">
      <div class="horizon-header">
        <div>
          <div class="horizon-title">
            <span>📈 VISIBILIDADE DA TRAJETÓRIA ANTECIPADA: HORIZONTE DE 5 MINUTOS COM CONE DE INCERTEZA (95%)</span>
            <span class="status-badge" [ngClass]="'badge-' + (store.projection()?.collapse_status?.toLowerCase() || 'healthy')">
              {{ getBadgeText() }}
            </span>
          </div>
          <div class="horizon-subtitle">
            Modelagem estocástica projetando saturação de Little, cone de incerteza a 95% e impacto de auto-cura
          </div>
        </div>

        <div class="horizon-chips">
          <div class="chip">
            <span class="chip-label">Ocupação (ρ):</span>
            <span class="chip-val text-blue">
              {{ ((store.projection()?.current_rho ?? 0) * 100) | number:'1.1-1' }}%
            </span>
          </div>
          <div class="chip">
            <span class="chip-label">Velocidade (dρ/dt):</span>
            <span class="chip-val" [style.color]="(store.projection()?.d_rho_dt_per_min ?? 0) > 0.05 ? '#ef4444' : '#10b981'">
              {{ (store.projection()?.d_rho_dt_per_min ?? 0) > 0 ? '+' : '' }}{{ store.projection()?.d_rho_dt_per_min ?? 0 | number:'1.2-2' }}/min
            </span>
          </div>
          <div class="chip">
            <span class="chip-label">Tempo até Colapso (TTC):</span>
            <span class="chip-val" [style.color]="store.projection()?.collapse_status === 'CRITICAL' ? '#ef4444' : (store.projection()?.collapse_status === 'WARNING' ? '#f59e0b' : '#10b981')">
              {{ store.projection()?.time_to_collapse_display || 'ESTÁVEL / INFINITO (∞)' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Canvas do Gráfico Chart.js 4 -->
      <div class="chart-container">
        <canvas #horizonCanvas></canvas>
      </div>

      <!-- Legenda Científica -->
      <div class="horizon-legend">
        <span class="leg-item"><span class="dot-solid dot-blue"></span> Histórico Observado (-20s)</span>
        <span class="leg-item"><span class="dot-box dot-cone"></span> Cone Incerteza 95% (Limiares de Little)</span>
        <span class="leg-item"><span class="line-dashed line-red"></span> Projeção Sem Mitigação</span>
        <span class="leg-item"><span class="line-dashed line-green"></span> Projeção Sob Auto-Cura ARKHÉ</span>
        <span class="leg-item"><span class="dot-solid dot-yellow"></span> Limite Bacia Estável (50%)</span>
        <span class="leg-item"><span class="dot-solid dot-red"></span> Limiar Crítico de Ruptura (80%)</span>
      </div>
    </div>
  `,
  styles: [`
    .horizon-deck {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 20px;
    }
    .horizon-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .horizon-title {
      font-size: 13px;
      font-weight: 800;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .horizon-subtitle {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .horizon-chips {
      display: flex;
      gap: 10px;
    }
    .chip {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      padding: 4px 10px;
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
    }
    .chip-label {
      color: var(--text-muted);
    }
    .chip-val {
      font-family: var(--font-mono);
      font-weight: 700;
    }

    .chart-container {
      position: relative;
      height: 240px;
      width: 100%;
      margin-bottom: 12px;
    }

    .horizon-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 11px;
      color: var(--text-secondary);
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      padding-top: 10px;
    }
    .leg-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .dot-solid {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    .dot-box {
      width: 12px;
      height: 8px;
      border-radius: 2px;
    }
    .dot-blue { background: #38bdf8; }
    .dot-cone { background: rgba(239, 68, 68, 0.4); }
    .dot-yellow { background: #f59e0b; }
    .dot-red { background: #ef4444; }

    .line-dashed {
      width: 16px;
      height: 0;
      border-top: 2px dashed;
    }
    .line-red { border-color: #f43f5e; }
    .line-green { border-color: #22c55e; }

    .text-blue { color: #38bdf8; }

    .status-badge {
      font-size: 10px;
      font-weight: 800;
      padding: 2px 7px;
      border-radius: 4px;
    }
    .badge-healthy {
      background: rgba(16, 185, 129, 0.15);
      color: #10b981;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-warning {
      background: rgba(245, 158, 11, 0.15);
      color: #f59e0b;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .badge-critical {
      background: rgba(239, 68, 68, 0.2);
      color: #ef4444;
      border: 1px solid rgba(239, 68, 68, 0.4);
      animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
  `]
})
export class HorizonChartComponent implements AfterViewInit, OnDestroy {
  @ViewChild('horizonCanvas') horizonCanvasRef!: ElementRef<HTMLCanvasElement>;

  public store = inject(TelemetryStore);
  private chart?: Chart;

  constructor() {
    // Reage imediatamente a cada novo frame do WebSocket a 20 FPS
    effect(() => {
      const proj = this.store.projection();
      if (proj && this.chart) {
        this.updateChartData(proj);
      }
    });
  }

  ngAfterViewInit(): void {
    this.initChart();
  }

  ngOnDestroy(): void {
    if (this.chart) {
      this.chart.destroy();
    }
  }

  public getBadgeText(): string {
    const status = this.store.projection()?.collapse_status;
    if (status === 'CRITICAL') return 'RUPTURA IMINENTE';
    if (status === 'WARNING') return 'DRIFT DE CONCORRÊNCIA';
    return 'BACIA ESTÁVEL';
  }

  private initChart(): void {
    const canvas = this.horizonCanvasRef.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const horizonLabels = [
      '-20s', '-15s', '-10s', '-5s', 'Agora', 
      '+30s', '+1.0m', '+1.5m', '+2.0m', '+3.0m', '+4.0m', '+5.0m'
    ];

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: horizonLabels,
        datasets: [
          // 0: Cone Superior 95%
          {
            label: 'Limite Superior (95%)',
            data: Array(12).fill(null),
            borderColor: 'transparent',
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            fill: '+1',
            pointRadius: 0,
            tension: 0.25
          },
          // 1: Cone Inferior 95%
          {
            label: 'Limite Inferior (95%)',
            data: Array(12).fill(null),
            borderColor: 'transparent',
            backgroundColor: 'transparent',
            fill: false,
            pointRadius: 0,
            tension: 0.25
          },
          // 2: Histórico Observado
          {
            label: 'Histórico Observado',
            data: Array(12).fill(null),
            borderColor: '#38bdf8',
            backgroundColor: '#38bdf8',
            borderWidth: 2.5,
            pointRadius: 3,
            pointHoverRadius: 5,
            tension: 0.2
          },
          // 3: Projeção Não Mitigada
          {
            label: 'Projeção (Sem Mitigação)',
            data: Array(12).fill(null),
            borderColor: '#f43f5e',
            borderDash: [5, 4],
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.25
          },
          // 4: Projeção Mitigada Closed-Loop
          {
            label: 'Projeção Sob Auto-Cura ARKHÉ',
            data: Array(12).fill(null),
            borderColor: '#22c55e',
            borderDash: [4, 4],
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: {
          intersect: false,
          mode: 'index'
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#0f172a',
            borderColor: '#334155',
            borderWidth: 1,
            callbacks: {
              label: (ctx) => {
                if (ctx.raw === null || ctx.raw === undefined) return '';
                return `${ctx.dataset.label}: ${((ctx.raw as number) * 100).toFixed(1)}%`;
              }
            }
          }
        },
        scales: {
          y: {
            min: 0,
            max: 1.0,
            ticks: {
              color: '#94a3b8',
              callback: (v) => `${((v as number) * 100).toFixed(0)}%`,
              stepSize: 0.25
            },
            grid: { color: 'rgba(30, 41, 59, 0.6)' }
          },
          x: {
            ticks: { color: '#94a3b8' },
            grid: { color: 'rgba(30, 41, 59, 0.4)' }
          }
        }
      }
    });
  }

  private updateChartData(proj: ProjectionState): void {
    if (!this.chart) return;

    const past = proj.past_trajectory || [];
    const curRho = proj.current_rho;
    const pLen = past.length;

    const p1 = pLen >= 15 ? past[pLen - 15].rho : (pLen >= 1 ? past[0].rho : curRho);
    const p2 = pLen >= 10 ? past[pLen - 10].rho : (pLen >= 1 ? past[0].rho : curRho);
    const p3 = pLen >= 6 ? past[pLen - 6].rho : (pLen >= 1 ? past[0].rho : curRho);
    const p4 = pLen >= 3 ? past[pLen - 3].rho : curRho;

    const histData = [p1, p2, p3, p4, curRho, null, null, null, null, null, null, null];
    this.chart.data.datasets[2].data = histData;

    const fut = proj.horizon_points || [];
    if (fut.length >= 8) {
      const coneUpper = [
        null, null, null, null, curRho,
        fut[1].rho_upper, fut[2].rho_upper, fut[3].rho_upper,
        fut[4].rho_upper, fut[5].rho_upper, fut[6].rho_upper, fut[7].rho_upper
      ];
      const coneLower = [
        null, null, null, null, curRho,
        fut[1].rho_lower, fut[2].rho_lower, fut[3].rho_lower,
        fut[4].rho_lower, fut[5].rho_lower, fut[6].rho_lower, fut[7].rho_lower
      ];
      const projMedian = [
        null, null, null, null, curRho,
        fut[1].rho_expected, fut[2].rho_expected, fut[3].rho_expected,
        fut[4].rho_expected, fut[5].rho_expected, fut[6].rho_expected, fut[7].rho_expected
      ];
      const projMit = [
        null, null, null, null, curRho,
        fut[1].rho_mitigated, fut[2].rho_mitigated, fut[3].rho_mitigated,
        fut[4].rho_mitigated, fut[5].rho_mitigated, fut[6].rho_mitigated, fut[7].rho_mitigated
      ];

      this.chart.data.datasets[0].data = coneUpper;
      this.chart.data.datasets[1].data = coneLower;
      this.chart.data.datasets[3].data = projMedian;
      this.chart.data.datasets[4].data = projMit;
    }

    // Zero-overhead update at 20 FPS
    this.chart.update('none');
  }
}
