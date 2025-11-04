"""
Tests for player management functionality
"""
import pytest


class TestPlayerJoining:
    """Test player joining games"""
    
    def test_player_joins_game(self, client, sample_game):
        """Test a player successfully joining a game"""
        game_code = sample_game["game_code"]
        response = client.post("/api/join", json={
            "game_code": game_code,
            "player_name": "NewPlayer",
            "role": "player"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["player_name"] == "NewPlayer"
        assert data["role"] == "player"
        # Unauthenticated users need approval
        assert data["is_approved"] == False
    
    def test_guest_joins_game(self, client, sample_game):
        """Test a guest joining a game (needs approval)"""
        game_code = sample_game["game_code"]
        response = client.post("/api/join", json={
            "game_code": game_code,
            "player_name": "GuestPlayer",
            "role": "player"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["player_name"] == "GuestPlayer"
        assert data["is_approved"] == False  # Guests need approval
    
    def test_join_nonexistent_game(self, client):
        """Test joining a non-existent game"""
        response = client.post("/api/join", json={
            "game_code": "XXXXXX",
            "player_name": "Player",
            "role": "player"
        })
        
        assert response.status_code == 404
    
    def test_duplicate_player_name(self, client, sample_game):
        """Test joining with duplicate player name"""
        game_code = sample_game["game_code"]
        
        # First player joins
        client.post("/api/join", json={
            "game_code": game_code,
            "player_name": "SameName",
            "role": "player"
        })
        
        # Second player with same name
        response = client.post("/api/join", json={
            "game_code": game_code,
            "player_name": "SameName",
            "role": "player"
        })
        
        # Should reject duplicate names
        assert response.status_code == 400


class TestPlayerRetrieval:
    """Test retrieving player information"""
    
    def test_get_all_players(self, client, sample_game, sample_players):
        """Test retrieving all players in a game"""
        game_code = sample_game["game_code"]
        response = client.get(f"/games/{game_code}/players")
        
        assert response.status_code == 200
        players = response.json()
        assert isinstance(players, list)
        assert len(players) >= 3  # At least the 3 sample players
    
    def test_get_unassigned_players(self, client, sample_game, sample_players):
        """Test retrieving unassigned players"""
        game_code = sample_game["game_code"]
        response = client.get(f"/games/{game_code}/unassigned-players")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "players" in data
        assert "unassigned_count" in data
        # All players should be unassigned initially (excluding host)
        assert len(data["players"]) >= 3


class TestPlayerApproval:
    """Test guest player approval"""
    
    def test_approve_guest_player(self, client, sample_game):
        """Test approving a guest player"""
        game_code = sample_game["game_code"]
        
        # Add guest player
        join_response = client.post("/api/join", json={
            "game_code": game_code,
            "player_name": "GuestToApprove",
            "role": "player"
        })
        player_id = join_response.json()["id"]
        
        # Approve the player
        response = client.put(f"/games/{game_code}/players/{player_id}/approve")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["player"]["is_approved"] == True
    
    def test_approve_already_approved_player(self, client, sample_game, sample_players):
        """Test approving an already approved player"""
        game_code = sample_game["game_code"]
        player_id = sample_players[0]["id"]
        
        response = client.put(f"/games/{game_code}/players/{player_id}/approve")
        
        # Should succeed (idempotent) or return appropriate status
        assert response.status_code in [200, 400]


class TestRoleAssignment:
    """Test player role assignment"""
    
    def test_assign_player_to_banker(self, client, sample_game, sample_players):
        """Test promoting a player to banker"""
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
        assert data["player"]["group_number"] is None  # Bankers shouldn't have team
    
    def test_demote_banker_to_player(self, client, sample_game, sample_players):
        """Test demoting a banker back to player"""
        game_code = sample_game["game_code"]
        player_id = sample_players[0]["id"]
        
        # First promote to banker
        client.put(
            f"/games/{game_code}/players/{player_id}/assign-role",
            params={"role": "banker"}
        )
        
        # Then demote back to player
        response = client.put(
            f"/games/{game_code}/players/{player_id}/assign-role",
            params={"role": "player"}
        )
        
        assert response.status_code == 200
        assert response.json()["player"]["role"] == "player"
    
    def test_assign_invalid_role(self, client, sample_game, sample_players):
        """Test assigning an invalid role"""
        game_code = sample_game["game_code"]
        player_id = sample_players[0]["id"]
        
        response = client.put(
            f"/games/{game_code}/players/{player_id}/assign-role",
            params={"role": "invalid_role"}
        )
        
        assert response.status_code in [400, 422]  # Validation error


class TestPlayerRemoval:
    """Test removing players from game"""
    
    def test_remove_player(self, client, sample_game, sample_players):
        """Test removing a player from the game"""
        game_code = sample_game["game_code"]
        # Use a non-host player (sample_players[0] is host)
        player_id = sample_players[1]["id"]
        
        response = client.delete(f"/games/{game_code}/players/{player_id}")
        
        assert response.status_code == 200
        assert response.json()["success"] == True
    
    def test_remove_host_fails(self, client, sample_game):
        """Test that host cannot be removed"""
        game_code = sample_game["game_code"]
        
        # Get host player
        players_response = client.get(f"/games/{game_code}/players")
        players = players_response.json()
        host = next((p for p in players if p["role"] == "host"), None)
        assert host is not None, "Host player not found"
        
        response = client.delete(f"/games/{game_code}/players/{host['id']}")
        
        assert response.status_code == 400
        assert "host" in response.json()["detail"].lower()
    
    def test_clear_all_players(self, client, sample_game, sample_players):
        """Test clearing all non-host players"""
        game_code = sample_game["game_code"]
        
        response = client.delete(f"/games/{game_code}/players")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        # Should delete all players except host (sample_players[0])
        assert data["deleted_count"] == len(sample_players) - 1
    
    def test_remove_nonexistent_player(self, client, sample_game):
        """Test removing a non-existent player"""
        game_code = sample_game["game_code"]
        
        response = client.delete(f"/games/{game_code}/players/99999")
        
        assert response.status_code == 404
