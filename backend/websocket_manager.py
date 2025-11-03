"""
WebSocket connection manager for real-time game updates
"""

from typing import Dict, List, Set
from fastapi import WebSocket
import json


class ConnectionManager:
    """Manages WebSocket connections for game sessions"""
    
    def __init__(self):
        # game_code -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> (game_code, player_id, role)
        self.connection_info: Dict[WebSocket, tuple] = {}
    
    async def connect(self, websocket: WebSocket, game_code: str, player_id: int, role: str):
        """Connect a player to a game session"""
        await websocket.accept()
        
        if game_code not in self.active_connections:
            self.active_connections[game_code] = set()
        
        self.active_connections[game_code].add(websocket)
        self.connection_info[websocket] = (game_code, player_id, role)
        
        # Notify others that a player connected
        await self.broadcast_to_game(game_code, {
            "type": "player_connected",
            "player_id": player_id,
            "role": role
        }, exclude=websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a player from their game session"""
        if websocket in self.connection_info:
            game_code, player_id, role = self.connection_info[websocket]
            
            if game_code in self.active_connections:
                self.active_connections[game_code].discard(websocket)
                
                # Clean up empty game sessions
                if not self.active_connections[game_code]:
                    del self.active_connections[game_code]
            
            del self.connection_info[websocket]
            
            # Could notify others, but we'll skip for disconnects
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific connection"""
        await websocket.send_json(message)
    
    async def broadcast_to_game(self, game_code: str, message: dict, exclude: WebSocket = None):
        """Broadcast a message to all players in a game"""
        if game_code not in self.active_connections:
            return
        
        dead_connections = set()
        
        for connection in self.active_connections[game_code]:
            if connection == exclude:
                continue
            
            try:
                await connection.send_json(message)
            except Exception:
                # Connection is dead, mark for removal
                dead_connections.add(connection)
        
        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection)
    
    async def send_to_role(self, game_code: str, role: str, message: dict):
        """Send a message to all players with a specific role in a game"""
        if game_code not in self.active_connections:
            return
        
        for connection in self.active_connections[game_code]:
            if connection in self.connection_info:
                _, _, conn_role = self.connection_info[connection]
                if conn_role == role:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        pass
    
    async def send_to_player(self, game_code: str, player_id: int, message: dict):
        """Send a message to a specific player in a game"""
        if game_code not in self.active_connections:
            return
        
        for connection in self.active_connections[game_code]:
            if connection in self.connection_info:
                _, conn_player_id, _ = self.connection_info[connection]
                if conn_player_id == player_id:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        pass
                    break
    
    # ==================== Challenge-Specific Broadcasts ====================
    
    async def broadcast_challenge_requested(self, game_code: str, challenge_data: dict):
        """
        Broadcast that a new challenge has been requested.
        
        This notifies host/banker that a player needs a challenge assigned.
        Frontend expects format: {"event_type": "challenge_request", "data": {...}}
        """
        await self.broadcast_to_game(game_code, {
            "type": "event",
            "event_type": "challenge_request",
            "data": challenge_data
        })
    
    async def broadcast_challenge_assigned(self, game_code: str, challenge_data: dict):
        """
        Broadcast that a challenge has been assigned.
        
        This notifies:
        - The requesting player: their challenge is ready
        - Host/banker: challenge moved from pending to active
        - Other players: awareness of ongoing challenges
        
        Frontend expects format: {"event_type": "challenge_assigned", "data": {...}}
        """
        await self.broadcast_to_game(game_code, {
            "type": "event",
            "event_type": "challenge_assigned",
            "data": challenge_data
        })
    
    async def broadcast_challenge_completed(self, game_code: str, challenge_data: dict):
        """
        Broadcast that a challenge has been completed.
        
        This notifies all users that the challenge is done and can be removed
        from active lists.
        
        Frontend expects format: {"event_type": "challenge_completed", "data": {...}}
        """
        await self.broadcast_to_game(game_code, {
            "type": "event",
            "event_type": "challenge_completed",
            "data": challenge_data
        })
    
    async def broadcast_challenge_cancelled(self, game_code: str, challenge_data: dict):
        """
        Broadcast that a challenge has been cancelled.
        
        This notifies all users to remove the challenge from their UI.
        
        Frontend expects format: {"event_type": "challenge_cancelled", "data": {...}}
        """
        await self.broadcast_to_game(game_code, {
            "type": "event",
            "event_type": "challenge_cancelled",
            "data": challenge_data
        })
    
    async def broadcast_challenge_expired(self, game_code: str, challenge_data: dict):
        """
        Broadcast that a challenge has expired (time ran out).
        
        This notifies all users that the challenge deadline passed.
        
        Frontend expects format: {"event_type": "challenge_expired", "data": {...}}
        """
        await self.broadcast_to_game(game_code, {
            "type": "event",
            "event_type": "challenge_expired",
            "data": challenge_data
        })


# Global connection manager instance
manager = ConnectionManager()
