/**
 * Challenge Manager - Frontend
 * 
 * Single source of truth for challenge state with multi-user support.
 * Handles challenge lifecycle, pause-aware timing, and WebSocket synchronization.
 * 
 * Usage:
 *   const manager = new ChallengeManager(gameCode, currentPlayer, gameAPI, gameWS);
 *   await manager.initialize();
 *   manager.onChallengesUpdated((challenges) => { updateUI(challenges); });
 */

class ChallengeManager {
    constructor(gameCode, currentPlayer, gameAPI, gameWS) {
        this.gameCode = gameCode;
        this.currentPlayer = currentPlayer;
        this.gameAPI = gameAPI;
        this.gameWS = gameWS;
        
        // State
        this.challenges = new Map(); // Map<challengeKey, challengeData>
        this.gameStatus = 'waiting'; // 'waiting', 'in_progress', 'paused', 'completed'
        this.lastPauseTime = null;
        
        // Callbacks
        this.updateCallbacks = [];
        this.timerInterval = null;
        
        // Constants
        this.CHALLENGE_DURATION_MS = 10 * 60 * 1000; // 10 minutes
        this.EXPIRY_CHECK_INTERVAL_MS = 1000; // Check every second
        
        // Bind WebSocket handler
        this._setupWebSocketHandlers();
    }
    
    /**
     * Initialize the challenge manager by loading challenges from server
     */
    async initialize() {
        // console.log('[ChallengeManager] Initializing...');
        await this.loadFromServer();
        this.startTimerInterval();
        // console.log('[ChallengeManager] Initialized with', this.challenges.size, 'challenges');
    }
    
    /**
     * Load all active challenges from server
     */
    async loadFromServer() {
        try {
            const challenges = await this.gameAPI.getChallenges(this.gameCode);
            // console.log('[ChallengeManager] loadFromServer - Raw challenges from API:', challenges);
            // console.log('[ChallengeManager] loadFromServer - Number of challenges:', challenges.length);
            
            // Fetch player names to enrich challenge data
            const players = await this.gameAPI.getPlayers(this.gameCode);
            // console.log('[ChallengeManager] loadFromServer - Players from API:', players);
            // console.log('[ChallengeManager] loadFromServer - First player structure:', players[0]);
            const playerMap = new Map(players.map(p => [p.id, p.name || p.player_name]));
            
            // Clear and rebuild challenge map
            this.challenges.clear();
            
            for (const challenge of challenges) {
                // console.log('[ChallengeManager] loadFromServer - Processing challenge:', challenge);
                // console.log('[ChallengeManager] loadFromServer - Challenge ID:', challenge.id);
                // console.log('[ChallengeManager] loadFromServer - Challenge status:', challenge.status);
                // console.log('[ChallengeManager] loadFromServer - Challenge player_id:', challenge.player_id);
                // console.log('[ChallengeManager] loadFromServer - Challenge team_number:', challenge.team_number);
                // console.log('[ChallengeManager] loadFromServer - Challenge building_type:', challenge.building_type);
                // console.log('[ChallengeManager] loadFromServer - Challenge assigned_at:', challenge.assigned_at);
                // console.log('[ChallengeManager] loadFromServer - Challenge start_time:', challenge.start_time);
                
                // Only load active challenges
                if (challenge.status === 'requested' || challenge.status === 'assigned') {
                    const key = this._getChallengeKey(challenge);
                    // console.log('[ChallengeManager] loadFromServer - Challenge key:', key);
                    const normalizedChallenge = this._normalizeChallenge(challenge);
                    // console.log('[ChallengeManager] loadFromServer - Normalized challenge:', normalizedChallenge);
                    // console.log('[ChallengeManager] loadFromServer - Normalized status:', normalizedChallenge.status);
                    
                    // Add player name from players list
                    normalizedChallenge.player_name = playerMap.get(challenge.player_id) || 'Unknown Player';
                    this.challenges.set(key, normalizedChallenge);
                }
            }
            
            this._notifyUpdates();
            // console.log('[ChallengeManager] Loaded', this.challenges.size, 'challenges from server');
            // console.log('[ChallengeManager] Final challenges map:', Array.from(this.challenges.entries()));
        } catch (error) {
            console.error('[ChallengeManager] Failed to load challenges:', error);
            throw error;
        }
    }
    
    /**
     * Request a new challenge (player action)
     */
    async requestChallenge(playerId, buildingType, buildingName, teamNumber, hasSchool) {
        try {
            // console.log('[ChallengeManager] Requesting challenge:', { playerId, buildingType });
            
            const response = await fetch(`${this.gameAPI.baseUrl}/games/${this.gameCode}/challenges`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.gameAPI.token}`
                },
                body: JSON.stringify({
                    player_id: playerId,
                    building_type: buildingType,
                    building_name: buildingName,
                    team_number: teamNumber,
                    has_school: hasSchool
                })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to request challenge: ${response.statusText}`);
            }
            
            const challenge = await response.json();
            
            // Add to local state (WebSocket will sync with others)
            const key = this._getChallengeKey(challenge);
            this.challenges.set(key, this._normalizeChallenge(challenge));
            this._notifyUpdates();
            
            return challenge;
        } catch (error) {
            console.error('[ChallengeManager] Request failed:', error);
            throw error;
        }
    }
    
    /**
     * Assign a challenge (host/banker action)
     */
    async assignChallenge(challengeId, challengeType, challengeDescription, targetNumber) {
        try {
            // console.log('[ChallengeManager] Assigning challenge:', challengeId);
            
            const response = await this.gameAPI.updateChallenge(this.gameCode, challengeId, {
                status: 'assigned',
                challenge_type: challengeType,
                challenge_description: challengeDescription,
                target_number: targetNumber
            });
            
            // Update local state
            const key = this._findChallengeKeyById(challengeId);
            if (key) {
                const challenge = this.challenges.get(key);
                challenge.status = 'assigned';
                challenge.challenge_type = challengeType;
                challenge.challenge_description = challengeDescription;
                challenge.target_number = targetNumber;
                challenge.start_time = Date.now();
                challenge.assigned_at = new Date().toISOString();
                this.challenges.set(key, challenge);
                this._notifyUpdates();
            }
            
            return response;
        } catch (error) {
            console.error('[ChallengeManager] Assignment failed:', error);
            throw error;
        }
    }
    
    /**
     * Complete a challenge (host/banker action)
     */
    async completeChallenge(challengeId) {
        try {
            // console.log('[ChallengeManager] Completing challenge:', challengeId);
            
            await this.gameAPI.updateChallenge(this.gameCode, challengeId, {
                status: 'completed'
            });
            
            // Remove from local state
            const key = this._findChallengeKeyById(challengeId);
            if (key) {
                this.challenges.delete(key);
                this._notifyUpdates();
            }
            
            return { success: true };
        } catch (error) {
            console.error('[ChallengeManager] Completion failed:', error);
            throw error;
        }
    }
    
    /**
     * Cancel a challenge (host/banker action)
     */
    async cancelChallenge(challengeId) {
        try {
            // console.log('[ChallengeManager] Cancelling challenge:', challengeId);
            
            await this.gameAPI.updateChallenge(this.gameCode, challengeId, {
                status: 'cancelled'
            });
            
            // Remove from local state
            const key = this._findChallengeKeyById(challengeId);
            if (key) {
                this.challenges.delete(key);
                this._notifyUpdates();
            }
            
            return { success: true };
        } catch (error) {
            console.error('[ChallengeManager] Cancellation failed:', error);
            throw error;
        }
    }
    
    /**
     * Adjust challenge times for pause (called on resume)
     */
    async adjustForPause(pauseDurationMs) {
        try {
            // console.log('[ChallengeManager] Adjusting for pause:', pauseDurationMs, 'ms');
            
            const response = await fetch(`${this.gameAPI.baseUrl}/games/${this.gameCode}/challenges/adjust-for-pause`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.gameAPI.token}`
                },
                body: JSON.stringify({ pause_duration_ms: pauseDurationMs })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to adjust challenges: ${response.statusText}`);
            }
            
            // Wait a moment for DB to commit
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Reload from server to get updated timestamps
            await this.loadFromServer();
            
            return await response.json();
        } catch (error) {
            console.error('[ChallengeManager] Pause adjustment failed:', error);
            throw error;
        }
    }
    
    /**
     * Get challenges for display (filtered by user role)
     */
    getChallengesForUser() {
        // console.log('[ChallengeManager] getChallengesForUser - currentPlayer:', this.currentPlayer);
        const isHostOrBanker = this.currentPlayer.role === 'host' || this.currentPlayer.role === 'banker';
        const challenges = Array.from(this.challenges.values());
        // console.log('[ChallengeManager] getChallengesForUser - all challenges:', challenges);
        // console.log('[ChallengeManager] getChallengesForUser - isHostOrBanker:', isHostOrBanker);
        
        if (isHostOrBanker) {
            // Host/banker sees all challenges
            // console.log('[ChallengeManager] getChallengesForUser - returning all challenges (host/banker)');
            return challenges;
        } else {
            // Team members see only their team's challenges
            // console.log('[ChallengeManager] getChallengesForUser - filtering by team:', this.currentPlayer.groupNumber);
            const filtered = challenges.filter(c => {
                // console.log('[ChallengeManager] getChallengesForUser - checking challenge team:', c.team_number, 'vs player team:', this.currentPlayer.groupNumber);
                return c.team_number === this.currentPlayer.groupNumber;
            });
            // console.log('[ChallengeManager] getChallengesForUser - filtered challenges:', filtered);
            return filtered;
        }
    }
    
    /**
     * Get only assigned challenges (for Active Challenges tab)
     */
    getAssignedChallenges() {
        const userChallenges = this.getChallengesForUser();
        // console.log('[ChallengeManager] getAssignedChallenges - user challenges:', userChallenges);
        // console.log('[ChallengeManager] getAssignedChallenges - current player role:', this.currentPlayer.role);
        // console.log('[ChallengeManager] getAssignedChallenges - current player groupNumber:', this.currentPlayer.groupNumber);
        
        const assigned = userChallenges.filter(c => {
            // console.log('[ChallengeManager] Checking challenge:', c);
            // console.log('[ChallengeManager] - status:', c.status, 'expected: assigned');
            // console.log('[ChallengeManager] - start_time:', c.start_time);
            return c.status === 'assigned' && c.start_time;
        });
        
        // console.log('[ChallengeManager] getAssignedChallenges - filtered assigned challenges:', assigned);
        return assigned;
    }
    
    /**
     * Get only requested challenges (for Challenge Requests tab)
     */
    getRequestedChallenges() {
        // console.log('[ChallengeManager] getRequestedChallenges called');
        // console.log('[ChallengeManager] currentPlayer:', this.currentPlayer);
        // console.log('[ChallengeManager] currentPlayer.role:', this.currentPlayer?.role);
        // console.log('[ChallengeManager] typeof role:', typeof this.currentPlayer?.role);
        
        // Normalize role to lowercase for comparison
        const role = this.currentPlayer?.role?.toLowerCase();
        const isHostOrBanker = role === 'host' || role === 'banker';
        // console.log('[ChallengeManager] normalized role:', role);
        // console.log('[ChallengeManager] isHostOrBanker:', isHostOrBanker);
        
        if (!isHostOrBanker) {
            // console.log('[ChallengeManager] Not host or banker, returning empty array');
            return [];
        }
        
        const requested = Array.from(this.challenges.values()).filter(c => c.status === 'requested');
        // console.log('[ChallengeManager] Requested challenges:', requested);
        // console.log('[ChallengeManager] Challenges map size:', this.challenges.size);
        // console.log('[ChallengeManager] All challenges:', Array.from(this.challenges.entries()));
        return requested;
    }
    
    /**
     * Calculate time remaining for a challenge
     */
    getTimeRemaining(challenge) {
        if (!challenge.start_time) {
            return null;
        }
        
        let now = Date.now();
        
        // If game is paused, freeze time at pause moment
        if (this.gameStatus === 'paused' && this.lastPauseTime) {
            now = this.lastPauseTime;
        }
        
        const elapsed = now - challenge.start_time;
        const remaining = this.CHALLENGE_DURATION_MS - elapsed;
        
        return Math.max(0, remaining);
    }
    
    /**
     * Set game status (waiting, in_progress, paused, completed)
     */
    setGameStatus(status, pauseTime = null) {
        // console.log('[ChallengeManager] Game status:', status);
        this.gameStatus = status;
        
        if (status === 'paused') {
            this.lastPauseTime = pauseTime || Date.now();
        } else if (status === 'in_progress') {
            this.lastPauseTime = null;
        }
    }
    
    /**
     * Register a callback for when challenges are updated
     */
    onChallengesUpdated(callback) {
        this.updateCallbacks.push(callback);
    }
    
    /**
     * Clean up resources
     */
    async clearAll() {
        // console.log('[ChallengeManager] Clearing all challenges');
        this.challenges.clear();
        this._notifyUpdates();
    }
    
    destroy() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        this.updateCallbacks = [];
        this.challenges.clear();
    }
    
    // Private methods
    
    _getChallengeKey(challenge) {
        if (challenge.has_school) {
            return `${challenge.player_id}-${challenge.building_type}`;
        } else {
            return `team${challenge.team_number}-${challenge.building_type}`;
        }
    }
    
    _findChallengeKeyById(challengeId) {
        for (const [key, challenge] of this.challenges.entries()) {
            if (challenge.db_id === challengeId) {
                return key;
            }
        }
        return null;
    }
    
    _normalizeChallenge(challenge) {
        return {
            db_id: challenge.id,
            player_id: challenge.player_id,
            team_number: challenge.team_number,
            building_type: challenge.building_type,
            building_name: challenge.building_name,
            has_school: challenge.has_school,
            status: challenge.status,
            challenge_type: challenge.challenge_type || null,
            challenge_description: challenge.challenge_description || null,
            target_number: challenge.target_number || null,
            start_time: challenge.assigned_at ? new Date(challenge.assigned_at).getTime() : null,
            timestamp: challenge.requested_at || challenge.assigned_at || new Date().toISOString(),
            requested_at: challenge.requested_at,
            assigned_at: challenge.assigned_at,
            completed_at: challenge.completed_at
        };
    }
    
    _notifyUpdates() {
        // console.log('[ChallengeManager] _notifyUpdates called, callbacks count:', this.updateCallbacks.length);
        // console.log('[ChallengeManager] Current challenges:', Array.from(this.challenges.entries()));
        for (const callback of this.updateCallbacks) {
            try {
                callback(this.challenges);
            } catch (error) {
                console.error('[ChallengeManager] Update callback error:', error);
            }
        }
    }
    
    _setupWebSocketHandlers() {
        // Hook into existing WebSocket event system
        // This assumes the WebSocket has an event handler we can extend
        // console.log('[ChallengeManager] Setting up WebSocket handlers');
    }
    
    startTimerInterval() {
        // Clear existing interval
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
        }
        
        // Start new interval
        this.timerInterval = setInterval(() => {
            this._checkExpiry();
            // Also notify updates every second to refresh countdown timers in UI
            // Only if there are active challenges and game is in progress
            if (this.gameStatus === 'in_progress' && this.getAssignedChallenges().length > 0) {
                this._notifyUpdates();
            }
        }, this.EXPIRY_CHECK_INTERVAL_MS);
    }
    
    _checkExpiry() {
        // Only expire challenges when game is actively running
        if (this.gameStatus !== 'in_progress') {
            return;
        }
        
        const now = Date.now();
        let expiredAny = false;
        
        for (const [key, challenge] of this.challenges.entries()) {
            if (challenge.status === 'assigned' && challenge.start_time) {
                const elapsed = now - challenge.start_time;
                
                if (elapsed >= this.CHALLENGE_DURATION_MS) {
                    // console.log('[ChallengeManager] Challenge expired:', key);
                    
                    // Mark as expired in database
                    this.gameAPI.updateChallenge(this.gameCode, challenge.db_id, { status: 'expired' })
                        .catch(err => console.error('[ChallengeManager] Failed to expire challenge:', err));
                    
                    // Remove from local state
                    this.challenges.delete(key);
                    expiredAny = true;
                }
            }
        }
        
        // No need to call _notifyUpdates here since the interval already does it every second
        // This avoids double notifications
    }
    
    // WebSocket event handlers (to be called from main dashboard code)
    
    handleChallengeRequest(eventData) {
        // console.log('[ChallengeManager] WebSocket: challenge_request', eventData);
        // console.log('[ChallengeManager] Current player:', this.currentPlayer);
        // console.log('[ChallengeManager] Current player role:', this.currentPlayer?.role);
        
        const challenge = {
            db_id: eventData.db_id || null, // Database ID from HTTP response
            player_id: eventData.player_id,
            player_name: eventData.player_name,
            team_number: eventData.team_number,
            building_type: eventData.building_type,
            building_name: eventData.building_name,
            has_school: eventData.has_school,
            status: 'requested',
            challenge_type: null,
            challenge_description: null,
            target_number: null,
            start_time: null,
            timestamp: new Date().toISOString(),
            requested_at: new Date().toISOString(),
            assigned_at: null,
            completed_at: null
        };
        
        const key = this._getChallengeKey(challenge);
        // console.log('[ChallengeManager] Adding challenge with key:', key);
        // console.log('[ChallengeManager] Challenge object:', challenge);
        this.challenges.set(key, challenge);
        // console.log('[ChallengeManager] Challenges map after add:', Array.from(this.challenges.entries()));
        // console.log('[ChallengeManager] Challenges map size:', this.challenges.size);
        // console.log('[ChallengeManager] Calling _notifyUpdates()...');
        this._notifyUpdates();
        // console.log('[ChallengeManager] _notifyUpdates() called');
    }
    
    handleChallengeAssigned(eventData) {
        // console.log('[ChallengeManager] WebSocket: challenge_assigned', eventData);
        
        // Find existing challenge
        const key = this._findChallengeKeyByPlayerAndBuilding(eventData.player_id, eventData.building_type);
        
        if (key) {
            const challenge = this.challenges.get(key);
            challenge.status = 'assigned';
            challenge.challenge_type = eventData.challenge_type;
            challenge.challenge_description = eventData.challenge_description;
            challenge.target_number = eventData.target_number;
            challenge.start_time = eventData.start_time;
            // Handle date conversion safely
            if (eventData.start_time) {
                const date = new Date(eventData.start_time);
                challenge.assigned_at = isNaN(date.getTime()) ? new Date().toISOString() : date.toISOString();
            } else {
                challenge.assigned_at = new Date().toISOString();
            }
            this.challenges.set(key, challenge);
            this._notifyUpdates();
        } else {
            // Challenge doesn't exist locally - reload from server
            // console.log('[ChallengeManager] Challenge not found locally, reloading from server');
            this.loadFromServer();
        }
    }
    
    handleChallengeCompleted(eventData) {
        // console.log('[ChallengeManager] WebSocket: challenge_completed', eventData);
        
        const key = this._findChallengeKeyByPlayerAndBuilding(eventData.player_id, eventData.building_type);
        if (key) {
            this.challenges.delete(key);
            this._notifyUpdates();
        }
    }
    
    handleChallengeCancelled(eventData) {
        // console.log('[ChallengeManager] WebSocket: challenge_cancelled', eventData);
        
        const key = this._findChallengeKeyByPlayerAndBuilding(eventData.player_id, eventData.building_type);
        if (key) {
            this.challenges.delete(key);
            this._notifyUpdates();
        }
    }
    
    _findChallengeKeyByPlayerAndBuilding(playerId, buildingType) {
        for (const [key, challenge] of this.challenges.entries()) {
            if (challenge.player_id === playerId && challenge.building_type === buildingType) {
                return key;
            }
        }
        return null;
    }
}

// Export for use in dashboard
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChallengeManager;
}
