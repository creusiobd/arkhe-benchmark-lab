import { Injectable, signal, computed, OnDestroy } from '@angular/core';
import { Observable, Subject, Subscription, timer } from 'rxjs';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { retry, tap, delayWhen } from 'rxjs/operators';
import { TelemetryPayload } from '../models/telemetry.model';

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected';

@Injectable({
  providedIn: 'root'
})
export class WebsocketTelemetryService implements OnDestroy {
  private socket$?: WebSocketSubject<any>;
  private telemetrySubject$ = new Subject<TelemetryPayload>();
  private sub?: Subscription;

  // Signals para reatividade fina (Zoneless / Angular 17+)
  public readonly connectionStatus = signal<ConnectionStatus>('disconnected');
  public readonly latestPayload = signal<TelemetryPayload | null>(null);
  public readonly fpsCount = signal<number>(20);
  public readonly isConnected = computed(() => this.connectionStatus() === 'connected');

  private lastMessageTime = Date.now();
  private frameCount = 0;
  private fpsTimer?: any;

  constructor() {
    this.startFpsCounter();
    this.connect();
  }

  private getDefaultWsUrl(): string {
    if (typeof window !== 'undefined' && window.location) {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${proto}//${window.location.host}/ws/telemetry`;
    }
    return 'ws://127.0.0.1:8080/ws/telemetry';
  }

  public connect(url?: string): void {
    if (this.sub) {
      this.sub.unsubscribe();
    }

    const wsUrl = url || this.getDefaultWsUrl();
    this.connectionStatus.set('connecting');

    this.socket$ = webSocket({
      url: wsUrl,
      openObserver: {
        next: () => {
          this.connectionStatus.set('connected');
        }
      },
      closeObserver: {
        next: () => {
          this.connectionStatus.set('disconnected');
        }
      }
    });

    this.sub = this.socket$
      .pipe(
        tap((data: TelemetryPayload) => {
          this.frameCount++;
          this.latestPayload.set(data);
          this.telemetrySubject$.next(data);
        }),
        retry({
          delay: (error, retryCount) => {
            this.connectionStatus.set('connecting');
            const backoff = Math.min(1000 * Math.pow(1.5, retryCount), 5000);
            return timer(backoff);
          }
        })
      )
      .subscribe({
        error: (err) => {
          console.error('[WebsocketTelemetryService] Erro fatal no stream:', err);
          this.connectionStatus.set('disconnected');
        }
      });
  }

  public getTelemetryStream(): Observable<TelemetryPayload> {
    return this.telemetrySubject$.asObservable();
  }

  public sendCommand(cmd: string): void {
    if (this.socket$ && this.isConnected()) {
      this.socket$.next(cmd);
    } else {
      console.warn('[WebsocketTelemetryService] Não conectado. Comando ignorado:', cmd);
    }
  }

  public triggerScenario(scenarioName: string): void {
    this.sendCommand(`scenario:${scenarioName}`);
  }

  public toggleMitigation(): void {
    this.sendCommand('toggle_mitigation');
  }

  public setTps(tps: number): void {
    this.sendCommand(`set_tps:${tps}`);
  }

  public adjustTps(delta: number): void {
    this.sendCommand(`delta_tps:${delta}`);
  }

  public toggleStochastic(): void {
    this.sendCommand('toggle_stochastic');
  }

  private startFpsCounter(): void {
    this.fpsTimer = setInterval(() => {
      this.fpsCount.set(this.frameCount);
      this.frameCount = 0;
    }, 1000);
  }

  ngOnDestroy(): void {
    if (this.fpsTimer) {
      clearInterval(this.fpsTimer);
    }
    if (this.sub) {
      this.sub.unsubscribe();
    }
    if (this.socket$) {
      this.socket$.complete();
    }
  }
}
