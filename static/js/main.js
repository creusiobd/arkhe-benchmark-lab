/**
 * main.js - Orquestrador Principal do Cockpit ARKHÉ SENTINEL (ES6 Modular)
 * Conecta e coordena API, WebSocket, Gráficos Chart.js 4, Espaço de Fase e Topologia.
 */

import { fetchLiveTelemetry, toggleMitigationApi, triggerScenarioApi, resetSystemStateApi } from './api.js';
import { TelemetryStreamClient } from './websocket.js';
import { ChartEngine } from './charts.js';
import { PhaseSpaceRenderer } from './phase_space.js';
import { TopologyManager } from './topology.js';
import { WaterfallRenderer } from './waterfall.js';

class ArkheCockpitApp {
    constructor() {
        this.charts = new ChartEngine();
        this.phaseSpace = new PhaseSpaceRenderer('canvasPhaseSpace');
        this.topology = new TopologyManager();
        this.waterfall = new WaterfallRenderer('journey-tbody');
        this.wsClient = null;

        this.chartCounter = 0;
        this.fallbackTimer = null;
    }

    init() {
        // Inicializa subsistemas visuais
        this.charts.init();
        this.topology.init();

        // Expõe funções no window para compatibilidade com handlers onclick no HTML
        window.setScenario = (name) => this.handleSetScenario(name);
        window.toggleMitigation = () => this.handleToggleMitigation();
        window.selectTopoNode = (nodeId) => this.topology.selectNode(nodeId);

        // Inicializa cliente WebSocket
        this.wsClient = new TelemetryStreamClient({
            onMessage: (data) => this.renderTelemetryFrame(data),
            onStatusChange: (status) => this.updateWsStatus(status),
            onError: (err) => console.warn('Aviso WebSocket:', err)
        });

        this.wsClient.connect();

        // Fallback HTTP periódio se o WebSocket estiver desconectado
        this.fallbackTimer = setInterval(() => this.fallbackHttpPoll(), 1000);
    }

    updateWsStatus(statusInfo) {
        const badge = document.getElementById('ws-badge');
        const text = document.getElementById('ws-text');
        if (badge) badge.className = statusInfo.badgeClass;
        if (text) text.textContent = statusInfo.text;
    }

    async handleSetScenario(name) {
        document.querySelectorAll('.btn-scenario').forEach(b => b.classList.remove('active'));
        const btn = document.getElementById('btn-' + name);
        if (btn) btn.classList.add('active');

        if (name === 'recover') {
            await resetSystemStateApi();
            return;
        }

        const sentViaWs = this.wsClient.sendScenario(name);
        if (!sentViaWs) {
            await triggerScenarioApi(name);
        }
    }

    async handleToggleMitigation() {
        const sentViaWs = this.wsClient.sendToggleMitigation();
        if (!sentViaWs) {
            await toggleMitigationApi();
        }
    }

    updateMitigationButton(enabled) {
        const btn = document.getElementById('btn-toggle-mitigation');
        if (!btn) return;
        if (enabled) {
            btn.className = 'btn-mitigation-toggle enabled';
            btn.innerHTML = '⚡ Mitigação Autônoma: ATIVADA';
        } else {
            btn.className = 'btn-mitigation-toggle';
            btn.innerHTML = '⚡ Mitigação Autônoma: DESATIVADA';
        }
    }

    renderTelemetryFrame(d) {
        if (!d || !d.telemetry) return;

        // 1. Cenário Ativo & Mitigação
        const sc = d.scenario ? d.scenario.id : 'nominal';
        document.querySelectorAll('.btn-scenario').forEach(b => b.classList.remove('active'));
        const curBtn = document.getElementById('btn-' + sc);
        if (curBtn) curBtn.classList.add('active');

        this.updateMitigationButton(d.mitigation ? d.mitigation.enabled : false);

        // 2. Banner de Antecedência Operacional
        const ltSec = d.sentinel ? d.sentinel.lead_time_seconds : 0.0;
        const ltEl = document.getElementById('lead-time-counter');
        const ltDesc = document.getElementById('lead-status-desc');
        if (ltEl && ltDesc) {
            if (ltSec > 0) {
                ltEl.textContent = `+${ltSec.toFixed(1)}s`;
                ltDesc.innerHTML = `<strong style="color:#60a5fa;">ARKHÉ ANTECIPOU O SRE EM ${ltSec.toFixed(1)} SEGUNDOS!</strong> Mitigação autônoma ativada no minuto zero do Drift.`;
            } else {
                ltEl.textContent = '+0.0s';
                ltDesc.textContent = 'Aguardando divergência de sinais de trajetória nos 6 saltos...';
            }
        }

        // 3. Painel do Agente Atuador Autônomo
        const mit = d.mitigation || {};
        const mitBadge = document.getElementById('mitigation-status-badge');
        const mitDesc = document.getElementById('mitigation-action-desc');
        const mitPoolCap = document.getElementById('mit-pool-cap');
        const mitPrevented = document.getElementById('mit-prevented-count');
        const mitDowntime = document.getElementById('mit-downtime-saved');

        if (mit.active) {
            if (mitBadge) {
                mitBadge.style.background = 'rgba(16, 185, 129, 0.25)';
                mitBadge.style.color = 'var(--green-glow)';
                mitBadge.style.borderColor = 'var(--green-glow)';
                mitBadge.textContent = 'CLOSED-LOOP ATIVO (AUTO-CURA EM CURSO)';
            }
            if (mitDesc) {
                const acts = (mit.actions || []).map(a => `<span style="color:#60a5fa;">[${a.action}]</span> ${a.detail}`).join('<br>');
                mitDesc.innerHTML = acts || 'Fast-Path ativado + Expansão elástica do pool.';
            }
        } else {
            if (mitBadge) {
                mitBadge.style.background = 'rgba(148, 163, 184, 0.2)';
                mitBadge.style.color = '#cbd5e1';
                mitBadge.style.borderColor = '#475569';
                mitBadge.textContent = mit.enabled ? 'STANDBY (MONITORANDO DERIVADA)' : 'DESATIVADO PELO OPERADOR';
            }
            if (mitDesc) {
                mitDesc.textContent = 'Nenhuma anomalia crítica de saturação detectada.';
            }
        }
        if (mitPoolCap) mitPoolCap.textContent = `${mit.pool_capacity || 30} slots`;
        if (mitPrevented) mitPrevented.textContent = `${mit.prevented_failures || 0} falhas`;
        if (mitDowntime) mitDowntime.textContent = `${(mit.downtime_avoided_min || 0.0).toFixed(1)} min`;

        // 4. SRE Error Budget & Burn Rate
        const gov = d.sre_governance || {};
        const sliAvail = document.getElementById('sli-availability');
        const errBudget = document.getElementById('error-budget');
        const burnRate = document.getElementById('burn-rate');
        const burnBadge = document.getElementById('burn-status-badge');

        if (sliAvail) sliAvail.textContent = `${(gov.current_sli_availability_pct || 100).toFixed(2)}%`;
        if (errBudget) {
            errBudget.textContent = `${(gov.error_budget_remaining_pct || 100).toFixed(1)}%`;
            errBudget.style.color = gov.error_budget_remaining_pct > 50 ? 'var(--green-glow)' : (gov.error_budget_remaining_pct > 10 ? 'var(--yellow)' : 'var(--red-glow)');
        }
        if (burnRate) burnRate.textContent = `${(gov.burn_rate || 0).toFixed(2)}x`;
        if (burnBadge) {
            burnBadge.textContent = gov.burn_rate_status || 'NORMAL (0.0x)';
            burnBadge.style.background = (gov.burn_rate || 0) > 14.4 ? 'rgba(239, 68, 68, 0.25)' : ((gov.burn_rate || 0) > 1.0 ? 'rgba(234, 179, 8, 0.25)' : 'rgba(34, 197, 94, 0.25)');
            burnBadge.style.color = (gov.burn_rate || 0) > 14.4 ? 'var(--red-glow)' : ((gov.burn_rate || 0) > 1.0 ? 'var(--yellow)' : 'var(--green-glow)');
        }

        // 5. KPIs Principais
        const score = d.sentinel ? d.sentinel.score : 0.0;
        const scoreEl = document.getElementById('kpi-score');
        const badgeEl = document.getElementById('kpi-score-badge');
        const barScore = document.getElementById('bar-score');

        if (scoreEl) scoreEl.textContent = `${score.toFixed(1)} / 100`;
        if (badgeEl) badgeEl.textContent = (d.sentinel ? d.sentinel.level : 'healthy').toUpperCase();
        if (barScore) {
            barScore.style.width = Math.min(100, score) + '%';
            if (score < 50) {
                if (scoreEl) scoreEl.style.color = 'var(--green-glow)';
                if (badgeEl) badgeEl.className = 'status-badge badge-healthy';
                barScore.style.background = 'var(--green-glow)';
            } else if (score < 75) {
                if (scoreEl) scoreEl.style.color = 'var(--yellow)';
                if (badgeEl) badgeEl.className = 'status-badge badge-warning';
                barScore.style.background = 'var(--yellow)';
            } else {
                if (scoreEl) scoreEl.style.color = 'var(--red-glow)';
                if (badgeEl) badgeEl.className = 'status-badge badge-danger';
                barScore.style.background = 'var(--red-glow)';
            }
        }

        const resources = d.telemetry.resources || {};
        const used = resources.antifraud_pool_in_use || 0;
        const cap = resources.antifraud_pool_capacity || 30;
        const pct = (used / Math.max(1, cap)) * 100;

        const kpiPool = document.getElementById('kpi-pool');
        const kpiPoolSub = document.getElementById('kpi-pool-sub');
        const barPool = document.getElementById('bar-pool');
        if (kpiPool) kpiPool.textContent = `${used} / ${cap}`;
        if (kpiPoolSub) kpiPoolSub.textContent = `${pct.toFixed(1)}% de ocupação`;
        if (barPool) {
            barPool.style.width = pct + '%';
            barPool.style.background = pct > 80 ? 'var(--red-glow)' : (pct > 50 ? 'var(--yellow)' : 'var(--arkhe-blue)');
        }

        const traffic = d.telemetry.traffic || {};
        const kpiTraffic = document.getElementById('kpi-traffic');
        const kpiTrafficSub = document.getElementById('kpi-traffic-sub');
        if (kpiTraffic) kpiTraffic.textContent = `${traffic.unique_transactions_total || 0} tx`;
        if (kpiTrafficSub) kpiTrafficSub.textContent = `${traffic.attempts_total || 0} tentativas (R_retry: ${traffic.retry_amplification_ratio || 1.0})`;

        const latencies = d.telemetry.latency_ms || {};
        const kpiP95 = document.getElementById('kpi-p95');
        const kpiWaiters = document.getElementById('kpi-waiters');
        if (kpiP95) kpiP95.textContent = `${(latencies.p95 || 0).toFixed(1)} ms`;
        if (kpiWaiters) kpiWaiters.textContent = `${resources.antifraud_waiters_count || 0} conexões em fila física`;

        // 6. Comparação ARKHÉ vs SRE Clássico
        const detBadge = document.getElementById('sentinel-det-badge');
        const sentinelReason = document.getElementById('sentinel-reason');
        if (detBadge && sentinelReason) {
            if (d.sentinel && d.sentinel.triggered) {
                detBadge.className = 'status-badge badge-warning';
                detBadge.textContent = 'ANOMALIA DETECTADA (ANTECIPADO)';
                sentinelReason.textContent = d.sentinel.trigger_reason;
            } else {
                detBadge.className = 'status-badge badge-healthy';
                detBadge.textContent = 'NOMINAL';
                sentinelReason.textContent = 'Operação estável sem anomalias estruturais.';
            }
        }

        const sreBadge = document.getElementById('sre-badge');
        if (sreBadge) {
            if (gov.traditional_alert_triggered) {
                sreBadge.className = 'status-badge badge-danger';
                sreBadge.textContent = 'ALARME SRE DISPARADO (PÓS-IMPACTO)';
            } else {
                sreBadge.className = 'status-badge badge-healthy';
                sreBadge.textContent = 'EM SILÊNCIO (0 ALARMES)';
            }
        }

        // 7. Atualização do Grafo Topológico Interativo (6 Hops)
        this.topology.update(d.topology);

        // 8. Horizonte Preditivo com Cone de Incerteza Estocástica
        if (d.projection) {
            const proj = d.projection;
            const rhoValEl = document.getElementById('hz-rho-val');
            const drhoValEl = document.getElementById('hz-drho-val');
            const colValEl = document.getElementById('hz-collapse-val');
            const statBadgeEl = document.getElementById('hz-status-badge');

            if (rhoValEl) rhoValEl.textContent = `${(proj.current_rho * 100).toFixed(1)}%`;
            if (drhoValEl) {
                const sgn = proj.d_rho_dt_per_min >= 0 ? '+' : '';
                drhoValEl.textContent = `${sgn}${proj.d_rho_dt_per_min.toFixed(2)}/min`;
                drhoValEl.style.color = proj.d_rho_dt_per_min > 5 ? 'var(--red-glow)' : (proj.d_rho_dt_per_min > 0 ? 'var(--yellow)' : 'var(--green-glow)');
            }
            if (colValEl) colValEl.textContent = proj.time_to_collapse_display || 'ESTÁVEL';
            if (statBadgeEl) {
                if (proj.collapse_status === 'CRITICAL') {
                    if (colValEl) colValEl.style.color = 'var(--red-glow)';
                    statBadgeEl.textContent = 'RUPTURA IMINENTE';
                    statBadgeEl.style.color = 'var(--red-glow)';
                } else if (proj.collapse_status === 'WARNING') {
                    if (colValEl) colValEl.style.color = 'var(--yellow)';
                    statBadgeEl.textContent = 'DERIVA ACELERADA';
                    statBadgeEl.style.color = 'var(--yellow)';
                } else {
                    if (colValEl) colValEl.style.color = 'var(--green-glow)';
                    statBadgeEl.textContent = 'BACIA ESTÁVEL';
                    statBadgeEl.style.color = 'var(--green-glow)';
                }
            }

            // Amostragem nos gráficos Chart.js 4 a cada 10 frames (~500ms a 20 FPS para máxima fluidez e baixo consumo de CPU)
            if (this.chartCounter % 10 === 0) {
                this.charts.updateHorizon(proj);
            }
        }

        // 9. Atualização dos Gráficos de Métricas
        this.chartCounter++;
        if (this.chartCounter % 10 === 0) {
            this.charts.updateMetrics(latencies.p95 || 0, used, cap);
        }

        // 10. Espaço de Fase 2D a 20 FPS
        const rho = resources.antifraud_pool_utilization_ratio || 0.0;
        const wq_ws = (d.telemetry.queueing ? d.telemetry.queueing.wq_ws_ratio : 0.0) || 0.0;
        const isMitActive = mit.active || false;
        this.phaseSpace.draw(rho, wq_ws, isMitActive);

        // 11. Tabela Waterfall de Trajetórias
        this.waterfall.render(d.recent_journeys || []);

        // 12. Logs de Auditoria
        const logCont = document.getElementById('logs-container');
        if (logCont) {
            logCont.innerHTML = '';
            (d.event_logs || []).slice(0, 8).forEach(l => {
                const div = document.createElement('div');
                div.className = 'log-item';
                div.innerHTML = `<span class="log-time">[${l.timestamp}]</span> <span>${l.message}</span>`;
                logCont.appendChild(div);
            });
        }
    }

    async fallbackHttpPoll() {
        if (!this.wsClient || !this.wsClient.isConnected) {
            try {
                const data = await fetchLiveTelemetry();
                this.renderTelemetryFrame(data);
            } catch (e) {
                // Silencioso em fallback
            }
        }
    }
}

// Inicializa a aplicação ao carregar o DOM
window.addEventListener('DOMContentLoaded', () => {
    const app = new ArkheCockpitApp();
    app.init();
});
