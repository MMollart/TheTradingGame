/**
 * Trading Manager - Handles bank and team-to-team trading
 */

class TradingManager {
    constructor(gameCode, playerId, teamNumber, gameAPI, gameWS) {
        this.gameCode = gameCode;
        this.playerId = playerId;
        this.teamNumber = teamNumber;
        this.gameAPI = gameAPI;
        this.gameWS = gameWS;
        
        this.currentPrices = {};
        this.priceChart = null;
        this.teamTradeOffers = [];
        
        // Resource tracking for trade offers
        this.offerResources = {};  // {resource_type: quantity}
        this.requestResources = {};  // {resource_type: quantity}
    }
    
    async initialize() {
        await this.loadBankPrices();
        await this.loadTeamTrades();
    }
    
    // ==================== Bank Trading ====================
    
    async loadBankPrices() {
        try {
            const response = await fetch(`/api/v2/trading/${this.gameCode}/bank/prices`);
            const data = await response.json();
            this.currentPrices = data.prices;
            return this.currentPrices;
        } catch (error) {
            console.error('Failed to load bank prices:', error);
            return {};
        }
    }
    
    async loadPriceHistory(resourceType = null) {
        try {
            const url = resourceType 
                ? `/api/v2/trading/${this.gameCode}/bank/price-history?resource_type=${resourceType}&limit=50`
                : `/api/v2/trading/${this.gameCode}/bank/price-history?limit=50`;
            
            const response = await fetch(url);
            const data = await response.json();
            return data.history;
        } catch (error) {
            console.error('Failed to load price history:', error);
            return [];
        }
    }
    
    async executeBankTrade(resourceType, quantity, isBuying) {
        try {
            const response = await fetch(`/api/v2/trading/${this.gameCode}/bank/trade`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    game_code: this.gameCode,
                    team_number: this.teamNumber,
                    player_id: this.playerId,
                    resource_type: resourceType,
                    quantity: quantity,
                    is_buying: isBuying
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Trade failed');
            }
            
            const data = await response.json();
            this.currentPrices = data.new_prices;
            
            return data;
        } catch (error) {
            console.error('Bank trade failed:', error);
            throw error;
        }
    }
    
    calculateTradeCost(resourceType, quantity, isBuying) {
        if (!this.currentPrices[resourceType]) {
            return 0;
        }
        
        const priceInfo = this.currentPrices[resourceType];
        const unitPrice = isBuying ? priceInfo.buy_price : priceInfo.sell_price;
        
        return unitPrice * quantity;
    }
    
    async renderPriceChart(canvasId, resourceType) {
        const history = await this.loadPriceHistory(resourceType);
        
        if (history.length === 0) {
            return;
        }
        
        const canvas = document.getElementById(canvasId);
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart if any
        if (this.priceChart) {
            this.priceChart.destroy();
        }
        
        // Prepare data
        const labels = history.map(h => {
            const date = new Date(h.timestamp);
            return date.toLocaleTimeString();
        });
        
        const buyPrices = history.map(h => h.buy_price);
        const sellPrices = history.map(h => h.sell_price);
        const baselinePrices = history.map(h => h.baseline_price);
        
        // Create chart
        this.priceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Buy Price (Bank Sells)',
                        data: buyPrices,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.1
                    },
                    {
                        label: 'Sell Price (Bank Buys)',
                        data: sellPrices,
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.1
                    },
                    {
                        label: 'Baseline',
                        data: baselinePrices,
                        borderColor: 'rgb(201, 203, 207)',
                        backgroundColor: 'rgba(201, 203, 207, 0.1)',
                        borderDash: [5, 5],
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: `Price History - ${this.formatResourceName(resourceType)}`
                    },
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Price (Currency)'
                        }
                    }
                }
            }
        });
    }
    
    // ==================== Team Trading ====================
    
    async loadTeamTrades() {
        try {
            const response = await fetch(
                `/api/v2/trading/${this.gameCode}/team/${this.teamNumber}/offers?include_completed=false`
            );
            const data = await response.json();
            this.teamTradeOffers = data.offers;
            return this.teamTradeOffers;
        } catch (error) {
            console.error('Failed to load team trades:', error);
            return [];
        }
    }
    
    async createTradeOffer(toTeamNumber, offeredResources, requestedResources) {
        try {
            const response = await fetch(`/api/v2/trading/${this.gameCode}/team/offer`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    game_code: this.gameCode,
                    from_team_number: this.teamNumber,
                    to_team_number: toTeamNumber,
                    player_id: this.playerId,
                    offered_resources: offeredResources,
                    requested_resources: requestedResources
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create trade offer');
            }
            
            const data = await response.json();
            await this.loadTeamTrades();  // Refresh trades
            
            return data;
        } catch (error) {
            console.error('Failed to create trade offer:', error);
            throw error;
        }
    }
    
    async createCounterOffer(tradeId, counterOfferedResources, counterRequestedResources) {
        try {
            const response = await fetch(
                `/api/v2/trading/${this.gameCode}/team/offer/${tradeId}/counter`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        player_id: this.playerId,
                        counter_offered_resources: counterOfferedResources,
                        counter_requested_resources: counterRequestedResources
                    })
                }
            );
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create counter-offer');
            }
            
            const data = await response.json();
            await this.loadTeamTrades();  // Refresh trades
            
            return data;
        } catch (error) {
            console.error('Failed to create counter-offer:', error);
            throw error;
        }
    }
    
    async acceptTrade(tradeId, acceptCounter = false) {
        try {
            const response = await fetch(
                `/api/v2/trading/${this.gameCode}/team/offer/${tradeId}/accept`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        player_id: this.playerId,
                        accept_counter: acceptCounter
                    })
                }
            );
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to accept trade');
            }
            
            const data = await response.json();
            await this.loadTeamTrades();  // Refresh trades
            
            return data;
        } catch (error) {
            console.error('Failed to accept trade:', error);
            throw error;
        }
    }
    
    async rejectTrade(tradeId) {
        try {
            const response = await fetch(
                `/api/v2/trading/${this.gameCode}/team/offer/${tradeId}/reject`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        player_id: this.playerId
                    })
                }
            );
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to reject trade');
            }
            
            const data = await response.json();
            await this.loadTeamTrades();  // Refresh trades
            
            return data;
        } catch (error) {
            console.error('Failed to reject trade:', error);
            throw error;
        }
    }
    
    async cancelTrade(tradeId) {
        try {
            const response = await fetch(
                `/api/v2/trading/${this.gameCode}/team/offer/${tradeId}/cancel`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        player_id: this.playerId
                    })
                }
            );
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to cancel trade');
            }
            
            const data = await response.json();
            await this.loadTeamTrades();  // Refresh trades
            
            return data;
        } catch (error) {
            console.error('Failed to cancel trade:', error);
            throw error;
        }
    }
    
    // ==================== Utility Methods ====================
    
    formatResourceName(resource) {
        const names = {
            'food': '🌾 Food',
            'raw_materials': '⚙️ Raw Materials',
            'electrical_goods': '⚡ Electrical Goods',
            'medical_goods': '🏥 Medical Goods',
            'currency': '💰 Currency'
        };
        return names[resource] || resource;
    }
    
    formatResourcesDisplay(resources) {
        return Object.entries(resources)
            .map(([resource, amount]) => `${this.formatResourceName(resource)}: ${amount}`)
            .join(', ');
    }
}

// Make TradingManager available globally
window.TradingManager = TradingManager;
