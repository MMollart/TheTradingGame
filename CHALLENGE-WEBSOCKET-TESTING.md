# Challenge WebSocket Testing Guide

## Quick Start Testing

### 1. Start the Backend

```bash
cd backend
uvicorn main:app --reload
```

Backend should start on `http://localhost:8000`

### 2. Test WebSocket Connection

Open browser console and run:

```javascript
// Connect as Player 1
const ws1 = new WebSocket('ws://localhost:8000/ws/ABC123/1');
ws1.onopen = () => console.log('Player 1 connected');
ws1.onmessage = (e) => console.log('Player 1 received:', JSON.parse(e.data));

// Connect as Player 2 (Host/Banker)
const ws2 = new WebSocket('ws://localhost:8000/ws/ABC123/2');
ws2.onopen = () => console.log('Host connected');
ws2.onmessage = (e) => console.log('Host received:', JSON.parse(e.data));
```

You should see both connections open successfully.

### 3. Test Challenge Request

In **another** browser tab's console (or use curl):

```javascript
// Request a challenge (Player 1)
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
}).then(r => r.json()).then(console.log);
```

**Expected Result**: Both WebSocket connections should receive a `challenge_requested` message:

```json
{
  "type": "challenge_requested",
  "challenge": {
    "id": 1,
    "player_id": 1,
    "building_type": "farm",
    "status": "requested",
    ...
  }
}
```

### 4. Test Challenge Assignment

```javascript
// Assign the challenge (Host/Banker)
fetch('http://localhost:8000/api/v2/challenges/ABC123/1/assign', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    challenge_type: 'push_ups',
    challenge_description: '20 Push-ups',
    target_number: 20
  })
}).then(r => r.json()).then(console.log);
```

**Expected Result**: Both WebSocket connections receive `challenge_assigned`:

```json
{
  "type": "challenge_assigned",
  "challenge": {
    "id": 1,
    "status": "assigned",
    "challenge_type": "push_ups",
    "challenge_description": "20 Push-ups",
    "time_remaining_seconds": 600,
    ...
  }
}
```

### 5. Test Challenge Completion

```javascript
// Complete the challenge
fetch('http://localhost:8000/api/v2/challenges/ABC123/1/complete', {
  method: 'POST'
}).then(r => r.json()).then(console.log);
```

**Expected Result**: Both WebSocket connections receive `challenge_completed`:

```json
{
  "type": "challenge_completed",
  "challenge": {
    "id": 1,
    "status": "completed",
    "completed_at": "2025-11-03T12:05:00",
    ...
  }
}
```

## Full Test Scenario

### Setup

1. Create a game with code `ABC123`
2. Add Player 1 (player role, team 1)
3. Add Player 2 (host role)

### Test Flow

```javascript
// Step 1: Connect both users
const player = new WebSocket('ws://localhost:8000/ws/ABC123/1');
const host = new WebSocket('ws://localhost:8000/ws/ABC123/2');

player.onmessage = (e) => {
  const data = JSON.parse(e.data);
  console.log(`[PLAYER] Received ${data.type}:`, data.challenge);
};

host.onmessage = (e) => {
  const data = JSON.parse(e.data);
  console.log(`[HOST] Received ${data.type}:`, data.challenge);
};

// Wait for connections to open...

// Step 2: Player requests challenge
await fetch('http://localhost:8000/api/v2/challenges/ABC123/request', {
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

// Both consoles should show:
// [PLAYER] Received challenge_requested: {...}
// [HOST] Received challenge_requested: {...}

// Step 3: Host assigns challenge
await fetch('http://localhost:8000/api/v2/challenges/ABC123/1/assign', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    challenge_type: 'push_ups',
    challenge_description: '20 Push-ups',
    target_number: 20
  })
});

// Both consoles should show:
// [PLAYER] Received challenge_assigned: {...}
// [HOST] Received challenge_assigned: {...}

// Step 4: Player completes challenge
await fetch('http://localhost:8000/api/v2/challenges/ABC123/1/complete', {
  method: 'POST'
});

// Both consoles should show:
// [PLAYER] Received challenge_completed: {...}
// [HOST] Received challenge_completed: {...}
```

## Testing with Multiple Players

### Scenario: 4 Players + Host

```javascript
// Open 5 browser tabs
// Tab 1-4: Players
// Tab 5: Host

// Tab 1 (Player 1):
const ws = new WebSocket('ws://localhost:8000/ws/ABC123/1');
ws.onmessage = (e) => console.log('P1:', JSON.parse(e.data));

// Tab 2 (Player 2):
const ws = new WebSocket('ws://localhost:8000/ws/ABC123/2');
ws.onmessage = (e) => console.log('P2:', JSON.parse(e.data));

// Tab 3 (Player 3):
const ws = new WebSocket('ws://localhost:8000/ws/ABC123/3');
ws.onmessage = (e) => console.log('P3:', JSON.parse(e.data));

// Tab 4 (Player 4):
const ws = new WebSocket('ws://localhost:8000/ws/ABC123/4');
ws.onmessage = (e) => console.log('P4:', JSON.parse(e.data));

// Tab 5 (Host):
const ws = new WebSocket('ws://localhost:8000/ws/ABC123/5');
ws.onmessage = (e) => console.log('HOST:', JSON.parse(e.data));

// Now request a challenge from Tab 1 (Player 1)
// ALL 5 tabs should receive the message
```

## Common Issues

### Issue: WebSocket connection refused

**Solution**:
```bash
# Check backend is running
curl http://localhost:8000/

# Check if port 8000 is in use
lsof -i :8000
```

### Issue: Messages not received

**Check**:
1. WebSocket is connected: `ws.readyState === 1` (OPEN)
2. Backend logs show broadcast: `[WebSocketManager] Broadcasting to game ABC123`
3. Correct game code in WebSocket URL

### Issue: "Game not found" error

**Solution**:
```python
# Create a game first via API or database
# Or use an existing game code
```

## Automated Test (Python)

```python
import asyncio
import websockets
import json

async def test_challenge_flow():
    """Test full challenge workflow with WebSocket"""
    
    # Connect two clients
    async with websockets.connect('ws://localhost:8000/ws/ABC123/1') as player_ws, \
               websockets.connect('ws://localhost:8000/ws/ABC123/2') as host_ws:
        
        print("✓ Connected")
        
        # Request challenge
        import requests
        response = requests.post('http://localhost:8000/api/v2/challenges/ABC123/request', json={
            'player_id': 1,
            'building_type': 'farm',
            'building_name': 'Farm',
            'team_number': 1,
            'has_school': False
        })
        
        challenge_id = response.json()['id']
        print(f"✓ Challenge {challenge_id} requested")
        
        # Both should receive message
        player_msg = json.loads(await player_ws.recv())
        host_msg = json.loads(await host_ws.recv())
        
        assert player_msg['type'] == 'challenge_requested'
        assert host_msg['type'] == 'challenge_requested'
        print("✓ Both received challenge_requested")
        
        # Assign challenge
        response = requests.post(f'http://localhost:8000/api/v2/challenges/ABC123/{challenge_id}/assign', json={
            'challenge_type': 'push_ups',
            'challenge_description': '20 Push-ups',
            'target_number': 20
        })
        
        # Both should receive message
        player_msg = json.loads(await player_ws.recv())
        host_msg = json.loads(await host_ws.recv())
        
        assert player_msg['type'] == 'challenge_assigned'
        assert host_msg['type'] == 'challenge_assigned'
        print("✓ Both received challenge_assigned")
        
        # Complete challenge
        response = requests.post(f'http://localhost:8000/api/v2/challenges/ABC123/{challenge_id}/complete')
        
        # Both should receive message
        player_msg = json.loads(await player_ws.recv())
        host_msg = json.loads(await host_ws.recv())
        
        assert player_msg['type'] == 'challenge_completed'
        assert host_msg['type'] == 'challenge_completed'
        print("✓ Both received challenge_completed")
        
        print("\n✅ All tests passed!")

# Run test
asyncio.run(test_challenge_flow())
```

## Performance Test

```python
import asyncio
import websockets
import time

async def stress_test():
    """Test with many concurrent connections"""
    
    connections = []
    
    # Connect 20 clients
    for i in range(20):
        ws = await websockets.connect(f'ws://localhost:8000/ws/ABC123/{i}')
        connections.append(ws)
    
    print(f"✓ Connected {len(connections)} clients")
    
    # Send a challenge request
    import requests
    start = time.time()
    
    requests.post('http://localhost:8000/api/v2/challenges/ABC123/request', json={
        'player_id': 1,
        'building_type': 'farm',
        'building_name': 'Farm',
        'team_number': 1,
        'has_school': False
    })
    
    # All clients should receive message
    for ws in connections:
        msg = await ws.recv()
        # Message received
    
    elapsed = time.time() - start
    print(f"✓ Broadcast to 20 clients in {elapsed:.3f}s")
    
    # Cleanup
    for ws in connections:
        await ws.close()

asyncio.run(stress_test())
```

## Expected Output

When everything works correctly, you should see:

```
[ChallengeWS] Connecting to ws://localhost:8000/ws/ABC123/1
[ChallengeWS] Connected
[ChallengeWS] Received: {type: "challenge_requested", challenge: {...}}
[ChallengeWS] Received: {type: "challenge_assigned", challenge: {...}}
[ChallengeWS] Received: {type: "challenge_completed", challenge: {...}}
```

## Next Steps

Once testing confirms WebSocket sync works:

1. Integrate into React/Vue frontend
2. Add UI components for challenge cards
3. Implement timer countdown display
4. Add notification sounds/toasts
5. Test with real users in different browsers
