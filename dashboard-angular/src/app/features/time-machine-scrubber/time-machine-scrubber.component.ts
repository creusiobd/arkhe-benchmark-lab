import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TimeMachineService, TimelineMarker } from '../../core/services/time-machine.service';

@Component({
  selector: 'arkhe-time-machine-scrubber',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="scrubber-deck" [class.scrubber-rewound]="!tm.isLive()">
      <div class="scrubber-header">
        <div class="status-indicator">
          @if (tm.isLive()) {
            <span class="live-beacon">
              <span class="beacon-pulse"></span>
              <span class="beacon-text">TRANSMISSÃO AO VIVO (20 FPS)</span>
            </span>
          } @else {
            <span class="rewind-beacon">
              <span class="rewind-icon">⏪</span>
              <span class="rewind-text">FLIGHT RECORDER TIME MACHINE: <strong>{{ tm.currentOffsetSeconds() }}s</strong></span>
              <span class="frame-tag">Frame #{{ tm.playbackIndex() + 1 }} de {{ tm.snapshotBuffer().length }}</span>
            </span>
          }
        </div>

        <!-- BOTÕES DE PLAYBACK & VELOCIDADE -->
        <div class="scrubber-actions">
          <div class="speed-selector">
            <button 
              type="button" 
              class="speed-btn" 
              [class.active]="tm.playbackSpeed() === 0.5" 
              (click)="tm.setSpeed(0.5)">0.5x</button>
            <button 
              type="button" 
              class="speed-btn" 
              [class.active]="tm.playbackSpeed() === 1.0" 
              (click)="tm.setSpeed(1.0)">1.0x</button>
            <button 
              type="button" 
              class="speed-btn" 
              [class.active]="tm.playbackSpeed() === 2.0" 
              (click)="tm.setSpeed(2.0)">2.0x</button>
          </div>

          <div class="transport-controls">
            <!-- Pular para o início -->
            <button 
              type="button" 
              class="btn-transport" 
              title="Ir para o frame mais antigo gravado"
              (click)="tm.scrubTo(0)">
              ⏮️
            </button>
            <!-- Step -1 Frame -->
            <button 
              type="button" 
              class="btn-transport" 
              title="Retroceder 1 frame (50ms)"
              (click)="tm.step(-1)">
              ◀️
            </button>
            <!-- Play / Pause -->
            @if (tm.isPlaying()) {
              <button 
                type="button" 
                class="btn-transport btn-play-active" 
                title="Pausar reprodução"
                (click)="tm.pause()">
                ⏸️
              </button>
            } @else {
              <button 
                type="button" 
                class="btn-transport" 
                title="Reproduzir trajetória gravada"
                (click)="tm.play()">
                ▶️
              </button>
            }
            <!-- Step +1 Frame -->
            <button 
              type="button" 
              class="btn-transport" 
              title="Avançar 1 frame (50ms)"
              (click)="tm.step(1)">
              ▶️
            </button>
          </div>

          <!-- BOTÃO VOLTAR AO VIVO -->
          <button 
            type="button" 
            class="btn-live-toggle" 
            [class.btn-is-live]="tm.isLive()"
            (click)="tm.returnToLive()">
            <span class="live-dot"></span>
            {{ tm.isLive() ? 'Sincronizado' : '🔴 VOLTAR AO VIVO' }}
          </button>
        </div>
      </div>

      <!-- TIMELINE SLIDER (SCRUBBER TRACK) -->
      <div class="slider-wrapper">
        <input 
          type="range" 
          class="timeline-slider"
          [min]="0" 
          [max]="maxIndex"
          [value]="tm.playbackIndex()"
          [disabled]="tm.snapshotBuffer().length <= 1"
          (input)="onSliderInput($event)"
        />

        <!-- MARCADORES DE ESCALA TEMPORAL -->
        <div class="timeline-scale">
          <span>-{{ getMaxSeconds() | number:'1.0-0' }}s</span>
          <span>-{{ (getMaxSeconds() * 0.75) | number:'1.0-0' }}s</span>
          <span>-{{ (getMaxSeconds() * 0.5) | number:'1.0-0' }}s</span>
          <span>-{{ (getMaxSeconds() * 0.25) | number:'1.0-0' }}s</span>
          <span class="scale-live">AGORA (0.0s)</span>
        </div>
      </div>

      <!-- MARCADORES DE INCIDENTES (CHIPS PARA SALTO RÁPIDO) -->
      @if (tm.markers().length > 0) {
        <div class="markers-row">
          <span class="markers-label">Pontos de Mutação Gravados:</span>
          <div class="markers-list">
            @for (m of tm.markers(); track m.id) {
              <button 
                type="button" 
                class="marker-chip" 
                [ngClass]="'marker-' + m.type"
                (click)="tm.jumpToMarker(m)">
                {{ m.label }}
              </button>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .scrubber-deck {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px 18px;
      margin-bottom: 20px;
      transition: all 0.3s ease;
    }
    .scrubber-rewound {
      border-color: #f59e0b;
      box-shadow: 0 0 20px rgba(245, 158, 11, 0.15);
      background: linear-gradient(180deg, rgba(30, 27, 22, 0.9) 0%, rgba(15, 23, 42, 0.8) 100%);
    }

    .scrubber-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      flex-wrap: wrap;
      gap: 12px;
    }

    .status-indicator {
      display: flex;
      align-items: center;
    }

    /* Live Beacon */
    .live-beacon {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      font-weight: 800;
      color: #10b981;
      letter-spacing: 0.5px;
    }
    .beacon-pulse {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 10px #10b981;
      animation: livePulse 1.5s infinite;
    }

    /* Rewind Beacon */
    .rewind-beacon {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      font-weight: 800;
      color: #f59e0b;
      letter-spacing: 0.5px;
    }
    .rewind-icon {
      font-size: 14px;
      animation: spinBack 3s infinite linear;
    }
    .frame-tag {
      font-size: 10px;
      font-family: var(--font-mono);
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.3);
      padding: 2px 6px;
      border-radius: 4px;
      color: #fcd34d;
    }

    /* Ações de Transporte */
    .scrubber-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .speed-selector {
      display: flex;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 4px;
      padding: 2px;
    }
    .speed-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 3px;
      cursor: pointer;
    }
    .speed-btn.active {
      background: rgba(56, 189, 248, 0.2);
      color: #38bdf8;
    }

    .transport-controls {
      display: flex;
      gap: 4px;
    }
    .btn-transport {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--text-primary);
      width: 28px;
      height: 28px;
      border-radius: 4px;
      font-size: 11px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.15s;
    }
    .btn-transport:hover {
      background: rgba(30, 41, 59, 0.9);
      border-color: rgba(56, 189, 248, 0.4);
    }
    .btn-play-active {
      background: rgba(245, 158, 11, 0.2) !important;
      border-color: #f59e0b !important;
    }

    .btn-live-toggle {
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: #ef4444;
      font-size: 11px;
      font-weight: 800;
      padding: 5px 12px;
      border-radius: 5px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }
    .btn-live-toggle:hover {
      background: rgba(239, 68, 68, 0.25);
    }
    .btn-is-live {
      background: rgba(16, 185, 129, 0.1);
      border-color: rgba(16, 185, 129, 0.3);
      color: #10b981;
    }
    .live-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
    }

    /* Slider Track */
    .slider-wrapper {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .timeline-slider {
      -webkit-appearance: none;
      width: 100%;
      height: 8px;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.08);
      outline: none;
      cursor: pointer;
      transition: background 0.2s;
    }
    .timeline-slider::-webkit-slider-thumb {
      -webkit-appearance: none;
      appearance: none;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: #38bdf8;
      box-shadow: 0 0 10px #38bdf8;
      cursor: pointer;
      border: 2px solid #fff;
    }
    .scrubber-rewound .timeline-slider::-webkit-slider-thumb {
      background: #f59e0b;
      box-shadow: 0 0 12px #f59e0b;
    }

    .timeline-scale {
      display: flex;
      justify-content: space-between;
      font-size: 9px;
      font-family: var(--font-mono);
      color: var(--text-muted);
      padding: 0 2px;
    }
    .scale-live {
      color: #10b981;
      font-weight: 700;
    }

    /* Marcadores de Incidentes */
    .markers-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 10px;
      padding-top: 8px;
      border-top: 1px solid rgba(255, 255, 255, 0.04);
      flex-wrap: wrap;
    }
    .markers-label {
      font-size: 10px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
    }
    .markers-list {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
    .marker-chip {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 4px;
      padding: 2px 7px;
      font-size: 10px;
      color: var(--text-secondary);
      cursor: pointer;
      transition: all 0.15s;
    }
    .marker-chip:hover {
      background: rgba(30, 41, 59, 0.9);
      color: #fff;
    }
    .marker-scenario {
      border-color: rgba(56, 189, 248, 0.3);
      color: #93c5fd;
    }
    .marker-sentinel_alert {
      border-color: rgba(245, 158, 11, 0.4);
      background: rgba(245, 158, 11, 0.1);
      color: #fcd34d;
    }

    @keyframes livePulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
    @keyframes spinBack {
      from { transform: rotate(0deg); }
      to { transform: rotate(-360deg); }
    }
  `]
})
export class TimeMachineScrubberComponent {
  public tm = inject(TimeMachineService);

  public get maxIndex(): number {
    const len = this.tm.snapshotBuffer().length;
    return len > 0 ? len - 1 : 0;
  }

  public getMaxSeconds(): number {
    const len = this.tm.snapshotBuffer().length;
    return Math.max(10, Math.round(len / 20)); // ~20 frames por segundo
  }

  public onSliderInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    const val = parseInt(target.value, 10);
    this.tm.scrubTo(val);
  }
}
