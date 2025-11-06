# Challenge Management System

Complete rebuild of the challenge system with multi-user support, pause-aware timing, and comprehensive testing.

## Architecture

### Backend Components

1. **`challenge_manager.py`** - Core business logic
   - Single source of truth for challenge state
   - Handles all challenge lifecycle operations
   - Pause-aware timing calculations
   - Database operations

2. **`challenge_api.py`** - REST API endpoints (v2)
   - Clean, RESTful API design
   - Uses ChallengeManager service
   - Proper error handling

3. **`test_challenge_manager.py`** - Backend tests
   - Comprehensive test coverage
   - Tests all challenge operations
   - Tests pause-aware timing

### Frontend Components

1. **`challenge-manager.js`** - Frontend state manager
   - Single source of truth for client-side state
   - WebSocket synchronization
   - Multi-user support (host/banker)
   - Automatic expiry checking

2. **`test-challenge-manager.test.js`** - Frontend tests
   - Jest-based testing
   - Mocked dependencies
   - Tests all state management logic

## Key Features

### 1. Multi-User Support

Both host and banker can view and manage all challenges. The system properly synchronizes state across all clients using WebSocket events and database as the source of truth.

### 2. Pause-Aware Timing

Challenges are valid for exactly 10 minutes of *active gameplay*. When the game is paused:
- Challenge timers freeze (frontend display)
- On resume, all `assigned_at` timestamps are adjusted by the pause duration
- This extends the deadline so players get full 10 minutes

**Example:**
```
Challenge assigned: 10:00 AM
Game paused: 10:03 AM (3 minutes elapsed)
Game resumed: 10:15 AM (12 minutes pause)
New deadline: 10:22 AM (original 10:10 + 12 min pause)
```

### 3. Database as Source of Truth

All challenge state is stored in the database. The frontend loads state from the server on:
- Initial page load
- After game resume
- When receiving unknown challenge via WebSocket
- On manual refresh

This prevents desync issues between multiple hosts/bankers.

## Usage

### Backend Setup

1. **Install dependencies:**
```bash
cd backend
pip install -r backend/requirements.txt
```

2. **Run tests:**
```bash
pytest test_challenge_manager.py -v
```

3. **Import new API routes** (in `main.py`):
```python
from challenge_api import router as challenge_router_v2

app.include_router(challenge_router_v2)
```

### Frontend Setup

1. **Include challenge-manager.js:**
```html
<script src="challenge-manager.js"></script>
```

2. **Initialize in dashboard.js:**
```javascript
// Global variable
let challengeManager = null;

// After game starts
async function initializeChallengeManager() {
    challengeManager = new ChallengeManager(
        currentGameCode,
        currentPlayer,
        gameAPI,
        gameWS
    );
    
    await challengeManager.initialize();
    
    // Register update callback
    challengeManager.onChallengesUpdated((challenges) => {
        updateActiveChallengesList();
        updateChallengeRequestsList();
    });
}

// Update game status
function pauseGame() {
    challengeManager.setGameStatus('paused');
    // ... rest of pause logic
}

function resumeGame() {
    const pauseDuration = Date.now() - lastPauseTime;
    await challengeManager.adjustForPause(pauseDuration);
    challengeManager.setGameStatus('in_progress');
    // ... rest of resume logic
}

// Use manager for all challenge operations
async function requestChallenge() {
    await challengeManager.requestChallenge(
        playerId, buildingType, buildingName, teamNumber, hasSchool
    );
}

async function assignChallenge(challengeId) {
    await challengeManager.assignChallenge(
        challengeId, challengeType, description, targetNumber
    );
}

async function completeChallenge(challengeId) {
    await challengeManager.completeChallenge(challengeId);
}
```

3. **Connect WebSocket events:**
```javascript
// In WebSocket message handler
switch (event_type) {
    case 'challenge_request':
        challengeManager.handleChallengeRequest(eventData);
        break;
    case 'challenge_assigned':
        challengeManager.handleChallengeAssigned(eventData);
        break;
    case 'challenge_completed':
        challengeManager.handleChallengeCompleted(eventData);
        break;
    case 'challenge_cancelled':
        challengeManager.handleChallengeCancelled(eventData);
        break;
}
```

4. **Update UI rendering:**
```javascript
function updateActiveChallengesList() {
    const challenges = challengeManager.getAssignedChallenges();
    
    listDiv.innerHTML = '';
    
    challenges.forEach(challenge => {
        const remaining = challengeManager.getTimeRemaining(challenge);
        const minutes = Math.floor(remaining / 60000);
        const seconds = Math.floor((remaining % 60000) / 1000);
        
        // Render challenge with timer
        // ...
    });
}

function updateChallengeRequestsList() {
    const requests = challengeManager.getRequestedChallenges();
    
    // Render pending requests
    // ...
}
```

## API Reference

### Backend Endpoints (v2)

#### POST `/api/v2/challenges/{game_code}/request`
Create a new challenge request.

**Request Body:**
```json
{
    "player_id": 1,
    "building_type": "farm",
    "building_name": "🌾 Farm",
    "team_number": 1,
    "has_school": true
}
```

#### POST `/api/v2/challenges/{game_code}/{challenge_id}/assign`
Assign a challenge to a player.

**Request Body:**
```json
{
    "challenge_type": "push_ups",
    "challenge_description": "20 Push-ups",
    "target_number": 20
}
```

#### POST `/api/v2/challenges/{game_code}/{challenge_id}/complete`
Mark challenge as completed.

#### POST `/api/v2/challenges/{game_code}/{challenge_id}/cancel`
Cancel a challenge.

#### POST `/api/v2/challenges/{game_code}/adjust-for-pause`
Adjust all active challenges for pause duration.

**Request Body:**
```json
{
    "pause_duration_ms": 120000
}
```

#### GET `/api/v2/challenges/{game_code}/active`
Get all active challenges.

**Query Params:**
- `include_time_remaining` (boolean) - Include calculated time remaining

### Frontend ChallengeManager API

#### Constructor
```javascript
new ChallengeManager(gameCode, currentPlayer, gameAPI, gameWS)
```

#### Methods

**`async initialize()`**
Load initial state from server and start timer interval.

**`async loadFromServer()`**
Reload all challenges from server.

**`async requestChallenge(playerId, buildingType, buildingName, teamNumber, hasSchool)`**
Request a new challenge.

**`async assignChallenge(challengeId, challengeType, description, targetNumber)`**
Assign a challenge.

**`async completeChallenge(challengeId)`**
Complete a challenge.

**`async cancelChallenge(challengeId)`**
Cancel a challenge.

**`async adjustForPause(pauseDurationMs)`**
Adjust all challenge times for pause.

**`getChallengesForUser()`**
Get challenges filtered by user role.

**`getAssignedChallenges()`**
Get only assigned challenges.

**`getRequestedChallenges()`**
Get only requested challenges (host/banker only).

**`getTimeRemaining(challenge)`**
Calculate time remaining for a challenge.

**`setGameStatus(status, pauseTime)`**
Update game status ('waiting', 'in_progress', 'paused', 'completed').

**`onChallengesUpdated(callback)`**
Register callback for state updates.

**`destroy()`**
Clean up resources.

## Testing

### Backend Tests

Run all tests:
```bash
cd backend
pytest test_challenge_manager.py -v
```

Run specific test class:
```bash
pytest test_challenge_manager.py::TestPauseAwareTiming -v
```

Run with coverage:
```bash
pytest test_challenge_manager.py --cov=challenge_manager --cov-report=html
```

### Frontend Tests

Install dependencies:
```bash
npm install --save-dev jest
```

Run tests:
```bash
npm test frontend/test-challenge-manager.test.js
```

Run with coverage:
```bash
npm test -- --coverage
```

## Migration from Old System

### Step 1: Deploy Backend Changes

1. Add `challenge_manager.py` and `challenge_api.py` to backend
2. Update `main.py` to include new API routes
3. Run tests to verify
4. Deploy backend

### Step 2: Update Frontend

1. Add `challenge-manager.js` to frontend
2. Update `dashboard.js` to use ChallengeManager
3. Replace direct API calls with manager methods
4. Update WebSocket handlers to call manager methods
5. Test thoroughly in staging

### Step 3: Clean Up

1. Remove old challenge management code from `dashboard.js`
2. Remove old unused API endpoints (optional - keep for backward compatibility)
3. Update documentation

## Troubleshooting

### Challenges not appearing for banker/host

**Symptom:** Challenge shows for one banker but not the other.

**Solution:** Ensure `loadFromServer()` is called after WebSocket events that might introduce challenges the local client doesn't know about.

### Timer doesn't pause

**Symptom:** Challenge timer continues during pause.

**Solution:** Ensure `setGameStatus('paused', pauseTime)` is called when game pauses, and `getTimeRemaining()` uses the frozen time.

### Challenges expire during pause

**Symptom:** Challenges marked as expired even though game was paused.

**Solution:** The expiry check in `_checkExpiry()` only runs when `gameStatus === 'in_progress'`. Verify this is set correctly.

### Desync between clients

**Symptom:** Different clients show different challenge states.

**Solution:** Call `loadFromServer()` more frequently, especially after state-changing WebSocket events. The database is the source of truth.

## Performance Considerations

- **Timer Interval:** Runs every 1 second. Consider increasing interval (e.g., 2-5 seconds) if performance is an issue.
- **Database Queries:** Challenge queries are lightweight. No significant load concerns.
- **WebSocket Traffic:** Minimal - only sends events on state changes, not periodic updates.
- **Memory:** Challenge manager holds challenges in a Map. Even with 100 concurrent challenges, memory usage is negligible.

## Future Enhancements

1. **Challenge History:** Add endpoint to retrieve completed/cancelled challenges
2. **Analytics:** Track challenge completion rates, average times
3. **Notifications:** Push notifications when challenge is assigned/expires
4. **Configurable Duration:** Allow different challenge durations per building type
5. **Challenge Templates:** Pre-defined challenge types with recommended targets
6. **Leaderboard:** Track which teams complete challenges fastest

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review test cases for usage examples
3. Check console logs for detailed error messages
4. Verify database state using admin tools
