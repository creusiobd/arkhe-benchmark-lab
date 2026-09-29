/**
 * websocket.js - Cliente de Streaming WebSocket em Alta Frequência (20 FPS / 20 Hz)
 * Gerencia a conexão bidirecional de telemetria com reconexão resiliente.
 */

export class TelemetryStreamClient {
    constructor(options = {}) {
        this.options = Object.assign({
            url: null,
            reconnectIntervalMs: 1500,
            maxReconnectIntervalMs: 8000,
            onMessage: () => {},
            onStatusChange: () => {},
            onError: () => {}
        }, options);

        this.socket = null;
        this.isConnected = false;
        this.reconnectTimer = null;
        this.currentBackoff = this.options.reconnectIntervalMs;
        this.isExplicitlyClosed = false;
    }

    _resolveWsUrl() {
        if (this.options.url) return this.options.url;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/ws/telemetry`;
    }

    connect() {
        this.isExplicitlyClosed = false;
        const url = this._resolveWsUrl();

        try {
            this.socket = new WebSocket(url);

            this.socket.onopen = () => {
                this.isConnected = true;
                this.currentBackoff = this.options.reconnectIntervalMs;
                this.options.onStatusChange({
                    status: 'connected',
                    text: 'WEBSOCKET 20 FPS (STREAM AO VIVO ULTRA-RÁPIDO)',
                    badgeClass: 'ws-badge ws-active'
                });
            };

            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.options.onMessage(data);
                } catch (err) {
                    // Frame em formato texto simples (ex: "pong")
                    if (event.data === 'pong') {
                        // Resposta ao ping de healthcheck
                    } else {
                        console.warn('Frame WS não-JSON recebido:', event.data);
                    }
                }
            };

            this.socket.onclose = () => {
                this.isConnected = false;
                this.options.onStatusChange({
                    status: 'disconnected',
                    text: 'RECONECTANDO WS (MODO HTTP ATIVO)...',
                    badgeClass: 'ws-badge ws-polling'
                });

                if (!this.isExplicitlyClosed) {
                    this._scheduleReconnect();
                }
            };

            this.socket.onerror = (error) => {
                this.options.onError(error);
                if (this.socket) {
                    this.socket.close();
                }
            };
        } catch (e) {
            console.error('Falha de inicialização WebSocket:', e);
            this._scheduleReconnect();
        }
    }

    _scheduleReconnect() {
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        this.reconnectTimer = setTimeout(() => {
            this.connect();
        }, this.currentBackoff);
        this.currentBackoff = Math.min(this.currentBackoff * 1.5, this.options.maxReconnectIntervalMs);
    }

    send(command) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(command);
            return true;
        }
        return false;
    }

    sendScenario(scenarioId) {
        return this.send(`scenario:${scenarioId}`);
    }

    sendToggleMitigation() {
        return this.send('toggle_mitigation');
    }

    sendSetTps(tps) {
        return this.send(`set_tps:${tps}`);
    }

    sendAdjustTps(delta) {
        return this.send(`delta_tps:${delta}`);
    }

    sendToggleStochastic() {
        return this.send('toggle_stochastic');
    }

    sendPing() {
        return this.send('ping');
    }

    disconnect() {
        this.isExplicitlyClosed = true;
        if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        if (this.socket) {
            this.socket.close();
        }
    }
}
