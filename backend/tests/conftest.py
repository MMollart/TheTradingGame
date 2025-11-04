"""
Pytest configuration and fixtures for Trading Game tests
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from database import get_db
from models import Base

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with overridden database and optional auth bypass"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    # Override auth to return None (simulate unauthenticated but allowed access)
    from auth import get_current_user_optional
    def override_get_current_user_optional():
        return None
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_optional] = override_get_current_user_optional
    
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_game(client):
    """Create a sample game session with host"""
    # Step 1: Create game session
    response = client.post("/games", json={
        "config_id": None,
        "config_data": {}
    })
    assert response.status_code == 201, f"Failed to create game: {response.status_code} - {response.text}"
    game_data = response.json()
    game_code = game_data["game_code"]
    
    # Step 2: Set number of teams
    teams_response = client.post(f"/games/{game_code}/set-teams", params={"num_teams": 4})
    assert teams_response.status_code == 200, f"Failed to set teams: {teams_response.status_code}"
    
    # Step 3: Host joins the game
    host_response = client.post("/api/join", json={
        "game_code": game_code,
        "player_name": "TestHost",
        "role": "host"  # Host role auto-approves
    })
    assert host_response.status_code == 200, f"Failed to add host: {host_response.status_code} - {host_response.text}"
    
    # Return game data with updated team count
    game_data["num_teams"] = 4
    game_data["host_player"] = host_response.json()
    return game_data


@pytest.fixture
def sample_players(client, sample_game):
    """Create sample players in a game"""
    game_code = sample_game["game_code"]
    players = []
    
    # Get the host player that was created with the game
    host_response = client.get(f"/games/{game_code}/players")
    if host_response.status_code == 200:
        host_players = [p for p in host_response.json() if p.get("role") == "host"]
        if host_players:
            players.extend(host_players)
    
    # Add 3 regular players (will join as guests with is_approved=False)
    for i in range(1, 4):
        response = client.post("/api/join", json={
            "game_code": game_code,
            "player_name": f"Player{i}",
            "role": "player"
        })
        assert response.status_code == 200, f"Failed to add player: {response.status_code} - {response.text}"
        player_data = response.json()
        
        # Approve the player immediately for testing
        if not player_data.get("is_approved", False):
            approve_response = client.put(
                f"/games/{game_code}/players/{player_data['id']}/approve"
            )
            if approve_response.status_code == 200:
                approve_data = approve_response.json()
                player_data = approve_data.get("player", player_data)
        
        players.append(player_data)
    
    return players


@pytest.fixture
def authenticated_headers():
    """Mock authentication headers"""
    return {"Authorization": "Bearer fake_token_for_testing"}
