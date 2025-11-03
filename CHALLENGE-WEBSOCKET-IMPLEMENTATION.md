# Challenge WebSocket Real-Time Synchronization

## Overview

This implementation provides **real-time bidirectional challenge synchronization** for multi-user workflows in The Trading Game. When a challenge is created, assigned, completed, or cancelled by one user, all connected users (players, host, banker) receive instant updates via WebSocket.

## Problem Solved

**Before**: If Player A requests a challenge and Player B (host/banker) assigns it, Player A wouldn't know until they manually refreshed or polled the API.

**After**: Player A's UI updates instantly when the challenge is assigned, and both users see the same state in real-time.

## Architecture

```
┌─────────────┐                    ┌──────────────────┐                    ┌─────────────┐
│   Player A  │                    │  FastAPI Server  │                    │ Host/Banker │
│  (Frontend) │                    │    (Backend)     │                    │  (Frontend) │
└──────┬──────┘                    └────────┬─────────┘                    └──────┬──────┘
       │                                    │                                      │
       │  1. POST /api/v2/challenges       │                                      │
       │     /ABC123/request               │                                      │
       ├──────────────────────────────────>│                                      │
       │                                    │                                      │
       │  2. DB Write + WebSocket Broadcast│                                      │
       │     "challenge_requested"          │                                      │
       │<───────────────────────────────────┤────────────────────────────────────>│
       │     (via WebSocket)                │        (via WebSocket)              │
       │                                    │                                      │
       │                                    │  3. POST /api/v2/challenges         │
       │                                    │     /ABC123/123/assign              │
       │                                    │<─────────────────────────────────────┤
       │                                    │                                      │
       │  4. DB Write + WebSocket Broadcast│                                      │
       │     "challenge_assigned"           │                                      │
       │<───────────────────────────────────┤────────────────────────────────────>│
       │     (via WebSocket)                │        (via WebSocket)              │
       │                                    │                                      │
       │  5. POST /api/v2/challenges        │                                      │
       │     /ABC123/123/complete           │                                      │
       ├──────────────────────────────────>│                                      │
       │                                    │                                      │
       │  6. DB Write + WebSocket Broadcast│                                      │
       │     "challenge_completed"          │                                      │
       │<───────────────────────────────────┤────────────────────────────────────>│
       │     (via WebSocket)                │        (via WebSocket)              │
```

## Components Modified

### 1. WebSocket Manager (`backend/websocket_manager.py`)

**Added Methods**:
- `broadcast_challenge_requested(game_code, challenge_data)`
- `broadcast_challenge_assigned(game_code, challenge_data)`
- `broadcast_challenge_completed(game_code, challenge_data)`
- `broadcast_challenge_cancelled(game_code, challenge_data)`
- `broadcast_challenge_expired(game_code, challenge_data)`

**Purpose**: Centralized challenge event broadcasting to all connected clients in a game.

### 2. Challenge Manager (`backend/challenge_manager.py`)

**Modified Methods** (converted to async):
- `async create_challenge_request()` - Broadcasts `challenge_requested`
- `async assign_challenge()` - Broadcasts `challenge_assigned`
- `async complete_challenge()` - Broadcasts `challenge_completed`
- `async cancel_challenge()` - Broadcasts `challenge_cancelled`

**New Behavior**: After each database operation, automatically broadcasts the event to all connected WebSocket clients.

### 3. Challenge API (`backend/challenge_api.py`)

**Modified Endpoints** (converted to async):
- `POST /api/v2/challenges/{game_code}/request`
- `POST /api/v2/challenges/{game_code}/{challenge_id}/assign`
- `POST /api/v2/challenges/{game_code}/{challenge_id}/complete`
- `POST /api/v2/challenges/{game_code}/{challenge_id}/cancel`

**Change**: Now `async` functions that `await` the ChallengeManager methods.

## WebSocket Message Format

All challenge events follow this structure (matching existing game event format):

```json
{
  "type": "event",
  "event_type": "challenge_request|challenge_assigned|challenge_completed|challenge_cancelled|challenge_expired",
  "data": {
    "id": 123,
    "game_session_id": 456,
    "player_id": 1,
    "player_name": "John Doe",
    "building_type": "farm",
    "building_name": "Farm",
    "team_number": 1,
    "has_school": false,
    "challenge_type": "push_ups",
    "challenge_description": "20 Push-ups",
    "target_number": 20,
    "status": "assigned",
    "requested_at": "2025-11-03T12:00:00",
    "assigned_at": "2025-11-03T12:01:00",
    "completed_at": null,
    "timestamp": "2025-11-03T12:01:00",
    "start_time": 1699012860000,
    "time_remaining_seconds": 600
  }
}
```

## Frontend Integration

### React Hook Example

```jsx
import { useChallengeWebSocket } from './challenge-websocket-integration';

function PlayerDashboard({ gameCode, playerId }) {
  const [activeChallenges, setActiveChallenges] = useState([]);
  
  useChallengeWebSocket(gameCode, playerId, {
    onChallengeAssigned: (challenge) => {
      // Challenge assigned to this player - show in UI
      setActiveChallenges(prev => [...prev, challenge]);
      showNotification(`New challenge: ${challenge.challenge_description}`);
    },
    
    onChallengeCompleted: (challenge) => {
      // Challenge completed - remove from UI
      setActiveChallenges(prev => 
        prev.filter(c => c.id !== challenge.id)
      );
    }
  });
  
  return (
    <div>
      <h2>Active Challenges</h2>
      {activeChallenges.map(challenge => (
        <ChallengeCard key={challenge.id} challenge={challenge} />
      ))}
    </div>
  );
}
```

### Host/Banker View Example

```jsx
function HostDashboard({ gameCode, playerId }) {
  const [pendingChallenges, setPendingChallenges] = useState([]);
  const [activeChallenges, setActiveChallenges] = useState([]);
  
  useChallengeWebSocket(gameCode, playerId, {
    onChallengeRequested: (challenge) => {
      // New challenge request - add to pending
      setPendingChallenges(prev => [...prev, challenge]);
      playNotificationSound();
    },
    
    onChallengeAssigned: (challenge) => {
      // Challenge assigned - move from pending to active
      setPendingChallenges(prev => 
        prev.filter(c => c.id !== challenge.id)
      );
      setActiveChallenges(prev => [...prev, challenge]);
    },
    
    onChallengeCompleted: (challenge) => {
      // Challenge completed - remove from active
      setActiveChallenges(prev => 
        prev.filter(c => c.id !== challenge.id)
      );
    }
  });
  
  return (
    <div>
      <h2>Pending Challenges ({pendingChallenges.length})</h2>
      {pendingChallenges.map(challenge => (
        <PendingChallengeCard 
          key={challenge.id} 
          challenge={challenge}
          onAssign={assignChallenge}
        />
      ))}
      
      <h2>Active Challenges ({activeChallenges.length})</h2>
      {activeChallenges.map(challenge => (
        <ActiveChallengeCard 
          key={challenge.id} 
          challenge={challenge}
          onComplete={completeChallenge}
          onCancel={cancelChallenge}
        />
      ))}
    </div>
  );
}
```

## Event Flow Examples

### Example 1: Challenge Request to Assignment

1. **Player A** clicks "Request Challenge" for Farm
2. **Frontend** calls `POST /api/v2/challenges/ABC123/request`
3. **Backend** creates challenge in DB with status `REQUESTED`
4. **Backend** broadcasts `challenge_requested` via WebSocket
5. **Host/Banker UI** instantly shows new challenge in pending list
6. **Host/Banker** selects "20 Push-ups" and clicks "Assign"
7. **Frontend** calls `POST /api/v2/challenges/ABC123/123/assign`
8. **Backend** updates challenge status to `ASSIGNED` with timestamp
9. **Backend** broadcasts `challenge_assigned` via WebSocket
10. **Player A UI** instantly shows active challenge with countdown timer
11. **Host/Banker UI** moves challenge from pending to active tab

### Example 2: Challenge Completion

1. **Player A** completes 20 push-ups and clicks "Mark Complete"
2. **Frontend** calls `POST /api/v2/challenges/ABC123/123/complete`
3. **Backend** updates challenge status to `COMPLETED`
4. **Backend** broadcasts `challenge_completed` via WebSocket
5. **Player A UI** removes challenge and shows success message
6. **Host/Banker UI** removes challenge from active tab
7. **Player A** can now build the Farm

## Connection Management

### Auto-Reconnect

The WebSocket client includes automatic reconnection with exponential backoff:

```javascript
attemptReconnect() {
  if (this.reconnectAttempts >= this.maxReconnectAttempts) {
    console.error('[ChallengeWS] Max reconnect attempts reached');
    return;
  }
  
  this.reconnectAttempts++;
  const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
  
  console.log(`[ChallengeWS] Reconnecting in ${delay}ms`);
  setTimeout(() => this.connect(), delay);
}
```

**Retry delays**: 2s, 4s, 8s, 10s (capped), 10s

### Connection URL

```
ws://localhost:8000/ws/{game_code}/{player_id}
```

**Production**: Replace with `wss://` for secure WebSocket over TLS.

## Testing the Implementation

### Manual Test Flow

1. **Start Backend**:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. **Open Two Browser Windows**:
   - Window 1: Player A (player_id=1)
   - Window 2: Host/Banker (player_id=2)

3. **Test Challenge Request**:
   - Window 1: Request challenge for Farm
   - Window 2: Should instantly see pending challenge

4. **Test Challenge Assignment**:
   - Window 2: Assign "20 Push-ups"
   - Window 1: Should instantly see active challenge with timer

5. **Test Challenge Completion**:
   - Window 1: Mark complete
   - Both windows: Challenge removed from active lists

### Browser Console Testing

```javascript
// In Player A's console
const ws = new WebSocket('ws://localhost:8000/ws/ABC123/1');
ws.onmessage = (e) => console.log('Player A received:', JSON.parse(e.data));

// In Host/Banker's console
const ws = new WebSocket('ws://localhost:8000/ws/ABC123/2');
ws.onmessage = (e) => console.log('Host received:', JSON.parse(e.data));

// Make API call from one window, see message in both
fetch('http://localhost:8000/api/v2/challenges/ABC123/request', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    player_id: 1,
    building_type: 'farm',
    building_name: 'Farm',
    team_number: 1,
    has_school: false
  })
});
```

## Performance Considerations

### Scalability

- **WebSocket connections**: 1 per connected user
- **Broadcast complexity**: O(n) where n = users in game
- **Typical game size**: 4-20 players = minimal overhead
- **Large games**: Consider Redis pub/sub for horizontal scaling

### Network Efficiency

- **Message size**: ~500 bytes per challenge event
- **Frequency**: Low (only on challenge state changes)
- **Bandwidth**: Negligible for typical game sessions

### Database Impact

- **No additional queries**: WebSocket broadcasts use existing data
- **Connection pooling**: SQLAlchemy handles DB connections
- **No N+1 queries**: Single query per operation

## Troubleshooting

### WebSocket Connection Fails

**Symptom**: Browser console shows `WebSocket connection failed`

**Fixes**:
1. Check backend is running: `curl http://localhost:8000/`
2. Verify game code and player ID exist
3. Check browser console for CORS errors
4. Ensure using correct protocol (ws:// vs wss://)

### Messages Not Received

**Symptom**: API call succeeds but UI doesn't update

**Fixes**:
1. Check WebSocket is connected: `ws.readyState === WebSocket.OPEN`
2. Verify event handler is registered: `client.on('challenge_assigned', ...)`
3. Check browser console for WebSocket messages
4. Confirm game_code matches between API and WebSocket

### Race Conditions

**Symptom**: UI shows challenge before database commit completes

**Solution**: Backend commits to DB *before* broadcasting, ensuring consistency.

## Migration from Old Challenge System

If you have existing challenge code without WebSocket:

1. **Keep API endpoints**: V2 endpoints are backward compatible
2. **Add WebSocket client**: Use `challenge-websocket-integration.js`
3. **Update event handlers**: Replace polling with WebSocket callbacks
4. **Test both users**: Ensure host and player see same state

## Future Enhancements

1. **Challenge expiry notifications**: Broadcast when timer runs out
2. **Pause/resume sync**: Adjust timers for all clients when game pauses
3. **Challenge history**: Show completed challenges in game summary
4. **Multi-challenge support**: Allow players to have multiple active challenges
5. **Team-wide visibility**: Show other team members' challenges

## API Endpoints Reference

### Request Challenge
```http
POST /api/v2/challenges/{game_code}/request
Content-Type: application/json

{
  "player_id": 1,
  "building_type": "farm",
  "building_name": "Farm",
  "team_number": 1,
  "has_school": false
}
```

### Assign Challenge
```http
POST /api/v2/challenges/{game_code}/{challenge_id}/assign
Content-Type: application/json

{
  "challenge_type": "push_ups",
  "challenge_description": "20 Push-ups",
  "target_number": 20
}
```

### Complete Challenge
```http
POST /api/v2/challenges/{game_code}/{challenge_id}/complete
```

### Cancel Challenge
```http
POST /api/v2/challenges/{game_code}/{challenge_id}/cancel
```

### Get Active Challenges
```http
GET /api/v2/challenges/{game_code}/active?include_time_remaining=true
```

## Summary

This implementation provides **production-ready real-time challenge synchronization** using:
- FastAPI WebSockets (async/await)
- Centralized broadcast management
- Automatic reconnection
- Type-safe event handling
- React hooks for easy integration

**Result**: Players and host/banker stay perfectly in sync with zero polling overhead and instant UI updates.
