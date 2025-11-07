"""
Challenge Management Service

Handles all challenge lifecycle operations with pause-aware timing.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Challenge, ChallengeStatus, GameSession, Player
from websocket_manager import manager as ws_manager


class ChallengeManager:
    """
    Centralized challenge management with pause-aware timing.
    
    Key features:
    - Single source of truth for challenge state
    - Automatic expiry checking with pause compensation
    - Multi-user (host/banker) support
    - Database-backed state management
    """
    
    CHALLENGE_DURATION_MINUTES = 10
    
    def __init__(self, db: Session):
        self.db = db
    
    async def create_challenge_request(
        self,
        game_code: str,
        player_id: int,
        building_type: str,
        building_name: str,
        team_number: int,
        has_school: bool
    ) -> Challenge:
        """
        Create a new challenge request from a player.
        
        Args:
            game_code: Game session code
            player_id: ID of requesting player
            building_type: Type of building (farm, mine, etc.)
            building_name: Formatted building name
            team_number: Player's team number
            has_school: Whether team has a school (affects locking)
        
        Returns:
            Created Challenge object
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            raise ValueError(f"Game {game_code} not found")
        
        # Check if there's already an active challenge for this player/building
        existing = self.db.query(Challenge).filter(
            Challenge.game_session_id == game.id,
            Challenge.player_id == player_id,
            Challenge.building_type == building_type,
            Challenge.status.in_([ChallengeStatus.REQUESTED, ChallengeStatus.ASSIGNED])
        ).first()
        
        if existing:
            raise ValueError(f"Challenge already exists for player {player_id} building {building_type}")
        
        # Check bank inventory for required resources
        team_key = str(team_number)
        team_data = game.game_state.get('teams', {}).get(team_key, {}) if game.game_state else {}
        building_count = team_data.get('buildings', {}).get(building_type, 0)
        
        # Map building types to resources
        production_grants = {
            'farm': {'resource': 'food', 'amount': 5},
            'mine': {'resource': 'raw_materials', 'amount': 5},
            'electrical_factory': {'resource': 'electrical_goods', 'amount': 5},
            'medical_factory': {'resource': 'medical_goods', 'amount': 5}
        }
        
        grant_info = production_grants.get(building_type)
        if not grant_info:
            raise ValueError(f"Invalid building type: {building_type}")
        
        required_resource = grant_info['resource']
        base_amount = grant_info['amount']
        required_amount = base_amount * building_count * 1.0  # Normal difficulty
        
        # Check bank inventory from game_state
        if game.game_state and 'bank_inventory' in game.game_state:
            bank_inventory = game.game_state.get('bank_inventory', {})
            current_inventory = bank_inventory.get(required_resource, 0)
            
            if current_inventory < required_amount:
                raise ValueError(
                    f"Bank does not have enough {required_resource}. "
                    f"Required: {int(required_amount)}, Available: {int(current_inventory)}"
                )
        
        challenge = Challenge(
            game_session_id=game.id,
            player_id=player_id,
            building_type=building_type,
            building_name=building_name,
            team_number=team_number,
            has_school=has_school,
            status=ChallengeStatus.REQUESTED,
            requested_at=datetime.utcnow()
        )
        
        self.db.add(challenge)
        self.db.commit()
        self.db.refresh(challenge)
        
        # Broadcast to all connected clients (especially host/banker)
        await ws_manager.broadcast_challenge_requested(
            game_code.upper(),
            self.serialize_challenge(challenge)
        )
        
        return challenge
    
    async def assign_challenge(
        self,
        challenge_id: int,
        challenge_type: str,
        challenge_description: str,
        target_number: int
    ) -> Challenge:
        """
        Assign a challenge to a player (host/banker action).
        
        Args:
            challenge_id: ID of the challenge to assign
            challenge_type: Type of physical challenge (push_ups, etc.)
            challenge_description: Full description ("20 Push-ups")
            target_number: Target count
        
        Returns:
            Updated Challenge object with assigned_at timestamp
        """
        challenge = self.db.query(Challenge).filter(
            Challenge.id == challenge_id
        ).first()
        
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")
        
        if challenge.status != ChallengeStatus.REQUESTED:
            raise ValueError(f"Challenge {challenge_id} is not in REQUESTED state")
        
        challenge.status = ChallengeStatus.ASSIGNED
        challenge.challenge_type = challenge_type
        challenge.challenge_description = challenge_description
        challenge.target_number = target_number
        challenge.assigned_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(challenge)
        
        # Broadcast to all connected clients
        game = challenge.game_session
        await ws_manager.broadcast_challenge_assigned(
            game_code=game.game_code,
            challenge_data=self.serialize_challenge(challenge, include_time_remaining=True)
        )
        
        # Send notification to the team
        player = challenge.player
        if player and player.group_number:
            challenge_type_name = challenge_type.replace('_', ' ').title()
            notification_message = f"Challenge assigned: {challenge_description} for {challenge.building_type.replace('_', ' ').title()}"
            
            await ws_manager.send_to_team(
                game_code=game.game_code,
                team_number=player.group_number,
                message={
                    "type": "notification",
                    "message": notification_message,
                    "notification_type": "challenge_assigned",
                    "challenge_data": self.serialize_challenge(challenge, include_time_remaining=True)
                },
                db_session=self.db
            )
        
        return challenge
    
    async def complete_challenge(self, challenge_id: int) -> Challenge:
        """
        Mark a challenge as completed.
        
        Args:
            challenge_id: ID of the challenge to complete
        
        Returns:
            Updated Challenge object
        """
        challenge = self.db.query(Challenge).filter(
            Challenge.id == challenge_id
        ).first()
        
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")
        
        if challenge.status != ChallengeStatus.ASSIGNED:
            raise ValueError(f"Challenge {challenge_id} is not in ASSIGNED state")
        
        challenge.status = ChallengeStatus.COMPLETED
        challenge.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(challenge)
        
        # Broadcast completion to all connected clients
        game = challenge.game_session
        await ws_manager.broadcast_challenge_completed(
            game_code=game.game_code,
            challenge_data=self.serialize_challenge(challenge)
        )
        
        # Send notification to the team
        player = challenge.player
        if player and player.group_number:
            building_name = challenge.building_type.replace('_', ' ').title()
            
            # Determine the resource and amount earned
            production_grants = {
                'farm': {'resource': 'food', 'amount': 5},
                'mine': {'resource': 'raw_materials', 'amount': 5},
                'electrical_factory': {'resource': 'electrical_goods', 'amount': 5},
                'medical_factory': {'resource': 'medical_goods', 'amount': 5}
            }
            
            grant_info = production_grants.get(challenge.building_type, {'resource': 'resources', 'amount': 5})
            resource_name = grant_info['resource'].replace('_', ' ').title()
            resource_amount = grant_info['amount']
            
            notification_message = f"✅ {player.player_name} completed {challenge.challenge_description} and earned {resource_amount} {resource_name}!"
            
            await ws_manager.send_to_team(
                game_code=game.game_code,
                team_number=player.group_number,
                message={
                    "type": "notification",
                    "message": notification_message,
                    "notification_type": "challenge_completed",
                    "challenge_data": self.serialize_challenge(challenge)
                },
                db_session=self.db
            )
        
        return challenge
    
    async def cancel_challenge(self, challenge_id: int) -> Challenge:
        """
        Cancel a challenge (can be requested or assigned).
        
        Args:
            challenge_id: ID of the challenge to cancel
        
        Returns:
            Updated Challenge object
        """
        challenge = self.db.query(Challenge).filter(
            Challenge.id == challenge_id
        ).first()
        
        if not challenge:
            raise ValueError(f"Challenge {challenge_id} not found")
        
        if challenge.status in [ChallengeStatus.COMPLETED, ChallengeStatus.CANCELLED]:
            raise ValueError(f"Challenge {challenge_id} is already {challenge.status.value}")
        
        challenge.status = ChallengeStatus.CANCELLED
        
        self.db.commit()
        self.db.refresh(challenge)
        
        # Broadcast cancellation to all connected clients
        game = challenge.game_session
        await ws_manager.broadcast_challenge_cancelled(
            game_code=game.game_code,
            challenge_data=self.serialize_challenge(challenge)
        )
        
        return challenge
    
    def adjust_for_pause(self, game_code: str, pause_duration_ms: int) -> Dict[str, Any]:
        """
        Adjust all active challenge timestamps to account for pause duration.
        This extends the deadline by adding the pause duration to assigned_at.
        
        Args:
            game_code: Game session code
            pause_duration_ms: Duration of pause in milliseconds
        
        Returns:
            Dict with adjustment details
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            raise ValueError(f"Game {game_code} not found")
        
        # Get all assigned challenges
        active_challenges = self.db.query(Challenge).filter(
            Challenge.game_session_id == game.id,
            Challenge.status == ChallengeStatus.ASSIGNED,
            Challenge.assigned_at.isnot(None)
        ).all()
        
        if not active_challenges:
            return {
                "success": True,
                "adjusted_count": 0,
                "pause_duration_ms": pause_duration_ms
            }
        
        pause_duration = timedelta(milliseconds=pause_duration_ms)
        adjusted_count = 0
        
        for challenge in active_challenges:
            original_time = challenge.assigned_at
            challenge.assigned_at = challenge.assigned_at + pause_duration
            adjusted_count += 1
        
        self.db.commit()
        
        return {
            "success": True,
            "adjusted_count": adjusted_count,
            "pause_duration_ms": pause_duration_ms
        }
    
    def check_and_expire_challenges(self, game_code: str) -> List[Challenge]:
        """
        Check all assigned challenges and expire those past their deadline.
        
        Args:
            game_code: Game session code
        
        Returns:
            List of expired challenges
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            raise ValueError(f"Game {game_code} not found")
        
        # Get all assigned challenges
        active_challenges = self.db.query(Challenge).filter(
            Challenge.game_session_id == game.id,
            Challenge.status == ChallengeStatus.ASSIGNED,
            Challenge.assigned_at.isnot(None)
        ).all()
        
        expired_challenges = []
        now = datetime.utcnow()
        expiry_duration = timedelta(minutes=self.CHALLENGE_DURATION_MINUTES)
        
        for challenge in active_challenges:
            deadline = challenge.assigned_at + expiry_duration
            if now >= deadline:
                challenge.status = ChallengeStatus.EXPIRED
                expired_challenges.append(challenge)
        
        if expired_challenges:
            self.db.commit()
        
        return expired_challenges
    
    def get_active_challenges(self, game_code: str) -> List[Challenge]:
        """
        Get all active (requested or assigned) challenges for a game.
        
        Args:
            game_code: Game session code
        
        Returns:
            List of active challenges
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            raise ValueError(f"Game {game_code} not found")
        
        challenges = self.db.query(Challenge).filter(
            Challenge.game_session_id == game.id,
            Challenge.status.in_([ChallengeStatus.REQUESTED, ChallengeStatus.ASSIGNED])
        ).order_by(Challenge.requested_at.desc()).all()
        
        return challenges
    
    def get_challenge_time_remaining(self, challenge: Challenge) -> Optional[int]:
        """
        Calculate remaining time for a challenge in seconds.
        
        Args:
            challenge: Challenge object
        
        Returns:
            Remaining seconds, or None if not assigned
        """
        if challenge.status != ChallengeStatus.ASSIGNED or not challenge.assigned_at:
            return None
        
        now = datetime.utcnow()
        expiry_duration = timedelta(minutes=self.CHALLENGE_DURATION_MINUTES)
        deadline = challenge.assigned_at + expiry_duration
        remaining = deadline - now
        
        return max(0, int(remaining.total_seconds()))
    
    def serialize_challenge(self, challenge: Challenge, include_time_remaining: bool = False) -> Dict[str, Any]:
        """
        Serialize a challenge to a dict for API responses.
        
        Args:
            challenge: Challenge object
            include_time_remaining: Whether to include calculated time remaining
        
        Returns:
            Dict representation of challenge
        """
        # Get player name from relationship
        player_name = challenge.player.player_name if challenge.player else "Unknown"
        
        data = {
            "id": challenge.id,
            "game_session_id": challenge.game_session_id,
            "player_id": challenge.player_id,
            "player_name": player_name,
            "building_type": challenge.building_type,
            "building_name": challenge.building_name,
            "team_number": challenge.team_number,
            "has_school": challenge.has_school,
            "challenge_type": challenge.challenge_type,
            "challenge_description": challenge.challenge_description,
            "target_number": challenge.target_number,
            "status": challenge.status.value,
            "requested_at": challenge.requested_at.isoformat() if challenge.requested_at else None,
            "assigned_at": challenge.assigned_at.isoformat() if challenge.assigned_at else None,
            "completed_at": challenge.completed_at.isoformat() if challenge.completed_at else None,
            "timestamp": challenge.requested_at.isoformat() if challenge.requested_at else None,  # For frontend compatibility
            "start_time": int(challenge.assigned_at.timestamp() * 1000) if challenge.assigned_at else None,  # Milliseconds for JS
        }
        
        if include_time_remaining:
            data["time_remaining_seconds"] = self.get_challenge_time_remaining(challenge)
        
        return data
