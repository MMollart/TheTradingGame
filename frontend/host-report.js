/**
 * Host Report JavaScript
 * Comprehensive game report with team scores and rankings
 */

let gameAPI = new GameAPI();
let gameCode = null;

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

async function loadHostReport() {
    try {
        // Get game code from URL
        const params = new URLSearchParams(window.location.search);
        gameCode = params.get('gameCode');
        
        if (!gameCode) {
            alert('No game code provided');
            window.location.href = 'index.html';
            return;
        }
        
        // Display game code
        document.getElementById('game-code').textContent = gameCode;
        
        // Fetch game data
        const game = await gameAPI.getGame(gameCode);
        const players = await gameAPI.getPlayers(gameCode);
        const challenges = await gameAPI.getChallenges(gameCode);
        
        // console.log('Game:', game);
        // console.log('Players:', players);
        // console.log('Challenges:', challenges);
        
        // Get bank prices from game state or use defaults
        const bankPrices = game.game_state?.bank_prices || BANK_INITIAL_PRICES;
        
        // Calculate team scores
        const teamScores = calculateTeamScores(players, bankPrices);
        
        // Populate statistics
        populateStats(game, players, challenges, teamScores);
        
        // Populate team scores section
        populateTeamScores(teamScores, players);
        
        // Populate challenges table
        populateChallengesTable(challenges, players);
        
        // Populate teams section
        populateTeamsSection(players);
        
        // Show report content
        document.getElementById('loading').style.display = 'none';
        document.getElementById('report-content').style.display = 'block';
        
    } catch (error) {
        console.error('Failed to load host report:', error);
        alert('Failed to load host report: ' + error.message);
        document.getElementById('loading').textContent = 'Failed to load report. Please try again.';
    }
}

function calculateTeamScores(players, bankPrices) {
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

function populateStats(game, players, challenges, teamScores) {
    // Total teams
    const totalTeams = Object.keys(teamScores).length;
    document.getElementById('total-teams').textContent = totalTeams;
    
    // Total players (exclude host and banker)
    const totalPlayers = players.filter(p => p.role === 'player').length;
    document.getElementById('total-players').textContent = totalPlayers;
    
    // Challenges statistics
    const completedChallenges = challenges.filter(c => c.status === 'completed').length;
    document.getElementById('challenges-completed').textContent = `${completedChallenges} / ${challenges.length}`;
    
    // Game duration
    if (game.started_at && game.game_duration_minutes) {
        const durationHours = Math.floor(game.game_duration_minutes / 60);
        const durationMins = game.game_duration_minutes % 60;
        let durationText = '';
        if (durationHours > 0) {
            durationText = `${durationHours}h`;
            if (durationMins > 0) {
                durationText += ` ${durationMins}m`;
            }
        } else {
            durationText = `${durationMins}m`;
        }
        document.getElementById('game-duration').textContent = durationText;
    } else {
        document.getElementById('game-duration').textContent = '--';
    }
}

function populateTeamScores(teamScores, players) {
    const container = document.getElementById('team-scores-container');
    
    if (Object.keys(teamScores).length === 0) {
        container.innerHTML = '<div class="empty-state">No team scores available.</div>';
        return;
    }
    
    // Sort teams by total score (descending)
    const sortedTeams = Object.values(teamScores).sort((a, b) => b.total - a.total);
    
    const teamCards = sortedTeams.map((team, index) => {
        const rank = index + 1;
        const rankClass = rank <= 3 ? `rank-${rank}` : 'other';
        const cardClass = rank <= 3 ? `rank-${rank}` : '';
        
        let rankBadge = '';
        if (rank === 1) rankBadge = '🥇 1st Place';
        else if (rank === 2) rankBadge = '🥈 2nd Place';
        else if (rank === 3) rankBadge = '🥉 3rd Place';
        else rankBadge = `#${rank}`;
        
        return `
            <div class="team-score-card ${cardClass}">
                <div class="team-header">
                    <div class="team-name">${team.team_name || `Team ${team.team_number}`}</div>
                    <div class="team-rank ${rankClass}">${rankBadge}</div>
                </div>
                
                <div class="score-breakdown">
                    <div class="score-item">
                        <div class="score-item-label">💰 Resources</div>
                        <div class="score-item-value">${team.resource_value}</div>
                    </div>
                    <div class="score-item">
                        <div class="score-item-label">🏗️ Buildings</div>
                        <div class="score-item-value">${team.building_value}</div>
                    </div>
                    <div class="score-item">
                        <div class="score-item-label">🤝 Trade</div>
                        <div class="score-item-value">${team.trade_value}</div>
                    </div>
                    <div class="score-item">
                        <div class="score-item-label">❤️ Kindness</div>
                        <div class="score-item-value">${team.kindness_value}</div>
                    </div>
                </div>
                
                <div class="total-score">
                    <div class="total-score-label">Total Score</div>
                    <div class="total-score-value">${team.total}</div>
                </div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = teamCards;
}

function populateChallengesTable(challenges, players) {
    const tbody = document.getElementById('challenges-tbody');
    
    if (challenges.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No challenges were recorded during this game.</td></tr>';
        return;
    }
    
    // Sort by requested time (most recent first)
    challenges.sort((a, b) => new Date(b.requested_at) - new Date(a.requested_at));
    
    tbody.innerHTML = challenges.map(challenge => {
        // Find the player info
        const player = players.find(p => p.id === challenge.player_id);
        const teamName = player?.player_state?.team_name || (player ? `Team ${player.group_number}` : 'Unknown');
        const playerName = player?.player_name || 'Unknown';
        
        // Format status
        let statusClass = 'status-requested';
        let statusText = challenge.status;
        if (challenge.status === 'completed') {
            statusClass = 'status-completed';
            statusText = 'Completed';
        } else if (challenge.status === 'assigned') {
            statusClass = 'status-assigned';
            statusText = 'In Progress';
        } else if (challenge.status === 'requested') {
            statusText = 'Requested';
        }
        
        // Format dates
        const requestedDate = new Date(challenge.requested_at).toLocaleString();
        const completedDate = challenge.completed_at 
            ? new Date(challenge.completed_at).toLocaleString() 
            : '--';
        
        return `
            <tr>
                <td><strong>${teamName}</strong></td>
                <td>${playerName}</td>
                <td>${challenge.challenge_type || 'Challenge'}</td>
                <td>${challenge.challenge_description || 'No description'}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>${requestedDate}</td>
                <td>${completedDate}</td>
            </tr>
        `;
    }).join('');
}

function populateTeamsSection(players) {
    const container = document.getElementById('teams-container');
    
    // Group players by team
    const teams = {};
    players.forEach(player => {
        if (player.role === 'player' && player.group_number) {
            if (!teams[player.group_number]) {
                teams[player.group_number] = {
                    name: player.player_state?.team_name || `Team ${player.group_number}`,
                    members: []
                };
            }
            teams[player.group_number].members.push(player);
        }
    });
    
    if (Object.keys(teams).length === 0) {
        container.innerHTML = '<div class="empty-state">No teams were formed during this game.</div>';
        return;
    }
    
    // Create team cards
    const teamCards = Object.keys(teams).sort((a, b) => a - b).map(teamNum => {
        const team = teams[teamNum];
        const membersList = team.members.map(p => 
            `<li>${p.player_name}</li>`
        ).join('');
        
        return `
            <div class="team-card">
                <h3>${team.name}</h3>
                <p style="color: #666; margin-bottom: 15px;">
                    <strong>${team.members.length}</strong> member${team.members.length !== 1 ? 's' : ''}
                </p>
                <ul class="member-list">
                    ${membersList}
                </ul>
            </div>
        `;
    }).join('');
    
    container.innerHTML = teamCards;
}

// Load report when page loads
window.addEventListener('DOMContentLoaded', loadHostReport);
