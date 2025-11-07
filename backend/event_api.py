"""
Event API - REST API endpoints for game events

Provides endpoints for banker/host to:
- Trigger events with severity levels
- View active events
- Cure plague
- Complete automation breakthrough
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from database import get_db
from models import GameSession, GameStatus, EventType
from event_manager import EventManager
from websocket_manager import manager as ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/events", tags=["events"])


# ==================== Request/Response Models ====================

class TriggerEventRequest(BaseModel):
    """Request to trigger a game event"""
    event_type: str = Field(..., description="Type of event (earthquake, fire, drought, etc.)")
    severity: int = Field(3, ge=1, le=5, description="Event severity (1-5)")
    target_team: Optional[str] = Field(None, description="Target team for team-specific events")


class EventResponse(BaseModel):
    """Response for event operations"""
    success: bool
    message: str
    event_id: Optional[int] = None
    event_data: Optional[Dict[str, Any]] = None


class ActiveEventsResponse(BaseModel):
    """Response for active events list"""
    events: List[Dict[str, Any]]


class CurePlagueRequest(BaseModel):
    """Request to cure plague for a team"""
    team_number: str


class CompleteAutomationRequest(BaseModel):
    """Request to complete automation breakthrough payment"""
    team_number: str


# ==================== Event Trigger Endpoints ====================

@router.post("/games/{game_code}/trigger", response_model=EventResponse)
async def trigger_event(
    game_code: str,
    request: TriggerEventRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger a game event (banker/host only).
    
    Available event types:
    - earthquake: Destroys random buildings
    - fire: Destroys electrical factories
    - drought: Reduces farm/mine production for 2 cycles
    - plague: Contagious production penalty until cured
    - blizzard: Increases food tax and reduces production for 2 cycles
    - tornado: Destroys percentage of all resources
    - economic_recession: Increases bank prices and building costs
    - automation_breakthrough: Offers production bonus for payment
    """
    game_code = game_code.upper()
    
    # Get game
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code
    ).first()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    
    if game.status != GameStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game must be in progress to trigger events"
        )
    
    # Create event manager
    event_mgr = EventManager(db)
    
    # Trigger appropriate event
    event_type = request.event_type.lower()
    event = None
    
    try:
        if event_type == "earthquake":
            event = event_mgr.trigger_earthquake(game, request.severity)
            event_message = f"🏚️ Earthquake! Buildings destroyed across all nations. Severity: {request.severity}"
            
        elif event_type == "fire":
            event = event_mgr.trigger_fire(game, request.severity)
            event_message = f"🔥 Fire! Electrical factories damaged across all nations. Severity: {request.severity}"
            
        elif event_type == "drought":
            event = event_mgr.trigger_drought(game, request.severity)
            event_message = f"💧 Drought! Farm and mine production reduced for 2 tax cycles. Severity: {request.severity}"
            
        elif event_type == "plague":
            event = event_mgr.trigger_plague(game, request.severity)
            if event:
                infected_teams = event.event_data.get('infected_teams', [])
                event_message = f"🦠 Plague! {len(infected_teams)} nations infected. Contagious and reduces production. Severity: {request.severity}"
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No teams available to infect"
                )
            
        elif event_type == "blizzard":
            event = event_mgr.trigger_blizzard(game, request.severity)
            event_message = f"❄️ Blizzard! Food tax increased and production reduced for 2 cycles. Severity: {request.severity}"
            
        elif event_type == "tornado":
            event = event_mgr.trigger_tornado(game, request.severity)
            event_message = f"🌪️ Tornado! Resources destroyed across all nations. Severity: {request.severity}"
            
        elif event_type == "economic_recession":
            event = event_mgr.trigger_economic_recession(game, request.severity)
            event_message = f"📉 Economic Recession! Bank prices and building costs increased. Severity: {request.severity}"
            
        elif event_type == "automation_breakthrough":
            event = event_mgr.trigger_automation_breakthrough(game, request.severity, request.target_team)
            target = event.event_data.get('target_team', 'Unknown')
            event_message = f"🤖 Automation Breakthrough! Team {target} offered factory production bonus. Severity: {request.severity}"
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown event type: {event_type}"
            )
        
        # Broadcast event to all players
        await ws_manager.broadcast_to_game(game_code, {
            "type": "event",
            "event_type": "game_event_triggered",
            "data": {
                "event_id": event.id,
                "event_type": event_type,
                "category": event.event_category.value,
                "severity": request.severity,
                "message": event_message,
                "event_data": event.event_data
            }
        })
        
        logger.info(f"Event {event_type} (severity {request.severity}) triggered in {game_code}")
        
        return EventResponse(
            success=True,
            message=event_message,
            event_id=event.id,
            event_data=event.event_data
        )
    
    except Exception as e:
        logger.error(f"Error triggering event {event_type} in {game_code}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger event: {str(e)}"
        )


@router.get("/games/{game_code}/active", response_model=ActiveEventsResponse)
async def get_active_events(
    game_code: str,
    db: Session = Depends(get_db)
):
    """
    Get list of all active events for a game.
    """
    game_code = game_code.upper()
    
    # Get game
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code
    ).first()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    
    # Get active events
    event_mgr = EventManager(db)
    events = event_mgr.get_active_events(game)
    
    return ActiveEventsResponse(events=events)


@router.post("/games/{game_code}/cure-plague", response_model=EventResponse)
async def cure_plague(
    game_code: str,
    request: CurePlagueRequest,
    db: Session = Depends(get_db)
):
    """
    Cure plague for a specific team (after they pay medicine to bank).
    """
    game_code = game_code.upper()
    
    # Get game
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code
    ).first()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    
    # Cure plague
    event_mgr = EventManager(db)
    success = event_mgr.cure_plague(game, request.team_number)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team is not infected or plague is not active"
        )
    
    # Broadcast cure event
    await ws_manager.broadcast_to_game(game_code, {
        "type": "event",
        "event_type": "plague_cured",
        "data": {
            "team": request.team_number,
            "message": f"Team {request.team_number} has been cured of the plague!"
        }
    })
    
    logger.info(f"Plague cured for team {request.team_number} in {game_code}")
    
    return EventResponse(
        success=True,
        message=f"Plague cured for team {request.team_number}"
    )


@router.post("/games/{game_code}/complete-automation", response_model=EventResponse)
async def complete_automation_breakthrough(
    game_code: str,
    request: CompleteAutomationRequest,
    db: Session = Depends(get_db)
):
    """
    Complete automation breakthrough payment and activate bonus.
    """
    game_code = game_code.upper()
    
    # Get game
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code
    ).first()
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found"
        )
    
    # Complete automation breakthrough
    event_mgr = EventManager(db)
    success = event_mgr.complete_automation_breakthrough(game, request.team_number)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Automation breakthrough not available or already completed"
        )
    
    # Broadcast completion event
    await ws_manager.broadcast_to_game(game_code, {
        "type": "event",
        "event_type": "automation_activated",
        "data": {
            "team": request.team_number,
            "message": f"🤖 Automation activated for Team {request.team_number}! Factory production boosted!"
        }
    })
    
    logger.info(f"Automation breakthrough completed for team {request.team_number} in {game_code}")
    
    return EventResponse(
        success=True,
        message=f"Automation breakthrough activated for team {request.team_number}"
    )
