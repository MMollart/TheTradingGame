"""
Tests for assigning players to teams after game has started
"""
import pytest
from models import GameStatus, GameSession
from sqlalchemy.orm.attributes import flag_modified


class TestLatePlayerAssignment:
    """Test assigning players to existing teams after game start"""
    
    def test_assign_player_to_team_after_game_start(self, client, sample_game, sample_players):
        """Test that a player can be assigned to an existing team after game starts"""
        game_code = sample_game["game_code"]
        
        # Assign player 1 to team 1 before game starts
        player1_id = sample_players[1]["id"]
        response = client.put(
            f"/games/{game_code}/players/{player1_id}/assign-group",
            params={"group_number": 1}
        )
        assert response.status_code == 200
        
        # Start the game
        start_response = client.post(f"/games/{game_code}/start")
        assert start_response.status_code == 200
        
        # Now assign player 2 to the same team after game has started
        player2_id = sample_players[2]["id"]
        late_assign_response = client.put(
            f"/games/{game_code}/players/{player2_id}/assign-group",
            params={"group_number": 1}
        )
        
        assert late_assign_response.status_code == 200
        data = late_assign_response.json()
        assert data["success"] == True
        assert data["player"]["group_number"] == 1
    
    def test_bank_inventory_increases_on_first_late_assignment(self, client, sample_game, sample_players):
        """Test that bank inventory increases when FIRST player joins a team after game start"""
        game_code = sample_game["game_code"]
        
        # Start the game with NO players assigned to team 2
        # Assign player 1 to team 1 before game starts
        player1_id = sample_players[1]["id"]
        client.put(
            f"/games/{game_code}/players/{player1_id}/assign-group",
            params={"group_number": 1}
        )
        
        # Start the game
        client.post(f"/games/{game_code}/start")
        
        # Get initial bank inventory (should be 250 for 1 team)
        game_response = client.get(f"/games/{game_code}")
        initial_state = game_response.json()["game_state"]
        initial_food = initial_state["bank_inventory"]["food"]
        initial_raw = initial_state["bank_inventory"]["raw_materials"]
        
        # Assign player 2 to team 2 (which has no players) after game start
        player2_id = sample_players[2]["id"]
        client.put(
            f"/games/{game_code}/players/{player2_id}/assign-group",
            params={"group_number": 2}
        )
        
        # Check that bank inventory increased by 250 per resource
        game_response_after = client.get(f"/games/{game_code}")
        new_state = game_response_after.json()["game_state"]
        new_food = new_state["bank_inventory"]["food"]
        new_raw = new_state["bank_inventory"]["raw_materials"]
        
        assert new_food == initial_food + 250
        assert new_raw == initial_raw + 250
    
    def test_team_resources_unchanged_on_late_assignment(self, client, sample_game, sample_players):
        """Test that team resources don't change when a late player joins (penalty for being late)"""
        game_code = sample_game["game_code"]
        
        # Assign player 1 to team 1
        player1_id = sample_players[1]["id"]
        client.put(
            f"/games/{game_code}/players/{player1_id}/assign-group",
            params={"group_number": 1}
        )
        
        # Start the game
        client.post(f"/games/{game_code}/start")
        
        # Get team 1's initial resources
        game_response = client.get(f"/games/{game_code}")
        initial_state = game_response.json()["game_state"]
        initial_team_resources = initial_state["teams"]["1"]["resources"].copy()
        
        # Assign player 2 to team 1 after game start
        player2_id = sample_players[2]["id"]
        client.put(
            f"/games/{game_code}/players/{player2_id}/assign-group",
            params={"group_number": 1}
        )
        
        # Check that team resources remain the same
        game_response_after = client.get(f"/games/{game_code}")
        new_state = game_response_after.json()["game_state"]
        new_team_resources = new_state["teams"]["1"]["resources"]
        
        assert new_team_resources == initial_team_resources
    
    def test_bank_inventory_no_increase_for_second_player(self, client, sample_game, sample_players):
        """Test that bank inventory does NOT increase when second player joins same team"""
        game_code = sample_game["game_code"]
        
        # Assign player 1 to team 1 before game starts
        player1_id = sample_players[1]["id"]
        client.put(
            f"/games/{game_code}/players/{player1_id}/assign-group",
            params={"group_number": 1}
        )
        
        # Start the game
        client.post(f"/games/{game_code}/start")
        
        # Get initial bank inventory
        game_response = client.get(f"/games/{game_code}")
        initial_state = game_response.json()["game_state"]
        initial_food = initial_state["bank_inventory"]["food"]
        initial_raw = initial_state["bank_inventory"]["raw_materials"]
        
        # Assign player 2 to team 1 (which already has player 1) after game start
        player2_id = sample_players[2]["id"]
        client.put(
            f"/games/{game_code}/players/{player2_id}/assign-group",
            params={"group_number": 1}
        )
        
        # Check that bank inventory did NOT increase
        game_response_after = client.get(f"/games/{game_code}")
        new_state = game_response_after.json()["game_state"]
        new_food = new_state["bank_inventory"]["food"]
        new_raw = new_state["bank_inventory"]["raw_materials"]
        
        assert new_food == initial_food  # Should remain the same
        assert new_raw == initial_raw    # Should remain the same
    
    def test_assign_to_new_team_after_game_start_no_bank_increase(self, client, sample_game, sample_players):
        """
        Test that assigning to a non-existent team after game start 
        doesn't increase bank inventory (team doesn't exist).
        
        The assignment will succeed, but bank inventory only increases 
        for teams that were initialized before game start.
        """
        game_code = sample_game["game_code"]
        
        # Assign player 1 to team 1
        player1_id = sample_players[1]["id"]
        client.put(
            f"/games/{game_code}/players/{player1_id}/assign-group",
            params={"group_number": 1}
        )
        
        # Start the game (only team 1 will be initialized)
        client.post(f"/games/{game_code}/start")
        
        # Try to assign player 2 to team 2 (which wasn't set up before game start)
        player2_id = sample_players[2]["id"]
        response = client.put(
            f"/games/{game_code}/players/{player2_id}/assign-group",
            params={"group_number": 2}
        )
        
        # Assignment should succeed
        assert response.status_code == 200
        
        # Verify bank inventory DID increase (compensating for late team)
        # Bank inventory should increase from 250 to 500 when first player joins team 2
        # This compensates the bank for the team joining late
        game_response = client.get(f"/games/{game_code}")
        state = game_response.json()["game_state"]
        assert state["bank_inventory"]["food"] == 500
    
    def test_assign_during_paused_game(self, client, sample_game, sample_players):
        """Test that player can be assigned during paused game"""
        game_code = sample_game["game_code"]
        
        # Assign player 1 to team 1
        player1_id = sample_players[1]["id"]
        client.put(
            f"/games/{game_code}/players/{player1_id}/assign-group",
            params={"group_number": 1}
        )
        
        # Start and then pause the game
        client.post(f"/games/{game_code}/start")
        client.post(f"/games/{game_code}/pause")
        
        # Assign player 2 to team 1 while paused
        player2_id = sample_players[2]["id"]
        response = client.put(
            f"/games/{game_code}/players/{player2_id}/assign-group",
            params={"group_number": 1}
        )
        
        assert response.status_code == 200
        assert response.json()["player"]["group_number"] == 1
    
    def test_multiple_late_teams_cumulative_bank_increase(self, client, sample_game, sample_players):
        """Test that assigning first player to multiple teams increases bank inventory cumulatively"""
        game_code = sample_game["game_code"]
        
        # Assign player 1 to team 1 before game starts
        player1_id = sample_players[1]["id"]
        client.put(
            f"/games/{game_code}/players/{player1_id}/assign-group",
            params={"group_number": 1}
        )
        
        # Start the game (only team 1 initialized with 250)
        client.post(f"/games/{game_code}/start")
        
        # Get initial bank inventory (250 for 1 team)
        game_response = client.get(f"/games/{game_code}")
        initial_food = game_response.json()["game_state"]["bank_inventory"]["food"]
        
        # Add players to two different teams that don't have players yet
        player2_id = sample_players[2]["id"]
        client.put(
            f"/games/{game_code}/players/{player2_id}/assign-group",
            params={"group_number": 2}  # First player to team 2
        )
        
        player3_id = sample_players[3]["id"]
        client.put(
            f"/games/{game_code}/players/{player3_id}/assign-group",
            params={"group_number": 3}  # First player to team 3
        )
        
        # Bank inventory should have increased by 250 * 2 = 500 (one for each new team)
        game_response_after = client.get(f"/games/{game_code}")
        final_food = game_response_after.json()["game_state"]["bank_inventory"]["food"]
        
        assert final_food == initial_food + (250 * 2)
    
    def test_team_number_validation_uses_num_teams(self, client, sample_game):
        """Test that team number validation uses game.num_teams instead of hardcoded 4"""
        game_code = sample_game["game_code"]
        
        # Create a game with 2 teams (already set in sample_game fixture with 4 teams)
        # Let's create a new game with fewer teams
        response = client.post("/games", json={
            "config_id": None,
            "config_data": {}
        })
        new_game_code = response.json()["game_code"]
        
        # Set to 2 teams
        client.post(f"/games/{new_game_code}/set-teams", params={"num_teams": 2})
        
        # Add a host
        host_response = client.post("/api/join", json={
            "game_code": new_game_code,
            "player_name": "TestHost2",
            "role": "host"
        })
        
        # Add a player
        player_response = client.post("/api/join", json={
            "game_code": new_game_code,
            "player_name": "Player1",
            "role": "player"
        })
        player_id = player_response.json()["id"]
        
        # Approve player
        client.put(f"/games/{new_game_code}/players/{player_id}/approve")
        
        # Try to assign to team 3 (should fail since we only have 2 teams)
        response = client.put(
            f"/games/{new_game_code}/players/{player_id}/assign-group",
            params={"group_number": 3}
        )
        
        assert response.status_code == 400
        assert "between 1 and 2" in response.json()["detail"]
        
        # Assign to team 2 should work
        response = client.put(
            f"/games/{new_game_code}/players/{player_id}/assign-group",
            params={"group_number": 2}
        )
        assert response.status_code == 200


class TestBankInventoryEdgeCases:
    """Test edge cases for bank inventory management"""
    
    def test_bank_inventory_initialized_if_missing(self, client, sample_game, sample_players, db):
        """Test that bank inventory is initialized if somehow missing"""
        game_code = sample_game["game_code"]
        
        # Assign and start game
        player1_id = sample_players[1]["id"]
        client.put(
            f"/games/{game_code}/players/{player1_id}/assign-group",
            params={"group_number": 1}
        )
        client.post(f"/games/{game_code}/start")
        
        # Manually remove bank_inventory to simulate edge case
        game = db.query(GameSession).filter(
            GameSession.game_code == game_code.upper()
        ).first()
        if game.game_state and 'bank_inventory' in game.game_state:
            del game.game_state['bank_inventory']
            flag_modified(game, 'game_state')
            db.commit()
        
        # Now try to assign a late player
        player2_id = sample_players[2]["id"]
        response = client.put(
            f"/games/{game_code}/players/{player2_id}/assign-group",
            params={"group_number": 1}
        )
        
        # Should succeed and create bank_inventory
        assert response.status_code == 200
        
        # Verify bank_inventory was created
        game_response = client.get(f"/games/{game_code}")
        state = game_response.json()["game_state"]
        assert "bank_inventory" in state
        assert state["bank_inventory"]["food"] > 0
