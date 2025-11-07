"""
Game constants and rules based on Trading Game Rules and Setup
"""

from enum import Enum
from typing import Dict, List

# ==================== Game Difficulty ====================

class GameDifficulty(str, Enum):
    """Game difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# Difficulty modifiers for starting resources
# Easy: +25% resources, Medium: 0% (baseline), Hard: -25% resources
# Buildings are NOT affected by difficulty
DIFFICULTY_MODIFIERS = {
    GameDifficulty.EASY: 1.25,      # 25% more starting resources
    GameDifficulty.MEDIUM: 1.0,     # Normal baseline
    GameDifficulty.HARD: 0.75       # 25% fewer starting resources
}


# ==================== Resources ====================

class ResourceType(str, Enum):
    """Types of resources in the game"""
    FOOD = "food"
    RAW_MATERIALS = "raw_materials"
    ELECTRICAL_GOODS = "electrical_goods"
    MEDICAL_GOODS = "medical_goods"
    CURRENCY = "currency"


# ==================== Buildings ====================

class BuildingType(str, Enum):
    """Types of buildings that can be built"""
    FARM = "farm"
    MINE = "mine"
    ELECTRICAL_FACTORY = "electrical_factory"
    MEDICAL_FACTORY = "medical_factory"
    # Optional buildings
    SCHOOL = "school"
    HOSPITAL = "hospital"
    RESTAURANT = "restaurant"
    INFRASTRUCTURE = "infrastructure"


# Building costs (currency and resources required)
BUILDING_COSTS = {
    BuildingType.FARM: {
        ResourceType.CURRENCY: 50,
        ResourceType.RAW_MATERIALS: 30
    },
    BuildingType.MINE: {
        ResourceType.CURRENCY: 50,
        ResourceType.RAW_MATERIALS: 30,
        ResourceType.ELECTRICAL_GOODS: 5
    },
    BuildingType.ELECTRICAL_FACTORY: {
        ResourceType.CURRENCY: 200,
        ResourceType.RAW_MATERIALS: 50,
        ResourceType.ELECTRICAL_GOODS: 30
    },
    BuildingType.MEDICAL_FACTORY: {
        ResourceType.CURRENCY: 200,
        ResourceType.RAW_MATERIALS: 50,
        ResourceType.FOOD: 20,
        ResourceType.ELECTRICAL_GOODS: 15
    },
    BuildingType.SCHOOL: {
        ResourceType.CURRENCY: 100,
        ResourceType.RAW_MATERIALS: 30
    },
    BuildingType.HOSPITAL: {
        ResourceType.CURRENCY: 300,
        ResourceType.RAW_MATERIALS: 50,
        ResourceType.ELECTRICAL_GOODS: 10,
        ResourceType.MEDICAL_GOODS: 10
    },
    BuildingType.RESTAURANT: {
        ResourceType.CURRENCY: 200,
        ResourceType.RAW_MATERIALS: 50,
        ResourceType.FOOD: 25,
        ResourceType.ELECTRICAL_GOODS: 5
    },
    BuildingType.INFRASTRUCTURE: {
        ResourceType.CURRENCY: 300,
        ResourceType.RAW_MATERIALS: 50,
        ResourceType.ELECTRICAL_GOODS: 10
    }
}

# Building production outputs (per building)
BUILDING_PRODUCTION = {
    BuildingType.FARM: {
        "output": ResourceType.FOOD,
        "amount": 5,
        "input_required": None,
        "requires_full_team_default": True  # True without School, False with School
    },
    BuildingType.MINE: {
        "output": ResourceType.RAW_MATERIALS,
        "amount": 5,
        "input_required": None,
        "requires_full_team_default": True  # True without School, False with School
    },
    BuildingType.ELECTRICAL_FACTORY: {
        "output": ResourceType.ELECTRICAL_GOODS,
        "amount": 5,
        "input_required": {ResourceType.RAW_MATERIALS: 5},
        "requires_full_team_default": True  # True without School, False with School
    },
    BuildingType.MEDICAL_FACTORY: {
        "output": ResourceType.MEDICAL_GOODS,
        "amount": 5,
        "input_required": {ResourceType.FOOD: 5},
        "requires_full_team_default": True  # True without School, False with School
    }
}


def requires_full_team_for_production(building_type: BuildingType, has_school: bool) -> bool:
    """
    Determine if a building requires the full team for production.
    
    School effect: If a nation has a School, production buildings (Farm, Mine) 
    only require a single team member instead of the full team.
    
    Parameters:
        building_type: The type of building being used for production
        has_school: Whether the nation has built at least one School
    
    Returns:
        True if full team is required, False if single member can operate
    """
    production_info = BUILDING_PRODUCTION.get(building_type)
    if not production_info:
        return False
    
    requires_full_team_default = production_info.get("requires_full_team_default", False)
    
    # If building normally requires full team AND nation has a School, only single member needed
    if requires_full_team_default and has_school:
        return False
    
    return requires_full_team_default

# Building scoring (double currency value)
BUILDING_SCORES = {
    building: cost.get(ResourceType.CURRENCY, 0) * 2
    for building, cost in BUILDING_COSTS.items()
}


# ==================== Nations ====================

class NationType(str, Enum):
    """Types of nations (4 total)"""
    NATION_1_FOOD = "nation_1"  # Developed - Food focus
    NATION_2_RAW = "nation_2"   # Developed - Raw Materials focus
    NATION_3_ELEC = "nation_3"  # Developing - Electrical focus
    NATION_4_MED = "nation_4"   # Developing - Medical focus


# Starting resources for each nation
NATION_STARTING_RESOURCES = {
    NationType.NATION_1_FOOD: {
        "buildings": {
            BuildingType.FARM: 3,
            BuildingType.MINE: 1
        },
        "resources": {
            ResourceType.FOOD: 30,
            ResourceType.CURRENCY: 50
        },
        "is_developed": True,
        "name": "Nation 1 (Food Producer)"
    },
    NationType.NATION_2_RAW: {
        "buildings": {
            BuildingType.MINE: 3,
            BuildingType.FARM: 1
        },
        "resources": {
            ResourceType.FOOD: 5,
            ResourceType.RAW_MATERIALS: 25,
            ResourceType.CURRENCY: 50
        },
        "is_developed": True,
        "name": "Nation 2 (Raw Materials Producer)"
    },
    NationType.NATION_3_ELEC: {
        "buildings": {
            BuildingType.ELECTRICAL_FACTORY: 3,
            BuildingType.FARM: 1
        },
        "resources": {
            ResourceType.FOOD: 30,
            ResourceType.RAW_MATERIALS: 30,
            ResourceType.CURRENCY: 200
        },
        "is_developed": False,
        "name": "Nation 3 (Electrical Goods Producer)"
    },
    NationType.NATION_4_MED: {
        "buildings": {
            BuildingType.MEDICAL_FACTORY: 3,
            BuildingType.MINE: 1
        },
        "resources": {
            ResourceType.FOOD: 30,
            ResourceType.RAW_MATERIALS: 30,
            ResourceType.CURRENCY: 200
        },
        "is_developed": False,
        "name": "Nation 4 (Medical Goods Producer)"
    }
}


# ==================== Game Events ====================

class GameEventType(str, Enum):
    """Types of game events"""
    # Trading
    TRADE_NATION_TO_NATION = "trade_nation_to_nation"
    TRADE_NATION_TO_BANK = "trade_nation_to_bank"
    
    # Production
    PRODUCTION_COMPLETE = "production_complete"
    BUILDING_CONSTRUCTED = "building_constructed"
    
    # Bank events
    FOOD_TAX = "food_tax"
    NATURAL_DISASTER = "natural_disaster"
    FAMINE = "famine"
    DROUGHT = "drought"
    DISEASE = "disease"
    CLIMATE_CHANGE = "climate_change"
    SPECIAL_EVENT = "special_event"
    
    # Game control
    GAME_STARTED = "game_started"
    GAME_PAUSED = "game_paused"
    GAME_RESUMED = "game_resumed"
    GAME_ENDED = "game_ended"


# Special events (like Olympics)
SPECIAL_EVENTS = {
    "OLYMPICS": {
        "cost_to_host": {
            ResourceType.FOOD: 25,
            ResourceType.RAW_MATERIALS: 25,
            ResourceType.ELECTRICAL_GOODS: 10,
            ResourceType.MEDICAL_GOODS: 5,
            ResourceType.CURRENCY: 100
        },
        "return": {
            "multiplier": 5
        },
        "is_developed": True
    }
}


# ==================== Taxes and Penalties ====================

# Food tax amounts (every 15 minutes)
FOOD_TAX_DEVELOPED = 15  # Higher for developed nations
FOOD_TAX_DEVELOPING = 5  # Lower for developing nations
FOOD_TAX_INTERVAL_MINUTES = 15

# Famine penalty (if nation can't pay food tax)
FAMINE_PENALTY_MULTIPLIER = 2  # Pay double to bank


# ==================== Central Bank ====================

# Initial bank prices (adjustable during game)
BANK_INITIAL_PRICES = {
    ResourceType.FOOD: 2,
    ResourceType.RAW_MATERIALS: 3,
    ResourceType.ELECTRICAL_GOODS: 15,
    ResourceType.MEDICAL_GOODS: 20
}

# Optional buildings limits
MAX_HOSPITALS = 5
MAX_RESTAURANTS = 5
MAX_INFRASTRUCTURE = 5

# Optional building benefits
BUILDING_BENEFITS = {
    BuildingType.SCHOOL: {
        "description": "Allows single team member to use factories",
        "effect": "Farm and Mine production only requires 1 team member instead of full team. Increases food tax."
    },
    BuildingType.HOSPITAL: {
        "description": "Reduces disease impact",
        "effect": "Each hospital reduces disease impact by 20%. Max 5 hospitals = no disease impact.",
        "disease_reduction_per_building": 0.2  # 20% reduction per hospital
    },
    BuildingType.RESTAURANT: {
        "description": "Generates currency on food tax payment",
        "effect": "Generates currency every time food tax is paid. Amount scales with food tax level. Max 5 restaurants.",
        "currency_per_food_tax": 5  # Base currency per food unit taxed, scales with restaurant count
    },
    BuildingType.INFRASTRUCTURE: {
        "description": "Reduces drought impact",
        "effect": "Each infrastructure reduces drought impact by 20%. Max 5 infrastructure = no drought impact.",
        "drought_reduction_per_building": 0.2  # 20% reduction per infrastructure
    }
}


# ==================== Physical Challenges ====================

class ChallengeType(str, Enum):
    """Types of physical challenges for production"""
    PRESS_UPS = "press_ups"
    SIT_UPS = "sit_ups"
    SPRINT_LENGTHS = "sprint_lengths"
    BURPEES = "burpees"
    SKIPPING = "skipping"
    STAR_JUMPS = "star_jumps"


# Default challenge requirements (can be adjusted by bank)
DEFAULT_CHALLENGE_REQUIREMENTS = {
    BuildingType.FARM: {"type": ChallengeType.PRESS_UPS, "count": 20},
    BuildingType.MINE: {"type": ChallengeType.SIT_UPS, "count": 30},
    BuildingType.ELECTRICAL_FACTORY: {"type": ChallengeType.BURPEES, "count": 15},
    BuildingType.MEDICAL_FACTORY: {"type": ChallengeType.STAR_JUMPS, "count": 25}
}


# ==================== Scoring ====================

# Kindness scoring configuration
KINDNESS_FACTOR = 0.15  # 15% impact per unit of average margin
MIN_KINDNESS_MODIFIER = 0.5  # Minimum 50% of base score (caps penalty)
MAX_KINDNESS_MODIFIER = 1.5  # Maximum 150% of base score (caps bonus)

def calculate_kindness_modifier(trade_margins: List[Dict]) -> Dict:
    """
    Calculate the kindness modifier based on trade history.
    
    Args:
        trade_margins: List of trade margin records, each with 'margin' and 'trade_value'
                      Negative margins = generous trades, Positive = profitable trades
    
    Returns:
        Dictionary with 'modifier' (float), 'avg_margin' (float), and 'label' (str)
    """
    if not trade_margins:
        return {
            'modifier': 1.0,
            'avg_margin': 0.0,
            'label': 'No Trades'
        }
    
    # Calculate weighted average margin (larger trades have more influence)
    total_weighted_margin = 0.0
    total_weight = 0.0
    
    for trade in trade_margins:
        margin = trade.get('margin', 0.0)
        trade_value = trade.get('trade_value', 1.0)  # Use 1.0 as default weight
        
        total_weighted_margin += margin * trade_value
        total_weight += trade_value
    
    avg_margin = total_weighted_margin / total_weight if total_weight > 0 else 0.0
    
    # Calculate modifier: 1 - (avg_margin * kindness_factor)
    # Negative margins (losses) increase the modifier (reward) since subtracting a negative adds
    # Positive margins (profits) decrease the modifier (penalty)
    modifier = 1.0 - (avg_margin * KINDNESS_FACTOR)
    
    # Apply bounds to prevent extreme modifiers
    modifier = max(MIN_KINDNESS_MODIFIER, min(MAX_KINDNESS_MODIFIER, modifier))
    
    # Determine label
    if avg_margin <= -0.2:
        label = "Generous Trader"
    elif avg_margin <= -0.05:
        label = "Fair Trader"
    elif avg_margin < 0.05:
        label = "Balanced Trader"
    elif avg_margin < 0.2:
        label = "Shrewd Trader"
    else:
        label = "Profit-Focused"
    
    return {
        'modifier': round(modifier, 4),
        'avg_margin': round(avg_margin, 4),
        'label': label
    }

def calculate_final_score(nation_state: Dict) -> Dict:
    """
    Calculate final score for a nation based on:
    - Resources at current bank value
    - Buildings at double their currency cost
    - Trade deals
    - Donations/kindness
    - Trade fairness modifier (kindness-based)
    """
    score = {
        "resource_value": 0,
        "building_value": 0,
        "trade_value": 0,
        "kindness_value": 0,
        "base_total": 0,
        "kindness_modifier": 1.0,
        "kindness_label": "No Trades",
        "total": 0
    }
    
    # Calculate resource values
    bank_prices = nation_state.get("bank_prices", BANK_INITIAL_PRICES)
    for resource, amount in nation_state.get("resources", {}).items():
        if resource in bank_prices:
            score["resource_value"] += amount * bank_prices[resource]
    
    # Calculate building values (double currency cost)
    for building, count in nation_state.get("buildings", {}).items():
        score["building_value"] += BUILDING_SCORES.get(building, 0) * count
    
    # Add trade and kindness values
    score["trade_value"] = nation_state.get("trade_value", 0)
    score["kindness_value"] = nation_state.get("kindness_value", 0)
    
    # Calculate base total before kindness modifier
    score["base_total"] = (
        score["resource_value"] + 
        score["building_value"] + 
        score["trade_value"] + 
        score["kindness_value"]
    )
    
    # Apply kindness modifier based on trade history
    trade_margins = nation_state.get("trade_margins", [])
    if trade_margins:
        kindness_data = calculate_kindness_modifier(trade_margins)
        score["kindness_modifier"] = kindness_data['modifier']
        score["kindness_label"] = kindness_data['label']
        score["avg_trade_margin"] = kindness_data['avg_margin']
    
    # Calculate final total with kindness modifier
    score["total"] = int(score["base_total"] * score["kindness_modifier"])
    
    return score


# ==================== Game Rules ====================

GAME_RULES = {
    "objective": "To get the greatest result possible in the time available (most financial capital or most kind-hearted nation)",
    "player_rules": [
        "One person must be at the nation location at all times",
        "International (inter-nation) trade is encouraged",
        "Trading with Central Bank is permitted",
        "Any creative opportunity outside the rules should be run via Central Bank first"
    ],
    "bank_powers": [
        "Can buy and sell resources (prices adjust as required)",
        "Implements food tax every 15 minutes",
        "Can trigger natural disasters, famines, droughts, diseases, climate change",
        "Can add, remove, or change rules throughout the game"
    ]
}
