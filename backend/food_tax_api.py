"""
Food Tax API - REST endpoints for food tax management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from database import get_db
from food_tax_manager import FoodTaxManager
from models import GameSession, GameStatus

router = APIRouter(prefix="/api/v2/food-tax", tags=["food-tax"])


@router.get("/{game_code}/status")
def get_food_tax_status(
    game_code: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current food tax status for all teams.
    
    Returns information about next tax due, tax amounts, and statistics.
    """
    manager = FoodTaxManager(db)
    return manager.get_tax_status(game_code)


@router.post("/{game_code}/adjust-for-pause")
def adjust_for_pause(
    game_code: str,
    pause_duration_ms: int = Query(..., description="Pause duration in milliseconds"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Adjust food tax timings after game is resumed from pause.
    
    This endpoint should be called when the game is resumed to add
    the pause duration to all pending tax due times.
    """
    manager = FoodTaxManager(db)
    return manager.adjust_for_pause(game_code, pause_duration_ms)


@router.post("/{game_code}/force-apply")
def force_apply_tax(
    game_code: str,
    team_number: str = Query(..., description="Team number to apply tax to"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually trigger food tax for a specific team.
    
    This is an optional endpoint for banker to manually apply tax
    if needed (e.g., for testing or special circumstances).
    """
    manager = FoodTaxManager(db)
    return manager.force_apply_tax(game_code, team_number)


@router.post("/{game_code}/force-apply-all")
async def force_apply_tax_all(
    game_code: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually trigger food tax for ALL teams.
    
    This endpoint is used when the host or banker presses the 
    "Apply Food Tax (All Nations)" button.
    """
    manager = FoodTaxManager(db)
    return manager.force_apply_tax_all_teams(game_code)


@router.post("/{game_code}/initialize")
def initialize_food_tax(
    game_code: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Initialize food tax tracking for a game.
    
    This is typically called automatically when the game starts,
    but can be called manually if needed.
    """
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    manager = FoodTaxManager(db)
    manager.initialize_food_tax_tracking(game)
    
    return {
        "success": True,
        "message": "Food tax tracking initialized",
        "game_code": game_code.upper()
    }
