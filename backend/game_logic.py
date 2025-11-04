"""
Game logic and mechanics for The Trading Game
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from game_constants import (
    ResourceType, BuildingType, NationType, GameEventType,
    NATION_STARTING_RESOURCES, BUILDING_COSTS, BUILDING_PRODUCTION,
    FOOD_TAX_DEVELOPED, FOOD_TAX_DEVELOPING, BANK_INITIAL_PRICES,
    FAMINE_PENALTY_MULTIPLIER, calculate_final_score,
    MAX_HOSPITALS, MAX_RESTAURANTS, MAX_INFRASTRUCTURE
)


class GameLogic:
    """Handles all game logic operations"""
    
    @staticmethod
    def initialize_nation(nation_type: str) -> Dict[str, Any]:
        """
        Initialize a nation's starting state
        
        Args:
            nation_type: NationType enum value (nation_1, nation_2, nation_3, nation_4)
            
        Returns:
            Dictionary with initial resources and buildings
        """
        if nation_type not in [nt.value for nt in NationType]:
            raise ValueError(f"Invalid nation type: {nation_type}")
        
        nation_config = NATION_STARTING_RESOURCES[NationType(nation_type)]
        
        return {
            "nation_type": nation_type,
            "name": nation_config["name"],
            "is_developed": nation_config["is_developed"],
            "resources": {
                resource.value: amount 
                for resource, amount in nation_config["resources"].items()
            },
            "buildings": {
                building.value: count 
                for building, count in nation_config["buildings"].items()
            },
            "optional_buildings": {},
            "last_food_tax": None,
            "trade_history": [],
            "kindness_points": 0
        }
    
    @staticmethod
    def initialize_banker() -> Dict[str, Any]:
        """Initialize banker's state (Central Bank)"""
        return {
            "role": "banker",
            "bank_inventory": {
                resource.value: 1000  # Large starting inventory
                for resource in ResourceType
                if resource != ResourceType.CURRENCY
            },
            "bank_prices": {
                resource.value: price
                for resource, price in BANK_INITIAL_PRICES.items()
            },
            "currency_reserve": 10000,
            "price_history": [],
            "events_triggered": []
        }
    
    @staticmethod
    def can_afford(resources: Dict[str, int], cost: Dict[str, int]) -> Tuple[bool, Optional[str]]:
        """
        Check if a nation can afford a cost
        
        Returns:
            (can_afford: bool, missing_resource: Optional[str])
        """
        for resource, amount in cost.items():
            resource_key = resource.value if hasattr(resource, 'value') else resource
            if resources.get(resource_key, 0) < amount:
                return False, resource_key
        return True, None
    
    @staticmethod
    def deduct_resources(resources: Dict[str, int], cost: Dict[str, int]) -> Dict[str, int]:
        """Deduct resources from a nation's inventory"""
        new_resources = resources.copy()
        for resource, amount in cost.items():
            resource_key = resource.value if hasattr(resource, 'value') else resource
            new_resources[resource_key] = new_resources.get(resource_key, 0) - amount
        return new_resources
    
    @staticmethod
    def add_resources(resources: Dict[str, int], gain: Dict[str, int]) -> Dict[str, int]:
        """Add resources to a nation's inventory"""
        new_resources = resources.copy()
        for resource, amount in gain.items():
            resource_key = resource.value if hasattr(resource, 'value') else resource
            new_resources[resource_key] = new_resources.get(resource_key, 0) + amount
        return new_resources
    
    @staticmethod
    def build_building(
        nation_state: Dict[str, Any],
        building_type: str
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Attempt to build a building
        
        Returns:
            (success: bool, error_message: Optional[str], updated_state: Optional[Dict])
        """
        building = BuildingType(building_type)
        cost = BUILDING_COSTS[building]
        
        # Check if can afford
        can_afford, missing = GameLogic.can_afford(nation_state["resources"], cost)
        if not can_afford:
            return False, f"Insufficient {missing}", None
        
        # Check optional building limits
        if building in [BuildingType.HOSPITAL, BuildingType.RESTAURANT, BuildingType.INFRASTRUCTURE]:
            current_count = nation_state.get("buildings", {}).get(building_type, 0)
            max_count = {
                BuildingType.HOSPITAL: MAX_HOSPITALS,
                BuildingType.RESTAURANT: MAX_RESTAURANTS,
                BuildingType.INFRASTRUCTURE: MAX_INFRASTRUCTURE
            }.get(building, 5)
            
            if current_count >= max_count:
                return False, f"Maximum {building_type} limit reached ({max_count})", None
        
        # Deduct resources
        new_state = nation_state.copy()
        new_state["resources"] = GameLogic.deduct_resources(nation_state["resources"], cost)
        
        # Add building to buildings dict (all buildings stored in same place)
        if "buildings" not in new_state:
            new_state["buildings"] = {}
        new_state["buildings"][building_type] = new_state["buildings"].get(building_type, 0) + 1
        
        return True, None, new_state
    
    @staticmethod
    def produce_resources(
        nation_state: Dict[str, Any],
        building_type: str,
        challenge_completed: bool = True
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Produce resources from a building after physical challenge
        
        Args:
            nation_state: Current nation state
            building_type: Type of building producing
            challenge_completed: Whether physical challenge was completed
            
        Returns:
            (success: bool, error_message: Optional[str], updated_state: Optional[Dict])
        """
        if not challenge_completed:
            return False, "Physical challenge not completed", None
        
        building = BuildingType(building_type)
        production_info = BUILDING_PRODUCTION.get(building)
        
        if not production_info:
            return False, f"Building {building_type} cannot produce", None
        
        # Check if building exists
        building_count = nation_state["buildings"].get(building_type, 0)
        if building_count == 0:
            return False, f"No {building_type} available", None
        
        new_state = nation_state.copy()
        
        # Check if input resources are required
        if production_info["input_required"]:
            total_input_needed = {}
            for resource, amount_per_building in production_info["input_required"].items():
                total_needed = amount_per_building * building_count
                resource_key = resource.value if hasattr(resource, 'value') else resource
                total_input_needed[resource_key] = total_needed
            
            can_afford, missing = GameLogic.can_afford(nation_state["resources"], total_input_needed)
            if not can_afford:
                return False, f"Insufficient {missing} for production", None
            
            # Deduct input resources
            new_state["resources"] = GameLogic.deduct_resources(nation_state["resources"], total_input_needed)
        
        # Add output resources
        output_resource = production_info["output"].value
        output_amount = production_info["amount"] * building_count
        
        new_state["resources"][output_resource] = new_state["resources"].get(output_resource, 0) + output_amount
        
        return True, None, new_state
    
    @staticmethod
    def execute_trade(
        from_state: Dict[str, Any],
        to_state: Dict[str, Any],
        from_gives: Dict[str, int],
        to_gives: Dict[str, int]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Execute a trade between two parties (nation-to-nation or nation-to-bank)
        
        Returns:
            (success, error_message, updated_from_state, updated_to_state)
        """
        # Check if from party can afford
        can_afford, missing = GameLogic.can_afford(from_state["resources"], from_gives)
        if not can_afford:
            return False, f"Sender has insufficient {missing}", None, None
        
        # Check if to party can afford
        can_afford, missing = GameLogic.can_afford(to_state["resources"], to_gives)
        if not can_afford:
            return False, f"Receiver has insufficient {missing}", None, None
        
        # Execute trade
        new_from_state = from_state.copy()
        new_to_state = to_state.copy()
        
        # Deduct from sender, add to receiver
        new_from_state["resources"] = GameLogic.deduct_resources(from_state["resources"], from_gives)
        new_from_state["resources"] = GameLogic.add_resources(new_from_state["resources"], to_gives)
        
        new_to_state["resources"] = GameLogic.deduct_resources(to_state["resources"], to_gives)
        new_to_state["resources"] = GameLogic.add_resources(new_to_state["resources"], from_gives)
        
        # Record trade in history
        trade_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "from_gives": from_gives,
            "to_gives": to_gives
        }
        
        if "trade_history" not in new_from_state:
            new_from_state["trade_history"] = []
        new_from_state["trade_history"].append(trade_record)
        
        return True, None, new_from_state, new_to_state
    
    @staticmethod
    def apply_food_tax(nation_state: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Apply food tax to a nation
        
        Restaurant benefit: Generates currency when food tax is paid
        
        Returns:
            (success, error_message, updated_state)
        """
        is_developed = nation_state.get("is_developed", False)
        tax_amount = FOOD_TAX_DEVELOPED if is_developed else FOOD_TAX_DEVELOPING
        
        new_state = nation_state.copy()
        current_food = nation_state["resources"].get(ResourceType.FOOD.value, 0)
        
        # Get restaurant count for currency generation
        restaurant_count = nation_state.get("buildings", {}).get(BuildingType.RESTAURANT.value, 0)
        
        if current_food >= tax_amount:
            # Can pay tax
            new_state["resources"][ResourceType.FOOD.value] = current_food - tax_amount
            new_state["last_food_tax"] = datetime.utcnow().isoformat()
            
            # Restaurant benefit: Generate currency based on food tax paid
            if restaurant_count > 0:
                from game_constants import BUILDING_BENEFITS
                currency_per_food = BUILDING_BENEFITS[BuildingType.RESTAURANT].get("currency_per_food_tax", 5)
                currency_generated = tax_amount * currency_per_food * restaurant_count
                current_currency = new_state["resources"].get(ResourceType.CURRENCY.value, 0)
                new_state["resources"][ResourceType.CURRENCY.value] = current_currency + currency_generated
                return True, f"Food tax paid. Restaurants generated {currency_generated} currency!", new_state
            
            return True, None, new_state
        else:
            # Famine - must pay bank double rate
            shortage = tax_amount - current_food
            cost_currency = shortage * BANK_INITIAL_PRICES[ResourceType.FOOD] * FAMINE_PENALTY_MULTIPLIER
            
            current_currency = nation_state["resources"].get(ResourceType.CURRENCY.value, 0)
            if current_currency >= cost_currency:
                new_state["resources"][ResourceType.FOOD.value] = 0
                new_state["resources"][ResourceType.CURRENCY.value] = current_currency - cost_currency
                new_state["last_food_tax"] = datetime.utcnow().isoformat()
                return True, f"FAMINE: Paid {cost_currency} currency for {shortage} food shortage", new_state
            else:
                return False, f"Cannot pay food tax or famine penalty. Need {shortage} food or {cost_currency} currency", None
    
    @staticmethod
    def calculate_score(nation_state: Dict[str, Any], bank_prices: Dict[str, int]) -> Dict[str, Any]:
        """Calculate final score for a nation"""
        state_with_prices = nation_state.copy()
        state_with_prices["bank_prices"] = bank_prices
        return calculate_final_score(state_with_prices)
    
    @staticmethod
    def apply_disaster(
        nation_state: Dict[str, Any],
        disaster_type: str,
        severity: int = 1
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Apply a disaster event to a nation
        
        Hospital benefit: Reduces disease impact (20% per hospital, max 5)
        Infrastructure benefit: Reduces drought impact (20% per infrastructure, max 5)
        
        Args:
            disaster_type: Type of disaster (natural_disaster, drought, disease, etc.)
            severity: Severity level (1-5)
        """
        from game_constants import BUILDING_BENEFITS
        
        new_state = nation_state.copy()
        message = ""
        
        if disaster_type == "natural_disaster":
            # Destroy buildings or resources
            # Implementation depends on specific rules
            message = f"Natural disaster struck! Severity: {severity}"
        
        elif disaster_type == "drought":
            # Infrastructure benefit: Reduce drought impact
            infrastructure_count = new_state.get("buildings", {}).get(BuildingType.INFRASTRUCTURE.value, 0)
            reduction = min(infrastructure_count * BUILDING_BENEFITS[BuildingType.INFRASTRUCTURE]["drought_reduction_per_building"], 1.0)
            
            # Apply reduced drought impact
            effective_severity = severity * (1.0 - reduction)
            
            if effective_severity > 0:
                message = f"Drought occurred! Production reduced by {int(effective_severity * 100)}% (Infrastructure reduced impact by {int(reduction * 100)}%)"
            else:
                message = f"Drought occurred but Infrastructure completely negated the impact!"
        
        elif disaster_type == "disease":
            # Hospital benefit: Reduce disease impact
            hospital_count = new_state.get("buildings", {}).get(BuildingType.HOSPITAL.value, 0)
            reduction = min(hospital_count * BUILDING_BENEFITS[BuildingType.HOSPITAL]["disease_reduction_per_building"], 1.0)
            
            # Calculate medical goods needed after hospital reduction
            base_medical_needed = severity * 10
            medical_needed = int(base_medical_needed * (1.0 - reduction))
            
            if medical_needed > 0:
                current_medical = new_state["resources"].get(ResourceType.MEDICAL_GOODS.value, 0)
                if current_medical >= medical_needed:
                    new_state["resources"][ResourceType.MEDICAL_GOODS.value] = current_medical - medical_needed
                    message = f"Disease outbreak! Spent {medical_needed} medical goods (Hospitals reduced impact by {int(reduction * 100)}%)"
                else:
                    message = f"Disease outbreak! Need {medical_needed} medical goods but only have {current_medical} (Hospitals reduced impact by {int(reduction * 100)}%)"
            else:
                message = f"Disease outbreak but Hospitals completely negated the impact!"
        
        return True, message, new_state
