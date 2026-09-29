import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TelemetryStore } from '../../core/state/telemetry.store';
import { TopologyNode } from '../../core/models/telemetry.model';

interface NodeExplanation {
  title: string;
  role: string;
  desc: string;
  formula: string;
}

@Component({
  selector: 'arkhe-topology-graph',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="topology-deck">
      <div class="topology-header">
        <div>
          <div class="topo-title">
            <span>🌐 GRAFO TOPOLÓGICO DE CONCORRÊNCIA E FLUXO (6 HOPS ARQUITETURAIS)</span>
            <span class="status-badge badge-healthy">DAG AO VIVO (20 FPS)</span>
          </div>
          <div class="topo-subtitle">
            Rastreamento topológico de propagação de gargalos, latências e saturação da Lei de Little
          </div>
        </div>
        <div class="topo-legend">
          <span class="leg-item"><span class="dot dot-healthy"></span> Nominal</span>
          <span class="leg-item"><span class="dot dot-warning"></span> Fila / Drift</span>
          <span class="leg-item"><span class="dot dot-critical"></span> Saturação</span>
          <span class="leg-item"><span class="dot dot-mitigated"></span> Auto-Cura</span>
        </div>
      </div>

      <!-- 6 Hops Sequenciais e 5 Conectores com Pulsos de Fluxo -->
      <div class="topo-flow-container">
        @for (node of store.topologyNodes(); track node.id; let idx = $index; let last = $last) {
          <!-- Nó Topológico -->
          <div 
            class="topo-node" 
            [ngClass]="['node-' + node.status, selectedNodeId() === node.id ? 'node-selected' : '']"
            (click)="selectNode(node.id)">
            
            <div class="node-header">
              <span class="node-step">[{{ idx + 1 }}] {{ getStepTag(node.id) }}</span>
              <span class="status-pill" [ngClass]="'pill-' + node.status">
                {{ node.status | uppercase }}
              </span>
            </div>

            <div class="node-main">
              <span class="node-icon">{{ node.icon }}</span>
              <div class="node-info">
                <span class="node-label">{{ node.label }}</span>
                <span class="node-role">{{ node.role }}</span>
              </div>
            </div>

            <div class="node-metrics">
              <div class="metric-row">
                <span>Latência:</span>
                <strong>{{ node.latency_ms | number:'1.1-1' }} ms</strong>
              </div>
              <div class="metric-row">
                <span>Carga:</span>
                <strong>{{ node.load }}</strong>
              </div>
            </div>
          </div>

          <!-- Conector com animação de fluxo entre nós -->
          @if (!last) {
            <div class="topo-edge">
              <div class="edge-line">
                <span class="flow-particle" [ngClass]="'flow-' + node.status"></span>
              </div>
              <span class="edge-badge">120 TPS ➔</span>
            </div>
          }
        }
      </div>

      <!-- Barra de Inspeção Detalhada do Nó Selecionado -->
      <div class="inspector-bar">
        <div class="inspector-info">
          <span class="inspector-title">{{ currentExplanation.title }}</span>
          <span class="inspector-desc">{{ currentExplanation.desc }}</span>
        </div>
        <div class="inspector-formula">
          <code>{{ currentExplanation.formula }}</code>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .topology-deck {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 20px;
    }
    .topology-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 10px;
    }
    .topo-title {
      font-size: 13px;
      font-weight: 800;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .topo-subtitle {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .topo-legend {
      display: flex;
      gap: 12px;
      font-size: 11px;
      color: var(--text-secondary);
    }
    .leg-item {
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
    }
    .dot-healthy { background: #10b981; }
    .dot-warning { background: #f59e0b; }
    .dot-critical { background: #ef4444; }
    .dot-mitigated { background: #38bdf8; }

    .status-badge {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 4px;
    }
    .badge-healthy {
      background: rgba(16, 185, 129, 0.15);
      color: #10b981;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }

    /* Fluxo Sequencial dos 6 Nós */
    .topo-flow-container {
      display: flex;
      align-items: center;
      gap: 8px;
      overflow-x: auto;
      padding-bottom: 10px;
      margin-bottom: 14px;
    }

    .topo-node {
      flex: 1 0 170px;
      min-width: 170px;
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      padding: 10px;
      cursor: pointer;
      transition: all 0.2s ease;
      position: relative;
    }
    .topo-node:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }
    .node-selected {
      border-color: #38bdf8 !important;
      box-shadow: 0 0 14px rgba(56, 189, 248, 0.35) !important;
    }

    .node-healthy { border-top: 3px solid #10b981; }
    .node-warning { border-top: 3px solid #f59e0b; }
    .node-critical { border-top: 3px solid #ef4444; }
    .node-mitigated { border-top: 3px solid #38bdf8; }

    .node-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }
    .node-step {
      font-size: 9px;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.5px;
    }
    .status-pill {
      font-size: 8px;
      font-weight: 800;
      padding: 1px 5px;
      border-radius: 3px;
    }
    .pill-healthy { background: rgba(16, 185, 129, 0.2); color: #10b981; }
    .pill-warning { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
    .pill-critical { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
    .pill-mitigated { background: rgba(56, 189, 248, 0.2); color: #38bdf8; }

    .node-main {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }
    .node-icon {
      font-size: 18px;
    }
    .node-info {
      display: flex;
      flex-direction: column;
    }
    .node-label {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-primary);
    }
    .node-role {
      font-size: 9px;
      color: var(--text-muted);
    }

    .node-metrics {
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      padding-top: 6px;
      font-size: 10px;
    }
    .metric-row {
      display: flex;
      justify-content: space-between;
      color: var(--text-secondary);
      margin-bottom: 2px;
    }
    .metric-row strong {
      font-family: var(--font-mono);
      color: var(--text-primary);
    }

    /* Conectores e Pulsos de Fluxo */
    .topo-edge {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      flex: 0 0 45px;
      position: relative;
    }
    .edge-line {
      width: 100%;
      height: 2px;
      background: rgba(255, 255, 255, 0.12);
      position: relative;
      overflow: hidden;
    }
    .flow-particle {
      position: absolute;
      top: -2px;
      left: 0;
      width: 12px;
      height: 6px;
      border-radius: 3px;
      animation: flowAcross 1.2s infinite linear;
    }
    .flow-healthy { background: #10b981; box-shadow: 0 0 6px #10b981; }
    .flow-warning { background: #f59e0b; box-shadow: 0 0 6px #f59e0b; }
    .flow-critical { background: #ef4444; box-shadow: 0 0 6px #ef4444; }
    .flow-mitigated { background: #38bdf8; box-shadow: 0 0 6px #38bdf8; }

    .edge-badge {
      font-size: 8px;
      font-family: var(--font-mono);
      color: var(--text-muted);
      margin-top: 4px;
      white-space: nowrap;
    }

    @keyframes flowAcross {
      0% { left: -20%; opacity: 0; }
      20% { opacity: 1; }
      80% { opacity: 1; }
      100% { left: 110%; opacity: 0; }
    }

    /* Barra de Inspeção */
    .inspector-bar {
      background: rgba(11, 17, 32, 0.8);
      border: 1px solid rgba(56, 189, 248, 0.2);
      border-radius: 6px;
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }
    .inspector-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .inspector-title {
      font-size: 12px;
      font-weight: 700;
      color: #38bdf8;
    }
    .inspector-desc {
      font-size: 11px;
      color: var(--text-secondary);
    }
    .inspector-formula code {
      font-family: var(--font-mono);
      font-size: 11px;
      color: #a5b4fc;
      background: rgba(19, 29, 49, 0.9);
      padding: 4px 10px;
      border-radius: 4px;
      border: 1px solid rgba(165, 180, 252, 0.2);
      white-space: nowrap;
    }
  `]
})
export class TopologyGraphComponent {
  public store = inject(TelemetryStore);
  public selectedNodeId = signal<string>('antifraud');

  private explanations: Record<string, NodeExplanation> = {
    'gateway': {
      title: '🌐 Hop 1: Gateway de Ingestão (Envoy / Reverse Proxy)',
      role: 'Ingress Controller & Rate Limiter',
      desc: 'Porta de entrada HTTP/2 para transações de cartão de crédito. Despacha requisições a 120 TPS.',
      formula: 'Taxa de Chegada: λ = 120 req/s | Latência de Ingress: ~8.0ms'
    },
    'hsm_limits': {
      title: '🔐 Hop 2: HSM & Checagem de Limites Cadastrais',
      role: 'Criptografia EMV Pin-Block & Cache Redis',
      desc: 'Validação criptográfica do chip/token e checagem de limites. Vulnerável à contenção de CPU de criptografia.',
      formula: 'T_hsm = T_base + Δ_cripto | Carga: 120 validações/s'
    },
    'semaphore': {
      title: '⏳ Hop 3: Portão de Concorrência & Fila de Little',
      role: 'Semáforo Assíncrono Adaptativo',
      desc: 'Controlador de admissão limitando a concorrência no Antifraude. Quando W_s cresce, a fila explode.',
      formula: 'Lei de Little: L_q = λ * W_q | Razão de Estabilidade: W_q / W_s < 0.25'
    },
    'antifraud': {
      title: '🧠 Hop 4: Pool de Inteligência Antifraude (Cluster IA)',
      role: 'Microserviço de Machine Learning / Scoring',
      desc: 'Gargalo primário do sistema. Quando sofre drift de 45ms para 255ms+, rompe a capacidade de 30 slots.',
      formula: 'Utilização: ρ = (λ * W_s) / C | Ruptura quando ρ >= 1.0 (Demanda > 30 slots)'
    },
    'acquirer': {
      title: '🏛️ Hop 5: Conector com Adquirentes Externas',
      role: 'Redes Cielo, Stone, Rede & Bandeiras',
      desc: 'Comunicação síncrona com redes bancárias externas. Sujeito a flapping e indisponibilidades parciais.',
      formula: 'P_erro = Flapping% | Amplificação de Retries: λ_eff = λ / (1 - P_erro)'
    },
    'ledger': {
      title: '📒 Hop 6: Ledger Contábil Distribuído',
      role: 'Assentamento Transacional ACID',
      desc: 'Escrita de confirmação de saldo e conciliação em banco distribuído. Finaliza a jornada do pagamento.',
      formula: 'Commit Latency: ~3.0ms | Garantia: Strict Serializability ACID'
    }
  };

  public get currentExplanation(): NodeExplanation {
    return this.explanations[this.selectedNodeId()] || this.explanations['antifraud'];
  }

  public selectNode(nodeId: string): void {
    this.selectedNodeId.set(nodeId);
  }

  public getStepTag(nodeId: string): string {
    const tags: Record<string, string> = {
      'gateway': 'INGESTÃO',
      'hsm_limits': 'SEGURANÇA',
      'semaphore': 'CONCORRÊNCIA',
      'antifraud': 'INTELIGÊNCIA',
      'acquirer': 'BANDEIRAS',
      'ledger': 'ASSENTAMENTO'
    };
    return tags[nodeId] || 'ETAPA';
  }
}
