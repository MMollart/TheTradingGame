"""
Trade Manager - Handles team-to-team trading with negotiation
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from models import GameSession, Player, TradeOffer, TradeOfferStatus
from game_logic import GameLogic


class TradeMarginCalculator:
    """Calculate trade margins for kindness scoring"""
    
    @staticmethod
    def calculate_resource_value(resources: Dict[str, int], bank_prices: Dict[str, Dict[str, int]]) -> float:
        """
        Calculate the fair market value of resources based on bank prices.
        Uses the baseline price (midpoint between buy/sell) as the reference for fairness.
        
        Args:
            resources: Dictionary of resource types and quantities
            bank_prices: Current bank prices with buy_price, sell_price, baseline
            
        Returns:
            Total value in currency units
        """
        total_value = 0.0
        for resource_type, quantity in resources.items():
            if resource_type == 'currency':
                # Currency is worth its face value
                total_value += quantity
            elif resource_type in bank_prices:
                # Use baseline as the fair market value for trade fairness calculations
                price_info = bank_prices[resource_type]
                reference_price = price_info.get('baseline', price_info.get('sell_price', 0))
                total_value += quantity * reference_price
        return total_value
    
    @staticmethod
    def calculate_trade_margin(
        offered_resources: Dict[str, int],
        requested_resources: Dict[str, int],
        bank_prices: Dict[str, Dict[str, int]]
    ) -> Dict[str, float]:
        """
        Calculate the trade margin from the perspective of the offering team.
        
        Margin formula: (value_received - value_given) / value_given
        - Negative margin = trading at a loss (generous/kind)
        - Positive margin = trading at a profit (shrewd)
        - Zero margin = fair trade
        
        Args:
            offered_resources: What the team is giving away
            requested_resources: What the team is receiving
            bank_prices: Current bank prices for reference
            
        Returns:
            Dictionary with 'margin' (float) and 'trade_value' (float)
        """
        value_given = TradeMarginCalculator.calculate_resource_value(offered_resources, bank_prices)
        value_received = TradeMarginCalculator.calculate_resource_value(requested_resources, bank_prices)
        
        # Avoid division by zero
        if value_given == 0:
            # If giving nothing, can't calculate meaningful margin
            return {'margin': 0.0, 'trade_value': value_received}
        
        # Calculate margin: positive means profit, negative means loss
        margin = (value_received - value_given) / value_given
        
        return {
            'margin': round(margin, 4),  # Round to 4 decimal places
            'trade_value': round(value_given, 2)
        }


class TradeManager:
    """Manages team-to-team trade negotiations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_trade_offer(
        self,
        game_code: str,
        from_team_number: int,
        to_team_number: int,
        player_id: int,
        offered_resources: Dict[str, int],
        requested_resources: Dict[str, int]
    ) -> TradeOffer:
        """
        Create a new trade offer from one team to another.
        
        Args:
            game_code: Game code
            from_team_number: Team making the offer
            to_team_number: Team receiving the offer
            player_id: Player initiating the trade
            offered_resources: Resources being offered {"food": 10, "currency": 50}
            requested_resources: Resources being requested {"raw_materials": 20}
        
        Returns:
            Created TradeOffer
        
        Raises:
            ValueError: If validation fails
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            raise ValueError(f"Game {game_code} not found")
        
        # Validate player belongs to from_team
        player = self.db.query(Player).filter(
            Player.id == player_id,
            Player.game_session_id == game.id
        ).first()
        
        if not player:
            raise ValueError("Player not found")
        
        if player.group_number != from_team_number:
            raise ValueError("Player does not belong to the initiating team")
        
        # Validate teams are different
        if from_team_number == to_team_number:
            raise ValueError("Cannot trade with your own team")
        
        # Validate offered resources are available
        team_state = game.game_state.get('teams', {}).get(str(from_team_number), {})
        team_resources = team_state.get('resources', {})
        
        can_afford, missing = GameLogic.can_afford(team_resources, offered_resources)
        if not can_afford:
            raise ValueError(f"Insufficient {missing} to make this offer")
        
        # Create trade offer
        trade_offer = TradeOffer(
            game_session_id=game.id,
            from_team_number=from_team_number,
            to_team_number=to_team_number,
            initiated_by_player_id=player_id,
            offered_resources=offered_resources,
            requested_resources=requested_resources,
            status=TradeOfferStatus.PENDING
        )
        
        self.db.add(trade_offer)
        self.db.commit()
        self.db.refresh(trade_offer)
        
        return trade_offer
    
    def create_counter_offer(
        self,
        trade_offer_id: int,
        player_id: int,
        counter_offered_resources: Dict[str, int],
        counter_requested_resources: Dict[str, int]
    ) -> TradeOffer:
        """
        Create a counter-offer for an existing trade.
        
        Args:
            trade_offer_id: ID of the original trade offer
            player_id: Player making the counter-offer (must be from receiving team)
            counter_offered_resources: Resources counter-offered
            counter_requested_resources: Resources counter-requested
        
        Returns:
            Updated TradeOffer
        
        Raises:
            ValueError: If validation fails
        """
        trade_offer = self.db.query(TradeOffer).filter(
            TradeOffer.id == trade_offer_id
        ).first()
        
        if not trade_offer:
            raise ValueError("Trade offer not found")
        
        if trade_offer.status not in [TradeOfferStatus.PENDING, TradeOfferStatus.COUNTER_OFFERED]:
            raise ValueError(f"Cannot counter-offer a trade with status {trade_offer.status}")
        
        # Validate player belongs to receiving team
        player = self.db.query(Player).filter(
            Player.id == player_id,
            Player.game_session_id == trade_offer.game_session_id
        ).first()
        
        if not player:
            raise ValueError("Player not found")
        
        if player.group_number != trade_offer.to_team_number:
            raise ValueError("Player does not belong to the receiving team")
        
        # Validate counter-offered resources are available
        game = self.db.query(GameSession).filter(
            GameSession.id == trade_offer.game_session_id
        ).first()
        
        team_state = game.game_state.get('teams', {}).get(str(trade_offer.to_team_number), {})
        team_resources = team_state.get('resources', {})
        
        can_afford, missing = GameLogic.can_afford(team_resources, counter_offered_resources)
        if not can_afford:
            raise ValueError(f"Insufficient {missing} to make this counter-offer")
        
        # Update trade offer with counter-offer
        trade_offer.counter_offered_resources = counter_offered_resources
        trade_offer.counter_requested_resources = counter_requested_resources
        trade_offer.counter_offered_by_player_id = player_id
        trade_offer.counter_offered_at = datetime.utcnow()
        trade_offer.status = TradeOfferStatus.COUNTER_OFFERED
        
        self.db.commit()
        self.db.refresh(trade_offer)
        
        return trade_offer
    
    def accept_trade_offer(
        self,
        trade_offer_id: int,
        player_id: int,
        accept_counter: bool = False
    ) -> Tuple[TradeOffer, GameSession]:
        """
        Accept a trade offer and execute the resource exchange.
        
        Args:
            trade_offer_id: ID of the trade offer
            player_id: Player accepting the trade
            accept_counter: If True, original offerer is accepting counter-offer
        
        Returns:
            Tuple of (updated TradeOffer, updated GameSession)
        
        Raises:
            ValueError: If validation fails
        """
        trade_offer = self.db.query(TradeOffer).filter(
            TradeOffer.id == trade_offer_id
        ).first()
        
        if not trade_offer:
            raise ValueError("Trade offer not found")
        
        game = self.db.query(GameSession).filter(
            GameSession.id == trade_offer.game_session_id
        ).first()
        
        # Validate player
        player = self.db.query(Player).filter(
            Player.id == player_id,
            Player.game_session_id == game.id
        ).first()
        
        if not player:
            raise ValueError("Player not found")
        
        # Determine which version of the trade to execute
        if accept_counter:
            # Original offerer accepting counter-offer
            if player.group_number != trade_offer.from_team_number:
                raise ValueError("Only the original offerer can accept counter-offers")
            
            if trade_offer.status != TradeOfferStatus.COUNTER_OFFERED:
                raise ValueError("No counter-offer to accept")
            
            # Use counter-offer terms (swap directions)
            from_team = trade_offer.to_team_number
            to_team = trade_offer.from_team_number
            offered = trade_offer.counter_offered_resources
            requested = trade_offer.counter_requested_resources
        else:
            # Receiving team accepting original offer
            if player.group_number != trade_offer.to_team_number:
                raise ValueError("Only the receiving team can accept the offer")
            
            if trade_offer.status not in [TradeOfferStatus.PENDING, TradeOfferStatus.COUNTER_OFFERED]:
                raise ValueError(f"Cannot accept trade with status {trade_offer.status}")
            
            # Use original offer terms
            from_team = trade_offer.from_team_number
            to_team = trade_offer.to_team_number
            offered = trade_offer.offered_resources
            requested = trade_offer.requested_resources
        
        # Execute the trade
        from_team_state = game.game_state.get('teams', {}).get(str(from_team), {})
        to_team_state = game.game_state.get('teams', {}).get(str(to_team), {})
        
        from_resources = from_team_state.get('resources', {})
        to_resources = to_team_state.get('resources', {})
        
        # Validate both teams can still afford their parts
        can_afford_from, missing_from = GameLogic.can_afford(from_resources, offered)
        can_afford_to, missing_to = GameLogic.can_afford(to_resources, requested)
        
        if not can_afford_from:
            raise ValueError(f"Offering team no longer has sufficient {missing_from}")
        
        if not can_afford_to:
            raise ValueError(f"Requesting team no longer has sufficient {missing_to}")
        
        # Execute resource transfers
        from_resources = GameLogic.deduct_resources(from_resources, offered)
        from_resources = GameLogic.add_resources(from_resources, requested)
        
        to_resources = GameLogic.deduct_resources(to_resources, requested)
        to_resources = GameLogic.add_resources(to_resources, offered)
        
        # Calculate trade margins for kindness scoring
        bank_prices = game.game_state.get('bank_prices', {})
        if bank_prices:
            # From team's perspective: they give 'offered', receive 'requested'
            from_team_margin_data = TradeMarginCalculator.calculate_trade_margin(
                offered, requested, bank_prices
            )
            # To team's perspective: they give 'requested', receive 'offered'
            to_team_margin_data = TradeMarginCalculator.calculate_trade_margin(
                requested, offered, bank_prices
            )
            
            trade_offer.from_team_margin = from_team_margin_data
            trade_offer.to_team_margin = to_team_margin_data
        
        # Update game state
        game.game_state['teams'][str(from_team)]['resources'] = from_resources
        game.game_state['teams'][str(to_team)]['resources'] = to_resources
        flag_modified(game, 'game_state')
        
        # Update trade offer status
        trade_offer.status = TradeOfferStatus.ACCEPTED
        trade_offer.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(trade_offer)
        self.db.refresh(game)
        
        return trade_offer, game
    
    def reject_trade_offer(
        self,
        trade_offer_id: int,
        player_id: int
    ) -> TradeOffer:
        """
        Reject a trade offer.
        
        Args:
            trade_offer_id: ID of the trade offer
            player_id: Player rejecting the trade
        
        Returns:
            Updated TradeOffer
        """
        trade_offer = self.db.query(TradeOffer).filter(
            TradeOffer.id == trade_offer_id
        ).first()
        
        if not trade_offer:
            raise ValueError("Trade offer not found")
        
        if trade_offer.status not in [TradeOfferStatus.PENDING, TradeOfferStatus.COUNTER_OFFERED]:
            raise ValueError(f"Cannot reject trade with status {trade_offer.status}")
        
        # Validate player belongs to receiving team
        player = self.db.query(Player).filter(
            Player.id == player_id
        ).first()
        
        if not player:
            raise ValueError("Player not found")
        
        if player.group_number != trade_offer.to_team_number:
            raise ValueError("Only the receiving team can reject the offer")
        
        trade_offer.status = TradeOfferStatus.REJECTED
        trade_offer.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(trade_offer)
        
        return trade_offer
    
    def cancel_trade_offer(
        self,
        trade_offer_id: int,
        player_id: int
    ) -> TradeOffer:
        """
        Cancel a trade offer (only by initiator).
        
        Args:
            trade_offer_id: ID of the trade offer
            player_id: Player cancelling the trade (must be initiator)
        
        Returns:
            Updated TradeOffer
        """
        trade_offer = self.db.query(TradeOffer).filter(
            TradeOffer.id == trade_offer_id
        ).first()
        
        if not trade_offer:
            raise ValueError("Trade offer not found")
        
        if trade_offer.status not in [TradeOfferStatus.PENDING, TradeOfferStatus.COUNTER_OFFERED]:
            raise ValueError(f"Cannot cancel trade with status {trade_offer.status}")
        
        if trade_offer.initiated_by_player_id != player_id:
            raise ValueError("Only the initiator can cancel the trade offer")
        
        trade_offer.status = TradeOfferStatus.CANCELLED
        trade_offer.completed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(trade_offer)
        
        return trade_offer
    
    def get_team_trade_offers(
        self,
        game_code: str,
        team_number: int,
        include_completed: bool = False
    ) -> List[TradeOffer]:
        """
        Get all trade offers involving a team.
        
        Args:
            game_code: Game code
            team_number: Team number
            include_completed: Whether to include completed/rejected/cancelled trades
        
        Returns:
            List of TradeOffers
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            return []
        
        query = self.db.query(TradeOffer).filter(
            TradeOffer.game_session_id == game.id,
            (TradeOffer.from_team_number == team_number) | 
            (TradeOffer.to_team_number == team_number)
        )
        
        if not include_completed:
            query = query.filter(
                TradeOffer.status.in_([
                    TradeOfferStatus.PENDING,
                    TradeOfferStatus.COUNTER_OFFERED
                ])
            )
        
        return query.order_by(TradeOffer.created_at.desc()).all()
    
    def get_all_active_trades(self, game_code: str) -> List[TradeOffer]:
        """
        Get all active trade offers for a game (for host/banker view).
        
        Args:
            game_code: Game code
        
        Returns:
            List of active TradeOffers
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            return []
        
        return self.db.query(TradeOffer).filter(
            TradeOffer.game_session_id == game.id,
            TradeOffer.status.in_([
                TradeOfferStatus.PENDING,
                TradeOfferStatus.COUNTER_OFFERED
            ])
        ).order_by(TradeOffer.created_at.desc()).all()
