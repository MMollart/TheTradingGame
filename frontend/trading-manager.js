/**
 * Trading Manager - Handles all trading operations
 * Manages bank trades and team-to-team trades
 */

class TradingManager {
    constructor(gameCode, gameAPI, gameWS) {
        this.gameCode = gameCode;
        this.gameAPI = gameAPI;
        this.gameWS = gameWS;
        this.currentPrices = {};
        this.priceHistory = {};
        this.activeOffers = [];
        this.rentalOffers = [];
        this.activeRentals = [];
        this.priceChart = null;
    }

    /**
     * Initialize trading manager
     */
    async initialize() {
        await this.loadCurrentPrices();
        console.log('[TradingManager] Initialized with prices:', this.currentPrices);
    }

    /**
     * Load current bank prices
     */
    async loadCurrentPrices() {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/bank/prices`,
                { headers: this.gameAPI.headers }
            );
            
            if (!response.ok) {
                throw new Error(`Failed to load prices: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.currentPrices = data.prices;
            return this.currentPrices;
        } catch (error) {
            console.error('[TradingManager] Error loading prices:', error);
            throw error;
        }
    }

    /**
     * Load price history for charting
     */
    async loadPriceHistory(resource = null, limit = 50) {
        try {
            let url = `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/bank/price-history?limit=${limit}`;
            if (resource) {
                url += `&resource=${resource}`;
            }
            
            const response = await fetch(url, { headers: this.gameAPI.headers });
            
            if (!response.ok) {
                throw new Error(`Failed to load price history: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (resource) {
                this.priceHistory[resource] = data.history;
            } else {
                this.priceHistory = data.history;
            }
            
            return data.history;
        } catch (error) {
            console.error('[TradingManager] Error loading price history:', error);
            throw error;
        }
    }

    /**
     * Execute a bank trade
     */
    async executeBankTrade(teamNumber, resource, amount, tradeType) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/bank/trade`,
                {
                    method: 'POST',
                    headers: this.gameAPI.headers,
                    body: JSON.stringify({
                        team_number: teamNumber,
                        resource: resource,
                        amount: amount,
                        trade_type: tradeType
                    })
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Trade failed');
            }
            
            // Update local prices
            if (data.new_prices) {
                this.currentPrices = data.new_prices;
            }
            
            return data;
        } catch (error) {
            console.error('[TradingManager] Error executing bank trade:', error);
            throw error;
        }
    }

    /**
     * Create a team trade offer
     */
    async createTradeOffer(fromTeam, toTeam, offering, requesting, message = null) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/team-trade/offer`,
                {
                    method: 'POST',
                    headers: this.gameAPI.headers,
                    body: JSON.stringify({
                        from_team: fromTeam,
                        to_team: toTeam,
                        offering: offering,
                        requesting: requesting,
                        message: message
                    })
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to create trade offer');
            }
            
            return data.offer;
        } catch (error) {
            console.error('[TradingManager] Error creating trade offer:', error);
            throw error;
        }
    }

    /**
     * Load trade offers for a team
     */
    async loadTradeOffers(teamNumber = null, includeCompleted = false) {
        try {
            let url = `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/team-trade/offers?include_completed=${includeCompleted}`;
            if (teamNumber) {
                url += `&team_number=${teamNumber}`;
            }
            
            const response = await fetch(url, { headers: this.gameAPI.headers });
            
            if (!response.ok) {
                throw new Error(`Failed to load trade offers: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.activeOffers = data.offers;
            return this.activeOffers;
        } catch (error) {
            console.error('[TradingManager] Error loading trade offers:', error);
            throw error;
        }
    }

    /**
     * Counter a trade offer
     */
    async counterTradeOffer(offerId, offering, requesting, message = null) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/team-trade/${offerId}/counter`,
                {
                    method: 'POST',
                    headers: this.gameAPI.headers,
                    body: JSON.stringify({
                        offering: offering,
                        requesting: requesting,
                        message: message
                    })
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to counter offer');
            }
            
            return data.offer;
        } catch (error) {
            console.error('[TradingManager] Error countering trade offer:', error);
            throw error;
        }
    }

    /**
     * Accept a trade offer
     */
    async acceptTradeOffer(offerId) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/team-trade/${offerId}/accept`,
                {
                    method: 'POST',
                    headers: this.gameAPI.headers
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to accept offer');
            }
            
            return data.offer;
        } catch (error) {
            console.error('[TradingManager] Error accepting trade offer:', error);
            throw error;
        }
    }

    /**
     * Reject a trade offer
     */
    async rejectTradeOffer(offerId) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/team-trade/${offerId}/reject`,
                {
                    method: 'POST',
                    headers: this.gameAPI.headers
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to reject offer');
            }
            
            return data.offer;
        } catch (error) {
            console.error('[TradingManager] Error rejecting trade offer:', error);
            throw error;
        }
    }

    /**
     * Cancel a trade offer
     */
    async cancelTradeOffer(offerId) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/team-trade/${offerId}`,
                {
                    method: 'DELETE',
                    headers: this.gameAPI.headers
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to cancel offer');
            }
            
            return data.offer;
        } catch (error) {
            console.error('[TradingManager] Error cancelling trade offer:', error);
            throw error;
        }
    }

    /**
     * Render price chart using Chart.js
     */
    renderPriceChart(canvasId, resource) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error('[TradingManager] Canvas not found:', canvasId);
            return;
        }

        const ctx = canvas.getContext('2d');
        const history = this.priceHistory[resource] || [];

        if (history.length === 0) {
            console.warn('[TradingManager] No price history available for', resource);
            return;
        }

        // Prepare data
        const labels = history.map(h => {
            const date = new Date(h.timestamp);
            return date.toLocaleTimeString();
        });
        
        const buyPrices = history.map(h => h.buy_price);
        const sellPrices = history.map(h => h.sell_price);

        // Destroy existing chart if any
        if (this.priceChart) {
            this.priceChart.destroy();
        }

        // Create new chart
        this.priceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Buy Price (Bank Buys)',
                        data: buyPrices,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Sell Price (Bank Sells)',
                        data: sellPrices,
                        borderColor: '#ef4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: `${resource.replace(/_/g, ' ').toUpperCase()} Price History`
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + ' currency';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Price (Currency)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                }
            }
        });
    }

    /**
     * Handle WebSocket trade events
     */
    handleTradeEvent(eventType, data) {
        console.log('[TradingManager] Trade event:', eventType, data);

        switch (eventType) {
            case 'bank_trade_completed':
                if (data.new_prices) {
                    this.currentPrices = data.new_prices;
                }
                // Refresh UI if needed
                if (typeof updateTradingUI === 'function') {
                    updateTradingUI();
                }
                break;

            case 'team_trade_offer_created':
            case 'team_trade_offer_countered':
            case 'team_trade_offer_rejected':
            case 'team_trade_offer_cancelled':
            case 'team_trade_completed':
                // Reload trade offers
                this.loadTradeOffers().catch(console.error);
                
                // Refresh UI if needed
                if (typeof updateTeamTradeUI === 'function') {
                    updateTeamTradeUI();
                }
                break;
        }
    }

    /**
     * Format resource name for display
     */
    formatResourceName(resource) {
        return resource.replace(/_/g, ' ')
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    /**
     * Get resource emoji
     */
    getResourceEmoji(resource) {
        const emojis = {
            'food': '🌾',
            'raw_materials': '⛏️',
            'electrical_goods': '⚡',
            'medical_goods': '🏥',
            'currency': '💰'
        };
        return emojis[resource] || '📦';
    }
}

    // ==================== Building Rental Methods ====================

    /**
     * Create a building rental offer
     */
    async createRentalOffer(fromTeam, toTeam, buildingType, rentalPrice, durationCycles = 1, message = null) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/building-rental/offer`,
                {
                    method: 'POST',
                    headers: this.gameAPI.headers,
                    body: JSON.stringify({
                        from_team: fromTeam,
                        to_team: toTeam,
                        building_type: buildingType,
                        rental_price: rentalPrice,
                        duration_cycles: durationCycles,
                        message: message
                    })
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to create rental offer');
            }
            
            return data.offer;
        } catch (error) {
            console.error('[TradingManager] Error creating rental offer:', error);
            throw error;
        }
    }

    /**
     * Load rental offers for a team
     */
    async loadRentalOffers(teamNumber = null, includeCompleted = false) {
        try {
            let url = `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/building-rental/offers?include_completed=${includeCompleted}`;
            if (teamNumber) {
                url += `&team_number=${teamNumber}`;
            }
            
            const response = await fetch(url, { headers: this.gameAPI.headers });
            
            if (!response.ok) {
                throw new Error(`Failed to load rental offers: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.rentalOffers = data.offers;
            return this.rentalOffers;
        } catch (error) {
            console.error('[TradingManager] Error loading rental offers:', error);
            throw error;
        }
    }

    /**
     * Load active rentals for a team
     */
    async loadActiveRentals(teamNumber) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/building-rental/active?team_number=${teamNumber}`,
                { headers: this.gameAPI.headers }
            );
            
            if (!response.ok) {
                throw new Error(`Failed to load active rentals: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.activeRentals = data.active_rentals;
            return this.activeRentals;
        } catch (error) {
            console.error('[TradingManager] Error loading active rentals:', error);
            throw error;
        }
    }

    /**
     * Counter a rental offer
     */
    async counterRentalOffer(offerId, rentalPrice, durationCycles = null, message = null) {
        try {
            const body = {
                rental_price: rentalPrice,
                message: message
            };
            
            if (durationCycles !== null) {
                body.duration_cycles = durationCycles;
            }
            
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/building-rental/${offerId}/counter`,
                {
                    method: 'POST',
                    headers: this.gameAPI.headers,
                    body: JSON.stringify(body)
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to counter rental offer');
            }
            
            return data.offer;
        } catch (error) {
            console.error('[TradingManager] Error countering rental offer:', error);
            throw error;
        }
    }

    /**
     * Accept a rental offer
     */
    async acceptRentalOffer(offerId) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/building-rental/${offerId}/accept`,
                {
                    method: 'POST',
                    headers: this.gameAPI.headers
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to accept rental offer');
            }
            
            return data.offer;
        } catch (error) {
            console.error('[TradingManager] Error accepting rental offer:', error);
            throw error;
        }
    }

    /**
     * Reject a rental offer
     */
    async rejectRentalOffer(offerId) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/building-rental/${offerId}/reject`,
                {
                    method: 'POST',
                    headers: this.gameAPI.headers
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to reject rental offer');
            }
            
            return data.offer;
        } catch (error) {
            console.error('[TradingManager] Error rejecting rental offer:', error);
            throw error;
        }
    }

    /**
     * Cancel a rental offer
     */
    async cancelRentalOffer(offerId) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/building-rental/${offerId}`,
                {
                    method: 'DELETE',
                    headers: this.gameAPI.headers
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to cancel rental offer');
            }
            
            return data.offer;
        } catch (error) {
            console.error('[TradingManager] Error cancelling rental offer:', error);
            throw error;
        }
    }

    /**
     * Use a rented building for production
     */
    async useRentedBuilding(offerId) {
        try {
            const response = await fetch(
                `${this.gameAPI.baseURL}/api/v2/trading/games/${this.gameCode}/building-rental/${offerId}/use`,
                {
                    method: 'POST',
                    headers: this.gameAPI.headers
                }
            );
            
            const data = await response.json();
            
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Failed to use rented building');
            }
            
            return data.offer;
        } catch (error) {
            console.error('[TradingManager] Error using rented building:', error);
            throw error;
        }
    }

    /**
     * Get building emoji
     */
    getBuildingEmoji(buildingType) {
        const emojis = {
            'farm': '🌾',
            'mine': '⛏️',
            'electrical_factory': '⚡',
            'medical_factory': '🏥',
            'school': '🏫',
            'hospital': '🏥',
            'restaurant': '🍽️',
            'infrastructure': '🏗️'
        };
        return emojis[buildingType] || '🏢';
    }

    /**
     * Format building name for display
     */
    formatBuildingName(buildingType) {
        return buildingType.replace(/_/g, ' ')
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
}
