"""
Tests for game duration configuration
"""
import pytest


class TestGameDuration:
    """Test game duration setting functionality"""
    
    def test_set_valid_duration_1_hour(self, client, sample_game):
        """Test setting game duration to 1 hour (60 minutes)"""
        game_code = sample_game["game_code"]
        
        response = client.post(
            f"/games/{game_code}/set-duration",
            params={"duration_minutes": 60}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["game_duration_minutes"] == 60
        assert "1 hour" in data["message"]
    
    def test_set_valid_duration_90_minutes(self, client, sample_game):
        """Test setting game duration to 1.5 hours (90 minutes)"""
        game_code = sample_game["game_code"]
        
        response = client.post(
            f"/games/{game_code}/set-duration",
            params={"duration_minutes": 90}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["game_duration_minutes"] == 90
        assert "1 hour 30 minutes" in data["message"]
    
    def test_set_valid_duration_4_hours(self, client, sample_game):
        """Test setting game duration to 4 hours (240 minutes)"""
        game_code = sample_game["game_code"]
        
        response = client.post(
            f"/games/{game_code}/set-duration",
            params={"duration_minutes": 240}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["game_duration_minutes"] == 240
        assert "4 hours" in data["message"]
    
    def test_set_all_valid_durations(self, client, sample_game):
        """Test all valid duration values (60-240 in 30min intervals)"""
        game_code = sample_game["game_code"]
        valid_durations = [60, 90, 120, 150, 180, 210, 240]
        
        for duration in valid_durations:
            response = client.post(
                f"/games/{game_code}/set-duration",
                params={"duration_minutes": duration}
            )
            assert response.status_code == 200
            assert response.json()["game_duration_minutes"] == duration
    
    def test_set_invalid_duration_too_short(self, client, sample_game):
        """Test setting duration below minimum (less than 60 minutes)"""
        game_code = sample_game["game_code"]
        
        response = client.post(
            f"/games/{game_code}/set-duration",
            params={"duration_minutes": 30}
        )
        
        assert response.status_code == 400
        assert "must be one of" in response.json()["detail"]
    
    def test_set_invalid_duration_too_long(self, client, sample_game):
        """Test setting duration above maximum (more than 240 minutes)"""
        game_code = sample_game["game_code"]
        
        response = client.post(
            f"/games/{game_code}/set-duration",
            params={"duration_minutes": 300}
        )
        
        assert response.status_code == 400
    
    def test_set_invalid_duration_not_interval(self, client, sample_game):
        """Test setting duration not in 30-minute intervals"""
        game_code = sample_game["game_code"]
        
        response = client.post(
            f"/games/{game_code}/set-duration",
            params={"duration_minutes": 75}  # Not a valid interval
        )
        
        assert response.status_code == 400
        assert "30-minute intervals" in response.json()["detail"]
    
    def test_set_duration_nonexistent_game(self, client):
        """Test setting duration for non-existent game"""
        response = client.post(
            "/games/XXXXXX/set-duration",
            params={"duration_minutes": 120}
        )
        
        assert response.status_code == 404
    
    def test_duration_persists_in_game_session(self, client, sample_game):
        """Test that duration persists when retrieving game"""
        game_code = sample_game["game_code"]
        
        # Set duration
        client.post(
            f"/games/{game_code}/set-duration",
            params={"duration_minutes": 120}
        )
        
        # Retrieve game
        response = client.get(f"/games/{game_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["game_duration_minutes"] == 120
    
    def test_update_duration(self, client, sample_game):
        """Test updating duration after initial set"""
        game_code = sample_game["game_code"]
        
        # Set initial duration
        client.post(
            f"/games/{game_code}/set-duration",
            params={"duration_minutes": 60}
        )
        
        # Update to new duration
        response = client.post(
            f"/games/{game_code}/set-duration",
            params={"duration_minutes": 180}
        )
        
        assert response.status_code == 200
        assert response.json()["game_duration_minutes"] == 180
        
        # Verify it persisted
        game_response = client.get(f"/games/{game_code}")
        assert game_response.json()["game_duration_minutes"] == 180
