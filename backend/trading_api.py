"""
Trading API endpoints for The Trading Game
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

from database import get_db
from models import GameSession, GameStatus
from trading_system import TradingManager, DynamicPricingSystem
from websocket_manager import manager


router = APIRouter(prefix="/api/v2/trading", tags=["Trading"])


# ==================== Request/Response Models ====================

class BankTradeRequest(BaseModel):
    """Request to trade with the bank"""
    resource: str = Field(..., description="Resource to trade")
    amount: int = Field(..., gt=0, description="Amount to trade")
    trade_type: str = Field(..., pattern="^(buy|sell)$", description="buy or sell")
    team_number: int = Field(..., ge=1, description="Team number")


class BankTradeResponse(BaseModel):
    """Response from bank trade"""
    success: bool
    message: str
    total_cost: Optional[float] = None
    new_resources: Optional[Dict[str, int]] = None
    new_prices: Optional[Dict[str, Any]] = None


class TeamTradeOfferRequest(BaseModel):
    """Request to create a team trade offer"""
    from_team: int = Field(..., ge=1, description="Team making the offer")
    to_team: int = Field(..., ge=1, description="Team receiving the offer")
    offering: Dict[str, int] = Field(..., description="Resources offered")
    requesting: Dict[str, int] = Field(..., description="Resources requested")
    message: Optional[str] = Field(None, description="Optional message")


class CounterOfferRequest(BaseModel):
    """Request to counter a trade offer"""
    offering: Dict[str, int] = Field(..., description="Counter offer resources")
    requesting: Dict[str, int] = Field(..., description="Counter requested resources")
    message: Optional[str] = Field(None, description="Optional message")


class PriceHistoryResponse(BaseModel):
    """Price history for a resource"""
    resource: Optional[str] = None
    history: List[Dict[str, Any]]


# ==================== Helper Functions ====================

def get_trading_manager(game: GameSession) -> TradingManager:
    """Get or create trading manager for a game"""
    if not game.game_state:
        game.game_state = {}
    
    if "trading_system" not in game.game_state:
        # Initialize new trading system
        trading_manager = TradingManager()
        game.game_state["trading_system"] = trading_manager.to_dict()
        flag_modified(game, "game_state")
    else:
        # Load existing trading system
        trading_manager = TradingManager.from_dict(game.game_state["trading_system"])
    
    return trading_manager


def save_trading_manager(game: GameSession, trading_manager: TradingManager, db: Session):
    """Save trading manager state to game"""
    game.game_state["trading_system"] = trading_manager.to_dict()
    flag_modified(game, "game_state")
    db.commit()


# ==================== Bank Trading Endpoints ====================

@router.get("/games/{game_code}/bank/prices")
async def get_bank_prices(
    game_code: str,
    db: Session = Depends(get_db)
):
    """Get current bank prices for all resources"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    trading_manager = get_trading_manager(game)
    prices = trading_manager.pricing_system.get_all_prices()
    
    return {
        "game_code": game_code.upper(),
        "prices": prices
    }


@router.get("/games/{game_code}/bank/price-history")
async def get_price_history(
    game_code: str,
    resource: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get price history for charting"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    trading_manager = get_trading_manager(game)
    history = trading_manager.pricing_system.get_price_history(resource=resource, limit=limit)
    
    return PriceHistoryResponse(
        resource=resource,
        history=history
    )


@router.post("/games/{game_code}/bank/trade", response_model=BankTradeResponse)
async def execute_bank_trade(
    game_code: str,
    request: BankTradeRequest,
    db: Session = Depends(get_db)
):
    """Execute a trade with the bank"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game.status not in [GameStatus.IN_PROGRESS, GameStatus.PAUSED]:
        raise HTTPException(status_code=400, detail="Game must be in progress to trade")
    
    # Get team resources
    if "teams" not in game.game_state:
        raise HTTPException(status_code=400, detail="Game not properly initialized")
    
    team_key = str(request.team_number)
    if team_key not in game.game_state["teams"]:
        raise HTTPException(status_code=404, detail=f"Team {request.team_number} not found")
    
    team_resources = game.game_state["teams"][team_key].get("resources", {})
    
    # Execute trade
    trading_manager = get_trading_manager(game)
    success, error_msg, new_resources, total_cost = trading_manager.execute_bank_trade(
        team_resources=team_resources,
        resource=request.resource,
        amount=request.amount,
        trade_type=request.trade_type
    )
    
    if not success:
        return BankTradeResponse(
            success=False,
            message=error_msg or "Trade failed"
        )
    
    # Update team resources in game state
    game.game_state["teams"][team_key]["resources"] = new_resources
    
    # Save trading manager and game state
    save_trading_manager(game, trading_manager, db)
    
    # Get updated prices
    new_prices = trading_manager.pricing_system.get_all_prices()
    
    # Broadcast trade event
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "event",
        "event_type": "bank_trade_completed",
        "data": {
            "team_number": request.team_number,
            "resource": request.resource,
            "amount": request.amount,
            "trade_type": request.trade_type,
            "total_cost": total_cost,
            "new_prices": new_prices
        }
    })
    
    return BankTradeResponse(
        success=True,
        message=f"Successfully {'bought' if request.trade_type == 'buy' else 'sold'} {request.amount} {request.resource}",
        total_cost=total_cost,
        new_resources=new_resources,
        new_prices=new_prices
    )


# ==================== Team-to-Team Trading Endpoints ====================

@router.post("/games/{game_code}/team-trade/offer")
async def create_team_trade_offer(
    game_code: str,
    request: TeamTradeOfferRequest,
    db: Session = Depends(get_db)
):
    """Create a trade offer from one team to another"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game.status not in [GameStatus.IN_PROGRESS, GameStatus.PAUSED]:
        raise HTTPException(status_code=400, detail="Game must be in progress to trade")
    
    # Validate teams exist
    if "teams" not in game.game_state:
        raise HTTPException(status_code=400, detail="Game not properly initialized")
    
    from_team_key = str(request.from_team)
    to_team_key = str(request.to_team)
    
    if from_team_key not in game.game_state["teams"]:
        raise HTTPException(status_code=404, detail=f"Team {request.from_team} not found")
    if to_team_key not in game.game_state["teams"]:
        raise HTTPException(status_code=404, detail=f"Team {request.to_team} not found")
    
    # Check if from_team has the resources they're offering
    from_team_resources = game.game_state["teams"][from_team_key].get("resources", {})
    for resource, amount in request.offering.items():
        if from_team_resources.get(resource, 0) < amount:
            raise HTTPException(
                status_code=400,
                detail=f"Team {request.from_team} has insufficient {resource}"
            )
    
    # Create trade offer
    trading_manager = get_trading_manager(game)
    offer = trading_manager.create_trade_offer(
        from_team=request.from_team,
        to_team=request.to_team,
        offering=request.offering,
        requesting=request.requesting,
        message=request.message
    )
    
    # Save trading manager
    save_trading_manager(game, trading_manager, db)
    
    # Broadcast trade offer event
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "event",
        "event_type": "team_trade_offer_created",
        "data": offer.to_dict()
    })
    
    return {
        "success": True,
        "message": "Trade offer created",
        "offer": offer.to_dict()
    }


@router.get("/games/{game_code}/team-trade/offers")
async def get_team_trade_offers(
    game_code: str,
    team_number: Optional[int] = None,
    include_completed: bool = False,
    db: Session = Depends(get_db)
):
    """Get trade offers for a team or all teams"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    trading_manager = get_trading_manager(game)
    
    if team_number:
        offers = trading_manager.get_team_trade_offers(
            team_number=team_number,
            include_completed=include_completed
        )
    else:
        # Get all offers
        offers = list(trading_manager.trade_offers.values())
        if not include_completed:
            offers = [o for o in offers if o.status.value in ["pending", "countered"]]
    
    return {
        "game_code": game_code.upper(),
        "offers": [offer.to_dict() for offer in offers]
    }


@router.post("/games/{game_code}/team-trade/{offer_id}/counter")
async def counter_team_trade_offer(
    game_code: str,
    offer_id: str,
    request: CounterOfferRequest,
    db: Session = Depends(get_db)
):
    """Counter a trade offer"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    trading_manager = get_trading_manager(game)
    offer = trading_manager.get_trade_offer(offer_id)
    
    if not offer:
        raise HTTPException(status_code=404, detail="Trade offer not found")
    
    if offer.status.value not in ["pending", "countered"]:
        raise HTTPException(status_code=400, detail=f"Cannot counter {offer.status.value} offer")
    
    # Create counter offer
    offer.counter(
        new_offering=request.offering,
        new_requesting=request.requesting,
        message=request.message
    )
    
    # Save trading manager
    save_trading_manager(game, trading_manager, db)
    
    # Broadcast counter offer event
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "event",
        "event_type": "team_trade_offer_countered",
        "data": offer.to_dict()
    })
    
    return {
        "success": True,
        "message": "Counter offer created",
        "offer": offer.to_dict()
    }


@router.post("/games/{game_code}/team-trade/{offer_id}/accept")
async def accept_team_trade_offer(
    game_code: str,
    offer_id: str,
    db: Session = Depends(get_db)
):
    """Accept a trade offer and execute the trade"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    trading_manager = get_trading_manager(game)
    offer = trading_manager.get_trade_offer(offer_id)
    
    if not offer:
        raise HTTPException(status_code=404, detail="Trade offer not found")
    
    if offer.status.value not in ["pending", "countered"]:
        raise HTTPException(status_code=400, detail=f"Cannot accept {offer.status.value} offer")
    
    # Get team resources
    from_team_key = str(offer.from_team)
    to_team_key = str(offer.to_team)
    
    from_team_resources = game.game_state["teams"][from_team_key].get("resources", {})
    to_team_resources = game.game_state["teams"][to_team_key].get("resources", {})
    
    # Execute trade
    success, error_msg, new_from_resources, new_to_resources = trading_manager.execute_team_trade(
        offer_id=offer_id,
        from_team_resources=from_team_resources,
        to_team_resources=to_team_resources
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=error_msg or "Trade execution failed")
    
    # Update team resources
    game.game_state["teams"][from_team_key]["resources"] = new_from_resources
    game.game_state["teams"][to_team_key]["resources"] = new_to_resources
    
    # Save trading manager and game state
    save_trading_manager(game, trading_manager, db)
    
    # Broadcast trade completed event
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "event",
        "event_type": "team_trade_completed",
        "data": {
            "offer_id": offer_id,
            "from_team": offer.from_team,
            "to_team": offer.to_team,
            "offer": offer.to_dict()
        }
    })
    
    return {
        "success": True,
        "message": "Trade completed successfully",
        "offer": offer.to_dict()
    }


@router.post("/games/{game_code}/team-trade/{offer_id}/reject")
async def reject_team_trade_offer(
    game_code: str,
    offer_id: str,
    db: Session = Depends(get_db)
):
    """Reject a trade offer"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    trading_manager = get_trading_manager(game)
    offer = trading_manager.get_trade_offer(offer_id)
    
    if not offer:
        raise HTTPException(status_code=404, detail="Trade offer not found")
    
    if offer.status.value not in ["pending", "countered"]:
        raise HTTPException(status_code=400, detail=f"Cannot reject {offer.status.value} offer")
    
    # Reject offer
    offer.reject()
    
    # Save trading manager
    save_trading_manager(game, trading_manager, db)
    
    # Broadcast rejection event
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "event",
        "event_type": "team_trade_offer_rejected",
        "data": offer.to_dict()
    })
    
    return {
        "success": True,
        "message": "Trade offer rejected",
        "offer": offer.to_dict()
    }


@router.delete("/games/{game_code}/team-trade/{offer_id}")
async def cancel_team_trade_offer(
    game_code: str,
    offer_id: str,
    db: Session = Depends(get_db)
):
    """Cancel a trade offer"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    trading_manager = get_trading_manager(game)
    offer = trading_manager.get_trade_offer(offer_id)
    
    if not offer:
        raise HTTPException(status_code=404, detail="Trade offer not found")
    
    if offer.status.value not in ["pending", "countered"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel {offer.status.value} offer")
    
    # Cancel offer
    offer.cancel()
    
    # Save trading manager
    save_trading_manager(game, trading_manager, db)
    
    # Broadcast cancellation event
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "event",
        "event_type": "team_trade_offer_cancelled",
        "data": offer.to_dict()
    })
    
    return {
        "success": True,
        "message": "Trade offer cancelled",
        "offer": offer.to_dict()
    }
