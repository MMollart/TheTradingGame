"""
Tests for special building effects (Hospital, Restaurant, Infrastructure)
"""
import pytest
from game_logic import GameLogic
from game_constants import BuildingType, ResourceType


def test_restaurant_effect_on_food_tax():
    """Test that restaurants generate currency when food tax is paid"""
    # Nation with 2 restaurants
    nation_state = {
        "nation_type": "nation_1",
        "is_developed": True,  # 15 food tax
        "resources": {
            "food": 50,
            "currency": 100
        },
        "buildings": {
            "farm": 3,
            "restaurant": 2
        }
    }
    
    # Apply food tax
    success, message, new_state = GameLogic.apply_food_tax(nation_state)
    
    assert success == True
    # Food tax for developed nation is 15
    assert new_state["resources"]["food"] == 50 - 15  # 35
    # Restaurants generate: 15 food tax * 5 currency per food * 2 restaurants = 150 currency
    assert new_state["resources"]["currency"] == 100 + 150  # 250
    assert "Restaurants generated" in message


def test_restaurant_effect_no_restaurants():
    """Test food tax without restaurants"""
    nation_state = {
        "nation_type": "nation_1",
        "is_developed": True,
        "resources": {
            "food": 50,
            "currency": 100
        },
        "buildings": {
            "farm": 3
        }
    }
    
    # Apply food tax
    success, message, new_state = GameLogic.apply_food_tax(nation_state)
    
    assert success == True
    assert new_state["resources"]["food"] == 35  # 50 - 15
    assert new_state["resources"]["currency"] == 100  # No change
    assert message is None  # No special message


def test_hospital_effect_on_disease():
    """Test that hospitals reduce disease impact"""
    # Nation with 3 hospitals (60% reduction)
    nation_state = {
        "nation_type": "nation_1",
        "resources": {
            "medical_goods": 50
        },
        "buildings": {
            "farm": 3,
            "hospital": 3
        }
    }
    
    # Apply disease with severity 5
    # Base medical needed: 5 * 10 = 50
    # With 3 hospitals: reduction = 60%, so 40% of base needed
    # medical_needed = round(50 * 0.4) = round(20.0) = 20
    success, message, new_state = GameLogic.apply_disaster(nation_state, "disease", severity=5)
    
    assert success == True
    medical_needed = round(50 * (1.0 - 0.6))  # Use same calculation as code
    assert new_state["resources"]["medical_goods"] == 50 - medical_needed
    assert "reduced impact by 60%" in message


def test_hospital_complete_protection():
    """Test that 5 hospitals completely negate disease"""
    nation_state = {
        "nation_type": "nation_1",
        "resources": {
            "medical_goods": 50
        },
        "buildings": {
            "farm": 3,
            "hospital": 5
        }
    }
    
    # Apply disease with any severity
    success, message, new_state = GameLogic.apply_disaster(nation_state, "disease", severity=5)
    
    assert success == True
    assert new_state["resources"]["medical_goods"] == 50  # No change
    assert "completely negated" in message


def test_hospital_effect_no_hospitals():
    """Test disease without hospitals"""
    nation_state = {
        "nation_type": "nation_1",
        "resources": {
            "medical_goods": 50
        },
        "buildings": {
            "farm": 3
        }
    }
    
    # Apply disease with severity 2
    # Medical needed: 2 * 10 = 20
    success, message, new_state = GameLogic.apply_disaster(nation_state, "disease", severity=2)
    
    assert success == True
    assert new_state["resources"]["medical_goods"] == 50 - 20  # 30 remaining


def test_infrastructure_effect_on_drought():
    """Test that infrastructure reduces drought impact"""
    # Nation with 2 infrastructures (40% reduction)
    nation_state = {
        "nation_type": "nation_1",
        "resources": {},
        "buildings": {
            "farm": 3,
            "infrastructure": 2
        }
    }
    
    # Apply drought with severity 5
    success, message, new_state = GameLogic.apply_disaster(nation_state, "drought", severity=5)
    
    assert success == True
    # Effective severity: 5 * (1 - 0.4) = 3
    assert "reduced by 60%" in message or "reduced impact by 40%" in message
    assert "Infrastructure" in message


def test_infrastructure_complete_protection():
    """Test that 5 infrastructures completely negate drought"""
    nation_state = {
        "nation_type": "nation_1",
        "resources": {},
        "buildings": {
            "farm": 3,
            "infrastructure": 5
        }
    }
    
    # Apply drought with any severity
    success, message, new_state = GameLogic.apply_disaster(nation_state, "drought", severity=5)
    
    assert success == True
    assert "completely negated" in message


def test_infrastructure_effect_no_infrastructure():
    """Test drought without infrastructure"""
    nation_state = {
        "nation_type": "nation_1",
        "resources": {},
        "buildings": {
            "farm": 3
        }
    }
    
    # Apply drought
    success, message, new_state = GameLogic.apply_disaster(nation_state, "drought", severity=3)
    
    assert success == True
    assert "reduced by 100%" in message or "Production reduced" in message


def test_multiple_restaurants_scaling():
    """Test that multiple restaurants scale currency generation"""
    # Test with 1, 2, 3, 4, 5 restaurants
    for num_restaurants in range(1, 6):
        nation_state = {
            "nation_type": "nation_1",
            "is_developed": False,  # 5 food tax
            "resources": {
                "food": 50,
                "currency": 0
            },
            "buildings": {
                "farm": 3,
                "restaurant": num_restaurants
            }
        }
        
        success, message, new_state = GameLogic.apply_food_tax(nation_state)
        
        assert success == True
        # Currency generated: 5 food tax * 5 currency per food * num_restaurants
        expected_currency = 5 * 5 * num_restaurants
        assert new_state["resources"]["currency"] == expected_currency


def test_multiple_hospitals_scaling():
    """Test that multiple hospitals scale disease protection"""
    for num_hospitals in range(1, 6):
        nation_state = {
            "nation_type": "nation_1",
            "resources": {
                "medical_goods": 100
            },
            "buildings": {
                "farm": 3,
                "hospital": num_hospitals
            }
        }
        
        # Apply disease with severity 5
        success, message, new_state = GameLogic.apply_disaster(nation_state, "disease", severity=5)
        
        assert success == True
        
        # Calculate expected medical goods used (use round to match code)
        base_medical = 50  # 5 * 10
        reduction = min(num_hospitals * 0.2, 1.0)  # 20% per hospital, max 100%
        medical_needed = round(base_medical * (1.0 - reduction))
        
        if num_hospitals >= 5:
            # Complete protection
            assert new_state["resources"]["medical_goods"] == 100
        else:
            assert new_state["resources"]["medical_goods"] == 100 - medical_needed


def test_multiple_infrastructure_scaling():
    """Test that multiple infrastructures scale drought protection"""
    for num_infrastructure in range(1, 6):
        nation_state = {
            "nation_type": "nation_1",
            "resources": {},
            "buildings": {
                "farm": 3,
                "infrastructure": num_infrastructure
            }
        }
        
        # Apply drought
        success, message, new_state = GameLogic.apply_disaster(nation_state, "drought", severity=5)
        
        assert success == True
        
        # Calculate expected reduction
        reduction = min(num_infrastructure * 0.2, 1.0)
        
        if num_infrastructure >= 5:
            assert "completely negated" in message
        else:
            # Check that reduction is mentioned
            assert "Infrastructure" in message or "reduced" in message.lower()


def test_restaurant_with_famine():
    """Test that restaurants don't generate currency during famine"""
    nation_state = {
        "nation_type": "nation_1",
        "is_developed": True,  # 15 food tax
        "resources": {
            "food": 5,  # Not enough for tax
            "currency": 100
        },
        "buildings": {
            "farm": 3,
            "restaurant": 2
        }
    }
    
    # Apply food tax (will result in famine)
    success, message, new_state = GameLogic.apply_food_tax(nation_state)
    
    # Famine happened, paid with currency
    assert success == True
    assert "FAMINE" in message
    # Restaurants should not generate currency during famine
    assert new_state["resources"]["currency"] < 100  # Currency was spent
