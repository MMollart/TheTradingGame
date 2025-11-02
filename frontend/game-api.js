/**
 * WebSocket client for real-time game updates
 */

class GameWebSocket {
    constructor(gameCode, playerId) {
        this.gameCode = gameCode;
        this.playerId = playerId;
        this.ws = null;
        this.listeners = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect() {
        const wsUrl = `ws://localhost:8000/ws/${this.gameCode}/${this.playerId}`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.trigger('connected');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Received:', data);
            this.trigger(data.type, data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.trigger('error', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.trigger('disconnected');
            this.attemptReconnect();
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            setTimeout(() => this.connect(), 2000 * this.reconnectAttempts);
        }
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.error('WebSocket not connected');
        }
    }

    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }

    trigger(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(callback => callback(data));
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

/**
 * Game API client
 */
class GameAPI {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.token = null;
    }

    setToken(token) {
        this.token = token;
    }

    async request(method, endpoint, data = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (this.token) {
            options.headers['Authorization'] = `Bearer ${this.token}`;
        }

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, options);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Request failed');
        }

        return response.json();
    }

    // Authentication
    async register(username, email, password) {
        return this.request('POST', '/auth/register', { username, email, password });
    }

    async login(username, password) {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${this.baseUrl}/auth/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error('Login failed');
        }

        const data = await response.json();
        this.setToken(data.access_token);
        return data;
    }

    // Game Sessions
    async createGame(configId = null) {
        return this.request('POST', '/games', { config_id: configId });
    }

    async getGame(gameCode) {
        return this.request('GET', `/games/${gameCode}`);
    }

    async getPlayers(gameCode) {
        return this.request('GET', `/games/${gameCode}/players`);
    }

    async joinGame(gameCode, playerName, role, groupNumber = null) {
        return this.request('POST', '/games/join', {
            game_code: gameCode,
            player_name: playerName,
            role,
            group_number: groupNumber
        });
    }

    async startGame(gameCode) {
        return this.request('POST', `/games/${gameCode}/start`);
    }

    async pauseGame(gameCode) {
        return this.request('POST', `/games/${gameCode}/pause`);
    }

    async endGame(gameCode) {
        return this.request('POST', `/games/${gameCode}/end`);
    }
}

// Export for use in HTML
window.GameWebSocket = GameWebSocket;
window.GameAPI = GameAPI;
