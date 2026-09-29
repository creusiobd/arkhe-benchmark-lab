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

@Component({
  selector: 'arkhe-realtime-metrics',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="metrics-grid">
      <!-- 1. Latência P95 Real vs Limiar SRE (1.500 ms) -->
      <div class="metric-chart-card">
        <div class="chart-header">
          <span class="chart-title">LATÊNCIA P95 vs LIMIAR SRE (1.500 ms)</span>
          <span class="current-val" [style.color]="store.p95Ms() > 1000 ? '#ef4444' : '#38bdf8'">
            {{ store.p95Ms() | number:'1.0-0' }} ms
          </span>
        </div>
        <div class="canvas-box">
          <canvas #latencyCanvas></canvas>
        </div>
      </div>

      <!-- 2. Saturação do Pool Antifraude vs Capacidade -->
      <div class="metric-chart-card">
        <div class="chart-header">
          <span class="chart-title">POOL ANTIFRAUDE vs CAPACIDADE</span>
          <span class="current-val" [style.color]="store.poolUtilizationPct() > 80 ? '#ef4444' : '#10b981'">
            {{ store.poolInUse() }} / {{ store.poolCapacity() }} slots
          </span>
        </div>
        <div class="canvas-box">
          <canvas #poolCanvas></canvas>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .metrics-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }
    @media (max-width: 768px) {
      .metrics-grid {
        grid-template-columns: 1fr;
      }
    }
    .metric-chart-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px;
      display: flex;
      flex-direction: column;
    }
    .chart-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .chart-title {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-primary);
      letter-spacing: 0.4px;
    }
    .current-val {
      font-size: 12px;
      font-weight: 800;
      font-family: var(--font-mono);
    }
    .canvas-box {
      position: relative;
      height: 120px;
      width: 100%;
    }
  `]
})
export class RealtimeMetricsComponent implements AfterViewInit, OnDestroy {
  @ViewChild('latencyCanvas') latencyCanvasRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('poolCanvas') poolCanvasRef!: ElementRef<HTMLCanvasElement>;

  public store = inject(TelemetryStore);

  private chartLatency?: Chart;
  private chartPool?: Chart;
  private maxPoints = 30;

  constructor() {
    effect(() => {
      const p95 = this.store.p95Ms();
      const inUse = this.store.poolInUse();
      const cap = this.store.poolCapacity();

      if (this.chartLatency && this.chartPool) {
        this.updateCharts(p95, inUse, cap);
      }
    });
  }

  ngAfterViewInit(): void {
    this.initLatencyChart();
    this.initPoolChart();
  }

  ngOnDestroy(): void {
    if (this.chartLatency) this.chartLatency.destroy();
    if (this.chartPool) this.chartPool.destroy();
  }

  private initLatencyChart(): void {
    const ctx = this.latencyCanvasRef.nativeElement.getContext('2d');
    if (!ctx) return;

    this.chartLatency = new Chart(ctx, {
      type: 'line',
      data: {
        labels: Array(this.maxPoints).fill(''),
        datasets: [
          {
            label: 'P95 Real',
            data: Array(this.maxPoints).fill(150),
            borderColor: '#388bfd',
            backgroundColor: 'rgba(56, 139, 253, 0.1)',
            fill: true,
            tension: 0.25,
            pointRadius: 0
          },
          {
            label: 'Limiar SRE (1500ms)',
            data: Array(this.maxPoints).fill(1500),
            borderColor: '#ef4444',
            borderDash: [5, 5],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            min: 0,
            max: 1800,
            ticks: {
              color: '#94a3b8',
              stepSize: 450,
              callback: (v) => `${v}ms`
            },
            grid: { color: 'rgba(30, 41, 59, 0.5)' }
          },
          x: { display: false }
        }
      }
    });
  }

  private initPoolChart(): void {
    const ctx = this.poolCanvasRef.nativeElement.getContext('2d');
    if (!ctx) return;

    this.chartPool = new Chart(ctx, {
      type: 'line',
      data: {
        labels: Array(this.maxPoints).fill(''),
        datasets: [
          {
            label: 'Uso do Pool',
            data: Array(this.maxPoints).fill(5),
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.25,
            pointRadius: 0
          },
          {
            label: 'Capacidade HPA',
            data: Array(this.maxPoints).fill(30),
            borderColor: '#8b5cf6',
            borderDash: [4, 4],
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            min: 0,
            max: 70,
            ticks: {
              color: '#94a3b8',
              stepSize: 15,
              callback: (v) => `${v} slots`
            },
            grid: { color: 'rgba(30, 41, 59, 0.5)' }
          },
          x: { display: false }
        }
      }
    });
  }

  private updateCharts(p95: number, inUse: number, cap: number): void {
    if (this.chartLatency) {
      this.chartLatency.data.datasets[0].data.shift();
      this.chartLatency.data.datasets[0].data.push(p95);
      this.chartLatency.update('none');
    }

    if (this.chartPool) {
      this.chartPool.data.datasets[0].data.shift();
      this.chartPool.data.datasets[0].data.push(inUse);
      this.chartPool.data.datasets[1].data = Array(this.maxPoints).fill(cap);
      this.chartPool.data.datasets[0].borderColor = inUse > (cap * 0.8) ? '#ef4444' : (inUse > (cap * 0.5) ? '#f59e0b' : '#10b981');
      this.chartPool.update('none');
    }
  }
}
