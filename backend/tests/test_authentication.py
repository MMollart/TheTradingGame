"""
Tests for authentication and authorization
"""
import pytest
from jose import jwt
from datetime import datetime, timedelta


class TestUserAuthentication:
    """Test user login and JWT token generation"""
    
    def test_login_with_valid_credentials(self, client, db):
        """Test successful login"""
        # First create a user
        from backend.models import User
        from backend.auth import get_password_hash
        
        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=get_password_hash("password123")
        )
        db.add(user)
        db.commit()
        
        # Login
        response = client.post(
            "/auth/token",
            data={"username": "testuser", "password": "password123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_with_invalid_password(self, client, db):
        """Test login with wrong password"""
        from backend.models import User
        from backend.auth import get_password_hash
        
        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=get_password_hash("password123")
        )
        db.add(user)
        db.commit()
        
        response = client.post(
            "/auth/token",
            data={"username": "testuser", "password": "wrongpassword"}
        )
        
        assert response.status_code == 401
    
    def test_login_with_nonexistent_user(self, client):
        """Test login with username that doesn't exist"""
        response = client.post(
            "/auth/token",
            data={"username": "nonexistent", "password": "password123"}
        )
        
        assert response.status_code == 401
    
    def test_jwt_token_contains_user_info(self, client, db):
        """Test that JWT token contains user ID"""
        from backend.models import User
        from backend.auth import get_password_hash, SECRET_KEY, ALGORITHM
        
        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=get_password_hash("password123")
        )
        db.add(user)
        db.commit()
        
        response = client.post(
            "/auth/token",
            data={"username": "testuser", "password": "password123"}
        )
        
        token = response.json()["access_token"]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        assert "sub" in payload  # subject (username)
        assert payload["sub"] == user.username


class TestGuestApproval:
    """Test guest player approval workflow"""
    
    def test_guest_joins_game(self, client, sample_game):
        """Test guest joining a game without authentication"""
        game_code = sample_game["game_code"]
        
        response = client.post(
            "/api/join",
            json={
                "game_code": game_code,
                "player_name": "GuestPlayer",
                "role": "player"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["player_name"] == "GuestPlayer"
        assert data["is_approved"] == False  # Guests need approval
    
    def test_approve_guest_player(self, client, sample_game):
        """Test host approving a guest player"""
        game_code = sample_game["game_code"]
        
        # Guest joins
        join_response = client.post(
            "/api/join",
            json={
                "game_code": game_code,
                "player_name": "GuestPlayer",
                "role": "player"
            }
        )
        player_id = join_response.json()["id"]
        
        # Host approves
        response = client.put(
            f"/games/{game_code}/players/{player_id}/approve"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["player"]["is_approved"] == True
    
    def test_reject_guest_player(self, client, sample_game):
        """Test removing unapproved guest"""
        game_code = sample_game["game_code"]
        
        # Guest joins
        join_response = client.post(
            "/api/join",
            json={
                "game_code": game_code,
                "player_name": "GuestPlayer",
                "role": "player"
            }
        )
        player_id = join_response.json()["id"]
        
        # Host removes
        response = client.delete(
            f"/games/{game_code}/players/{player_id}"
        )
        
        assert response.status_code == 200
        
        # Verify player is gone
        players_response = client.get(f"/games/{game_code}/players")
        players = players_response.json()
        assert player_id not in [p["id"] for p in players]


class TestAuthorization:
    """Test role-based access control"""
    
    def test_host_can_manage_game(self, client, sample_game):
        """Test that host can modify game settings"""
        game_code = sample_game["game_code"]
        
        response = client.post(
            f"/games/{game_code}/set-teams",
            params={"num_teams": 6}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["num_teams"] == 6
    
    def test_host_can_assign_roles(self, client, sample_game, sample_players):
        """Test that roles can be assigned to players"""
        game_code = sample_game["game_code"]
        player_id = sample_players[0]["id"]
        
        response = client.put(
            f"/games/{game_code}/players/{player_id}/assign-role",
            params={"role": "banker"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["player"]["role"] == "banker"
    
    def test_banker_role_clears_team_assignment(self, client, sample_game, sample_players):
        """Test that assigning banker role removes team assignment"""
        game_code = sample_game["game_code"]
        player_id = sample_players[0]["id"]
        
        # First assign to group
        client.put(
            f"/games/{game_code}/players/{player_id}/assign-group",
            params={"group_number": 1}
        )
        
        # Then assign banker role
        response = client.put(
            f"/games/{game_code}/players/{player_id}/assign-role",
            params={"role": "banker"}
        )
        
        data = response.json()
        assert data["success"] == True
        assert data["player"]["role"] == "banker"
        assert data["player"]["group_number"] is None
    
    def test_host_cannot_be_removed(self, client, sample_game):
        """Test that host player cannot be deleted"""
        game_code = sample_game["game_code"]
        
        # Get all players
        players_response = client.get(f"/games/{game_code}/players")
        players = players_response.json()
        
        # Find the host
        host = next((p for p in players if p["role"] == "host"), None)
        assert host is not None, "Host player not found"
        
        # Try to remove host
        response = client.delete(
            f"/games/{game_code}/players/{host['id']}"
        )
        
        # Should be rejected
        assert response.status_code in [400, 403]
    
    def test_player_role_can_have_team(self, client, sample_game, sample_players):
        """Test that regular players can be assigned to teams"""
        game_code = sample_game["game_code"]
        # Use a player, not the host (sample_players[0] is the host)
        player_id = sample_players[1]["id"]  # Player1
        
        # Assign to team
        response = client.put(
            f"/games/{game_code}/players/{player_id}/assign-group",
            params={"group_number": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["player"]["group_number"] == 1
        assert data["player"]["role"] == "player"
