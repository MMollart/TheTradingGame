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
    response = client.post("/games/create")
    assert response.status_code == 200
    game_code = response.json()["game_code"]
    
    # Set number of teams
    response = client.post(f"/games/{game_code}/set-num-teams", json={"num_teams": 4})
    assert response.status_code == 200
    
    # Create a player
    response = client.post(
        f"/games/{game_code}/join",
        json={"player_name": "TestPlayer", "role": "player"}
    )
    assert response.status_code == 200
    player_id = response.json()["player_id"]
    
    # Approve player
    response = client.post(f"/games/{game_code}/players/{player_id}/approve")
    assert response.status_code == 200
    
    # Assign to team 1
    response = client.post(
        f"/games/{game_code}/players/{player_id}/assign-group",
        json={"group_number": 1}
    )
    assert response.status_code == 200
    
    # Start game
    response = client.post(f"/games/{game_code}/start")
    assert response.status_code == 200
    
    # Give resources to team 1 (enough to build any building)
    response = client.post(
        f"/games/{game_code}/manual-resources",
        json={
            "team_number": 1,
            "resource_type": "currency",
            "amount": 1000
        }
    )
    assert response.status_code == 200
    
    response = client.post(
        f"/games/{game_code}/manual-resources",
        json={
            "team_number": 1,
            "resource_type": "raw_materials",
            "amount": 500
        }
    )
    assert response.status_code == 200
    
    response = client.post(
        f"/games/{game_code}/manual-resources",
        json={
            "team_number": 1,
            "resource_type": "food",
            "amount": 100
        }
    )
    assert response.status_code == 200
    
    response = client.post(
        f"/games/{game_code}/manual-resources",
        json={
            "team_number": 1,
            "resource_type": "electrical_goods",
            "amount": 100
        }
    )
    assert response.status_code == 200
    
    response = client.post(
        f"/games/{game_code}/manual-resources",
        json={
            "team_number": 1,
            "resource_type": "medical_goods",
            "amount": 50
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
    farm_cost = BUILDING_COSTS[BuildingType.FARM]
    remaining = data["remaining_resources"]
    assert remaining["currency"] == 1000 - farm_cost[ResourceType.CURRENCY]
    assert remaining["raw_materials"] == 500 - farm_cost[ResourceType.RAW_MATERIALS]


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
    """Test building fails with insufficient resources"""
    game_code, player_id = game_with_team
    
    # Use up all currency first
    response = client.post(
        f"/games/{game_code}/manual-resources",
        json={
            "team_number": 1,
            "resource_type": "currency",
            "amount": -1000  # Remove all currency
        }
    )
    
    # Try to build a farm (needs 50 currency)
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
    factory_cost = BUILDING_COSTS[BuildingType.ELECTRICAL_FACTORY]
    remaining = data["remaining_resources"]
    assert remaining["electrical_goods"] == 100 - factory_cost[ResourceType.ELECTRICAL_GOODS]


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
    factory_cost = BUILDING_COSTS[BuildingType.MEDICAL_FACTORY]
    remaining = data["remaining_resources"]
    assert remaining["food"] == 100 - factory_cost[ResourceType.FOOD]
    assert remaining["electrical_goods"] == 100 - factory_cost[ResourceType.ELECTRICAL_GOODS]


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
    
    # Verify all buildings are tracked correctly
    from database import get_db
    from models import GameSession
    db = next(get_db())
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    team_state = game.game_state["teams"]["1"]
    
    assert team_state["buildings"]["farm"] == 4
    assert team_state["buildings"]["school"] == 1
    assert team_state["buildings"]["hospital"] == 1
