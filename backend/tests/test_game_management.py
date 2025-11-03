"""
Tests for game session creation and management
"""
import pytest


class TestGameCreation:
    """Test game creation endpoints"""
    
    def test_create_game_success(self, client):
        """Test successful game creation"""
        # Create game
        response = client.post("/games", json={
            "config_id": None,
            "config_data": {}
        })
        
        assert response.status_code == 201
        data = response.json()
        assert "game_code" in data
        assert len(data["game_code"]) == 6
        assert data["status"] == "waiting"
        assert data["num_teams"] is None  # Not set until host configures
        
        # Set teams
        game_code = data["game_code"]
        teams_response = client.post(f"/games/{game_code}/set-teams", params={"num_teams": 4})
        assert teams_response.status_code == 200
        assert teams_response.json()["num_teams"] == 4
    
    def test_create_game_with_default_teams(self, client):
        """Test game creation defaults to no teams"""
        response = client.post("/games", json={
            "config_id": None
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["num_teams"] is None  # Must be set explicitly
    
    def test_create_game_invalid_team_count(self, client):
        """Test setting invalid team count"""
        # First create a game
        game_response = client.post("/games", json={"config_id": None})
        game_code = game_response.json()["game_code"]
        
        # Try to set invalid team count
        response = client.post(f"/games/{game_code}/set-teams", params={"num_teams": 0})
        
        # Should be rejected
        assert response.status_code == 400


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
    
    @pytest.mark.skip(reason="Game status endpoints not yet implemented")
    def test_start_game(self, client, sample_game):
        """Test starting a game"""
        game_code = sample_game["game_code"]
        response = client.put(f"/games/{game_code}/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
    
    @pytest.mark.skip(reason="Game status endpoints not yet implemented")
    def test_pause_game(self, client, sample_game):
        """Test pausing a game"""
        game_code = sample_game["game_code"]
        
        # First start the game
        client.put(f"/games/{game_code}/start")
        
        # Then pause it
        response = client.put(f"/games/{game_code}/pause")
        assert response.status_code == 200
        assert response.json()["status"] == "paused"
    
    @pytest.mark.skip(reason="Game status endpoints not yet implemented")
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
    
    @pytest.mark.skip(reason="Game status endpoints not yet implemented")
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
        response = client.post(f"/games/{game_code}/set-teams", params={"num_teams": 6})
        
        assert response.status_code == 200
        data = response.json()
        assert data["num_teams"] == 6
    
    def test_update_team_count_invalid(self, client, sample_game):
        """Test updating with invalid team count"""
        game_code = sample_game["game_code"]
        response = client.post(f"/games/{game_code}/set-teams", params={"num_teams": 0})
        
        # Should reject invalid counts
        assert response.status_code in [400, 422]
