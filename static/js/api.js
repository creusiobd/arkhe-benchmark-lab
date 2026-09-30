/**
 * api.js - Módulo de Comunicação REST do Cockpit ARKHÉ
 * Encapsula chamadas HTTP para o backend FastAPI.
 */

export async function fetchLiveTelemetry() {
    try {
        const response = await fetch('/telemetry/live');
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status} ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Falha ao obter telemetria ao vivo via HTTP:', error);
        throw error;
    }
}

export async function toggleMitigationApi() {
    try {
        const response = await fetch('/admin/mitigation/toggle', { method: 'POST' });
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Falha ao alternar mitigação autônoma:', error);
        throw error;
    }
}

export async function triggerScenarioApi(scenarioName) {
    try {
        const response = await fetch(`/admin/chaos/scenario/${encodeURIComponent(scenarioName)}`, { method: 'POST' });
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Falha ao disparar cenário ${scenarioName}:`, error);
        throw error;
    }
}

export async function resetSystemStateApi() {
    try {
        const response = await fetch('/admin/chaos/reset', { method: 'POST' });
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Falha ao resetar estado do sistema:', error);
        throw error;
    }
}

export async function fetchLoadConfigApi() {
    try {
        const response = await fetch('/admin/load/config');
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Falha ao obter configuração de carga:', error);
        throw error;
    }
}

export async function setTpsApi(tps) {
    try {
        const response = await fetch(`/admin/load/tps?tps=${encodeURIComponent(tps)}`, { method: 'POST' });
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Falha ao definir ${tps} TPS:`, error);
        throw error;
    }
}

export async function adjustTpsApi(delta) {
    try {
        const response = await fetch(`/admin/load/adjust?delta=${encodeURIComponent(delta)}`, { method: 'POST' });
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Falha ao ajustar TPS em ${delta}:`, error);
        throw error;
    }
}

export async function toggleStochasticApi() {
    try {
        const response = await fetch('/admin/load/toggle_stochastic', { method: 'POST' });
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Falha ao alternar simulação estocástica:', error);
        throw error;
    }
}
