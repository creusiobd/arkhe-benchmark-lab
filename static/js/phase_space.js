/**
 * phase_space.js - Renderizador do Espaço de Fase 2D de Lyapunov (Atrator de Colapso)
 * Desenha em Canvas 2D a trajetória dinâmica rho (ocupação) vs Wq/Ws (física de Little) a 20 FPS.
 */

export class PhaseSpaceRenderer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        this.history = []; // Histórico deslizante de coordenadas (rho, wq_ws)
        this.maxHistory = 45;
    }

    reset() {
        this.history = [];
        if (this.ctx) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
    }

    draw(rho, wq_ws, mitigationActive = false) {
        if (!this.ctx || !this.canvas) return;

        const w = this.canvas.width;
        const h = this.canvas.height;
        const ctx = this.ctx;

        // Limpa o canvas
        ctx.clearRect(0, 0, w, h);

        // Grid e eixos cartesianos
        ctx.strokeStyle = '#1e293b';
        ctx.lineWidth = 1;
        ctx.beginPath();
        // Eixo horizontal Wq/Ws
        ctx.moveTo(35, h - 25);
        ctx.lineTo(w - 15, h - 25);
        // Eixo vertical rho
        ctx.moveTo(35, 15);
        ctx.lineTo(35, h - 25);
        ctx.stroke();

        // Rótulos dos eixos
        ctx.fillStyle = '#64748b';
        ctx.font = '10px -apple-system, sans-serif';
        ctx.fillText('Wq/Ws (Fila)', w - 75, h - 10);
        ctx.save();
        ctx.translate(12, 60);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('ρ (Ocupação)', 0, 0);
        ctx.restore();

        // Marcações de escala
        ctx.fillStyle = '#475569';
        ctx.font = '9px monospace';
        ctx.fillText('0.0', 30, h - 12);
        ctx.fillText('0.5', 35 + (w - 50) * 0.5, h - 12);
        ctx.fillText('1.0', w - 25, h - 12);

        ctx.fillText('100%', 10, 22);
        ctx.fillText('50%', 14, 20 + (h - 45) * 0.5);

        // Mapeamento matemático de coordenadas de fase para pixels
        // x: Wq/Ws (0 a 1.2 mapeado para [35, w - 15])
        // y: rho (0 a 1.0 mapeado para [h - 25, 20])
        const plotX = (val) => 35 + Math.min(1.2, Math.max(0, val)) / 1.2 * (w - 50);
        const plotY = (val) => (h - 25) - Math.min(1.0, Math.max(0, val)) * (h - 45);

        // 1. Zona da Bacia de Estabilidade Nominal (verde suave)
        ctx.fillStyle = 'rgba(34, 197, 94, 0.08)';
        ctx.fillRect(plotX(0), plotY(0.50), plotX(0.25) - plotX(0), plotY(0) - plotY(0.50));

        // 2. Zona de Alerta / Drift Silencioso (amarelo)
        ctx.fillStyle = 'rgba(234, 179, 8, 0.08)';
        ctx.fillRect(plotX(0.25), plotY(0.80), plotX(0.70) - plotX(0.25), plotY(0) - plotY(0.80));

        // 3. Zona de Ruptura Catastrófica (vermelho)
        ctx.fillStyle = 'rgba(239, 68, 68, 0.12)';
        ctx.fillRect(plotX(0.70), plotY(1.0), plotX(1.2) - plotX(0.70), plotY(0) - plotY(1.0));

        // Linha crítica de saturação (rho = 0.80)
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.4)';
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(35, plotY(0.80));
        ctx.lineTo(w - 15, plotY(0.80));
        ctx.stroke();
        ctx.setLineDash([]);

        // Atualiza histórico temporal deslizante da trajetória
        const curX = plotX(wq_ws);
        const curY = plotY(rho);
        this.history.push({ x: curX, y: curY });
        if (this.history.length > this.maxHistory) {
            this.history.shift();
        }

        // Desenha a cauda da trajetória (Trail do Atrator)
        if (this.history.length > 1) {
            ctx.beginPath();
            ctx.moveTo(this.history[0].x, this.history[0].y);
            for (let i = 1; i < this.history.length; i++) {
                ctx.lineTo(this.history[i].x, this.history[i].y);
            }
            ctx.strokeStyle = mitigationActive ? 'rgba(34, 197, 94, 0.6)' : 'rgba(56, 189, 248, 0.5)';
            ctx.lineWidth = 2;
            ctx.stroke();

            // Desenha pequenas partículas históricas com fade out
            for (let i = 0; i < this.history.length; i++) {
                const alpha = (i / this.history.length) * 0.7;
                ctx.fillStyle = mitigationActive ? `rgba(34, 197, 94, ${alpha})` : `rgba(56, 189, 248, ${alpha})`;
                ctx.beginPath();
                ctx.arc(this.history[i].x, this.history[i].y, 2, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        // Ponto Atual da Trajetória com Halo Pulsante
        const isCritical = rho >= 0.80 || wq_ws > 0.6;
        const isWarning = rho >= 0.50 || wq_ws > 0.2;
        const pointColor = isCritical ? '#ef4444' : (isWarning ? '#f59e0b' : '#38bdf8');

        // Halo externo
        ctx.beginPath();
        ctx.arc(curX, curY, 7, 0, Math.PI * 2);
        ctx.fillStyle = isCritical ? 'rgba(239, 68, 68, 0.35)' : 'rgba(56, 189, 248, 0.25)';
        ctx.fill();

        // Ponto central sólido
        ctx.beginPath();
        ctx.arc(curX, curY, 4, 0, Math.PI * 2);
        ctx.fillStyle = pointColor;
        ctx.fill();

        // Se a mitigação autônoma estiver ativa, desenha o vetor corretivo de estabilização
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
            ctx.fillText('⚡ Vetor de Auto-Cura', targetX + 4, targetY + 12);
        }
    }
}
