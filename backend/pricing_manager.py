"""
Pricing Manager - Handles dynamic bank pricing with supply/demand mechanics
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import random
import json
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from models import GameSession, PriceHistory
from game_constants import BANK_INITIAL_PRICES, ResourceType


class PricingManager:
    """Manages dynamic pricing for bank trades"""
    
    # Price adjustment parameters
    MIN_MULTIPLIER = 0.5  # -50% from baseline
    MAX_MULTIPLIER = 3.5  # +250% from baseline (was 2.0)
    SPREAD_PERCENTAGE = 0.2  # 20% spread between buy and sell (was 0.1)
    
    # Supply/demand adjustment factors
    TRADE_IMPACT_FACTOR = 0.05  # 5% price change per significant trade
    MARKET_DEPTH_FACTOR = 0.10  # 10% additional impact per 100 units traded (market depth)
    
    # Random fluctuation parameters
    FLUCTUATION_PROBABILITY = 1.0  # 100% chance per 30-second check (was 3.33% per second)
    FLUCTUATION_MAGNITUDE = 0.02  # ±2% per fluctuation
    MOMENTUM_LOOKBACK_MINUTES = 2  # Look at last 2 minutes for momentum
    MEAN_REVERSION_TARGET_MINUTES = 15  # Target 15 minutes to return to baseline
    MOMENTUM_WEIGHT = 0.6  # 60% weight for momentum vs 40% for mean reversion
    
    # Price alert parameters
    PRICE_ALERT_THRESHOLD = 0.10  # Alert if price changes by 10% or more
    
    # Cache for event configuration (loaded once)
    _event_config_cache = None
    
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
        
        Standard market maker: buy_price > sell_price (bank buys low, sells high)
        
        Args:
            base_price: The base/middle price
            is_buy: True if this is buy_price (bank selling to teams at higher price), 
                   False if sell_price (bank buying from teams at lower price)
        
        Returns:
            Adjusted price with spread applied
        """
        spread = int(base_price * self.SPREAD_PERCENTAGE)
        # Ensure minimum spread of 1 to create price differentiation
        spread = max(1, spread)
        if is_buy:
            # buy_price: Bank sells to teams at HIGHER price
            return base_price + spread
        else:
            # sell_price: Bank buys from teams at LOWER price
            return max(1, base_price - spread)
    
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
        current_middle = round((price_info['buy_price'] + price_info['sell_price']) / 2.0)
        
        # Calculate price adjustment based on trade direction and size
        # If team is buying from bank, demand increases -> price goes up
        # If team is selling to bank, supply increases -> price goes down
        adjustment_direction = 1 if is_team_buying else -1
        
        # Scale adjustment based on quantity with market depth
        # Larger trades have exponentially greater impact (market depth effect)
        base_quantity_factor = min(quantity / 100, 1.0)  # Base scaling
        
        # Market depth: Additional impact for large trades
        # Every 100 units adds MARKET_DEPTH_FACTOR more impact
        depth_multiplier = 1.0 + (quantity // 100) * self.MARKET_DEPTH_FACTOR
        depth_multiplier = min(depth_multiplier, 3.0)  # Cap at 3x impact
        
        # Combined adjustment with market depth
        adjustment = int(baseline * self.TRADE_IMPACT_FACTOR * base_quantity_factor * depth_multiplier)
        
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
            current_middle = round((price_info['buy_price'] + price_info['sell_price']) / 2.0)
            
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
    
    def update_resource_baseline(
        self,
        game_code: str,
        resource_type: str,
        new_baseline: int,
        current_prices: Dict[str, Dict[str, int]]
    ) -> Dict[str, Dict[str, int]]:
        """
        Manually update the baseline price for a resource (for host/banker).
        
        Args:
            game_code: The game code
            resource_type: Resource to update
            new_baseline: New baseline price
            current_prices: Current price structure
        
        Returns:
            Updated price structure
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game:
            raise ValueError(f"Game {game_code} not found")
        
        if resource_type not in current_prices:
            raise ValueError(f"Unknown resource type: {resource_type}")
        
        if new_baseline < 1:
            raise ValueError("Baseline price must be at least 1")
        
        # Calculate new buy/sell prices with spread
        new_buy_price = self._apply_spread(new_baseline, is_buy=True)
        new_sell_price = self._apply_spread(new_baseline, is_buy=False)
        
        # Update prices
        updated_prices = current_prices.copy()
        updated_prices[resource_type] = {
            'baseline': new_baseline,
            'buy_price': new_buy_price,
            'sell_price': new_sell_price
        }
        
        # Record price change
        self._record_price_history(
            game.id,
            resource_type,
            new_buy_price,
            new_sell_price,
            new_baseline,
            triggered_by_trade=False
        )
        
        return updated_prices
    
    def apply_random_fluctuation(
        self,
        game_code: str,
        current_prices: Dict[str, Dict[str, int]]
    ) -> Tuple[Dict[str, Dict[str, int]], List[str]]:
        """
        Apply random price fluctuations to all resources.
        
        Called every second with 3.33% probability per resource.
        Considers momentum, mean reversion, and active game events.
        
        Args:
            game_code: The game code
            current_prices: Current price structure
        
        Returns:
            Tuple of (updated prices dict, list of changed resource names)
        """
        game = self.db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        
        if not game or not current_prices:
            return current_prices, []
        
        # Load event configuration
        event_effects = self._load_event_price_effects()
        
        # Get active event effects for this game
        active_event_effect = self._get_active_event_effect(game, event_effects)
        
        updated_prices = current_prices.copy()
        changed_resources = []
        
        for resource_type in current_prices.keys():
            # 3.33% probability check
            if random.random() > self.FLUCTUATION_PROBABILITY:
                continue
            
            price_info = current_prices[resource_type]
            baseline = price_info['baseline']
            
            # Validate baseline before calculations
            if baseline <= 0:
                continue
            
            # Calculate current middle price
            buy_price = price_info.get('buy_price', baseline)
            sell_price = price_info.get('sell_price', baseline)
            current_middle = max(1, round((buy_price + sell_price) / 2.0))
            
            # Calculate momentum bias from recent price history
            momentum_bias = self._calculate_momentum_bias(game.id, resource_type)
            
            # Calculate mean reversion pressure
            mean_reversion_pressure = self._calculate_mean_reversion_pressure(
                current_middle, baseline
            )
            
            # Get event effect for this resource
            resource_event_effect = active_event_effect.get(resource_type, 0.0)
            
            # Combine factors with weights
            # Momentum has priority, but mean reversion provides gentle pull back
            direction_bias = (
                self.MOMENTUM_WEIGHT * momentum_bias +
                (1 - self.MOMENTUM_WEIGHT) * mean_reversion_pressure +
                resource_event_effect
            )
            
            # Random fluctuation with directional bias
            # Base random change: -2% to +2%
            random_change = random.uniform(-self.FLUCTUATION_MAGNITUDE, self.FLUCTUATION_MAGNITUDE)
            
            # Apply bias to make it more likely to go in the biased direction
            # Positive bias increases probability of positive change
            if direction_bias > 0:
                # More likely to go up
                biased_random = random.random()
                if biased_random < 0.5 + abs(direction_bias) * 0.5:
                    random_change = abs(random_change)  # Force positive
            elif direction_bias < 0:
                # More likely to go down
                biased_random = random.random()
                if biased_random < 0.5 + abs(direction_bias) * 0.5:
                    random_change = -abs(random_change)  # Force negative
            
            # Apply the change
            new_middle = int(current_middle * (1 + random_change))
            
            # Clamp to min/max multipliers
            min_price = int(baseline * self.MIN_MULTIPLIER)
            max_price = int(baseline * self.MAX_MULTIPLIER)
            new_middle = max(min_price, min(max_price, new_middle))
            
            # Only update if price actually changed
            if new_middle != current_middle:
                # Apply spread to get buy/sell prices
                new_buy_price = self._apply_spread(new_middle, is_buy=True)
                new_sell_price = self._apply_spread(new_middle, is_buy=False)
                
                # Ensure buy > sell and re-validate bounds after spread adjustment
                if new_buy_price <= new_sell_price:
                    # Adjust to ensure proper spread
                    spread = max(1, int(new_middle * self.SPREAD_PERCENTAGE))
                    new_buy_price = new_middle + spread
                    new_sell_price = new_middle - spread
                
                # Re-clamp after spread adjustment to ensure bounds are respected
                new_buy_price = max(min_price, min(max_price, new_buy_price))
                new_sell_price = max(min_price, min(max_price, new_sell_price))
                
                # Final validation that buy > sell after all adjustments
                if new_buy_price <= new_sell_price:
                    # If still invalid, skip this update
                    continue
                
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
                    triggered_by_trade=False
                )
                
                changed_resources.append(resource_type)
        
        return updated_prices, changed_resources
    
    def _calculate_momentum_bias(self, game_session_id: int, resource_type: str) -> float:
        """
        Calculate momentum bias based on recent price changes.
        
        Looks at price changes over the last MOMENTUM_LOOKBACK_MINUTES to determine
        if prices have been trending up or down.
        
        Returns:
            Float between -1 and 1, where positive = upward momentum, negative = downward momentum
        """
        lookback_time = datetime.utcnow() - timedelta(minutes=self.MOMENTUM_LOOKBACK_MINUTES)
        
        # Get recent price history
        recent_prices = self.db.query(PriceHistory).filter(
            PriceHistory.game_session_id == game_session_id,
            PriceHistory.resource_type == resource_type,
            PriceHistory.timestamp >= lookback_time
        ).order_by(PriceHistory.timestamp.asc()).all()
        
        if len(recent_prices) < 2:
            return 0.0  # Not enough data for momentum
        
        # Calculate price changes
        price_changes = []
        for i in range(1, len(recent_prices)):
            prev_middle = (recent_prices[i-1].buy_price + recent_prices[i-1].sell_price) / 2.0
            curr_middle = (recent_prices[i].buy_price + recent_prices[i].sell_price) / 2.0
            change_pct = (curr_middle - prev_middle) / prev_middle if prev_middle > 0 else 0.0
            price_changes.append(change_pct)
        
        if not price_changes:
            return 0.0
        
        # Average percentage change
        avg_change = sum(price_changes) / len(price_changes)
        
        # Normalize to -1 to 1 range
        # If average change is ±5% over the period, that's strong momentum
        momentum = avg_change / 0.05
        momentum = max(-1.0, min(1.0, momentum))
        
        return momentum
    
    def _calculate_mean_reversion_pressure(self, current_price: int, baseline: int) -> float:
        """
        Calculate pressure to return to baseline price.
        
        The further from baseline, the stronger the pull back.
        Designed to bring prices back over ~15 minutes.
        
        Returns:
            Float between -1 and 1, where positive = pressure to increase (below baseline),
            negative = pressure to decrease (above baseline)
        """
        if baseline == 0:
            return 0.0
        
        # Calculate how far we are from baseline
        deviation = (current_price - baseline) / baseline
        
        # Invert the deviation: if price is high (positive deviation), 
        # we want negative pressure to bring it down
        pressure = -deviation
        
        # Scale so that being at max/min gives max pressure
        # MAX_MULTIPLIER = 2.0 means 100% above baseline
        # MIN_MULTIPLIER = 0.5 means 50% below baseline (or -50%)
        max_deviation = max(self.MAX_MULTIPLIER - 1.0, 1.0 - self.MIN_MULTIPLIER)
        pressure = pressure / max_deviation
        
        # Clamp to -1 to 1
        pressure = max(-1.0, min(1.0, pressure))
        
        return pressure
    
    def _get_active_event_effect(
        self,
        game: GameSession,
        event_effects: Dict
    ) -> Dict[str, float]:
        """
        Get the combined price effect from all active game events.
        
        Args:
            game: The game session
            event_effects: Dictionary of event configurations with price effects
        
        Returns:
            Dictionary mapping resource_type to cumulative price effect modifier
        """
        resource_effects = {}
        
        if 'active_events' not in game.game_state:
            return resource_effects
        
        active_events = game.game_state.get('active_events', {})
        
        for event_name, event_data in active_events.items():
            if event_name not in event_effects:
                continue
            
            event_config = event_effects[event_name]
            base_effect = event_config.get('price_effect', 0.0)
            
            if base_effect == 0.0:
                continue
            
            # Check if event specifies specific resources
            affected_resources = event_config.get('price_effect_resources')
            
            if affected_resources:
                # Apply to specific resources
                for resource in affected_resources:
                    if resource not in resource_effects:
                        resource_effects[resource] = 0.0
                    resource_effects[resource] += base_effect
            else:
                # Apply to all resources
                for resource_type in BANK_INITIAL_PRICES.keys():
                    resource_key = resource_type.value if hasattr(resource_type, 'value') else resource_type
                    if resource_key not in resource_effects:
                        resource_effects[resource_key] = 0.0
                    resource_effects[resource_key] += base_effect
        
        return resource_effects
    
    def _load_event_price_effects(self) -> Dict:
        """
        Load event price effects from event_config.json.
        Uses class-level cache to avoid repeated file reads.
        
        Returns:
            Dictionary mapping event names to their configurations
        """
        # Return cached config if available
        if PricingManager._event_config_cache is not None:
            return PricingManager._event_config_cache
        
        try:
            import os
            config_path = os.path.join(os.path.dirname(__file__), 'event_config.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Cache the loaded configuration
            PricingManager._event_config_cache = config.get('events', {})
            return PricingManager._event_config_cache
        except Exception as e:
            # If config can't be loaded, return empty dict
            # Don't cache failures so we can retry later
            return {}
