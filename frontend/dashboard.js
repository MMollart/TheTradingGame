/**
 * Dashboard JavaScript - Handles all dashboard interactions
 */

// Global variables
let gameAPI = new GameAPI();
let gameWS = null;
let currentGameCode = null;
let currentPlayer = null;
let originalPlayer = null; // Store the original player for when switching back from test mode
let playerState = {};
let teamState = { resources: {}, buildings: {} }; // Team-level resources and buildings
let gameState = {};
let currentGameStatus = 'waiting'; // Track game status (waiting, in_progress, paused, completed)
let challengeManager = null; // New challenge management system
let tradingManager = null; // Trading management system

// Countdown timer variables
let countdownInterval = null;
let gameStartTime = null;
let gameDurationMinutes = 120; // Default 2 hours
let totalPausedTime = 0; // Track total paused duration in milliseconds
let lastPauseTime = null; // Track when pause started
let pausedRemainingTime = null; // Store the exact remaining time when paused

// Production grant constants (per building)
const PRODUCTION_GRANTS = {
    'farm': { resource: 'food', amount: 5 },
    'mine': { resource: 'raw_materials', amount: 5 },
    'electrical_factory': { resource: 'electrical_goods', amount: 5 },
    'medical_factory': { resource: 'medical_goods', amount: 5 }
};

// Difficulty modifiers for production
const DIFFICULTY_MODIFIERS = {
    'easy': 1.5,
    'normal': 1.0,
    'hard': 0.75
};

// Current difficulty setting (can be changed by host/banker)
let currentDifficultyModifier = DIFFICULTY_MODIFIERS.normal;

// Initialize dashboard from URL parameters
async function initDashboard() {
    const params = new URLSearchParams(window.location.search);
    currentGameCode = params.get('gameCode');
    const playerId = params.get('playerId');
    const playerName = params.get('playerName');
    let role = params.get('role'); // Use URL role as initial/fallback
    
    if (!currentGameCode || !playerId || !playerName) {
        alert('Invalid dashboard link');
        window.location.href = 'index.html';
        return;
    }
    
    // Check if user is authenticated and set token
    const authToken = localStorage.getItem('authToken');
    if (authToken) {
        gameAPI.setToken(authToken);
        console.log('Auth token loaded from localStorage');
    }
    
    // Fetch actual player data from backend to get the real role
    try {
        const players = await gameAPI.getPlayers(currentGameCode);
        const playerData = players.find(p => p.id === parseInt(playerId));
        if (playerData && playerData.role) {
            role = playerData.role; // Use role from database, not URL
            console.log(`[initDashboard] Using role from database: ${role}`);
        }
    } catch (error) {
        console.error('[initDashboard] Failed to fetch player data, using URL role:', error);
        // Fall back to URL role if fetch fails
    }
    
    currentPlayer = {
        id: parseInt(playerId),
        name: playerName,
        role: role
    };
    
    // Store the original player for switching back from test mode
    originalPlayer = { ...currentPlayer };
    
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
        
        // Update teamState for players
        if (currentPlayer.role === 'player' && currentPlayer.groupNumber) {
            const teamNumber = String(currentPlayer.groupNumber);
            if (gameState.teams && gameState.teams[teamNumber]) {
                teamState = {
                    resources: gameState.teams[teamNumber].resources || {},
                    buildings: gameState.teams[teamNumber].buildings || {}
                };
                console.log('[WebSocket state_updated] Updated teamState for team', teamNumber, teamState);
            }
        }
        
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
    
    gameWS.on('player_approved', (data) => {
        console.log('[player_approved] Received approval notification:', data);
        // If this is me, reload the dashboard
        if (data.player_id === currentPlayer.id) {
            console.log('[player_approved] I was approved! Reloading dashboard...');
            addEventLog('You have been approved! Loading dashboard...', 'success');
            // Reload the page to refresh all data and show the dashboard
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else if (currentPlayer.role === 'host' || currentPlayer.role === 'banker') {
            // Host/Banker refreshes player lists
            addEventLog(`${data.player_name} was approved`, 'info');
            updatePlayersOverview();
            refreshPendingPlayers();
            refreshUnassigned();
        }
    });
    
    gameWS.on('player_assigned_team', (data) => {
        console.log('[player_assigned_team] Team assignment notification:', data);
        console.log('[player_assigned_team] Comparing player_id:', data.player_id, 'with currentPlayer.id:', currentPlayer.id);
        console.log('[player_assigned_team] Types:', typeof data.player_id, 'vs', typeof currentPlayer.id);
        console.log('[player_assigned_team] Match?', data.player_id == currentPlayer.id);
        
        // If this is me, refresh game data and update dashboard
        // Use loose equality to handle string/number mismatch
        if (data.player_id == currentPlayer.id) {
            console.log('[player_assigned_team] ✅ I was assigned to Team', data.team_number);
            console.log('[player_assigned_team] Setting currentPlayer.groupNumber to:', data.team_number);
            addEventLog(`You have been assigned to Team ${data.team_number}!`, 'success');
            // Update my group number
            currentPlayer.groupNumber = data.team_number;
            console.log('[player_assigned_team] currentPlayer.groupNumber is now:', currentPlayer.groupNumber);
            console.log('[player_assigned_team] Calling loadGameData()...');
            // Reload game data to get player state and show cards
            loadGameData().then(() => {
                console.log('[player_assigned_team] loadGameData() complete, calling updatePlayerCardsVisibility()...');
                updatePlayerCardsVisibility();
                console.log('[player_assigned_team] Calling updateDashboard()...');
                updateDashboard();
                console.log('[player_assigned_team] Calling refreshTeamMembers()...');
                refreshTeamMembers();
                console.log('[player_assigned_team] Dashboard update complete!');
            });
        } else {
            console.log('[player_assigned_team] ❌ Not me, checking if host/banker...');
            if (currentPlayer.role === 'host' || currentPlayer.role === 'banker') {
                // Host/Banker refreshes player lists and team overview
                console.log('[player_assigned_team] I am host/banker, refreshing displays');
                addEventLog(`${data.player_name} assigned to Team ${data.team_number}`, 'info');
                updatePlayersOverview();
                refreshUnassigned();
                updateNationsOverview();
            }
        }
    });
    
    gameWS.on('player_unassigned_team', (data) => {
        console.log('[player_unassigned_team] Team unassignment notification:', data);
        
        // If this is me, refresh game data and update dashboard
        if (data.player_id == currentPlayer.id) {
            console.log('[player_unassigned_team] ✅ I was unassigned from team');
            addEventLog(`You have been removed from your team`, 'warning');
            // Update my group number
            currentPlayer.groupNumber = null;
            console.log('[player_unassigned_team] Calling loadGameData()...');
            // Reload game data to get player state and hide cards
            loadGameData().then(() => {
                console.log('[player_unassigned_team] loadGameData() complete, calling updatePlayerCardsVisibility()...');
                updatePlayerCardsVisibility();
                console.log('[player_unassigned_team] Calling updateDashboard()...');
                updateDashboard();
                console.log('[player_unassigned_team] Calling refreshTeamMembers()...');
                refreshTeamMembers();
                console.log('[player_unassigned_team] Dashboard update complete!');
            });
        } else {
            console.log('[player_unassigned_team] ❌ Not me, checking if host/banker...');
            if (currentPlayer.role === 'host' || currentPlayer.role === 'banker') {
                // Host/Banker refreshes player lists and team overview
                console.log('[player_unassigned_team] I am host/banker, refreshing displays');
                addEventLog(`${data.player_name} removed from team`, 'info');
                updatePlayersOverview();
                refreshUnassigned();
                updateNationsOverview();
            }
        }
    });
    
    gameWS.on('player_role_changed', (data) => {
        console.log('[player_role_changed] Role change notification:', data);
        // If this is me, update my role and reload the dashboard
        if (data.player_id === currentPlayer.id) {
            console.log('[player_role_changed] My role changed to:', data.new_role);
            addEventLog(`Your role has been changed to ${data.new_role}!`, 'success');
            // Update role and reload page to show correct dashboard
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else if (currentPlayer.role === 'host' || currentPlayer.role === 'banker') {
            // Host/Banker refreshes player lists
            addEventLog(`${data.player_name} role changed to ${data.new_role}`, 'info');
            updatePlayersOverview();
            refreshUnassigned();
        }
    });
    
    gameWS.on('game_status_changed', (data) => {
        console.log('[game_status_changed] Game status changed:', data);
        // Update the game status for all players
        currentGameStatus = data.status;
        updateGameStatusDisplay();
        addEventLog(data.message, data.status === 'in_progress' ? 'success' : 'info');
        
        // Update challenge manager status
        if (challengeManager) {
            challengeManager.setGameStatus(data.status, data.status === 'paused' ? Date.now() : null);
        }
        
        // Update control buttons visibility
        updateControlButtons();
        
        // Handle countdown timer based on status
        if (data.status === 'paused') {
            console.log('[game_status_changed] Status is paused, calling pauseCountdownTimer()');
            pauseCountdownTimer();
            // Challenge states are already in the database - no action needed on pause
        } else if (data.status === 'in_progress') {
            console.log('[game_status_changed] Status is in_progress');
            console.log('[game_status_changed] gameStartTime:', gameStartTime);
            console.log('[game_status_changed] pausedRemainingTime:', pausedRemainingTime);
            console.log('[game_status_changed] lastPauseTime:', lastPauseTime);
            
            // Check if we're resuming from a pause
            const wasJustPaused = (pausedRemainingTime !== null || lastPauseTime !== null);
            console.log('[game_status_changed] wasJustPaused:', wasJustPaused);
            
            if (wasJustPaused) {
                // Resuming from pause - use stored state
                console.log('[game_status_changed] ***** CALLING resumeCountdownTimer() - detected pause state *****');
                resumeCountdownTimer();
            } else if (data.started_at && data.game_duration_minutes) {
                // Game starting fresh - need backend data
                console.log('[game_status_changed] Starting fresh game with backend data');
                if (!gameStartTime) {
                    startCountdownTimer(data.started_at, data.game_duration_minutes);
                }
            } else if (gameStartTime) {
                // Timer already running, just ensure interval is active
                console.log('[game_status_changed] Timer already running');
                if (!countdownInterval) {
                    resumeCountdownTimer();
                }
            }
            
            // On resume: Load updated challenge states from database into all clients
            if (challengeManager && wasJustPaused) {
                console.log('[game_status_changed] Resume detected - loading updated challenges from database');
                // Wait for backend to finish adjusting timestamps
                setTimeout(() => {
                    challengeManager.loadFromServer().then(() => {
                        console.log('[game_status_changed] Challenges loaded from database with adjusted timestamps');
                    }).catch(err => {
                        console.error('[game_status_changed] Failed to load challenges from database:', err);
                    });
                }, 500);
            }
            
            // Refresh player state
            loadGameData().then(() => {
                updatePlayerCardsVisibility();
                updateDashboard();
            });
        } else if (data.status === 'completed') {
            stopCountdownTimer();
            
            // Redirect to appropriate report based on role
            if (currentPlayer.role === 'host') {
                // Host gets redirected to report page (done in endGame function)
                // This case handles WebSocket-triggered completion (e.g., from another client)
                setTimeout(() => {
                    window.location.href = `host-report.html?gameCode=${currentGameCode}`;
                }, 1000);
            } else if (currentPlayer.role === 'player') {
                addEventLog('Game has ended!', 'success');
                // Redirect players to their team report
                setTimeout(() => {
                    window.location.href = `player-report.html?gameCode=${currentGameCode}&playerId=${currentPlayer.id}`;
                }, 2000);
            } else {
                // Banker sees notification with scores
                addEventLog('Game has ended!', 'success');
                if (data.scores) {
                    setTimeout(() => {
                        showFinalScores(data.scores);
                    }, 1000);
                }
            }
        }
    });
    
    gameWS.on('lobby_cleared', (data) => {
        console.log('[lobby_cleared] Lobby has been cleared by host');
        // If I'm not the host, redirect to join screen
        if (currentPlayer.role !== 'host') {
            alert(data.message || 'The host has closed the lobby.');
            // Disconnect and redirect to index
            if (gameWS) {
                gameWS.disconnect();
            }
            window.location.href = 'index.html';
        } else {
            // Host sees confirmation
            addEventLog('Lobby cleared - all players removed', 'warning');
        }
    });
    
    gameWS.on('game_deleted', (data) => {
        console.log('[game_deleted] Game has been deleted');
        // Everyone gets kicked out
        alert(data.message || 'This game has been deleted.');
        // Disconnect and redirect to index
        if (gameWS) {
            gameWS.disconnect();
        }
        window.location.href = 'index.html';
    });
    
    gameWS.connect();
}

async function loadGameData() {
    try {
        const game = await gameAPI.getGame(currentGameCode);
        const players = await gameAPI.getPlayers(currentGameCode);
        
        gameState = game.game_state || {};
        currentGameStatus = game.status || 'waiting';
        
        // Debug: Log gameState structure
        console.log('[loadGameData] gameState:', gameState);
        console.log('[loadGameData] gameState.teams:', gameState.teams);
        
        // Update game status display
        updateGameStatusDisplay();
        
        // Update control buttons based on game status
        updateControlButtons();
        
        // Initialize countdown timer if game is in progress or paused
        // BUT only if the timer isn't already running (don't reset during resume)
        if (currentGameStatus === 'in_progress' && game.started_at && game.game_duration_minutes) {
            if (!gameStartTime) {
                // Timer not yet started, start it
                startCountdownTimer(game.started_at, game.game_duration_minutes);
            }
            // If timer already exists, leave it running (don't reset during resume)
        } else if (currentGameStatus === 'paused' && game.started_at && game.game_duration_minutes) {
            if (!gameStartTime) {
                // Timer not yet started, start it then pause
                startCountdownTimer(game.started_at, game.game_duration_minutes);
                pauseCountdownTimer();
            }
            // If timer already exists and paused, leave it alone
        }
        
        // Update test mode toggle state based on game status
        updateTestModeToggleState();
        
        // Find current player and load team state
        const player = players.find(p => p.id === currentPlayer.id);
        if (player) {
            // Set player's individual state (excluding resources/buildings)
            if (player.player_state) {
                playerState = player.player_state;
            }
            
            if (player.group_number) {
                currentPlayer.groupNumber = player.group_number;
                
                // Load TEAM-LEVEL resources and buildings from gameState.teams (stored as string keys in backend)
                const teamNumber = String(player.group_number);
                if (gameState.teams && gameState.teams[teamNumber]) {
                    teamState = {
                        resources: gameState.teams[teamNumber].resources || {},
                        buildings: gameState.teams[teamNumber].buildings || {}
                    };
                    console.log('[loadGameData] Loaded team state from gameState.teams (team', teamNumber + ')');
                } else {
                    // Team exists but no state in gameState.teams - this will break if backend hasn't been updated
                    teamState = { resources: {}, buildings: {} };
                    console.error('[loadGameData] ERROR: gameState.teams[' + teamNumber + '] not found! Backend must store team data in gameState.teams');
                }
            } else {
                // Player not assigned to team yet, keep empty
                teamState = { resources: {}, buildings: {} };
                console.log('[loadGameData] Player not assigned to team - keeping team state empty');
            }
        }
        
        // Load active challenges from database
        await loadActiveChallenges(players);
        
        // Initialize challenge manager if game is in progress or paused
        // This ensures challenge manager is available for bankers/hosts who join mid-game
        if ((currentGameStatus === 'in_progress' || currentGameStatus === 'paused') && !challengeManager) {
            console.log('[loadGameData] Game in progress, initializing challenge manager...');
            await initializeChallengeManager();
        }
        
        updateDashboard();
    } catch (error) {
        console.error('Failed to load game data:', error);
        addEventLog('Failed to load game data', 'error');
    }
}

function updateDashboard() {
    if (currentPlayer.role === 'host' || currentPlayer.role === 'banker') {
        updateHostDashboard();
    } else {
        updatePlayerDashboard();
    }
    
    // Hide/show player cards based on game status
    updatePlayerCardsVisibility();
}

// Hide production, trading, and build buildings cards when in waiting state
function updatePlayerCardsVisibility() {
    // Only apply to player dashboard (not host or banker)
    if (currentPlayer.role === 'host' || currentPlayer.role === 'banker') {
        return;
    }
    
    console.log('[updatePlayerCardsVisibility] Current game status:', currentGameStatus);
    console.log('[updatePlayerCardsVisibility] Current player group:', currentPlayer.groupNumber);
    
    const resourcesCard = document.getElementById('card-resources');
    const buildingsCard = document.getElementById('card-buildings');
    const productionCard = document.getElementById('card-production');
    const tradingCard = document.getElementById('card-trading');
    const buildBuildingsCard = document.getElementById('card-build-buildings');
    
    // Check if game has started (in_progress or paused)
    const gameStarted = currentGameStatus === 'in_progress' || currentGameStatus === 'paused';
    
    console.log('[updatePlayerCardsVisibility] Game started:', gameStarted);
    
    // Show Resources and Buildings cards when game starts
    if (resourcesCard) {
        resourcesCard.style.display = gameStarted ? 'block' : 'none';
        console.log('[updatePlayerCardsVisibility] Resources card display:', resourcesCard.style.display);
    }
    if (buildingsCard) {
        buildingsCard.style.display = gameStarted ? 'block' : 'none';
        console.log('[updatePlayerCardsVisibility] Buildings card display:', buildingsCard.style.display);
    }
    
    // Hide gameplay cards if player is not assigned to a team
    if (!currentPlayer.groupNumber) {
        console.log('[updatePlayerCardsVisibility] Player not assigned to team - hiding gameplay cards');
        if (productionCard) productionCard.style.display = 'none';
        if (tradingCard) tradingCard.style.display = 'none';
        if (buildBuildingsCard) buildBuildingsCard.style.display = 'none';
        return;
    }
    
    // Show gameplay cards when player has a team AND game has started
    if (productionCard) {
        productionCard.style.display = gameStarted ? 'block' : 'none';
        console.log('[updatePlayerCardsVisibility] Production card display:', productionCard.style.display);
    }
    if (tradingCard) {
        tradingCard.style.display = gameStarted ? 'block' : 'none';
        console.log('[updatePlayerCardsVisibility] Trading card display:', tradingCard.style.display);
    }
    if (buildBuildingsCard) {
        buildBuildingsCard.style.display = gameStarted ? 'block' : 'none';
        console.log('[updatePlayerCardsVisibility] Build buildings card display:', buildBuildingsCard.style.display);
    }
    
    // Original logic (now disabled):
    // if (currentGameStatus === 'waiting') {
    //     // Hide gameplay cards in lobby
    //     if (productionCard) productionCard.style.display = 'none';
    //     if (tradingCard) tradingCard.style.display = 'none';
    //     if (buildBuildingsCard) buildBuildingsCard.style.display = 'none';
    // } else {
    //     // Show gameplay cards when game is active
    //     if (productionCard) productionCard.style.display = 'block';
    //     if (tradingCard) tradingCard.style.display = 'block';
    //     if (buildBuildingsCard) buildBuildingsCard.style.display = 'block';
    // }
}

// ==================== CHALLENGE REQUESTS ====================

// Track pending challenge requests
let pendingChallengeRequests = [];

// Track ALL active challenges across all teams (single source of truth)
// Structure: { challengeKey: { player_id, player_name, team_number, has_school, start_time, challenge_description, challenge_type, target_number, status, db_id } }
// Key format: "playerId-buildingType" (with school) or "teamN-buildingType" (without school)
let allActiveChallenges = {};

// Challenge timer interval
let challengeTimerInterval = null;

// Load active challenges from database
async function loadActiveChallenges(players = null) {
    try {
        console.log('[loadActiveChallenges] Loading challenges from database...');
        const challenges = await gameAPI.getChallenges(currentGameCode);
        
        console.log('[loadActiveChallenges] Loaded challenges:', challenges);
        
        // Clear and repopulate allActiveChallenges from database
        allActiveChallenges = {};
        
        // Clear and repopulate pendingChallengeRequests for host/banker
        const isHostOrBanker = (currentPlayer.role === 'host' || currentPlayer.role === 'banker') ||
                               (originalPlayer && (originalPlayer.role === 'host' || originalPlayer.role === 'banker'));
        if (isHostOrBanker) {
            pendingChallengeRequests = [];
        }
        
        for (const challenge of challenges) {
            // Only load requested and assigned challenges (not completed/cancelled/dismissed/expired)
            if (challenge.status === 'requested' || challenge.status === 'assigned') {
                const challengeKey = challenge.has_school 
                    ? `${challenge.player_id}-${challenge.building_type}`
                    : `team${challenge.team_number}-${challenge.building_type}`;
                
                // Find player name from players list
                let playerName = '';
                if (players) {
                    const player = players.find(p => p.id === challenge.player_id);
                    if (player) {
                        playerName = player.name;
                    }
                }
                
                const challengeData = {
                    db_id: challenge.id,
                    player_id: challenge.player_id,
                    player_name: playerName,
                    team_number: challenge.team_number,
                    building_type: challenge.building_type,
                    building_name: challenge.building_name,
                    has_school: challenge.has_school,
                    status: challenge.status
                };
                
                // Add requested challenges to pendingChallengeRequests for host/banker
                if (challenge.status === 'requested' && isHostOrBanker) {
                    pendingChallengeRequests.push({
                        db_id: challenge.id,
                        player_id: challenge.player_id,
                        player_name: playerName,
                        team_number: challenge.team_number,
                        building_type: challenge.building_type,
                        building_name: challenge.building_name,
                        has_school: challenge.has_school,
                        timestamp: challenge.created_at || new Date().toISOString()
                    });
                    console.log(`[loadActiveChallenges] Added challenge ${challenge.id} to pendingChallengeRequests (status: ${challenge.status})`);
                }
                
                // Add assignment data if challenge is assigned
                if (challenge.status === 'assigned' && challenge.assigned_at) {
                    const startTime = new Date(challenge.assigned_at).getTime();
                    const now = Date.now();
                    const elapsed = now - startTime;
                    const expiryTime = 10 * 60 * 1000; // 10 minutes in ms
                    
                    console.log(`[loadActiveChallenges] Challenge ${challenge.id}:`, {
                        assigned_at: challenge.assigned_at,
                        startTime: new Date(startTime).toISOString(),
                        now: new Date(now).toISOString(),
                        elapsed_seconds: Math.floor(elapsed/1000),
                        remaining_seconds: Math.floor((expiryTime - elapsed)/1000),
                        currentGameStatus: currentGameStatus,
                        will_check_expiry: currentGameStatus === 'in_progress'
                    });
                    
                    // Only check for expiry if game is actively running (not paused or waiting)
                    // When loading after resume, the database assigned_at has already been adjusted
                    // so we should trust it and let the timer handle expiry during gameplay
                    if (currentGameStatus === 'in_progress' && elapsed >= expiryTime) {
                        console.log(`[loadActiveChallenges] Challenge ${challenge.id} has expired (elapsed: ${Math.floor(elapsed/1000)}s), marking as expired`);
                        // Update challenge status in database to expired
                        try {
                            await gameAPI.updateChallenge(currentGameCode, challenge.id, { status: 'expired' });
                            console.log(`[loadActiveChallenges] Challenge ${challenge.id} marked as expired in database`);
                        } catch (err) {
                            console.error(`[loadActiveChallenges] Failed to mark challenge ${challenge.id} as expired:`, err);
                        }
                        // Skip adding this challenge to active lists
                        continue;
                    }
                    
                    challengeData.challenge_description = challenge.challenge_description;
                    challengeData.challenge_type = challenge.challenge_type;
                    challengeData.target_number = challenge.target_number;
                    challengeData.start_time = startTime;
                }
                
                // Add ALL challenges to allActiveChallenges (single source of truth)
                allActiveChallenges[challengeKey] = challengeData;
                console.log(`[loadActiveChallenges] Added challenge ${challengeKey} to allActiveChallenges (status: ${challenge.status})`);
            }
        }
        
        console.log('[loadActiveChallenges] allActiveChallenges:', allActiveChallenges);
        console.log('[loadActiveChallenges] pendingChallengeRequests:', pendingChallengeRequests);
        
        // Update UI
        updateActiveChallengesList();
        if (isHostOrBanker) {
            updateChallengeRequestsList();
        }
        if (Object.keys(allActiveChallenges).length > 0) {
            startChallengeTimers();
        }
        
    } catch (error) {
        console.error('[loadActiveChallenges] Failed to load challenges:', error);
    }
}

// Challenge types configuration
const challengeTypes = {
    'push_ups': { name: 'Push-ups', default: 20 },
    'sit_ups': { name: 'Sit-ups', default: 20 },
    'burpees': { name: 'Burpees', default: 20 },
    'star_jumps': { name: 'Star Jumps', default: 20 },
    'squats': { name: 'Squats', default: 20 },
    'lunges': { name: 'Lunges', default: 20 },
    'plank': { name: 'Plank (seconds)', default: 20 },
    'jumping_jacks': { name: 'Jumping Jacks', default: 20 }
};

function updateChallengeRequestsList() {
    console.log('[updateChallengeRequestsList] Called');
    const requestsList = document.getElementById('challenge-requests-list');
    if (!requestsList) {
        console.log('[updateChallengeRequestsList] Element not found: challenge-requests-list');
        return;
    }
    
    // Get requested challenges from challenge manager
    const requestedChallenges = challengeManager ? challengeManager.getRequestedChallenges() : [];
    console.log('[updateChallengeRequestsList] Requested challenges:', requestedChallenges);
    console.log('[updateChallengeRequestsList] Challenge manager exists:', !!challengeManager);
    
    if (requestedChallenges.length === 0) {
        requestsList.innerHTML = '<p style="color: #999; font-style: italic;">No pending challenge requests</p>';
        return;
    }
    
    requestsList.innerHTML = '';
    requestedChallenges.forEach(request => {
        const requestItem = document.createElement('div');
        requestItem.className = 'challenge-request-item';
        requestItem.style.cssText = 'background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #667eea;';
        
        // Build challenge type dropdown options
        let challengeOptions = '';
        Object.entries(challengeTypes).forEach(([key, config]) => {
            challengeOptions += `<option value="${key}">${config.name}</option>`;
        });
        
        requestItem.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: #333;">${request.player_name}</strong> <span style="color: #667eea; font-weight: 600;">(Team ${request.team_number})</span>
                    <p style="margin: 5px 0; color: #666;">${request.building_name}</p>
                    <small style="color: #999;">Requested: ${new Date(request.timestamp).toLocaleTimeString()}</small>
                </div>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <select id="challenge-type-${request.player_id}-${request.building_type}" 
                            onchange="updateChallengeTargetPreview(${request.player_id}, '${request.building_type}')"
                            style="padding: 8px; border: 2px solid #ddd; border-radius: 6px; font-size: 14px;">
                        ${challengeOptions}
                    </select>
                    <span id="challenge-target-${request.player_id}-${request.building_type}" 
                          style="padding: 8px 12px; background: #f0f0f0; border: 2px solid #ddd; border-radius: 6px; min-width: 50px; text-align: center; font-weight: 600; color: #333; font-size: 14px;">
                        ${challengeTypes[Object.keys(challengeTypes)[0]].default}
                    </span>
                    <button class="btn btn-success" 
                            onclick="assignChallenge(${request.player_id}, '${request.building_type}')"
                            style="padding: 8px 16px;">
                        ✅ Assign
                    </button>
                    <button class="btn btn-secondary" 
                            onclick="dismissChallengeRequest(${request.player_id}, '${request.building_type}')"
                            style="padding: 8px 16px;">
                        ❌ Dismiss
                    </button>
                </div>
            </div>
        `;
        
        requestsList.appendChild(requestItem);
    });
}

function updateChallengeTargetPreview(playerId, buildingType) {
    const typeSelect = document.getElementById(`challenge-type-${playerId}-${buildingType}`);
    const targetSpan = document.getElementById(`challenge-target-${playerId}-${buildingType}`);
    
    if (typeSelect && targetSpan) {
        const selectedType = typeSelect.value;
        const defaultValue = challengeTypes[selectedType].default;
        targetSpan.textContent = defaultValue;
    }
}

async function assignChallenge(playerId, buildingType) {
    console.log('[assignChallenge] ===== FUNCTION CALLED =====');
    console.log('[assignChallenge] playerId:', playerId, 'buildingType:', buildingType);
    
    const typeSelect = document.getElementById(`challenge-type-${playerId}-${buildingType}`);
    const targetSpan = document.getElementById(`challenge-target-${playerId}-${buildingType}`);
    
    console.log('[assignChallenge] typeSelect:', typeSelect);
    console.log('[assignChallenge] targetSpan:', targetSpan);
    
    if (!typeSelect || !targetSpan) {
        console.error('[assignChallenge] ❌ Challenge inputs not found');
        alert('Error: Challenge inputs not found');
        return;
    }
    
    const challengeType = typeSelect.value;
    const targetNumber = parseInt(targetSpan.textContent);
    
    console.log('[assignChallenge] challengeType:', challengeType);
    console.log('[assignChallenge] targetNumber:', targetNumber);
    
    if (!targetNumber || targetNumber < 1) {
        console.error('[assignChallenge] ❌ Invalid target number');
        alert('Please enter a valid target number');
        return;
    }
    
    // Build challenge description
    const challengeName = challengeTypes[challengeType].name;
    const challengeDescription = `${targetNumber} ${challengeName}`;
    const startTime = Date.now();
    
    console.log('[assignChallenge] challengeDescription:', challengeDescription);
    
    // Find the request - check challenge manager first, then fall back to legacy array
    let request = null;
    let challengeDbId = null;
    
    if (challengeManager) {
        // Get request from challenge manager
        const requestedChallenges = challengeManager.getRequestedChallenges();
        console.log('[assignChallenge] Requested challenges from manager:', requestedChallenges);
        
        request = requestedChallenges.find(
            req => req.player_id === playerId && req.building_type === buildingType
        );
        
        if (request) {
            challengeDbId = request.db_id;
            console.log('[assignChallenge] Found request in challenge manager:', request);
        }
    }
    
    // Fall back to legacy array
    if (!request) {
        request = pendingChallengeRequests.find(
            req => req.player_id === playerId && req.building_type === buildingType
        );
        
        if (request) {
            challengeDbId = request.db_id;
            console.log('[assignChallenge] Found request in pendingChallengeRequests:', request);
        }
    }
    
    console.log('[assignChallenge] Final request:', request);
    console.log('[assignChallenge] Challenge DB ID:', challengeDbId);
    
    if (!request) {
        console.error('[assignChallenge] ❌ Request not found');
        console.log('[assignChallenge] pendingChallengeRequests:', pendingChallengeRequests);
        if (challengeManager) {
            console.log('[assignChallenge] challengeManager.challenges:', Array.from(challengeManager.challenges.entries()));
        }
        alert('Error: Challenge request not found');
        return;
    }
    
    // Use challenge manager if available
    if (challengeManager && challengeDbId) {
        console.log('[assignChallenge] Using challenge manager to assign challenge');
        try {
            await challengeManager.assignChallenge(
                challengeDbId,
                challengeType,
                challengeDescription,
                targetNumber
            );
            console.log('[assignChallenge] ✅ Challenge assigned successfully via challenge manager');
        } catch (error) {
            console.error('[assignChallenge] ❌ Failed to assign challenge via challenge manager:', error);
            alert('Failed to assign challenge: ' + error.message);
            return;
        }
    } else {
        console.warn('[assignChallenge] ⚠️ Challenge manager not available or no db_id');
        console.log('[assignChallenge] challengeManager exists:', !!challengeManager);
        console.log('[assignChallenge] challengeDbId:', challengeDbId);
    }
    
    // Track as active challenge with timestamp (legacy support)
    const challengeKey = request.has_school 
        ? `${playerId}-${buildingType}`
        : `team${request.team_number}-${buildingType}`;
    
    allActiveChallenges[challengeKey] = {
        player_id: playerId,
        player_name: request.player_name,
        team_number: request.team_number || 0,
        building_type: buildingType,
        building_name: formatBuildingName(buildingType),
        challenge_description: challengeDescription,
        challenge_type: challengeType,
        target_number: targetNumber,
        start_time: startTime,
        has_school: request.has_school || false,
        status: 'assigned',
        db_id: request.db_id
    };
    
    console.log(`[assignChallenge] Added challenge to allActiveChallenges with key: ${challengeKey}`, allActiveChallenges[challengeKey]);
    
    // Send challenge assignment via WebSocket
    gameWS.send({
        type: 'event',
        event_type: 'challenge_assigned',
        data: {
            player_id: playerId,
            building_type: buildingType,
            challenge_description: challengeDescription,
            challenge_type: challengeType,
            target_number: targetNumber,
            start_time: startTime
        }
    });
    
    // Remove from pending list
    pendingChallengeRequests = pendingChallengeRequests.filter(
        req => !(req.player_id === playerId && req.building_type === buildingType)
    );
    
    updateChallengeRequestsList();
    updateActiveChallengesList();
    // Start timer if not already running
    startChallengeTimers();
    addEventLog(`Challenge assigned: ${challengeDescription}`, 'success');
}

async function dismissChallengeRequest(playerId, buildingType) {
    console.log('[dismissChallengeRequest] Called for player:', playerId, 'building:', buildingType);
    
    // Find the request - check challenge manager first
    let request = null;
    let challengeDbId = null;
    
    if (challengeManager) {
        const requestedChallenges = challengeManager.getRequestedChallenges();
        request = requestedChallenges.find(
            req => req.player_id === playerId && req.building_type === buildingType
        );
        if (request) {
            challengeDbId = request.db_id;
            console.log('[dismissChallengeRequest] Found in challenge manager, db_id:', challengeDbId);
        }
    }
    
    // Fall back to legacy array
    if (!request) {
        request = pendingChallengeRequests.find(
            req => req.player_id === playerId && req.building_type === buildingType
        );
        if (request) {
            challengeDbId = request.db_id;
            console.log('[dismissChallengeRequest] Found in pendingChallengeRequests, db_id:', challengeDbId);
        }
    }
    
    // Delete challenge from database if we have the ID
    if (challengeDbId) {
        try {
            await gameAPI.deleteChallenge(currentGameCode, challengeDbId);
            console.log('[dismissChallengeRequest] ✅ Challenge deleted from database');
        } catch (error) {
            console.error('[dismissChallengeRequest] ❌ Failed to delete challenge from database:', error);
        }
    }
    
    // Clear the active challenge lock (all possible formats)
    delete allActiveChallenges[buildingType];
    delete allActiveChallenges[`${playerId}-${buildingType}`];
    if (request && request.team_number) {
        delete allActiveChallenges[`team${request.team_number}-${buildingType}`];
    }
    
    // Remove from pending list (legacy)
    pendingChallengeRequests = pendingChallengeRequests.filter(
        req => !(req.player_id === playerId && req.building_type === buildingType)
    );
    
    // Notify player that request was dismissed
    gameWS.send({
        type: 'event',
        event_type: 'challenge_dismissed',
        data: {
            player_id: playerId,
            building_type: buildingType,
            team_number: request ? request.team_number : null
        }
    });
    
    updateChallengeRequestsList();
    addEventLog('Challenge request dismissed', 'info');
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
            <div class="team-box-header">
                <span class="team-name" id="team-${i}-name" ondblclick="renameTeam(${i})" title="Double-click to rename">Team ${i}</span>
                <button class="btn-icon-edit" onclick="renameTeam(${i})" title="Rename team">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                </button>
            </div>
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
        const game = await gameAPI.getGame(currentGameCode);
        const players = await gameAPI.getPlayers(currentGameCode);
        const teams = game.game_state?.teams || {};
        
        // Clear all team boxes first and update team names
        for (let i = 1; i <= 20; i++) {
            const teamPlayersDiv = document.getElementById(`team-${i}-players`);
            if (teamPlayersDiv) {
                teamPlayersDiv.innerHTML = '<p style="color: #999; font-style: italic; font-size: 14px;">Drop players here</p>';
            }
            
            // Update team name if it exists
            const teamNameSpan = document.getElementById(`team-${i}-name`);
            const teamData = teams[String(i)];
            if (teamNameSpan && teamData?.nation_name) {
                teamNameSpan.textContent = teamData.nation_name;
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
    playerItem.dataset.playerName = player.player_name;
    playerItem.dataset.currentTeam = player.group_number;
    playerItem.draggable = true;
    playerItem.ondragstart = handleDragStart;
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
    const currentTeam = e.dataTransfer.getData('currentTeam');
    const targetTeam = parseInt(e.currentTarget.dataset.teamNumber);
    
    if (!playerId || !targetTeam) return;
    
    // Check if player is already on this team
    if (currentTeam && parseInt(currentTeam) === targetTeam) {
        console.log(`${playerName} is already on Team ${targetTeam}`);
        return;
    }
    
    try {
        await gameAPI.assignPlayerGroup(currentGameCode, playerId, targetTeam);
        
        if (currentTeam) {
            console.log(`Moved ${playerName} from Team ${currentTeam} to Team ${targetTeam}`);
            addEventLog(`${playerName} moved from Team ${currentTeam} to Team ${targetTeam}`, 'info');
        } else {
            console.log(`Assigned ${playerName} to Team ${targetTeam}`);
            addEventLog(`${playerName} assigned to Team ${targetTeam}`, 'success');
        }
        
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
// Rename a team with inline editing
async function renameTeam(teamNumber) {
    const teamNameSpan = document.getElementById(`team-${teamNumber}-name`);
    if (!teamNameSpan) return;
    
    const currentName = teamNameSpan.textContent;
    
    // Create input element
    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentName;
    input.className = 'team-name-edit-input';
    input.style.cssText = 'width: 100%; padding: 4px 8px; border: 2px solid #667eea; border-radius: 4px; font-size: 16px; font-weight: 600; font-family: inherit;';
    
    // Replace span with input
    teamNameSpan.replaceWith(input);
    input.focus();
    input.select();
    
    // Save function
    const saveEdit = async () => {
        const newName = input.value.trim();
        
        // Create new span
        const newSpan = document.createElement('span');
        newSpan.className = 'team-name';
        newSpan.id = `team-${teamNumber}-name`;
        newSpan.ondblclick = () => renameTeam(teamNumber);
        newSpan.title = 'Double-click to rename';
        newSpan.textContent = newName || currentName;
        
        // Replace input with span
        input.replaceWith(newSpan);
        
        if (!newName || newName === currentName) {
            return; // No change
        }
        
        try {
            // Call API to update team name
            await gameAPI.updateTeamName(currentGameCode, teamNumber, newName);
            
            addEventLog(`Team ${teamNumber} renamed to "${newName}"`, 'success');
            
            // Refresh all team name displays locally
            await refreshAllTeamNameDisplays();
        } catch (error) {
            console.error('Error renaming team:', error);
            const errorMessage = error.message || error.detail || JSON.stringify(error);
            alert('Failed to rename team: ' + errorMessage);
            
            // Revert to old name on error
            newSpan.textContent = currentName;
        }
    };
    
    // Cancel function
    const cancelEdit = () => {
        const newSpan = document.createElement('span');
        newSpan.className = 'team-name';
        newSpan.id = `team-${teamNumber}-name`;
        newSpan.ondblclick = () => renameTeam(teamNumber);
        newSpan.title = 'Double-click to rename';
        newSpan.textContent = currentName;
        input.replaceWith(newSpan);
    };
    
    // Event handlers
    input.onblur = saveEdit;
    input.onkeydown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveEdit();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelEdit();
        }
    };
}

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
    
    // Attach event listeners to game control buttons
    const startBtn = document.getElementById('start-game-btn');
    const pauseBtn = document.getElementById('pause-game-btn');
    const resumeBtn = document.getElementById('resume-game-btn');
    const endBtn = document.getElementById('end-game-btn');
    
    if (startBtn) startBtn.addEventListener('click', startGame);
    if (pauseBtn) pauseBtn.addEventListener('click', pauseGame);
    if (resumeBtn) resumeBtn.addEventListener('click', resumeGame);
    if (endBtn) endBtn.addEventListener('click', endGame);
    
    updateControlButtons();
    
    // Show/hide manual management card based on role
    const manualManagementCard = document.getElementById('manual-management-card');
    if (manualManagementCard) {
        if (isHost) {
            manualManagementCard.style.display = 'block';
            // Populate team dropdowns dynamically
            await populateManualManagementTeamDropdowns();
        } else {
            manualManagementCard.style.display = 'none';
        }
    }
    
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
    
    // Use the current game status from the global variable
    const gameStatus = currentGameStatus || 'waiting';
    
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

function updateGameStatusDisplay() {
    const statusDisplay = document.getElementById('game-status-display');
    
    if (!statusDisplay) {
        console.warn('updateGameStatusDisplay: Status display element not found');
        return;
    }
    
    const gameStatus = currentGameStatus || 'waiting';
    
    // Map status values to display text
    const statusMap = {
        'waiting': 'Waiting',
        'in_progress': 'In Progress',
        'paused': 'Paused',
        'completed': 'Completed'
    };
    
    // Update text
    statusDisplay.textContent = statusMap[gameStatus] || 'Unknown';
    
    // Update styling based on status
    statusDisplay.className = ''; // Clear existing classes
    switch(gameStatus) {
        case 'waiting':
            statusDisplay.style.color = '#6c757d'; // Gray
            break;
        case 'in_progress':
            statusDisplay.style.color = '#28a745'; // Green
            statusDisplay.style.fontWeight = 'bold';
            break;
        case 'paused':
            statusDisplay.style.color = '#ffc107'; // Yellow/Orange
            break;
        case 'completed':
            statusDisplay.style.color = '#dc3545'; // Red
            break;
    }
}

function startCountdownTimer(startTime, durationMinutes) {
    console.log('[startCountdownTimer] Starting timer:', { startTime, durationMinutes });
    
    // Store game start time and duration
    gameStartTime = new Date(startTime);
    gameDurationMinutes = durationMinutes;
    totalPausedTime = 0;
    lastPauseTime = null;
    pausedRemainingTime = null;
    
    // Show the countdown timer
    const timerContainer = document.getElementById('countdown-timer');
    if (timerContainer) {
        timerContainer.style.display = 'flex';
        timerContainer.style.alignItems = 'center';
    }
    
    // Clear any existing interval
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    
    // Update immediately, then every second
    updateCountdownDisplay();
    countdownInterval = setInterval(updateCountdownDisplay, 1000);
}

function updateCountdownDisplay() {
    const display = document.getElementById('countdown-display');
    if (!display || !gameStartTime) {
        console.log('[updateCountdownDisplay] Early return - display:', !!display, 'gameStartTime:', !!gameStartTime);
        return;
    }
    
    // If the game is paused, don't update
    if (currentGameStatus === 'paused') {
        console.log('[updateCountdownDisplay] Paused, skipping update');
        return;
    }
    
    console.log('[updateCountdownDisplay] Updating display...');
    
    // Calculate remaining time
    const now = new Date();
    const elapsedActiveTime = (now - gameStartTime) - totalPausedTime;
    const totalGameTime = gameDurationMinutes * 60 * 1000;
    const remainingTime = totalGameTime - elapsedActiveTime;
    
    // Check if time expired
    if (remainingTime <= 0) {
        display.textContent = '00:00';
        display.style.color = '#dc3545'; // Red
        if (countdownInterval) {
            clearInterval(countdownInterval);
            countdownInterval = null;
        }
        
        // Auto-end the game when timer reaches zero (only if host)
        if (currentPlayer.role === 'host' && currentGameStatus === 'in_progress') {
            console.log('[updateCountdownDisplay] Time expired, auto-ending game...');
            autoEndGameOnTimeout();
        }
        return;
    }
    
    // Convert to minutes:seconds
    const totalSeconds = Math.floor(remainingTime / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    
    // Format display
    display.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    
    // Color coding based on time remaining
    if (minutes < 5) {
        display.style.color = '#dc3545'; // Red - less than 5 minutes
    } else if (minutes < 15) {
        display.style.color = '#ffc107'; // Yellow - less than 15 minutes
    } else {
        display.style.color = '#fff'; // White - plenty of time
    }
}

function pauseCountdownTimer() {
    console.log('[pauseCountdownTimer] Pausing timer');
    
    // Stop the interval immediately
    if (countdownInterval) {
        clearInterval(countdownInterval);
        countdownInterval = null;
    }
    
    // Calculate and store the EXACT remaining time at this moment
    if (gameStartTime && !pausedRemainingTime) {
        const now = new Date();
        const elapsedActiveTime = (now - gameStartTime) - totalPausedTime;
        const totalGameTime = gameDurationMinutes * 60 * 1000;
        pausedRemainingTime = totalGameTime - elapsedActiveTime;
        
        const mins = Math.floor(pausedRemainingTime / 60000);
        const secs = Math.floor((pausedRemainingTime % 60000) / 1000);
        console.log('[pauseCountdownTimer] Stored remaining time:', mins, 'min', secs, 'sec');
    }
    
    // Record when pause started
    if (!lastPauseTime) {
        lastPauseTime = new Date();
        console.log('[pauseCountdownTimer] Pause started at:', lastPauseTime.toISOString());
    }
    
    // Update display to show paused state
    const display = document.getElementById('countdown-display');
    if (display) {
        display.style.color = '#ffc107'; // Yellow to indicate paused
    }
}

function resumeCountdownTimer() {
    console.log('[resumeCountdownTimer] ===== FUNCTION CALLED =====');
    console.log('[resumeCountdownTimer] lastPauseTime:', lastPauseTime);
    console.log('[resumeCountdownTimer] pausedRemainingTime:', pausedRemainingTime);
    console.log('[resumeCountdownTimer] Resuming timer');
    
    let pauseDuration = 0;
    
    // Add pause duration to total paused time
    if (lastPauseTime) {
        pauseDuration = new Date() - lastPauseTime;
        totalPausedTime += pauseDuration;
        
        const pauseMins = Math.floor(pauseDuration / 60000);
        const pauseSecs = Math.floor((pauseDuration % 60000) / 1000);
        console.log('[resumeCountdownTimer] Pause duration:', pauseMins, 'min', pauseSecs, 'sec', '(' + pauseDuration + ' ms)');
        console.log('[resumeCountdownTimer] Total paused time:', totalPausedTime, 'ms');
        
        lastPauseTime = null;
    }
    
    // Adjust gameStartTime to account for pause and maintain exact remaining time
    if (pausedRemainingTime && gameStartTime) {
        const remainingMins = Math.floor(pausedRemainingTime / 60000);
        const remainingSecs = Math.floor((pausedRemainingTime % 60000) / 1000);
        console.log('[resumeCountdownTimer] Remaining time at resume:', remainingMins, 'min', remainingSecs, 'sec', '(' + pausedRemainingTime + ' ms)');
        
        const totalGameTime = gameDurationMinutes * 60 * 1000;
        gameStartTime = new Date(new Date() - (totalGameTime - pausedRemainingTime));
        totalPausedTime = 0;  // Reset since we adjusted start time
        pausedRemainingTime = null;
        console.log('[resumeCountdownTimer] Adjusted game start time to maintain remaining time');
    }
    
    // Restart the interval
    if (countdownInterval) {
        console.log('[resumeCountdownTimer] Clearing existing interval');
        clearInterval(countdownInterval);
    }
    console.log('[resumeCountdownTimer] Calling updateCountdownDisplay()');
    updateCountdownDisplay();
    console.log('[resumeCountdownTimer] Setting up new interval');
    countdownInterval = setInterval(updateCountdownDisplay, 1000);
    console.log('[resumeCountdownTimer] Timer resumed, interval ID:', countdownInterval);
}

function stopCountdownTimer() {
    console.log('[stopCountdownTimer] Stopping timer');
    
    if (countdownInterval) {
        clearInterval(countdownInterval);
        countdownInterval = null;
    }
    
    // Hide the countdown timer
    const timerContainer = document.getElementById('countdown-timer');
    if (timerContainer) {
        timerContainer.style.display = 'none';
    }
    
    // Reset variables
    gameStartTime = null;
    totalPausedTime = 0;
    lastPauseTime = null;
    pausedRemainingTime = null;
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
        console.error('Error details:', error.message, error.detail);
        // Re-throw the error so it can be caught by the caller
        throw error;
    }
}

function updateHostDashboard() {
    updatePlayersOverview();
    updateNationsOverview();
    refreshUnassigned();
    updateChallengeRequestsList();
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
    const currentTeam = e.currentTarget.dataset.currentTeam; // May be undefined for unassigned
    
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('playerId', playerId);
    e.dataTransfer.setData('playerName', playerName);
    if (currentTeam) {
        e.dataTransfer.setData('currentTeam', currentTeam);
    }
    
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
                    <strong>${player.name}</strong>
                    <span style="font-size: 12px; color: #666;">Guest User - ID: ${player.id}</span>
                </div>
                <div class="pending-actions">
                    <button class="approve-btn" onclick="approvePlayerAction(${player.id}, '${player.name}')">
                        Approve
                    </button>
                    <button class="reject-btn" onclick="rejectPlayerAction(${player.id}, '${player.name}')">
                        Reject
                    </button>
                </div>
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

// Reject a player
async function rejectPlayerAction(playerId, playerName) {
    // Confirm rejection
    if (!confirm(`Are you sure you want to reject ${playerName}? They will be removed from the game.`)) {
        return;
    }
    
    try {
        await gameAPI.removePlayerFromGame(currentGameCode, playerId);
        console.log(`Rejected player: ${playerName}`);
        
        // Refresh pending list and players overview
        await refreshPendingPlayers();
        await updatePlayersOverview();
        
        // Show success message
        alert(`${playerName} has been rejected and removed from the game.`);
    } catch (error) {
        console.error('Error rejecting player:', error);
        alert('Failed to reject player: ' + error.message);
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

async function clearAllPlayers() {
    if (!confirm(`👥 REMOVE ALL PLAYERS?\n\nThis will:\n• Remove ALL players and bankers (except you as host)\n• Keep the game code ${currentGameCode} active\n• Allow players to rejoin with the same game code\n• Keep all game settings intact\n\nPlayers will be sent back to the join screen but can rejoin immediately.\n\nContinue?`)) {
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

async function deleteGame() {
    if (!confirm(`🗑️ DELETE THIS GAME PERMANENTLY?\n\nThis will:\n• Remove ALL players from the game\n• Delete all game data (challenges, scores, settings)\n• Make the game code ${currentGameCode} permanently unusable\n• Send everyone (including you) back to the join screen\n\nThe game code cannot be reused after deletion.\nPlayer names can still be reused in other games.\n\nThis action CANNOT be undone!`)) {
        return;
    }
    
    // Double confirmation for such a destructive action
    if (!confirm(`Are you ABSOLUTELY SURE you want to permanently delete game ${currentGameCode}?\n\nClick OK to DELETE FOREVER, or Cancel to keep the game.`)) {
        return;
    }
    
    try {
        const result = await gameAPI.deleteGame(currentGameCode);
        console.log(`Game deleted:`, result);
        
        addEventLog(`Game ${currentGameCode} deleted - ${result.deleted_players} players removed`, 'warning');
        
        alert(`Game ${currentGameCode} has been permanently deleted.\n\nAll ${result.deleted_players} players have been notified and removed.`);
        
        // Disconnect WebSocket and redirect to index
        if (gameWS) {
            gameWS.disconnect();
        }
        
        window.location.href = 'index.html';
    } catch (error) {
        console.error('Error deleting game:', error);
        const errorMessage = error.message || error.detail || JSON.stringify(error);
        alert('Failed to delete game: ' + errorMessage);
    }
}

async function resetAllChallenges() {
    if (!confirm('🔄 Reset All Challenges?\n\nThis will:\n• Clear all pending challenge requests\n• Cancel all active challenges\n• Unlock all buildings\n• NOT refund any resources\n\nPlayers will need to request new challenges.\n\nContinue?')) {
        return;
    }
    
    try {
        console.log('[resetAllChallenges] Resetting all challenges for game:', currentGameCode);
        
        // Clear challenge manager's internal state
        if (challengeManager) {
            await challengeManager.clearAll();
        }
        
        // Get all challenges from the server and delete them
        const challenges = await gameAPI.getChallenges(currentGameCode);
        console.log('[resetAllChallenges] Found challenges:', challenges);
        
        let deletedCount = 0;
        for (const challenge of challenges) {
            try {
                await gameAPI.deleteChallenge(currentGameCode, challenge.id);
                deletedCount++;
            } catch (error) {
                console.error(`[resetAllChallenges] Failed to delete challenge ${challenge.id}:`, error);
            }
        }
        
        // Clear local challenge data
        allActiveChallenges = {};
        pendingChallengeRequests = [];
        
        // Refresh UI
        updateChallengeRequestsList();
        updateActiveChallengesList();
        updateAllBuildingButtons();
        
        addEventLog(`All challenges reset (${deletedCount} cleared)`, 'info');
        alert(`✅ Challenge Reset Complete\n\n${deletedCount} challenge(s) cleared.\nAll buildings unlocked.`);
        
        console.log('[resetAllChallenges] Reset complete');
    } catch (error) {
        console.error('[resetAllChallenges] Error:', error);
        alert('Failed to reset challenges: ' + (error.message || error));
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
        
        if (!overviewDiv) {
            // Nations overview not on current tab - skip silently
            return;
        }
        
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
        console.log('[startGame] Starting game...');
        await gameAPI.startGame(currentGameCode);
        console.log('[startGame] Game started on backend');
        
        // Note: WebSocket will broadcast the status change to all players
        // This function is just for the host's immediate feedback
        currentGameStatus = 'in_progress';
        
        // Initialize challenge manager
        await initializeChallengeManager();
        
        addEventLog('Game started!', 'success');
        
        // Update UI immediately
        updateControlButtons();
        updateGameStatusDisplay();
        console.log('[startGame] Control buttons and status display updated');
        
        // Disable test mode when game starts
        updateTestModeToggleState();
        
        // Update player card visibility (for players)
        updatePlayerCardsVisibility();
        console.log('[startGame] Player cards visibility updated');
        
        // Update dashboard to show new status
        updateDashboard();
        console.log('[startGame] Dashboard updated');
    } catch (error) {
        console.error('[startGame] Error:', error);
        alert('Failed to start game: ' + error.message);
    }
}

async function initializeChallengeManager() {
    try {
        console.log('[initializeChallengeManager] Initializing challenge manager...');
        
        // Clean up existing manager if any
        if (challengeManager) {
            challengeManager.destroy();
        }
        
        // Create new challenge manager
        challengeManager = new ChallengeManager(currentGameCode, currentPlayer, gameAPI, gameWS);
        await challengeManager.initialize();
        
        // Set initial game status
        challengeManager.setGameStatus(currentGameStatus);
        
        // Register update callback
        challengeManager.onChallengesUpdated(() => {
            console.log('[ChallengeManager] Challenges updated, refreshing UI');
            updateActiveChallengesList();
            updateChallengeRequestsList();
        });
        
        // Create trading manager
        if (!tradingManager) {
            tradingManager = new TradingManager(currentGameCode, gameAPI, gameWS);
            await tradingManager.initialize();
            console.log('[TradingManager] Initialized');
        }
        
        console.log('[initializeChallengeManager] Challenge manager initialized successfully');
    } catch (error) {
        console.error('[initializeChallengeManager] Failed to initialize challenge manager:', error);
        // Don't throw - allow game to continue even if challenge system fails
    }
}

async function pauseGame() {
    try {
        // Save current pause time for challenge adjustment later
        lastPauseTime = Date.now();
        
        // Update challenge manager status BEFORE pausing to ensure state is captured
        if (challengeManager) {
            challengeManager.setGameStatus('paused', lastPauseTime);
        }
        
        await gameAPI.pauseGame(currentGameCode);
        // Note: WebSocket will broadcast the status change
        currentGameStatus = 'paused';
        
        addEventLog('Game paused');
        updateControlButtons();
        updateGameStatusDisplay();
    } catch (error) {
        alert('Failed to pause game: ' + error.message);
    }
}

async function resumeGame() {
    try {
        // Calculate the duration of the most recent pause
        const pauseDuration = lastPauseTime ? (Date.now() - lastPauseTime) : 0;
        
        console.log(`[resumeGame] Pause duration: ${pauseDuration}ms`);
        
        // Use challenge manager to adjust for pause in database
        if (challengeManager && pauseDuration > 0) {
            try {
                console.log('[resumeGame] Adjusting challenges in database for pause...');
                await challengeManager.adjustForPause(pauseDuration);
                console.log('[resumeGame] Database adjusted successfully');
            } catch (error) {
                console.error('[resumeGame] Challenge manager adjustment failed:', error);
            }
        }
        
        // Resume the game on backend
        await gameAPI.resumeGame(currentGameCode);
        // Note: WebSocket will broadcast the status change to all clients
        
        // Set status to in_progress
        currentGameStatus = 'in_progress';
        
        // Reload challenges from database to get adjusted timestamps
        if (challengeManager) {
            console.log('[resumeGame] Reloading challenges from database...');
            await challengeManager.loadFromServer();
            challengeManager.setGameStatus('in_progress');
            console.log('[resumeGame] Challenges reloaded from database');
        }
        
        addEventLog('Game resumed');
        updateControlButtons();
        updateGameStatusDisplay();
    } catch (error) {
        alert('Failed to resume game: ' + error.message);
    }
}

async function endGame() {
    if (!confirm('Are you sure you want to end the game?')) return;
    
    try {
        const result = await gameAPI.endGame(currentGameCode);
        // Note: WebSocket will broadcast the status change
        currentGameStatus = 'completed';
        addEventLog('Game ended!', 'success');
        updateControlButtons();
        updateGameStatusDisplay();
        
        // Redirect to appropriate report based on role
        if (currentPlayer.role === 'host') {
            setTimeout(() => {
                window.location.href = `host-report.html?gameCode=${currentGameCode}`;
            }, 1000);
        } else if (currentPlayer.role === 'player') {
            setTimeout(() => {
                window.location.href = `player-report.html?gameCode=${currentGameCode}&playerId=${currentPlayer.id}`;
            }, 1000);
        } else {
            // Show final scores for banker
            showFinalScores(result.scores);
        }
    } catch (error) {
        alert('Failed to end game: ' + error.message);
    }
}

async function autoEndGameOnTimeout() {
    console.log('[autoEndGameOnTimeout] Auto-ending game due to timeout');
    
    try {
        const result = await gameAPI.endGame(currentGameCode);
        // Note: WebSocket will broadcast the status change
        currentGameStatus = 'completed';
        addEventLog('Game ended - Time expired!', 'info');
        
        // Redirect to appropriate report based on role
        if (currentPlayer.role === 'host') {
            setTimeout(() => {
                window.location.href = `host-report.html?gameCode=${currentGameCode}`;
            }, 2000);
        } else if (currentPlayer.role === 'player') {
            setTimeout(() => {
                window.location.href = `player-report.html?gameCode=${currentGameCode}&playerId=${currentPlayer.id}`;
            }, 2000);
        }
    } catch (error) {
        console.error('[autoEndGameOnTimeout] Failed to end game:', error);
        alert('Failed to auto-end game: ' + error.message);
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

// ==================== PLAYER DASHBOARD ====================

async function setupNationDashboard() {
    if (playerState.name) {
        document.getElementById('player-title').textContent = playerState.name;
    }
    // Load team members
    refreshTeamMembers();
    // Update card visibility based on game status
    updatePlayerCardsVisibility();
    // Initialize building button states
    await updateAllBuildingButtons();
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
        
        // Update player title to include team number
        const titleElement = document.getElementById('player-title');
        if (titleElement && currentPlayerData.group_number) {
            titleElement.textContent = `Team ${currentPlayerData.group_number} - ${playerState.name || 'Player Dashboard'}`;
        }
    } catch (error) {
        console.error('Error refreshing team members:', error);
    }
}

function updatePlayerDashboard() {
    // Update resources (from TEAM state)
    const resourcesDiv = document.getElementById('nation-resources');
    if (teamState.resources && Object.keys(teamState.resources).length > 0) {
        resourcesDiv.innerHTML = '';
        Object.entries(teamState.resources).forEach(([resource, amount]) => {
            const item = document.createElement('div');
            item.className = 'resource-item';
            item.innerHTML = `
                <span class="resource-name">${formatResourceName(resource)}</span>
                <span class="resource-amount">${amount}</span>
            `;
            resourcesDiv.appendChild(item);
        });
    }
    
    // Update buildings (from TEAM state)
    const buildingsDiv = document.getElementById('nation-buildings');
    if (teamState.buildings && Object.keys(teamState.buildings).length > 0) {
        buildingsDiv.innerHTML = '';
        Object.entries(teamState.buildings).forEach(([building, count]) => {
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
    
    // Update team name section
    updateTeamNameSection();
    
    // Update building button states after dashboard refresh
    updateAllBuildingButtons();
}

// Update team name section for players
async function updateTeamNameSection() {
    const teamNameSection = document.getElementById('team-name-section');
    const currentTeamNameSpan = document.getElementById('current-team-name');
    
    if (!teamNameSection || !currentTeamNameSpan) return;
    
    try {
        // Get game settings to check if team naming is allowed
        const game = await gameAPI.getGame(currentGameCode);
        const allowTeamNames = game.game_state?.allow_team_names || false;
        
        if (!allowTeamNames || !currentPlayer.groupNumber) {
            teamNameSection.style.display = 'none';
            return;
        }
        
        // Get current team name
        const teamNumber = currentPlayer.groupNumber;
        const teamData = game.game_state?.teams?.[String(teamNumber)];
        const teamName = teamData?.nation_name || `Team ${teamNumber}`;
        
        currentTeamNameSpan.textContent = teamName;
        teamNameSection.style.display = 'block';
    } catch (error) {
        console.error('Error updating team name section:', error);
        teamNameSection.style.display = 'none';
    }
}

// Player edits their team name inline
async function editPlayerTeamName() {
    if (!currentPlayer.groupNumber) {
        alert('You must be assigned to a team first!');
        return;
    }
    
    const teamNumber = currentPlayer.groupNumber;
    const currentTeamNameSpan = document.getElementById('current-team-name');
    const editInput = document.getElementById('team-name-edit-input');
    
    if (!currentTeamNameSpan || !editInput) return;
    
    const currentName = currentTeamNameSpan.textContent;
    
    // Show input, hide span
    currentTeamNameSpan.style.display = 'none';
    editInput.style.display = 'block';
    editInput.value = currentName;
    editInput.focus();
    editInput.select();
    
    // Handle save on Enter or blur
    const saveEdit = async () => {
        const newName = editInput.value.trim();
        
        // Hide input, show span
        editInput.style.display = 'none';
        currentTeamNameSpan.style.display = 'block';
        
        if (!newName || newName === currentName) {
            return; // No change
        }
        
        await savePlayerTeamName(newName);
    };
    
    // Handle cancel on Escape
    const cancelEdit = () => {
        editInput.style.display = 'none';
        currentTeamNameSpan.style.display = 'block';
    };
    
    editInput.onblur = saveEdit;
    editInput.onkeydown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            saveEdit();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelEdit();
        }
    };
}

// Save player team name
async function savePlayerTeamName(newName) {
    const teamNumber = currentPlayer.groupNumber;
    const currentTeamNameSpan = document.getElementById('current-team-name');
    
    try {
        // Call API to update team name
        await gameAPI.updateTeamName(currentGameCode, teamNumber, newName.trim());
        
        // Update the display
        if (currentTeamNameSpan) {
            currentTeamNameSpan.textContent = newName.trim();
        }
        
        console.log(`Team renamed to "${newName.trim()}"`);
    } catch (error) {
        console.error('Error choosing team name:', error);
        const errorMessage = error.message || error.detail || JSON.stringify(error);
        alert('Failed to update team name: ' + errorMessage);
        
        // Revert display on error
        await updateTeamNameSection();
    }
}

// Request a challenge from the banker/host
async function requestChallenge(buildingType) {
    // Check if building is locked by an active challenge
    const lockStatus = await checkChallengeLock(buildingType);
    
    if (lockStatus.isLocked) {
        if (lockStatus.lockedByCurrentPlayer) {
            alert(`You already have an active challenge!\n\nYour active challenge: ${lockStatus.buildingName}\n\nComplete your current challenge before requesting a new one.`);
        } else if (lockStatus.teamWide) {
            alert(`All buildings are locked!\n\n${lockStatus.lockedByName} has an active challenge for ${lockStatus.buildingName}.\n\nBuild a School to allow individual team members to work independently!`);
        } else {
            alert(`All buildings are locked!\n\n${lockStatus.lockedByName} has an active challenge for ${lockStatus.buildingName}.\n\nWait for them to complete their challenge.`);
        }
        return;
    }
    
    // Get team buildings to check for school
    const game = await gameAPI.getGame(currentGameCode);
    const teamNumber = currentPlayer.groupNumber;
    
    // Validate team has the building and required resources
    const validationResult = validateProductionRequirements(buildingType, teamNumber);
    if (!validationResult.canProduce) {
        alert(`Cannot request production challenge!\n\n${validationResult.reason}`);
        return;
    }
    
    const hasSchool = checkTeamHasSchool(game, teamNumber);
    
    // Track this as an active challenge using team-specific key
    const challengeKey = hasSchool 
        ? `${currentPlayer.id}-${buildingType}` // Individual key if has school
        : `team${teamNumber}-${buildingType}`; // Team-wide key if no school
    
    allActiveChallenges[challengeKey] = {
        player_id: currentPlayer.id,
        player_name: currentPlayer.name,
        team_number: teamNumber,
        building_type: buildingType,
        has_school: hasSchool,
        status: 'requested'
    };
    
    // Save challenge to database (with bank inventory check)
    let dbId = null;
    try {
        const dbChallenge = await gameAPI.createChallenge(currentGameCode, {
            player_id: currentPlayer.id,
            building_type: buildingType,
            building_name: formatBuildingName(buildingType),
            team_number: teamNumber,
            has_school: hasSchool
        });
        console.log(`[requestChallenge] Challenge saved to database:`, dbChallenge);
        
        // Store the database ID in the challenge object
        allActiveChallenges[challengeKey].db_id = dbChallenge.id;
        dbId = dbChallenge.id;
    } catch (error) {
        console.error('[requestChallenge] Failed to save challenge to database:', error);
        
        // Check if it's a bank inventory error
        if (error.message && error.message.includes('Bank does not have enough')) {
            // Soft error - show user-friendly message
            const resourceMatch = error.message.match(/Bank does not have enough (\w+)/);
            const resourceType = resourceMatch ? resourceMatch[1] : 'resources';
            const resourceName = formatResourceName(resourceType).replace(/^[^\s]+\s/, '');
            
            alert(`🏦 Challenge Request Declined\n\nThe bank doesn't have enough ${resourceName} in stock to grant this challenge reward.\n\nPlease try requesting a challenge for a different building type, or ask the banker to restock inventory.`);
            
            // Remove from active challenges since it failed
            delete allActiveChallenges[challengeKey];
            
            // Reset button
            const requestBtn = document.getElementById(`${buildingType}-request-btn`);
            if (requestBtn) {
                requestBtn.disabled = false;
                requestBtn.textContent = '🎯 Request Challenge';
            }
            
            addEventLog(`❌ Challenge declined: Bank has insufficient ${resourceName}`, 'warning');
            return; // Stop here, don't send WebSocket event
        }
        
        // For other errors, continue anyway - we'll rely on WebSocket events
        console.warn('[requestChallenge] Non-inventory error, continuing with WebSocket...');
    }
    
    // Send challenge request via WebSocket (include db_id from HTTP response)
    gameWS.send({
        type: 'event',
        event_type: 'challenge_request',
        data: {
            player_id: currentPlayer.id,
            player_name: currentPlayer.name,
            building_type: buildingType,
            building_name: formatBuildingName(buildingType),
            team_number: teamNumber,
            has_school: hasSchool,
            db_id: dbId  // Include database ID for assignment
        }
    });
    
    // Update UI to show request is pending
    const requestBtn = document.getElementById(`${buildingType}-request-btn`);
    if (requestBtn) {
        requestBtn.disabled = true;
        requestBtn.textContent = '⏳ Awaiting Challenge...';
    }
    
    // Update UI for other team members
    updateAllBuildingButtons();
    
    addEventLog(`Challenge requested for ${formatBuildingName(buildingType)}`, 'info');
}

// Validate that team has the building and required resources for production
function validateProductionRequirements(buildingType, teamNumber) {
    // Production requirements (from backend game_constants.py)
    const productionRequirements = {
        'farm': {
            output: 'Food',
            inputRequired: null
        },
        'mine': {
            output: 'Raw Materials',
            inputRequired: null
        },
        'electrical_factory': {
            output: 'Electrical Goods',
            inputRequired: { 'raw_materials': 5 }
        },
        'medical_factory': {
            output: 'Medical Goods',
            inputRequired: { 'food': 5 }
        }
    };
    
    const requirements = productionRequirements[buildingType];
    if (!requirements) {
        return { canProduce: false, reason: 'Invalid building type' };
    }
    
    // For players: use the global teamState which was loaded in loadGameData()
    // For host/banker: try to get from gameState.teams first, fall back to teamState
    let teamData;
    if (gameState?.teams) {
        const teamKey = String(teamNumber);
        teamData = gameState.teams[teamKey];
    }
    
    // If not found in gameState.teams, use the global teamState
    // This handles the player case where gameState.teams might be undefined
    if (!teamData) {
        teamData = teamState;
    }
    
    console.log(`[validateProductionRequirements] Checking ${buildingType} for team ${teamNumber}`);
    console.log(`[validateProductionRequirements] Using teamData:`, teamData);
    
    if (!teamData || !teamData.buildings) {
        console.error(`[validateProductionRequirements] No team data found for team ${teamNumber}`);
        return { canProduce: false, reason: 'Team data not found' };
    }
    
    // Check if team has the building
    const buildingCount = teamData.buildings[buildingType] || 0;
    console.log(`[validateProductionRequirements] Building count for ${buildingType}:`, buildingCount);
    if (buildingCount === 0) {
        const buildingName = formatBuildingName(buildingType).replace(/^[^\s]+\s/, ''); // Remove emoji
        return { 
            canProduce: false, 
            reason: `Your team doesn't have any ${buildingName} buildings.\n\nBuild one first before requesting production.` 
        };
    }
    
    // Check if team has required input resources
    if (requirements.inputRequired) {
        for (const [resource, amount] of Object.entries(requirements.inputRequired)) {
            const currentAmount = teamData.resources[resource] || 0;
            if (currentAmount < amount) {
                const resourceName = formatResourceName(resource).replace(/^[^\s]+\s/, ''); // Remove emoji
                return {
                    canProduce: false,
                    reason: `Insufficient ${resourceName}!\n\nRequired: ${amount}\nYou have: ${currentAmount}\n\nObtain more ${resourceName} before producing ${requirements.output}.`
                };
            }
        }
    }
    
    return { canProduce: true };
}

// Check if team has a school building
function checkTeamHasSchool(game, teamNumber) {
    if (!game || !game.game_state || !game.game_state.teams) {
        return false;
    }
    
    // Get team state (stored as string keys in backend)
    const teamState = game.game_state.teams[String(teamNumber)];
    
    if (!teamState || !teamState.buildings) {
        return false;
    }
    
    // Check if school count > 0
    return (teamState.buildings.school || 0) > 0;
}

// Check if a building type is locked by an active challenge
// NOTE: When a challenge is active, ALL buildings are locked (not just the requested building type)
async function checkChallengeLock(buildingType) {
    const currentTeamNumber = currentPlayer.groupNumber;
    
    console.log(`[checkChallengeLock] Checking ${buildingType} for player ${currentPlayer.name} (Team ${currentTeamNumber})`);
    console.log('[checkChallengeLock] allActiveChallenges:', JSON.stringify(allActiveChallenges, null, 2));
    
    // Check all active challenges - any challenge locks ALL buildings
    for (const [key, challenge] of Object.entries(allActiveChallenges)) {
        console.log(`[checkChallengeLock] Examining challenge key: ${key}`, challenge);
        console.log(`[checkChallengeLock] Challenge for building: ${challenge.building_type}, team: ${challenge.team_number}`);
        console.log(`[checkChallengeLock] Current team: ${currentTeamNumber}, Has school: ${challenge.has_school}`);
        
        // If no school, check team-wide lock (locks all buildings for the team)
        if (!challenge.has_school) {
            console.log(`[checkChallengeLock] No school - checking team-wide lock`);
            // Only lock if same team
            if (challenge.team_number === currentTeamNumber) {
                console.log(`[checkChallengeLock] LOCKED - Same team, team-wide lock (all buildings locked)`);
                return {
                    isLocked: true,
                    teamWide: true,
                    lockedByName: challenge.player_name,
                    lockedByCurrentPlayer: challenge.player_id === currentPlayer.id,
                    buildingName: formatBuildingName(challenge.building_type),
                    activeBuildingType: challenge.building_type
                };
            } else {
                console.log(`[checkChallengeLock] Different team (${challenge.team_number} vs ${currentTeamNumber}) - not locked`);
            }
        } else {
            console.log(`[checkChallengeLock] Has school - checking individual lock`);
            // With school, only lock for the specific player (locks all buildings for that player)
            if (challenge.player_id === currentPlayer.id && challenge.team_number === currentTeamNumber) {
                console.log(`[checkChallengeLock] LOCKED - Same player and team (all buildings locked for this player only)`);
                return {
                    isLocked: true,
                    teamWide: false,
                    lockedByName: challenge.player_name,
                    lockedByCurrentPlayer: true,
                    buildingName: formatBuildingName(challenge.building_type),
                    activeBuildingType: challenge.building_type
                };
            } else {
                console.log(`[checkChallengeLock] Different player (${challenge.player_id} vs ${currentPlayer.id}) or team - NOT locked (has school = individual locks)`);
                // Don't lock - this is a different player and the team has a school
            }
        }
    }
    
    console.log(`[checkChallengeLock] No locks found - returning unlocked`);
    return { isLocked: false };
}

// Update all building buttons based on active challenges
function updateAllBuildingButtons() {
    const buildingTypes = ['farm', 'mine', 'electrical_factory', 'medical_factory'];
    
    buildingTypes.forEach(async (buildingType) => {
        const requestBtn = document.getElementById(`${buildingType}-request-btn`);
        if (!requestBtn) return;
        
        const lockStatus = await checkChallengeLock(buildingType);
        const teamNumber = currentPlayer.groupNumber;
        const validationResult = validateProductionRequirements(buildingType, teamNumber);
        
        // Priority 1: Check if requirements are met (show this even if locked)
        if (!validationResult.canProduce) {
            // Requirements not met - show missing requirements
            requestBtn.disabled = true;
            requestBtn.textContent = '❌ Missing Requirements';
            requestBtn.title = validationResult.reason.replace(/\n\n/g, ' ');
        }
        // Priority 2: Check if locked by a challenge
        else if (lockStatus.isLocked) {
            requestBtn.disabled = true;
            if (lockStatus.lockedByCurrentPlayer) {
                requestBtn.textContent = '⏳ Challenge Active';
                requestBtn.title = 'Complete your current challenge before requesting a new one';
            } else if (lockStatus.teamWide) {
                requestBtn.textContent = `🔒 ${lockStatus.lockedByName} is working`;
                requestBtn.title = `${lockStatus.lockedByName} has an active challenge. Build a School to work independently!`;
            } else {
                requestBtn.textContent = '🔒 Locked';
                requestBtn.title = 'Another team member has an active challenge';
            }
        }
        // Priority 3: Requirements met and not locked - enable
        else {
            requestBtn.disabled = false;
            requestBtn.textContent = '📋 Request Challenge';
            requestBtn.title = '';
        }
    });
}

// Called when banker/host assigns a challenge
function receiveChallengeAssignment(buildingType, challengeDescription) {
    // Update the challenge display
    const challengeSpan = document.getElementById(`${buildingType}-challenge`);
    const challengeDisplay = document.getElementById(`${buildingType}-challenge-display`);
    const requestBtn = document.getElementById(`${buildingType}-request-btn`);
    const produceBtn = document.getElementById(`${buildingType}-produce-btn`);
    
    if (challengeSpan) challengeSpan.textContent = challengeDescription;
    if (challengeDisplay) challengeDisplay.style.display = 'block';
    if (requestBtn) {
        requestBtn.style.display = 'none';
        requestBtn.disabled = false;
        requestBtn.textContent = '📋 Request Challenge';
    }
    if (produceBtn) produceBtn.style.display = 'inline-block';
    
    addEventLog(`Challenge assigned: ${challengeDescription}`, 'success');
}

function startProduction(buildingType) {
    // Get the assigned challenge
    const challengeSpan = document.getElementById(`${buildingType}-challenge`);
    const challengeDescription = challengeSpan ? challengeSpan.textContent : 'Unknown challenge';
    
    // Show challenge modal
    const modal = document.getElementById('challenge-modal');
    const description = document.getElementById('challenge-description');
    
    description.textContent = challengeDescription;
    modal.classList.remove('hidden');
    modal.dataset.buildingType = buildingType;
}

function completeChallenge() {
    const modal = document.getElementById('challenge-modal');
    const buildingType = modal.dataset.buildingType;
    
    // Clear the active challenge lock (all possible key formats)
    delete allActiveChallenges[buildingType];
    delete allActiveChallenges[`${currentPlayer.id}-${buildingType}`];
    delete allActiveChallenges[`team${currentPlayer.groupNumber}-${buildingType}`];
    
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
    
    // Notify team members that building is now available
    gameWS.send({
        type: 'event',
        event_type: 'challenge_completed',
        data: {
            player_id: currentPlayer.id,
            player_name: currentPlayer.name,
            building_type: buildingType,
            team_number: currentPlayer.groupNumber
        }
    });
    
    // Update active challenges list if on that tab
    updateActiveChallengesList();
    
    // Reset challenge UI - player needs to request new challenge for next production
    const challengeDisplay = document.getElementById(`${buildingType}-challenge-display`);
    const challengeSpan = document.getElementById(`${buildingType}-challenge`);
    const requestBtn = document.getElementById(`${buildingType}-request-btn`);
    const produceBtn = document.getElementById(`${buildingType}-produce-btn`);
    
    if (challengeDisplay) challengeDisplay.style.display = 'none';
    if (challengeSpan) challengeSpan.textContent = 'Awaiting challenge...';
    if (requestBtn) {
        requestBtn.style.display = 'inline-block';
        requestBtn.disabled = false;
        requestBtn.textContent = '📋 Request Challenge';
    }
    if (produceBtn) produceBtn.style.display = 'none';
    
    // Update buttons for all team members
    updateAllBuildingButtons();
    
    addEventLog(`Completed production at ${formatBuildingName(buildingType)}`, 'success');
    closeChallengeModal();
}

function closeChallengeModal() {
    document.getElementById('challenge-modal').classList.add('hidden');
}

// ==================== TRADING FUNCTIONS ====================

async function openTradeWindow(tradeType) {
    if (!tradingManager) {
        alert('Trading system not initialized. Please wait for game to start.');
        return;
    }

    if (tradeType === 'bank') {
        await openBankTradeModal();
    } else if (tradeType === 'nation') {
        await openTeamTradeModal();
    }
}

async function openBankTradeModal() {
    // Initialize trading manager if not done
    if (!tradingManager) {
        tradingManager = new TradingManager(currentGameCode, gameAPI, gameWS);
        await tradingManager.initialize();
    }
    
    // Show modal
    document.getElementById('bank-trade-modal').classList.remove('hidden');
    
    // Load current prices
    await tradingManager.loadCurrentPrices();
}

function closeBankTradeModal() {
    document.getElementById('bank-trade-modal').classList.add('hidden');
    
    // Destroy chart if exists
    if (tradingManager && tradingManager.priceChart) {
        tradingManager.priceChart.destroy();
        tradingManager.priceChart = null;
    }
}

async function updateBankTradeDisplay() {
    const resource = document.getElementById('bank-trade-resource').value;
    
    if (!resource) {
        document.getElementById('price-chart-container').style.display = 'none';
        document.getElementById('current-prices-display').style.display = 'none';
        document.getElementById('bank-trade-form').style.display = 'none';
        return;
    }
    
    // Load and display price history
    await tradingManager.loadPriceHistory(resource, 50);
    tradingManager.renderPriceChart('price-chart', resource);
    document.getElementById('price-chart-container').style.display = 'block';
    
    // Display current prices
    const prices = tradingManager.currentPrices[resource];
    if (prices) {
        document.getElementById('bank-buy-price').textContent = prices.buy.toFixed(2) + ' 💰';
        document.getElementById('bank-sell-price').textContent = prices.sell.toFixed(2) + ' 💰';
        document.getElementById('current-prices-display').style.display = 'block';
    }
    
    // Show trade form
    document.getElementById('bank-trade-form').style.display = 'block';
    
    // Update your resources display
    updateBankTradeResourceDisplay();
    
    // Setup amount change listeners
    document.getElementById('buy-amount').oninput = updateBankTradeCosts;
    document.getElementById('sell-amount').oninput = updateBankTradeCosts;
    updateBankTradeCosts();
}

function updateBankTradeResourceDisplay() {
    const resource = document.getElementById('bank-trade-resource').value;
    if (!resource || !teamState.resources) return;
    
    const currency = teamState.resources.currency || 0;
    const stock = teamState.resources[resource] || 0;
    
    document.getElementById('buy-your-currency').textContent = currency + ' 💰';
    document.getElementById('sell-your-stock').textContent = stock + ' ' + tradingManager.getResourceEmoji(resource);
}

function updateBankTradeCosts() {
    const resource = document.getElementById('bank-trade-resource').value;
    if (!resource) return;
    
    const prices = tradingManager.currentPrices[resource];
    if (!prices) return;
    
    // Buy calculation
    const buyAmount = parseInt(document.getElementById('buy-amount').value) || 0;
    const buyCost = (buyAmount * prices.sell).toFixed(2);
    document.getElementById('buy-total-cost').textContent = buyCost + ' 💰';
    
    // Sell calculation
    const sellAmount = parseInt(document.getElementById('sell-amount').value) || 0;
    const sellRevenue = (sellAmount * prices.buy).toFixed(2);
    document.getElementById('sell-total-revenue').textContent = sellRevenue + ' 💰';
}

async function executeBankTrade(tradeType) {
    const resource = document.getElementById('bank-trade-resource').value;
    if (!resource) {
        alert('Please select a resource');
        return;
    }
    
    const teamNumber = currentPlayer.group_number || teamState.team_number;
    if (!teamNumber) {
        alert('Team number not found');
        return;
    }
    
    const amount = tradeType === 'buy' 
        ? parseInt(document.getElementById('buy-amount').value)
        : parseInt(document.getElementById('sell-amount').value);
    
    if (!amount || amount <= 0) {
        alert('Please enter a valid amount');
        return;
    }
    
    try {
        const result = await tradingManager.executeBankTrade(teamNumber, resource, amount, tradeType);
        
        if (result.success) {
            alert(`✅ ${result.message}\n\nTotal ${tradeType === 'buy' ? 'Cost' : 'Revenue'}: ${result.total_cost.toFixed(2)} 💰`);
            
            // Update local team state
            if (result.new_resources) {
                teamState.resources = result.new_resources;
                updateResourceDisplay();
            }
            
            // Refresh display
            await updateBankTradeDisplay();
        } else {
            alert('❌ Trade failed: ' + result.message);
        }
    } catch (error) {
        alert('❌ Trade failed: ' + error.message);
        console.error('[executeBankTrade] Error:', error);
    }
}

async function openTeamTradeModal() {
    // Initialize trading manager if not done
    if (!tradingManager) {
        tradingManager = new TradingManager(currentGameCode, gameAPI, gameWS);
        await tradingManager.initialize();
    }
    
    // Show modal
    document.getElementById('team-trade-modal').classList.remove('hidden');
    
    // Populate team dropdown
    populateTeamDropdown();
    
    // Initialize with empty resource inputs
    initializeTradeResourceInputs();
    
    // Load active offers
    await loadTeamTradeOffers();
}

function closeTeamTradeModal() {
    document.getElementById('team-trade-modal').classList.add('hidden');
}

function switchTeamTradeTab(tab) {
    // Update tab buttons
    document.getElementById('team-trade-tab-create').classList.toggle('active', tab === 'create');
    document.getElementById('team-trade-tab-offers').classList.toggle('active', tab === 'offers');
    
    // Update tab styling
    document.getElementById('team-trade-tab-create').style.borderBottom = tab === 'create' ? '3px solid #667eea' : '3px solid transparent';
    document.getElementById('team-trade-tab-offers').style.borderBottom = tab === 'offers' ? '3px solid #667eea' : '3px solid transparent';
    
    // Show/hide tab content
    document.getElementById('team-trade-create-tab').classList.toggle('hidden', tab !== 'create');
    document.getElementById('team-trade-offers-tab').classList.toggle('hidden', tab !== 'offers');
    
    if (tab === 'offers') {
        loadTeamTradeOffers();
    }
}

function populateTeamDropdown() {
    const dropdown = document.getElementById('trade-to-team');
    const currentTeam = currentPlayer.group_number || teamState.team_number;
    
    dropdown.innerHTML = '<option value="">Select Team...</option>';
    
    // Add all teams except current team
    const numTeams = Object.keys(gameState.teams || {}).length;
    for (let i = 1; i <= numTeams; i++) {
        if (i !== currentTeam) {
            dropdown.innerHTML += `<option value="${i}">Team ${i}</option>`;
        }
    }
}

function initializeTradeResourceInputs() {
    document.getElementById('offering-resources').innerHTML = '';
    document.getElementById('requesting-resources').innerHTML = '';
    
    addOfferingResource();
    addRequestingResource();
}

function addOfferingResource() {
    const container = document.getElementById('offering-resources');
    const index = container.children.length;
    
    const html = `
        <div class="resource-input-row" style="display: flex; gap: 10px; margin-bottom: 10px;">
            <select class="offering-resource-type" style="flex: 1; padding: 6px; border-radius: 4px; border: 1px solid #ddd;">
                <option value="">Resource...</option>
                <option value="food">🌾 Food</option>
                <option value="raw_materials">⛏️ Raw Materials</option>
                <option value="electrical_goods">⚡ Electrical</option>
                <option value="medical_goods">🏥 Medical</option>
                <option value="currency">💰 Currency</option>
            </select>
            <input type="number" class="offering-amount" min="1" placeholder="Amount" style="width: 100px; padding: 6px; border-radius: 4px; border: 1px solid #ddd;">
            <button type="button" onclick="this.parentElement.remove()" style="padding: 6px 12px; border: none; background: #ef4444; color: white; border-radius: 4px; cursor: pointer;">✖</button>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', html);
}

function addRequestingResource() {
    const container = document.getElementById('requesting-resources');
    const index = container.children.length;
    
    const html = `
        <div class="resource-input-row" style="display: flex; gap: 10px; margin-bottom: 10px;">
            <select class="requesting-resource-type" style="flex: 1; padding: 6px; border-radius: 4px; border: 1px solid #ddd;">
                <option value="">Resource...</option>
                <option value="food">🌾 Food</option>
                <option value="raw_materials">⛏️ Raw Materials</option>
                <option value="electrical_goods">⚡ Electrical</option>
                <option value="medical_goods">🏥 Medical</option>
                <option value="currency">💰 Currency</option>
            </select>
            <input type="number" class="requesting-amount" min="1" placeholder="Amount" style="width: 100px; padding: 6px; border-radius: 4px; border: 1px solid #ddd;">
            <button type="button" onclick="this.parentElement.remove()" style="padding: 6px 12px; border: none; background: #ef4444; color: white; border-radius: 4px; cursor: pointer;">✖</button>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', html);
}

async function createTeamTradeOffer(event) {
    event.preventDefault();
    
    const toTeam = parseInt(document.getElementById('trade-to-team').value);
    if (!toTeam) {
        alert('Please select a team');
        return;
    }
    
    const fromTeam = currentPlayer.group_number || teamState.team_number;
    
    // Collect offering resources
    const offering = {};
    document.querySelectorAll('.offering-resource-type').forEach((select, index) => {
        const resource = select.value;
        const amount = parseInt(document.querySelectorAll('.offering-amount')[index].value);
        if (resource && amount > 0) {
            offering[resource] = amount;
        }
    });
    
    // Collect requesting resources
    const requesting = {};
    document.querySelectorAll('.requesting-resource-type').forEach((select, index) => {
        const resource = select.value;
        const amount = parseInt(document.querySelectorAll('.requesting-amount')[index].value);
        if (resource && amount > 0) {
            requesting[resource] = amount;
        }
    });
    
    if (Object.keys(offering).length === 0) {
        alert('Please add at least one resource you are offering');
        return;
    }
    
    if (Object.keys(requesting).length === 0) {
        alert('Please add at least one resource you are requesting');
        return;
    }
    
    const message = document.getElementById('trade-message').value;
    
    try {
        const offer = await tradingManager.createTradeOffer(fromTeam, toTeam, offering, requesting, message);
        alert('✅ Trade offer sent successfully!');
        
        // Reset form
        document.getElementById('team-trade-offer-form').reset();
        initializeTradeResourceInputs();
        
        // Switch to offers tab
        switchTeamTradeTab('offers');
    } catch (error) {
        alert('❌ Failed to create trade offer: ' + error.message);
        console.error('[createTeamTradeOffer] Error:', error);
    }
}

async function loadTeamTradeOffers() {
    const teamNumber = currentPlayer.group_number || teamState.team_number;
    
    try {
        await tradingManager.loadTradeOffers(teamNumber, false);
        displayTeamTradeOffers();
    } catch (error) {
        console.error('[loadTeamTradeOffers] Error:', error);
        document.getElementById('team-trade-offers-list').innerHTML = '<p style="color: #ef4444;">Failed to load trade offers</p>';
    }
}

function displayTeamTradeOffers() {
    const container = document.getElementById('team-trade-offers-list');
    const offers = tradingManager.activeOffers;
    const currentTeam = currentPlayer.group_number || teamState.team_number;
    
    if (offers.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No active trade offers</p>';
        return;
    }
    
    let html = '';
    
    offers.forEach(offer => {
        const isFrom = offer.from_team === currentTeam;
        const isTo = offer.to_team === currentTeam;
        
        // Determine which resources to show (original or counter)
        let offering = offer.offering;
        let requesting = offer.requesting;
        if (offer.status === 'countered' && offer.counter_offer) {
            offering = offer.counter_offer.offering;
            requesting = offer.counter_offer.requesting;
        }
        
        html += `
            <div style="margin-bottom: 20px; padding: 15px; border: 2px solid ${offer.status === 'pending' ? '#667eea' : '#f59e0b'}; border-radius: 8px; background: white;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <div>
                        <strong>Team ${offer.from_team}</strong> → <strong>Team ${offer.to_team}</strong>
                    </div>
                    <span style="padding: 4px 8px; background: ${offer.status === 'pending' ? '#dbeafe' : '#fef3c7'}; color: ${offer.status === 'pending' ? '#1e40af' : '#92400e'}; border-radius: 4px; font-size: 12px; font-weight: 600;">
                        ${offer.status.toUpperCase()}
                    </span>
                </div>
                
                ${offer.status === 'countered' ? '<div style="margin-bottom: 10px; padding: 8px; background: #fef3c7; border-radius: 4px; font-size: 14px; color: #92400e;">⚠️ Counter Offer Received</div>' : ''}
                
                <div style="display: grid; grid-template-columns: 1fr auto 1fr; gap: 15px; margin-bottom: 10px;">
                    <div>
                        <div style="font-weight: 600; margin-bottom: 5px;">📤 Offering:</div>
                        ${formatResourceList(offering)}
                    </div>
                    <div style="display: flex; align-items: center; justify-content: center;">
                        <span style="font-size: 24px;">↔️</span>
                    </div>
                    <div>
                        <div style="font-weight: 600; margin-bottom: 5px;">📥 Requesting:</div>
                        ${formatResourceList(requesting)}
                    </div>
                </div>
                
                ${offer.message ? `<div style="padding: 8px; background: #f3f4f6; border-radius: 4px; margin-bottom: 10px; font-style: italic;">"${offer.message}"</div>` : ''}
                
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    ${isTo ? `
                        <button class="btn btn-success" onclick="acceptTeamTradeOffer('${offer.offer_id}')" style="flex: 1;">✅ Accept</button>
                        <button class="btn btn-warning" onclick="openCounterOfferModal('${offer.offer_id}')" style="flex: 1;">🔄 Counter</button>
                        <button class="btn btn-danger" onclick="rejectTeamTradeOffer('${offer.offer_id}')">❌ Reject</button>
                    ` : ''}
                    ${isFrom ? `
                        <button class="btn btn-danger" onclick="cancelTeamTradeOffer('${offer.offer_id}')" style="flex: 1;">🗑️ Cancel Offer</button>
                    ` : ''}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function formatResourceList(resources) {
    const items = Object.entries(resources).map(([resource, amount]) => {
        const emoji = tradingManager.getResourceEmoji(resource);
        const name = tradingManager.formatResourceName(resource);
        return `<div>${emoji} ${amount} ${name}</div>`;
    });
    return items.join('') || '<div style="color: #999;">None</div>';
}

async function acceptTeamTradeOffer(offerId) {
    if (!confirm('Accept this trade offer?')) return;
    
    try {
        await tradingManager.acceptTradeOffer(offerId);
        alert('✅ Trade completed successfully!');
        await loadTeamTradeOffers();
    } catch (error) {
        alert('❌ Failed to accept offer: ' + error.message);
        console.error('[acceptTeamTradeOffer] Error:', error);
    }
}

async function rejectTeamTradeOffer(offerId) {
    if (!confirm('Reject this trade offer?')) return;
    
    try {
        await tradingManager.rejectTradeOffer(offerId);
        alert('Trade offer rejected');
        await loadTeamTradeOffers();
    } catch (error) {
        alert('❌ Failed to reject offer: ' + error.message);
        console.error('[rejectTeamTradeOffer] Error:', error);
    }
}

async function cancelTeamTradeOffer(offerId) {
    if (!confirm('Cancel this trade offer?')) return;
    
    try {
        await tradingManager.cancelTradeOffer(offerId);
        alert('Trade offer cancelled');
        await loadTeamTradeOffers();
    } catch (error) {
        alert('❌ Failed to cancel offer: ' + error.message);
        console.error('[cancelTeamTradeOffer] Error:', error);
    }
}

function openCounterOfferModal(offerId) {
    // For now, use a simple prompt-based counter offer
    // In a full implementation, this would open a dedicated modal
    const offer = tradingManager.activeOffers.find(o => o.offer_id === offerId);
    if (!offer) return;
    
    alert('Counter offer feature: Use the trade creation form to make a new offer with adjusted terms.');
}

async function updateTradingUI() {
    // Called when bank trade completes via WebSocket
    if (tradingManager && document.getElementById('bank-trade-modal').classList.contains('hidden') === false) {
        await updateBankTradeDisplay();
    }
}

async function updateTeamTradeUI() {
    // Called when team trade events occur via WebSocket
    if (tradingManager && document.getElementById('team-trade-modal').classList.contains('hidden') === false) {
        await loadTeamTradeOffers();
    }
}

// ==================== BUILDING RENTAL FUNCTIONS ====================

async function openBuildingRentalModal() {
    // Initialize trading manager if not done
    if (!tradingManager) {
        tradingManager = new TradingManager(currentGameCode, gameAPI, gameWS);
        await tradingManager.initialize();
    }
    
    // Show modal
    document.getElementById('building-rental-modal').classList.remove('hidden');
    
    // Populate team dropdown
    populateRentalTeamDropdown();
    
    // Load rental offers and active rentals
    await loadRentalOffers();
    await loadActiveRentals();
}

function closeBuildingRentalModal() {
    document.getElementById('building-rental-modal').classList.add('hidden');
}

function switchRentalTab(tab) {
    // Update tab buttons
    document.getElementById('rental-tab-request').classList.toggle('active', tab === 'request');
    document.getElementById('rental-tab-offers').classList.toggle('active', tab === 'offers');
    document.getElementById('rental-tab-active').classList.toggle('active', tab === 'active');
    
    // Update tab styling
    document.getElementById('rental-tab-request').style.borderBottom = tab === 'request' ? '3px solid #667eea' : '3px solid transparent';
    document.getElementById('rental-tab-offers').style.borderBottom = tab === 'offers' ? '3px solid #667eea' : '3px solid transparent';
    document.getElementById('rental-tab-active').style.borderBottom = tab === 'active' ? '3px solid #667eea' : '3px solid transparent';
    
    // Show/hide tab content
    document.getElementById('rental-request-tab').classList.toggle('hidden', tab !== 'request');
    document.getElementById('rental-offers-tab').classList.toggle('hidden', tab !== 'offers');
    document.getElementById('rental-active-tab').classList.toggle('hidden', tab !== 'active');
    
    if (tab === 'offers') {
        loadRentalOffers();
    } else if (tab === 'active') {
        loadActiveRentals();
    }
}

function populateRentalTeamDropdown() {
    const dropdown = document.getElementById('rental-owner-team');
    const currentTeam = currentPlayer.group_number || teamState.team_number;
    
    dropdown.innerHTML = '<option value="">Select Team...</option>';
    
    // Add all teams except current team
    const numTeams = Object.keys(gameState.teams || {}).length;
    for (let i = 1; i <= numTeams; i++) {
        if (i !== currentTeam) {
            dropdown.innerHTML += `<option value="${i}">Team ${i}</option>`;
        }
    }
}

async function createBuildingRentalRequest(event) {
    event.preventDefault();
    
    const ownerTeam = parseInt(document.getElementById('rental-owner-team').value);
    const buildingType = document.getElementById('rental-building-type').value;
    const rentalPrice = parseFloat(document.getElementById('rental-price').value);
    const duration = parseInt(document.getElementById('rental-duration').value);
    const message = document.getElementById('rental-message').value;
    
    if (!ownerTeam || !buildingType || !rentalPrice) {
        alert('Please fill in all required fields');
        return;
    }
    
    const renterTeam = currentPlayer.group_number || teamState.team_number;
    
    try {
        const offer = await tradingManager.createRentalOffer(
            renterTeam,
            ownerTeam,
            buildingType,
            rentalPrice,
            duration,
            message || null
        );
        
        alert('✅ Building rental request sent successfully!');
        
        // Reset form
        document.getElementById('building-rental-request-form').reset();
        
        // Switch to offers tab
        switchRentalTab('offers');
    } catch (error) {
        alert('❌ Failed to create rental request: ' + error.message);
        console.error('[createBuildingRentalRequest] Error:', error);
    }
}

async function loadRentalOffers() {
    const teamNumber = currentPlayer.group_number || teamState.team_number;
    
    try {
        await tradingManager.loadRentalOffers(teamNumber, false);
        displayRentalOffers();
    } catch (error) {
        console.error('[loadRentalOffers] Error:', error);
        document.getElementById('rental-offers-list').innerHTML = '<p style="color: #ef4444;">Failed to load rental offers</p>';
    }
}

async function loadActiveRentals() {
    const teamNumber = currentPlayer.group_number || teamState.team_number;
    
    try {
        await tradingManager.loadActiveRentals(teamNumber);
        displayActiveRentals();
    } catch (error) {
        console.error('[loadActiveRentals] Error:', error);
        document.getElementById('rental-active-list').innerHTML = '<p style="color: #ef4444;">Failed to load active rentals</p>';
    }
}

function displayRentalOffers() {
    const container = document.getElementById('rental-offers-list');
    const offers = tradingManager.rentalOffers;
    const currentTeam = currentPlayer.group_number || teamState.team_number;
    
    if (offers.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No rental offers</p>';
        return;
    }
    
    let html = '';
    
    offers.forEach(offer => {
        const isRequester = offer.from_team === currentTeam;
        const isOwner = offer.to_team === currentTeam;
        
        // Determine price to show
        let rentalPrice = offer.rental_price;
        let duration = offer.duration_cycles;
        if (offer.status === 'countered' && offer.counter_offer) {
            rentalPrice = offer.counter_offer.rental_price;
            duration = offer.counter_offer.duration_cycles || offer.duration_cycles;
        }
        
        const buildingEmoji = tradingManager.getBuildingEmoji(offer.building_type);
        const buildingName = tradingManager.formatBuildingName(offer.building_type);
        
        html += `
            <div style="margin-bottom: 20px; padding: 15px; border: 2px solid ${offer.status === 'pending' ? '#667eea' : '#f59e0b'}; border-radius: 8px; background: white;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <div>
                        <strong>Team ${offer.from_team}</strong> → <strong>Team ${offer.to_team}</strong>
                    </div>
                    <span style="padding: 4px 8px; background: ${offer.status === 'pending' ? '#dbeafe' : '#fef3c7'}; color: ${offer.status === 'pending' ? '#1e40af' : '#92400e'}; border-radius: 4px; font-size: 12px; font-weight: 600;">
                        ${offer.status.toUpperCase()}
                    </span>
                </div>
                
                ${offer.status === 'countered' ? '<div style="margin-bottom: 10px; padding: 8px; background: #fef3c7; border-radius: 4px; font-size: 14px; color: #92400e;">⚠️ Counter Offer Received</div>' : ''}
                
                <div style="margin-bottom: 10px;">
                    <div style="font-size: 16px; font-weight: 600; margin-bottom: 5px;">
                        ${buildingEmoji} ${buildingName}
                    </div>
                    <div>💰 Rental Price: <strong>${rentalPrice.toFixed(2)}</strong> currency per cycle</div>
                    <div>⏱️ Duration: <strong>${duration}</strong> production cycles</div>
                    <div>📊 Total Cost: <strong>${(rentalPrice * duration).toFixed(2)}</strong> currency</div>
                </div>
                
                ${offer.message ? `<div style="padding: 8px; background: #f3f4f6; border-radius: 4px; margin-bottom: 10px; font-style: italic;">"${offer.message}"</div>` : ''}
                
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    ${isOwner ? `
                        <button class="btn btn-success" onclick="acceptRentalOffer('${offer.offer_id}')" style="flex: 1;">✅ Accept</button>
                        <button class="btn btn-warning" onclick="openRentalCounterModal('${offer.offer_id}')" style="flex: 1;">🔄 Counter</button>
                        <button class="btn btn-danger" onclick="rejectRentalOffer('${offer.offer_id}')">❌ Reject</button>
                    ` : ''}
                    ${isRequester ? `
                        <button class="btn btn-danger" onclick="cancelRentalOffer('${offer.offer_id}')" style="flex: 1;">🗑️ Cancel Request</button>
                    ` : ''}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function displayActiveRentals() {
    const container = document.getElementById('rental-active-list');
    const rentals = tradingManager.activeRentals;
    
    if (rentals.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No active rentals</p>';
        return;
    }
    
    let html = '';
    
    rentals.forEach(rental => {
        const buildingEmoji = tradingManager.getBuildingEmoji(rental.building_type);
        const buildingName = tradingManager.formatBuildingName(rental.building_type);
        const cyclesRemaining = rental.duration_cycles - rental.cycles_used;
        
        html += `
            <div style="margin-bottom: 20px; padding: 15px; border: 2px solid #10b981; border-radius: 8px; background: white;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <div>
                        <strong>Team ${rental.from_team}</strong> ← <strong>Team ${rental.to_team}</strong>
                    </div>
                    <span style="padding: 4px 8px; background: #d1fae5; color: #065f46; border-radius: 4px; font-size: 12px; font-weight: 600;">
                        ACTIVE
                    </span>
                </div>
                
                <div style="margin-bottom: 10px;">
                    <div style="font-size: 16px; font-weight: 600; margin-bottom: 5px;">
                        ${buildingEmoji} ${buildingName}
                    </div>
                    <div>💰 Price: <strong>${rental.rental_price.toFixed(2)}</strong> currency per cycle</div>
                    <div>📊 Cycles Used: <strong>${rental.cycles_used}</strong> / <strong>${rental.duration_cycles}</strong></div>
                    <div>⏱️ Remaining: <strong>${cyclesRemaining}</strong> cycles</div>
                </div>
                
                <div style="margin-top: 10px; padding: 10px; background: #f0fdf4; border-radius: 4px; border-left: 4px solid #10b981;">
                    <strong>Note:</strong> This building is available for production. When you complete production, one cycle will be used.
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function acceptRentalOffer(offerId) {
    if (!confirm('Accept this rental offer? Payment will be made immediately.')) return;
    
    try {
        await tradingManager.acceptRentalOffer(offerId);
        alert('✅ Rental activated successfully!');
        await loadRentalOffers();
        await loadActiveRentals();
    } catch (error) {
        alert('❌ Failed to accept rental offer: ' + error.message);
        console.error('[acceptRentalOffer] Error:', error);
    }
}

async function rejectRentalOffer(offerId) {
    if (!confirm('Reject this rental offer?')) return;
    
    try {
        await tradingManager.rejectRentalOffer(offerId);
        alert('Rental offer rejected');
        await loadRentalOffers();
    } catch (error) {
        alert('❌ Failed to reject rental offer: ' + error.message);
        console.error('[rejectRentalOffer] Error:', error);
    }
}

async function cancelRentalOffer(offerId) {
    if (!confirm('Cancel this rental request?')) return;
    
    try {
        await tradingManager.cancelRentalOffer(offerId);
        alert('Rental request cancelled');
        await loadRentalOffers();
    } catch (error) {
        alert('❌ Failed to cancel rental request: ' + error.message);
        console.error('[cancelRentalOffer] Error:', error);
    }
}

function openRentalCounterModal(offerId) {
    // For now, use a simple prompt-based counter offer
    const offer = tradingManager.rentalOffers.find(o => o.offer_id === offerId);
    if (!offer) return;
    
    const newPrice = prompt(`Counter offer price (original: ${offer.rental_price}):`, offer.rental_price);
    if (newPrice === null) return;
    
    const price = parseFloat(newPrice);
    if (isNaN(price) || price <= 0) {
        alert('Invalid price');
        return;
    }
    
    counterRentalOffer(offerId, price);
}

async function counterRentalOffer(offerId, price, duration = null, message = null) {
    try {
        await tradingManager.counterRentalOffer(offerId, price, duration, message);
        alert('✅ Counter offer sent!');
        await loadRentalOffers();
    } catch (error) {
        alert('❌ Failed to send counter offer: ' + error.message);
        console.error('[counterRentalOffer] Error:', error);
    }
}

async function updateRentalUI() {
    // Called when rental events occur via WebSocket
    if (tradingManager && document.getElementById('building-rental-modal').classList.contains('hidden') === false) {
        await loadRentalOffers();
        await loadActiveRentals();
    }
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

// ==================== MANUAL RESOURCE/BUILDING MANAGEMENT (HOST ONLY) ====================

async function populateManualManagementTeamDropdowns() {
    try {
        const game = await gameAPI.getGame(currentGameCode);
        const players = await gameAPI.getPlayers(currentGameCode);
        
        // Get all unique team numbers from players
        const teamNumbers = [...new Set(
            players
                .filter(p => p.role === 'player' && p.group_number)
                .map(p => p.group_number)
        )].sort((a, b) => a - b);
        
        // Populate both dropdowns
        const resourcesTeamSelect = document.getElementById('give-resources-team');
        const buildingsTeamSelect = document.getElementById('give-buildings-team');
        
        if (resourcesTeamSelect && buildingsTeamSelect) {
            // Clear existing options except the first "Select Team..." option
            resourcesTeamSelect.innerHTML = '<option value="">Select Team...</option>';
            buildingsTeamSelect.innerHTML = '<option value="">Select Team...</option>';
            
            // Add an option for each team
            teamNumbers.forEach(teamNum => {
                const teamData = game.game_state?.teams?.[String(teamNum)];
                const teamName = teamData?.nation_name || `Team ${teamNum}`;
                
                const resourceOption = document.createElement('option');
                resourceOption.value = teamNum;
                resourceOption.textContent = teamName;
                resourcesTeamSelect.appendChild(resourceOption);
                
                const buildingOption = document.createElement('option');
                buildingOption.value = teamNum;
                buildingOption.textContent = teamName;
                buildingsTeamSelect.appendChild(buildingOption);
            });
        }
    } catch (error) {
        console.error('Failed to populate team dropdowns:', error);
    }
}

async function giveResources() {
    // Verify user is host
    if (currentPlayer.role !== 'host' && originalPlayer.role !== 'host') {
        alert('Only the game host can manually give resources!');
        return;
    }
    
    const teamNumber = parseInt(document.getElementById('give-resources-team').value);
    const resourceType = document.getElementById('give-resources-type').value;
    const amount = parseInt(document.getElementById('give-resources-amount').value);
    
    // Validation
    if (!teamNumber) {
        alert('Please select a team!');
        return;
    }
    
    if (!resourceType) {
        alert('Please select a resource type!');
        return;
    }
    
    if (!amount || amount <= 0) {
        alert('Please enter a valid amount (greater than 0)!');
        return;
    }
    
    try {
        // Call backend API to add resources
        const response = await fetch(`${gameAPI.baseUrl}/games/${currentGameCode}/manual-resources`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${gameAPI.token}`
            },
            body: JSON.stringify({
                team_number: teamNumber,
                resource_type: resourceType,
                amount: amount
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to give resources');
        }
        
        const result = await response.json();
        
        // Get actual team name for display
        const game = await gameAPI.getGame(currentGameCode);
        const teamData = game.game_state?.teams?.[String(teamNumber)];
        const teamName = teamData?.nation_name || `Team ${teamNumber}`;
        
        // Show success message
        const resourceName = formatResourceName(resourceType).replace(/^[^\s]+\s/, '');
        alert(`Successfully gave ${amount} ${resourceName} to ${teamName}!`);
        
        // Log event
        addEventLog(`🎁 Host gave ${amount} ${resourceName} to ${teamName}`, 'success');
        
        // Refresh team resources displays
        await loadTeamResourcesOverview();
        await loadHostNationsOverview();
        
        // Notify team members via WebSocket
        gameWS.send({
            type: 'event',
            event_type: 'resources_updated',
            data: {
                team_number: teamNumber,
                resource_type: resourceType,
                amount: amount,
                source: 'host_manual'
            }
        });
        
        // Reset form
        document.getElementById('give-resources-amount').value = '10';
        
    } catch (error) {
        console.error('Error giving resources:', error);
        alert(`Failed to give resources: ${error.message}`);
    }
}

async function giveBuildings() {
    // Verify user is host
    if (currentPlayer.role !== 'host' && originalPlayer.role !== 'host') {
        alert('Only the game host can manually give buildings!');
        return;
    }
    
    const teamNumber = parseInt(document.getElementById('give-buildings-team').value);
    const buildingType = document.getElementById('give-buildings-type').value;
    const quantity = parseInt(document.getElementById('give-buildings-amount').value);
    
    // Validation
    if (!teamNumber) {
        alert('Please select a team!');
        return;
    }
    
    if (!buildingType) {
        alert('Please select a building type!');
        return;
    }
    
    if (!quantity || quantity <= 0) {
        alert('Please enter a valid quantity (greater than 0)!');
        return;
    }
    
    try {
        // Call backend API to add buildings
        const response = await fetch(`${gameAPI.baseUrl}/games/${currentGameCode}/manual-buildings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${gameAPI.token}`
            },
            body: JSON.stringify({
                team_number: teamNumber,
                building_type: buildingType,
                quantity: quantity
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to give buildings');
        }
        
        const result = await response.json();
        
        // Get actual team name for display
        const game = await gameAPI.getGame(currentGameCode);
        const teamData = game.game_state?.teams?.[String(teamNumber)];
        const teamName = teamData?.nation_name || `Team ${teamNumber}`;
        
        // Show success message
        const buildingName = formatBuildingName(buildingType).replace(/^[^\s]+\s/, '');
        alert(`Successfully gave ${quantity} ${buildingName}${quantity > 1 ? 's' : ''} to ${teamName}!`);
        
        // Log event
        addEventLog(`🎁 Host gave ${quantity} ${buildingName}${quantity > 1 ? 's' : ''} to ${teamName}`, 'success');
        
        // Refresh team resources displays
        await loadTeamResourcesOverview();
        await loadHostNationsOverview();
        
        // Notify team members via WebSocket
        gameWS.send({
            type: 'event',
            event_type: 'buildings_updated',
            data: {
                team_number: teamNumber,
                building_type: buildingType,
                quantity: quantity,
                source: 'host_manual'
            }
        });
        
        // Reset form
        document.getElementById('give-buildings-amount').value = '1';
        
    } catch (error) {
        console.error('Error giving buildings:', error);
        alert(`Failed to give buildings: ${error.message}`);
    }
}

function handleGameEvent(data) {
    const { event_type, data: eventData } = data;
    
    console.log(`[WebSocket Event] Received event_type: ${event_type}`, eventData);
    
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
        case 'challenge_request':
            // Use challenge manager to handle request
            if (challengeManager) {
                challengeManager.handleChallengeRequest(eventData);
            }
            
            // Log and UI updates
            console.log(`[challenge_request] Received for player ${eventData.player_name}`);
            addEventLog(`Challenge requested by ${eventData.player_name} (Team ${eventData.team_number}) for ${eventData.building_name}`, 'info');
            
            // Update UI for team members
            if (eventData.team_number === currentPlayer.groupNumber && eventData.player_id !== currentPlayer.id) {
                updateAllBuildingButtons();
            }
            break;
        case 'challenge_assigned':
            // Use challenge manager to handle assignment
            if (challengeManager) {
                challengeManager.handleChallengeAssigned(eventData);
            }
            
            // Player receives their assigned challenge
            if (eventData.player_id === currentPlayer.id) {
                receiveChallengeAssignment(eventData.building_type, eventData.challenge_description);
            }
            
            // Update UI for team members
            if (eventData.player_id !== currentPlayer.id) {
                updateAllBuildingButtons();
            }
            break;
        case 'challenge_completed':
            // Use challenge manager to handle completion
            if (challengeManager) {
                challengeManager.handleChallengeCompleted(eventData);
            }
            
            // Refresh banker view if this is the banker/host
            if (currentPlayer.role === 'banker' || currentPlayer.role === 'host') {
                (async () => {
                    // Refresh player data to get updated bank inventory
                    const players = await gameAPI.getPlayers(currentGameCode);
                    const bankerPlayer = players.find(p => p.role === 'banker');
                    if (bankerPlayer && bankerPlayer.player_state) {
                        playerState = bankerPlayer.player_state;
                        loadHostBankerView();
                        console.log('[challenge_completed] Refreshed banker view, new inventory:', playerState.bank_inventory);
                    }
                })();
            }
            
            // Update UI for team members
            if (eventData.team_number === currentPlayer.groupNumber && eventData.player_id !== currentPlayer.id) {
                updateAllBuildingButtons();
                const buildingName = formatBuildingName(eventData.building_type);
                addEventLog(`${eventData.player_name} completed production at ${buildingName}`, 'info');
            }
            break;
        case 'challenge_dismissed':
            // Use challenge manager to handle dismissal
            if (challengeManager) {
                challengeManager.handleChallengeCancelled(eventData);
            }
            
            // Clear challenge from allActiveChallenges (all possible key formats)
            delete allActiveChallenges[eventData.building_type];
            delete allActiveChallenges[`${eventData.player_id}-${eventData.building_type}`];
            if (eventData.team_number) {
                delete allActiveChallenges[`team${eventData.team_number}-${eventData.building_type}`];
            }
            
            // Update building buttons for all players (lock is cleared for entire team)
            updateAllBuildingButtons();
            
            // Show message to the player whose request was dismissed
            if (eventData.player_id === currentPlayer.id) {
                const requestBtn = document.getElementById(`${eventData.building_type}-request-btn`);
                if (requestBtn) {
                    requestBtn.disabled = false;
                    requestBtn.textContent = '📋 Request Challenge';
                }
                addEventLog('Your challenge request was dismissed', 'warning');
            }
            
            // Update active challenges list
            updateActiveChallengesList();
            break;
        case 'challenge_cancelled':
            // Use challenge manager to handle cancellation
            if (challengeManager) {
                challengeManager.handleChallengeCancelled(eventData);
            }
            
            // Challenge was cancelled by host/banker
            if (eventData.player_id === currentPlayer.id) {
                updateAllBuildingButtons();
                alert('Your challenge was cancelled by the host/banker');
                addEventLog('Challenge cancelled by host/banker', 'error');
            }
            
            // Update active challenges list
            updateActiveChallengesList();
            break;
        case 'challenge_expired':
            // Use challenge manager to handle expiration
            if (challengeManager) {
                challengeManager.handleChallengeCancelled(eventData);  // Expired uses same logic as cancelled
            }
            
            // Challenge expired (10 minutes elapsed)
            if (eventData.player_id === currentPlayer.id) {
                updateAllBuildingButtons();
                alert('Your challenge has expired! Please request a new challenge.');
                addEventLog('Challenge expired - time ran out', 'error');
            }
            
            // Update active challenges list
            updateActiveChallengesList();
            break;
        case 'team_name_changed':
            // Team name has been changed by host
            console.log(`[team_name_changed] Team ${eventData.team_number} renamed to "${eventData.team_name}"`);
            
            // Refresh all displays that show team names
            refreshAllTeamNameDisplays();
            
            addEventLog(`Team ${eventData.team_number} renamed to "${eventData.team_name}"`, 'info');
            break;
        
        // Trading events
        case 'bank_trade_completed':
            if (tradingManager) {
                tradingManager.handleTradeEvent(event_type, eventData);
            }
            addEventLog(`Team ${eventData.team_number} traded ${eventData.amount} ${eventData.resource} with bank`, 'success');
            
            // Refresh resources display
            if (eventData.team_number === (currentPlayer.group_number || teamState.team_number)) {
                loadGameState();
            }
            break;
        
        case 'team_trade_offer_created':
            if (tradingManager) {
                tradingManager.handleTradeEvent(event_type, eventData);
            }
            addEventLog(`Trade offer created: Team ${eventData.from_team} → Team ${eventData.to_team}`, 'info');
            break;
        
        case 'team_trade_offer_countered':
            if (tradingManager) {
                tradingManager.handleTradeEvent(event_type, eventData);
            }
            addEventLog(`Trade offer countered: Team ${eventData.from_team} ↔ Team ${eventData.to_team}`, 'info');
            break;
        
        case 'team_trade_completed':
            if (tradingManager) {
                tradingManager.handleTradeEvent(event_type, eventData);
            }
            addEventLog(`Trade completed between Team ${eventData.from_team} and Team ${eventData.to_team}`, 'success');
            
            // Refresh resources if involved in trade
            const currentTeam = currentPlayer.group_number || teamState.team_number;
            if (currentTeam === eventData.from_team || currentTeam === eventData.to_team) {
                loadGameState();
            }
            break;
        
        case 'team_trade_offer_rejected':
        case 'team_trade_offer_cancelled':
            if (tradingManager) {
                tradingManager.handleTradeEvent(event_type, eventData);
            }
            addEventLog(`Trade offer ${event_type === 'team_trade_offer_rejected' ? 'rejected' : 'cancelled'}`, 'info');
            break;
        
        // Building rental events
        case 'building_rental_offer_created':
            addEventLog(`Rental offer created: Team ${eventData.from_team} → Team ${eventData.to_team} for ${eventData.building_type}`, 'info');
            if (typeof updateRentalUI === 'function') {
                updateRentalUI();
            }
            break;
        
        case 'building_rental_offer_countered':
            addEventLog(`Rental offer countered: Team ${eventData.from_team} ↔ Team ${eventData.to_team}`, 'info');
            if (typeof updateRentalUI === 'function') {
                updateRentalUI();
            }
            break;
        
        case 'building_rental_activated':
            addEventLog(`Building rental activated: Team ${eventData.from_team} renting ${eventData.building_type} from Team ${eventData.to_team}`, 'success');
            const currentTeam = currentPlayer.group_number || teamState.team_number;
            if (currentTeam === eventData.from_team || currentTeam === eventData.to_team) {
                loadGameState();
            }
            if (typeof updateRentalUI === 'function') {
                updateRentalUI();
            }
            break;
        
        case 'building_rental_completed':
            addEventLog(`Building rental completed: ${eventData.building_type}`, 'info');
            if (typeof updateRentalUI === 'function') {
                updateRentalUI();
            }
            break;
        
        case 'building_rental_offer_rejected':
        case 'building_rental_offer_cancelled':
            addEventLog(`Rental offer ${event_type === 'building_rental_offer_rejected' ? 'rejected' : 'cancelled'}`, 'info');
            if (typeof updateRentalUI === 'function') {
                updateRentalUI();
            }
            break;
    }
}

// Refresh all team name displays across the dashboard
async function refreshAllTeamNameDisplays() {
    try {
        // Refresh Nations Overview (shows team names in cards)
        await updateNationsOverview();
        
        // Refresh Team Resources tab
        await loadTeamResourcesOverview();
        
        // Refresh manual management dropdowns
        await populateManualManagementTeamDropdowns();
        
        // Refresh team boxes in Game Controls
        const game = await gameAPI.getGame(currentGameCode);
        const teams = game.game_state?.teams || {};
        
        // Update team name spans in team assignment boxes
        Object.keys(teams).forEach(teamNum => {
            const teamNameSpan = document.getElementById(`team-${teamNum}-name`);
            const teamData = teams[teamNum];
            if (teamNameSpan && teamData?.nation_name) {
                teamNameSpan.textContent = teamData.nation_name;
            }
        });
        
        console.log('[refreshAllTeamNameDisplays] All team name displays refreshed');
    } catch (error) {
        console.error('Error refreshing team name displays:', error);
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

function updateDurationDisplayModal(minutes) {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    
    let displayText = '';
    if (hours > 0) {
        displayText = hours + (hours === 1 ? ' hour' : ' hours');
    }
    if (remainingMinutes > 0) {
        if (displayText) displayText += ' ';
        displayText += remainingMinutes + ' minutes';
    }
    
    document.getElementById('duration-display-modal').textContent = displayText;
}

function applyChallengeDefaults() {
    // Get all challenge input values from the modal
    const newDefaults = {
        'push_ups': parseInt(document.getElementById('challenge-push_ups').value),
        'sit_ups': parseInt(document.getElementById('challenge-sit_ups').value),
        'burpees': parseInt(document.getElementById('challenge-burpees').value),
        'star_jumps': parseInt(document.getElementById('challenge-star_jumps').value),
        'squats': parseInt(document.getElementById('challenge-squats').value),
        'lunges': parseInt(document.getElementById('challenge-lunges').value),
        'plank': parseInt(document.getElementById('challenge-plank').value),
        'jumping_jacks': parseInt(document.getElementById('challenge-jumping_jacks').value)
    };
    
    // Update the global challengeTypes configuration
    Object.keys(newDefaults).forEach(key => {
        if (challengeTypes[key] && !isNaN(newDefaults[key]) && newDefaults[key] > 0) {
            challengeTypes[key].default = newDefaults[key];
        }
    });
    
    // Show success message
    const statusDiv = document.createElement('div');
    statusDiv.style.cssText = 'background: #d4edda; color: #155724; padding: 10px; border-radius: 6px; margin-top: 10px; border: 2px solid #c3e6cb;';
    statusDiv.textContent = '✓ Challenge defaults updated successfully!';
    
    const section = event.target.closest('.setting-section');
    const existingStatus = section.querySelector('.status-message');
    if (existingStatus) existingStatus.remove();
    
    section.appendChild(statusDiv);
    
    setTimeout(() => statusDiv.remove(), 3000);
    
    addEventLog('Challenge defaults updated', 'success');
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
        
        // Update game duration slider
        const durationSlider = document.getElementById('game-duration-modal');
        if (durationSlider && game.game_duration_minutes) {
            durationSlider.value = game.game_duration_minutes;
            updateDurationDisplayModal(game.game_duration_minutes);
        }
        
        // Load challenge defaults from global config
        Object.keys(challengeTypes).forEach(key => {
            const input = document.getElementById(`challenge-${key}`);
            if (input) {
                input.value = challengeTypes[key].default;
            }
        });
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
        console.log('Applying team configuration:', numTeams);
        const response = await gameAPI.setNumTeams(currentGameCode, numTeams);
        console.log('Team configuration response:', response);
        
        const statusSpan = document.getElementById('teams-status-modal');
        if (statusSpan) {
            statusSpan.textContent = `✓ Saved: ${numTeams} teams`;
            statusSpan.style.color = '#4caf50';
        }
        
        addEventLog(`Team configuration updated: ${numTeams} teams`, 'info');
        
        // Reload team boxes
        console.log('Reloading team boxes...');
        await loadGameAndCreateTeamBoxes();
        console.log('Team boxes reloaded successfully');
        
        alert(`Team configuration saved: ${numTeams} teams`);
    } catch (error) {
        console.error('Error setting team configuration:', error);
        console.error('Error details:', {
            message: error.message,
            detail: error.detail,
            stack: error.stack
        });
        const errorMessage = error.message || error.detail || 'Unknown error occurred';
        alert('Failed to save team configuration: ' + errorMessage);
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
    const toggleContainer = document.getElementById('test-mode-toggle-container');
    
    if (!testModeToggle || !toggleContainer) return;
    
    // Only show test mode toggle for hosts
    if (currentPlayer && currentPlayer.role !== 'host') {
        toggleContainer.style.display = 'none';
        return;
    }
    
    // Show toggle for host
    toggleContainer.style.display = 'flex';
    
    // Disable test mode if game is not in waiting status
    const gameNotWaiting = currentGameStatus !== 'waiting';
    
    if (gameNotWaiting) {
        testModeToggle.disabled = true;
        testModeToggle.checked = false;
        toggleTestMode(false);
        
        // Add visual indicator that it's disabled
        toggleContainer.style.opacity = '0.5';
        toggleContainer.title = 'Test mode is disabled once the game has started';
    } else {
        testModeToggle.disabled = false;
        toggleContainer.style.opacity = '1';
        toggleContainer.title = '';
    }
}

// Test Mode Toggle
function toggleTestMode(enabled) {
    console.log('Test mode toggled:', enabled);
    
    // Only allow hosts to enable test mode
    if (enabled && currentPlayer && currentPlayer.role !== 'host') {
        console.warn('Test mode can only be enabled by the host');
        const toggleCheckbox = document.getElementById('test-mode-toggle');
        if (toggleCheckbox) {
            toggleCheckbox.checked = false;
        }
        return;
    }
    
    // Show/hide test mode settings in the settings modal
    const testModeSettings = document.getElementById('test-mode-settings');
    if (testModeSettings) {
        testModeSettings.style.display = enabled ? 'block' : 'none';
    }
    
    // Show/hide role view switcher (only for hosts)
    const roleViewSwitcher = document.getElementById('role-view-switcher');
    if (roleViewSwitcher) {
        // Always show View As dropdown if the actual logged-in player is a host
        const isActualHost = originalPlayer && originalPlayer.role === 'host';
        roleViewSwitcher.style.display = isActualHost ? 'flex' : 'none';
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
            // Restore original player when switching back to host/banker view
            if (originalPlayer) {
                console.log(`[switchRoleView] Restoring original player: ${originalPlayer.name} (ID: ${originalPlayer.id})`);
                currentPlayer = { ...originalPlayer };
                
                // Reconnect WebSocket with original player ID
                if (gameWS) {
                    gameWS.disconnect();
                    gameWS = new GameWebSocket(currentGameCode, currentPlayer.id);
                    
                    gameWS.on('connected', () => {
                        console.log(`[switchRoleView] WebSocket reconnected as original player ${currentPlayer.name}`);
                    });
                    
                    gameWS.on('game_event', (data) => {
                        handleGameEvent(data);
                    });
                }
            }
            
            if (hostDashboard) hostDashboard.classList.remove('hidden');
            document.getElementById('player-view-switcher').style.display = 'none';
            
            // Refresh challenge requests list
            updateChallengeRequestsList();
            
            // Reorder tabs based on role (this also shows/hides Game Controls tab)
            reorderTabsForRole(role);
            
            // If viewing as banker, ensure we're on the Banker View tab
            if (role === 'banker') {
                // Hide ALL tab contents first
                document.querySelectorAll('.host-tab-content').forEach(content => content.classList.remove('active'));
                
                // Show only Banker View tab content
                const bankerTabContent = document.getElementById('host-tab-banker');
                if (bankerTabContent) {
                    bankerTabContent.classList.add('active');
                }
                
                // Update tab button active state
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                const bankerTabBtn = document.getElementById('tab-btn-banker');
                if (bankerTabBtn) {
                    bankerTabBtn.classList.add('active');
                }
                
                // Load banker view
                loadHostBankerView();
            } else {
                // For host role, show Game Controls tab by default
                document.querySelectorAll('.host-tab-content').forEach(content => content.classList.remove('active'));
                const controlsTabContent = document.getElementById('host-tab-controls');
                if (controlsTabContent) {
                    controlsTabContent.classList.add('active');
                }
                
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                const controlsTabBtn = document.getElementById('tab-btn-controls');
                if (controlsTabBtn) {
                    controlsTabBtn.classList.add('active');
                }
            }
            break;
        case 'player':
            if (nationDashboard) nationDashboard.classList.remove('hidden');
            // Show player switcher dropdown when host is viewing as player
            const isActualHost = originalPlayer && originalPlayer.role === 'host';
            if (isActualHost) {
                document.getElementById('player-view-switcher').style.display = 'flex';
                populatePlayerSwitcher();
                // Hide player dashboard content until a player is selected
                hidePlayerDashboardContent();
            } else {
                // Normal player mode - show their dashboard
                showPlayerDashboardContent();
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

// Helper function to hide player dashboard content when no player is selected
function hidePlayerDashboardContent() {
    const nationDashboard = document.getElementById('nation-dashboard');
    if (nationDashboard) {
        // Add a CSS class to hide content or directly hide child elements
        const contentDivs = nationDashboard.querySelectorAll('.card, .dashboard-grid, h2');
        contentDivs.forEach(div => {
            div.style.display = 'none';
        });
        
        // Show a placeholder message
        let placeholder = nationDashboard.querySelector('.no-player-selected-msg');
        if (!placeholder) {
            placeholder = document.createElement('div');
            placeholder.className = 'no-player-selected-msg';
            placeholder.style.cssText = 'padding: 40px; text-align: center; color: #999; font-size: 18px;';
            placeholder.innerHTML = `
                <div style="font-size: 48px; margin-bottom: 20px;">👤</div>
                <p style="font-size: 20px; font-weight: 600; margin-bottom: 10px;">No Player Selected</p>
                <p>Please select a player from the dropdown above to view their dashboard.</p>
            `;
            nationDashboard.appendChild(placeholder);
        } else {
            placeholder.style.display = 'block';
        }
    }
}

// Helper function to show player dashboard content when a player is selected
function showPlayerDashboardContent() {
    const nationDashboard = document.getElementById('nation-dashboard');
    if (nationDashboard) {
        // Show all content
        const contentDivs = nationDashboard.querySelectorAll('.card, .dashboard-grid, h2');
        contentDivs.forEach(div => {
            div.style.display = '';
        });
        
        // Hide placeholder message
        const placeholder = nationDashboard.querySelector('.no-player-selected-msg');
        if (placeholder) {
            placeholder.style.display = 'none';
        }
        
        // Reset all request buttons to default state
        const buildingTypes = ['farm', 'mine', 'electrical_factory', 'medical_factory'];
        buildingTypes.forEach(buildingType => {
            const requestBtn = document.getElementById(`${buildingType}-request-btn`);
            if (requestBtn) {
                requestBtn.disabled = false;
                requestBtn.textContent = '📋 Request Challenge';
                requestBtn.style.display = 'inline-block';
            }
            
            const produceBtn = document.getElementById(`${buildingType}-produce-btn`);
            if (produceBtn) {
                produceBtn.style.display = 'none';
            }
            
            const challengeDisplay = document.getElementById(`${buildingType}-challenge-display`);
            if (challengeDisplay) {
                challengeDisplay.style.display = 'none';
            }
        });
    }
}

async function switchPlayerView(playerId) {
    if (!playerId) {
        console.log('No player selected');
        hidePlayerDashboardContent();
        return;
    }
    
    try {
        const players = await gameAPI.getPlayers(currentGameCode);
        const selectedPlayer = players.find(p => p.id === parseInt(playerId));
        
        if (!selectedPlayer) {
            console.error('Player not found:', playerId);
            hidePlayerDashboardContent();
            return;
        }
        
        // IMPORTANT: Update currentPlayer to impersonate the selected player
        currentPlayer = {
            id: selectedPlayer.id,
            name: selectedPlayer.player_name,
            role: selectedPlayer.role,
            groupNumber: selectedPlayer.group_number
        };
        
        console.log(`[switchPlayerView] Now viewing as: ${currentPlayer.name} (ID: ${currentPlayer.id}, Team: ${currentPlayer.groupNumber})`);
        
        // DON'T clear allActiveChallenges - they should persist across player switches
        // The WebSocket events keep them synchronized
        console.log(`[switchPlayerView] Keeping allActiveChallenges:`, allActiveChallenges);
        
        // DON'T reconnect WebSocket in test mode - keep the original host/banker connection
        // This ensures challenge requests are received even when viewing as a player
        console.log(`[switchPlayerView] Keeping WebSocket connected as original player (${originalPlayer.name})`);
        console.log(`[switchPlayerView] Events will be received and processed based on the original connection`)
        
        // Show the dashboard content AFTER currentPlayer is updated
        showPlayerDashboardContent();
        
        // Update player dashboard with selected player's data
        const playerTitle = document.getElementById('player-title');
        if (playerTitle) {
            playerTitle.textContent = `${selectedPlayer.player_name}'s Dashboard`;
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
        
        // Reload game data to load the selected player's team resources
        await loadGameData();
        
        // Update building buttons
        await updateAllBuildingButtons();
        
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
        
        // Always show View As dropdown for hosts
        const roleViewSwitcher = document.getElementById('role-view-switcher');
        if (roleViewSwitcher) {
            roleViewSwitcher.style.display = 'flex';
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
    const resourcesTab = document.getElementById('tab-btn-resources');
    const challengesTab = document.getElementById('tab-btn-challenges');
    const bankerTab = document.getElementById('tab-btn-banker');
    
    if (!controlsTab || !nationsTab || !resourcesTab || !challengesTab || !bankerTab) return;
    
    // Set visibility for Game Controls based on role
    if (role === 'banker') {
        controlsTab.style.display = 'none';  // Hide Game Controls for banker
    } else {
        controlsTab.style.display = 'inline-block';  // Show Game Controls for host
    }
    
    // Remove all tabs from container
    container.innerHTML = '';
    
    if (role === 'banker') {
        // Banker order: Banker View first, then others (Game Controls hidden but still added)
        container.appendChild(bankerTab);
        container.appendChild(nationsTab);
        container.appendChild(resourcesTab);
        container.appendChild(challengesTab);
        container.appendChild(controlsTab);  // Add but it's hidden
    } else {
        // Host order: Game Controls first, then others
        container.appendChild(controlsTab);
        container.appendChild(nationsTab);
        container.appendChild(resourcesTab);
        container.appendChild(challengesTab);
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
    } else if (tabName === 'resources') {
        loadTeamResourcesOverview();
    } else if (tabName === 'challenges') {
        loadActiveChallengesView();
    } else if (tabName === 'banker') {
        loadHostBankerView();
    }
}

// Load team resources overview
async function loadTeamResourcesOverview() {
    try {
        const game = await gameAPI.getGame(currentGameCode);
        const players = await gameAPI.getPlayers(currentGameCode);
        const teamResourcesDiv = document.getElementById('team-resources-overview');
        
        if (!game || !game.game_state || !game.game_state.teams) {
            teamResourcesDiv.innerHTML = '<p style="color: #666; font-style: italic;">No team data available yet</p>';
            return;
        }
        
        const teams = game.game_state.teams;
        const teamNumbers = Object.keys(teams).map(key => parseInt(key)).sort((a, b) => a - b);
        
        if (teamNumbers.length === 0) {
            teamResourcesDiv.innerHTML = '<p style="color: #666; font-style: italic;">No teams created yet</p>';
            return;
        }
        
        teamResourcesDiv.innerHTML = '';
        
        teamNumbers.forEach(teamNum => {
            const teamKey = String(teamNum);
            const teamData = teams[teamKey];
            // Use custom team name if set, otherwise "Team X"
            const teamName = teamData.nation_name || `Team ${teamNum}`;
            const nationTypeName = teamData.name || '';  // Nation type (e.g., "Nation 1 (Food Producer)")
            
            const card = document.createElement('div');
            card.className = 'team-resource-card';
            
            // Resources section
            let resourcesHTML = '<div class="team-resource-list">';
            if (teamData.resources) {
                Object.entries(teamData.resources).forEach(([resource, amount]) => {
                    resourcesHTML += `
                        <div class="team-resource-item">
                            <span class="team-resource-name">${formatResourceName(resource)}</span>
                            <span class="team-resource-value">${amount}</span>
                        </div>
                    `;
                });
            } else {
                resourcesHTML += '<p style="color: #999; font-style: italic; font-size: 13px;">No resources yet</p>';
            }
            resourcesHTML += '</div>';
            
            // Buildings section
            let buildingsHTML = '<div class="team-resource-list">';
            if (teamData.buildings) {
                Object.entries(teamData.buildings).forEach(([building, count]) => {
                    if (count > 0) {
                        buildingsHTML += `
                            <div class="team-resource-item">
                                <span class="team-resource-name">${formatBuildingName(building)}</span>
                                <span class="team-resource-value">${count}</span>
                            </div>
                        `;
                    }
                });
            } else {
                buildingsHTML += '<p style="color: #999; font-style: italic; font-size: 13px;">No buildings yet</p>';
            }
            buildingsHTML += '</div>';
            
            const hasSchool = (teamData.buildings?.school || 0) > 0;
            
            card.innerHTML = `
                <h4>🏛️ ${teamName} ${hasSchool ? '🏫' : ''}</h4>
                ${nationTypeName ? `<p style="color: #667eea; font-size: 12px; margin: -10px 0 15px 0; font-weight: 600;">${nationTypeName}</p>` : ''}
                <div class="team-resource-section">
                    <h5>📦 Resources</h5>
                    ${resourcesHTML}
                </div>
                <div class="team-resource-section">
                    <h5>🏗️ Buildings</h5>
                    ${buildingsHTML}
                </div>
            `;
            
            teamResourcesDiv.appendChild(card);
        });
    } catch (error) {
        console.error('Failed to load team resources:', error);
        document.getElementById('team-resources-overview').innerHTML = '<p style="color: #f44336;">Error loading team resources</p>';
    }
}

// Load active challenges view
function loadActiveChallengesView() {
    updateActiveChallengesList();
    // Start timer if not already running
    startChallengeTimers();
}

// Update active challenges list display
function updateActiveChallengesList() {
    const listDiv = document.getElementById('active-challenges-list');
    if (!listDiv) return;
    
    // Get assigned challenges from challenge manager (already filtered by role)
    const activeChallengesList = challengeManager ? challengeManager.getAssignedChallenges() : [];
    
    console.log(`[updateActiveChallengesList] Role: ${currentPlayer.role}`);
    console.log(`[updateActiveChallengesList] Filtered challenges:`, activeChallengesList);
    
    if (activeChallengesList.length === 0) {
        listDiv.innerHTML = '<p style="color: #999; font-style: italic;">No active challenges</p>';
        return;
    }
    
    listDiv.innerHTML = '';
    
    activeChallengesList.forEach(challenge => {
        // Use challenge manager to calculate time remaining (handles pause-aware timing)
        const remaining = challengeManager ? challengeManager.getTimeRemaining(challenge) : 0;
        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);
        const isExpiring = remaining < 120000; // Less than 2 minutes
        
        const challengeItem = document.createElement('div');
        challengeItem.className = `active-challenge-item ${isExpiring ? 'expiring' : ''}`;
        challengeItem.dataset.challengeKey = `${challenge.player_id}-${challenge.building_type}`;
        
        challengeItem.innerHTML = `
            <div class="challenge-header">
                <div class="challenge-info">
                    <h4>🏛️ Team ${challenge.team_number}: ${challenge.player_name || 'Unknown Player'}</h4>
                    <p><strong>Building:</strong> ${challenge.building_name}</p>
                    <p><strong>Started:</strong> ${new Date(challenge.start_time).toLocaleTimeString()}</p>
                </div>
                <div class="challenge-timer">
                    <div class="timer-display ${isExpiring ? 'expiring' : ''}" id="timer-${challenge.player_id}-${challenge.building_type}">
                        ${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}
                    </div>
                    <div class="timer-label">TIME REMAINING</div>
                </div>
            </div>
            <div class="challenge-details">
                <p><strong>Challenge:</strong> <span class="challenge-description">${challenge.challenge_description}</span></p>
                <p><strong>Type:</strong> ${challenge.has_school ? 'Individual (has school 🏫)' : 'Team-wide (no school)'}</p>
            </div>
            <div class="challenge-actions">
                <button class="btn btn-success" onclick="completeChallengeAndGrantResources('${challenge.player_id}', '${challenge.building_type}', ${challenge.team_number})" style="margin-right: 10px;">
                    ✅ Complete Challenge
                </button>
                <button class="btn btn-danger" onclick="cancelActiveChallenge('${challenge.player_id}', '${challenge.building_type}')">
                    ❌ Cancel Challenge
                </button>
            </div>
        `;
        
        listDiv.appendChild(challengeItem);
        
        // Auto-expire if time is up
        if (remaining === 0) {
            setTimeout(() => expireChallenge(challenge.player_id, challenge.building_type), 100);
        }
    });
}

// Start challenge timers
function startChallengeTimers() {
    // Note: The challenge manager now handles timer updates internally with its own interval.
    // This function is kept for backward compatibility but is no longer needed.
    // The challenge manager's timer calls the onChallengesUpdated callback,
    // which triggers updateActiveChallengesList() to refresh the UI.
    console.log('[startChallengeTimers] Challenge manager handles timers automatically');
}

// Complete challenge and grant resources (host/banker only)
async function completeChallengeAndGrantResources(playerId, buildingType, teamNumber) {
    console.log('[completeChallengeAndGrantResources] Called for player:', playerId, 'building:', buildingType, 'team:', teamNumber);
    console.log('[completeChallengeAndGrantResources] playerId type:', typeof playerId);
    
    // Convert playerId to number if it's a string
    const playerIdNum = typeof playerId === 'string' ? parseInt(playerId) : playerId;
    console.log('[completeChallengeAndGrantResources] playerIdNum:', playerIdNum);
    
    // Find challenge - check challenge manager first
    let challenge = null;
    let challengeDbId = null;
    
    if (challengeManager) {
        const assignedChallenges = challengeManager.getAssignedChallenges();
        console.log('[completeChallengeAndGrantResources] Assigned challenges:', assignedChallenges);
        challenge = assignedChallenges.find(
            ch => ch.player_id === playerIdNum && ch.building_type === buildingType
        );
        if (challenge) {
            challengeDbId = challenge.db_id;
            console.log('[completeChallengeAndGrantResources] Found in challenge manager, db_id:', challengeDbId);
        }
    }
    
    // Fall back to legacy object
    if (!challenge) {
        const challengeKey = `team${teamNumber}-${buildingType}`;
        console.log('[completeChallengeAndGrantResources] Trying legacy key:', challengeKey);
        challenge = allActiveChallenges[challengeKey];
        if (challenge) {
            challengeDbId = challenge.db_id;
            console.log('[completeChallengeAndGrantResources] Found in allActiveChallenges');
        }
    }
    
    if (!challenge) {
        console.error('[completeChallengeAndGrantResources] Challenge not found!');
        console.error('[completeChallengeAndGrantResources] allActiveChallenges:', allActiveChallenges);
        alert('Challenge not found');
        return;
    }
    
    console.log('[completeChallengeAndGrantResources] Challenge found:', challenge);
    
    try {
        // Get production grant info
        const productionInfo = PRODUCTION_GRANTS[buildingType];
        if (!productionInfo) {
            alert('Invalid building type for production');
            return;
        }
        
        // Get team's building count
        const game = await gameAPI.getGame(currentGameCode);
        const teamKey = String(teamNumber);
        const teamData = game.game_state?.teams?.[teamKey];
        
        if (!teamData) {
            alert('Team data not found');
            return;
        }
        
        const buildingCount = teamData.buildings?.[buildingType] || 0;
        if (buildingCount === 0) {
            alert('Team has no buildings of this type!');
            return;
        }
        
        // Calculate total resources to grant
        const baseAmount = productionInfo.amount;
        const totalAmount = Math.floor(baseAmount * buildingCount * currentDifficultyModifier);
        const resourceType = productionInfo.resource;
        
        // Confirm with host/banker
        const resourceName = formatResourceName(resourceType).replace(/^[^\s]+\s/, '');
        const confirmMsg = `Complete challenge for ${challenge.player_name}?\n\n` +
                          `Building: ${formatBuildingName(buildingType)}\n` +
                          `Building Count: ${buildingCount}\n` +
                          `Base Grant: ${baseAmount} per building\n` +
                          `Difficulty Modifier: ${currentDifficultyModifier}x\n` +
                          `Total Grant: ${totalAmount} ${resourceName}\n\n` +
                          `This will credit Team ${teamNumber} and remove the challenge.`;
        
        if (!confirm(confirmMsg)) {
            return;
        }
        
        // Grant resources from bank via new endpoint
        const response = await fetch(`${gameAPI.baseUrl}/games/${currentGameCode}/challenges/${challengeDbId}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${gameAPI.token}`
            },
            body: JSON.stringify({
                team_number: teamNumber,
                resource_type: resourceType,
                amount: totalAmount
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            alert(`❌ Cannot complete challenge!\n\n${error.detail || 'Failed to grant resources'}`);
            return;
        }
        
        const result = await response.json();
        console.log('[completeChallengeAndGrantResources] Bank transfer result:', result);
        
        // Complete challenge via challenge manager
        if (challengeManager && challengeDbId) {
            try {
                await challengeManager.completeChallenge(challengeDbId);
                console.log('[completeChallengeAndGrantResources] ✅ Challenge completed via manager');
            } catch (error) {
                console.error('[completeChallengeAndGrantResources] ❌ Failed to complete via manager:', error);
            }
        }
        
        // Remove from active challenges (legacy)
        const challengeKey = `${playerId}-${buildingType}`;
        delete allActiveChallenges[challengeKey];
        
        // Notify via WebSocket
        gameWS.send({
            type: 'event',
            event_type: 'challenge_completed',
            data: {
                player_id: playerId,
                building_type: buildingType,
                team_number: teamNumber,
                resources_granted: {
                    resource_type: resourceType,
                    amount: totalAmount
                }
            }
        });
        
        // Update displays
        updateActiveChallengesList();
        await loadTeamResourcesOverview();
        await loadHostNationsOverview();
        
        addEventLog(`✅ Challenge completed! Team ${teamNumber} received ${totalAmount} ${resourceName}`, 'success');
        
    } catch (error) {
        console.error('Error completing challenge:', error);
        alert(`Failed to complete challenge: ${error.message}`);
    }
}

// Cancel an active challenge (host/banker only)
async function cancelActiveChallenge(playerId, buildingType) {
    if (!confirm('Are you sure you want to cancel this challenge?')) {
        return;
    }
    
    console.log('[cancelActiveChallenge] Called for player:', playerId, 'building:', buildingType);
    
    // Find challenge - check challenge manager first
    let challenge = null;
    let challengeDbId = null;
    
    if (challengeManager) {
        const assignedChallenges = challengeManager.getAssignedChallenges();
        challenge = assignedChallenges.find(
            ch => ch.player_id === playerId && ch.building_type === buildingType
        );
        if (challenge) {
            challengeDbId = challenge.db_id;
            console.log('[cancelActiveChallenge] Found in challenge manager, db_id:', challengeDbId);
        }
    }
    
    // Fall back to legacy object
    if (!challenge) {
        const challengeKey = `${playerId}-${buildingType}`;
        challenge = allActiveChallenges[challengeKey];
        if (challenge) {
            challengeDbId = challenge.db_id;
            console.log('[cancelActiveChallenge] Found in allActiveChallenges');
        }
    }
    
    if (!challenge) {
        console.error('[cancelActiveChallenge] Challenge not found');
        return;
    }
    
    // Cancel via challenge manager
    if (challengeManager && challengeDbId) {
        try {
            await challengeManager.cancelChallenge(challengeDbId);
            console.log('[cancelActiveChallenge] ✅ Challenge cancelled via manager');
        } catch (error) {
            console.error('[cancelActiveChallenge] ❌ Failed to cancel via manager:', error);
        }
    }
    
    // Remove from active challenges (legacy)
    const challengeKey = `${playerId}-${buildingType}`;
    delete allActiveChallenges[challengeKey];
    
    // Notify player via WebSocket
    gameWS.send({
        type: 'event',
        event_type: 'challenge_cancelled',
        data: {
            player_id: playerId,
            building_type: buildingType,
            team_number: challenge.team_number
        }
    });
    
    // Update display
    updateActiveChallengesList();
    addEventLog(`Challenge cancelled for ${challenge.player_name} at ${challenge.building_name}`, 'warning');
}

// Expire a challenge when time runs out
function expireChallenge(playerId, buildingType) {
    const challengeKey = `${playerId}-${buildingType}`;
    const challenge = allActiveChallenges[challengeKey];
    
    if (!challenge) return;
    
    // Remove from active challenges
    delete allActiveChallenges[challengeKey];
    
    // Notify player via WebSocket
    gameWS.send({
        type: 'event',
        event_type: 'challenge_expired',
        data: {
            player_id: playerId,
            building_type: buildingType,
            team_number: challenge.team_number
        }
    });
    
    // Update display
    updateActiveChallengesList();
    addEventLog(`Challenge expired for ${challenge.player_name} at ${challenge.building_name}`, 'error');
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
        const game = await gameAPI.getGame(currentGameCode);
        const teamsData = {};
        const unassignedPlayers = [];
        
        // Build dynamic nation name mapping from game state
        // This automatically adapts to however many nation types are configured
        const nationNameMap = {};
        if (game.game_state?.teams) {
            Object.entries(game.game_state.teams).forEach(([teamNum, teamData]) => {
                if (teamData.name) {
                    nationNameMap[teamNum] = teamData.name;
                }
            });
        }
        
        // Fallback function if name not found in game state
        const getNationName = (teamNumber) => {
            const teamKey = String(teamNumber);
            if (nationNameMap[teamKey]) {
                return nationNameMap[teamKey];
            }
            // Fallback: just show team number
            return `Team ${teamNumber}`;
        };
        
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
            
            // Get team state from game.game_state.teams (stored as string keys in backend)
            const teamState = game.game_state?.teams?.[String(team.teamNumber)];
            const nationName = getNationName(team.teamNumber);
            
            let resourcesHTML = '';
            let buildingsHTML = '';
            
            if (teamState) {
                // Display resources
                const resources = teamState.resources || {};
                resourcesHTML = `
                    <div class="nation-section">
                        <strong>📦 Resources:</strong>
                        <div class="nation-stats">
                            <div class="nation-stat">💰 Currency: ${resources.currency || 0}</div>
                            <div class="nation-stat">🌾 Food: ${resources.food || 0}</div>
                            <div class="nation-stat">⚙️ Raw Materials: ${resources.raw_materials || 0}</div>
                            <div class="nation-stat">⚡ Electrical Goods: ${resources.electrical_goods || 0}</div>
                            <div class="nation-stat">� Medical Goods: ${resources.medical_goods || 0}</div>
                        </div>
                    </div>
                `;
                
                // Display buildings
                const buildings = teamState.buildings || {};
                const buildingsList = [];
                if (buildings.farm > 0) buildingsList.push(`🌾 Farms: ${buildings.farm}`);
                if (buildings.mine > 0) buildingsList.push(`⛏️ Mines: ${buildings.mine}`);
                if (buildings.electrical_factory > 0) buildingsList.push(`⚡ Electrical Factories: ${buildings.electrical_factory}`);
                if (buildings.medical_factory > 0) buildingsList.push(`🏥 Medical Factories: ${buildings.medical_factory}`);
                
                if (buildingsList.length > 0) {
                    buildingsHTML = `
                        <div class="nation-section">
                            <strong>🏗️ Buildings:</strong>
                            <div class="nation-stats">
                                ${buildingsList.map(b => `<div class="nation-stat">${b}</div>`).join('')}
                            </div>
                        </div>
                    `;
                } else {
                    buildingsHTML = `
                        <div class="nation-section">
                            <strong>🏗️ Buildings:</strong>
                            <div class="nation-stats"><div class="nation-stat" style="color: #999;">No buildings yet</div></div>
                        </div>
                    `;
                }
            } else {
                resourcesHTML = '<div class="nation-section" style="color: #999; font-style: italic;">Game not started - resources will appear once game begins</div>';
            }
            
            teamCard.innerHTML = `
                <div class="nation-header">
                    <h3>🌍 Team ${team.teamNumber}</h3>
                    <span class="nation-type">${nationName}</span>
                </div>
                <div class="nation-members">
                    <strong>👥 Team Members (${team.members.length}):</strong>
                    ${team.members.map(m => `<div class="member-badge">${m.player_name}</div>`).join('')}
                </div>
                ${resourcesHTML}
                ${buildingsHTML}
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
