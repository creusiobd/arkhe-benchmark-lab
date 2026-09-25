/**
 * waterfall.js - Câmara de Trajetórias Transacionais ao Vivo (Waterfall Stream)
 * Renderiza em tabela HTML o desdobramento milissegundo a milissegundo de cada transação.
 */

export class WaterfallRenderer {
    constructor(tbodyId) {
        this.tbody = document.getElementById(tbodyId);
        this.lastRenderedTxId = null;
    }

    render(journeys) {
        if (!this.tbody || !journeys || journeys.length === 0) return;

        // Evita re-renderizações desnecessárias se os dados não mudaram
        if (journeys[0].tx_id === this.lastRenderedTxId) {
            return;
        }
        this.lastRenderedTxId = journeys[0].tx_id;

        this.tbody.innerHTML = '';

        journeys.forEach(j => {
            const tr = document.createElement('tr');
            tr.className = 'journey-row';

            let pillClass = 'pill-authorized';
            let slaBadge = '<span style="color:var(--green-glow);">🟢 Neutro (SLA Preservado)</span>';

            if (j.status === 'TIMEOUT_504' || j.status === 'POOL_SATURATED_503') {
                pillClass = 'pill-timeout';
                slaBadge = '<span style="color:var(--red-glow); font-weight:bold;">🔴 Queimou Budget (-1)</span>';
            } else if (j.status === 'ACQUIRER_ERROR_503') {
                pillClass = 'pill-timeout';
                slaBadge = '<span style="color:var(--yellow); font-weight:bold;">🟡 Retry Amplificado</span>';
            }

            const st = j.stages || {};
            const totalMs = Math.max(1.0, j.total_ms || 1.0);
            const pIngest = ((st.ingest_ms || 0) / totalMs) * 100;
            const pLimits = ((st.limits_ms || 0) / totalMs) * 100;
            const pQueue = ((st.antifraud_queue_ms || 0) / totalMs) * 100;
            const pAntifraud = ((st.antifraud_service_ms || 0) / totalMs) * 100;
            const pAuth = ((st.authorizer_ms || 0) / totalMs) * 100;
            const pLedger = ((st.ledger_ms || 0) / totalMs) * 100;

            const isPoolSat = j.status === 'POOL_SATURATED_503';
            const isTimeout = j.status === 'TIMEOUT_504';
            const queueColorClass = isPoolSat ? 'w-failed' : '';
            const afColorClass = isTimeout ? 'w-failed' : '';

            tr.innerHTML = `
                <td style="font-family:monospace; color:var(--text-muted); font-size:11px;">${j.timestamp || '--:--:--'}</td>
                <td><strong style="color:#e2e8f0; font-family:monospace; font-size:11px;">${j.tx_id}</strong></td>
                <td>R$ ${(j.amount_brl || 0).toFixed(2)}</td>
                <td><span class="status-pill ${pillClass}">${j.status}</span></td>
                <td>${slaBadge}</td>
                <td><strong style="color:var(--text-main); font-size:12px;">${totalMs.toFixed(1)}ms</strong></td>
                <td style="width: 38%;">
                    <div class="waterfall-track">
                        ${pIngest > 0.5 ? `<div class="w-stage w-ingest" style="width: ${pIngest}%"></div>` : ''}
                        ${pLimits > 0.5 ? `<div class="w-stage w-limits" style="width: ${pLimits}%"></div>` : ''}
                        ${pQueue > 0.5 ? `<div class="w-stage w-queue ${queueColorClass}" style="width: ${pQueue}%">${st.antifraud_queue_ms > 20 ? st.antifraud_queue_ms.toFixed(0) + 'ms' : ''}</div>` : ''}
                        <div class="w-stage w-antifraud ${afColorClass}" style="width: ${pAntifraud}%;">${st.antifraud_service_ms > 50 ? st.antifraud_service_ms.toFixed(0) + 'ms' : ''}</div>
                        ${pAuth > 0.5 ? `<div class="w-stage w-authorizer" style="width: ${pAuth}%">${st.authorizer_ms > 50 ? st.authorizer_ms.toFixed(0) + 'ms' : ''}</div>` : ''}
                        ${pLedger > 0.5 ? `<div class="w-stage w-ledger" style="width: ${pLedger}%"></div>` : ''}
                    </div>
                </td>
            `;
            this.tbody.appendChild(tr);
        });
    }
}
