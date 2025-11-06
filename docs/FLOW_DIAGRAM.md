# Player Dashboard Refresh Flow

## Before Fix ❌

### Challenge Completion
```
Player completes challenge
         ↓
Host/Banker marks complete
         ↓
Backend: complete_challenge_with_bank_transfer()
         ↓
   Update database:
   - Team resources +X
   - Banker inventory -X
   - Challenge status = COMPLETED
         ↓
   db.commit()
         ↓
   Return success
         ↓
   ❌ NO WEBSOCKET BROADCAST
         ↓
   Player dashboard shows STALE DATA
   (Must manually refresh page to see new resources)
```

### Manual Resource/Building Grant
```
Host gives resources/buildings to team
         ↓
Backend: give_manual_resources() or give_manual_buildings()
         ↓
   Update database:
   - Team resources/buildings += amount
         ↓
   db.commit()
         ↓
   Return success
         ↓
   ❌ NO WEBSOCKET BROADCAST
         ↓
   Team dashboard shows STALE DATA
   (Must manually refresh page to see new items)
```

## After Fix ✅

### Challenge Completion
```
Player completes challenge
         ↓
Host/Banker marks complete
         ↓
Backend: complete_challenge_with_bank_transfer()
         ↓
   Update database:
   - Team resources +X
   - Banker inventory -X
   - Challenge status = COMPLETED
         ↓
   db.commit()
         ↓
   ✅ WEBSOCKET BROADCAST: state_updated
         ↓
   All connected clients receive update
         ↓
   Frontend handler (dashboard.js):
   - Updates gameState
   - Updates teamState for players
   - Calls updateDashboard()
         ↓
   ✅ Player dashboard AUTO-REFRESHES with new resources
```

### Manual Resource/Building Grant
```
Host gives resources/buildings to team
         ↓
Backend: give_manual_resources() or give_manual_buildings()
         ↓
   Update database:
   - Team resources/buildings += amount
         ↓
   db.commit()
         ↓
   ✅ WEBSOCKET BROADCAST: state_updated
         ↓
   All connected clients receive update
         ↓
   Frontend handler (dashboard.js):
   - Updates gameState
   - Updates teamState for players
   - Calls updateDashboard()
         ↓
   ✅ Team dashboard AUTO-REFRESHES with new items
```

## Technical Details

### Backend Broadcast Code
```python
# After db.commit(), add:
await manager.broadcast_to_game(game_code.upper(), {
    "type": "state_updated",
    "state": game.game_state
})
```

### Frontend Handler (Already Exists)
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
    
    updateDashboard();  // 🎉 Dashboard refreshes!
});
```

## Key Points

1. **Minimal Change**: Only 15 lines added to production code (3 broadcasts)
2. **No Breaking Changes**: Only adds missing WebSocket events
3. **Leverages Existing Code**: Frontend handler already exists and works
4. **Consistent Pattern**: Follows same pattern used by other endpoints
5. **Database Safety**: Broadcast happens AFTER db.commit(), ensuring data is persisted
6. **Game Code Normalization**: Uses game_code.upper() for consistency
