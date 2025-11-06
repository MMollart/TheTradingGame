"""
Tests for building construction system
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models import GameSession, Player, GameStatus, PlayerRole
from game_constants import BuildingType, ResourceType, BUILDING_COSTS


@pytest.fixture
def game_with_team(client, db):
    """Create a game with a team that has resources"""
    # Create game
    response = client.post("/games", json={"config_id": None, "config_data": {}})
    assert response.status_code == 201
    game_code = response.json()["game_code"]
    
    # Set number of teams
    response = client.post(f"/games/{game_code}/set-teams?num_teams=4")
    assert response.status_code == 200
    
    # Create a player
    response = client.post(
        "/api/join",
        json={"game_code": game_code, "player_name": "TestPlayer", "role": "player"}
    )
    assert response.status_code == 200
    player_id = response.json()["id"]
    
    # Approve player
    response = client.put(f"/games/{game_code}/players/{player_id}/approve")
    assert response.status_code == 200
    
    # Assign to team 1
    response = client.put(
        f"/games/{game_code}/players/{player_id}/assign-group?group_number=1"
    )
    assert response.status_code == 200
    
    # Start game
    response = client.post(f"/games/{game_code}/start")
    assert response.status_code == 200
    
    # Give resources to team 1 (enough to build any building multiple times)
    # Hospital costs 300 currency each, so give enough for 5 hospitals (1500)
    # Plus extra for other buildings
    response = client.post(
        f"/games/{game_code}/manual-resources",
        json={
            "team_number": 1,
            "resource_type": "currency",
            "amount": 3000  # Increased from 1000 to support multiple expensive buildings
        }
    )
    assert response.status_code == 200
    
    response = client.post(
        f"/games/{game_code}/manual-resources",
        json={
            "team_number": 1,
            "resource_type": "raw_materials",
            "amount": 500  # Enough for 10 hospitals (50 each)
        }
    )
    assert response.status_code == 200
    
    response = client.post(
        f"/games/{game_code}/manual-resources",
        json={
            "team_number": 1,
            "resource_type": "food",
            "amount": 200  # Enough for multiple restaurants/medical factories
        }
    )
    assert response.status_code == 200
    
    response = client.post(
        f"/games/{game_code}/manual-resources",
        json={
            "team_number": 1,
            "resource_type": "electrical_goods",
            "amount": 200  # Enough for multiple buildings
        }
    )
    assert response.status_code == 200
    
    response = client.post(
        f"/games/{game_code}/manual-resources",
        json={
            "team_number": 1,
            "resource_type": "medical_goods",
            "amount": 100  # Enough for 10 hospitals (10 each)
        }
    )
    assert response.status_code == 200
    
    return game_code, player_id


def test_build_farm_success(client, game_with_team):
    """Test successfully building a farm"""
    game_code, player_id = game_with_team
    
    # Build a farm
    response = client.post(
        f"/games/{game_code}/build-building",
        json={
            "team_number": 1,
            "building_type": "farm"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["building_type"] == "farm"
    assert data["new_count"] == 4  # Started with 3 farms
    
    # Verify resources were deducted
    # Team 1 (Nation 1) starts with 50 currency + 3000 from fixture = 3050
    # After building farm (costs 50 currency, 30 raw_materials): 3000 currency, 470 raw_materials
    farm_cost = BUILDING_COSTS[BuildingType.FARM]
    remaining = data["remaining_resources"]
    assert remaining["currency"] == 3050 - farm_cost[ResourceType.CURRENCY]  # 3050 - 50 = 3000
    assert remaining["raw_materials"] == 500 - farm_cost[ResourceType.RAW_MATERIALS]  # 500 - 30 = 470


def test_build_school_success(client, game_with_team):
    """Test successfully building a school"""
    game_code, player_id = game_with_team
    
    # Build a school
    response = client.post(
        f"/games/{game_code}/build-building",
        json={
            "team_number": 1,
            "building_type": "school"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["building_type"] == "school"
    assert data["new_count"] == 1  # First school


def test_build_hospital_success(client, game_with_team):
    """Test successfully building a hospital"""
    game_code, player_id = game_with_team
    
    # Build a hospital
    response = client.post(
        f"/games/{game_code}/build-building",
        json={
            "team_number": 1,
            "building_type": "hospital"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["building_type"] == "hospital"
    assert data["new_count"] == 1


def test_build_building_insufficient_resources(client, game_with_team):
    """Test that building fails when team doesn't have enough resources"""
    game_code, player_id = game_with_team
    
    # Build farms until we run out of a resource
    # Team has 3050 currency and 500 raw_materials
    # Farm costs: 50 currency, 30 raw_materials
    # Currency allows: 3050/50 = 61 farms
    # Raw materials allows: 500/30 = 16.67 farms (so 16 farms)
    # We'll hit raw_materials limit first
    for i in range(16):
        response = client.post(
            f"/games/{game_code}/build-building",
            json={
                "team_number": 1,
                "building_type": "farm"
            }
        )
        assert response.status_code == 200, f"Farm {i+1} failed unexpectedly"
    
    # Try to build one more farm (needs 30 raw_materials, but team only has 20)
    response = client.post(
        f"/games/{game_code}/build-building",
        json={
            "team_number": 1,
            "building_type": "farm"
        }
    )
    
    assert response.status_code == 400
    assert "Insufficient resources" in response.json()["detail"]


def test_build_hospital_limit(client, game_with_team):
    """Test building hospital respects the maximum limit of 5"""
    game_code, player_id = game_with_team
    
    # Build 5 hospitals
    for i in range(5):
        response = client.post(
            f"/games/{game_code}/build-building",
            json={
                "team_number": 1,
                "building_type": "hospital"
            }
        )
        assert response.status_code == 200
        assert response.json()["new_count"] == i + 1
    
    # Try to build a 6th hospital
    response = client.post(
        f"/games/{game_code}/build-building",
        json={
            "team_number": 1,
            "building_type": "hospital"
        }
    )
    
    assert response.status_code == 400
    assert "Maximum hospital limit reached" in response.json()["detail"]


def test_build_restaurant_limit(client, game_with_team):
    """Test building restaurant respects the maximum limit of 5"""
    game_code, player_id = game_with_team
    
    # Build 5 restaurants
    for i in range(5):
        response = client.post(
            f"/games/{game_code}/build-building",
            json={
                "team_number": 1,
                "building_type": "restaurant"
            }
        )
        assert response.status_code == 200
        assert response.json()["new_count"] == i + 1
    
    # Try to build a 6th restaurant
    response = client.post(
        f"/games/{game_code}/build-building",
        json={
            "team_number": 1,
            "building_type": "restaurant"
        }
    )
    
    assert response.status_code == 400
    assert "Maximum restaurant limit reached" in response.json()["detail"]


def test_build_infrastructure_limit(client, game_with_team):
    """Test building infrastructure respects the maximum limit of 5"""
    game_code, player_id = game_with_team
    
    # Build 5 infrastructures
    for i in range(5):
        response = client.post(
            f"/games/{game_code}/build-building",
            json={
                "team_number": 1,
                "building_type": "infrastructure"
            }
        )
        assert response.status_code == 200
        assert response.json()["new_count"] == i + 1
    
    # Try to build a 6th infrastructure
    response = client.post(
        f"/games/{game_code}/build-building",
        json={
            "team_number": 1,
            "building_type": "infrastructure"
        }
    )
    
    assert response.status_code == 400
    assert "Maximum infrastructure limit reached" in response.json()["detail"]


def test_build_electrical_factory(client, game_with_team):
    """Test building an electrical factory (requires electrical goods)"""
    game_code, player_id = game_with_team
    
    # Build an electrical factory
    response = client.post(
        f"/games/{game_code}/build-building",
        json={
            "team_number": 1,
            "building_type": "electrical_factory"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["building_type"] == "electrical_factory"
    
    # Verify electrical goods were deducted
    # Electrical factory costs 30 electrical_goods
    factory_cost = BUILDING_COSTS[BuildingType.ELECTRICAL_FACTORY]
    remaining = data["remaining_resources"]
    assert remaining["electrical_goods"] == 200 - factory_cost[ResourceType.ELECTRICAL_GOODS]  # 200 - 30 = 170


def test_build_medical_factory(client, game_with_team):
    """Test building a medical factory (requires food and electrical goods)"""
    game_code, player_id = game_with_team
    
    # Build a medical factory
    response = client.post(
        f"/games/{game_code}/build-building",
        json={
            "team_number": 1,
            "building_type": "medical_factory"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["building_type"] == "medical_factory"
    
    # Verify resources were deducted
    # Team 1 starts with 30 food + 200 from fixture = 230 total
    # Medical factory costs: 200 currency, 50 raw_materials, 20 food, 15 electrical_goods
    factory_cost = BUILDING_COSTS[BuildingType.MEDICAL_FACTORY]
    remaining = data["remaining_resources"]
    assert remaining["food"] == 230 - factory_cost[ResourceType.FOOD]  # 230 - 20 = 210
    assert remaining["electrical_goods"] == 200 - factory_cost[ResourceType.ELECTRICAL_GOODS]  # 200 - 15 = 185


def test_build_invalid_building_type(client, game_with_team):
    """Test building with invalid building type"""
    game_code, player_id = game_with_team
    
    response = client.post(
        f"/games/{game_code}/build-building",
        json={
            "team_number": 1,
            "building_type": "invalid_building"
        }
    )
    
    assert response.status_code == 400
    assert "Invalid building type" in response.json()["detail"]


def test_build_multiple_buildings(client, game_with_team):
    """Test building multiple different buildings"""
    game_code, player_id = game_with_team
    
    # Build a farm
    response = client.post(
        f"/games/{game_code}/build-building",
        json={"team_number": 1, "building_type": "farm"}
    )
    assert response.status_code == 200
    assert response.json()["new_count"] == 4
    
    # Build a school
    response = client.post(
        f"/games/{game_code}/build-building",
        json={"team_number": 1, "building_type": "school"}
    )
    assert response.status_code == 200
    assert response.json()["new_count"] == 1
    
    # Build a hospital
    response = client.post(
        f"/games/{game_code}/build-building",
        json={"team_number": 1, "building_type": "hospital"}
    )
    assert response.status_code == 200
    assert response.json()["new_count"] == 1
    
    # Verify all buildings are tracked correctly by checking response data
    # Each build response includes the new_count which confirms tracking
    # We've already verified counts above: farm=4, school=1, hospital=1
