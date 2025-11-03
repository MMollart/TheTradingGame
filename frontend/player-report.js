/**
 * Player Report JavaScript
 * Shows team-specific performance and individual contributions
 */

let gameAPI = new GameAPI();
let gameCode = null;
let playerId = null;

// Bank initial prices for score calculation
const BANK_INITIAL_PRICES = {
    "food": 2,
    "raw_materials": 3,
    "electrical_goods": 15,
    "medical_goods": 20,
    "currency": 1
};

// Building scores (double currency cost)
const BUILDING_SCORES = {
    "farm": 10,
    "mine": 20,
    "electrical_factory": 60,
    "medical_factory": 100,
    "school": 40,
    "hospital": 120,
    "restaurant": 80,
    "water_treatment": 60
};

// Resource icons
const RESOURCE_ICONS = {
    "food": "🌾",
    "raw_materials": "⛏️",
    "electrical_goods": "⚡",
    "medical_goods": "🏥",
    "currency": "💰"
};

// Building icons
const BUILDING_ICONS = {
    "farm": "🌾",
    "mine": "⛏️",
    "electrical_factory": "⚡",
    "medical_factory": "🏥",
    "school": "🏫",
    "hospital": "🏥",
    "restaurant": "🍽️",
    "water_treatment": "💧"
};

async function loadPlayerReport() {
    try {
        // Get game code and player ID from URL
        const params = new URLSearchParams(window.location.search);
        gameCode = params.get('gameCode');
        playerId = parseInt(params.get('playerId'));
        
        if (!gameCode || !playerId) {
            alert('Missing game code or player ID');
            window.location.href = 'index.html';
            return;
        }
        
        // Display game code
        document.getElementById('game-code').textContent = gameCode;
        
        // Fetch game data
        const game = await gameAPI.getGame(gameCode);
        const players = await gameAPI.getPlayers(gameCode);
        const challenges = await gameAPI.getChallenges(gameCode);
        
        console.log('Game:', game);
        console.log('Players:', players);
        console.log('Challenges:', challenges);
        
        // Find current player
        const currentPlayer = players.find(p => p.id === playerId);
        if (!currentPlayer) {
            alert('Player not found');
            window.location.href = 'index.html';
            return;
        }
        
        console.log('Current player:', currentPlayer);
        
        // Get bank prices from game state or use defaults
        const bankPrices = game.game_state?.bank_prices || BANK_INITIAL_PRICES;
        
        // Calculate all team scores for ranking
        const allTeamScores = calculateAllTeamScores(players, bankPrices);
        
        // Get current team's data
        const teamPlayers = players.filter(p => 
            p.role === 'player' && p.group_number === currentPlayer.group_number
        );
        const teamChallenges = challenges.filter(c => 
            teamPlayers.some(p => p.id === c.player_id)
        );
        
        // Calculate team score
        const teamScore = allTeamScores[currentPlayer.group_number] || {
            team_number: currentPlayer.group_number,
            team_name: currentPlayer.player_state?.team_name || `Team ${currentPlayer.group_number}`,
            resources: {},
            buildings: {},
            resource_value: 0,
            building_value: 0,
            trade_value: 0,
            kindness_value: 0,
            total: 0
        };
        
        // Display team name
        document.getElementById('team-name').textContent = teamScore.team_name;
        
        // Calculate ranking
        const ranking = calculateTeamRanking(allTeamScores, currentPlayer.group_number);
        
        // Populate all sections
        populateStats(currentPlayer, teamPlayers, teamChallenges, challenges, ranking);
        populateTeamScore(teamScore, ranking);
        populatePlayerContributions(currentPlayer, teamPlayers, challenges);
        populateResources(teamScore.resources);
        populateBuildings(teamScore.buildings);
        populateTeamMembers(currentPlayer, teamPlayers);
        
        // Show report content
        document.getElementById('loading').style.display = 'none';
        document.getElementById('report-content').style.display = 'block';
        
    } catch (error) {
        console.error('Failed to load player report:', error);
        alert('Failed to load player report: ' + error.message);
        document.getElementById('loading').textContent = 'Failed to load report. Please try again.';
    }
}

function calculateAllTeamScores(players, bankPrices) {
    const teams = {};
    
    players.forEach(player => {
        if (player.role === 'player' && player.group_number && player.player_state) {
            const teamNum = player.group_number;
            
            if (!teams[teamNum]) {
                teams[teamNum] = {
                    team_number: teamNum,
                    team_name: player.player_state.team_name || `Team ${teamNum}`,
                    resources: {},
                    buildings: {},
                    resource_value: 0,
                    building_value: 0,
                    trade_value: 0,
                    kindness_value: 0,
                    total: 0
                };
            }
            
            const team = teams[teamNum];
            const state = player.player_state;
            
            // Aggregate resources
            if (state.resources) {
                Object.keys(state.resources).forEach(resource => {
                    team.resources[resource] = (team.resources[resource] || 0) + (state.resources[resource] || 0);
                });
            }
            
            // Aggregate buildings
            if (state.buildings) {
                Object.keys(state.buildings).forEach(building => {
                    team.buildings[building] = (team.buildings[building] || 0) + (state.buildings[building] || 0);
                });
            }
            
            // Aggregate trade and kindness values
            team.trade_value += state.trade_value || 0;
            team.kindness_value += state.kindness_value || 0;
        }
    });
    
    // Calculate scores for each team
    Object.keys(teams).forEach(teamNum => {
        const team = teams[teamNum];
        
        // Calculate resource values
        Object.keys(team.resources).forEach(resource => {
            const price = bankPrices[resource] || BANK_INITIAL_PRICES[resource] || 0;
            team.resource_value += (team.resources[resource] || 0) * price;
        });
        
        // Calculate building values
        Object.keys(team.buildings).forEach(building => {
            team.building_value += (BUILDING_SCORES[building] || 0) * (team.buildings[building] || 0);
        });
        
        // Calculate total
        team.total = team.resource_value + team.building_value + team.trade_value + team.kindness_value;
    });
    
    return teams;
}

function calculateTeamRanking(allTeamScores, currentTeamNumber) {
    const sortedTeams = Object.values(allTeamScores).sort((a, b) => b.total - a.total);
    const rank = sortedTeams.findIndex(t => t.team_number === currentTeamNumber) + 1;
    return {
        rank: rank,
        total: sortedTeams.length
    };
}

function populateStats(currentPlayer, teamPlayers, teamChallenges, allChallenges, ranking) {
    // Team ranking
    let rankText = `#${ranking.rank}`;
    if (ranking.rank === 1) rankText = '🥇';
    else if (ranking.rank === 2) rankText = '🥈';
    else if (ranking.rank === 3) rankText = '🥉';
    document.getElementById('team-rank').textContent = rankText;
    
    // Player's challenges
    const playerChallenges = allChallenges.filter(c => 
        c.player_id === currentPlayer.id && c.status === 'completed'
    );
    document.getElementById('player-challenges').textContent = playerChallenges.length;
    
    // Team challenges
    const completedTeamChallenges = teamChallenges.filter(c => c.status === 'completed').length;
    document.getElementById('team-challenges').textContent = `${completedTeamChallenges} / ${teamChallenges.length}`;
    
    // Team members count
    document.getElementById('team-members-count').textContent = teamPlayers.length;
}

function populateTeamScore(teamScore, ranking) {
    document.getElementById('resource-value').textContent = teamScore.resource_value;
    document.getElementById('building-value').textContent = teamScore.building_value;
    document.getElementById('trade-value').textContent = teamScore.trade_value;
    document.getElementById('kindness-value').textContent = teamScore.kindness_value;
    document.getElementById('total-score').textContent = teamScore.total;
    
    // Ranking text
    let rankingText = '';
    if (ranking.rank === 1) {
        rankingText = `🥇 1st Place out of ${ranking.total} teams - Congratulations!`;
    } else if (ranking.rank === 2) {
        rankingText = `🥈 2nd Place out of ${ranking.total} teams - Great job!`;
    } else if (ranking.rank === 3) {
        rankingText = `🥉 3rd Place out of ${ranking.total} teams - Well done!`;
    } else {
        rankingText = `Ranked #${ranking.rank} out of ${ranking.total} teams`;
    }
    document.getElementById('ranking-text').textContent = rankingText;
}

function populatePlayerContributions(currentPlayer, teamPlayers, challenges) {
    const container = document.getElementById('contributions-list');
    
    // Calculate contributions for each team member
    const contributions = teamPlayers.map(player => {
        const playerChallenges = challenges.filter(c => 
            c.player_id === player.id && c.status === 'completed'
        );
        return {
            player: player,
            count: playerChallenges.length,
            isCurrent: player.id === currentPlayer.id
        };
    });
    
    // Sort by contribution count (descending)
    contributions.sort((a, b) => b.count - a.count);
    
    const html = contributions.map(contrib => `
        <div class="contribution-item">
            <div class="contribution-player ${contrib.isCurrent ? 'current' : ''}">
                ${contrib.player.player_name}
            </div>
            <div class="contribution-count">${contrib.count} challenge${contrib.count !== 1 ? 's' : ''}</div>
        </div>
    `).join('');
    
    container.innerHTML = html || '<div class="empty-state">No challenges completed yet</div>';
}

function populateResources(resources) {
    const container = document.getElementById('resources-container');
    
    if (!resources || Object.keys(resources).length === 0) {
        container.innerHTML = '<div class="empty-state">No resources yet</div>';
        return;
    }
    
    const html = Object.entries(resources).map(([resource, amount]) => `
        <div class="resource-item">
            <div class="resource-icon">${RESOURCE_ICONS[resource] || '📦'}</div>
            <div class="resource-name">${resource.replace(/_/g, ' ')}</div>
            <div class="resource-amount">${amount}</div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function populateBuildings(buildings) {
    const container = document.getElementById('buildings-container');
    
    if (!buildings || Object.keys(buildings).length === 0) {
        container.innerHTML = '<div class="empty-state">No buildings yet</div>';
        return;
    }
    
    const html = Object.entries(buildings).map(([building, count]) => `
        <div class="building-item">
            <div class="building-icon">${BUILDING_ICONS[building] || '🏢'}</div>
            <div class="building-name">${building.replace(/_/g, ' ')}</div>
            <div class="building-count">${count}</div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function populateTeamMembers(currentPlayer, teamPlayers) {
    const container = document.getElementById('members-container');
    
    const html = teamPlayers.map(player => `
        <div class="member-card ${player.id === currentPlayer.id ? 'current' : ''}">
            <div class="member-name">${player.player_name}</div>
        </div>
    `).join('');
    
    container.innerHTML = html;
}

// Load report when page loads
window.addEventListener('DOMContentLoaded', loadPlayerReport);
