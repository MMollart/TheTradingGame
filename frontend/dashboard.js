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
let currentGameStatus = 'waiting'; // Track game status (waiting, in_progress, paused, completed)

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
    
    // Check if user is authenticated and set token
    const authToken = localStorage.getItem('authToken');
    if (authToken) {
        gameAPI.setToken(authToken);
        console.log('Auth token loaded from localStorage');
    }
    
    // Update header
    document.getElementById('header-game-code').textContent = currentGameCode;
    document.getElementById('player-name-display').textContent = `${playerName} (${role})`;
    
    // Update big game code in welcome banner if it exists
    const bigGameCode = document.getElementById('big-game-code');
    if (bigGameCode) {
        bigGameCode.textContent = currentGameCode;
    }
    
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
    document.getElementById('nation-dashboard').classList.add('hidden');
    
    // Show appropriate dashboard
    if (role === 'host' || role === 'banker') {
        // Both hosts and bankers use the host-dashboard
        document.getElementById('host-dashboard').classList.remove('hidden');
        
        // Check if welcome banner should be shown (first time only, host-only)
        const welcomeBanner = document.getElementById('welcome-banner');
        const welcomeDismissed = sessionStorage.getItem('welcomeDismissed');
        if (welcomeBanner && role === 'host' && !welcomeDismissed) {
            welcomeBanner.classList.remove('hidden');
        } else if (welcomeBanner) {
            welcomeBanner.classList.add('hidden');
        }
        
        setupHostDashboard();
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
            refreshPendingPlayers();
            refreshUnassigned();
        } else if (currentPlayer.role === 'banker') {
            refreshPendingPlayers();
            refreshUnassigned();
        } else if (currentPlayer.role === 'player') {
            refreshTeamMembers();
        }
    });
    
    gameWS.on('player_joined', (data) => {
        addEventLog(`${data.player_name} joined the game${data.is_approved ? '' : ' (pending approval)'}`, 'info');
        if (currentPlayer.role === 'host' || currentPlayer.role === 'banker') {
            updatePlayersOverview();
            refreshPendingPlayers();
            refreshUnassigned();
        }
    });
    
    gameWS.connect();
}

async function loadGameData() {
    try {
        const game = await gameAPI.getGame(currentGameCode);
        const players = await gameAPI.getPlayers(currentGameCode);
        
        gameState = game.game_state || {};
        currentGameStatus = game.status || 'waiting';
        
        // Update test mode toggle state based on game status
        updateTestModeToggleState();
        
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

// Set number of teams for the game
async function setTeamsConfiguration() {
    const numTeamsInput = document.getElementById('num-teams-config');
    const numTeams = parseInt(numTeamsInput.value);
    
    if (!numTeams || numTeams < 1 || numTeams > 20) {
        alert('Please enter a valid number of teams (1-20)');
        return;
    }
    
    if (!confirm(`Configure game for ${numTeams} teams? This should be done BEFORE players join.`)) {
        return;
    }
    
    try {
        const result = await gameAPI.setNumberOfTeams(currentGameCode, numTeams);
        
        // Update status display
        const statusSpan = document.getElementById('teams-status');
        statusSpan.textContent = `✓ ${numTeams} teams configured`;
        statusSpan.style.color = '#4caf50';
        
        // Create team boxes
        createTeamBoxes(numTeams);
        
        alert(result.message);
    } catch (error) {
        console.error('Error setting teams:', error);
        alert('Failed to configure teams: ' + error.message);
    }
}

// Create team boxes for drag and drop
function createTeamBoxes(numTeams) {
    console.log('createTeamBoxes called with numTeams:', numTeams);
    const teamsGrid = document.getElementById('teams-grid');
    console.log('teamsGrid element:', teamsGrid);
    if (!teamsGrid) {
        console.error('teams-grid element not found!');
        return;
    }
    
    teamsGrid.innerHTML = '';
    
    for (let i = 1; i <= numTeams; i++) {
        const teamBox = document.createElement('div');
        teamBox.className = 'team-box';
        teamBox.dataset.teamNumber = i;
        
        // Enable drop
        teamBox.addEventListener('dragover', handleDragOver);
        teamBox.addEventListener('drop', handleDrop);
        teamBox.addEventListener('dragleave', handleDragLeave);
        
        teamBox.innerHTML = `
            <div class="team-box-header">Team ${i}</div>
            <div class="team-box-players" id="team-${i}-players">
                <p style="color: #999; font-style: italic; font-size: 14px;">Drop players here</p>
            </div>
        `;
        
        teamsGrid.appendChild(teamBox);
    }
    
    // Load existing team assignments
    loadTeamAssignments();
}

// Load and display current team assignments
async function loadTeamAssignments() {
    try {
        const players = await gameAPI.getPlayers(currentGameCode);
        
        // Clear all team boxes first
        for (let i = 1; i <= 20; i++) {
            const teamPlayersDiv = document.getElementById(`team-${i}-players`);
            if (teamPlayersDiv) {
                teamPlayersDiv.innerHTML = '<p style="color: #999; font-style: italic; font-size: 14px;">Drop players here</p>';
            }
        }
        
        // Add players to their teams
        players.forEach(player => {
            if (player.group_number && player.role === 'player') {
                addPlayerToTeamBox(player);
            }
        });
        
        // Update nations overview after loading assignments
        await updateNationsOverview();
    } catch (error) {
        console.error('Error loading team assignments:', error);
    }
}

// Add a player to a team box display
function addPlayerToTeamBox(player) {
    const teamPlayersDiv = document.getElementById(`team-${player.group_number}-players`);
    if (!teamPlayersDiv) return;
    
    // Remove placeholder text
    const placeholder = teamPlayersDiv.querySelector('p');
    if (placeholder) {
        teamPlayersDiv.innerHTML = '';
    }
    
    const playerItem = document.createElement('div');
    playerItem.className = 'team-player-item';
    playerItem.dataset.playerId = player.id;
    playerItem.innerHTML = `
        <span><strong>${player.player_name}</strong></span>
        <button class="remove-btn" onclick="unassignPlayer(${player.id}, '${player.player_name}')">✕</button>
    `;
    
    teamPlayersDiv.appendChild(playerItem);
}

// Drag and drop event handlers
function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

async function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    
    const playerId = parseInt(e.dataTransfer.getData('playerId'));
    const playerName = e.dataTransfer.getData('playerName');
    const teamNumber = parseInt(e.currentTarget.dataset.teamNumber);
    
    if (!playerId || !teamNumber) return;
    
    try {
        await gameAPI.assignPlayerGroup(currentGameCode, playerId, teamNumber);
        console.log(`Assigned ${playerName} to Team ${teamNumber}`);
        
        // Refresh displays
        await loadTeamAssignments();
        await refreshUnassigned();
        await updatePlayersOverview();
        await updateNationsOverview();
    } catch (error) {
        console.error('Error assigning player:', error);
        alert('Failed to assign player: ' + error.message);
    }
}

// Unassign a player from their team
async function unassignPlayer(playerId, playerName) {
    if (!confirm(`Remove ${playerName} from their team?`)) {
        return;
    }
    
    try {
        await gameAPI.unassignPlayerGroup(currentGameCode, playerId);
        console.log(`Unassigned ${playerName} from team`);
        
        addEventLog(`${playerName} removed from team`, 'info');
        
        // Refresh displays
        await loadTeamAssignments();
        await refreshUnassigned();
        await updateNationsOverview();
    } catch (error) {
        console.error('Error unassigning player:', error);
        const errorMessage = error.message || error.detail || JSON.stringify(error);
        alert('Failed to unassign player: ' + errorMessage);
    }
}

async function setupHostDashboard() {
    console.log('setupHostDashboard: Starting setup...');
    console.log('currentPlayer.role:', currentPlayer.role);
    
    // Show test mode toggle for host only
    showTestModeToggleForHost();
    
    // Configure tabs based on role
    const isHost = currentPlayer.role === 'host';
    const isBanker = currentPlayer.role === 'banker';
    
    console.log('isHost:', isHost, 'isBanker:', isBanker);
    
    // Reorder tabs based on role
    reorderTabsForRole(currentPlayer.role);
    
    // Show/hide Game Controls tab based on role
    const gameControlsTab = document.getElementById('tab-btn-controls');
    console.log('gameControlsTab found:', !!gameControlsTab);
    if (gameControlsTab) {
        if (isHost) {
            console.log('Showing Game Controls tab for host');
            gameControlsTab.style.display = 'inline-block';
        } else {
            console.log('Hiding Game Controls tab for non-host');
            gameControlsTab.style.display = 'none';
        }
    }
    
    // If banker, switch to Banker View tab by default (since they can't see Game Controls)
    if (isBanker) {
        // Hide the Game Controls tab content
        const controlsTab = document.getElementById('host-tab-controls');
        if (controlsTab) {
            controlsTab.classList.remove('active');
        }
        
        // Show Banker View tab instead
        const bankerTab = document.getElementById('host-tab-banker');
        if (bankerTab) {
            bankerTab.classList.add('active');
        }
        
        // Update tab button active state
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        const bankerTabBtn = document.getElementById('tab-btn-banker');
        if (bankerTabBtn) {
            bankerTabBtn.classList.add('active');
        }
        
        // Load banker view
        loadHostBankerView();
    }
    
    // Show host controls (if element exists) - only for hosts
    const hostControls = document.getElementById('host-controls');
    if (hostControls) {
        hostControls.style.display = isHost ? 'block' : 'none';
    }
    
    // Show team assignment section
    const teamAssignment = document.getElementById('team-assignment');
    if (teamAssignment) {
        teamAssignment.style.display = 'block';
    }
    
    // Show pending approvals section
    const pendingApprovals = document.getElementById('pending-approvals');
    if (pendingApprovals) {
        pendingApprovals.style.display = 'block';
    }
    
    // Show role assignment section
    const roleAssignment = document.getElementById('role-assignment');
    if (roleAssignment) {
        roleAssignment.style.display = 'block';
    }
    
    // Load all host-specific data
    updatePlayersOverview();
    refreshUnassigned();
    refreshPendingPlayers();
    
    // Try to load team configuration if it exists
    console.log('setupHostDashboard: About to call loadGameAndCreateTeamBoxes...');
    await loadGameAndCreateTeamBoxes();
    console.log('setupHostDashboard: loadGameAndCreateTeamBoxes completed');
    
    // Update nations/teams overview after team assignments are loaded
    await updateNationsOverview();
    
    updateControlButtons();
    console.log('setupHostDashboard: Setup complete');
}

// Update game control button states based on current game status
function updateControlButtons() {
    const startBtn = document.getElementById('start-game-btn');
    const pauseBtn = document.getElementById('pause-game-btn');
    const resumeBtn = document.getElementById('resume-game-btn');
    const endBtn = document.getElementById('end-game-btn');
    
    if (!startBtn || !pauseBtn || !resumeBtn || !endBtn) {
        console.warn('updateControlButtons: Some control buttons not found in DOM');
        return;
    }
    
    // Get current game status from the global game object if available
    // For now, default to 'waiting' state (game not started)
    // This will be enhanced when we add game status tracking
    const gameStatus = 'waiting';
    
    switch(gameStatus) {
        case 'waiting':
            startBtn.disabled = false;
            pauseBtn.disabled = true;
            resumeBtn.disabled = true;
            endBtn.disabled = true;
            break;
        case 'in_progress':
            startBtn.disabled = true;
            pauseBtn.disabled = false;
            resumeBtn.disabled = true;
            endBtn.disabled = false;
            break;
        case 'paused':
            startBtn.disabled = true;
            pauseBtn.disabled = true;
            resumeBtn.disabled = false;
            endBtn.disabled = false;
            break;
        case 'completed':
            startBtn.disabled = true;
            pauseBtn.disabled = true;
            resumeBtn.disabled = true;
            endBtn.disabled = true;
            break;
    }
}

// Load game data and create team boxes if teams are configured
async function loadGameAndCreateTeamBoxes() {
    try {
        console.log('loadGameAndCreateTeamBoxes: Loading game config...');
        const game = await gameAPI.getGame(currentGameCode);
        console.log('Game data:', game);
        console.log('num_teams:', game.num_teams);
        
        if (game.num_teams && game.num_teams > 0) {
            console.log('Creating team boxes for', game.num_teams, 'teams');
            // Update the input and status
            const numTeamsInput = document.getElementById('num-teams-config');
            if (numTeamsInput) {
                numTeamsInput.value = game.num_teams;
            }
            
            const statusSpan = document.getElementById('teams-status');
            if (statusSpan) {
                statusSpan.textContent = `✓ ${game.num_teams} teams configured`;
                statusSpan.style.color = '#4caf50';
            }
            
            // Create the team boxes
            createTeamBoxes(game.num_teams);
        } else {
            console.log('No teams configured yet (num_teams is', game.num_teams, ')');
        }
    } catch (error) {
        console.error('Error loading game configuration:', error);
    }
}

function updateHostDashboard() {
    updatePlayersOverview();
    updateNationsOverview();
    refreshUnassigned();
}

// Team Assignment Functions
// Refresh the list of unassigned players
async function refreshUnassigned() {
    try {
        const unassignedList = document.getElementById('unassigned-players-list');
        if (!unassignedList) {
            console.log('refreshUnassigned: unassigned-players-list element not found');
            return;
        }

        console.log('Fetching unassigned players for game:', currentGameCode);
        const response = await gameAPI.getUnassignedPlayers(currentGameCode);
        console.log('Unassigned players response:', response);
        const players = response.players || [];
        console.log('Extracted players array:', players);
        
        // Update count
        const countSpan = document.getElementById('unassigned-count');
        if (countSpan) {
            countSpan.textContent = players.length;
        }
        
        if (players.length === 0) {
            unassignedList.innerHTML = '<p style="color: #666; font-style: italic;">All players have been assigned to teams</p>';
        } else {
            unassignedList.innerHTML = players.map(player => `
                <div class="unassigned-player-item" 
                     draggable="true" 
                     data-player-id="${player.id}" 
                     data-player-name="${player.name}"
                     ondragstart="handleDragStart(event)">
                    <span><strong>${player.name}</strong> (ID: ${player.id})</span>
                    <span style="color: #999; font-size: 12px;">🖱️ Drag to team</span>
                </div>
            `).join('');
        }
        
        // Update auto-assign button text
        await updateAutoAssignButtonText();
    } catch (error) {
        console.error('Error refreshing unassigned players:', error);
    }
}

// Handle drag start for players
function handleDragStart(e) {
    const playerId = e.currentTarget.dataset.playerId;
    const playerName = e.currentTarget.dataset.playerName;
    
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('playerId', playerId);
    e.dataTransfer.setData('playerName', playerName);
    
    e.currentTarget.classList.add('dragging');
    
    // Remove dragging class when drag ends
    e.currentTarget.addEventListener('dragend', function() {
        e.currentTarget.classList.remove('dragging');
    }, { once: true });
}

// Refresh the list of pending approvals
async function refreshPendingPlayers() {
    try {
        const pendingList = document.getElementById('pending-players-list');
        if (!pendingList) return;

        const response = await gameAPI.getPendingPlayers(currentGameCode);
        const players = Array.isArray(response) ? response : (response.players || []);
        
        // Update count
        const countSpan = document.getElementById('pending-count');
        if (countSpan) {
            countSpan.textContent = players.length;
        }
        
        if (players.length === 0) {
            pendingList.innerHTML = '<p style="color: #666; font-style: italic;">No players awaiting approval</p>';
            return;
        }

        pendingList.innerHTML = players.map(player => `
            <div class="pending-player-item">
                <div class="player-info">
                    <strong>${player.player_name}</strong>
                    <span style="font-size: 12px; color: #666;">Guest User - ID: ${player.id}</span>
                </div>
                <button class="approve-btn" onclick="approvePlayerAction(${player.id}, '${player.player_name}')">
                    Approve
                </button>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error refreshing pending players:', error);
    }
}

// Approve a player
async function approvePlayerAction(playerId, playerName) {
    try {
        await gameAPI.approvePlayer(currentGameCode, playerId);
        console.log(`Approved player: ${playerName}`);
        
        // Refresh pending list and players overview
        await refreshPendingPlayers();
        await updatePlayersOverview();
        
        // Show success message
        alert(`${playerName} has been approved and can now join the game.`);
    } catch (error) {
        console.error('Error approving player:', error);
        alert('Failed to approve player: ' + error.message);
    }
}

// Refresh the role assignment list
// Toggle a player's role between player and banker
async function togglePlayerRole(playerId, playerName, currentRole) {
    // Toggle between player and banker
    const newRole = currentRole === 'player' ? 'banker' : 'player';
    
    try {
        // Backend automatically removes bankers/hosts from teams
        await gameAPI.assignPlayerRole(currentGameCode, playerId, newRole);
        console.log(`Changed ${playerName}'s role from ${currentRole} to ${newRole}`);
        
        // Refresh the players list and team assignments
        await updatePlayersOverview();
        await refreshUnassigned();
        await updateNationsOverview();
        await loadTeamAssignments();
        
        const message = newRole === 'banker' 
            ? `${playerName} promoted to banker and removed from team`
            : `${playerName} demoted to player`;
        addEventLog(message, 'info');
    } catch (error) {
        console.error('Error changing player role:', error);
        alert('Failed to change role: ' + error.message);
    }
}

// Remove a player from the game entirely
async function removePlayerFromGame(playerId, playerName) {
    if (!confirm(`⚠️ Remove ${playerName} from the game?\n\nThis will permanently remove them from the game session. They will need to rejoin with the game code if they want to play again.`)) {
        return;
    }
    
    try {
        await gameAPI.removePlayerFromGame(currentGameCode, playerId);
        console.log(`Removed ${playerName} from game`);
        
        addEventLog(`${playerName} removed from game`, 'warning');
        
        // Refresh all displays
        await updatePlayersOverview();
        await refreshUnassigned();
        await refreshPendingPlayers();
        await updateNationsOverview();
        await loadTeamAssignments();
    } catch (error) {
        console.error('Error removing player:', error);
        const errorMessage = error.message || error.detail || JSON.stringify(error);
        alert('Failed to remove player: ' + errorMessage);
    }
}

async function clearAllPlayers() {
    if (!confirm(`⚠️ Remove ALL players from the lobby?\n\nThis will permanently remove all players (except the host) from the game. They will need to rejoin with the game code if they want to play again.\n\nThis action cannot be undone.`)) {
        return;
    }
    
    try {
        const result = await gameAPI.clearAllPlayersFromLobby(currentGameCode);
        console.log(`Cleared ${result.deleted_count} players from lobby`);
        
        addEventLog(`Cleared ${result.deleted_count} players from lobby`, 'warning');
        
        // Refresh all displays
        await updatePlayersOverview();
        await refreshUnassigned();
        await refreshPendingPlayers();
        await updateNationsOverview();
        await loadTeamAssignments();
    } catch (error) {
        console.error('Error clearing lobby:', error);
        const errorMessage = error.message || error.detail || JSON.stringify(error);
        alert('Failed to clear lobby: ' + errorMessage);
    }
}

async function autoAssignTeams() {
    // Get configured number of teams from the game
    try {
        const game = await gameAPI.getGame(currentGameCode);
        const numTeams = game.num_teams;
        
        if (!numTeams || numTeams < 1) {
            alert('Please configure the number of teams first using the Team Configuration section above.');
            return;
        }
        
        if (!confirm(`Assign all unassigned players to ${numTeams} teams with random nation types?`)) {
            return;
        }
        
        const result = await gameAPI.autoAssignGroups(currentGameCode, numTeams);
        
        if (result.assigned_count === 0) {
            alert('No unassigned players found');
            return;
        }
        
        addEventLog(`Auto-assigned ${result.assigned_count} players to ${numTeams} teams`, 'success');
        alert(`Successfully assigned ${result.assigned_count} players!\n\nTeam Distribution:\n${Object.entries(result.group_distribution).map(([team, count]) => `Team ${team}: ${count} players`).join('\n')}`);
        
        // Refresh displays
        await loadTeamAssignments();
        await refreshUnassigned();
        await updatePlayersOverview();
        await updateNationsOverview();
    } catch (error) {
        console.error('Failed to auto-assign teams:', error);
        alert('Failed to assign teams: ' + error.message);
        addEventLog('Auto-assignment failed', 'error');
    }
}

async function promptManualAssign(playerId, playerName) {
    const teamNumber = prompt(`Assign ${playerName} to which team number?`);
    
    if (!teamNumber) {
        return;
    }
    
    const teamNum = parseInt(teamNumber);
    if (isNaN(teamNum) || teamNum < 1) {
        alert('Please enter a valid team number (must be 1 or greater)');
        return;
    }
    
    try {
        await gameAPI.assignPlayerGroup(currentGameCode, playerId, teamNum);
        addEventLog(`Assigned ${playerName} to Team ${teamNum}`, 'success');
        
        // Refresh displays
        refreshUnassigned();
        updatePlayersOverview();
    } catch (error) {
        console.error('Failed to assign player:', error);
        alert('Failed to assign player: ' + error.message);
        addEventLog('Manual assignment failed', 'error');
    }
}

// Test Mode: Create Fake Players
async function createFakePlayers() {
    const numPlayers = parseInt(document.getElementById('num-fake-players').value);
    
    if (numPlayers < 1 || numPlayers > 50) {
        alert('Please enter a number between 1 and 50');
        return;
    }
    
    if (!confirm(`Create ${numPlayers} fake players for testing?`)) {
        return;
    }
    
    try {
        const result = await gameAPI.createFakePlayers(currentGameCode, numPlayers);
        
        addEventLog(`Created ${result.created_count} fake players`, 'success');
        alert(`Successfully created ${result.created_count} fake players!\n\nNames:\n${result.player_names.slice(0, 10).join('\n')}${result.player_names.length > 10 ? '\n...' : ''}`);
        
        // Refresh displays
        refreshUnassigned();
        updatePlayersOverview();
    } catch (error) {
        console.error('Failed to create fake players:', error);
        alert('Failed to create fake players: ' + error.message);
        addEventLog('Failed to create fake players', 'error');
    }
}

async function updatePlayersOverview() {
    try {
        const players = await gameAPI.getPlayers(currentGameCode);
        const playersList = document.getElementById('players-list');
        playersList.innerHTML = '';
        
        if (players.length === 0) {
            playersList.innerHTML = '<p style="color: #999; font-style: italic;">No players yet</p>';
            return;
        }
        
        players.forEach(player => {
            const card = document.createElement('div');
            card.className = 'player-card';
            
            // Add visual indicator for unapproved players
            const approvalBadge = !player.is_approved ? 
                '<span style="background: #ff9800; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-left: 8px;">⏳ Pending</span>' : '';
            
            // Only show role for host - otherwise allow clicking to toggle
            const isHost = player.role === 'host';
            const roleDisplay = player.role;
            const teamDisplay = player.group_number ? ` - Team ${player.group_number}` : '';
            
            // Show remove button for host (but not for the host themselves)
            const isCurrentHost = currentPlayer && currentPlayer.role === 'host';
            const removeButton = (isCurrentHost && !isHost) ? 
                `<button class="remove-player-btn" onclick="removePlayerFromGame(${player.id}, '${player.player_name}')" title="Remove player from game">✕</button>` : '';
            
            card.innerHTML = `
                <span>${player.player_name}${approvalBadge}</span>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="player-role-badge role-${player.role} ${!isHost ? 'clickable' : ''}" 
                          ${!isHost ? `onclick="togglePlayerRole(${player.id}, '${player.player_name}', '${player.role}')"` : ''}
                          ${!isHost ? 'title="Click to toggle between player and banker"' : ''}>
                        ${roleDisplay}${teamDisplay}
                    </span>
                    ${removeButton}
                </div>
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
        
        // Check if game has started (players have player_state with resources)
        const playersWithState = players.filter(p => p.role === 'player' && p.player_state && p.player_state.resources);
        
        if (playersWithState.length > 0) {
            // Show nation cards with resources (game is running)
            playersWithState.forEach(player => {
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
        } else {
            // Show team assignments (pre-game setup)
            const teamPlayers = players.filter(p => p.role === 'player' && p.group_number);
            const unassignedPlayers = players.filter(p => p.role === 'player' && !p.group_number);
            const teams = {};
            
            // Group players by team
            teamPlayers.forEach(player => {
                if (!teams[player.group_number]) {
                    teams[player.group_number] = [];
                }
                teams[player.group_number].push(player);
            });
            
            // Display teams
            if (Object.keys(teams).length > 0 || unassignedPlayers.length > 0) {
                // Display assigned teams
                Object.keys(teams).sort((a, b) => a - b).forEach(teamNum => {
                    const card = document.createElement('div');
                    card.className = 'nation-card';
                    const teamMembers = teams[teamNum].map(p => p.player_name).join(', ');
                    card.innerHTML = `
                        <h4>Team ${teamNum}</h4>
                        <div class="nation-stat">
                            <span>👥 Members (${teams[teamNum].length}):</span>
                        </div>
                        <div style="padding: 8px; color: #666; font-size: 14px;">
                            ${teamMembers}
                        </div>
                    `;
                    overviewDiv.appendChild(card);
                });
                
                // Display unassigned players as a separate "team"
                if (unassignedPlayers.length > 0) {
                    const card = document.createElement('div');
                    card.className = 'nation-card';
                    card.style.border = '2px dashed #ff9800';
                    card.style.background = '#fff3e0';
                    const unassignedNames = unassignedPlayers.map(p => p.player_name).join(', ');
                    card.innerHTML = `
                        <h4>⚠️ Unassigned Players</h4>
                        <div class="nation-stat">
                            <span>👥 Awaiting Assignment (${unassignedPlayers.length}):</span>
                        </div>
                        <div style="padding: 8px; color: #e65100; font-size: 14px;">
                            ${unassignedNames}
                        </div>
                    `;
                    overviewDiv.appendChild(card);
                }
            } else {
                overviewDiv.innerHTML = '<p style="color: #666; font-style: italic;">No teams assigned yet. Assign players to teams to see them here.</p>';
            }
        }
    } catch (error) {
        console.error('Failed to update nations:', error);
    }
}

async function startGame() {
    try {
        await gameAPI.startGame(currentGameCode);
        currentGameStatus = 'in_progress';
        addEventLog('Game started!', 'success');
        document.getElementById('start-game-btn').disabled = true;
        document.getElementById('pause-game-btn').disabled = false;
        document.getElementById('end-game-btn').disabled = false;
        
        // Disable test mode when game starts
        updateTestModeToggleState();
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

// ==================== BANKER FUNCTIONS ====================

function updatePrice(resource, source = 'banker') {
    const prefix = source === 'host' ? 'host-' : '';
    const value = parseInt(document.getElementById(`${prefix}price-${resource}`).value);
    
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

function triggerDisaster(source = 'banker') {
    const prefix = source === 'host' ? 'host-' : '';
    const nation = document.getElementById(`${prefix}disaster-nation`).value;
    const type = document.getElementById(`${prefix}disaster-type`).value;
    const severity = parseInt(document.getElementById(`${prefix}disaster-severity`).value);
    
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

function openBankTrade(source = 'banker') {
    const prefix = source === 'host' ? 'host-' : '';
    const nation = document.getElementById(`${prefix}trade-nation`).value;
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
    // Load team members
    refreshTeamMembers();
}

// Refresh team members list for player dashboard
async function refreshTeamMembers() {
    try {
        const teamMembersList = document.getElementById('team-members-list');
        if (!teamMembersList) return;

        const allPlayers = await gameAPI.getPlayers(currentGameCode);
        
        // Filter to only show players with the same group_number as current player
        // First, find current player to get their group number
        const currentPlayerData = allPlayers.find(p => p.id === currentPlayer.id);
        
        if (!currentPlayerData || !currentPlayerData.group_number) {
            teamMembersList.innerHTML = '<p style="color: #666; font-style: italic;">You have not been assigned to a team yet. Please wait for the host or banker to assign you.</p>';
            return;
        }
        
        const teamMembers = allPlayers.filter(p => 
            p.group_number === currentPlayerData.group_number && 
            p.role === 'player'
        );
        
        if (teamMembers.length === 0) {
            teamMembersList.innerHTML = '<p style="color: #666; font-style: italic;">No team members yet</p>';
            return;
        }

        teamMembersList.innerHTML = teamMembers.map(player => {
            const isCurrentPlayer = player.id === currentPlayer.id;
            const statusClass = player.is_connected ? '' : 'offline';
            const statusText = player.is_connected ? '🟢 Online' : '⚪ Offline';
            
            return `
                <div class="team-member-item ${isCurrentPlayer ? 'is-current-player' : ''}">
                    <span class="member-icon">${isCurrentPlayer ? '👤' : '👥'}</span>
                    <div class="member-info">
                        <strong>${player.player_name}</strong>
                        ${isCurrentPlayer ? '<span style="font-size: 12px; color: #1976d2;"> (You)</span>' : ''}
                    </div>
                    <span class="member-status ${statusClass}">${statusText}</span>
                </div>
            `;
        }).join('');
        
        // Update nation title to include team number
        const titleElement = document.getElementById('nation-title');
        if (titleElement && currentPlayerData.group_number) {
            titleElement.textContent = `Team ${currentPlayerData.group_number} - ${playerState.name || 'Nation Dashboard'}`;
        }
    } catch (error) {
        console.error('Error refreshing team members:', error);
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

// Copy game code to clipboard
function copyGameCode() {
    const gameCode = currentGameCode;
    
    // Try modern clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(gameCode).then(() => {
            alert(`Game code ${gameCode} copied to clipboard!`);
        }).catch(err => {
            // Fallback for older browsers
            fallbackCopyTextToClipboard(gameCode);
        });
    } else {
        // Fallback for older browsers
        fallbackCopyTextToClipboard(gameCode);
    }
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.top = '-9999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            alert(`Game code ${text} copied to clipboard!`);
        } else {
            alert(`Game code: ${text}\n\nPlease copy manually.`);
        }
    } catch (err) {
        alert(`Game code: ${text}\n\nPlease copy manually.`);
    }
    
    document.body.removeChild(textArea);
}

// Dismiss welcome banner
function dismissWelcome() {
    const banner = document.getElementById('welcome-banner');
    if (banner) {
        banner.classList.add('hidden');
        // Store in sessionStorage so it doesn't show again this session
        sessionStorage.setItem('welcomeDismissed', 'true');
    }
}

// Toggle card collapse/expand
function toggleCard(cardId) {
    const card = document.getElementById(cardId);
    if (!card) return;
    
    const content = card.querySelector('.card-content');
    const toggle = card.querySelector('.card-toggle');
    
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        if (toggle) toggle.textContent = '▼';
    } else {
        content.classList.add('collapsed');
        if (toggle) toggle.textContent = '▶';
    }
}

// Initialize collapsible cards
function initCollapsibleCards() {
    const cards = document.querySelectorAll('.card[id]');
    cards.forEach(card => {
        const h3 = card.querySelector('h3');
        if (h3 && !h3.querySelector('.card-toggle')) {
            // Wrap content in a collapsible div
            const content = document.createElement('div');
            content.className = 'card-content';
            
            // Move all children except h3 into the content div
            const children = Array.from(card.children).filter(child => child !== h3);
            children.forEach(child => content.appendChild(child));
            card.appendChild(content);
            
            // Add toggle button to header
            const toggle = document.createElement('span');
            toggle.className = 'card-toggle';
            toggle.textContent = '▼';
            
            // Make the whole header clickable (not just toggle)
            h3.style.cursor = 'pointer';
            h3.style.display = 'flex';
            h3.style.justifyContent = 'space-between';
            h3.style.alignItems = 'center';
            h3.style.userSelect = 'none'; // Prevent text selection when clicking
            h3.appendChild(toggle);
            
            // Click handler on the entire h3
            h3.onclick = (e) => {
                e.stopPropagation();
                toggleCard(card.id);
            };
        }
    });
}

// Game Settings Modal Functions
function openGameSettings() {
    const modal = document.getElementById('settings-modal');
    modal.classList.add('show');
    
    // Load current game configuration
    loadGameSettings();
}

function closeGameSettings() {
    const modal = document.getElementById('settings-modal');
    modal.classList.remove('show');
}

async function loadGameSettings() {
    try {
        const game = await gameAPI.getGame(currentGameCode);
        
        // Update team configuration input
        const teamsInput = document.getElementById('num-teams-modal');
        if (teamsInput && game.num_teams) {
            teamsInput.value = game.num_teams;
        }
        
        // Update status
        const statusSpan = document.getElementById('teams-status-modal');
        if (statusSpan && game.num_teams) {
            statusSpan.textContent = `✓ Currently: ${game.num_teams} teams`;
            statusSpan.style.color = '#4caf50';
        }
    } catch (error) {
        console.error('Error loading game settings:', error);
    }
}

async function applyTeamConfiguration() {
    const numTeams = parseInt(document.getElementById('num-teams-modal').value);
    
    if (numTeams < 1 || numTeams > 20) {
        alert('Number of teams must be between 1 and 20');
        return;
    }
    
    try {
        await gameAPI.setNumTeams(currentGameCode, numTeams);
        
        const statusSpan = document.getElementById('teams-status-modal');
        if (statusSpan) {
            statusSpan.textContent = `✓ Saved: ${numTeams} teams`;
            statusSpan.style.color = '#4caf50';
        }
        
        addEventLog(`Team configuration updated: ${numTeams} teams`, 'info');
        
        // Reload team boxes
        await loadGameAndCreateTeamBoxes();
        
        alert(`Team configuration saved: ${numTeams} teams`);
    } catch (error) {
        console.error('Error setting team configuration:', error);
        alert('Failed to save team configuration: ' + error.message);
    }
}

function createFakePlayersFromModal() {
    const numPlayers = parseInt(document.getElementById('num-fake-players-modal').value);
    
    // Use the existing createFakePlayers function
    const originalInput = document.getElementById('num-fake-players');
    if (originalInput) {
        originalInput.value = numPlayers;
        createFakePlayers();
    }
}

// Update auto-assign button text based on player assignments
async function updateAutoAssignButtonText() {
    try {
        const autoAssignBtn = document.getElementById('auto-assign-btn');
        if (!autoAssignBtn) return;
        
        const players = await gameAPI.getPlayers(currentGameCode);
        
        // Check if any players are assigned to teams (have group_number)
        const assignedPlayers = players.filter(p => p.group_number && p.group_number > 0);
        
        if (assignedPlayers.length > 0) {
            autoAssignBtn.innerHTML = '🎲 Auto-Assign Remaining Players';
        } else {
            autoAssignBtn.innerHTML = '🎲 Auto-Assign All Players';
        }
    } catch (error) {
        console.error('Error updating auto-assign button text:', error);
    }
}

// Update test mode toggle state (disable if game has started)
function updateTestModeToggleState() {
    const testModeToggle = document.getElementById('test-mode-toggle');
    if (!testModeToggle) return;
    
    // Disable test mode if game is not in waiting status
    const gameNotWaiting = currentGameStatus !== 'waiting';
    
    if (gameNotWaiting) {
        testModeToggle.disabled = true;
        testModeToggle.checked = false;
        toggleTestMode(false);
        
        // Add visual indicator that it's disabled
        const toggleContainer = document.getElementById('test-mode-toggle-container');
        if (toggleContainer) {
            toggleContainer.style.opacity = '0.5';
            toggleContainer.title = 'Test mode is disabled once the game has started';
        }
    } else {
        testModeToggle.disabled = false;
        
        const toggleContainer = document.getElementById('test-mode-toggle-container');
        if (toggleContainer) {
            toggleContainer.style.opacity = '1';
            toggleContainer.title = '';
        }
    }
}

// Test Mode Toggle
function toggleTestMode(enabled) {
    console.log('Test mode toggled:', enabled);
    
    // Show/hide test mode settings in the settings modal
    const testModeSettings = document.getElementById('test-mode-settings');
    if (testModeSettings) {
        testModeSettings.style.display = enabled ? 'block' : 'none';
    }
    
    // Show/hide role view switcher
    const roleViewSwitcher = document.getElementById('role-view-switcher');
    if (roleViewSwitcher) {
        roleViewSwitcher.style.display = enabled ? 'flex' : 'none';
    }
    
    // Hide/show game code display
    const gameCodeDisplay = document.querySelector('.game-code-display');
    if (gameCodeDisplay) {
        gameCodeDisplay.style.display = enabled ? 'none' : 'flex';
    }
    
    // Store test mode state in localStorage
    localStorage.setItem('testModeEnabled', enabled);
    
    // Add visual indicator to header
    const toggle = document.querySelector('.test-mode-toggle');
    if (toggle) {
        if (enabled) {
            toggle.style.background = 'rgba(76, 175, 80, 0.3)';
            toggle.style.borderColor = 'rgba(76, 175, 80, 0.6)';
        } else {
            toggle.style.background = 'rgba(255, 255, 255, 0.2)';
            toggle.style.borderColor = 'rgba(255, 255, 255, 0.3)';
        }
    }
    
    // Log event
    addEventLog(enabled ? '🧪 Test mode enabled' : 'Test mode disabled', 'info');
    
    // Reset to host view when test mode is disabled
    if (!enabled) {
        const viewAsRole = document.getElementById('view-as-role');
        if (viewAsRole) {
            viewAsRole.value = 'host';
            switchRoleView('host');
        }
    }
}

// Switch the dashboard view to simulate different roles
function switchRoleView(role) {
    console.log('Switching view to role:', role);
    
    // Hide all role dashboards
    const hostDashboard = document.getElementById('host-dashboard');
    const nationDashboard = document.getElementById('nation-dashboard');
    
    if (hostDashboard) hostDashboard.classList.add('hidden');
    if (nationDashboard) nationDashboard.classList.add('hidden');
    
    // Show the selected role dashboard
    switch(role) {
        case 'host':
        case 'banker':
            if (hostDashboard) hostDashboard.classList.remove('hidden');
            document.getElementById('player-view-switcher').style.display = 'none';
            
            // Reorder tabs based on role
            reorderTabsForRole(role);
            
            // Show/hide Game Controls tab based on role
            const gameControlsTab = document.getElementById('tab-btn-controls');
            if (gameControlsTab) {
                if (role === 'host') {
                    gameControlsTab.style.display = 'inline-block';
                } else {
                    gameControlsTab.style.display = 'none';
                }
            }
            
            // If viewing as banker, ensure we're on the Banker View tab
            if (role === 'banker') {
                // Hide Game Controls content
                const controlsTab = document.getElementById('host-tab-controls');
                if (controlsTab) {
                    controlsTab.classList.remove('active');
                }
                
                // Hide Nations Overview content
                const nationsTab = document.getElementById('host-tab-nations');
                if (nationsTab) {
                    nationsTab.classList.remove('active');
                }
                
                // Show Banker View tab
                const bankerTab = document.getElementById('host-tab-banker');
                if (bankerTab) {
                    bankerTab.classList.add('active');
                }
                
                // Update tab button active state
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                const bankerTabBtn = document.getElementById('tab-btn-banker');
                if (bankerTabBtn) {
                    bankerTabBtn.classList.add('active');
                }
                
                // Load banker view
                loadHostBankerView();
            }
            break;
        case 'player':
            if (nationDashboard) nationDashboard.classList.remove('hidden');
            // Show player switcher dropdown only in test mode
            const testModeEnabled = localStorage.getItem('testModeEnabled') === 'true';
            if (testModeEnabled && currentPlayer && currentPlayer.role === 'host') {
                document.getElementById('player-view-switcher').style.display = 'flex';
                populatePlayerSwitcher();
            }
            break;
    }
    
    addEventLog(`👁️ Viewing as: ${role}`, 'info');
}

async function populatePlayerSwitcher() {
    const dropdown = document.getElementById('view-as-player');
    if (!dropdown) return;
    
    try {
        const players = await gameAPI.getPlayers(currentGameCode);
        
        // Clear existing options except the first placeholder
        dropdown.innerHTML = '<option value="">Select Player...</option>';
        
        // Add an option for each player (excluding the host)
        players
            .filter(p => p.role === 'player')
            .forEach(player => {
                const option = document.createElement('option');
                option.value = player.id;
                option.textContent = `${player.player_name}${player.group_number ? ` (Team ${player.group_number})` : ' (Unassigned)'}`;
                dropdown.appendChild(option);
            });
    } catch (error) {
        console.error('Error populating player switcher:', error);
    }
}

async function switchPlayerView(playerId) {
    if (!playerId) {
        console.log('No player selected');
        return;
    }
    
    try {
        const players = await gameAPI.getPlayers(currentGameCode);
        const selectedPlayer = players.find(p => p.id === parseInt(playerId));
        
        if (!selectedPlayer) {
            console.error('Player not found:', playerId);
            return;
        }
        
        // Update player dashboard with selected player's data
        const nationTitle = document.getElementById('nation-title');
        if (nationTitle) {
            nationTitle.textContent = `${selectedPlayer.player_name}'s Dashboard`;
        }
        
        // Show team information
        const teamInfoDiv = document.getElementById('team-info');
        const teamMembersList = document.getElementById('team-members-list');
        
        if (teamInfoDiv && teamMembersList) {
            if (selectedPlayer.group_number) {
                // Player is assigned to a team
                const teamPlayers = players.filter(p => p.group_number === selectedPlayer.group_number && p.role === 'player');
                
                teamInfoDiv.innerHTML = `<strong>Team ${selectedPlayer.group_number}</strong> (${teamPlayers.length} members)`;
                
                teamMembersList.innerHTML = teamPlayers
                    .map(p => `
                        <div class="team-member-item ${p.id === selectedPlayer.id ? 'is-current-player' : ''}">
                            <span class="member-icon">${p.id === selectedPlayer.id ? '👤' : '👥'}</span>
                            <div class="member-info">
                                <strong>${p.player_name}</strong>
                                ${p.id === selectedPlayer.id ? '<span style="font-size: 12px; color: #1976d2;"> (You)</span>' : ''}
                            </div>
                            <span class="member-status">🟢 Online</span>
                        </div>
                    `)
                    .join('');
            } else {
                // Player is unassigned
                teamInfoDiv.innerHTML = '<strong>⚠️ No Team Assignment</strong>';
                teamMembersList.innerHTML = '<div style="color: #999; font-style: italic; padding: 10px;">You are not assigned to a team yet. Please wait for the host to assign you.</div>';
            }
        }
        
        addEventLog(`👤 Viewing as player: ${selectedPlayer.player_name}`, 'info');
    } catch (error) {
        console.error('Error switching player view:', error);
    }
}

// Show test mode toggle only for hosts
function showTestModeToggleForHost() {
    if (currentPlayer && currentPlayer.role === 'host') {
        const toggleContainer = document.getElementById('test-mode-toggle-container');
        if (toggleContainer) {
            toggleContainer.style.display = 'flex';
        }
    }
}

// Load test mode state on page load
function loadTestModeState() {
    const testModeEnabled = localStorage.getItem('testModeEnabled') === 'true';
    const toggleCheckbox = document.getElementById('test-mode-toggle');
    
    if (toggleCheckbox) {
        toggleCheckbox.checked = testModeEnabled;
        toggleTestMode(testModeEnabled);
    }
}

// Reorder tabs based on role
function reorderTabsForRole(role) {
    const container = document.getElementById('dashboard-tabs-container');
    if (!container) return;
    
    const controlsTab = document.getElementById('tab-btn-controls');
    const nationsTab = document.getElementById('tab-btn-nations');
    const bankerTab = document.getElementById('tab-btn-banker');
    
    if (!controlsTab || !nationsTab || !bankerTab) return;
    
    // Remove all tabs from container
    container.innerHTML = '';
    
    if (role === 'banker') {
        // Banker order: Banker View, Nations Overview (no Game Controls)
        container.appendChild(bankerTab);
        container.appendChild(nationsTab);
        container.appendChild(controlsTab);
    } else {
        // Host order: Game Controls, Nations Overview, Banker View
        container.appendChild(controlsTab);
        container.appendChild(nationsTab);
        container.appendChild(bankerTab);
    }
}

// Switch between host dashboard tabs
function switchHostTab(tabName) {
    console.log('Switching to tab:', tabName);
    
    // Remove active class from all tabs
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.host-tab-content').forEach(content => content.classList.remove('active'));
    
    // Add active class to selected tab
    event.target.classList.add('active');
    
    // Show the corresponding content
    const tabContent = document.getElementById(`host-tab-${tabName}`);
    if (tabContent) {
        tabContent.classList.add('active');
    }
    
    // Load appropriate data based on tab
    if (tabName === 'nations') {
        loadHostNationsOverview();
    } else if (tabName === 'banker') {
        loadHostBankerView();
    }
}

// Load banker view for host
async function loadHostBankerView() {
    // Load bank prices
    if (playerState.bank_prices) {
        document.getElementById('host-price-food').value = playerState.bank_prices.food || 2;
        document.getElementById('host-price-raw-materials').value = playerState.bank_prices.raw_materials || 3;
        document.getElementById('host-price-electrical-goods').value = playerState.bank_prices.electrical_goods || 15;
        document.getElementById('host-price-medical-goods').value = playerState.bank_prices.medical_goods || 20;
    }
    
    // Load bank inventory
    const inventoryDiv = document.getElementById('host-bank-inventory');
    if (playerState.bank_inventory) {
        inventoryDiv.innerHTML = '';
        Object.entries(playerState.bank_inventory).forEach(([resource, amount]) => {
            const item = document.createElement('div');
            item.className = 'resource-item';
            item.innerHTML = `<strong>${resource}:</strong> ${amount}`;
            inventoryDiv.appendChild(item);
        });
    }
}

// Load nations overview for host
async function loadHostNationsOverview() {
    try {
        const players = await gameAPI.getPlayers(currentGameCode);
        const teamsData = {};
        const unassignedPlayers = [];
        
        // Group players by team
        players.forEach(player => {
            if (player.role === 'player') {
                if (player.group_number) {
                    if (!teamsData[player.group_number]) {
                        teamsData[player.group_number] = {
                            teamNumber: player.group_number,
                            members: []
                        };
                    }
                    teamsData[player.group_number].members.push(player);
                } else {
                    unassignedPlayers.push(player);
                }
            }
        });
        
        // Render nation cards
        const container = document.getElementById('host-nations-overview');
        container.innerHTML = '';
        
        if (Object.keys(teamsData).length === 0 && unassignedPlayers.length === 0) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #999;">No teams assigned yet. Go to Game Controls tab to assign players to teams.</div>';
            return;
        }
        
        // Display assigned teams
        Object.values(teamsData).sort((a, b) => a.teamNumber - b.teamNumber).forEach(team => {
            const teamCard = document.createElement('div');
            teamCard.className = 'nation-card';
            teamCard.innerHTML = `
                <div class="nation-header">
                    <h3>🌍 Team ${team.teamNumber}</h3>
                    <span class="nation-type">${team.members.length} members</span>
                </div>
                <div class="nation-members">
                    <strong>Team Members:</strong>
                    ${team.members.map(m => `<div class="member-badge">${m.player_name}</div>`).join('')}
                </div>
            `;
            container.appendChild(teamCard);
        });
        
        // Display unassigned players
        if (unassignedPlayers.length > 0) {
            const unassignedCard = document.createElement('div');
            unassignedCard.className = 'nation-card';
            unassignedCard.style.border = '2px dashed #ff9800';
            unassignedCard.style.background = '#fff3e0';
            unassignedCard.innerHTML = `
                <div class="nation-header">
                    <h3>⚠️ Unassigned Players</h3>
                    <span class="nation-type">${unassignedPlayers.length} awaiting assignment</span>
                </div>
                <div class="nation-members">
                    <strong>Players:</strong>
                    ${unassignedPlayers.map(m => `<div class="member-badge" style="background: #ff9800; color: white;">${m.player_name}</div>`).join('')}
                </div>
            `;
            container.appendChild(unassignedCard);
        }
    } catch (error) {
        console.error('Error loading nations overview:', error);
    }
}

// Load nations overview for banker
async function loadBankerNationsOverview() {
    try {
        const players = await gameAPI.getPlayers(currentGameCode);
        const teamsData = {};
        
        // Group players by team
        players.forEach(player => {
            if (player.group_number && player.role === 'player') {
                if (!teamsData[player.group_number]) {
                    teamsData[player.group_number] = {
                        teamNumber: player.group_number,
                        members: []
                    };
                }
                teamsData[player.group_number].members.push(player);
            }
        });
        
        // Render nation cards
        const container = document.getElementById('banker-nations-overview');
        container.innerHTML = '';
        
        if (Object.keys(teamsData).length === 0) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: #999;">No teams assigned yet.</div>';
            return;
        }
        
        Object.values(teamsData).sort((a, b) => a.teamNumber - b.teamNumber).forEach(team => {
            const teamCard = document.createElement('div');
            teamCard.className = 'nation-card';
            teamCard.innerHTML = `
                <div class="nation-header">
                    <h3>🌍 Team ${team.teamNumber}</h3>
                    <span class="nation-type">${team.members.length} members</span>
                </div>
                <div class="nation-members">
                    <strong>Team Members:</strong>
                    ${team.members.map(m => `<div class="member-badge">${m.player_name}</div>`).join('')}
                </div>
            `;
            container.appendChild(teamCard);
        });
    } catch (error) {
        console.error('Error loading nations overview:', error);
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('settings-modal');
    if (event.target === modal) {
        closeGameSettings();
    }
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    initDashboard();
    initCollapsibleCards();
    loadTestModeState();
});
