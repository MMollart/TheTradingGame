"""
Additional Challenge Management API Endpoints

These endpoints use the ChallengeManager service for cleaner, more reliable challenge operations.
Add these to main.py or import them.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from database import get_db
from challenge_manager import ChallengeManager
from websocket_manager import manager as ws_manager


router = APIRouter(prefix="/api/v2/challenges", tags=["challenges-v2"])


# Request/Response Models
class ChallengeRequestCreate(BaseModel):
    player_id: int
    building_type: str
    building_name: str
    team_number: int
    has_school: bool


class ChallengeAssignment(BaseModel):
    challenge_type: str
    challenge_description: str
    target_number: int


class PauseAdjustment(BaseModel):
    pause_duration_ms: int


class ChallengeResponse(BaseModel):
    id: int
    game_session_id: int
    player_id: int
    building_type: str
    building_name: str
    team_number: int
    has_school: bool
    challenge_type: Optional[str]
    challenge_description: Optional[str]
    target_number: Optional[int]
    status: str
    requested_at: Optional[str]
    assigned_at: Optional[str]
    completed_at: Optional[str]
    time_remaining_seconds: Optional[int] = None


# Endpoints
@router.post("/{game_code}/request", response_model=ChallengeResponse)
async def create_challenge_request(
    game_code: str,
    request: ChallengeRequestCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new challenge request from a player.
    
    This endpoint is called when a player requests a production challenge.
    WebSocket broadcast: challenge_requested event sent to all clients.
    """
    try:
        manager = ChallengeManager(db)
        challenge = await manager.create_challenge_request(
            game_code=game_code,
            player_id=request.player_id,
            building_type=request.building_type,
            building_name=request.building_name,
            team_number=request.team_number,
            has_school=request.has_school
        )
        
        return manager.serialize_challenge(challenge)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_code}/{challenge_id}/assign", response_model=ChallengeResponse)
async def assign_challenge(
    game_code: str,
    challenge_id: int,
    assignment: ChallengeAssignment,
    db: Session = Depends(get_db)
):
    """
    Assign a challenge to a player (host/banker action).
    
    This endpoint is called when a host or banker assigns a physical challenge.
    WebSocket broadcast: challenge_assigned event sent to all clients.
    """
    try:
        manager = ChallengeManager(db)
        challenge = await manager.assign_challenge(
            challenge_id=challenge_id,
            challenge_type=assignment.challenge_type,
            challenge_description=assignment.challenge_description,
            target_number=assignment.target_number
        )
        
        return manager.serialize_challenge(challenge, include_time_remaining=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_code}/{challenge_id}/complete", response_model=ChallengeResponse)
async def complete_challenge(
    game_code: str,
    challenge_id: int,
    db: Session = Depends(get_db)
):
    """
    Mark a challenge as completed (host/banker action).
    
    This endpoint is called when a host or banker confirms challenge completion.
    WebSocket broadcast: challenge_completed event sent to all clients.
    """
    try:
        manager = ChallengeManager(db)
        challenge = await manager.complete_challenge(challenge_id)
        
        return manager.serialize_challenge(challenge)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_code}/{challenge_id}/cancel", response_model=ChallengeResponse)
async def cancel_challenge(
    game_code: str,
    challenge_id: int,
    db: Session = Depends(get_db)
):
    """
    Cancel a challenge (host/banker action).
    
    This endpoint is called when a host or banker cancels a challenge.
    WebSocket broadcast: challenge_cancelled event sent to all clients.
    """
    try:
        manager = ChallengeManager(db)
        challenge = await manager.cancel_challenge(challenge_id)
        
        return manager.serialize_challenge(challenge)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_code}/adjust-for-pause")
def adjust_challenges_for_pause(
    game_code: str,
    adjustment: PauseAdjustment,
    db: Session = Depends(get_db)
):
    """
    Adjust all active challenge timestamps to account for game pause.
    
    This endpoint is called when the game resumes from pause.
    It extends the deadline for all active challenges by the pause duration.
    """
    try:
        manager = ChallengeManager(db)
        result = manager.adjust_for_pause(game_code, adjustment.pause_duration_ms)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_code}/check-expiry")
def check_challenge_expiry(
    game_code: str,
    db: Session = Depends(get_db)
):
    """
    Check and expire any challenges past their deadline.
    
    This endpoint can be called periodically or on-demand to ensure
    expired challenges are properly marked.
    """
    try:
        manager = ChallengeManager(db)
        expired = manager.check_and_expire_challenges(game_code)
        return {
            "success": True,
            "expired_count": len(expired),
            "expired_challenge_ids": [c.id for c in expired]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{game_code}/active", response_model=List[ChallengeResponse])
def get_active_challenges(
    game_code: str,
    include_time_remaining: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get all active (requested or assigned) challenges for a game.
    
    This endpoint returns the current state of all challenges that are
    either pending assignment or currently active.
    """
    try:
        manager = ChallengeManager(db)
        challenges = manager.get_active_challenges(game_code)
        return [
            manager.serialize_challenge(c, include_time_remaining=include_time_remaining)
            for c in challenges
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
