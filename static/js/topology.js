/**
 * topology.js - Gerenciador do Grafo Topológico Interativo (DAG dos 6 Hops)
 * Atualiza nós, conectores com fluxo de partículas a 120 TPS e inspetor arquitetural.
 */

export const NODE_DESCRIPTIONS = {
    "gateway": {
        "title": "🌐 Hop 1: Gateway de Ingestão (Envoy / API Ingress)",
        "desc": "Ponto de entrada único HTTP/2 & gRPC. Executa buffer de requisições, terminação TLS e roteamento não-bloqueante para a malha interna.",
        "formula": "Taxa de Chegada: λ = 120 TPS nominais | Event Loop Lag < 1ms"
    },
    "hsm_limits": {
        "title": "🔐 Hop 2: Validação Criptográfica HSM & Limites de Cartão",
        "desc": "Descriptografia do Pin-Block e validação do CVC/CVV via Hardware Security Module (HSM). Em saturação, gera contenção severa de CPU criptográfica.",
        "formula": "Custo Cripto: T_crypto = 8ms + Contenção CPU HSM | Chaves EMV ZMK/PVK"
    },
    "semaphore": {
        "title": "⏳ Hop 3: Fila Little & Semáforo Físico de Concorrência",
        "desc": "Portão de admissão baseado na Lei de Little. Quando a demanda excede a capacidade do pool, retém conexões e gera fila física exponencial.",
        "formula": "Lei de Little: L_q = λ * W_q | Equação de Kingman: W_q ≈ (ρ / (1 - ρ)) * W_s"
    },
    "antifraud": {
        "title": "🧠 Hop 4: Pool de Inteligência Antifraude (Cluster IA)",
        "desc": "Execução de modelos preditivos de detecção de fraude e risco. O gatilho primário do colapso de Little ocorre quando sua latência de serviço sofre drift silencioso.",
        "formula": "Utilização: ρ = (λ * W_s) / C | Demanda Little: L(t) = λ(t) * W_s(t)"
    },
    "acquirer": {
        "title": "🏛️ Hop 5: Adquirente Externa (Bandeiras Cielo / Stone / Rede)",
        "desc": "Conexão externa síncrona com os adquirentes e emissores de cartão. Sujeito a flapping de rede, jitter assimétrico na cauda P99 e retries tempestuosos.",
        "formula": "Cauda Longa: P99 Jitter Outlier (1.200ms) | Retries: R_retry = Tentativas / Tx_Unicas"
    },
    "ledger": {
        "title": "📒 Hop 6: Ledger Contábil e Assentamento Financeiro",
        "desc": "Finalização da transação com garantia estrita de ACID distribuído e idempotência no banco de dados contábil.",
        "formula": "Compromisso Distribuído: T_ledger = 3ms fixos | Idempotência: x-transaction-id"
    }
};

export class TopologyManager {
    constructor() {
        this.selectedNodeId = 'antifraud';
    }

    init() {
        this.selectNode(this.selectedNodeId);
    }

    selectNode(nodeId) {
        this.selectedNodeId = nodeId;
        document.querySelectorAll('.topo-node').forEach(el => el.classList.remove('active-selected'));
        const targetNode = document.getElementById('node-' + nodeId);
        if (targetNode) {
            targetNode.classList.add('active-selected');
        }

        const info = NODE_DESCRIPTIONS[nodeId];
        if (info) {
            const titleEl = document.getElementById('inspector-title');
            const descEl = document.getElementById('inspector-desc');
            const formulaEl = document.getElementById('inspector-formula');
            if (titleEl) titleEl.textContent = info.title;
            if (descEl) descEl.textContent = info.desc;
            if (formulaEl) formulaEl.textContent = info.formula;
        }
    }

    update(topologyData) {
        if (!topologyData) return;

        // Atualização dos 6 Nós
        if (topologyData.nodes) {
            topologyData.nodes.forEach(n => {
                const nodeEl = document.getElementById('node-' + n.id);
                const pillEl = document.getElementById('pill-' + n.id);
                const latEl = document.getElementById('topo-lat-' + n.id);
                const loadEl = document.getElementById('topo-load-' + n.id);

                if (nodeEl && pillEl && latEl && loadEl) {
                    latEl.textContent = n.latency_ms.toFixed(1) + ' ms';
                    loadEl.textContent = n.load;

                    // Atualiza classes visuais
                    nodeEl.className = 'topo-node node-' + n.status + (n.id === this.selectedNodeId ? ' active-selected' : '');
                    pillEl.className = 'node-status-pill pill-' + n.status;
                    pillEl.textContent = n.status.toUpperCase();
                }
            });
        }

        // Atualização dos 5 Conectores (Edges)
        if (topologyData.edges) {
            topologyData.edges.forEach((edge, idx) => {
                const edgeEl = document.getElementById('edge-' + idx);
                const tpsBadgeEl = document.getElementById('edge-tps-' + idx);
                if (edgeEl && tpsBadgeEl) {
                    edgeEl.className = 'topo-edge edge-' + edge.status;
                    tpsBadgeEl.textContent = `${edge.tps} TPS ➔`;
                }
            });
        }
    }
}
