import { 
  Component, 
  ElementRef, 
  ViewChild, 
  AfterViewInit, 
  inject, 
  effect 
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { TelemetryStore } from '../../core/state/telemetry.store';

interface Point {
  x: number;
  y: number;
}

@Component({
  selector: 'arkhe-lyapunov-canvas',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="phase-space-box">
      <div class="box-header">
        <span class="box-title">ESPAÇO DE FASE 2D: ATRATOR DE COLAPSO</span>
        <span class="formula-badge">ρ vs Wq/Ws</span>
      </div>
      <div class="canvas-wrapper">
        <canvas #phaseCanvas width="340" height="150"></canvas>
      </div>
      <div class="phase-legend">
        <span><span class="dot-green"></span> Bacia Estável (ρ &lt; 0.5)</span>
        <span><span class="dot-yellow"></span> Drift</span>
        <span><span class="dot-red"></span> Ruptura (ρ &gt; 0.8)</span>
      </div>
    </div>
  `,
  styles: [`
    .phase-space-box {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px;
      display: flex;
      flex-direction: column;
    }
    .box-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .box-title {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-primary);
    }
    .formula-badge {
      font-size: 10px;
      font-family: var(--font-mono);
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.1);
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid rgba(56, 189, 248, 0.2);
    }
    .canvas-wrapper {
      position: relative;
      width: 100%;
      height: 150px;
    }
    canvas {
      width: 100%;
      height: 100%;
      background: #0b1120;
      border-radius: 6px;
      border: 1px solid #1f293d;
      display: block;
    }
    .phase-legend {
      display: flex;
      justify-content: space-between;
      font-size: 10px;
      color: var(--text-muted);
      margin-top: 8px;
      padding-top: 6px;
      border-top: 1px solid rgba(255, 255, 255, 0.04);
    }
    .phase-legend span {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .dot-green { width: 6px; height: 6px; border-radius: 50%; background: #10b981; }
    .dot-yellow { width: 6px; height: 6px; border-radius: 50%; background: #f59e0b; }
    .dot-red { width: 6px; height: 6px; border-radius: 50%; background: #ef4444; }
  `]
})
export class LyapunovCanvasComponent implements AfterViewInit {
  @ViewChild('phaseCanvas') phaseCanvasRef!: ElementRef<HTMLCanvasElement>;

  public store = inject(TelemetryStore);

  private ctx: CanvasRenderingContext2D | null = null;
  private history: Point[] = [];
  private maxHistory = 45;

  constructor() {
    effect(() => {
      const rho = this.store.poolUtilizationRatio();
      const wqWs = this.store.wqWsRatio();
      const mitActive = this.store.isMitigationActive();

      if (this.ctx) {
        this.renderPhaseSpace(rho, wqWs, mitActive);
      }
    });
  }

  ngAfterViewInit(): void {
    const canvas = this.phaseCanvasRef.nativeElement;
    this.ctx = canvas.getContext('2d');
    this.renderPhaseSpace(
      this.store.poolUtilizationRatio(),
      this.store.wqWsRatio(),
      this.store.isMitigationActive()
    );
  }

  private renderPhaseSpace(rho: number, wqWs: number, mitigationActive: boolean): void {
    if (!this.ctx || !this.phaseCanvasRef) return;

    const canvas = this.phaseCanvasRef.nativeElement;
    const w = canvas.width;
    const h = canvas.height;
    const ctx = this.ctx;

    // Limpa quadro anterior
    ctx.clearRect(0, 0, w, h);

    // Eixos cartesianos
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(35, h - 25);
    ctx.lineTo(w - 15, h - 25); // Eixo X (Wq/Ws)
    ctx.moveTo(35, 15);
    ctx.lineTo(35, h - 25);     // Eixo Y (rho)
    ctx.stroke();

    // Rótulos dos eixos
    ctx.fillStyle = '#64748b';
    ctx.font = '10px sans-serif';
    ctx.fillText('Wq/Ws (Fila)', w - 75, h - 10);
    ctx.save();
    ctx.translate(12, 60);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('ρ (Ocupação)', 0, 0);
    ctx.restore();

    // Escala
    ctx.fillStyle = '#475569';
    ctx.font = '9px monospace';
    ctx.fillText('0.0', 30, h - 12);
    ctx.fillText('0.5', 35 + (w - 50) * 0.5, h - 12);
    ctx.fillText('1.0', w - 25, h - 12);
    ctx.fillText('100%', 8, 20);
    ctx.fillText('50%', 12, 20 + (h - 45) * 0.5);

    // Funções de projeção de coordenadas
    const plotX = (val: number) => 35 + Math.min(1.2, Math.max(0, val)) / 1.2 * (w - 50);
    const plotY = (val: number) => (h - 25) - Math.min(1.0, Math.max(0, val)) * (h - 45);

    // 1. Zona da Bacia de Estabilidade Nominal (verde suave)
    ctx.fillStyle = 'rgba(34, 197, 94, 0.08)';
    ctx.fillRect(plotX(0), plotY(0.50), plotX(0.25) - plotX(0), plotY(0) - plotY(0.50));

    // 2. Zona de Alerta / Drift Silencioso (amarelo)
    ctx.fillStyle = 'rgba(234, 179, 8, 0.08)';
    ctx.fillRect(plotX(0.25), plotY(0.80), plotX(0.70) - plotX(0.25), plotY(0) - plotY(0.80));

    // 3. Zona de Ruptura Catastrófica (vermelho)
    ctx.fillStyle = 'rgba(239, 68, 68, 0.12)';
    ctx.fillRect(plotX(0.70), plotY(1.0), plotX(1.2) - plotX(0.70), plotY(0) - plotY(1.0));

    // Linha de Limiar Crítico (rho = 0.80)
    ctx.strokeStyle = 'rgba(239, 68, 68, 0.4)';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(35, plotY(0.80));
    ctx.lineTo(w - 15, plotY(0.80));
    ctx.stroke();
    ctx.setLineDash([]);

    // Atualiza histórico temporal deslizante da trajetória
    const curX = plotX(wqWs);
    const curY = plotY(rho);
    this.history.push({ x: curX, y: curY });
    if (this.history.length > this.maxHistory) {
      this.history.shift();
    }

    // Desenha o trail do atrator
    if (this.history.length > 1) {
      ctx.beginPath();
      ctx.moveTo(this.history[0].x, this.history[0].y);
      for (let i = 1; i < this.history.length; i++) {
        ctx.lineTo(this.history[i].x, this.history[i].y);
      }
      ctx.strokeStyle = mitigationActive ? 'rgba(34, 197, 94, 0.6)' : 'rgba(56, 189, 248, 0.5)';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Partículas históricas com gradiente alpha
      for (let i = 0; i < this.history.length; i++) {
        const alpha = (i / this.history.length) * 0.7;
        ctx.fillStyle = mitigationActive ? `rgba(34, 197, 94, ${alpha})` : `rgba(56, 189, 248, ${alpha})`;
        ctx.beginPath();
        ctx.arc(this.history[i].x, this.history[i].y, 2, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Ponto Atual com Halo Pulsante
    const isCritical = rho >= 0.80 || wqWs > 0.6;
    const isWarning = rho >= 0.50 || wqWs > 0.2;
    const pointColor = isCritical ? '#ef4444' : (isWarning ? '#f59e0b' : '#38bdf8');

    // Halo
    ctx.beginPath();
    ctx.arc(curX, curY, 7, 0, Math.PI * 2);
    ctx.fillStyle = isCritical ? 'rgba(239, 68, 68, 0.35)' : 'rgba(56, 189, 248, 0.25)';
    ctx.fill();

    // Ponto sólido
    ctx.beginPath();
    ctx.arc(curX, curY, 4, 0, Math.PI * 2);
    ctx.fillStyle = pointColor;
    ctx.fill();

    // Se a mitigação estiver ativa, projeta o vetor corretivo
    if (mitigationActive) {
      const targetX = plotX(0.05);
      const targetY = plotY(0.12);

      ctx.beginPath();
      ctx.moveTo(curX, curY);
      ctx.lineTo(targetX, targetY);
      ctx.strokeStyle = '#22c55e';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#22c55e';
      ctx.font = '10px monospace';
      ctx.fillText('⚡ Auto-Cura', targetX + 4, targetY + 12);
    }
  }
}
