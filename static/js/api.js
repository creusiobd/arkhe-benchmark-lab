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
