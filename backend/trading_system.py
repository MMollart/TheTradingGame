"""
Trading System for The Trading Game

Handles:
- Dynamic bank pricing based on supply and demand
- Buy/sell price spreads
- Price history tracking for charting
- Team-to-team trade offers and counter offers
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
import math

from game_constants import ResourceType, BANK_INITIAL_PRICES


class TradeOfferStatus(str, Enum):
    """Status of team-to-team trade offers"""
    PENDING = "pending"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class DynamicPricingSystem:
    """
    Manages dynamic pricing for bank trades
    
    Features:
    - Prices can range from -50% to +100% of baseline
    - Separate buy and sell prices with spread
    - Supply and demand tracking
    - Price history for charting
    """
    
    # Price bounds relative to baseline
    MIN_PRICE_MULTIPLIER = 0.5   # -50%
    MAX_PRICE_MULTIPLIER = 2.0   # +100%
    
    # Default spread between buy and sell (bank buys cheaper, sells higher)
    DEFAULT_SPREAD = 0.15  # 15% spread (7.5% on each side)
    
    def __init__(self, baseline_prices: Dict[str, float] = None):
        """Initialize with baseline prices"""
        self.baseline_prices = baseline_prices or {
            resource.value: float(price)
            for resource, price in BANK_INITIAL_PRICES.items()
        }
        
        # Current multipliers for each resource (1.0 = baseline)
        self.price_multipliers = {
            resource: 1.0 for resource in self.baseline_prices.keys()
        }
        
        # Track trade volumes for supply/demand calculations
        self.trade_volumes = {
            resource: {"bought": 0, "sold": 0}
            for resource in self.baseline_prices.keys()
        }
        
        # Price history for charting
        self.price_history: List[Dict[str, Any]] = []
        self._record_prices()
    
    def _record_prices(self):
        """Record current prices to history"""
        timestamp = datetime.utcnow().isoformat()
        price_snapshot = {
            "timestamp": timestamp,
            "prices": {
                resource: {
                    "buy": self.get_buy_price(resource),
                    "sell": self.get_sell_price(resource),
                    "multiplier": self.price_multipliers[resource]
                }
                for resource in self.baseline_prices.keys()
            }
        }
        self.price_history.append(price_snapshot)
        
        # Keep last 100 price records
        if len(self.price_history) > 100:
            self.price_history = self.price_history[-100:]
    
    def get_sell_price(self, resource: str) -> float:
        """
        Get price at which bank SELLS to players (players buy from bank)
        Bank sells at higher price
        """
        baseline = self.baseline_prices.get(resource, 1.0)
        multiplier = self.price_multipliers.get(resource, 1.0)
        
        # Apply spread - bank sells higher
        spread_multiplier = 1.0 + (self.DEFAULT_SPREAD / 2)
        price = baseline * multiplier * spread_multiplier
        
        # Ensure within bounds
        min_price = baseline * self.MIN_PRICE_MULTIPLIER
        max_price = baseline * self.MAX_PRICE_MULTIPLIER
        
        return max(min_price, min(max_price, price))
    
    def get_buy_price(self, resource: str) -> float:
        """
        Get price at which bank BUYS from players (players sell to bank)
        Bank buys at lower price
        """
        baseline = self.baseline_prices.get(resource, 1.0)
        multiplier = self.price_multipliers.get(resource, 1.0)
        
        # Apply spread - bank buys lower
        spread_multiplier = 1.0 - (self.DEFAULT_SPREAD / 2)
        price = baseline * multiplier * spread_multiplier
        
        # Ensure within bounds
        min_price = baseline * self.MIN_PRICE_MULTIPLIER
        max_price = baseline * self.MAX_PRICE_MULTIPLIER
        
        return max(min_price, min(max_price, price))
    
    def update_prices_after_trade(
        self,
        resource: str,
        amount: int,
        trade_type: str  # "bank_sells" or "bank_buys"
    ):
        """
        Update prices based on supply and demand after a trade
        
        Logic:
        - When bank sells a lot (high demand): price increases
        - When bank buys a lot (high supply): price decreases
        - Changes are gradual and balanced
        """
        if resource not in self.baseline_prices:
            return
        
        # Track trade volume
        if trade_type == "bank_sells":
            self.trade_volumes[resource]["sold"] += amount
        elif trade_type == "bank_buys":
            self.trade_volumes[resource]["bought"] += amount
        
        # Calculate supply/demand ratio
        sold = self.trade_volumes[resource]["sold"]
        bought = self.trade_volumes[resource]["bought"]
        
        # Prevent division by zero
        total_volume = sold + bought
        if total_volume == 0:
            return
        
        # Calculate demand pressure (-1 to +1)
        # Positive = high demand (more sold than bought) -> price up
        # Negative = high supply (more bought than sold) -> price down
        demand_ratio = (sold - bought) / total_volume
        
        # Apply gradual price adjustment
        # Use logarithmic scaling for smoother changes
        adjustment_factor = 0.05  # 5% adjustment per significant trade imbalance
        price_change = demand_ratio * adjustment_factor
        
        # Update multiplier
        new_multiplier = self.price_multipliers[resource] + price_change
        
        # Clamp to bounds
        min_mult = self.MIN_PRICE_MULTIPLIER
        max_mult = self.MAX_PRICE_MULTIPLIER
        self.price_multipliers[resource] = max(min_mult, min(max_mult, new_multiplier))
        
        # Record new prices
        self._record_prices()
    
    def get_price_history(
        self,
        resource: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get price history for charting
        
        Args:
            resource: Specific resource or None for all
            limit: Maximum number of historical points
        
        Returns:
            List of price history records
        """
        history = self.price_history[-limit:]
        
        if resource:
            # Filter for specific resource
            return [
                {
                    "timestamp": record["timestamp"],
                    "buy_price": record["prices"].get(resource, {}).get("buy", 0),
                    "sell_price": record["prices"].get(resource, {}).get("sell", 0),
                    "multiplier": record["prices"].get(resource, {}).get("multiplier", 1.0)
                }
                for record in history
            ]
        
        return history
    
    def get_all_prices(self) -> Dict[str, Dict[str, float]]:
        """Get current buy and sell prices for all resources"""
        return {
            resource: {
                "buy": self.get_buy_price(resource),
                "sell": self.get_sell_price(resource),
                "baseline": self.baseline_prices[resource],
                "multiplier": self.price_multipliers[resource]
            }
            for resource in self.baseline_prices.keys()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize pricing system state"""
        return {
            "baseline_prices": self.baseline_prices,
            "price_multipliers": self.price_multipliers,
            "trade_volumes": self.trade_volumes,
            "price_history": self.price_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DynamicPricingSystem':
        """Deserialize pricing system state"""
        system = cls(baseline_prices=data.get("baseline_prices"))
        system.price_multipliers = data.get("price_multipliers", system.price_multipliers)
        system.trade_volumes = data.get("trade_volumes", system.trade_volumes)
        system.price_history = data.get("price_history", [])
        return system


class TeamTradeOffer:
    """Represents a trade offer between teams"""
    
    def __init__(
        self,
        offer_id: str,
        from_team: int,
        to_team: int,
        offering: Dict[str, int],
        requesting: Dict[str, int],
        message: Optional[str] = None
    ):
        self.offer_id = offer_id
        self.from_team = from_team
        self.to_team = to_team
        self.offering = offering  # What from_team gives
        self.requesting = requesting  # What from_team wants
        self.message = message
        self.status = TradeOfferStatus.PENDING
        self.created_at = datetime.utcnow()
        self.counter_offer: Optional[Dict[str, Any]] = None
    
    def counter(
        self,
        new_offering: Dict[str, int],
        new_requesting: Dict[str, int],
        message: Optional[str] = None
    ):
        """Create a counter offer"""
        self.counter_offer = {
            "offering": new_offering,
            "requesting": new_requesting,
            "message": message,
            "created_at": datetime.utcnow().isoformat()
        }
        self.status = TradeOfferStatus.COUNTERED
    
    def accept(self):
        """Accept the trade offer"""
        self.status = TradeOfferStatus.ACCEPTED
    
    def reject(self):
        """Reject the trade offer"""
        self.status = TradeOfferStatus.REJECTED
    
    def cancel(self):
        """Cancel the trade offer"""
        self.status = TradeOfferStatus.CANCELLED
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize trade offer"""
        return {
            "offer_id": self.offer_id,
            "from_team": self.from_team,
            "to_team": self.to_team,
            "offering": self.offering,
            "requesting": self.requesting,
            "message": self.message,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "counter_offer": self.counter_offer
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TeamTradeOffer':
        """Deserialize trade offer"""
        offer = cls(
            offer_id=data["offer_id"],
            from_team=data["from_team"],
            to_team=data["to_team"],
            offering=data["offering"],
            requesting=data["requesting"],
            message=data.get("message")
        )
        offer.status = TradeOfferStatus(data["status"])
        offer.created_at = datetime.fromisoformat(data["created_at"])
        offer.counter_offer = data.get("counter_offer")
        return offer


class TradingManager:
    """
    Manages all trading operations
    """
    
    def __init__(self, pricing_system: Optional[DynamicPricingSystem] = None):
        self.pricing_system = pricing_system or DynamicPricingSystem()
        self.trade_offers: Dict[str, TeamTradeOffer] = {}
    
    def execute_bank_trade(
        self,
        team_resources: Dict[str, int],
        resource: str,
        amount: int,
        trade_type: str  # "buy" or "sell"
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, int]], Optional[float]]:
        """
        Execute a trade with the bank
        
        Args:
            team_resources: Team's current resources
            resource: Resource to trade
            amount: Amount to trade
            trade_type: "buy" (team buys from bank) or "sell" (team sells to bank)
        
        Returns:
            (success, error_message, updated_resources, total_cost)
        """
        if amount <= 0:
            return False, "Amount must be positive", None, None
        
        if resource not in self.pricing_system.baseline_prices:
            return False, f"Invalid resource: {resource}", None, None
        
        # Get price
        if trade_type == "buy":
            # Team buys from bank (bank sells)
            unit_price = self.pricing_system.get_sell_price(resource)
            total_cost = unit_price * amount
            
            # Check if team has enough currency
            current_currency = team_resources.get("currency", 0)
            if current_currency < total_cost:
                return False, f"Insufficient currency. Need {total_cost}, have {current_currency}", None, None
            
            # Update resources
            new_resources = team_resources.copy()
            new_resources["currency"] = current_currency - total_cost
            new_resources[resource] = new_resources.get(resource, 0) + amount
            
            # Update prices based on trade
            self.pricing_system.update_prices_after_trade(resource, amount, "bank_sells")
            
            return True, None, new_resources, total_cost
        
        elif trade_type == "sell":
            # Team sells to bank (bank buys)
            unit_price = self.pricing_system.get_buy_price(resource)
            total_revenue = unit_price * amount
            
            # Check if team has enough resource
            current_resource = team_resources.get(resource, 0)
            if current_resource < amount:
                return False, f"Insufficient {resource}. Need {amount}, have {current_resource}", None, None
            
            # Update resources
            new_resources = team_resources.copy()
            new_resources[resource] = current_resource - amount
            new_resources["currency"] = new_resources.get("currency", 0) + total_revenue
            
            # Update prices based on trade
            self.pricing_system.update_prices_after_trade(resource, amount, "bank_buys")
            
            return True, None, new_resources, total_revenue
        
        else:
            return False, f"Invalid trade type: {trade_type}", None, None
    
    def create_trade_offer(
        self,
        from_team: int,
        to_team: int,
        offering: Dict[str, int],
        requesting: Dict[str, int],
        message: Optional[str] = None
    ) -> TeamTradeOffer:
        """Create a new trade offer between teams"""
        offer_id = f"trade_{from_team}_{to_team}_{int(datetime.utcnow().timestamp())}"
        offer = TeamTradeOffer(
            offer_id=offer_id,
            from_team=from_team,
            to_team=to_team,
            offering=offering,
            requesting=requesting,
            message=message
        )
        self.trade_offers[offer_id] = offer
        return offer
    
    def get_trade_offer(self, offer_id: str) -> Optional[TeamTradeOffer]:
        """Get a trade offer by ID"""
        return self.trade_offers.get(offer_id)
    
    def get_team_trade_offers(
        self,
        team_number: int,
        include_completed: bool = False
    ) -> List[TeamTradeOffer]:
        """Get all trade offers involving a team"""
        offers = []
        for offer in self.trade_offers.values():
            if offer.from_team == team_number or offer.to_team == team_number:
                if include_completed or offer.status == TradeOfferStatus.PENDING or offer.status == TradeOfferStatus.COUNTERED:
                    offers.append(offer)
        return offers
    
    def execute_team_trade(
        self,
        offer_id: str,
        from_team_resources: Dict[str, int],
        to_team_resources: Dict[str, int]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, int]], Optional[Dict[str, int]]]:
        """
        Execute a team-to-team trade
        
        Returns:
            (success, error_message, updated_from_resources, updated_to_resources)
        """
        offer = self.trade_offers.get(offer_id)
        if not offer:
            return False, "Trade offer not found", None, None
        
        if offer.status != TradeOfferStatus.PENDING and offer.status != TradeOfferStatus.COUNTERED:
            return False, f"Trade offer is {offer.status.value}", None, None
        
        # Determine which resources to use (original or counter offer)
        if offer.status == TradeOfferStatus.COUNTERED and offer.counter_offer:
            offering = offer.counter_offer["offering"]
            requesting = offer.counter_offer["requesting"]
        else:
            offering = offer.offering
            requesting = offer.requesting
        
        # Check if from_team has enough resources
        for resource, amount in offering.items():
            if from_team_resources.get(resource, 0) < amount:
                return False, f"From team has insufficient {resource}", None, None
        
        # Check if to_team has enough resources
        for resource, amount in requesting.items():
            if to_team_resources.get(resource, 0) < amount:
                return False, f"To team has insufficient {resource}", None, None
        
        # Execute trade
        new_from_resources = from_team_resources.copy()
        new_to_resources = to_team_resources.copy()
        
        # from_team gives and receives
        for resource, amount in offering.items():
            new_from_resources[resource] = new_from_resources.get(resource, 0) - amount
        for resource, amount in requesting.items():
            new_from_resources[resource] = new_from_resources.get(resource, 0) + amount
        
        # to_team gives and receives
        for resource, amount in requesting.items():
            new_to_resources[resource] = new_to_resources.get(resource, 0) - amount
        for resource, amount in offering.items():
            new_to_resources[resource] = new_to_resources.get(resource, 0) + amount
        
        # Mark offer as accepted
        offer.accept()
        
        return True, None, new_from_resources, new_to_resources
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize trading manager state"""
        return {
            "pricing_system": self.pricing_system.to_dict(),
            "trade_offers": {
                offer_id: offer.to_dict()
                for offer_id, offer in self.trade_offers.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingManager':
        """Deserialize trading manager state"""
        pricing_system = DynamicPricingSystem.from_dict(data.get("pricing_system", {}))
        manager = cls(pricing_system=pricing_system)
        
        # Restore trade offers
        for offer_id, offer_data in data.get("trade_offers", {}).items():
            manager.trade_offers[offer_id] = TeamTradeOffer.from_dict(offer_data)
        
        return manager
