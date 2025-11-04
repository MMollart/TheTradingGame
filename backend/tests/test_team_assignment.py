"""
Tests for team assignment functionality
"""
import pytest


class TestTeamAssignment:
    """Test assigning players to teams"""
    
    def test_assign_player_to_team(self, client, sample_game, sample_players):
        """Test assigning a player to a team"""
        game_code = sample_game["game_code"]
        # Use non-host player (sample_players[0] is host)
        player_id = sample_players[1]["id"]
        
        response = client.put(
            f"/games/{game_code}/players/{player_id}/assign-group",
            params={"group_number": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["player"]["group_number"] == 1
    
    def test_assign_multiple_players_to_teams(self, client, sample_game, sample_players):
        """Test assigning multiple players to different teams"""
        game_code = sample_game["game_code"]
        
        # Skip host (sample_players[0]) and assign players 1-3 to teams
        for i, player in enumerate(sample_players[1:4], start=1):
            response = client.put(
                f"/games/{game_code}/players/{player['id']}/assign-group",
                params={"group_number": i}
            )
            assert response.status_code == 200
            assert response.json()["player"]["group_number"] == i
    
    def test_reassign_player_to_different_team(self, client, sample_game, sample_players):
        """Test reassigning a player to a different team"""
        game_code = sample_game["game_code"]
        # Use non-host player
        player_id = sample_players[1]["id"]
        
        # First assignment
        client.put(
            f"/games/{game_code}/players/{player_id}/assign-group",
            params={"group_number": 1}
        )
        
        # Reassignment
        response = client.put(
            f"/games/{game_code}/players/{player_id}/assign-group",
            params={"group_number": 2}
        )
        
        assert response.status_code == 200
        assert response.json()["player"]["group_number"] == 2
    
    def test_assign_to_invalid_team_number(self, client, sample_game, sample_players):
        """Test assigning to invalid team number"""
        game_code = sample_game["game_code"]
        # Use non-host player
        player_id = sample_players[1]["id"]
        
        response = client.put(
            f"/games/{game_code}/players/{player_id}/assign-group",
            params={"group_number": 0}
        )
        
        # Should reject invalid team numbers
        assert response.status_code in [400, 422]


class TestTeamUnassignment:
    """Test removing players from teams"""
    
    def test_unassign_player_from_team(self, client, sample_game, sample_players):
        """Test removing a player from their team"""
        game_code = sample_game["game_code"]
        player_id = sample_players[0]["id"]
        
        # First assign to a team
        client.put(
            f"/games/{game_code}/players/{player_id}/assign-group",
            params={"group_number": 1}
        )
        
        # Then unassign
        response = client.delete(
            f"/games/{game_code}/players/{player_id}/unassign-group"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["player"]["group_number"] is None
    
    def test_unassign_unassigned_player(self, client, sample_game, sample_players):
        """Test unassigning a player who has no team"""
        game_code = sample_game["game_code"]
        player_id = sample_players[0]["id"]
        
        response = client.delete(
            f"/games/{game_code}/players/{player_id}/unassign-group"
        )
        
        # Should succeed (idempotent)
        assert response.status_code == 200


class TestAutoAssignment:
    """Test automatic team assignment"""
    
    def test_auto_assign_all_players(self, client, sample_game, sample_players):
        """Test automatically assigning all players to teams"""
        game_code = sample_game["game_code"]
        
        response = client.post(
            f"/games/{game_code}/auto-assign-groups",
            params={"num_teams": 2}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        # Should assign all non-host players (sample_players[0] is host)
        assert data["assigned_count"] == len(sample_players) - 1
    
    def test_auto_assign_distributes_evenly(self, client, sample_game, sample_players):
        """Test that auto-assign distributes players evenly"""
        game_code = sample_game["game_code"]
        num_teams = 2
        
        # Auto-assign
        client.post(
            f"/games/{game_code}/auto-assign-groups",
            params={"num_teams": num_teams}
        )
        
        # Check distribution
        response = client.get(f"/games/{game_code}/players")
        players = response.json()
        
        team_counts = {}
        for player in players:
            if player["group_number"]:
                team_counts[player["group_number"]] = team_counts.get(player["group_number"], 0) + 1
        
        # Teams should be relatively balanced
        assert len(team_counts) <= num_teams
        if len(team_counts) > 1:
            max_diff = max(team_counts.values()) - min(team_counts.values())
            assert max_diff <= 1  # At most 1 player difference
    
    def test_auto_assign_with_existing_assignments(self, client, sample_game, sample_players):
        """Test auto-assign when some players already have teams"""
        game_code = sample_game["game_code"]
        
        # Manually assign one player
        client.put(
            f"/games/{game_code}/players/{sample_players[0]['id']}/assign-group",
            params={"group_number": 1}
        )
        
        # Auto-assign the rest
        response = client.post(
            f"/games/{game_code}/auto-assign-groups",
            params={"num_teams": 2}
        )
        
        assert response.status_code == 200
        # Should only assign unassigned players
        assert response.json()["assigned_count"] == len(sample_players) - 1


class TestTeamQueries:
    """Test querying team information"""
    
    def test_get_team_members(self, client, sample_game, sample_players):
        """Test getting all members of a specific team"""
        game_code = sample_game["game_code"]
        
        # Assign players to teams
        for i, player in enumerate(sample_players):
            team_num = (i % 2) + 1  # Alternate between team 1 and 2
            client.put(
                f"/games/{game_code}/players/{player['id']}/assign-group",
                params={"group_number": team_num}
            )
        
        # Get all players
        response = client.get(f"/games/{game_code}/players")
        players = response.json()
        
        # Filter by team
        team_1_players = [p for p in players if p["group_number"] == 1]
        team_2_players = [p for p in players if p["group_number"] == 2]
        
        assert len(team_1_players) > 0
        assert len(team_2_players) > 0
    
    def test_unassigned_players_query(self, client, sample_game, sample_players):
        """Test getting only unassigned players"""
        game_code = sample_game["game_code"]
        
        # Assign a non-host player (sample_players[0] is host)
        client.put(
            f"/games/{game_code}/players/{sample_players[1]['id']}/assign-group",
            params={"group_number": 1}
        )
        
        # Get unassigned
        response = client.get(f"/games/{game_code}/unassigned-players")
        data = response.json()
        
        assert response.status_code == 200
        # Should have len(sample_players) - 2: -1 for host, -1 for assigned player
        assert data["unassigned_count"] == len(sample_players) - 2
        # Verify the assigned player is not in the list
        assert sample_players[1]["id"] not in [p["id"] for p in data["players"]]
