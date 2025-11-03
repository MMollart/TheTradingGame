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
    """Create a test client with overridden database"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_game(client):
    """Create a sample game session"""
    response = client.post("/games/", json={
        "host_name": "TestHost",
        "num_teams": 4
    })
    assert response.status_code == 201
    game_data = response.json()
    return game_data


@pytest.fixture
def sample_players(client, sample_game):
    """Create sample players in a game"""
    game_code = sample_game["game_code"]
    players = []
    
    # Add host (already exists from game creation)
    # Add 3 regular players
    for i in range(1, 4):
        response = client.post("/api/join", json={
            "game_code": game_code,
            "player_name": f"Player{i}",
            "role": "player"
        })
        assert response.status_code == 200
        players.append(response.json())
    
    return players


@pytest.fixture
def authenticated_headers():
    """Mock authentication headers"""
    return {"Authorization": "Bearer fake_token_for_testing"}
