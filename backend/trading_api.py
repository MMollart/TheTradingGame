"""
Trading API - REST endpoints for bank and team-to-team trading
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from pydantic import BaseModel

from database import get_db
from models import GameSession, Player, TradeOffer, TradeOfferStatus
from pricing_manager import PricingManager
from trade_manager import TradeManager
from game_logic import GameLogic
from websocket_manager import manager
from sqlalchemy.orm.attributes import flag_modified


router = APIRouter(prefix="/api/v2/trading", tags=["trading"])


# ==================== Request/Response Models ====================

class BankTradeRequest(BaseModel):
    """Request model for bank trades"""
    game_code: str
    team_number: int
    player_id: int
    resource_type: str
    quantity: int
    is_buying: bool  # True = team buys from bank, False = team sells to bank


class TeamTradeRequest(BaseModel):
    """Request model for initiating team-to-team trade"""
    game_code: str
    from_team_number: int
    to_team_number: int
    player_id: int
    offered_resources: Dict[str, int]
    requested_resources: Dict[str, int]


class CounterOfferRequest(BaseModel):
    """Request model for counter-offers"""
    player_id: int
    counter_offered_resources: Dict[str, int]
    counter_requested_resources: Dict[str, int]


class TradeActionRequest(BaseModel):
    """Request model for accepting/rejecting trades"""
    player_id: int
    accept_counter: Optional[bool] = False


# ==================== Bank Trading Endpoints ====================

@router.post("/{game_code}/bank/initialize-prices")
async def initialize_bank_prices(game_code: str, db: Session = Depends(get_db)):
    """
    Initialize bank prices for a game.
    Called when game starts.
    """
    pricing_mgr = PricingManager(db)
    
    try:
        prices = pricing_mgr.initialize_bank_prices(game_code)
        
        # Store prices in game_state
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        
        if not game.game_state:
            game.game_state = {}
        
        game.game_state['bank_prices'] = prices
        flag_modified(game, 'game_state')
        db.commit()
        
        # Broadcast price initialization
        await manager.broadcast_to_game(game_code.upper(), {
            "type": "event",
            "event_type": "bank_prices_initialized",
            "data": {
                "prices": prices
            }
        })
        
        return {
            "success": True,
            "prices": prices
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{game_code}/bank/trade")
async def execute_bank_trade(
    game_code: str,
    trade: BankTradeRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    Execute a trade with the bank.
    Adjusts prices based on supply/demand after the trade.
    """
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Validate player
    player = db.query(Player).filter(
        Player.id == trade.player_id,
        Player.game_session_id == game.id
    ).first()
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if player.group_number != trade.team_number:
        raise HTTPException(status_code=403, detail="Player does not belong to this team")
    
    # Get current prices from game_state (or fall back to banker's player_state for legacy games)
    current_prices = None
    if game.game_state and 'bank_prices' in game.game_state:
        current_prices = game.game_state['bank_prices']
    else:
        # Legacy: try banker's player_state
        banker = db.query(Player).filter(
            Player.game_session_id == game.id,
            Player.role == "banker"
        ).first()
        
        if banker and banker.player_state:
            current_prices = banker.player_state.get('bank_prices', {})
    
    if not current_prices:
        raise HTTPException(status_code=400, detail="Bank prices not initialized. Please initialize prices first.")
    
    # Calculate trade cost
    pricing_mgr = PricingManager(db)
    try:
        currency_cost = pricing_mgr.calculate_trade_cost(
            trade.resource_type,
            trade.quantity,
            trade.is_buying,
            current_prices
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get team state
    team_state = game.game_state.get('teams', {}).get(str(trade.team_number), {})
    team_resources = team_state.get('resources', {})
    
    # Validate team can afford the trade
    if trade.is_buying:
        # Team is buying from bank: need currency
        if team_resources.get('currency', 0) < currency_cost:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient currency. Need {currency_cost}, have {team_resources.get('currency', 0)}"
            )
    else:
        # Team is selling to bank: need the resource
        if team_resources.get(trade.resource_type, 0) < trade.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient {trade.resource_type}. Need {trade.quantity}, have {team_resources.get(trade.resource_type, 0)}"
            )
    
    # Execute the trade (bank has infinite inventory in banker-less mode)
    if trade.is_buying:
        # Team buys from bank
        team_resources['currency'] = team_resources.get('currency', 0) - currency_cost
        team_resources[trade.resource_type] = team_resources.get(trade.resource_type, 0) + trade.quantity
    else:
        # Team sells to bank
        team_resources[trade.resource_type] = team_resources.get(trade.resource_type, 0) - trade.quantity
        team_resources['currency'] = team_resources.get('currency', 0) + currency_cost
    
    # Update team resources in game state
    game.game_state['teams'][str(trade.team_number)]['resources'] = team_resources
    flag_modified(game, 'game_state')
    
    # Adjust prices based on this trade (considering all resources)
    updated_prices = pricing_mgr.adjust_all_prices_after_trade(
        game_code,
        trade.resource_type,
        trade.quantity,
        trade.is_buying,
        current_prices
    )
    
    # Store updated prices in game_state
    game.game_state['bank_prices'] = updated_prices
    flag_modified(game, 'game_state')
    
    db.commit()
    
    # Broadcast trade completion and price updates
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "event",
        "event_type": "bank_trade_completed",
        "data": {
            "team_number": trade.team_number,
            "resource_type": trade.resource_type,
            "quantity": trade.quantity,
            "is_buying": trade.is_buying,
            "currency_cost": currency_cost,
            "new_prices": updated_prices,
            "team_resources": team_resources
        }
    })
    
    return {
        "success": True,
        "currency_cost": currency_cost,
        "new_prices": updated_prices,
        "team_resources": team_resources
    }


@router.get("/{game_code}/bank/prices")
async def get_bank_prices(game_code: str, db: Session = Depends(get_db)):
    """Get current bank prices"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Try to get prices from game_state first (preferred location)
    if game.game_state and 'bank_prices' in game.game_state:
        current_prices = game.game_state['bank_prices']
    else:
        # Fall back to banker's player_state (legacy location)
        banker = db.query(Player).filter(
            Player.game_session_id == game.id,
            Player.role == "banker"
        ).first()
        
        if banker and banker.player_state and 'bank_prices' in banker.player_state:
            current_prices = banker.player_state['bank_prices']
        else:
            raise HTTPException(status_code=400, detail="Bank prices not initialized. Please initialize prices first.")
    
    return {
        "prices": current_prices
    }


@router.get("/{game_code}/bank/price-history")
async def get_price_history(
    game_code: str,
    resource_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get price history for charting"""
    pricing_mgr = PricingManager(db)
    
    history = pricing_mgr.get_price_history(game_code, resource_type, limit)
    
    return {
        "history": history
    }


# ==================== Team Trading Endpoints ====================

@router.post("/{game_code}/team/offer")
async def create_team_trade_offer(
    game_code: str,
    trade_request: TeamTradeRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Create a new team-to-team trade offer"""
    trade_mgr = TradeManager(db)
    
    try:
        trade_offer = trade_mgr.create_trade_offer(
            game_code,
            trade_request.from_team_number,
            trade_request.to_team_number,
            trade_request.player_id,
            trade_request.offered_resources,
            trade_request.requested_resources
        )
        
        # Send notification only to the receiving team
        await manager.send_to_team(game_code.upper(), trade_offer.to_team_number, {
            "type": "notification",
            "event_type": "trade_offer_received",
            "data": {
                "trade_id": trade_offer.id,
                "from_team": trade_offer.from_team_number,
                "to_team": trade_offer.to_team_number,
                "offered": trade_offer.offered_resources,
                "requested": trade_offer.requested_resources,
                "message": f"Team {trade_offer.from_team_number} has sent you a trade offer!"
            }
        }, db_session=db)
        
        # Send confirmation to the offering team
        await manager.send_to_team(game_code.upper(), trade_offer.from_team_number, {
            "type": "event",
            "event_type": "trade_offer_created",
            "data": {
                "trade_id": trade_offer.id,
                "from_team": trade_offer.from_team_number,
                "to_team": trade_offer.to_team_number,
                "offered": trade_offer.offered_resources,
                "requested": trade_offer.requested_resources
            }
        }, db_session=db)
        
        return {
            "success": True,
            "trade_id": trade_offer.id,
            "trade_offer": {
                "id": trade_offer.id,
                "from_team": trade_offer.from_team_number,
                "to_team": trade_offer.to_team_number,
                "offered_resources": trade_offer.offered_resources,
                "requested_resources": trade_offer.requested_resources,
                "status": trade_offer.status.value,
                "created_at": trade_offer.created_at.isoformat()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_code}/team/offer/{trade_id}/counter")
async def create_counter_offer(
    game_code: str,
    trade_id: int,
    counter_request: CounterOfferRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Create a counter-offer for an existing trade"""
    trade_mgr = TradeManager(db)
    
    try:
        trade_offer = trade_mgr.create_counter_offer(
            trade_id,
            counter_request.player_id,
            counter_request.counter_offered_resources,
            counter_request.counter_requested_resources
        )
        
        # Determine which team made the counter offer (recipient of original offer)
        player = db.query(Player).filter(Player.id == counter_request.player_id).first()
        countering_team = player.group_number
        receiving_team = trade_offer.from_team_number if countering_team == trade_offer.to_team_number else trade_offer.to_team_number
        
        # Send notification to the team that will receive the counter-offer
        await manager.send_to_team(game_code.upper(), receiving_team, {
            "type": "notification",
            "event_type": "trade_counter_received",
            "data": {
                "trade_id": trade_offer.id,
                "from_team": countering_team,
                "to_team": receiving_team,
                "counter_offered": trade_offer.counter_offered_resources,
                "counter_requested": trade_offer.counter_requested_resources,
                "message": f"Team {countering_team} has sent you a counter-offer!"
            }
        }, db_session=db)
        
        # Send confirmation to the countering team
        await manager.send_to_team(game_code.upper(), countering_team, {
            "type": "event",
            "event_type": "trade_counter_offered",
            "data": {
                "trade_id": trade_offer.id,
                "from_team": countering_team,
                "to_team": receiving_team,
                "counter_offered": trade_offer.counter_offered_resources,
                "counter_requested": trade_offer.counter_requested_resources
            }
        }, db_session=db)
        
        return {
            "success": True,
            "trade_offer": {
                "id": trade_offer.id,
                "status": trade_offer.status.value,
                "counter_offered_resources": trade_offer.counter_offered_resources,
                "counter_requested_resources": trade_offer.counter_requested_resources,
                "counter_offered_at": trade_offer.counter_offered_at.isoformat()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_code}/team/offer/{trade_id}/accept")
async def accept_trade_offer(
    game_code: str,
    trade_id: int,
    action_request: TradeActionRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Accept a trade offer"""
    trade_mgr = TradeManager(db)
    
    try:
        trade_offer, game = trade_mgr.accept_trade_offer(
            trade_id,
            action_request.player_id,
            action_request.accept_counter or False
        )
        
        # Get updated team states
        from_team_state = game.game_state['teams'][str(trade_offer.from_team_number)]
        to_team_state = game.game_state['teams'][str(trade_offer.to_team_number)]
        
        # Send notification to both teams involved in the trade
        trade_data = {
            "trade_id": trade_offer.id,
            "from_team": trade_offer.from_team_number,
            "to_team": trade_offer.to_team_number,
            "was_counter_offer": action_request.accept_counter or False,
            "team_states": {
                str(trade_offer.from_team_number): from_team_state,
                str(trade_offer.to_team_number): to_team_state
            }
        }
        
        # Notify both teams with different messages
        await manager.send_to_team(game_code.upper(), trade_offer.from_team_number, {
            "type": "notification",
            "event_type": "trade_accepted",
            "data": {
                **trade_data,
                "message": f"Your trade with Team {trade_offer.to_team_number} has been accepted!"
            }
        }, db_session=db)
        
        await manager.send_to_team(game_code.upper(), trade_offer.to_team_number, {
            "type": "notification",
            "event_type": "trade_accepted",
            "data": {
                **trade_data,
                "message": f"Your trade with Team {trade_offer.from_team_number} has been accepted!"
            }
        }, db_session=db)
        
        return {
            "success": True,
            "message": "Trade completed successfully",
            "team_states": {
                str(trade_offer.from_team_number): from_team_state,
                str(trade_offer.to_team_number): to_team_state
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_code}/team/offer/{trade_id}/reject")
async def reject_trade_offer(
    game_code: str,
    trade_id: int,
    action_request: TradeActionRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Reject a trade offer"""
    trade_mgr = TradeManager(db)
    
    try:
        trade_offer = trade_mgr.reject_trade_offer(
            trade_id,
            action_request.player_id
        )
        
        # Determine which team rejected and which team needs to be notified
        player = db.query(Player).filter(Player.id == action_request.player_id).first()
        rejecting_team = player.group_number
        other_team = trade_offer.from_team_number if rejecting_team == trade_offer.to_team_number else trade_offer.to_team_number
        
        # Send notification to the team whose offer was rejected
        await manager.send_to_team(game_code.upper(), other_team, {
            "type": "notification",
            "event_type": "trade_rejected",
            "data": {
                "trade_id": trade_offer.id,
                "from_team": trade_offer.from_team_number,
                "to_team": trade_offer.to_team_number,
                "rejecting_team": rejecting_team,
                "message": f"Team {rejecting_team} has rejected your trade offer."
            }
        }, db_session=db)
        
        # Send confirmation to the rejecting team
        await manager.send_to_team(game_code.upper(), rejecting_team, {
            "type": "event",
            "event_type": "trade_rejected",
            "data": {
                "trade_id": trade_offer.id,
                "from_team": trade_offer.from_team_number,
                "to_team": trade_offer.to_team_number
            }
        }, db_session=db)
        
        return {
            "success": True,
            "message": "Trade rejected"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_code}/team/offer/{trade_id}/cancel")
async def cancel_trade_offer(
    game_code: str,
    trade_id: int,
    action_request: TradeActionRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Cancel a trade offer"""
    trade_mgr = TradeManager(db)
    
    try:
        trade_offer = trade_mgr.cancel_trade_offer(
            trade_id,
            action_request.player_id
        )
        
        # Determine which team cancelled and which team needs to be notified
        player = db.query(Player).filter(Player.id == action_request.player_id).first()
        cancelling_team = player.group_number
        other_team = trade_offer.from_team_number if cancelling_team == trade_offer.to_team_number else trade_offer.to_team_number
        
        # Send notification to the other team
        await manager.send_to_team(game_code.upper(), other_team, {
            "type": "notification",
            "event_type": "trade_cancelled",
            "data": {
                "trade_id": trade_offer.id,
                "from_team": trade_offer.from_team_number,
                "to_team": trade_offer.to_team_number,
                "cancelling_team": cancelling_team,
                "message": f"Team {cancelling_team} has cancelled the trade offer."
            }
        }, db_session=db)
        
        # Send confirmation to the cancelling team
        await manager.send_to_team(game_code.upper(), cancelling_team, {
            "type": "event",
            "event_type": "trade_cancelled",
            "data": {
                "trade_id": trade_offer.id,
                "from_team": trade_offer.from_team_number,
                "to_team": trade_offer.to_team_number
            }
        }, db_session=db)
        
        return {
            "success": True,
            "message": "Trade cancelled"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{game_code}/team/{team_number}/offers")
async def get_team_trade_offers(
    game_code: str,
    team_number: int,
    include_completed: bool = False,
    db: Session = Depends(get_db)
):
    """Get all trade offers for a team"""
    trade_mgr = TradeManager(db)
    
    offers = trade_mgr.get_team_trade_offers(game_code, team_number, include_completed)
    
    return {
        "offers": [
            {
                "id": offer.id,
                "from_team": offer.from_team_number,
                "to_team": offer.to_team_number,
                "offered_resources": offer.offered_resources,
                "requested_resources": offer.requested_resources,
                "counter_offered_resources": offer.counter_offered_resources,
                "counter_requested_resources": offer.counter_requested_resources,
                "status": offer.status.value,
                "created_at": offer.created_at.isoformat(),
                "counter_offered_at": offer.counter_offered_at.isoformat() if offer.counter_offered_at else None
            }
            for offer in offers
        ]
    }


@router.get("/{game_code}/team/offers/all")
async def get_all_trade_offers(game_code: str, db: Session = Depends(get_db)):
    """Get all active trade offers (for host/banker view)"""
    trade_mgr = TradeManager(db)
    
    offers = trade_mgr.get_all_active_trades(game_code)
    
    return {
        "offers": [
            {
                "id": offer.id,
                "from_team": offer.from_team_number,
                "to_team": offer.to_team_number,
                "offered_resources": offer.offered_resources,
                "requested_resources": offer.requested_resources,
                "counter_offered_resources": offer.counter_offered_resources,
                "counter_requested_resources": offer.counter_requested_resources,
                "status": offer.status.value,
                "created_at": offer.created_at.isoformat(),
                "counter_offered_at": offer.counter_offered_at.isoformat() if offer.counter_offered_at else None
            }
            for offer in offers
        ]
    }
