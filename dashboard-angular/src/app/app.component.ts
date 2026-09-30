import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TelemetryStore } from './core/state/telemetry.store';
import { ScenarioBarComponent } from './features/scenario-bar/scenario-bar.component';
import { KpiHeroComponent } from './features/kpi-hero/kpi-hero.component';
import { GovernanceDeckComponent } from './features/governance-deck/governance-deck.component';
import { TopologyGraphComponent } from './features/topology-graph/topology-graph.component';
import { HorizonChartComponent } from './features/horizon-chart/horizon-chart.component';
import { RealtimeMetricsComponent } from './features/realtime-metrics/realtime-metrics.component';
import { LyapunovCanvasComponent } from './features/lyapunov-canvas/lyapunov-canvas.component';
import { JourneyWaterfallComponent } from './features/journey-waterfall/journey-waterfall.component';
import { AuditLogsComponent } from './features/audit-logs/audit-logs.component';
import { TimeMachineScrubberComponent } from './features/time-machine-scrubber/time-machine-scrubber.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    TimeMachineScrubberComponent,
    ScenarioBarComponent,
    KpiHeroComponent,
    GovernanceDeckComponent,
    TopologyGraphComponent,
    HorizonChartComponent,
    RealtimeMetricsComponent,
    LyapunovCanvasComponent,
    JourneyWaterfallComponent,
    AuditLogsComponent
  ],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  public store = inject(TelemetryStore);

  public toggleMitigation(): void {
    this.store.toggleMitigation();
  }

  public adjustTps(delta: number): void {
    this.store.adjustTps(delta);
  }

  public setTps(tps: number): void {
    this.store.setTps(tps);
  }

  public toggleStochasticMode(): void {
    this.store.toggleStochasticMode();
  }
}
