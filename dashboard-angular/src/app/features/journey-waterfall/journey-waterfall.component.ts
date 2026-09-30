import { 
  Component, 
  inject, 
  signal, 
  computed, 
  effect, 
  ViewChild 
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ScrollingModule, CdkVirtualScrollViewport } from '@angular/cdk/scrolling';
import { FormsModule } from '@angular/forms';
import { TelemetryStore } from '../../core/state/telemetry.store';
import { RecentJourney, StageBreakdown } from '../../core/models/telemetry.model';

@Component({
  selector: 'arkhe-journey-waterfall',
  standalone: true,
  imports: [CommonModule, ScrollingModule, FormsModule],
  template: `
    <div class="waterfall-deck">
      <!-- CABEÇALHO DO FLIGHT RECORDER -->
      <div class="deck-header">
        <div class="title-group">
          <div class="deck-title">
            <span>⚡ CÂMARA DE TRAJETÓRIAS COM VIRTUAL SCROLL (CDK BUFFER)</span>
            <span class="buffer-badge">{{ historyBuffer().length }} transações retidas</span>
            @if (!isLiveStream()) {
              <span class="pause-badge">STREAM PAUSADO (INSPEÇÃO)</span>
            }
          </div>
          <div class="deck-subtitle">
            Streaming de alta concorrência (120 TPS) com renderização virtual O(1) e inspeção profunda de traces
          </div>
        </div>

        <!-- CONTROLES DE STREAM & AUTO-SCROLL -->
        <div class="header-actions">
          <button 
            type="button" 
            class="btn-control" 
            [class.btn-paused]="!isLiveStream()"
            (click)="toggleLiveStream()">
            {{ isLiveStream() ? '⏸️ Pausar Streaming' : '▶️ Retomar Ao Vivo' }}
          </button>
          <button 
            type="button" 
            class="btn-control" 
            (click)="clearBuffer()">
            🧹 Limpar Buffer
          </button>
        </div>
      </div>

      <!-- BARRA DE FILTROS & PESQUISA EM TEMPO REAL -->
      <div class="filter-bar">
        <!-- Filtro por Status -->
        <div class="filter-group">
          <span class="filter-lbl">Status:</span>
          <div class="pill-group">
            <button 
              type="button" 
              class="pill-btn" 
              [class.active]="statusFilter() === 'ALL'"
              (click)="setStatusFilter('ALL')">
              Todos ({{ historyBuffer().length }})
            </button>
            <button 
              type="button" 
              class="pill-btn pill-crit" 
              [class.active]="statusFilter() === 'TIMEOUT_504'"
              (click)="setStatusFilter('TIMEOUT_504')">
              🔴 504 Timeout ({{ countStatus('TIMEOUT_504') }})
            </button>
            <button 
              type="button" 
              class="pill-btn pill-warn" 
              [class.active]="statusFilter() === 'ACQUIRER_503'"
              (click)="setStatusFilter('ACQUIRER_503')">
              🟡 503 Flapping ({{ countStatus('ACQUIRER_503') }})
            </button>
            <button 
              type="button" 
              class="pill-btn pill-ok" 
              [class.active]="statusFilter() === 'AUTHORIZED'"
              (click)="setStatusFilter('AUTHORIZED')">
              🟢 Aprovadas ({{ countStatus('AUTHORIZED') }})
            </button>
          </div>
        </div>

        <!-- Filtro por Latência Mínima -->
        <div class="filter-group">
          <span class="filter-lbl">Latência:</span>
          <div class="pill-group">
            <button 
              type="button" 
              class="pill-btn" 
              [class.active]="minLatencyFilter() === 0"
              (click)="setMinLatency(0)">
              Todas
            </button>
            <button 
              type="button" 
              class="pill-btn" 
              [class.active]="minLatencyFilter() === 300"
              (click)="setMinLatency(300)">
              &gt; 300 ms
            </button>
            <button 
              type="button" 
              class="pill-btn pill-crit" 
              [class.active]="minLatencyFilter() === 1000"
              (click)="setMinLatency(1000)">
              &gt; 1.000 ms
            </button>
          </div>
        </div>

        <!-- Busca por TX ID / Cartão -->
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input 
            type="text" 
            class="search-input" 
            placeholder="Filtrar por TX ID ou Token..."
            [ngModel]="searchQuery()"
            (ngModelChange)="searchQuery.set($event)"
          />
          @if (searchQuery()) {
            <button type="button" class="btn-clear-search" (click)="searchQuery.set('')">✕</button>
          }
        </div>
      </div>

      <!-- LEGENDA DOS ESTÁGIOS DA CASCATA -->
      <div class="waterfall-legend-bar">
        <span class="legend-note">Clique em qualquer linha para abrir a inspeção completa de tracing</span>
        <div class="legend-items">
          <span><span class="dot-bar" style="background:#3b82f6;"></span> Ingestão</span>
          <span><span class="dot-bar" style="background:#06b6d4;"></span> Limites</span>
          <span><span class="dot-bar" style="background:#eab308;"></span> Fila Little</span>
          <span><span class="dot-bar" style="background:#10b981;"></span> Antifraude</span>
          <span><span class="dot-bar" style="background:#8b5cf6;"></span> Adquirente</span>
        </div>
      </div>

      <!-- TABELA COM CABEÇALHO FIXO -->
      <div class="table-wrapper">
        <div class="table-header-row">
          <div class="col-hora">Hora</div>
          <div class="col-txid">ID Transação</div>
          <div class="col-token">Token / Tentativa</div>
          <div class="col-valor">Valor</div>
          <div class="col-status">Status</div>
          <div class="col-sla">Impacto SLA</div>
          <div class="col-total">Total</div>
          <div class="col-waterfall">Cascata Temporal dos 6 Estágios (Waterfall)</div>
        </div>

        <!-- CDK VIRTUAL SCROLL VIEWPORT COM ALTA PERFORMANCE -->
        <cdk-virtual-scroll-viewport 
          #scrollViewport
          itemSize="44" 
          class="waterfall-viewport">
          <div 
            *cdkVirtualFor="let item of filteredJourneys(); trackBy: trackByTx" 
            class="virtual-row"
            [class.row-selected]="selectedJourney()?.tx_id === item.tx_id"
            (click)="selectJourney(item)">
            
            <div class="col-hora font-mono text-muted">{{ item.timestamp }}</div>
            <div class="col-txid font-mono font-bold">{{ item.tx_id }}</div>
            <div class="col-token font-mono text-muted text-xs">
              {{ item.card_token }} <span class="badge-attempt">att: {{ item.attempt_id.split('_').pop() }}</span>
            </div>
            <div class="col-valor font-mono text-right">R$ {{ (item.amount_brl / 100) | number:'1.2-2' }}</div>
            <div class="col-status">
              <span class="status-pill" [ngClass]="getStatusPillClass(item.status)">
                {{ item.status }}
              </span>
            </div>
            <div class="col-sla font-mono text-xs" [style.color]="item.sla_impact.includes('Intacto') ? '#10b981' : '#ef4444'">
              {{ item.sla_impact }}
            </div>
            <div class="col-total font-mono font-bold" [style.color]="item.total_ms > 1000 ? '#ef4444' : (item.total_ms > 400 ? '#f59e0b' : '#f0f6fc')">
              {{ item.total_ms | number:'1.0-0' }} ms
            </div>
            <div class="col-waterfall">
              <div class="waterfall-bar-track">
                <!-- Ingestão -->
                @if (item.stages.ingest_ms) {
                  <div 
                    class="stage-bar bg-blue" 
                    [style.width.%]="calcStagePct(item.stages.ingest_ms, item.total_ms)"
                    [title]="'Ingestão: ' + item.stages.ingest_ms + 'ms'">
                  </div>
                }
                <!-- Limites -->
                @if (item.stages.limits_ms) {
                  <div 
                    class="stage-bar bg-cyan" 
                    [style.width.%]="calcStagePct(item.stages.limits_ms, item.total_ms)"
                    [title]="'Limites: ' + item.stages.limits_ms + 'ms'">
                  </div>
                }
                <!-- Fila Little -->
                @if (item.stages.antifraud_queue_ms) {
                  <div 
                    class="stage-bar bg-amber" 
                    [style.width.%]="calcStagePct(item.stages.antifraud_queue_ms, item.total_ms)"
                    [title]="'Fila Little: ' + item.stages.antifraud_queue_ms + 'ms'">
                  </div>
                }
                <!-- Antifraude -->
                @if (item.stages.antifraud_service_ms) {
                  <div 
                    class="stage-bar bg-emerald" 
                    [style.width.%]="calcStagePct(item.stages.antifraud_service_ms, item.total_ms)"
                    [title]="'Antifraude: ' + item.stages.antifraud_service_ms + 'ms'">
                  </div>
                }
                <!-- Adquirente -->
                @if (item.stages.authorizer_ms) {
                  <div 
                    class="stage-bar bg-violet" 
                    [style.width.%]="calcStagePct(item.stages.authorizer_ms, item.total_ms)"
                    [title]="'Adquirente: ' + item.stages.authorizer_ms + 'ms'">
                  </div>
                }
              </div>
            </div>
          </div>

          @if (filteredJourneys().length === 0) {
            <div class="empty-viewport">
              Nenhuma transação corresponde aos filtros ativos.
            </div>
          }
        </cdk-virtual-scroll-viewport>
      </div>

      <!-- MODAL / DRAWER DE INSPEÇÃO PROFUNDA DE DISTRIBUTED TRACING -->
      @if (selectedJourney(); as j) {
        <div class="drawer-backdrop" (click)="closeDetail()">
          <div class="trace-drawer" (click)="$event.stopPropagation()">
            <div class="drawer-header">
              <div class="drawer-title-box">
                <span class="drawer-pre">INSPEÇÃO PROFUNDA DE TRACING DISTRIBUÍDO</span>
                <h3 class="drawer-title">{{ j.tx_id }}</h3>
              </div>
              <button type="button" class="btn-close-drawer" (click)="closeDetail()">✕</button>
            </div>

            <div class="drawer-body">
              <!-- Resumo do Status -->
              <div class="trace-summary-grid">
                <div class="sum-card">
                  <span class="sum-label">Status da Transação</span>
                  <span class="status-pill" [ngClass]="getStatusPillClass(j.status)">{{ j.status }}</span>
                </div>
                <div class="sum-card">
                  <span class="sum-label">Latência Total (E2E)</span>
                  <span class="sum-val font-mono" [style.color]="j.total_ms > 1000 ? '#ef4444' : '#38bdf8'">
                    {{ j.total_ms | number:'1.1-1' }} ms
                  </span>
                </div>
                <div class="sum-card">
                  <span class="sum-label">Valor Transacionado</span>
                  <span class="sum-val font-mono">R$ {{ (j.amount_brl / 100) | number:'1.2-2' }}</span>
                </div>
                <div class="sum-card">
                  <span class="sum-label">Impacto no SLA</span>
                  <span class="sum-val font-mono" [style.color]="j.sla_impact.includes('Intacto') ? '#10b981' : '#ef4444'">
                    {{ j.sla_impact }}
                  </span>
                </div>
              </div>

              <!-- Análise Forense de Causa Raiz do ARKHÉ -->
              <div class="rca-box">
                <span class="rca-badge">DIAGNÓSTICO ARKHÉ SENTINEL</span>
                <p class="rca-text">{{ getRcaExplanation(j) }}</p>
              </div>

              <!-- Quebra Detalhada dos 6 Spans de OpenTelemetry -->
              <div class="spans-container">
                <span class="spans-title">CASCATA DE SPANS DE TEMPO (OPENTELEMETRY TRACE SPANS)</span>

                <div class="span-row">
                  <div class="span-info">
                    <span class="span-name">[1] Ingress Gateway</span>
                    <span class="span-component">Envoy Proxy HTTP/2</span>
                  </div>
                  <div class="span-bar-container">
                    <div class="span-bar bg-blue" [style.width.%]="calcStagePct(j.stages.ingest_ms, j.total_ms)"></div>
                  </div>
                  <span class="span-ms font-mono">{{ j.stages.ingest_ms ?? 0 | number:'1.1-1' }} ms</span>
                </div>

                <div class="span-row">
                  <div class="span-info">
                    <span class="span-name">[2] HSM & Limites</span>
                    <span class="span-component">Cripto EMV Pin-Block</span>
                  </div>
                  <div class="span-bar-container">
                    <div class="span-bar bg-cyan" [style.width.%]="calcStagePct(j.stages.limits_ms, j.total_ms)"></div>
                  </div>
                  <span class="span-ms font-mono">{{ j.stages.limits_ms ?? 0 | number:'1.1-1' }} ms</span>
                </div>

                <div class="span-row" [class.span-highlight]="(j.stages.antifraud_queue_ms ?? 0) > 100">
                  <div class="span-info">
                    <span class="span-name">[3] Fila Little (Semáforo)</span>
                    <span class="span-component">Espera por Slot de Concorrência</span>
                  </div>
                  <div class="span-bar-container">
                    <div class="span-bar bg-amber" [style.width.%]="calcStagePct(j.stages.antifraud_queue_ms, j.total_ms)"></div>
                  </div>
                  <span class="span-ms font-mono" [style.color]="(j.stages.antifraud_queue_ms ?? 0) > 100 ? '#ef4444' : '#f59e0b'">
                    {{ j.stages.antifraud_queue_ms ?? 0 | number:'1.1-1' }} ms
                  </span>
                </div>

                <div class="span-row" [class.span-highlight]="(j.stages.antifraud_service_ms ?? 0) > 200">
                  <div class="span-info">
                    <span class="span-name">[4] Pool Antifraude</span>
                    <span class="span-component">Inferência IA de Scoring</span>
                  </div>
                  <div class="span-bar-container">
                    <div class="span-bar bg-emerald" [style.width.%]="calcStagePct(j.stages.antifraud_service_ms, j.total_ms)"></div>
                  </div>
                  <span class="span-ms font-mono" [style.color]="(j.stages.antifraud_service_ms ?? 0) > 200 ? '#ef4444' : '#10b981'">
                    {{ j.stages.antifraud_service_ms ?? 0 | number:'1.1-1' }} ms
                  </span>
                </div>

                <div class="span-row" [class.span-highlight]="j.status === 'ACQUIRER_503'">
                  <div class="span-info">
                    <span class="span-name">[5] Adquirente Externa</span>
                    <span class="span-component">Bandeiras Cielo / Stone / Visa</span>
                  </div>
                  <div class="span-bar-container">
                    <div class="span-bar bg-violet" [style.width.%]="calcStagePct(j.stages.authorizer_ms, j.total_ms)"></div>
                  </div>
                  <span class="span-ms font-mono">{{ j.stages.authorizer_ms ?? 0 | number:'1.1-1' }} ms</span>
                </div>

                <div class="span-row">
                  <div class="span-info">
                    <span class="span-name">[6] Ledger Contábil</span>
                    <span class="span-component">Commit Distribuído ACID</span>
                  </div>
                  <div class="span-bar-container">
                    <div class="span-bar" style="background:#ec4899;" [style.width.%]="calcStagePct(j.stages.ledger_ms, j.total_ms)"></div>
                  </div>
                  <span class="span-ms font-mono">{{ j.stages.ledger_ms ?? 3 | number:'1.1-1' }} ms</span>
                </div>
              </div>

              <!-- Metadados Técnicos da Transação -->
              <div class="raw-meta">
                <div class="meta-field">
                  <span class="mf-label">Card Token:</span>
                  <span class="mf-val font-mono">{{ j.card_token }}</span>
                </div>
                <div class="meta-field">
                  <span class="mf-label">Attempt ID:</span>
                  <span class="mf-val font-mono">{{ j.attempt_id }}</span>
                </div>
                <div class="meta-field">
                  <span class="mf-label">Trace Provider:</span>
                  <span class="mf-val font-mono">OpenTelemetry / W3C TraceContext</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .waterfall-deck {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 20px;
    }

    .deck-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      flex-wrap: wrap;
      gap: 12px;
    }
    .deck-title {
      font-size: 13px;
      font-weight: 800;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }
    .deck-subtitle {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .buffer-badge {
      font-size: 10px;
      font-weight: 700;
      background: rgba(56, 189, 248, 0.15);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 2px 7px;
      border-radius: 4px;
    }
    .pause-badge {
      font-size: 10px;
      font-weight: 800;
      background: rgba(245, 158, 11, 0.2);
      color: #f59e0b;
      border: 1px solid rgba(245, 158, 11, 0.4);
      padding: 2px 7px;
      border-radius: 4px;
      animation: pulse 1.5s infinite;
    }

    .header-actions {
      display: flex;
      gap: 8px;
    }
    .btn-control {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--text-secondary);
      font-size: 11px;
      font-weight: 600;
      padding: 5px 12px;
      border-radius: 5px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-control:hover {
      background: rgba(30, 41, 59, 0.9);
      color: var(--text-primary);
      border-color: rgba(56, 189, 248, 0.4);
    }
    .btn-paused {
      background: rgba(245, 158, 11, 0.15) !important;
      border-color: #f59e0b !important;
      color: #f59e0b !important;
    }

    /* BARRA DE FILTROS */
    .filter-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      background: rgba(11, 17, 32, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 6px;
      padding: 8px 12px;
      margin-bottom: 10px;
      flex-wrap: wrap;
    }
    .filter-group {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .filter-lbl {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
    }
    .pill-group {
      display: flex;
      gap: 4px;
    }
    .pill-btn {
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: var(--text-secondary);
      font-size: 10px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s;
    }
    .pill-btn:hover {
      border-color: rgba(56, 189, 248, 0.3);
      color: var(--text-primary);
    }
    .pill-btn.active {
      background: rgba(56, 189, 248, 0.2);
      border-color: #38bdf8;
      color: #38bdf8;
    }
    .pill-crit.active {
      background: rgba(239, 68, 68, 0.2);
      border-color: #ef4444;
      color: #ef4444;
    }
    .pill-warn.active {
      background: rgba(245, 158, 11, 0.2);
      border-color: #f59e0b;
      color: #f59e0b;
    }
    .pill-ok.active {
      background: rgba(16, 185, 129, 0.2);
      border-color: #10b981;
      color: #10b981;
    }

    .search-box {
      display: flex;
      align-items: center;
      gap: 6px;
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 4px;
      padding: 2px 8px;
      flex: 0 1 240px;
    }
    .search-icon {
      font-size: 11px;
      color: var(--text-muted);
    }
    .search-input {
      background: transparent;
      border: none;
      outline: none;
      color: var(--text-primary);
      font-size: 11px;
      width: 100%;
      font-family: var(--font-mono);
    }
    .btn-clear-search {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      font-size: 10px;
    }

    /* LEGENDA */
    .waterfall-legend-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 10px;
      color: var(--text-muted);
      margin-bottom: 8px;
      flex-wrap: wrap;
      gap: 8px;
    }
    .legend-items {
      display: flex;
      gap: 10px;
    }
    .legend-items span {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .dot-bar {
      width: 10px;
      height: 5px;
      border-radius: 2px;
    }

    /* TABELA E VIEWPORT VIRTUAL */
    .table-wrapper {
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      overflow: hidden;
      background: #06080e;
    }
    .table-header-row {
      display: flex;
      align-items: center;
      background: rgba(15, 23, 42, 0.9);
      padding: 9px 12px;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--text-muted);
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      user-select: none;
    }

    .waterfall-viewport {
      height: 380px;
      width: 100%;
      overflow-y: auto;
    }

    .virtual-row {
      display: flex;
      align-items: center;
      height: 44px;
      padding: 0 12px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.03);
      cursor: pointer;
      transition: background 0.15s;
    }
    .virtual-row:hover {
      background: rgba(56, 189, 248, 0.06);
    }
    .row-selected {
      background: rgba(56, 189, 248, 0.15) !important;
      border-left: 3px solid #38bdf8;
    }

    /* LARGURAS DAS COLUNAS */
    .col-hora { flex: 0 0 75px; font-size: 11px; }
    .col-txid { flex: 0 0 150px; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .col-token { flex: 0 0 130px; }
    .col-valor { flex: 0 0 85px; font-size: 11px; }
    .col-status { flex: 0 0 115px; }
    .col-sla { flex: 0 0 140px; }
    .col-total { flex: 0 0 75px; font-size: 11px; }
    .col-waterfall { flex: 1 1 200px; min-width: 140px; }

    .font-mono { font-family: var(--font-mono); }
    .font-bold { font-weight: 700; }
    .text-muted { color: var(--text-muted); }
    .text-right { text-align: right; }
    .text-xs { font-size: 10px; }

    .badge-attempt {
      background: rgba(255, 255, 255, 0.06);
      padding: 1px 4px;
      border-radius: 3px;
      font-size: 9px;
    }

    .status-pill {
      font-size: 9px;
      font-weight: 800;
      padding: 2px 6px;
      border-radius: 4px;
      display: inline-block;
    }
    .pill-authorized {
      background: rgba(16, 185, 129, 0.2);
      color: #10b981;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .pill-declined {
      background: rgba(245, 158, 11, 0.2);
      color: #f59e0b;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .pill-timeout {
      background: rgba(239, 68, 68, 0.25);
      color: #ef4444;
      border: 1px solid rgba(239, 68, 68, 0.4);
      animation: pulse 1s infinite alternate;
    }

    .waterfall-bar-track {
      background: rgba(0, 0, 0, 0.4);
      height: 12px;
      border-radius: 3px;
      overflow: hidden;
      display: flex;
      width: 100%;
    }
    .stage-bar {
      height: 100%;
      min-width: 2px;
      transition: width 0.2s ease;
    }
    .bg-blue { background: #3b82f6; }
    .bg-cyan { background: #06b6d4; }
    .bg-amber { background: #eab308; }
    .bg-emerald { background: #10b981; }
    .bg-violet { background: #8b5cf6; }

    .empty-viewport {
      text-align: center;
      padding: 40px;
      color: var(--text-muted);
      font-size: 12px;
    }

    /* MODAL / DRAWER DE INSPEÇÃO */
    .drawer-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(4px);
      z-index: 1000;
      display: flex;
      justify-content: flex-end;
    }
    .trace-drawer {
      width: 580px;
      max-width: 90vw;
      height: 100%;
      background: #090d16;
      border-left: 1px solid rgba(56, 189, 248, 0.3);
      box-shadow: -10px 0 30px rgba(0, 0, 0, 0.8);
      display: flex;
      flex-direction: column;
      animation: slideInRight 0.25s ease-out;
    }
    .drawer-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(15, 23, 42, 0.6);
    }
    .drawer-pre {
      font-size: 10px;
      font-weight: 700;
      color: #38bdf8;
      letter-spacing: 0.5px;
    }
    .drawer-title {
      font-size: 16px;
      font-family: var(--font-mono);
      font-weight: 800;
      color: var(--text-primary);
      margin: 2px 0 0 0;
    }
    .btn-close-drawer {
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--text-secondary);
      font-size: 14px;
      width: 28px;
      height: 28px;
      border-radius: 6px;
      cursor: pointer;
    }
    .btn-close-drawer:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
    }

    .drawer-body {
      padding: 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .trace-summary-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .sum-card {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 6px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .sum-label {
      font-size: 10px;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 700;
    }
    .sum-val {
      font-size: 14px;
      font-weight: 700;
    }

    .rca-box {
      background: rgba(30, 58, 138, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 6px;
      padding: 12px;
    }
    .rca-badge {
      font-size: 9px;
      font-weight: 800;
      color: #38bdf8;
      letter-spacing: 0.5px;
    }
    .rca-text {
      font-size: 12px;
      color: #cbd5e1;
      margin: 4px 0 0 0;
      line-height: 1.5;
    }

    .spans-container {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.05);
      border-radius: 6px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .spans-title {
      font-size: 10px;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }
    .span-row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 6px 8px;
      border-radius: 4px;
      background: rgba(0, 0, 0, 0.2);
    }
    .span-highlight {
      border: 1px solid rgba(239, 68, 68, 0.4);
      background: rgba(239, 68, 68, 0.08);
    }
    .span-info {
      flex: 0 0 170px;
      display: flex;
      flex-direction: column;
    }
    .span-name {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-primary);
    }
    .span-component {
      font-size: 9px;
      color: var(--text-muted);
    }
    .span-bar-container {
      flex: 1;
      height: 10px;
      background: rgba(0, 0, 0, 0.4);
      border-radius: 2px;
      overflow: hidden;
    }
    .span-ms {
      flex: 0 0 65px;
      text-align: right;
      font-size: 11px;
      font-weight: 700;
    }

    .raw-meta {
      background: rgba(6, 8, 13, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.04);
      border-radius: 6px;
      padding: 10px 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 11px;
    }
    .meta-field {
      display: flex;
      gap: 8px;
    }
    .mf-label { color: var(--text-muted); width: 100px; }
    .mf-val { color: #94a3b8; }

    @keyframes slideInRight {
      from { transform: translateX(100%); }
      to { transform: translateX(0); }
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
  `]
})
export class JourneyWaterfallComponent {
  @ViewChild('scrollViewport') scrollViewport?: CdkVirtualScrollViewport;

  public store = inject(TelemetryStore);

  // Buffer cumulativo deslizante de alta capacidade (500 transações)
  public historyBuffer = signal<RecentJourney[]>([]);
  private seenIds = new Set<string>();
  private maxBufferSize = 500;

  // Estado de streaming e auto-scroll
  public isLiveStream = signal<boolean>(true);

  // Filtros Reativos
  public statusFilter = signal<string>('ALL');
  public minLatencyFilter = signal<number>(0);
  public searchQuery = signal<string>('');

  // Item Selecionado para Drawer
  public selectedJourney = signal<RecentJourney | null>(null);

  // Lista filtrada computada eficientemente com Signals
  public filteredJourneys = computed(() => {
    const list = this.historyBuffer();
    const st = this.statusFilter();
    const minLat = this.minLatencyFilter();
    const query = this.searchQuery().trim().toLowerCase();

    return list.filter(item => {
      // Filtro de status
      if (st !== 'ALL' && item.status !== st) return false;
      // Filtro de latência
      if (minLat > 0 && item.total_ms < minLat) return false;
      // Filtro de busca textual
      if (query && !item.tx_id.toLowerCase().includes(query) && !item.card_token.toLowerCase().includes(query)) {
        return false;
      }
      return true;
    });
  });

  constructor() {
    // Escuta novas transações a cada frame do WebSocket
    effect(() => {
      const incoming = this.store.recentJourneys();
      if (this.isLiveStream() && incoming && incoming.length > 0) {
        this.accumulateJourneys(incoming);
      }
    });
  }

  public trackByTx(index: number, item: RecentJourney): string {
    return item.tx_id + '_' + item.attempt_id;
  }

  private accumulateJourneys(incoming: RecentJourney[]): void {
    let added = false;
    const current = [...this.historyBuffer()];

    for (const item of incoming) {
      const key = item.tx_id + '_' + item.attempt_id;
      if (!this.seenIds.has(key)) {
        this.seenIds.add(key);
        current.unshift(item); // Mais recentes no topo
        added = true;
      }
    }

    if (added) {
      // Limita ao tamanho máximo do ring buffer
      if (current.length > this.maxBufferSize) {
        const trimmed = current.slice(0, this.maxBufferSize);
        // Limpa chaves removidas do set
        this.seenIds.clear();
        trimmed.forEach(t => this.seenIds.add(t.tx_id + '_' + t.attempt_id));
        this.historyBuffer.set(trimmed);
      } else {
        this.historyBuffer.set(current);
      }
    }
  }

  public toggleLiveStream(): void {
    this.isLiveStream.update(v => !v);
  }

  public clearBuffer(): void {
    this.seenIds.clear();
    this.historyBuffer.set([]);
    this.selectedJourney.set(null);
  }

  public setStatusFilter(status: string): void {
    this.statusFilter.set(status);
  }

  public setMinLatency(latencyMs: number): void {
    this.minLatencyFilter.set(latencyMs);
  }

  public countStatus(status: string): number {
    return this.historyBuffer().filter(j => j.status === status).length;
  }

  public selectJourney(journey: RecentJourney): void {
    this.selectedJourney.set(journey);
  }

  public closeDetail(): void {
    this.selectedJourney.set(null);
  }

  public calcStagePct(stageMs?: number, totalMs?: number): number {
    if (!stageMs || !totalMs || totalMs <= 0) return 0;
    return Math.min(100, Math.max(2, (stageMs / totalMs) * 100));
  }

  public getStatusPillClass(status: string): string {
    if (status === 'AUTHORIZED') return 'pill-authorized';
    if (status === 'DECLINED') return 'pill-declined';
    return 'pill-timeout';
  }

  public getRcaExplanation(j: RecentJourney): string {
    if (j.status === 'TIMEOUT_504') {
      const qMs = j.stages.antifraud_queue_ms ?? 0;
      const sMs = j.stages.antifraud_service_ms ?? 0;
      if (qMs > 300) {
        return `Ruptura catastrófica da Lei de Little: a requisição passou ${qMs.toFixed(0)}ms na fila de admissão aguardando vaga no pool antifraude, excedendo o timeout HTTP de 2.000ms.`;
      }
      return `Timeout de borda (504): o tempo total acumulado entre os 6 saltos atingiu ${(j.total_ms / 1000).toFixed(2)}s, superando o limite máximo de espera do cliente.`;
    }
    if (j.status === 'ACQUIRER_503') {
      return `Falha intermitente na adquirente externa: a rede Cielo/Stone retornou 503 com tempo de ${(j.stages.authorizer_ms ?? 0).toFixed(0)}ms. O cliente executou retries sucessivos provocando amplificação de carga.`;
    }
    if (j.status === 'DECLINED') {
      return `Recusa de negócio legítima: regras de limite ou score de fraude identificaram transação suspeita. Tempo de resposta normal (${j.total_ms.toFixed(0)}ms) sem impacto no SLA técnico.`;
    }
    return `Transação aprovada com sucesso e assentamento contábil estrito: todos os 6 hops executaram em ${j.total_ms.toFixed(0)}ms dentro da bacia estável de latência (P95 < 1.500ms).`;
  }
}
