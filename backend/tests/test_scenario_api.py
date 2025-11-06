"""
Integration tests for scenario API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database import get_db
from models import GameSession, Player, GameStatus
from scenarios import ScenarioType


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_game(client, db):
    """Create a test game using the API (db ensures database is created)"""
    response = client.post("/games", json={
        "config_id": None,
        "config_data": {}
    })
    assert response.status_code == 201
    game_data = response.json()
    return game_data["game_code"]


class TestScenarioAPI:
    """Test scenario-related API endpoints"""
    
    def test_get_scenarios_list(self, client):
        """Test GET /scenarios endpoint"""
        response = client.get("/scenarios")
        assert response.status_code == 200
        
        data = response.json()
        assert "scenarios" in data
        assert len(data["scenarios"]) == 6
        
        # Check structure
        scenario = data["scenarios"][0]
        assert "id" in scenario
        assert "name" in scenario
        assert "period" in scenario
        assert "difficulty" in scenario
        assert "recommended_duration" in scenario
        assert "description" in scenario
    
    def test_get_scenario_details(self, client):
        """Test GET /scenarios/{scenario_id} endpoint"""
        response = client.get(f"/scenarios/{ScenarioType.MARSHALL_PLAN}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == ScenarioType.MARSHALL_PLAN
        assert data["name"] == "Post-WWII Marshall Plan"
        assert "nation_profiles" in data
        assert "special_rules" in data
        assert "victory_conditions" in data
    
    def test_get_invalid_scenario(self, client):
        """Test GET /scenarios/{scenario_id} with invalid scenario"""
        response = client.get("/scenarios/invalid_scenario")
        assert response.status_code == 404
    
    def test_set_scenario(self, client, test_game):
        """Test POST /games/{game_code}/set-scenario endpoint"""
        response = client.post(
            f"/games/{test_game}/set-scenario",
            params={"scenario_id": ScenarioType.SILK_ROAD}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["scenario_id"] == ScenarioType.SILK_ROAD
        assert data["scenario_name"] == "Silk Road Trade Routes"
        assert data["num_teams"] == 4  # Should auto-set to 4 teams
        assert data["game_duration_minutes"] == 90
        assert data["difficulty"] == "easy"
    
    def test_set_scenario_invalid_game(self, client):
        """Test setting scenario on non-existent game"""
        response = client.post(
            "/games/NOTEXIST/set-scenario",
            params={"scenario_id": ScenarioType.MARSHALL_PLAN}
        )
        assert response.status_code == 404
    
    def test_set_invalid_scenario(self, client, test_game):
        """Test setting invalid scenario"""
        response = client.post(
            f"/games/{test_game}/set-scenario",
            params={"scenario_id": "invalid_scenario"}
        )
        assert response.status_code == 404
    
    def test_set_scenario_after_game_started(self, client):
        """Test that scenario cannot be changed after game starts"""
        # Create game
        response = client.post("/games", json={
            "config_id": None,
            "config_data": {}
        })
        assert response.status_code == 201
        game_code = response.json()["game_code"]
        
        # Start the game
        start_response = client.post(f"/games/{game_code}/start")
        assert start_response.status_code == 200
        
        # Try to set scenario after game started
        response = client.post(
            f"/games/{game_code}/set-scenario",
            params={"scenario_id": ScenarioType.MARSHALL_PLAN}
        )
        assert response.status_code == 400
        assert "Cannot change scenario after game has started" in response.json()["detail"]
    
    def test_scenario_sets_game_config(self, client, test_game):
        """Test that setting scenario properly configures the game"""
        response = client.post(
            f"/games/{test_game}/set-scenario",
            params={"scenario_id": ScenarioType.INDUSTRIAL_REVOLUTION}
        )
        assert response.status_code == 200
        
        # Get game to verify configuration
        game_response = client.get(f"/games/{test_game}")
        assert game_response.status_code == 200
        game = game_response.json()
        
        # Check that game was configured
        assert game["scenario_id"] == ScenarioType.INDUSTRIAL_REVOLUTION
        assert game["num_teams"] == 4
        assert game["game_duration_minutes"] == 120
        assert game["difficulty"] == "hard"
        
        # Check game_state has scenario info
        assert "scenario" in game["game_state"]
        assert game["game_state"]["scenario"]["id"] == ScenarioType.INDUSTRIAL_REVOLUTION
        assert game["game_state"]["scenario"]["name"] == "Industrial Revolution Britain"
    
    def test_all_scenarios_can_be_set(self, client):
        """Test that all 6 scenarios can be successfully set"""
        scenarios = [
            ScenarioType.MARSHALL_PLAN,
            ScenarioType.SILK_ROAD,
            ScenarioType.INDUSTRIAL_REVOLUTION,
            ScenarioType.SPACE_RACE,
            ScenarioType.AGE_OF_EXPLORATION,
            ScenarioType.GREAT_DEPRESSION
        ]
        
        for scenario_id in scenarios:
            # Create a new game for each scenario
            game_response = client.post("/games", json={
                "config_id": None,
                "config_data": {}
            })
            assert game_response.status_code == 201
            game_code = game_response.json()["game_code"]
            
            # Set scenario
            response = client.post(
                f"/games/{game_code}/set-scenario",
                params={"scenario_id": scenario_id}
            )
            assert response.status_code == 200, f"Failed to set {scenario_id}"
            assert response.json()["scenario_id"] == scenario_id
