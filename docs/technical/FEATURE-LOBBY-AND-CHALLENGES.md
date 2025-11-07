# Lobby State and Production Challenge System

## Overview
Implemented two major gameplay improvements:
1. **Lobby State Management**: Hide gameplay cards (Production, Trading, Build Buildings) when game is in WAITING state
2. **Challenge Request System**: Players must request challenges from banker/host before production

## Changes Implemented

### 1. Lobby State - Hide Gameplay Cards

**Problem**: Players in the game lobby (WAITING state) could see all gameplay cards including Production, Trading, and Build Buildings, even though these aren't functional until the game starts.

**Solution**: Cards are now dynamically hidden/shown based on game status.

#### Frontend Changes (`dashboard.html`)
- Added IDs to gameplay cards:
  - `card-production` - Production card
  - `card-trading` - Trading card  
  - `card-build-buildings` - Build Buildings card

#### Frontend Changes (`dashboard.js`)
- Added `updatePlayerCardsVisibility()` function that:
  - Checks current game status (`currentGameStatus`)
  - Hides gameplay cards when `status === 'waiting'`
  - Shows cards when game is active (`in_progress`, `paused`, etc.)
  - Only applies to player role (not host/banker)

**Behavior**:
- **WAITING state**: Players only see Resources, Buildings, and Team Members cards
- **IN_PROGRESS state**: All gameplay cards become visible
- **Host/Banker**: Always see all cards regardless of game state

---

### 2. Production Challenge Request System

**Problem**: Players could see their challenges immediately and complete production without banker/host oversight.

**Solution**: Implemented request/approval workflow for production challenges.

#### Player Experience

**Before requesting challenge**:
- Production buttons show: `📋 Request Challenge`
- Challenge description hidden
- "Complete Challenge" button hidden

**After requesting challenge**:
- Button changes to: `⏳ Awaiting Challenge...`
- Button becomes disabled
- Request sent to banker/host via WebSocket

**After challenge assigned**:
- Challenge description appears: "Challenge: 20 Press-ups"
- Request button hidden
- `✅ Complete Challenge` button appears
- Player can now complete the challenge

**After completing challenge**:
- UI resets to initial state
- Player must request new challenge for next production cycle

#### Banker/Host Experience

**Challenge Requests Dashboard**:
- New card: "🏋️ Production Challenge Requests"
- Located in Banker View tab
- Shows all pending challenge requests with:
  - Player name
  - Building type (Farm, Mine, etc.)
  - Timestamp of request

**Assigning Challenges**:
1. Banker/host sees request in list
2. Selects challenge type from dropdown (Push-ups, Sit-ups, Burpees, etc.)
3. Sets target number (auto-fills with default value, can be adjusted)
4. Clicks `✅ Assign` button
5. Challenge sent to player via WebSocket as formatted string (e.g., "20 Push-ups")
6. Request removed from pending list

**Available Challenge Types**:
- Push-ups (default: 20)
- Sit-ups (default: 30)
- Burpees (default: 15)
- Star Jumps (default: 25)
- Squats (default: 20)
- Lunges (default: 20)
- Plank in seconds (default: 60)
- Jumping Jacks (default: 30)

**Dismissing Requests**:
- Banker/host can click `❌ Dismiss` to remove request without assigning challenge

#### Frontend Changes (`dashboard.html`)

**Production Card Updates**:
```html
<!-- Old -->
<p>Challenge: <span id="farm-challenge">20 Press-ups</span></p>
<button onclick="startProduction('farm')">Produce</button>

<!-- New -->
<p class="challenge-display" id="farm-challenge-display" style="display: none;">
    Challenge: <span id="farm-challenge">Awaiting challenge...</span>
</p>
<button onclick="requestChallenge('farm')" id="farm-request-btn">
    📋 Request Challenge
</button>
<button onclick="startProduction('farm')" id="farm-produce-btn" style="display: none;">
    ✅ Complete Challenge
</button>
```

**Host/Banker Dashboard Addition**:
```html
<div class="card full-width" id="card-challenge-requests">
    <h3>🏋️ Production Challenge Requests</h3>
    <div id="challenge-requests-list">
        <!-- Requests populate here with dropdown and number input -->
    </div>
</div>
```

#### Frontend Changes (`dashboard.js`)

**New Functions**:
- `requestChallenge(buildingType)` - Player requests challenge from banker/host
- `receiveChallengeAssignment(buildingType, challengeDescription)` - Player receives assigned challenge
- `updateChallengeRequestsList()` - Renders pending challenge requests with dropdown UI
- `updateChallengeTargetPreview(playerId, buildingType)` - Updates target number when challenge type changes
- `assignChallenge(playerId, buildingType)` - Banker/host assigns challenge to player from dropdown selection
- `dismissChallengeRequest(playerId, buildingType)` - Banker/host dismisses request

**New Data Structures**:
- `challengeTypes` - Configuration object with challenge names and default values
- `pendingChallengeRequests` - Array tracking all pending challenge requests

**Updated Functions**:
- `startProduction()` - Now uses assigned challenge description
- `completeChallenge()` - Resets UI after production completion

**New State Management**:
- `pendingChallengeRequests` array tracks all pending requests
- Each request contains: `player_id`, `player_name`, `building_type`, `building_name`, `timestamp`

#### WebSocket Events

**challenge_request** (Player → Banker/Host):
```javascript
{
    type: 'event',
    event_type: 'challenge_request',
    data: {
        player_id: 123,
        player_name: "Alice",
        building_type: "farm",
        building_name: "🌾 Farm"
    }
}
```

**challenge_assigned** (Banker/Host → Player):
```javascript
{
    type: 'event',
    event_type: 'challenge_assigned',
    data: {
        player_id: 123,
        building_type: "farm",
        challenge_description: "20 Push-ups",
        challenge_type: "push_ups",
        target_number: 20
    }
}
```

#### CSS Changes (`dashboard-styles.css`)

Added styles for:
- `.challenge-requests-section` - Container styling
- `.challenge-requests-list` - List layout
- `.challenge-request-item` - Individual request card with hover effects
- `.challenge-display` - Challenge description styling

---

## User Workflows

### Player Production Workflow

1. Player navigates to Production card (only visible when game is IN_PROGRESS)
2. Player clicks `📋 Request Challenge` for desired building
3. Button changes to `⏳ Awaiting Challenge...`
4. Player waits for banker/host to assign challenge
5. Challenge appears: "Challenge: 20 Press-ups"
6. `✅ Complete Challenge` button appears
7. Player performs physical challenge
8. Player clicks `✅ Complete Challenge`
9. Challenge modal opens for final confirmation
10. Player confirms challenge completion
11. Production resources granted
12. UI resets - player must request new challenge for next production

### Banker/Host Challenge Assignment Workflow

1. Banker/host monitors "🏋️ Production Challenge Requests" card
2. New request appears with player name and building type
3. Banker/host selects challenge type from dropdown (e.g., "Push-ups")
4. Target number auto-fills with default value (e.g., 20 for Push-ups)
5. Banker/host can adjust target number if needed
6. Banker/host clicks `✅ Assign`
7. Challenge sent to player as formatted string (e.g., "20 Push-ups")
8. Request removed from pending list
9. Event log shows: "Challenge assigned: 20 Push-ups"

---

## Backend Integration Required

The following WebSocket event types need backend handling:

### challenge_request
- Received from player
- Broadcast to host and banker roles
- Store in game state (optional - for persistence)

### challenge_assigned
- Received from host/banker
- Send to specific player_id
- Store challenge in player state (optional)

### Example Backend Handler (Pseudocode)
```python
@websocket_event
def handle_challenge_request(data):
    player_id = data['player_id']
    building_type = data['building_type']
    
    # Broadcast to host and banker
    broadcast_to_roles(['host', 'banker'], {
        'event_type': 'challenge_request',
        'data': data
    })

@websocket_event
def handle_challenge_assigned(data):
    player_id = data['player_id']
    challenge = data['challenge_description']
    
    # Send to specific player
    send_to_player(player_id, {
        'event_type': 'challenge_assigned',
        'data': data
    })
```

---

## Testing Checklist

### Lobby State
- [x] Player in WAITING state sees limited cards
- [x] Player in IN_PROGRESS state sees all cards
- [x] Host/Banker always see all cards
- [x] Cards properly show/hide on game state transitions

### Challenge Request System
- [ ] Player can request challenge
- [ ] Request button disables after click
- [ ] Banker/Host sees request in dashboard
- [ ] Banker can enter custom challenge text
- [ ] Challenge assignment reaches player
- [ ] Challenge description displays correctly
- [ ] Complete Challenge button appears after assignment
- [ ] Production completes successfully
- [ ] UI resets after production
- [ ] Multiple simultaneous requests handled correctly
- [ ] Dismiss request removes it from list

---

## Files Modified

1. `TheTradingGame/frontend/dashboard.html`
   - Added IDs to gameplay cards
   - Modified production buttons structure
   - Added Challenge Requests card to Banker tab

2. `TheTradingGame/frontend/dashboard.js`
   - Added `updatePlayerCardsVisibility()` 
   - Added `requestChallenge()`, `receiveChallengeAssignment()`
   - Added `updateBankerDashboard()`, `updateChallengeRequestsList()`
   - Added `assignChallenge()`, `dismissChallengeRequest()`
   - Updated `handleGameEvent()` with new event types
   - Updated `completeChallenge()` to reset UI

3. `TheTradingGame/frontend/dashboard-styles.css`
   - Added `.challenge-requests-section`
   - Added `.challenge-request-item`
   - Added `.challenge-display`

---

## Future Enhancements

1. ~~**Challenge Templates**: Predefined challenge options for banker to select~~ ✅ **Implemented**
2. **Challenge History**: Track which challenges were assigned to each player
3. **Challenge Difficulty**: Scale challenges based on building count
4. **Bulk Assignment**: Assign same challenge to multiple pending requests
5. **Challenge Timer**: Limit time to complete challenge
6. **Challenge Verification**: Require photo/video proof of completion
7. **Auto-Dismiss**: Automatically dismiss old requests after timeout
8. **Custom Challenge Types**: Allow host to add custom challenge types with defaults
9. **Challenge Presets per Building**: Different default challenges for different building types

---

## Known Limitations

1. Challenge requests are not persisted - lost on page refresh
2. No notification sound/alert when new request arrives
3. Banker must manually scroll to see all pending requests
4. No search/filter for challenge requests
5. Challenge description limited to text input (no presets yet)

---

## Status
✅ **Complete** - Ready for backend integration and testing
