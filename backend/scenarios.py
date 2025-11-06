"""
Historical Scenarios for The Trading Game

This module defines historical scenarios with custom resources and buildings.
Each scenario can override the default game resources (food, raw_materials, etc.)
with themed alternatives (e.g., Space Race uses Knowledge, Liquid Fuels, etc.)
"""

from typing import Dict, List, Any, Optional
from game_constants import ResourceType, BuildingType


class ScenarioType:
    """Historical scenario identifiers"""
    MARSHALL_PLAN = "marshall_plan"
    SILK_ROAD = "silk_road"
    INDUSTRIAL_REVOLUTION = "industrial_revolution"
    SPACE_RACE = "space_race"
    AGE_OF_EXPLORATION = "age_of_exploration"
    GREAT_DEPRESSION = "great_depression"


# Scenario-specific resource definitions
# Each scenario can define custom resources that replace the default ones
SCENARIO_RESOURCES = {
    ScenarioType.SPACE_RACE: {
        "resource_1": {
            "id": "knowledge",
            "name": "Knowledge",
            "icon": "📚",
            "description": "Scientific research and expertise",
            "base_price": 3,
            "rarity": "common",
            "maps_to": ResourceType.FOOD  # Maps to default resource slot
        },
        "resource_2": {
            "id": "liquid_fuels",
            "name": "Liquid Fuels",
            "icon": "🛢️",
            "description": "Rocket propellants and fuel",
            "base_price": 5,
            "rarity": "uncommon",
            "maps_to": ResourceType.RAW_MATERIALS
        },
        "resource_3": {
            "id": "metals",
            "name": "Metals",
            "icon": "🔩",
            "description": "Titanium, aluminum, and steel",
            "base_price": 20,
            "rarity": "rare",
            "maps_to": ResourceType.ELECTRICAL_GOODS
        },
        "resource_4": {
            "id": "electronics",
            "name": "Electronics",
            "icon": "💻",
            "description": "Silicon chips and computing components",
            "base_price": 25,
            "rarity": "rare",
            "maps_to": ResourceType.MEDICAL_GOODS
        }
    },
    ScenarioType.MARSHALL_PLAN: {
        # Marshall Plan uses default resources with themed names
        "resource_1": {
            "id": "food",
            "name": "Food Supplies",
            "icon": "🌾",
            "description": "Agricultural products and food aid",
            "base_price": 2,
            "rarity": "common",
            "maps_to": ResourceType.FOOD
        },
        "resource_2": {
            "id": "raw_materials",
            "name": "Construction Materials",
            "icon": "🏗️",
            "description": "Steel, timber, and building supplies",
            "base_price": 3,
            "rarity": "common",
            "maps_to": ResourceType.RAW_MATERIALS
        },
        "resource_3": {
            "id": "machinery",
            "name": "Machinery",
            "icon": "⚙️",
            "description": "Industrial equipment",
            "base_price": 15,
            "rarity": "uncommon",
            "maps_to": ResourceType.ELECTRICAL_GOODS
        },
        "resource_4": {
            "id": "medical_supplies",
            "name": "Medical Supplies",
            "icon": "💊",
            "description": "Medicine and healthcare equipment",
            "base_price": 20,
            "rarity": "rare",
            "maps_to": ResourceType.MEDICAL_GOODS
        }
    },
    ScenarioType.SILK_ROAD: {
        "resource_1": {
            "id": "food",
            "name": "Food & Grain",
            "icon": "🌾",
            "description": "Rice, wheat, and provisions",
            "base_price": 2,
            "rarity": "common",
            "maps_to": ResourceType.FOOD
        },
        "resource_2": {
            "id": "raw_materials",
            "name": "Raw Silk",
            "icon": "🧵",
            "description": "Unprocessed silk thread",
            "base_price": 4,
            "rarity": "uncommon",
            "maps_to": ResourceType.RAW_MATERIALS
        },
        "resource_3": {
            "id": "luxury_goods",
            "name": "Luxury Goods",
            "icon": "💎",
            "description": "Porcelain, jade, and fine textiles",
            "base_price": 18,
            "rarity": "rare",
            "maps_to": ResourceType.ELECTRICAL_GOODS
        },
        "resource_4": {
            "id": "spices",
            "name": "Spices & Perfumes",
            "icon": "🌶️",
            "description": "Exotic spices and fragrances",
            "base_price": 22,
            "rarity": "rare",
            "maps_to": ResourceType.MEDICAL_GOODS
        }
    },
    ScenarioType.INDUSTRIAL_REVOLUTION: {
        "resource_1": {
            "id": "food",
            "name": "Food",
            "icon": "🌾",
            "description": "Agricultural products",
            "base_price": 2,
            "rarity": "common",
            "maps_to": ResourceType.FOOD
        },
        "resource_2": {
            "id": "coal_iron",
            "name": "Coal & Iron",
            "icon": "⛏️",
            "description": "Mining resources",
            "base_price": 3,
            "rarity": "common",
            "maps_to": ResourceType.RAW_MATERIALS
        },
        "resource_3": {
            "id": "textiles",
            "name": "Textiles",
            "icon": "🧶",
            "description": "Cotton and wool products",
            "base_price": 15,
            "rarity": "uncommon",
            "maps_to": ResourceType.ELECTRICAL_GOODS
        },
        "resource_4": {
            "id": "labor",
            "name": "Labor Services",
            "icon": "👷",
            "description": "Worker availability and welfare",
            "base_price": 20,
            "rarity": "rare",
            "maps_to": ResourceType.MEDICAL_GOODS
        }
    },
    ScenarioType.AGE_OF_EXPLORATION: {
        "resource_1": {
            "id": "food",
            "name": "Provisions",
            "icon": "🥖",
            "description": "Ship provisions and supplies",
            "base_price": 2,
            "rarity": "common",
            "maps_to": ResourceType.FOOD
        },
        "resource_2": {
            "id": "timber_naval_stores",
            "name": "Timber & Naval Stores",
            "icon": "🌲",
            "description": "Shipbuilding materials",
            "base_price": 4,
            "rarity": "uncommon",
            "maps_to": ResourceType.RAW_MATERIALS
        },
        "resource_3": {
            "id": "colonial_goods",
            "name": "Colonial Goods",
            "icon": "📦",
            "description": "Sugar, tobacco, and trade goods",
            "base_price": 16,
            "rarity": "uncommon",
            "maps_to": ResourceType.ELECTRICAL_GOODS
        },
        "resource_4": {
            "id": "precious_metals",
            "name": "Precious Metals",
            "icon": "🏆",
            "description": "Gold and silver from colonies",
            "base_price": 25,
            "rarity": "rare",
            "maps_to": ResourceType.MEDICAL_GOODS
        }
    },
    ScenarioType.GREAT_DEPRESSION: {
        "resource_1": {
            "id": "food",
            "name": "Food",
            "icon": "🌾",
            "description": "Essential food supplies",
            "base_price": 3,
            "rarity": "uncommon",
            "maps_to": ResourceType.FOOD
        },
        "resource_2": {
            "id": "raw_materials",
            "name": "Raw Materials",
            "icon": "⚙️",
            "description": "Industrial materials",
            "base_price": 4,
            "rarity": "uncommon",
            "maps_to": ResourceType.RAW_MATERIALS
        },
        "resource_3": {
            "id": "manufactured_goods",
            "name": "Manufactured Goods",
            "icon": "📻",
            "description": "Factory products",
            "base_price": 18,
            "rarity": "rare",
            "maps_to": ResourceType.ELECTRICAL_GOODS
        },
        "resource_4": {
            "id": "employment",
            "name": "Employment",
            "icon": "💼",
            "description": "Jobs and economic activity",
            "base_price": 22,
            "rarity": "rare",
            "maps_to": ResourceType.MEDICAL_GOODS
        }
    }
}

# Scenario-specific building definitions
SCENARIO_BUILDINGS = {
    ScenarioType.SPACE_RACE: {
        "building_1": {
            "id": "library",
            "name": "Research Library",
            "icon": "📖",
            "description": "Produces Knowledge",
            "produces": "knowledge",
            "maps_to": BuildingType.FARM
        },
        "building_2": {
            "id": "fuel_depot",
            "name": "Fuel Refinery",
            "icon": "🏭",
            "description": "Produces Liquid Fuels",
            "produces": "liquid_fuels",
            "maps_to": BuildingType.MINE
        },
        "building_3": {
            "id": "metal_works",
            "name": "Metalworks",
            "icon": "🔨",
            "description": "Produces Metals from Liquid Fuels",
            "produces": "metals",
            "requires": "liquid_fuels",
            "maps_to": BuildingType.ELECTRICAL_FACTORY
        },
        "building_4": {
            "id": "tech_lab",
            "name": "Electronics Lab",
            "icon": "🔬",
            "description": "Produces Electronics from Knowledge",
            "produces": "electronics",
            "requires": "knowledge",
            "maps_to": BuildingType.MEDICAL_FACTORY
        }
    }
    # Other scenarios use default buildings with their default resource mappings
}


def get_scenario_resources(scenario_id: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """
    Get resource definitions for a scenario.
    Returns default resources if scenario has no custom resources.
    
    Args:
        scenario_id: Scenario identifier or None for default game
        
    Returns:
        Dictionary of resource definitions with structure:
        {
            "resource_1": {
                "id": "knowledge",
                "name": "Knowledge",
                "icon": "📚",
                "description": "Scientific research and expertise",
                "base_price": 3,
                "rarity": "common",
                "maps_to": ResourceType.FOOD
            },
            ...
        }
    
    Example:
        >>> resources = get_scenario_resources("space_race")
        >>> resources["resource_1"]["name"]
        'Knowledge'
    """
    if scenario_id and scenario_id in SCENARIO_RESOURCES:
        return SCENARIO_RESOURCES[scenario_id]
    
    # Return default resources
    return {
        "resource_1": {
            "id": "food",
            "name": "Food",
            "icon": "🌾",
            "description": "Agricultural products",
            "base_price": 2,
            "rarity": "common",
            "maps_to": ResourceType.FOOD
        },
        "resource_2": {
            "id": "raw_materials",
            "name": "Raw Materials",
            "icon": "⛏️",
            "description": "Mining and construction materials",
            "base_price": 3,
            "rarity": "common",
            "maps_to": ResourceType.RAW_MATERIALS
        },
        "resource_3": {
            "id": "electrical_goods",
            "name": "Electrical Goods",
            "icon": "⚡",
            "description": "Electronic products",
            "base_price": 15,
            "rarity": "uncommon",
            "maps_to": ResourceType.ELECTRICAL_GOODS
        },
        "resource_4": {
            "id": "medical_goods",
            "name": "Medical Goods",
            "icon": "🏥",
            "description": "Healthcare products",
            "base_price": 20,
            "rarity": "rare",
            "maps_to": ResourceType.MEDICAL_GOODS
        }
    }


def get_scenario_buildings(scenario_id: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """
    Get building definitions for a scenario.
    Returns default buildings if scenario has no custom buildings.
    
    Args:
        scenario_id: Scenario identifier or None for default game
        
    Returns:
        Dictionary of building definitions with structure:
        {
            "building_1": {
                "id": "library",
                "name": "Research Library",
                "icon": "📖",
                "description": "Produces Knowledge",
                "produces": "knowledge",
                "maps_to": BuildingType.FARM
            },
            ...
        }
    
    Example:
        >>> buildings = get_scenario_buildings("space_race")
        >>> buildings["building_1"]["name"]
        'Research Library'
    """
    if scenario_id and scenario_id in SCENARIO_BUILDINGS:
        return SCENARIO_BUILDINGS[scenario_id]
    
    # Return default buildings
    return {
        "building_1": {
            "id": "farm",
            "name": "Farm",
            "icon": "🚜",
            "description": "Produces Food",
            "produces": "food",
            "maps_to": BuildingType.FARM
        },
        "building_2": {
            "id": "mine",
            "name": "Mine",
            "icon": "⛏️",
            "description": "Produces Raw Materials",
            "produces": "raw_materials",
            "maps_to": BuildingType.MINE
        },
        "building_3": {
            "id": "electrical_factory",
            "name": "Electrical Factory",
            "icon": "⚡",
            "description": "Produces Electrical Goods from Raw Materials",
            "produces": "electrical_goods",
            "requires": "raw_materials",
            "maps_to": BuildingType.ELECTRICAL_FACTORY
        },
        "building_4": {
            "id": "medical_factory",
            "name": "Medical Factory",
            "icon": "🏥",
            "description": "Produces Medical Goods from Food",
            "produces": "medical_goods",
            "requires": "food",
            "maps_to": BuildingType.MEDICAL_FACTORY
        }
    }


def get_resource_price(scenario_id: Optional[str], resource_id: str, difficulty: str = "medium") -> int:
    """
    Calculate resource price based on scenario, resource rarity, and difficulty.
    
    Args:
        scenario_id: Scenario identifier or None
        resource_id: Resource identifier  
        difficulty: Game difficulty (easy/medium/hard)
        
    Returns:
        Base price for the resource
    """
    resources = get_scenario_resources(scenario_id)
    
    # Find the resource
    resource_def = None
    for res in resources.values():
        if res["id"] == resource_id:
            resource_def = res
            break
    
    if not resource_def:
        return 10  # Default fallback price
    
    base_price = resource_def["base_price"]
    
    # Apply difficulty multiplier
    difficulty_multipliers = {
        "easy": 0.8,      # 20% cheaper in easy mode
        "medium": 1.0,    # Normal price
        "hard": 1.3       # 30% more expensive in hard mode
    }
    
    multiplier = difficulty_multipliers.get(difficulty, 1.0)
    
    return int(base_price * multiplier)


# Define historical scenarios with complete configurations
SCENARIOS = {
    ScenarioType.MARSHALL_PLAN: {
        "id": ScenarioType.MARSHALL_PLAN,
        "name": "Post-WWII Marshall Plan",
        "period": "1948-1952",
        "difficulty": "medium",
        "recommended_duration": 120,  # minutes
        "min_duration": 90,
        "max_duration": 120,
        "description": "Four European nations compete to rebuild after WWII using American aid. Teams must balance infrastructure development, industrial production, and maintaining food security for their populations.",
        
        "nation_profiles": {
            "1": {
                "name": "Britain",
                "description": "Strong starting infrastructure, moderate resources",
                "starting_resources": {
                    ResourceType.FOOD: 40,
                    ResourceType.RAW_MATERIALS: 30,
                    ResourceType.ELECTRICAL_GOODS: 10,
                    ResourceType.MEDICAL_GOODS: 5,
                    ResourceType.CURRENCY: 150
                },
                "starting_buildings": {
                    BuildingType.INFRASTRUCTURE: 2,
                    BuildingType.FARM: 2,
                    BuildingType.MINE: 1
                }
            },
            "2": {
                "name": "France",
                "description": "Agricultural strength, needs industrial development",
                "starting_resources": {
                    ResourceType.FOOD: 60,
                    ResourceType.RAW_MATERIALS: 20,
                    ResourceType.ELECTRICAL_GOODS: 5,
                    ResourceType.MEDICAL_GOODS: 5,
                    ResourceType.CURRENCY: 100
                },
                "starting_buildings": {
                    BuildingType.FARM: 4,
                    BuildingType.MINE: 1,
                    BuildingType.INFRASTRUCTURE: 1
                }
            },
            "3": {
                "name": "West Germany",
                "description": "Industrial potential, low starting resources",
                "starting_resources": {
                    ResourceType.FOOD: 25,
                    ResourceType.RAW_MATERIALS: 15,
                    ResourceType.ELECTRICAL_GOODS: 5,
                    ResourceType.MEDICAL_GOODS: 3,
                    ResourceType.CURRENCY: 50
                },
                "starting_buildings": {
                    BuildingType.ELECTRICAL_FACTORY: 2,
                    BuildingType.FARM: 1,
                    BuildingType.MINE: 1
                }
            },
            "4": {
                "name": "Italy",
                "description": "Balanced but resource-poor, must trade aggressively",
                "starting_resources": {
                    ResourceType.FOOD: 30,
                    ResourceType.RAW_MATERIALS: 20,
                    ResourceType.ELECTRICAL_GOODS: 5,
                    ResourceType.MEDICAL_GOODS: 5,
                    ResourceType.CURRENCY: 75
                },
                "starting_buildings": {
                    BuildingType.FARM: 2,
                    BuildingType.MINE: 2,
                    BuildingType.MEDICAL_FACTORY: 1
                }
            }
        },
        
        "special_rules": [
            {
                "name": "Marshall Aid Rounds",
                "description": "Banker distributes bonus currency every 20 minutes (decreasing amounts)",
                "implementation": "banker_event",
                "parameters": {
                    "interval_minutes": 20,
                    "amounts": [100, 75, 50, 25]  # Decreasing aid amounts
                }
            },
            {
                "name": "Cold War Effect",
                "description": "Teams can form trading blocs (shared resource pools) but must all agree",
                "implementation": "game_mechanic",
                "parameters": {}
            },
            {
                "name": "Food Crisis",
                "description": "If any nation drops below food threshold, ALL nations lose 10% currency",
                "implementation": "penalty_trigger",
                "parameters": {
                    "food_threshold": 10,
                    "currency_penalty_percent": 10
                }
            }
        ],
        
        "victory_conditions": [
            {
                "type": "buildings_count",
                "description": "First to build 8 buildings (infrastructure-heavy recovery)",
                "target": 8
            },
            {
                "type": "combined_score",
                "description": "Highest combined infrastructure + medical goods at time limit",
                "formula": "infrastructure_buildings + medical_goods"
            }
        ]
    },
    
    ScenarioType.SILK_ROAD: {
        "id": ScenarioType.SILK_ROAD,
        "name": "Silk Road Trade Routes",
        "period": "200 BCE - 1400 CE",
        "difficulty": "easy",
        "recommended_duration": 90,
        "min_duration": 90,
        "max_duration": 90,
        "description": "Four merchant nations compete along the ancient Silk Road. Success requires smart trading, diverse production, and adapting to changing demand.",
        
        "nation_profiles": {
            "1": {
                "name": "China",
                "description": "Raw materials abundance, electrical goods (silk/porcelain analog)",
                "starting_resources": {
                    ResourceType.FOOD: 40,
                    ResourceType.RAW_MATERIALS: 60,
                    ResourceType.ELECTRICAL_GOODS: 20,
                    ResourceType.MEDICAL_GOODS: 5,
                    ResourceType.CURRENCY: 100
                },
                "starting_buildings": {
                    BuildingType.MINE: 3,
                    BuildingType.ELECTRICAL_FACTORY: 2,
                    BuildingType.FARM: 1
                }
            },
            "2": {
                "name": "Persia",
                "description": "Central trading hub, balanced resources",
                "starting_resources": {
                    ResourceType.FOOD: 45,
                    ResourceType.RAW_MATERIALS: 40,
                    ResourceType.ELECTRICAL_GOODS: 15,
                    ResourceType.MEDICAL_GOODS: 15,
                    ResourceType.CURRENCY: 150
                },
                "starting_buildings": {
                    BuildingType.FARM: 2,
                    BuildingType.MINE: 2,
                    BuildingType.ELECTRICAL_FACTORY: 1,
                    BuildingType.MEDICAL_FACTORY: 1
                }
            },
            "3": {
                "name": "Arabia",
                "description": "Food and medical goods (spices/perfumes)",
                "starting_resources": {
                    ResourceType.FOOD: 60,
                    ResourceType.RAW_MATERIALS: 30,
                    ResourceType.ELECTRICAL_GOODS: 5,
                    ResourceType.MEDICAL_GOODS: 25,
                    ResourceType.CURRENCY: 100
                },
                "starting_buildings": {
                    BuildingType.FARM: 3,
                    BuildingType.MEDICAL_FACTORY: 2,
                    BuildingType.MINE: 1
                }
            },
            "4": {
                "name": "Rome",
                "description": "Currency-rich, resource-poor (must trade)",
                "starting_resources": {
                    ResourceType.FOOD: 30,
                    ResourceType.RAW_MATERIALS: 20,
                    ResourceType.ELECTRICAL_GOODS: 10,
                    ResourceType.MEDICAL_GOODS: 10,
                    ResourceType.CURRENCY: 300
                },
                "starting_buildings": {
                    BuildingType.FARM: 1,
                    BuildingType.MINE: 1,
                    BuildingType.INFRASTRUCTURE: 2
                }
            }
        },
        
        "special_rules": [
            {
                "name": "Trading Caravans",
                "description": "Trades take 2 minutes to 'travel' (must wait before receiving goods)",
                "implementation": "trade_delay",
                "parameters": {
                    "delay_minutes": 2
                }
            },
            {
                "name": "Demand Shifts",
                "description": "Every 15 minutes, Banker announces which resource doubles in value",
                "implementation": "banker_event",
                "parameters": {
                    "interval_minutes": 15
                }
            },
            {
                "name": "Bandit Raids",
                "description": "Random 10% resource loss events (challenge to prevent)",
                "implementation": "random_event",
                "parameters": {
                    "resource_loss_percent": 10
                }
            }
        ],
        
        "victory_conditions": [
            {
                "type": "diverse_buildings",
                "description": "First to complete 6 buildings across all types (diversification strategy)",
                "target": 6
            },
            {
                "type": "total_resources",
                "description": "Most total resource volume at time limit",
                "formula": "sum_all_resources"
            }
        ]
    },
    
    ScenarioType.INDUSTRIAL_REVOLUTION: {
        "id": ScenarioType.INDUSTRIAL_REVOLUTION,
        "name": "Industrial Revolution Britain",
        "period": "1760-1840",
        "difficulty": "hard",
        "recommended_duration": 120,
        "min_duration": 120,
        "max_duration": 120,
        "description": "Four British regions race to industrialize. Teams must balance agricultural base with factory development while managing worker welfare.",
        
        "nation_profiles": {
            "1": {
                "name": "Lancashire",
                "description": "Textile focus (electrical goods = textiles)",
                "starting_resources": {
                    ResourceType.FOOD: 30,
                    ResourceType.RAW_MATERIALS: 40,
                    ResourceType.ELECTRICAL_GOODS: 15,
                    ResourceType.MEDICAL_GOODS: 5,
                    ResourceType.CURRENCY: 100
                },
                "starting_buildings": {
                    BuildingType.ELECTRICAL_FACTORY: 3,
                    BuildingType.MINE: 2,
                    BuildingType.FARM: 1
                }
            },
            "2": {
                "name": "Yorkshire",
                "description": "Mining and raw materials",
                "starting_resources": {
                    ResourceType.FOOD: 35,
                    ResourceType.RAW_MATERIALS: 60,
                    ResourceType.ELECTRICAL_GOODS: 5,
                    ResourceType.MEDICAL_GOODS: 5,
                    ResourceType.CURRENCY: 80
                },
                "starting_buildings": {
                    BuildingType.MINE: 4,
                    BuildingType.FARM: 2,
                    BuildingType.ELECTRICAL_FACTORY: 1
                }
            },
            "3": {
                "name": "Midlands",
                "description": "Ironworks and infrastructure",
                "starting_resources": {
                    ResourceType.FOOD: 30,
                    ResourceType.RAW_MATERIALS: 50,
                    ResourceType.ELECTRICAL_GOODS: 10,
                    ResourceType.MEDICAL_GOODS: 5,
                    ResourceType.CURRENCY: 120
                },
                "starting_buildings": {
                    BuildingType.MINE: 2,
                    BuildingType.INFRASTRUCTURE: 2,
                    BuildingType.ELECTRICAL_FACTORY: 2
                }
            },
            "4": {
                "name": "Scotland",
                "description": "Agricultural base, late industrializer",
                "starting_resources": {
                    ResourceType.FOOD: 60,
                    ResourceType.RAW_MATERIALS: 30,
                    ResourceType.ELECTRICAL_GOODS: 5,
                    ResourceType.MEDICAL_GOODS: 3,
                    ResourceType.CURRENCY: 60
                },
                "starting_buildings": {
                    BuildingType.FARM: 4,
                    BuildingType.MINE: 1,
                    BuildingType.MEDICAL_FACTORY: 1
                }
            }
        },
        
        "special_rules": [
            {
                "name": "Factory System",
                "description": "Factories produce double output but cost 1 food per production cycle",
                "implementation": "production_modifier",
                "parameters": {
                    "production_multiplier": 2,
                    "food_cost_per_cycle": 1
                }
            },
            {
                "name": "Worker Strikes",
                "description": "If medical goods fall below threshold, all factories stop for 5 minutes",
                "implementation": "penalty_trigger",
                "parameters": {
                    "medical_goods_threshold": 5,
                    "shutdown_minutes": 5
                }
            },
            {
                "name": "Railway Boom",
                "description": "After 60 minutes, Infrastructure buildings unlock 50% faster trades",
                "implementation": "time_trigger",
                "parameters": {
                    "trigger_time_minutes": 60,
                    "trade_speed_bonus": 0.5
                }
            }
        ],
        
        "victory_conditions": [
            {
                "type": "factory_count",
                "description": "First to build 10 factories (any type)",
                "target": 10
            },
            {
                "type": "industrial_score",
                "description": "Highest (buildings × remaining resources) score at time limit",
                "formula": "total_buildings * sum_all_resources"
            }
        ]
    },
    
    ScenarioType.SPACE_RACE: {
        "id": ScenarioType.SPACE_RACE,
        "name": "Space Race",
        "period": "1957-1975",
        "difficulty": "medium",
        "recommended_duration": 90,
        "min_duration": 90,
        "max_duration": 90,
        "description": "Four space agencies compete to achieve milestones. Technology, infrastructure, and international cooperation determine success.",
        
        "nation_profiles": {
            "1": {
                "name": "USA",
                "description": "High starting currency, balanced production",
                "starting_resources": {
                    ResourceType.FOOD: 40,
                    ResourceType.RAW_MATERIALS: 40,
                    ResourceType.ELECTRICAL_GOODS: 20,
                    ResourceType.MEDICAL_GOODS: 15,
                    ResourceType.CURRENCY: 250
                },
                "starting_buildings": {
                    BuildingType.FARM: 2,
                    BuildingType.MINE: 2,
                    BuildingType.ELECTRICAL_FACTORY: 2,
                    BuildingType.MEDICAL_FACTORY: 1
                }
            },
            "2": {
                "name": "USSR",
                "description": "Strong raw materials, infrastructure focus",
                "starting_resources": {
                    ResourceType.FOOD: 35,
                    ResourceType.RAW_MATERIALS: 60,
                    ResourceType.ELECTRICAL_GOODS: 15,
                    ResourceType.MEDICAL_GOODS: 10,
                    ResourceType.CURRENCY: 150
                },
                "starting_buildings": {
                    BuildingType.MINE: 3,
                    BuildingType.INFRASTRUCTURE: 2,
                    BuildingType.FARM: 2
                }
            },
            "3": {
                "name": "Europe",
                "description": "Collaborative (shared resources with one ally)",
                "starting_resources": {
                    ResourceType.FOOD: 45,
                    ResourceType.RAW_MATERIALS: 35,
                    ResourceType.ELECTRICAL_GOODS: 20,
                    ResourceType.MEDICAL_GOODS: 20,
                    ResourceType.CURRENCY: 180
                },
                "starting_buildings": {
                    BuildingType.FARM: 2,
                    BuildingType.MINE: 2,
                    BuildingType.ELECTRICAL_FACTORY: 1,
                    BuildingType.MEDICAL_FACTORY: 1
                }
            },
            "4": {
                "name": "China",
                "description": "Late starter, faster production after first building",
                "starting_resources": {
                    ResourceType.FOOD: 50,
                    ResourceType.RAW_MATERIALS: 45,
                    ResourceType.ELECTRICAL_GOODS: 10,
                    ResourceType.MEDICAL_GOODS: 8,
                    ResourceType.CURRENCY: 100
                },
                "starting_buildings": {
                    BuildingType.FARM: 3,
                    BuildingType.MINE: 2,
                    BuildingType.ELECTRICAL_FACTORY: 1
                }
            }
        },
        
        "special_rules": [
            {
                "name": "Research Milestones",
                "description": "First team to build each building type earns bonus currency",
                "implementation": "first_builder_bonus",
                "parameters": {
                    "bonus_currency": 50
                }
            },
            {
                "name": "Satellite Network",
                "description": "Teams with 3+ Infrastructure buildings can 'spy' on others' resources once per game",
                "implementation": "game_mechanic",
                "parameters": {
                    "required_infrastructure": 3
                }
            },
            {
                "name": "Moon Race",
                "description": "Final 20 minutes, all building costs increase 50% (resource scarcity)",
                "implementation": "time_trigger",
                "parameters": {
                    "trigger_time_remaining_minutes": 20,
                    "cost_increase_percent": 50
                }
            }
        ],
        
        "victory_conditions": [
            {
                "type": "advanced_technology",
                "description": "First to build 3 Medical Factories (advanced technology)",
                "target": 3,
                "building_type": "medical_factory"
            },
            {
                "type": "diverse_portfolio",
                "description": "Most diverse portfolio (all 8 building types) at time limit",
                "formula": "unique_building_types"
            }
        ]
    },
    
    ScenarioType.AGE_OF_EXPLORATION: {
        "id": ScenarioType.AGE_OF_EXPLORATION,
        "name": "Age of Exploration",
        "period": "1492-1600",
        "difficulty": "medium",
        "recommended_duration": 120,  # 90-120 minutes
        "min_duration": 90,
        "max_duration": 120,
        "description": "Four European powers compete to establish colonial trade empires. Discovery, exploitation, and strategic partnerships drive success.",
        
        "nation_profiles": {
            "1": {
                "name": "Spain",
                "description": "Gold-rich (high currency), low initial production",
                "starting_resources": {
                    ResourceType.FOOD: 30,
                    ResourceType.RAW_MATERIALS: 20,
                    ResourceType.ELECTRICAL_GOODS: 10,
                    ResourceType.MEDICAL_GOODS: 10,
                    ResourceType.CURRENCY: 400
                },
                "starting_buildings": {
                    BuildingType.FARM: 1,
                    BuildingType.MINE: 1,
                    BuildingType.INFRASTRUCTURE: 2
                }
            },
            "2": {
                "name": "Portugal",
                "description": "Trade specialists (cheaper exchanges)",
                "starting_resources": {
                    ResourceType.FOOD: 35,
                    ResourceType.RAW_MATERIALS: 30,
                    ResourceType.ELECTRICAL_GOODS: 15,
                    ResourceType.MEDICAL_GOODS: 15,
                    ResourceType.CURRENCY: 200
                },
                "starting_buildings": {
                    BuildingType.FARM: 2,
                    BuildingType.MINE: 2,
                    BuildingType.MEDICAL_FACTORY: 1,
                    BuildingType.INFRASTRUCTURE: 1
                }
            },
            "3": {
                "name": "England",
                "description": "Naval infrastructure focus",
                "starting_resources": {
                    ResourceType.FOOD: 40,
                    ResourceType.RAW_MATERIALS: 35,
                    ResourceType.ELECTRICAL_GOODS: 10,
                    ResourceType.MEDICAL_GOODS: 10,
                    ResourceType.CURRENCY: 150
                },
                "starting_buildings": {
                    BuildingType.FARM: 2,
                    BuildingType.MINE: 2,
                    BuildingType.INFRASTRUCTURE: 3
                }
            },
            "4": {
                "name": "Netherlands",
                "description": "Agricultural and industrial balance",
                "starting_resources": {
                    ResourceType.FOOD: 50,
                    ResourceType.RAW_MATERIALS: 40,
                    ResourceType.ELECTRICAL_GOODS: 15,
                    ResourceType.MEDICAL_GOODS: 10,
                    ResourceType.CURRENCY: 180
                },
                "starting_buildings": {
                    BuildingType.FARM: 3,
                    BuildingType.MINE: 2,
                    BuildingType.ELECTRICAL_FACTORY: 2
                }
            }
        },
        
        "special_rules": [
            {
                "name": "Discovery Voyages",
                "description": "Teams spend 100 currency + 1 food to attempt discovery (challenge) for resource bonuses",
                "implementation": "challenge_reward",
                "parameters": {
                    "currency_cost": 100,
                    "food_cost": 1,
                    "bonus_resources": {
                        "random": True,
                        "amount_range": [20, 50]
                    }
                }
            },
            {
                "name": "Colonial Goods",
                "description": "Medical goods and electrical goods are worth 2× in trades (represent spices/luxury goods)",
                "implementation": "price_modifier",
                "parameters": {
                    "medical_goods_multiplier": 2,
                    "electrical_goods_multiplier": 2
                }
            },
            {
                "name": "Piracy Tax",
                "description": "Every 15 minutes, all teams lose 5% resources (challenge to prevent)",
                "implementation": "periodic_penalty",
                "parameters": {
                    "interval_minutes": 15,
                    "resource_loss_percent": 5
                }
            }
        ],
        
        "victory_conditions": [
            {
                "type": "wealth_accumulation",
                "description": "First to 800 total currency accumulated",
                "target": 800
            },
            {
                "type": "combined_assets",
                "description": "Highest (buildings + remaining currency) score at time limit",
                "formula": "total_buildings + currency"
            }
        ]
    },
    
    ScenarioType.GREAT_DEPRESSION: {
        "id": ScenarioType.GREAT_DEPRESSION,
        "name": "Great Depression Recovery",
        "period": "1929-1939",
        "difficulty": "hard",
        "recommended_duration": 90,
        "min_duration": 90,
        "max_duration": 90,
        "description": "Four nations attempt different economic strategies to escape depression. Resource scarcity, trade restrictions, and food insecurity create intense pressure.",
        
        "nation_profiles": {
            "1": {
                "name": "USA",
                "description": "New Deal focus (infrastructure-heavy)",
                "starting_resources": {
                    ResourceType.FOOD: 20,
                    ResourceType.RAW_MATERIALS: 15,
                    ResourceType.ELECTRICAL_GOODS: 5,
                    ResourceType.MEDICAL_GOODS: 3,
                    ResourceType.CURRENCY: 75
                },
                "starting_buildings": {
                    BuildingType.FARM: 2,
                    BuildingType.MINE: 1,
                    BuildingType.INFRASTRUCTURE: 2
                }
            },
            "2": {
                "name": "Germany",
                "description": "Industrial rearmament (factory focus)",
                "starting_resources": {
                    ResourceType.FOOD: 15,
                    ResourceType.RAW_MATERIALS: 20,
                    ResourceType.ELECTRICAL_GOODS: 8,
                    ResourceType.MEDICAL_GOODS: 3,
                    ResourceType.CURRENCY: 50
                },
                "starting_buildings": {
                    BuildingType.MINE: 2,
                    BuildingType.ELECTRICAL_FACTORY: 2,
                    BuildingType.FARM: 1
                }
            },
            "3": {
                "name": "Britain",
                "description": "Imperial trade preference (trading bloc with one ally)",
                "starting_resources": {
                    ResourceType.FOOD: 25,
                    ResourceType.RAW_MATERIALS: 15,
                    ResourceType.ELECTRICAL_GOODS: 8,
                    ResourceType.MEDICAL_GOODS: 5,
                    ResourceType.CURRENCY: 100
                },
                "starting_buildings": {
                    BuildingType.FARM: 2,
                    BuildingType.MINE: 1,
                    BuildingType.MEDICAL_FACTORY: 1,
                    BuildingType.INFRASTRUCTURE: 1
                }
            },
            "4": {
                "name": "Sweden",
                "description": "Social democracy (balanced approach)",
                "starting_resources": {
                    ResourceType.FOOD: 30,
                    ResourceType.RAW_MATERIALS: 20,
                    ResourceType.ELECTRICAL_GOODS: 8,
                    ResourceType.MEDICAL_GOODS: 8,
                    ResourceType.CURRENCY: 80
                },
                "starting_buildings": {
                    BuildingType.FARM: 2,
                    BuildingType.MINE: 2,
                    BuildingType.MEDICAL_FACTORY: 1,
                    BuildingType.ELECTRICAL_FACTORY: 1
                }
            }
        },
        
        "special_rules": [
            {
                "name": "Depression Start",
                "description": "All teams begin with 50% normal starting resources (already applied above)",
                "implementation": "initial_modifier",
                "parameters": {
                    "resource_multiplier": 0.5
                }
            },
            {
                "name": "Trade Barriers",
                "description": "International trades cost 10% tariff (paid to banker)",
                "implementation": "trade_cost",
                "parameters": {
                    "tariff_percent": 10
                }
            },
            {
                "name": "Public Works",
                "description": "Infrastructure buildings provide +5% food production to team",
                "implementation": "production_bonus",
                "parameters": {
                    "food_bonus_percent_per_infrastructure": 5
                }
            },
            {
                "name": "Bank Runs",
                "description": "Every 20 minutes, all teams must have 100 currency or lose 1 building",
                "implementation": "periodic_check",
                "parameters": {
                    "interval_minutes": 20,
                    "currency_requirement": 100,
                    "penalty": "lose_1_building"
                }
            }
        ],
        
        "victory_conditions": [
            {
                "type": "prosperity_restoration",
                "description": "First team to reach pre-depression prosperity (1000 total assets)",
                "target": 1000,
                "formula": "currency + sum_resources + (total_buildings * 50)"
            },
            {
                "type": "buildings_count",
                "description": "Most buildings at time limit (recovery metric)",
                "formula": "total_buildings"
            }
        ]
    }
}


def get_scenario(scenario_id: str) -> Dict[str, Any]:
    """
    Get a scenario configuration by ID, including resource and building metadata
    
    Args:
        scenario_id: Scenario identifier (e.g., 'marshall_plan')
        
    Returns:
        Scenario configuration dictionary with resources and buildings metadata
        
    Raises:
        ValueError: If scenario_id is not found
    """
    if scenario_id not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    
    scenario = SCENARIOS[scenario_id].copy()
    
    # Add resource and building metadata
    scenario["resources"] = get_scenario_resources(scenario_id)
    scenario["buildings"] = get_scenario_buildings(scenario_id)
    
    return scenario


def list_scenarios() -> List[Dict[str, Any]]:
    """
    Get a list of all available scenarios with basic info
    
    Returns:
        List of scenario summaries
    """
    return [
        {
            "id": scenario["id"],
            "name": scenario["name"],
            "period": scenario["period"],
            "difficulty": scenario["difficulty"],
            "recommended_duration": scenario["recommended_duration"],
            "description": scenario["description"]
        }
        for scenario in SCENARIOS.values()
    ]


def get_nation_config_for_scenario(scenario_id: str, team_number: int) -> Dict[str, Any]:
    """
    Get the nation configuration for a specific team in a scenario
    
    Args:
        scenario_id: Scenario identifier
        team_number: Team number (1-4)
        
    Returns:
        Nation configuration with resources and buildings
    """
    scenario = get_scenario(scenario_id)
    team_key = str(team_number)
    
    if team_key not in scenario["nation_profiles"]:
        raise ValueError(f"Team {team_number} not defined for scenario {scenario_id}")
    
    nation_profile = scenario["nation_profiles"][team_key]
    
    # Convert enum keys to string values for JSON serialization
    def _enum_to_str(key):
        """Helper to convert enum keys to string values"""
        return key.value if hasattr(key, 'value') else key
    
    return {
        "name": nation_profile["name"],
        "description": nation_profile["description"],
        "resources": {_enum_to_str(k): v for k, v in nation_profile["starting_resources"].items()},
        "buildings": {_enum_to_str(k): v for k, v in nation_profile["starting_buildings"].items()},
        "optional_buildings": {},
        "scenario_id": scenario_id,
        "team_number": team_number
    }
