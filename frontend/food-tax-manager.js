/**
 * FoodTaxManager - Frontend manager for automated food tax system
 * 
 * Handles:
 * - Displaying tax status and countdown timers
 * - Showing warnings when tax is approaching
 * - Processing tax payment notifications
 * - Adjusting timers when game is paused/resumed
 */

class FoodTaxManager {
    constructor(gameCode, currentPlayer, gameAPI, gameWS) {
        this.gameCode = gameCode;
        this.currentPlayer = currentPlayer;
        this.gameAPI = gameAPI;
        this.gameWS = gameWS;
        
        // Tax status for all teams
        this.taxStatus = {};
        
        // Timer interval for updating countdown displays
        this.timerInterval = null;
        
        // Track if we've shown warning already
        this.warningsShown = new Set();
    }
    
    /**
     * Initialize the food tax manager
     */
    async initialize() {
        console.log('[FoodTaxManager] Initializing...');
        
        try {
            await this.loadTaxStatus();
            this.startTimer();
            console.log('[FoodTaxManager] Initialized successfully');
        } catch (error) {
            console.error('[FoodTaxManager] Initialization failed:', error);
        }
    }
    
    /**
     * Load current tax status from server
     */
    async loadTaxStatus() {
        try {
            const response = await fetch(
                `${this.gameAPI.baseUrl}/api/v2/food-tax/${this.gameCode}/status`,
                {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            
            if (!response.ok) {
                throw new Error(`Failed to load tax status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.taxStatus = data.teams || {};
                console.log('[FoodTaxManager] Tax status loaded:', this.taxStatus);
                this.updateUI();
            }
        } catch (error) {
            console.error('[FoodTaxManager] Failed to load tax status:', error);
        }
    }
    
    /**
     * Adjust tax timings after game is resumed from pause
     */
    async adjustForPause(pauseDurationMs) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseUrl}/api/v2/food-tax/${this.gameCode}/adjust-for-pause?pause_duration_ms=${pauseDurationMs}`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            
            if (!response.ok) {
                throw new Error(`Failed to adjust for pause: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('[FoodTaxManager] Adjusted for pause:', data);
            
            // Reload status after adjustment
            await this.loadTaxStatus();
            
            return data;
        } catch (error) {
            console.error('[FoodTaxManager] Failed to adjust for pause:', error);
            throw error;
        }
    }
    
    /**
     * Start the timer for updating countdown displays
     */
    startTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
        }
        
        this.timerInterval = setInterval(() => {
            this.updateUI();
        }, 1000);  // Update every second
    }
    
    /**
     * Stop the timer
     */
    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }
    
    /**
     * Update UI with current tax status
     */
    updateUI() {
        // Update based on role
        if (this.currentPlayer.role === 'player') {
            this.updatePlayerUI();
        } else if (this.currentPlayer.role === 'host' || this.currentPlayer.role === 'banker') {
            this.updateHostBankerUI();
        }
    }
    
    /**
     * Update UI for player role
     */
    updatePlayerUI() {
        // Find player's team number
        const teamNumber = this.getPlayerTeamNumber();
        if (!teamNumber) return;
        
        const teamTaxStatus = this.taxStatus[teamNumber];
        if (!teamTaxStatus) return;
        
        // Find or create food tax display element
        let taxDisplay = document.getElementById('food-tax-status');
        if (!taxDisplay) {
            // Create the display element if it doesn't exist
            const productionCard = document.querySelector('.production-card');
            if (productionCard) {
                taxDisplay = document.createElement('div');
                taxDisplay.id = 'food-tax-status';
                taxDisplay.className = 'food-tax-status';
                productionCard.insertBefore(taxDisplay, productionCard.firstChild);
            } else {
                return;
            }
        }
        
        // Calculate time remaining
        const minutesRemaining = this.calculateMinutesRemaining(teamTaxStatus.next_tax_due);
        
        // Determine status class
        let statusClass = 'safe';
        if (minutesRemaining <= 1) {
            statusClass = 'critical';
        } else if (minutesRemaining <= 3) {
            statusClass = 'warning';
        }
        
        // Format display
        const timeStr = this.formatTimeRemaining(minutesRemaining);
        const taxAmount = teamTaxStatus.tax_amount || 0;
        
        taxDisplay.className = `food-tax-status ${statusClass}`;
        taxDisplay.innerHTML = `
            <div class="tax-header">
                <span class="tax-icon">🍽️</span>
                <span class="tax-title">Food Tax</span>
            </div>
            <div class="tax-amount">Amount: ${taxAmount} food</div>
            <div class="tax-timer">Next due: ${timeStr}</div>
            <div class="tax-stats">Paid: ${teamTaxStatus.total_taxes_paid || 0} | Famines: ${teamTaxStatus.total_famines || 0}</div>
        `;
    }
    
    /**
     * Update UI for host/banker role
     */
    updateHostBankerUI() {
        // Find or create food tax overview element
        let taxOverview = document.getElementById('food-tax-overview');
        if (!taxOverview) {
            // Try to add to banker dashboard
            const bankerDashboard = document.getElementById('banker-dashboard');
            if (bankerDashboard) {
                taxOverview = document.createElement('div');
                taxOverview.id = 'food-tax-overview';
                taxOverview.className = 'food-tax-overview card';
                bankerDashboard.appendChild(taxOverview);
            } else {
                return;
            }
        }
        
        // Build overview HTML
        let html = '<h3>📊 Food Tax Overview</h3>';
        html += '<div class="tax-overview-grid">';
        
        for (const [teamNumber, taxData] of Object.entries(this.taxStatus)) {
            const minutesRemaining = this.calculateMinutesRemaining(taxData.next_tax_due);
            const timeStr = this.formatTimeRemaining(minutesRemaining);
            
            let statusClass = 'safe';
            if (minutesRemaining <= 1) {
                statusClass = 'critical';
            } else if (minutesRemaining <= 3) {
                statusClass = 'warning';
            }
            
            html += `
                <div class="team-tax-status ${statusClass}">
                    <div class="team-header">Team ${teamNumber}</div>
                    <div class="team-tax-amount">Tax: ${taxData.tax_amount || 0} food</div>
                    <div class="team-tax-timer">Due: ${timeStr}</div>
                    <div class="team-tax-stats">
                        <span title="Taxes paid">✅ ${taxData.total_taxes_paid || 0}</span>
                        <span title="Famines">⚠️ ${taxData.total_famines || 0}</span>
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        taxOverview.innerHTML = html;
    }
    
    /**
     * Calculate minutes remaining until tax is due
     */
    calculateMinutesRemaining(nextTaxDue) {
        if (!nextTaxDue) return 0;
        
        const now = new Date();
        const due = new Date(nextTaxDue);
        const diffMs = due - now;
        const diffMinutes = diffMs / (1000 * 60);
        
        return Math.max(0, diffMinutes);
    }
    
    /**
     * Format time remaining as string
     */
    formatTimeRemaining(minutes) {
        if (minutes <= 0) {
            return 'Processing...';
        }
        
        if (minutes < 1) {
            const seconds = Math.floor(minutes * 60);
            return `${seconds}s`;
        }
        
        if (minutes < 60) {
            const mins = Math.floor(minutes);
            const secs = Math.floor((minutes - mins) * 60);
            return `${mins}m ${secs}s`;
        }
        
        const hours = Math.floor(minutes / 60);
        const mins = Math.floor(minutes % 60);
        return `${hours}h ${mins}m`;
    }
    
    /**
     * Get the team number for the current player
     */
    getPlayerTeamNumber() {
        // This should be set from the global teamState or currentPlayer
        // For now, try to get it from DOM or global state
        if (window.currentPlayer && window.currentPlayer.group_number) {
            return String(window.currentPlayer.group_number);
        }
        return null;
    }
    
    /**
     * Handle food tax warning event
     */
    handleFoodTaxWarning(eventData) {
        console.log('[FoodTaxManager] Warning received:', eventData);
        
        const teamNumber = eventData.team_number;
        const minutesRemaining = eventData.minutes_remaining;
        
        // Update local status
        if (this.taxStatus[teamNumber]) {
            this.taxStatus[teamNumber].warning_sent = true;
        }
        
        // Show warning notification
        const warningKey = `${teamNumber}-${eventData.next_tax_due}`;
        if (!this.warningsShown.has(warningKey)) {
            this.showWarningNotification(teamNumber, minutesRemaining);
            this.warningsShown.add(warningKey);
        }
        
        this.updateUI();
    }
    
    /**
     * Handle food tax applied event
     */
    handleFoodTaxApplied(eventData) {
        console.log('[FoodTaxManager] Tax applied:', eventData);
        
        const teamNumber = eventData.team_number;
        const taxAmount = eventData.tax_amount;
        const message = eventData.message;
        
        // Update local status
        if (this.taxStatus[teamNumber]) {
            this.taxStatus[teamNumber].next_tax_due = eventData.next_tax_due;
            this.taxStatus[teamNumber].total_taxes_paid = (this.taxStatus[teamNumber].total_taxes_paid || 0) + 1;
            this.taxStatus[teamNumber].warning_sent = false;
        }
        
        // Show notification
        this.showTaxAppliedNotification(teamNumber, taxAmount, message);
        
        this.updateUI();
    }
    
    /**
     * Handle food tax famine event
     */
    handleFoodTaxFamine(eventData) {
        console.log('[FoodTaxManager] Famine occurred:', eventData);
        
        const teamNumber = eventData.team_number;
        const message = eventData.message;
        
        // Update local status
        if (this.taxStatus[teamNumber]) {
            this.taxStatus[teamNumber].next_tax_due = eventData.next_tax_due;
            this.taxStatus[teamNumber].total_famines = (this.taxStatus[teamNumber].total_famines || 0) + 1;
            this.taxStatus[teamNumber].warning_sent = false;
        }
        
        // Show famine notification
        this.showFamineNotification(teamNumber, message);
        
        this.updateUI();
    }
    
    /**
     * Show warning notification
     */
    showWarningNotification(teamNumber, minutesRemaining) {
        const playerTeam = this.getPlayerTeamNumber();
        
        // Only show to affected team or host/banker
        if (this.currentPlayer.role === 'player' && playerTeam !== teamNumber) {
            return;
        }
        
        const roundedMinutes = Math.round(minutesRemaining * 10) / 10;
        
        this.showNotification(
            '⚠️ Food Tax Warning',
            `Team ${teamNumber}: Food tax due in ${roundedMinutes} minutes!`,
            'warning'
        );
    }
    
    /**
     * Show tax applied notification
     */
    showTaxAppliedNotification(teamNumber, taxAmount, message) {
        const playerTeam = this.getPlayerTeamNumber();
        
        // Only show to affected team or host/banker
        if (this.currentPlayer.role === 'player' && playerTeam !== teamNumber) {
            return;
        }
        
        let title = '✅ Food Tax Paid';
        let text = `Team ${teamNumber}: Paid ${taxAmount} food tax`;
        
        if (message && message.includes('Restaurants generated')) {
            text += '. ' + message;
        }
        
        this.showNotification(title, text, 'success');
    }
    
    /**
     * Show famine notification
     */
    showFamineNotification(teamNumber, message) {
        const playerTeam = this.getPlayerTeamNumber();
        
        // Only show to affected team or host/banker
        if (this.currentPlayer.role === 'player' && playerTeam !== teamNumber) {
            return;
        }
        
        this.showNotification(
            '🚨 FAMINE!',
            `Team ${teamNumber}: ${message}`,
            'error'
        );
    }
    
    /**
     * Show a notification to the user
     */
    showNotification(title, message, type = 'info') {
        // Use existing notification system if available
        if (window.showNotification) {
            window.showNotification(title, message, type);
            return;
        }
        
        // Fallback to console if no notification system
        console.log(`[${type.toUpperCase()}] ${title}: ${message}`);
        
        // Could also use browser's native notification API
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                body: message,
                icon: '/favicon.ico'
            });
        }
    }
    
    /**
     * Clean up resources
     */
    destroy() {
        this.stopTimer();
        this.taxStatus = {};
        this.warningsShown.clear();
        console.log('[FoodTaxManager] Destroyed');
    }
}

// Export for use in dashboard
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FoodTaxManager;
}
