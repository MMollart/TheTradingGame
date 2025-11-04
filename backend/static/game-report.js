/**
 * Game Report JavaScript
 */

let gameAPI = new GameAPI();
let gameCode = null;

async function loadGameReport() {
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
        
        console.log('Game:', game);
        console.log('Players:', players);
        console.log('Challenges:', challenges);
        
        // Populate statistics
        populateStats(game, players, challenges);
        
        // Populate challenges table
        populateChallengesTable(challenges, players);
        
        // Populate teams section
        populateTeamsSection(players);
        
        // Show report content
        document.getElementById('loading').style.display = 'none';
        document.getElementById('report-content').style.display = 'block';
        
    } catch (error) {
        console.error('Failed to load game report:', error);
        alert('Failed to load game report: ' + error.message);
        document.getElementById('loading').textContent = 'Failed to load report. Please try again.';
    }
}

function populateStats(game, players, challenges) {
    // Total players (exclude host)
    const totalPlayers = players.filter(p => p.role !== 'host').length;
    document.getElementById('total-players').textContent = totalPlayers;
    
    // Challenges statistics
    const completedChallenges = challenges.filter(c => c.status === 'completed').length;
    document.getElementById('challenges-completed').textContent = completedChallenges;
    document.getElementById('total-challenges').textContent = challenges.length;
    
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

function populateChallengesTable(challenges, players) {
    const tbody = document.getElementById('challenges-tbody');
    
    if (challenges.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No challenges were recorded during this game.</td></tr>';
        return;
    }
    
    // Sort by requested time (most recent first)
    challenges.sort((a, b) => new Date(b.requested_at) - new Date(a.requested_at));
    
    tbody.innerHTML = challenges.map(challenge => {
        // Find the team/player info
        const player = players.find(p => p.id === challenge.player_id);
        const teamName = player ? `Team ${player.group_number}` : 'Unknown';
        
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
                teams[player.group_number] = [];
            }
            teams[player.group_number].push(player);
        }
    });
    
    if (Object.keys(teams).length === 0) {
        container.innerHTML = '<div class="empty-state">No teams were formed during this game.</div>';
        return;
    }
    
    // Create team cards
    const teamCards = Object.keys(teams).sort((a, b) => a - b).map(teamNum => {
        const teamPlayers = teams[teamNum];
        const playersList = teamPlayers.map(p => p.player_name).join(', ');
        
        return `
            <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 15px;">
                <h3 style="margin: 0 0 10px 0; color: #2c3e50;">Team ${teamNum}</h3>
                <p style="margin: 0; color: #666;">
                    <strong>Members (${teamPlayers.length}):</strong> ${playersList}
                </p>
            </div>
        `;
    }).join('');
    
    container.innerHTML = teamCards;
}

// Load report when page loads
window.addEventListener('DOMContentLoaded', loadGameReport);
