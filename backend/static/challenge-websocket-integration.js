/**
 * Challenge WebSocket Integration - Frontend Example
 * 
 * This module demonstrates how to integrate real-time challenge updates
 * into your React/Vue/vanilla JS frontend.
 */

/**
 * Get API base URL (auto-detect production vs development)
 */
function getApiBaseUrl() {
  const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  return isLocalhost ? 'http://localhost:8000' : window.location.origin;
}

/**
 * Get WebSocket base URL (auto-detect production vs development)
 */
function getWsBaseUrl() {
  const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  if (isLocalhost) {
    return 'ws://localhost:8000';
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}`;
}

class ChallengeWebSocketClient {
  constructor(gameCode, playerId) {
    this.gameCode = gameCode;
    this.playerId = playerId;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    
    // Callback handlers for different event types
    this.handlers = {
      challenge_requested: [],
      challenge_assigned: [],
      challenge_completed: [],
      challenge_cancelled: [],
      challenge_expired: [],
    };
  }

  /**
   * Connect to the WebSocket server
   */
  connect() {
    const wsUrl = `${getWsBaseUrl()}/ws/${this.gameCode}/${this.playerId}`;
    
    // console.log(`[ChallengeWS] Connecting to ${wsUrl}`);
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      // console.log('[ChallengeWS] Connected');
      this.reconnectAttempts = 0;
    };
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
    
    this.ws.onerror = (error) => {
      console.error('[ChallengeWS] Error:', error);
    };
    
    this.ws.onclose = () => {
      // console.log('[ChallengeWS] Disconnected');
      this.attemptReconnect();
    };
  }

  /**
   * Handle incoming WebSocket messages
   */
  handleMessage(data) {
    // console.log('[ChallengeWS] Received:', data);
    
    const { type, challenge } = data;
    
    // Route message to registered handlers
    if (this.handlers[type]) {
      this.handlers[type].forEach(handler => handler(challenge));
    }
  }

  /**
   * Register a callback for a specific event type
   * 
   * @param {string} eventType - One of: challenge_requested, challenge_assigned, challenge_completed, challenge_cancelled, challenge_expired
   * @param {function} callback - Function to call when event occurs
   */
  on(eventType, callback) {
    if (!this.handlers[eventType]) {
      console.warn(`[ChallengeWS] Unknown event type: ${eventType}`);
      return;
    }
    
    this.handlers[eventType].push(callback);
  }

  /**
   * Attempt to reconnect after disconnect
   */
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[ChallengeWS] Max reconnect attempts reached');
      return;
    }
    
    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
    
    // console.log(`[ChallengeWS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    setTimeout(() => this.connect(), delay);
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}


// ============================================================================
// React Hook Example
// ============================================================================

/**
 * React Hook for challenge WebSocket integration
 * 
 * Usage:
 * ```jsx
 * function PlayerDashboard({ gameCode, playerId }) {
 *   const [challenges, setChallenges] = useState([]);
 *   
 *   useChallengeWebSocket(gameCode, playerId, {
 *     onChallengeRequested: (challenge) => {
 *       // console.log('New challenge requested:', challenge);
 *       // Host/Banker sees this in their pending challenges list
 *     },
 *     onChallengeAssigned: (challenge) => {
 *       // console.log('Challenge assigned:', challenge);
 *       // Player sees this - move to active challenges tab
 *       setChallenges(prev => [...prev, challenge]);
 *     },
 *     onChallengeCompleted: (challenge) => {
 *       // console.log('Challenge completed:', challenge);
 *       // Remove from active challenges
 *       setChallenges(prev => prev.filter(c => c.id !== challenge.id));
 *     }
 *   });
 *   
 *   return <div>Active Challenges: {challenges.length}</div>;
 * }
 * ```
 */
export function useChallengeWebSocket(gameCode, playerId, callbacks = {}) {
  const wsClientRef = React.useRef(null);

  React.useEffect(() => {
    // Create WebSocket client
    const client = new ChallengeWebSocketClient(gameCode, playerId);
    wsClientRef.current = client;

    // Register callbacks
    if (callbacks.onChallengeRequested) {
      client.on('challenge_requested', callbacks.onChallengeRequested);
    }
    if (callbacks.onChallengeAssigned) {
      client.on('challenge_assigned', callbacks.onChallengeAssigned);
    }
    if (callbacks.onChallengeCompleted) {
      client.on('challenge_completed', callbacks.onChallengeCompleted);
    }
    if (callbacks.onChallengeCancelled) {
      client.on('challenge_cancelled', callbacks.onChallengeCancelled);
    }
    if (callbacks.onChallengeExpired) {
      client.on('challenge_expired', callbacks.onChallengeExpired);
    }

    // Connect
    client.connect();

    // Cleanup on unmount
    return () => {
      client.disconnect();
    };
  }, [gameCode, playerId]);

  return wsClientRef.current;
}


// ============================================================================
// Vanilla JS Example
// ============================================================================

/**
 * Example: Two-user challenge workflow
 * 
 * Scenario:
 * 1. Player A requests a challenge for their farm
 * 2. Host/Banker (Player B) sees the request in real-time
 * 3. Host/Banker assigns "20 Push-ups"
 * 4. Player A sees the assigned challenge in real-time
 * 5. Player A completes it
 * 6. Both users see the completion
 */

// Player A (requesting challenge)
const playerA = new ChallengeWebSocketClient('ABC123', 1);

playerA.on('challenge_assigned', (challenge) => {
  // console.log('[Player A] My challenge is ready!', challenge);
  // Show challenge in UI
  showActiveChallenge(challenge);
  // Start timer countdown
  startChallengeTimer(challenge.time_remaining_seconds);
});

playerA.on('challenge_completed', (challenge) => {
  // console.log('[Player A] Challenge completed!', challenge);
  // Remove from active challenges
  removeActiveChallenge(challenge.id);
  // Show success message
  showSuccessMessage(`${challenge.building_name} is now unlocked!`);
});

playerA.connect();


// Host/Banker (assigning challenges)
const hostBanker = new ChallengeWebSocketClient('ABC123', 2);

hostBanker.on('challenge_requested', (challenge) => {
  // console.log('[Host] New challenge request:', challenge);
  // Add to pending challenges list
  addToPendingChallenges(challenge);
  // Show notification
  showNotification(`${challenge.player_name} needs a challenge!`);
});

hostBanker.on('challenge_assigned', (challenge) => {
  // console.log('[Host] Challenge assigned:', challenge);
  // Move from pending to active
  movePendingToActive(challenge);
});

hostBanker.on('challenge_completed', (challenge) => {
  // console.log('[Host] Challenge completed by player:', challenge);
  // Remove from active challenges
  removeFromActiveChallenges(challenge.id);
});

hostBanker.connect();


// ============================================================================
// UI Update Functions (example implementations)
// ============================================================================

function showActiveChallenge(challenge) {
  // Update React state or DOM
  const activeChallengesEl = document.getElementById('active-challenges');
  const challengeEl = document.createElement('div');
  challengeEl.id = `challenge-${challenge.id}`;
  challengeEl.innerHTML = `
    <div class="challenge-card">
      <h3>${challenge.challenge_description}</h3>
      <p>Building: ${challenge.building_name}</p>
      <p>Target: ${challenge.target_number}</p>
      <div class="timer" id="timer-${challenge.id}">
        Time remaining: ${challenge.time_remaining_seconds}s
      </div>
      <button onclick="completeChallenge(${challenge.id})">
        Mark Complete
      </button>
    </div>
  `;
  activeChallengesEl.appendChild(challengeEl);
}

function addToPendingChallenges(challenge) {
  // Host/Banker UI update
  const pendingEl = document.getElementById('pending-challenges');
  const challengeEl = document.createElement('div');
  challengeEl.id = `pending-${challenge.id}`;
  challengeEl.innerHTML = `
    <div class="pending-challenge">
      <p>${challenge.player_name} - ${challenge.building_name}</p>
      <p>Team ${challenge.team_number}</p>
      <button onclick="assignChallenge(${challenge.id})">
        Assign Challenge
      </button>
    </div>
  `;
  pendingEl.appendChild(challengeEl);
}

function movePendingToActive(challenge) {
  // Remove from pending
  const pendingEl = document.getElementById(`pending-${challenge.id}`);
  if (pendingEl) pendingEl.remove();
  
  // Add to active (for host view)
  const activeEl = document.getElementById('host-active-challenges');
  const challengeEl = document.createElement('div');
  challengeEl.id = `active-${challenge.id}`;
  challengeEl.innerHTML = `
    <div class="active-challenge">
      <p>${challenge.player_name} - ${challenge.challenge_description}</p>
      <p>Time remaining: <span id="timer-${challenge.id}">${challenge.time_remaining_seconds}s</span></p>
      <button onclick="completeChallenge(${challenge.id})">Complete</button>
      <button onclick="cancelChallenge(${challenge.id})">Cancel</button>
    </div>
  `;
  activeEl.appendChild(challengeEl);
}

function removeActiveChallenge(challengeId) {
  const el = document.getElementById(`challenge-${challengeId}`);
  if (el) el.remove();
}

function removeFromActiveChallenges(challengeId) {
  const el = document.getElementById(`active-${challengeId}`);
  if (el) el.remove();
}

function showNotification(message) {
  // Show toast notification
  // console.log('Notification:', message);
}

function showSuccessMessage(message) {
  // Show success modal/toast
  // console.log('Success:', message);
}

function startChallengeTimer(seconds) {
  // Start countdown timer
  // console.log('Starting timer:', seconds);
}


// ============================================================================
// API Integration Functions
// ============================================================================

async function assignChallenge(challengeId) {
  const gameCode = 'ABC123';
  
  // Show modal to select challenge type
  const challengeType = await selectChallengeType();
  
  const response = await fetch(
    `${getApiBaseUrl()}/api/v2/challenges/${gameCode}/${challengeId}/assign`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        challenge_type: challengeType.type,
        challenge_description: challengeType.description,
        target_number: challengeType.target
      })
    }
  );
  
  if (response.ok) {
    // WebSocket will handle UI update automatically
    // console.log('Challenge assigned successfully');
  } else {
    console.error('Failed to assign challenge');
  }
}

async function completeChallenge(challengeId) {
  const gameCode = 'ABC123';
  
  const response = await fetch(
    `${getApiBaseUrl()}/api/v2/challenges/${gameCode}/${challengeId}/complete`,
    { method: 'POST' }
  );
  
  if (response.ok) {
    // WebSocket will handle UI update automatically
    // console.log('Challenge completed successfully');
  } else {
    console.error('Failed to complete challenge');
  }
}

async function cancelChallenge(challengeId) {
  const gameCode = 'ABC123';
  
  const response = await fetch(
    `${getApiBaseUrl()}/api/v2/challenges/${gameCode}/${challengeId}/cancel`,
    { method: 'POST' }
  );
  
  if (response.ok) {
    // WebSocket will handle UI update automatically
    // console.log('Challenge cancelled successfully');
  } else {
    console.error('Failed to cancel challenge');
  }
}

async function selectChallengeType() {
  // Modal UI to select challenge type
  return {
    type: 'push_ups',
    description: '20 Push-ups',
    target: 20
  };
}
