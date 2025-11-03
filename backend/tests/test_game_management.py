"""
Tests for game session creation and management
"""
import pytest


class TestGameCreation:
    """Test game creation endpoints"""
    
    def test_create_game_success(self, client):
        """Test successful game creation"""
        response = client.post("/games/", json={
            "host_name": "TestHost",
            "num_teams": 4
        })
        
        assert response.status_code == 201
        data = response.json()
        assert "game_code" in data
        assert len(data["game_code"]) == 6
        assert data["host_name"] == "TestHost"
        assert data["num_teams"] == 4
        assert data["status"] == "waiting"
    
    def test_create_game_with_default_teams(self, client):
        """Test game creation with default team count"""
        response = client.post("/games/", json={
            "host_name": "HostWithDefaults"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["num_teams"] == 4  # Default value
    
    def test_create_game_invalid_team_count(self, client):
        """Test game creation with invalid team count"""
        response = client.post("/games/", json={
            "host_name": "TestHost",
            "num_teams": 0
        })
        
        # Should either reject or use default
        assert response.status_code in [200, 422]


class TestGameRetrieval:
    """Test game retrieval endpoints"""
    
    def test_get_game_by_code(self, client, sample_game):
        """Test retrieving game by code"""
        game_code = sample_game["game_code"]
        response = client.get(f"/games/{game_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["game_code"] == game_code
        assert data["num_teams"] == 4
    
    def test_get_nonexistent_game(self, client):
        """Test retrieving non-existent game"""
        response = client.get("/games/XXXXXX")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_game_case_insensitive(self, client, sample_game):
        """Test game code is case-insensitive"""
        game_code = sample_game["game_code"]
        response = client.get(f"/games/{game_code.lower()}")
        
        assert response.status_code == 200
        assert response.json()["game_code"] == game_code


class TestGameStatus:
    """Test game status management"""
    
    def test_start_game(self, client, sample_game):
        """Test starting a game"""
        game_code = sample_game["game_code"]
        response = client.put(f"/games/{game_code}/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
    
    def test_pause_game(self, client, sample_game):
        """Test pausing a game"""
        game_code = sample_game["game_code"]
        
        # First start the game
        client.put(f"/games/{game_code}/start")
        
        # Then pause it
        response = client.put(f"/games/{game_code}/pause")
        assert response.status_code == 200
        assert response.json()["status"] == "paused"
    
    def test_resume_game(self, client, sample_game):
        """Test resuming a paused game"""
        game_code = sample_game["game_code"]
        
        # Start and pause
        client.put(f"/games/{game_code}/start")
        client.put(f"/games/{game_code}/pause")
        
        # Resume
        response = client.put(f"/games/{game_code}/resume")
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"
    
    def test_end_game(self, client, sample_game):
        """Test ending a game"""
        game_code = sample_game["game_code"]
        
        # Start the game first
        client.put(f"/games/{game_code}/start")
        
        # End it
        response = client.put(f"/games/{game_code}/end")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"


class TestTeamConfiguration:
    """Test team configuration"""
    
    def test_update_team_count(self, client, sample_game):
        """Test updating number of teams"""
        game_code = sample_game["game_code"]
        response = client.put(f"/games/{game_code}/teams", params={"num_teams": 6})
        
        assert response.status_code == 200
        data = response.json()
        assert data["num_teams"] == 6
    
    def test_update_team_count_invalid(self, client, sample_game):
        """Test updating with invalid team count"""
        game_code = sample_game["game_code"]
        response = client.put(f"/games/{game_code}/teams", params={"num_teams": 0})
        
        # Should reject invalid counts
        assert response.status_code in [400, 422]
