/**
 * charts.js - Motor de Gráficos em Tempo Real com Chart.js 4
 * Gerencia:
 * 1. Gráfico de Horizonte Preditivo com Cone de Incerteza Estocástica a 95%
 * 2. Gráfico de Latência P95 vs Limiar SRE (1.500 ms)
 * 3. Gráfico de Saturação do Pool Antifraude vs Capacidade
 */

export class ChartEngine {
    constructor() {
        this.chartHorizon = null;
        this.chartLatency = null;
        this.chartPool = null;
        this.maxMetricsPoints = 30;
    }

    init() {
        this._applyChartDefaults();
        this._initHorizonChart();
        this._initLatencyChart();
        this._initPoolChart();
    }

    _applyChartDefaults() {
        if (!window.Chart) {
            console.error('Chart.js 4 não foi carregado!');
            return;
        }

        // Configurações globais de tema escuro para Chart.js 4
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.borderColor = '#1e293b';
        Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    }

    _initHorizonChart() {
        const ctx = document.getElementById('chartHorizon');
        if (!ctx) return;

        const horizonLabels = ['-20s', '-15s', '-10s', '-5s', 'Agora', '+30s', '+1.0m', '+1.5m', '+2.0m', '+3.0m', '+4.0m', '+5.0m'];

        this.chartHorizon = new Chart(ctx, {
            type: 'line',
            data: {
                labels: horizonLabels,
                datasets: [
                    {
                        label: 'Limite Superior (95%)',
                        data: Array(12).fill(null),
                        borderColor: 'transparent',
                        backgroundColor: 'rgba(239, 68, 68, 0.12)',
                        fill: '+1',
                        pointRadius: 0,
                        tension: 0.25
                    },
                    {
                        label: 'Limite Inferior (95%)',
                        data: Array(12).fill(null),
                        borderColor: 'transparent',
                        backgroundColor: 'transparent',
                        fill: false,
                        pointRadius: 0,
                        tension: 0.25
                    },
                    {
                        label: 'Histórico Observado',
                        data: Array(12).fill(null),
                        borderColor: '#38bdf8',
                        backgroundColor: '#38bdf8',
                        borderWidth: 2.5,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        tension: 0.2
                    },
                    {
                        label: 'Projeção (Sem Mitigação)',
                        data: Array(12).fill(null),
                        borderColor: '#f43f5e',
                        borderDash: [5, 4],
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.25
                    },
                    {
                        label: 'Projeção (Com Mitigação Closed-Loop)',
                        data: Array(12).fill(null),
                        borderColor: '#22c55e',
                        borderDash: [4, 4],
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderWidth: 1,
                        callbacks: {
                            label: function(ctx) {
                                if (ctx.raw === null || ctx.raw === undefined) return null;
                                return `${ctx.dataset.label}: ${(ctx.raw * 100).toFixed(1)}%`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        min: 0,
                        max: 1.0,
                        ticks: {
                            callback: (v) => `${(v * 100).toFixed(0)}%`,
                            stepSize: 0.25
                        },
                        grid: { color: 'rgba(30, 41, 59, 0.6)' }
                    },
                    x: {
                        grid: { color: 'rgba(30, 41, 59, 0.4)' }
                    }
                }
            }
        });
    }

    _initLatencyChart() {
        const ctx = document.getElementById('chartLatency');
        if (!ctx) return;

        this.chartLatency = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(this.maxMetricsPoints).fill(''),
                datasets: [
                    {
                        label: 'P95 Real (ms)',
                        data: Array(this.maxMetricsPoints).fill(150),
                        borderColor: '#388bfd',
                        backgroundColor: 'rgba(56, 139, 253, 0.1)',
                        fill: true,
                        tension: 0.25,
                        pointRadius: 0
                    },
                    {
                        label: 'Limiar SRE Clássico (1.500 ms)',
                        data: Array(this.maxMetricsPoints).fill(1500),
                        borderColor: '#da3633',
                        borderDash: [5, 5],
                        borderWidth: 1.5,
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                animation: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        min: 0,
                        max: 1800,
                        ticks: { stepSize: 400, callback: (v) => v + 'ms' },
                        grid: { color: '#1f2937' }
                    },
                    x: { display: false }
                }
            }
        });
    }

    _initPoolChart() {
        const ctx = document.getElementById('chartPool');
        if (!ctx) return;

        this.chartPool = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(this.maxMetricsPoints).fill(''),
                datasets: [
                    {
                        label: 'Ocupação do Pool',
                        data: Array(this.maxMetricsPoints).fill(5),
                        borderColor: '#3fb950',
                        backgroundColor: 'rgba(63, 185, 80, 0.1)',
                        fill: true,
                        tension: 0.25,
                        pointRadius: 0
                    },
                    {
                        label: 'Capacidade Total',
                        data: Array(this.maxMetricsPoints).fill(30),
                        borderColor: '#8b5cf6',
                        borderDash: [4, 4],
                        borderWidth: 1.5,
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                animation: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        min: 0,
                        max: 70,
                        ticks: { stepSize: 15, callback: (v) => v + ' slots' },
                        grid: { color: '#1f2937' }
                    },
                    x: { display: false }
                }
            }
        });
    }

    updateHorizon(proj) {
        if (!this.chartHorizon || !proj) return;

        const past = proj.past_trajectory || [];
        const curRho = proj.current_rho;
        const pLen = past.length;

        const p1 = pLen >= 15 ? past[pLen - 15].rho : (pLen >= 1 ? past[0].rho : curRho);
        const p2 = pLen >= 10 ? past[pLen - 10].rho : (pLen >= 1 ? past[0].rho : curRho);
        const p3 = pLen >= 6 ? past[pLen - 6].rho : (pLen >= 1 ? past[0].rho : curRho);
        const p4 = pLen >= 3 ? past[pLen - 3].rho : curRho;

        const histData = [p1, p2, p3, p4, curRho, null, null, null, null, null, null, null];
        this.chartHorizon.data.datasets[2].data = histData;

        const fut = proj.horizon_points || [];
        if (fut.length >= 8) {
            const coneUpper = [null, null, null, null, curRho, fut[1].rho_upper, fut[2].rho_upper, fut[3].rho_upper, fut[4].rho_upper, fut[5].rho_upper, fut[6].rho_upper, fut[7].rho_upper];
            const coneLower = [null, null, null, null, curRho, fut[1].rho_lower, fut[2].rho_lower, fut[3].rho_lower, fut[4].rho_lower, fut[5].rho_lower, fut[6].rho_lower, fut[7].rho_lower];
            const projMedian = [null, null, null, null, curRho, fut[1].rho_expected, fut[2].rho_expected, fut[3].rho_expected, fut[4].rho_expected, fut[5].rho_expected, fut[6].rho_expected, fut[7].rho_expected];
            const projMit = [null, null, null, null, curRho, fut[1].rho_mitigated, fut[2].rho_mitigated, fut[3].rho_mitigated, fut[4].rho_mitigated, fut[5].rho_mitigated, fut[6].rho_mitigated, fut[7].rho_mitigated];

            this.chartHorizon.data.datasets[0].data = coneUpper;
            this.chartHorizon.data.datasets[1].data = coneLower;
            this.chartHorizon.data.datasets[3].data = projMedian;
            this.chartHorizon.data.datasets[4].data = projMit;
        }

        // Atualização instantânea de alta performance sem reflow de layout
        this.chartHorizon.update('none');
    }

    updateMetrics(latencyP95, usedPool, capacityPool) {
        if (this.chartLatency) {
            this.chartLatency.data.datasets[0].data.shift();
            this.chartLatency.data.datasets[0].data.push(latencyP95);
            this.chartLatency.update('none');
        }

        if (this.chartPool) {
            this.chartPool.data.datasets[0].data.shift();
            this.chartPool.data.datasets[0].data.push(usedPool);
            this.chartPool.data.datasets[1].data = Array(this.maxMetricsPoints).fill(capacityPool);
            this.chartPool.data.datasets[0].borderColor = usedPool > (capacityPool * 0.8) ? '#f85149' : (usedPool > (capacityPool * 0.5) ? '#d29922' : '#3fb950');
            this.chartPool.update('none');
        }
    }
}
