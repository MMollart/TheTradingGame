"""
Game constants and rules based on Trading Game Rules and Setup
"""

from enum import Enum
from typing import Dict, List

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
        "requires_full_team": True
    },
    BuildingType.MINE: {
        "output": ResourceType.RAW_MATERIALS,
        "amount": 5,
        "input_required": None,
        "requires_full_team": True
    },
    BuildingType.ELECTRICAL_FACTORY: {
        "output": ResourceType.ELECTRICAL_GOODS,
        "amount": 5,
        "input_required": {ResourceType.RAW_MATERIALS: 5},
        "requires_full_team": False
    },
    BuildingType.MEDICAL_FACTORY: {
        "output": ResourceType.MEDICAL_GOODS,
        "amount": 5,
        "input_required": {ResourceType.FOOD: 5},
        "requires_full_team": False
    }
}

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
    
    # Game control
    GAME_STARTED = "game_started"
    GAME_PAUSED = "game_paused"
    GAME_RESUMED = "game_resumed"
    GAME_ENDED = "game_ended"


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

def calculate_final_score(nation_state: Dict) -> Dict:
    """
    Calculate final score for a nation based on:
    - Resources at current bank value
    - Buildings at double their currency cost
    - Trade deals
    - Donations/kindness
    """
    score = {
        "resource_value": 0,
        "building_value": 0,
        "trade_value": 0,
        "kindness_value": 0,
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
    
    score["total"] = sum(score.values())
    
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
