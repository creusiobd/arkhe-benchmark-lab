import { Injectable, signal, computed, effect } from '@angular/core';
import { TelemetryPayload } from '../models/telemetry.model';

export interface TimelineMarker {
  id: string;
  label: string;
  type: 'scenario' | 'sentinel_alert' | 'sre_alert' | 'mitigation_start';
  index: number;
  offsetSeconds: number;
  timestamp: number;
}

@Injectable({
  providedIn: 'root'
})
export class TimeMachineService {
  // Buffer FIFO de snapshots de telemetria de alta resolução (até 600 frames = ~30s a 20 FPS ou ~60s a 10 FPS)
  public readonly snapshotBuffer = signal<TelemetryPayload[]>([]);
  public readonly maxBufferSize = 600;

  // Estado do Scrubber
  public readonly isLive = signal<boolean>(true);
  public readonly playbackIndex = signal<number>(0);
  public readonly isPlaying = signal<boolean>(false);
  public readonly playbackSpeed = signal<number>(1.0);

  // Marcadores de incidentes para salto rápido
  public readonly markers = signal<TimelineMarker[]>([]);

  // Snapshot atualmente ativo (para alimentar a store quando em replay)
  public readonly currentSnapshot = computed(() => {
    const buf = this.snapshotBuffer();
    if (buf.length === 0) return null;
    const idx = Math.min(buf.length - 1, Math.max(0, this.playbackIndex()));
    return buf[idx];
  });

  // Offset de tempo em segundos em relação ao frame mais recente
  public readonly currentOffsetSeconds = computed(() => {
    const buf = this.snapshotBuffer();
    if (buf.length === 0 || this.isLive()) return 0;
    const latest = buf[buf.length - 1];
    const current = this.currentSnapshot();
    if (!latest || !current) return 0;
    const diff = (current.stream_meta.timestamp - latest.stream_meta.timestamp);
    return Math.round(diff * 10) / 10;
  });

  private playTimer: any = null;
  private lastRecordedScenario = '';
  private lastRecordedSentinelState = false;

  constructor() {}

  /**
   * Registra um novo frame recebido via WebSocket
   */
  public pushSnapshot(payload: TelemetryPayload): void {
    if (!payload || !payload.stream_meta) return;

    this.snapshotBuffer.update(buf => {
      const updated = [...buf, payload];
      if (updated.length > this.maxBufferSize) {
        updated.shift();
      }
      return updated;
    });

    const buf = this.snapshotBuffer();
    const newIdx = buf.length - 1;

    // Se estiver em modo Live, mantém o ponteiro de reprodução no frame mais recente
    if (this.isLive()) {
      this.playbackIndex.set(newIdx);
    }

    // Detecta e cria marcadores de incidentes automaticamente
    this.detectIncidentMarkers(payload, newIdx);
  }

  private detectIncidentMarkers(payload: TelemetryPayload, index: number): void {
    const scId = payload.scenario?.id || '';
    const sentTriggered = payload.sentinel?.triggered || false;
    const now = payload.stream_meta.timestamp;

    // Marcador de mudança de cenário
    if (scId && scId !== this.lastRecordedScenario) {
      this.lastRecordedScenario = scId;
      const label = payload.scenario?.description?.split('.')[1]?.trim() || scId.toUpperCase();
      this.addMarker({
        id: `sc_${now}`,
        label: `Cenário: ${label}`,
        type: 'scenario',
        index,
        offsetSeconds: 0,
        timestamp: now
      });
    }

    // Marcador de disparo do ARKHÉ Sentinel
    if (sentTriggered && !this.lastRecordedSentinelState) {
      this.lastRecordedSentinelState = true;
      this.addMarker({
        id: `sent_${now}`,
        label: `⚡ Disparo ARKHÉ (${payload.sentinel?.lead_time_seconds || 0}s antecipado)`,
        type: 'sentinel_alert',
        index,
        offsetSeconds: 0,
        timestamp: now
      });
    } else if (!sentTriggered) {
      this.lastRecordedSentinelState = false;
    }
  }

  private addMarker(marker: TimelineMarker): void {
    this.markers.update(m => {
      const next = [...m, marker];
      if (next.length > 8) next.shift(); // Mantém até 8 marcadores recentes
      return next;
    });
  }

  /**
   * Arrasta o scrubber para um frame específico
   */
  public scrubTo(index: number): void {
    this.pause();
    this.isLive.set(false);
    const buf = this.snapshotBuffer();
    const clamped = Math.max(0, Math.min(buf.length - 1, index));
    this.playbackIndex.set(clamped);
  }

  /**
   * Avança ou retrocede frames individuais
   */
  public step(delta: number): void {
    this.pause();
    this.isLive.set(false);
    const buf = this.snapshotBuffer();
    const nextIdx = Math.max(0, Math.min(buf.length - 1, this.playbackIndex() + delta));
    this.playbackIndex.set(nextIdx);
  }

  /**
   * Inicia o playback de reprodução
   */
  public play(): void {
    if (this.isPlaying()) return;
    this.isLive.set(false);
    this.isPlaying.set(true);

    const intervalMs = Math.round(50 / this.playbackSpeed()); // 50ms = 20 FPS base
    this.playTimer = setInterval(() => {
      const buf = this.snapshotBuffer();
      const current = this.playbackIndex();
      if (current >= buf.length - 1) {
        // Chegou ao fim do buffer, volta ao modo ao vivo
        this.returnToLive();
      } else {
        this.playbackIndex.set(current + 1);
      }
    }, intervalMs);
  }

  /**
   * Pausa a reprodução
   */
  public pause(): void {
    this.isPlaying.set(false);
    if (this.playTimer) {
      clearInterval(this.playTimer);
      this.playTimer = null;
    }
  }

  /**
   * Altera a velocidade do playback (0.5x, 1x, 2x)
   */
  public setSpeed(speed: number): void {
    this.playbackSpeed.set(speed);
    if (this.isPlaying()) {
      this.pause();
      this.play();
    }
  }

  /**
   * Salta diretamente para um marcador de evento crítico
   */
  public jumpToMarker(marker: TimelineMarker): void {
    this.scrubTo(marker.index);
  }

  /**
   * Retorna ao streaming em tempo real
   */
  public returnToLive(): void {
    this.pause();
    this.isLive.set(true);
    const buf = this.snapshotBuffer();
    if (buf.length > 0) {
      this.playbackIndex.set(buf.length - 1);
    }
  }
}
