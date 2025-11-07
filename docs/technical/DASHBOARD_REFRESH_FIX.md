# Dashboard Refresh Fix

## Issue
Player Dashboard does not refresh when:
1. A challenge is marked as complete
2. They are sent resources/buildings by the host

## Root Cause
Three backend endpoints were modifying team resources/buildings but not broadcasting WebSocket events to notify connected clients:

1. **`complete_challenge_with_bank_transfer`** (main.py line ~1457)
   - Transfers resources from bank to team when challenge is completed
   - Updates `game.game_state['teams'][team_number]['resources']`
   - Missing: WebSocket broadcast

2. **`give_manual_resources`** (main.py line ~1234)
   - Host manually gives resources to a team
   - Updates `game.game_state['teams'][team_number]['resources']`
   - Missing: WebSocket broadcast

3. **`give_manual_buildings`** (main.py line ~1290)
   - Host manually gives buildings to a team
   - Updates `game.game_state['teams'][team_number]['buildings']`
   - Missing: WebSocket broadcast

## Solution
Added WebSocket `state_updated` broadcasts to all three endpoints after `db.commit()`:

```python
# Broadcast state update to all players so dashboards refresh
await manager.broadcast_to_game(game_code.upper(), {
    "type": "state_updated",
    "state": game.game_state
})
```

### Why This Works

The frontend already has a handler for `state_updated` events (dashboard.js line 154-170):

```javascript
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
        }
    }
    
    updateDashboard();
});
```

When a `state_updated` event is received:
1. Updates global `gameState` with latest data
2. For players: updates `teamState` with their team's resources/buildings
3. Calls `updateDashboard()` to refresh the UI

## Implementation Details

### Changes Made
1. All three endpoints are already `async` functions (required for WebSocket broadcasts)
2. Added broadcast after `db.commit()` to ensure data persistence before notification
3. Used `game_code.upper()` for consistency with other broadcasts
4. Broadcast includes entire `game.game_state` to sync all clients

### Testing
Created `test_dashboard_refresh.py` with tests to verify:
- ✓ All three endpoints broadcast `state_updated` events
- ✓ Broadcasts include the game state
- ✓ Broadcasts use `game_code.upper()` for consistency
- ✓ Broadcasts happen after `db.commit()` to ensure data persistence

## Impact
- **Players**: Dashboard now refreshes automatically when:
  - They complete a challenge and receive resources
  - Host manually gives them resources
  - Host manually gives them buildings
  
- **Host/Banker**: Already had refresh mechanisms, but these are now more consistent

- **Backward Compatibility**: No breaking changes - only adds missing WebSocket events

## Files Modified
- `backend/main.py`: Added broadcasts to 3 endpoints
- `backend/tests/test_dashboard_refresh.py`: New test file

## Related Code
- WebSocket manager: `backend/websocket_manager.py`
- Frontend handler: `frontend/dashboard.js` (line 154-170)
- Team state structure: `backend/game_constants.py`
