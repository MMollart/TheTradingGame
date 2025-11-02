/**
 * Dashboard JavaScript - Handles all dashboard interactions
 */

// Global variables
let gameAPI = new GameAPI();
let gameWS = null;
let currentGameCode = null;
let currentPlayer = null;
let playerState = {};
let gameState = {};

// Initialize dashboard from URL parameters
function initDashboard() {
    const params = new URLSearchParams(window.location.search);
    currentGameCode = params.get('gameCode');
    const playerId = params.get('playerId');
    const playerName = params.get('playerName');
    const role = params.get('role');
    
    if (!currentGameCode || !playerId || !playerName || !role) {
        alert('Invalid dashboard link');
        window.location.href = 'index.html';
        return;
    }
    
    currentPlayer = {
        id: parseInt(playerId),
        name: playerName,
        role: role
    };
    
    // Update header
    document.getElementById('header-game-code').textContent = currentGameCode;
    document.getElementById('player-name-display').textContent = `${playerName} (${role})`;
    
    // Show appropriate dashboard
    showDashboard(role);
    
    // Connect WebSocket
    connectWebSocket();
    
    // Load initial data
    loadGameData();
}

function showDashboard(role) {
    // Hide all dashboards
    document.getElementById('host-dashboard').classList.add('hidden');
    document.getElementById('banker-dashboard').classList.add('hidden');
    document.getElementById('nation-dashboard').classList.add('hidden');
    
    // Show appropriate dashboard
    if (role === 'host') {
        document.getElementById('host-dashboard').classList.remove('hidden');
        setupHostDashboard();
    } else if (role === 'banker') {
        document.getElementById('banker-dashboard').classList.remove('hidden');
        setupBankerDashboard();
    } else {
        document.getElementById('nation-dashboard').classList.remove('hidden');
        setupNationDashboard();
    }
}

function connectWebSocket() {
    const statusIndicator = document.getElementById('connection-status');
    
    gameWS = new GameWebSocket(currentGameCode, currentPlayer.id);
    
    gameWS.on('connected', () => {
        statusIndicator.classList.add('connected');
        statusIndicator.classList.remove('disconnected');
        addEventLog('Connected to game');
    });
    
    gameWS.on('disconnected', () => {
        statusIndicator.classList.remove('connected');
        statusIndicator.classList.add('disconnected');
        addEventLog('Disconnected from game', 'error');
    });
    
    gameWS.on('game_state', (data) => {
        gameState = data.state;
        updateDashboard();
    });
    
    gameWS.on('state_updated', (data) => {
        gameState = data.state;
        updateDashboard();
    });
    
    gameWS.on('player_state_updated', (data) => {
        if (data.player_id === currentPlayer.id) {
            playerState = data.player_state;
            updateDashboard();
        }
        // Update in players list if host
        if (currentPlayer.role === 'host') {
            updatePlayersOverview();
        }
    });
    
    gameWS.on('game_event', (data) => {
        handleGameEvent(data);
    });
    
    gameWS.on('player_connected', (data) => {
        addEventLog(`Player ${data.player_id} connected (${data.role})`);
        if (currentPlayer.role === 'host') {
            updatePlayersOverview();
        }
    });
    
    gameWS.connect();
}

async function loadGameData() {
    try {
        const game = await gameAPI.getGame(currentGameCode);
        const players = await gameAPI.getPlayers(currentGameCode);
        
        gameState = game.game_state || {};
        
        // Find current player's state
        const player = players.find(p => p.id === currentPlayer.id);
        if (player && player.player_state) {
            playerState = player.player_state;
        }
        
        updateDashboard();
    } catch (error) {
        console.error('Failed to load game data:', error);
        addEventLog('Failed to load game data', 'error');
    }
}

function updateDashboard() {
    if (currentPlayer.role === 'host') {
        updateHostDashboard();
    } else if (currentPlayer.role === 'banker') {
        updateBankerDashboard();
    } else {
        updateNationDashboard();
    }
}

// ==================== HOST DASHBOARD ====================

function setupHostDashboard() {
    document.getElementById('start-game-btn').onclick = startGame;
    document.getElementById('pause-game-btn').onclick = pauseGame;
    document.getElementById('resume-game-btn').onclick = resumeGame;
    document.getElementById('end-game-btn').onclick = endGame;
}

function updateHostDashboard() {
    updatePlayersOverview();
    updateNationsOverview();
}

async function updatePlayersOverview() {
    try {
        const players = await gameAPI.getPlayers(currentGameCode);
        const playersList = document.getElementById('players-list');
        playersList.innerHTML = '';
        
        players.forEach(player => {
            const card = document.createElement('div');
            card.className = 'player-card';
            card.innerHTML = `
                <span>${player.player_name}</span>
                <span class="player-role-badge role-${player.role}">
                    ${player.role}${player.group_number ? ` ${player.group_number}` : ''}
                </span>
            `;
            playersList.appendChild(card);
        });
    } catch (error) {
        console.error('Failed to update players:', error);
    }
}

async function updateNationsOverview() {
    try {
        const players = await gameAPI.getPlayers(currentGameCode);
        const overviewDiv = document.getElementById('nations-overview');
        overviewDiv.innerHTML = '';
        
        players.filter(p => p.role === 'player' && p.player_state).forEach(player => {
            const state = player.player_state;
            const card = document.createElement('div');
            card.className = 'nation-card';
            card.innerHTML = `
                <h4>${state.name || `Nation ${player.group_number}`}</h4>
                <div class="nation-stat">
                    <span>💰 Currency:</span>
                    <span>${state.resources?.currency || 0}</span>
                </div>
                <div class="nation-stat">
                    <span>🌾 Food:</span>
                    <span>${state.resources?.food || 0}</span>
                </div>
                <div class="nation-stat">
                    <span>⚙️ Raw Materials:</span>
                    <span>${state.resources?.raw_materials || 0}</span>
                </div>
                <div class="nation-stat">
                    <span>⚡ Electrical:</span>
                    <span>${state.resources?.electrical_goods || 0}</span>
                </div>
                <div class="nation-stat">
                    <span>🏥 Medical:</span>
                    <span>${state.resources?.medical_goods || 0}</span>
                </div>
            `;
            overviewDiv.appendChild(card);
        });
    } catch (error) {
        console.error('Failed to update nations:', error);
    }
}

async function startGame() {
    try {
        await gameAPI.startGame(currentGameCode);
        addEventLog('Game started!', 'success');
        document.getElementById('start-game-btn').disabled = true;
        document.getElementById('pause-game-btn').disabled = false;
        document.getElementById('end-game-btn').disabled = false;
    } catch (error) {
        alert('Failed to start game: ' + error.message);
    }
}

async function pauseGame() {
    try {
        await gameAPI.pauseGame(currentGameCode);
        addEventLog('Game paused');
        document.getElementById('pause-game-btn').disabled = true;
        document.getElementById('resume-game-btn').disabled = false;
    } catch (error) {
        alert('Failed to pause game: ' + error.message);
    }
}

async function resumeGame() {
    try {
        await gameAPI.startGame(currentGameCode);
        addEventLog('Game resumed');
        document.getElementById('pause-game-btn').disabled = false;
        document.getElementById('resume-game-btn').disabled = true;
    } catch (error) {
        alert('Failed to resume game: ' + error.message);
    }
}

async function endGame() {
    if (!confirm('Are you sure you want to end the game?')) return;
    
    try {
        const result = await gameAPI.endGame(currentGameCode);
        addEventLog('Game ended!', 'success');
        
        // Show final scores
        showFinalScores(result.scores);
    } catch (error) {
        alert('Failed to end game: ' + error.message);
    }
}

function showFinalScores(scores) {
    const scoresHTML = Object.values(scores)
        .sort((a, b) => b.score.total - a.score.total)
        .map((s, i) => `
            <div style="margin: 10px 0; padding: 15px; background: ${i === 0 ? '#ffd700' : '#f8f9fa'}; border-radius: 8px;">
                <strong>${i + 1}. ${s.player_name} - ${s.nation}</strong><br>
                Total Score: ${s.score.total}<br>
                Resources: ${s.score.resource_value} | Buildings: ${s.score.building_value}
            </div>
        `).join('');
    
    alert('Game Complete!\n\nFinal Scores:\n' + scoresHTML);
}

// ==================== BANKER DASHBOARD ====================

function setupBankerDashboard() {
    if (playerState.bank_prices) {
        document.getElementById('price-food').value = playerState.bank_prices.food || 2;
        document.getElementById('price-raw-materials').value = playerState.bank_prices.raw_materials || 3;
        document.getElementById('price-electrical-goods').value = playerState.bank_prices.electrical_goods || 15;
        document.getElementById('price-medical-goods').value = playerState.bank_prices.medical_goods || 20;
    }
}

function updateBankerDashboard() {
    // Update bank inventory
    const inventoryDiv = document.getElementById('bank-inventory');
    if (playerState.bank_inventory) {
        inventoryDiv.innerHTML = '';
        Object.entries(playerState.bank_inventory).forEach(([resource, amount]) => {
            const item = document.createElement('div');
            item.className = 'resource-item';
            item.innerHTML = `
                <span class="resource-name">${formatResourceName(resource)}</span>
                <span class="resource-amount">${amount}</span>
            `;
            inventoryDiv.appendChild(item);
        });
    }
}

function updatePrice(resource) {
    const value = parseInt(document.getElementById(`price-${resource}`).value);
    
    if (!playerState.bank_prices) playerState.bank_prices = {};
    playerState.bank_prices[resource] = value;
    
    // Update state
    gameWS.send({
        type: 'update_player_state',
        player_state: playerState
    });
    
    addEventLog(`Updated ${formatResourceName(resource)} price to ${value}`);
}

function triggerFoodTax() {
    gameWS.send({
        type: 'event',
        event_type: 'food_tax',
        data: { triggered_by: currentPlayer.name }
    });
    
    addEventLog('Food tax applied to all nations', 'warning');
}

function triggerDisaster() {
    const nation = document.getElementById('disaster-nation').value;
    const type = document.getElementById('disaster-type').value;
    const severity = parseInt(document.getElementById('disaster-severity').value);
    
    gameWS.send({
        type: 'event',
        event_type: type,
        data: {
            target_nation: nation,
            severity: severity,
            triggered_by: currentPlayer.name
        }
    });
    
    addEventLog(`Triggered ${type} (severity ${severity}) on ${nation === 'all' ? 'all nations' : `Nation ${nation}`}`, 'error');
}

function openBankTrade() {
    const nation = document.getElementById('trade-nation').value;
    if (!nation) {
        alert('Please select a nation');
        return;
    }
    
    // Implementation for trading interface
    alert('Bank trading interface - to be implemented');
}

// ==================== NATION DASHBOARD ====================

function setupNationDashboard() {
    if (playerState.name) {
        document.getElementById('nation-title').textContent = playerState.name;
    }
}

function updateNationDashboard() {
    // Update resources
    const resourcesDiv = document.getElementById('nation-resources');
    if (playerState.resources) {
        resourcesDiv.innerHTML = '';
        Object.entries(playerState.resources).forEach(([resource, amount]) => {
            const item = document.createElement('div');
            item.className = 'resource-item';
            item.innerHTML = `
                <span class="resource-name">${formatResourceName(resource)}</span>
                <span class="resource-amount">${amount}</span>
            `;
            resourcesDiv.appendChild(item);
        });
    }
    
    // Update buildings
    const buildingsDiv = document.getElementById('nation-buildings');
    if (playerState.buildings) {
        buildingsDiv.innerHTML = '';
        Object.entries(playerState.buildings).forEach(([building, count]) => {
            const item = document.createElement('div');
            item.className = 'building-item';
            item.innerHTML = `
                <span>${formatBuildingName(building)}</span>
                <span class="resource-amount">${count}</span>
            `;
            buildingsDiv.appendChild(item);
            
            // Update production counts
            const countSpan = document.getElementById(`${building}-count`);
            if (countSpan) countSpan.textContent = count;
        });
    }
}

function startProduction(buildingType) {
    // Show challenge modal
    const modal = document.getElementById('challenge-modal');
    const description = document.getElementById('challenge-description');
    
    const challenges = {
        'farm': '20 Press-ups',
        'mine': '30 Sit-ups',
        'electrical_factory': '15 Burpees',
        'medical_factory': '25 Star Jumps'
    };
    
    description.textContent = challenges[buildingType];
    modal.classList.remove('hidden');
    modal.dataset.buildingType = buildingType;
}

function completeChallenge() {
    const modal = document.getElementById('challenge-modal');
    const buildingType = modal.dataset.buildingType;
    
    // Send production request
    gameWS.send({
        type: 'event',
        event_type: 'production_complete',
        data: {
            player_id: currentPlayer.id,
            building_type: buildingType,
            challenge_completed: true
        }
    });
    
    addEventLog(`Completed production at ${formatBuildingName(buildingType)}`, 'success');
    closeChallengeModal();
}

function closeChallengeModal() {
    document.getElementById('challenge-modal').classList.add('hidden');
}

function openTradeWindow(tradeType) {
    alert(`${tradeType === 'bank' ? 'Bank' : 'Nation'} trading interface - to be implemented`);
}

function closeTradeModal() {
    document.getElementById('trade-modal').classList.add('hidden');
}

// ==================== UTILITY FUNCTIONS ====================

function formatResourceName(resource) {
    const names = {
        'food': '🌾 Food',
        'raw_materials': '⚙️ Raw Materials',
        'electrical_goods': '⚡ Electrical Goods',
        'medical_goods': '🏥 Medical Goods',
        'currency': '💰 Currency'
    };
    return names[resource] || resource;
}

function formatBuildingName(building) {
    const names = {
        'farm': '🌾 Farm',
        'mine': '⛏️ Mine',
        'electrical_factory': '⚡ Electrical Factory',
        'medical_factory': '🏥 Medical Factory',
        'school': '🏫 School',
        'hospital': '🏥 Hospital',
        'restaurant': '🍽️ Restaurant',
        'infrastructure': '🏗️ Infrastructure'
    };
    return names[building] || building;
}

function addEventLog(message, type = 'info') {
    const logDiv = document.getElementById('events-log');
    if (!logDiv) return;
    
    const eventItem = document.createElement('div');
    eventItem.className = 'event-item';
    
    const now = new Date().toLocaleTimeString();
    eventItem.innerHTML = `
        <div class="event-time">${now}</div>
        <div>${message}</div>
    `;
    
    logDiv.insertBefore(eventItem, logDiv.firstChild);
    
    // Keep only last 50 events
    while (logDiv.children.length > 50) {
        logDiv.removeChild(logDiv.lastChild);
    }
}

function handleGameEvent(data) {
    const { event_type, data: eventData } = data;
    
    switch (event_type) {
        case 'food_tax':
            addEventLog('Food tax has been applied!', 'warning');
            break;
        case 'natural_disaster':
        case 'drought':
        case 'disease':
        case 'famine':
            addEventLog(`${event_type} event triggered! Severity: ${eventData.severity}`, 'error');
            break;
        case 'production_complete':
            if (eventData.player_id === currentPlayer.id) {
                addEventLog('Production completed successfully!', 'success');
            }
            break;
    }
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', initDashboard);
