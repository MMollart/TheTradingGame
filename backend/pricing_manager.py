"""
Pricing Manager - Handles dynamic bank pricing with supply/demand mechanics
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from models import GameSession, PriceHistory
from game_constants import BANK_INITIAL_PRICES, ResourceType


class PricingManager:
    """Manages dynamic pricing for bank trades"""
    
    # Price adjustment parameters
    MIN_MULTIPLIER = 0.5  # -50% from baseline
    MAX_MULTIPLIER = 2.0  # +100% from baseline
    SPREAD_PERCENTAGE = 0.1  # 10% spread between buy and sell
    
    # Supply/demand adjustment factors
    TRADE_IMPACT_FACTOR = 0.05  # 5% price change per significant trade
    
    def __init__(self, db: Session):
        self.db = db
    
    def initialize_bank_prices(self, game_code: str) -> Dict[str, Dict[str, int]]:
        """
        Initialize bank prices for a new game.
        
        Returns:
            Dictionary with resource prices containing buy_price, sell_price, baseline
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            raise ValueError(f"Game {game_code} not found")
        
        prices = {}
        
        for resource_type, baseline_price in BANK_INITIAL_PRICES.items():
            resource_key = resource_type.value if hasattr(resource_type, 'value') else resource_type
            
            # Calculate buy and sell prices with spread
            buy_price = self._apply_spread(baseline_price, is_buy=True)
            sell_price = self._apply_spread(baseline_price, is_buy=False)
            
            prices[resource_key] = {
                'baseline': baseline_price,
                'buy_price': buy_price,  # Bank sells at higher price
                'sell_price': sell_price  # Bank buys at lower price
            }
            
            # Record initial price
            self._record_price_history(
                game.id,
                resource_key,
                buy_price,
                sell_price,
                baseline_price,
                triggered_by_trade=False
            )
        
        return prices
    
    def _apply_spread(self, base_price: int, is_buy: bool) -> int:
        """
        Apply buy/sell spread to a base price.
        
        Args:
            base_price: The base/middle price
            is_buy: True if bank is selling (buy price), False if bank is buying (sell price)
        
        Returns:
            Adjusted price with spread applied
        """
        spread = int(base_price * self.SPREAD_PERCENTAGE)
        if is_buy:
            return base_price + spread  # Bank sells higher
        else:
            return max(1, base_price - spread)  # Bank buys lower, minimum 1
    
    def adjust_price_after_trade(
        self,
        game_code: str,
        resource_type: str,
        quantity: int,
        is_team_buying: bool,
        current_prices: Dict[str, Dict[str, int]]
    ) -> Dict[str, Dict[str, int]]:
        """
        Adjust prices after a bank trade based on supply/demand.
        
        Args:
            game_code: The game code
            resource_type: Resource that was traded
            quantity: Amount traded
            is_team_buying: True if team bought from bank, False if team sold to bank
            current_prices: Current price structure
        
        Returns:
            Updated price structure
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game or resource_type not in current_prices:
            return current_prices
        
        # Get current price info
        price_info = current_prices[resource_type]
        baseline = price_info['baseline']
        current_middle = (price_info['buy_price'] + price_info['sell_price']) // 2
        
        # Calculate price adjustment based on trade direction and size
        # If team is buying from bank, demand increases -> price goes up
        # If team is selling to bank, supply increases -> price goes down
        adjustment_direction = 1 if is_team_buying else -1
        
        # Scale adjustment based on quantity (more significant for larger trades)
        quantity_factor = min(quantity / 100, 1.0)  # Cap at 100 units for max effect
        adjustment = int(baseline * self.TRADE_IMPACT_FACTOR * quantity_factor)
        
        # Apply adjustment
        new_middle = current_middle + (adjustment * adjustment_direction)
        
        # Clamp to min/max multipliers
        min_price = int(baseline * self.MIN_MULTIPLIER)
        max_price = int(baseline * self.MAX_MULTIPLIER)
        new_middle = max(min_price, min(max_price, new_middle))
        
        # Apply spread to get buy/sell prices
        new_buy_price = self._apply_spread(new_middle, is_buy=True)
        new_sell_price = self._apply_spread(new_middle, is_buy=False)
        
        # Update prices
        updated_prices = current_prices.copy()
        updated_prices[resource_type] = {
            'baseline': baseline,
            'buy_price': new_buy_price,
            'sell_price': new_sell_price
        }
        
        # Record price change
        self._record_price_history(
            game.id,
            resource_type,
            new_buy_price,
            new_sell_price,
            baseline,
            triggered_by_trade=True
        )
        
        return updated_prices
    
    def adjust_all_prices_after_trade(
        self,
        game_code: str,
        traded_resource: str,
        quantity: int,
        is_team_buying: bool,
        current_prices: Dict[str, Dict[str, int]]
    ) -> Dict[str, Dict[str, int]]:
        """
        Adjust all resource prices after a trade, with smaller effects on non-traded resources.
        
        This creates a more realistic economy where all resource prices are interconnected.
        """
        updated_prices = current_prices.copy()
        
        # Primary resource gets full adjustment
        updated_prices = self.adjust_price_after_trade(
            game_code,
            traded_resource,
            quantity,
            is_team_buying,
            updated_prices
        )
        
        # Secondary effect: other resources get small adjustment in same direction
        # This simulates market interconnection
        secondary_adjustment_factor = 0.2  # 20% of primary effect
        
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            return updated_prices
        
        for resource_type in updated_prices.keys():
            if resource_type == traded_resource:
                continue  # Already adjusted
            
            price_info = updated_prices[resource_type]
            baseline = price_info['baseline']
            current_middle = (price_info['buy_price'] + price_info['sell_price']) // 2
            
            # Small adjustment in same direction as primary resource
            adjustment_direction = 1 if is_team_buying else -1
            adjustment = int(baseline * self.TRADE_IMPACT_FACTOR * secondary_adjustment_factor)
            
            new_middle = current_middle + (adjustment * adjustment_direction)
            
            # Clamp to limits
            min_price = int(baseline * self.MIN_MULTIPLIER)
            max_price = int(baseline * self.MAX_MULTIPLIER)
            new_middle = max(min_price, min(max_price, new_middle))
            
            # Apply spread
            new_buy_price = self._apply_spread(new_middle, is_buy=True)
            new_sell_price = self._apply_spread(new_middle, is_buy=False)
            
            updated_prices[resource_type] = {
                'baseline': baseline,
                'buy_price': new_buy_price,
                'sell_price': new_sell_price
            }
            
            # Record secondary price change
            self._record_price_history(
                game.id,
                resource_type,
                new_buy_price,
                new_sell_price,
                baseline,
                triggered_by_trade=True
            )
        
        return updated_prices
    
    def _record_price_history(
        self,
        game_session_id: int,
        resource_type: str,
        buy_price: int,
        sell_price: int,
        baseline_price: int,
        triggered_by_trade: bool
    ) -> None:
        """Record a price snapshot in history"""
        price_record = PriceHistory(
            game_session_id=game_session_id,
            resource_type=resource_type,
            buy_price=buy_price,
            sell_price=sell_price,
            baseline_price=baseline_price,
            triggered_by_trade=triggered_by_trade
        )
        self.db.add(price_record)
        self.db.commit()
    
    def get_price_history(
        self,
        game_code: str,
        resource_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get price history for charting.
        
        Args:
            game_code: The game code
            resource_type: Optional filter for specific resource
            limit: Maximum number of records to return
        
        Returns:
            List of price history records
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            return []
        
        query = self.db.query(PriceHistory).filter(
            PriceHistory.game_session_id == game.id
        )
        
        if resource_type:
            query = query.filter(PriceHistory.resource_type == resource_type)
        
        query = query.order_by(PriceHistory.timestamp.desc()).limit(limit)
        
        records = query.all()
        
        # Convert to dict format for API response
        return [
            {
                'resource_type': record.resource_type,
                'buy_price': record.buy_price,
                'sell_price': record.sell_price,
                'baseline_price': record.baseline_price,
                'timestamp': record.timestamp.isoformat(),
                'triggered_by_trade': record.triggered_by_trade
            }
            for record in reversed(records)  # Reverse to get chronological order
        ]
    
    def calculate_trade_cost(
        self,
        resource_type: str,
        quantity: int,
        is_team_buying: bool,
        current_prices: Dict[str, Dict[str, int]]
    ) -> int:
        """
        Calculate the currency cost/gain for a bank trade.
        
        Args:
            resource_type: Resource to trade
            quantity: Amount to trade
            is_team_buying: True if team is buying, False if selling
            current_prices: Current price structure
        
        Returns:
            Currency amount (positive = cost, negative = gain)
        """
        if resource_type not in current_prices:
            raise ValueError(f"Unknown resource type: {resource_type}")
        
        price_info = current_prices[resource_type]
        unit_price = price_info['buy_price'] if is_team_buying else price_info['sell_price']
        
        return unit_price * quantity
