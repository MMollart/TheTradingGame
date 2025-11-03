# Testing Guide for The Trading Game Backend

## Quick Start

Install test dependencies:
```bash
cd backend
pip install -r requirements-test.txt
```

Run all tests:
```bash
pytest
# OR from project root:
python -m pytest backend/tests/
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

## VS Code Test Discovery

The project is configured to use pytest in VS Code. Configuration files:
- **Workspace**: `.vscode/settings.json` - Enables pytest globally
- **Project**: `TheTradingGame/.vscode/settings.json` - Project-specific pytest config
- **Backend**: `backend/pytest.ini` - Pytest configuration

## Test Structure

### Test Files

- **conftest.py** - Pytest fixtures and configuration
  - `db` - In-memory SQLite database
  - `client` - FastAPI TestClient
  - `sample_game` - Pre-created game session
  - `sample_players` - 3 test players

- **test_game_management.py** - Game CRUD operations
  - Game creation and validation
  - Game retrieval (by code, case-insensitive)
  - Status management (start, pause, resume, end)
  - Team configuration updates

- **test_player_management.py** - Player operations
  - Joining games (authenticated & guest)
  - Player retrieval (all, unassigned)
  - Guest approval workflow
  - Role assignment (promote, demote)
  - Player removal (single, bulk, protection)

- **test_team_assignment.py** - Team management
  - Manual team assignment
  - Team reassignment
  - Unassignment from teams
  - Auto-assignment algorithm
  - Team distribution queries

- **test_authentication.py** - Auth & authorization
  - User login with JWT tokens
  - Guest player approval
  - Role-based access control
  - Host protection rules

## Running Specific Tests

Run a specific test file:
```bash
pytest tests/test_game_management.py
```

Run a specific test class:
```bash
pytest tests/test_player_management.py::TestPlayerRemoval
```

Run a specific test:
```bash
pytest tests/test_player_management.py::TestPlayerRemoval::test_clear_all_players
```

Run with markers (when defined):
```bash
pytest -m quick      # Fast unit tests only
pytest -m integration  # Integration tests only
```

## Test Coverage

Generate coverage report:
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html  # View in browser
```

Check coverage for specific module:
```bash
pytest --cov=main --cov-report=term
```

## Writing New Tests

### Using Fixtures

```python
def test_something(client, sample_game, sample_players):
    """Use fixtures to avoid setup duplication"""
    game_code = sample_game["game_code"]
    player_id = sample_players[0]["id"]
    
    response = client.get(f"/games/{game_code}/players/{player_id}")
    assert response.status_code == 200
```

### Test Structure Template

```python
class TestFeatureName:
    """Test group for related functionality"""
    
    def test_success_case(self, client):
        """Test the happy path"""
        response = client.post("/endpoint", json={...})
        assert response.status_code == 200
    
    def test_error_case(self, client):
        """Test error handling"""
        response = client.post("/endpoint", json={...})
        assert response.status_code == 400
```

## Current Test Coverage

### Covered Functionality ✅

- Game creation, retrieval, status management
- Player joining (authenticated & guest)
- Guest approval workflow
- Role assignment (Host, Banker, Player)
- Team assignment (manual, auto, unassign)
- Player removal (single, bulk, host protection)
- Team configuration (num_teams updates)
- JWT authentication and token generation
- Authorization rules (role-based access)

### Not Yet Covered ⚠️

- WebSocket real-time updates
- Game mechanics (trading, production, disasters)
- Bank inventory management
- Price calculations
- Multi-user concurrent operations
- Frontend JavaScript logic

## Debugging Failed Tests

Verbose output:
```bash
pytest -vv
```

Show print statements:
```bash
pytest -s
```

Drop into debugger on failure:
```bash
pytest --pdb
```

Show local variables on failure:
```bash
pytest -l
```

## Continuous Integration

To run tests in CI/CD pipeline:
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Run tests with coverage
pytest --cov=. --cov-report=xml --cov-report=term

# Fail if coverage below threshold
pytest --cov=. --cov-fail-under=80
```

## Test Data

### Sample Game
- game_code: Auto-generated (e.g., "ABC123")
- host_name: "TestHost"
- num_teams: 4
- status: "setup"

### Sample Players
- Player 1: "Player1", role=Player, approved=True
- Player 2: "Player2", role=Player, approved=True  
- Player 3: "Player3", role=Player, approved=True

All players are pre-approved authenticated users.

## Common Issues

### Import Errors
If tests can't import modules:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Database Errors
Tests use in-memory SQLite, so no persistent data issues. Each test gets a fresh database.

### Port Conflicts
Tests use TestClient which doesn't bind to actual ports. No need to stop running server.

## Next Steps

1. Run full test suite: `pytest`
2. Check coverage: `pytest --cov=. --cov-report=html`
3. Add tests for any uncovered functionality
4. Integrate into CI/CD pipeline
5. Consider adding frontend tests (Jest/Mocha)
6. Add WebSocket integration tests
7. Add end-to-end game flow tests
