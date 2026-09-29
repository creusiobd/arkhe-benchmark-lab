import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TelemetryStore } from '../../core/state/telemetry.store';
import { ChaosApiService } from '../../core/services/chaos-api.service';

interface ScenarioDef {
  id: string;
  title: string;
  icon: string;
  sub: string;
}

@Component({
  selector: 'arkhe-scenario-bar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="deck">
      <div class="deck-header">
        <span class="deck-title">CONTROLE DE INJEÇÃO DE CENÁRIOS & CAOS (FÍSICA EM TEMPO REAL)</span>
        <span class="deck-desc">Selecione o perfil estocástico para testar a sensibilidade da esteira</span>
      </div>
      <div class="scenario-buttons">
        @for (sc of scenarios; track sc.id) {
          <button 
            class="btn-scenario" 
            [ngClass]="{ 'active': isScenarioActive(sc.id) }"
            (click)="selectScenario(sc.id)">
            <span class="btn-main">{{ sc.icon }} {{ sc.title }}</span>
            <span class="btn-sub">{{ sc.sub }}</span>
          </button>
        }
      </div>
    </div>
  `,
  styles: [`
    .deck {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 20px;
    }
    .deck-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 6px;
    }
    .deck-title {
      font-size: 11px;
      font-weight: 800;
      color: var(--text-secondary);
      letter-spacing: 0.6px;
    }
    .deck-desc {
      font-size: 11px;
      color: var(--text-muted);
    }
    .scenario-buttons {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 10px;
    }
    .btn-scenario {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      padding: 10px;
      text-align: left;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 4px;
      transition: all 0.2s ease;
    }
    .btn-scenario:hover {
      background: rgba(30, 41, 59, 0.8);
      border-color: rgba(56, 189, 248, 0.4);
      transform: translateY(-1px);
    }
    .btn-scenario.active {
      background: rgba(30, 58, 138, 0.4);
      border-color: #38bdf8;
      box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
    }
    .btn-main {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-primary);
    }
    .btn-sub {
      font-size: 10px;
      color: var(--text-muted);
      line-height: 1.2;
    }
    .btn-scenario.active .btn-sub {
      color: #93c5fd;
    }
  `]
})
export class ScenarioBarComponent {
  public store = inject(TelemetryStore);
  private api = inject(ChaosApiService);

  public readonly scenarios: ScenarioDef[] = [
    {
      id: 'nominal',
      title: '1. Operação Nominal',
      icon: '🟢',
      sub: '45ms antifraude • Pool ~10% • Budget 100%'
    },
    {
      id: 'drift',
      title: '2. Drift Silencioso',
      icon: '🟡',
      sub: '255ms antifraude • Pool sobe para 68% • SRE mudo'
    },
    {
      id: 'rupture',
      title: '3. Ruptura Little',
      icon: '🔴',
      sub: '420ms antifraude • Pool estoura (100%) • Burn acelerado'
    },
    {
      id: 'recover',
      title: '4. Restaurar / Autocura',
      icon: '🔄',
      sub: 'Volta para 45ms nominais • Estabiliza Burn Rate'
    },
    {
      id: 'hsm_saturation',
      title: '5. Gargalo de HSM / Cripto',
      icon: '⚡',
      sub: '+120ms na validação EMV • Contenção de CPU'
    },
    {
      id: 'acquirer_flapping',
      title: '6. Flapping Adquirente',
      icon: '🌪️',
      sub: '35% erros 503 • Tempestade de Retries'
    },
    {
      id: 'network_jitter',
      title: '7. Jitter de Rede P99',
      icon: '🌊',
      sub: '10% com atraso de 1200ms • Saturação'
    }
  ];

  public isScenarioActive(scenarioId: string): boolean {
    return this.store.scenario()?.id === scenarioId;
  }

  public selectScenario(scenarioId: string): void {
    if (scenarioId === 'recover') {
      this.api.resetSimulation().subscribe();
    } else {
      this.api.setScenario(scenarioId).subscribe();
    }
  }
}
