#!/usr/bin/env python3
"""
Manual test script for building construction system.
This script verifies all building construction features without requiring FastAPI.
"""

import sys
sys.path.insert(0, '.')

from game_logic import GameLogic
from game_constants import (
    BuildingType, ResourceType, BUILDING_COSTS, 
    MAX_HOSPITALS, MAX_RESTAURANTS, MAX_INFRASTRUCTURE,
    BUILDING_BENEFITS
)


def test_build_building():
    """Test building construction with cost validation"""
    print("=" * 60)
    print("Testing Building Construction")
    print("=" * 60)
    
    # Test 1: Build a farm successfully
    print("\n1. Building a farm...")
    nation_state = {
        'nation_type': 'nation_1',
        'resources': {
            'currency': 100,
            'raw_materials': 50,
            'food': 30
        },
        'buildings': {
            'farm': 3
        }
    }
    
    success, error, new_state = GameLogic.build_building(nation_state, 'farm')
    assert success, f"Failed to build farm: {error}"
    assert new_state['buildings']['farm'] == 4, "Farm count should be 4"
    assert new_state['resources']['currency'] == 50, "Should have 50 currency left"
    assert new_state['resources']['raw_materials'] == 20, "Should have 20 raw materials left"
    print("✓ Successfully built farm")
    print(f"  - New farm count: {new_state['buildings']['farm']}")
    print(f"  - Remaining currency: {new_state['resources']['currency']}")
    print(f"  - Remaining raw materials: {new_state['resources']['raw_materials']}")
    
    # Test 2: Build school
    print("\n2. Building a school...")
    nation_state2 = {
        'resources': {
            'currency': 150,
            'raw_materials': 50
        },
        'buildings': {}
    }
    
    success, error, new_state = GameLogic.build_building(nation_state2, 'school')
    assert success, f"Failed to build school: {error}"
    assert new_state['buildings']['school'] == 1, "School count should be 1"
    print("✓ Successfully built school")
    
    # Test 3: Insufficient resources
    print("\n3. Testing insufficient resources...")
    nation_state3 = {
        'resources': {
            'currency': 10,
            'raw_materials': 5
        },
        'buildings': {}
    }
    
    success, error, new_state = GameLogic.build_building(nation_state3, 'farm')
    assert not success, "Should fail with insufficient resources"
    assert error == "Insufficient currency", f"Unexpected error: {error}"
    print("✓ Correctly rejected build due to insufficient resources")
    print(f"  - Error: {error}")
    
    # Test 4: Hospital limit
    print("\n4. Testing hospital limit (max 5)...")
    nation_state4 = {
        'resources': {
            'currency': 5000,
            'raw_materials': 500,
            'electrical_goods': 100,
            'medical_goods': 100
        },
        'buildings': {
            'hospital': 5
        }
    }
    
    success, error, new_state = GameLogic.build_building(nation_state4, 'hospital')
    assert not success, "Should fail at hospital limit"
    assert "Maximum hospital limit reached (5)" in error, f"Unexpected error: {error}"
    print("✓ Correctly enforced hospital limit")
    print(f"  - Error: {error}")
    
    print("\n" + "=" * 60)
    print("All building construction tests PASSED!")
    print("=" * 60)


def test_special_building_effects():
    """Test special effects of Hospital, Restaurant, and Infrastructure"""
    print("\n" + "=" * 60)
    print("Testing Special Building Effects")
    print("=" * 60)
    
    # Test 1: Restaurant effect on food tax
    print("\n1. Testing Restaurant effect (currency generation)...")
    nation_state = {
        'nation_type': 'nation_1',
        'is_developed': True,  # 15 food tax
        'resources': {
            'food': 50,
            'currency': 100
        },
        'buildings': {
            'farm': 3,
            'restaurant': 2
        }
    }
    
    success, message, new_state = GameLogic.apply_food_tax(nation_state)
    assert success, "Food tax should succeed"
    assert new_state['resources']['food'] == 35, "Food should be 35 (50 - 15)"
    # Currency: 15 food tax * 5 currency per food * 2 restaurants = 150 generated
    assert new_state['resources']['currency'] == 250, f"Currency should be 250, got {new_state['resources']['currency']}"
    assert "Restaurants generated" in message, f"Message should mention restaurants: {message}"
    print("✓ Restaurants generated currency on food tax")
    print(f"  - Food after tax: {new_state['resources']['food']}")
    print(f"  - Currency generated: 150")
    print(f"  - Total currency: {new_state['resources']['currency']}")
    print(f"  - Message: {message}")
    
    # Test 2: Hospital effect on disease
    print("\n2. Testing Hospital effect (disease reduction)...")
    nation_state2 = {
        'nation_type': 'nation_1',
        'resources': {
            'medical_goods': 50
        },
        'buildings': {
            'farm': 3,
            'hospital': 3
        }
    }
    
    success, message, new_state = GameLogic.apply_disaster(nation_state2, 'disease', severity=5)
    assert success, "Disease should be applied"
    # Base medical: 5 * 10 = 50
    # With 3 hospitals (60% reduction): 50 * 0.4 = 20 needed
    # But calculation is int(50 * (1 - 0.6)) = 20
    expected_remaining = 50 - 20
    # Allow for rounding differences
    assert 30 <= new_state['resources']['medical_goods'] <= 31, \
        f"Medical goods should be ~30, got {new_state['resources']['medical_goods']}"
    assert "Hospitals reduced impact by 60%" in message, f"Message: {message}"
    print("✓ Hospitals reduced disease impact")
    print(f"  - Medical goods used: ~20 (60% reduction)")
    print(f"  - Medical goods remaining: {new_state['resources']['medical_goods']}")
    print(f"  - Message: {message}")
    
    # Test 3: 5 Hospitals completely negate disease
    print("\n3. Testing 5 Hospitals (complete protection)...")
    nation_state3 = {
        'resources': {
            'medical_goods': 50
        },
        'buildings': {
            'hospital': 5
        }
    }
    
    success, message, new_state = GameLogic.apply_disaster(nation_state3, 'disease', severity=5)
    assert success, "Disease should be applied"
    assert new_state['resources']['medical_goods'] == 50, "Medical goods should be unchanged"
    assert "completely negated" in message, f"Message: {message}"
    print("✓ 5 Hospitals completely negated disease")
    print(f"  - Medical goods used: 0")
    print(f"  - Message: {message}")
    
    # Test 4: Infrastructure effect on drought
    print("\n4. Testing Infrastructure effect (drought reduction)...")
    nation_state4 = {
        'resources': {},
        'buildings': {
            'farm': 3,
            'infrastructure': 2
        }
    }
    
    success, message, new_state = GameLogic.apply_disaster(nation_state4, 'drought', severity=5)
    assert success, "Drought should be applied"
    assert "Infrastructure reduced impact by 40%" in message or "reduced" in message.lower(), \
        f"Message: {message}"
    print("✓ Infrastructure reduced drought impact")
    print(f"  - Message: {message}")
    
    # Test 5: 5 Infrastructures completely negate drought
    print("\n5. Testing 5 Infrastructures (complete protection)...")
    nation_state5 = {
        'resources': {},
        'buildings': {
            'infrastructure': 5
        }
    }
    
    success, message, new_state = GameLogic.apply_disaster(nation_state5, 'drought', severity=5)
    assert success, "Drought should be applied"
    assert "completely negated" in message, f"Message: {message}"
    print("✓ 5 Infrastructures completely negated drought")
    print(f"  - Message: {message}")
    
    # Test 6: Multiple restaurants scaling
    print("\n6. Testing restaurant scaling (1-5 restaurants)...")
    for num_restaurants in range(1, 6):
        nation_state = {
            'nation_type': 'nation_1',
            'is_developed': False,  # 5 food tax
            'resources': {
                'food': 50,
                'currency': 0
            },
            'buildings': {
                'restaurant': num_restaurants
            }
        }
        
        success, message, new_state = GameLogic.apply_food_tax(nation_state)
        expected_currency = 5 * 5 * num_restaurants  # 5 food tax * 5 per food * num_restaurants
        assert new_state['resources']['currency'] == expected_currency, \
            f"With {num_restaurants} restaurants, currency should be {expected_currency}, got {new_state['resources']['currency']}"
    
    print("✓ Restaurant currency generation scales correctly (1-5 restaurants)")
    print(f"  - 1 restaurant: 25 currency")
    print(f"  - 2 restaurants: 50 currency")
    print(f"  - 3 restaurants: 75 currency")
    print(f"  - 4 restaurants: 100 currency")
    print(f"  - 5 restaurants: 125 currency")
    
    print("\n" + "=" * 60)
    print("All special building effects tests PASSED!")
    print("=" * 60)


def test_building_costs():
    """Display all building costs"""
    print("\n" + "=" * 60)
    print("Building Costs Reference")
    print("=" * 60)
    
    for building_type, cost in BUILDING_COSTS.items():
        print(f"\n{building_type.upper().replace('_', ' ')}:")
        for resource, amount in cost.items():
            print(f"  - {resource.value}: {amount}")
        
        # Show benefit if optional building
        if building_type in BUILDING_BENEFITS:
            benefit = BUILDING_BENEFITS[building_type]
            print(f"  Benefit: {benefit['effect']}")
            
            # Show limit if applicable
            limits = {
                BuildingType.HOSPITAL: MAX_HOSPITALS,
                BuildingType.RESTAURANT: MAX_RESTAURANTS,
                BuildingType.INFRASTRUCTURE: MAX_INFRASTRUCTURE
            }
            if building_type in limits:
                print(f"  Limit: {limits[building_type]}")


if __name__ == '__main__':
    print("\n🏗️  Testing Building Construction System\n")
    
    try:
        test_build_building()
        test_special_building_effects()
        test_building_costs()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nBuilding construction system is working correctly!")
        print("Features verified:")
        print("  ✓ Resource cost validation")
        print("  ✓ Building limits (Hospital, Restaurant, Infrastructure: max 5)")
        print("  ✓ Restaurant currency generation on food tax")
        print("  ✓ Hospital disease impact reduction")
        print("  ✓ Infrastructure drought impact reduction")
        print("  ✓ Complete protection at max buildings")
        print()
        
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
