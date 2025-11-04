"""
Test that Host can complete challenges when no Banker exists

This test addresses the issue where hosts couldn't complete challenges
when there was no banker in the game.
"""
import pytest
from models import Challenge, ChallengeStatus, Player, GameSession


@pytest.mark.quick
def test_host_can_complete_challenge_without_banker(client, sample_game, db):
    """
    Test that a host can complete challenges in a game without a banker.
    
    This is the critical test for the fix - previously this would fail with
    "Banker not found" error.
    """
    game_code = sample_game["game_code"]
    
    # Add a player to Team 1
    player_response = client.post("/api/join", json={
        "game_code": game_code,
        "player_name": "TeamPlayer",
        "role": "player"
    })
    assert player_response.status_code == 200
    player_data = player_response.json()
    player_id = player_data["id"]
    
    # Approve the player
    approve_response = client.put(f"/games/{game_code}/players/{player_id}/approve")
    assert approve_response.status_code == 200
    
    # Assign player to Team 1
    assign_response = client.post(
        f"/games/{game_code}/players/{player_id}/assign-team",
        params={"team_number": 1}
    )
    assert assign_response.status_code == 200
    
    # Start the game (this initializes team states but NO banker exists)
    start_response = client.post(f"/games/{game_code}/start")
    assert start_response.status_code == 200, f"Failed to start game: {start_response.text}"
    
    # Verify no banker exists in the game
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    bankers = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.role == "banker"
    ).all()
    assert len(bankers) == 0, "Test setup error: Banker should not exist"
    
    # Verify host exists
    hosts = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.role == "host"
    ).all()
    assert len(hosts) == 1, "Test setup error: Host should exist"
    
    # Create a challenge for the player
    challenge = Challenge(
        game_session_id=game.id,
        player_id=player_id,
        building_type="farm",
        building_name="🌾 Farm",
        team_number=1,
        has_school=False,
        status=ChallengeStatus.ASSIGNED,
        challenge_type="push_ups",
        challenge_description="20 Push-ups",
        target_number=20
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    
    # Try to complete the challenge (this is where it previously failed)
    complete_response = client.post(
        f"/games/{game_code}/challenges/{challenge.id}/complete",
        json={
            "team_number": 1,
            "resource_type": "food",
            "amount": 15  # 3 farms * 5 food per farm
        }
    )
    
    # This should now succeed with the fix
    assert complete_response.status_code == 200, f"Failed to complete challenge: {complete_response.status_code} - {complete_response.text}"
    response_data = complete_response.json()
    
    assert response_data["success"] is True
    assert "Transferred" in response_data["message"]
    assert response_data["bank_remaining"] == 985  # 1000 - 15
    assert response_data["team_total"] >= 15  # At least the transferred amount
    
    # Verify challenge status
    db.refresh(challenge)
    assert challenge.status == ChallengeStatus.COMPLETED
    assert challenge.completed_at is not None


@pytest.mark.quick
def test_host_bank_inventory_initialized(client, sample_game, db):
    """
    Test that host's bank inventory is properly initialized when completing a challenge.
    """
    game_code = sample_game["game_code"]
    
    # Add a player
    player_response = client.post("/api/join", json={
        "game_code": game_code,
        "player_name": "TeamPlayer",
        "role": "player"
    })
    assert player_response.status_code == 200
    player_id = player_response.json()["id"]
    
    # Approve and assign to team
    client.put(f"/games/{game_code}/players/{player_id}/approve")
    client.post(f"/games/{game_code}/players/{player_id}/assign-team", params={"team_number": 1})
    
    # Start the game
    client.post(f"/games/{game_code}/start")
    
    # Get the host player
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    host = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.role == "host"
    ).first()
    
    # Before completing a challenge, host might not have bank inventory
    initial_state = host.player_state or {}
    assert 'bank_inventory' not in initial_state or initial_state.get('bank_inventory') == {}
    
    # Create and complete a challenge
    challenge = Challenge(
        game_session_id=game.id,
        player_id=player_id,
        building_type="farm",
        building_name="🌾 Farm",
        team_number=1,
        has_school=False,
        status=ChallengeStatus.ASSIGNED,
        challenge_type="push_ups",
        challenge_description="20 Push-ups",
        target_number=20
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    
    # Complete the challenge
    complete_response = client.post(
        f"/games/{game_code}/challenges/{challenge.id}/complete",
        json={
            "team_number": 1,
            "resource_type": "food",
            "amount": 15
        }
    )
    assert complete_response.status_code == 200
    
    # Verify host now has initialized bank inventory
    db.refresh(host)
    assert host.player_state is not None
    assert 'bank_inventory' in host.player_state
    assert host.player_state['bank_inventory']['food'] == 985  # 1000 - 15


@pytest.mark.quick
def test_banker_takes_precedence_over_host(client, sample_game, db):
    """
    Test that if both banker and host exist, banker is used for bank management.
    """
    game_code = sample_game["game_code"]
    
    # Add a banker
    banker_response = client.post("/api/join", json={
        "game_code": game_code,
        "player_name": "Banker",
        "role": "banker"
    })
    assert banker_response.status_code == 200
    banker_id = banker_response.json()["id"]
    
    # Add a player
    player_response = client.post("/api/join", json={
        "game_code": game_code,
        "player_name": "TeamPlayer",
        "role": "player"
    })
    assert player_response.status_code == 200
    player_id = player_response.json()["id"]
    
    # Approve and assign player to team
    client.put(f"/games/{game_code}/players/{player_id}/approve")
    client.post(f"/games/{game_code}/players/{player_id}/assign-team", params={"team_number": 1})
    
    # Start the game (this initializes banker's bank_inventory)
    client.post(f"/games/{game_code}/start")
    
    # Verify both banker and host exist
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    banker = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.role == "banker"
    ).first()
    host = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.role == "host"
    ).first()
    assert banker is not None
    assert host is not None
    
    # Banker should have initialized bank inventory
    assert 'bank_inventory' in banker.player_state
    initial_banker_food = banker.player_state['bank_inventory']['food']
    
    # Create and complete a challenge
    challenge = Challenge(
        game_session_id=game.id,
        player_id=player_id,
        building_type="farm",
        building_name="🌾 Farm",
        team_number=1,
        has_school=False,
        status=ChallengeStatus.ASSIGNED,
        challenge_type="push_ups",
        challenge_description="20 Push-ups",
        target_number=20
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    
    # Complete the challenge
    complete_response = client.post(
        f"/games/{game_code}/challenges/{challenge.id}/complete",
        json={
            "team_number": 1,
            "resource_type": "food",
            "amount": 15
        }
    )
    assert complete_response.status_code == 200
    
    # Verify banker's inventory was used (not host's)
    db.refresh(banker)
    db.refresh(host)
    assert banker.player_state['bank_inventory']['food'] == initial_banker_food - 15
    
    # Host should not have bank_inventory (since banker exists)
    assert 'bank_inventory' not in host.player_state or host.player_state.get('bank_inventory', {}).get('food', 0) == 0
