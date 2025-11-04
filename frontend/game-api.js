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
            console.log('[WebSocket] Received message:', data);
            console.log('[WebSocket] Message type:', data.type);
            this.trigger(data.type, data);
            console.log('[WebSocket] Triggered event handler for type:', data.type);
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
        console.log(`[GameAPI] ${method} ${endpoint}`, data);
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

        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, options);
            
            if (!response.ok) {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const error = await response.json();
                    errorMessage = error.detail || error.message || errorMessage;
                } catch (jsonError) {
                    // If response is not JSON, use the text
                    try {
                        const errorText = await response.text();
                        if (errorText) errorMessage = errorText;
                    } catch (textError) {
                        // Use the default error message
                    }
                }
                throw new Error(errorMessage);
            }

            return response.json();
        } catch (error) {
            // If it's already an Error, re-throw it
            if (error instanceof Error) {
                throw error;
            }
            // Otherwise, wrap it in an Error
            throw new Error('Network request failed: ' + error);
        }
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

    async joinGame(gameCode, playerName, role) {
        return this.request('POST', '/api/join', {
            game_code: gameCode,
            player_name: playerName,
            role
        });
    }

    // Group assignment (host actions)
    async assignPlayerGroup(gameCode, playerId, groupNumber) {
        return this.request('PUT', `/games/${gameCode}/players/${playerId}/assign-group?group_number=${groupNumber}`);
    }

    async unassignPlayerGroup(gameCode, playerId) {
        return this.request('DELETE', `/games/${gameCode}/players/${playerId}/unassign-group`);
    }

    async removePlayerFromGame(gameCode, playerId) {
        return this.request('DELETE', `/games/${gameCode}/players/${playerId}`);
    }

    async clearAllPlayersFromLobby(gameCode) {
        return this.request('DELETE', `/games/${gameCode}/players`);
    }

    async deleteGame(gameCode) {
        return this.request('DELETE', `/games/${gameCode}`);
    }

    async autoAssignGroups(gameCode, numTeams = 4) {
        return this.request('POST', `/games/${gameCode}/auto-assign-groups?num_teams=${numTeams}`);
    }

    async getUnassignedPlayers(gameCode) {
        return this.request('GET', `/games/${gameCode}/unassigned-players`);
    }

    // Test mode
    async createFakePlayers(gameCode, numPlayers) {
        return this.request('POST', `/games/${gameCode}/create-fake-players?num_players=${numPlayers}`);
    }

    async setNumberOfTeams(gameCode, numTeams) {
        return this.request('POST', `/games/${gameCode}/set-teams?num_teams=${numTeams}`);
    }

    // Alias for setNumberOfTeams
    async setNumTeams(gameCode, numTeams) {
        return this.setNumberOfTeams(gameCode, numTeams);
    }

    async setGameDuration(gameCode, durationMinutes) {
        return this.request('POST', `/games/${gameCode}/set-duration?duration_minutes=${durationMinutes}`);
    }

    async updateTeamName(gameCode, teamNumber, teamName) {
        return this.request('POST', `/games/${gameCode}/teams/${teamNumber}/set-name?name=${encodeURIComponent(teamName)}`);
    }

    // Player management
    async assignPlayerRole(gameCode, playerId, role) {
        return this.request('PUT', `/games/${gameCode}/players/${playerId}/assign-role?role=${role}`);
    }

    async approvePlayer(gameCode, playerId) {
        return this.request('PUT', `/games/${gameCode}/players/${playerId}/approve`);
    }

    async getPendingPlayers(gameCode) {
        return this.request('GET', `/games/${gameCode}/pending-players`);
    }

    async startGame(gameCode) {
        return this.request('POST', `/games/${gameCode}/start`);
    }

    async pauseGame(gameCode) {
        return this.request('POST', `/games/${gameCode}/pause`);
    }

    async resumeGame(gameCode) {
        return this.request('POST', `/games/${gameCode}/resume`);
    }

    async endGame(gameCode) {
        return this.request('POST', `/games/${gameCode}/end`);
    }

    // ==================== CHALLENGE METHODS ====================

    async createChallenge(gameCode, challengeData) {
        // Use v2 API endpoint which triggers WebSocket broadcasts
        return this.request('POST', `/api/v2/challenges/${gameCode}/request`, challengeData);
    }

    async getChallenges(gameCode, status = null) {
        // Use v2 API endpoint which returns proper challenge format
        return this.request('GET', `/api/v2/challenges/${gameCode}/active`);
    }

    async updateChallenge(gameCode, challengeId, updateData) {
        return this.request('PATCH', `/games/${gameCode}/challenges/${challengeId}`, updateData);
    }

    async deleteChallenge(gameCode, challengeId) {
        return this.request('DELETE', `/games/${gameCode}/challenges/${challengeId}`);
    }
}

// Export for use in HTML
window.GameWebSocket = GameWebSocket;
window.GameAPI = GameAPI;
