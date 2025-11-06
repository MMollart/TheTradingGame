# Copilot Instructions for The Trading Game

## Project Overview

**The Trading Game** is a real-time multiplayer economic simulation where player teams manage nation economies with role-based access (Host, Banker, Players). Core gameplay involves production challenges (physical activities), resource trading, and building construction with WebSocket-based synchronization.

## Architecture

### Stack
- **Backend**: Python 3.8+ with FastAPI, SQLAlchemy, SQLite, WebSockets
- **Frontend**: Vanilla JavaScript (no frameworks), HTML5, CSS3
- **Real-time**: WebSocket connections via FastAPI (`/ws/{game_code}/{player_id}`)

### Key Architectural Patterns

**1. Team-Level State Management**
- Resources/buildings stored in `GameSession.game_state['teams'][team_number]`, NOT in individual `Player.player_state`
- Multiple players per team share state via WebSocket broadcasts
- Example:
```python
game.game_state['teams']['1'] = {
    'resources': {'food': 30, 'currency': 50},
    'buildings': {'farm': 3, 'mine': 1},
    'nation_type': 'nation_1'  # Cycles through 4 nation types
}
```

**2. Role-Based Access Control**
- `host`: Full control (start/pause, assign teams, view all)
- `banker`: Manages challenges, bank transactions, economy
- `player`: Team gameplay (production, trading, building)
- Frontend: Cards shown/hidden based on `currentPlayer.role` and `currentGameStatus`

**3. Challenge System (Production Gating)**
Players request physical challenges (push-ups, burpees) → Host/Banker assigns → Player completes → Production unlocks.

**Architecture**:
- Backend: `ChallengeManager` service + v2 REST API (`/api/v2/challenges/`)
- Frontend: `ChallengeManager` class in `challenge-manager.js`
- Database as source of truth; WebSocket events sync state
- **Pause-aware timing**: 10-minute challenge duration pauses when game pauses; `assigned_at` timestamps adjusted via `/adjust-for-pause`

**Key files**:
- Backend: `backend/challenge_manager.py`, `backend/challenge_api.py`, `backend/models.py` (Challenge, ChallengeStatus enum)
- Frontend: `frontend/challenge-manager.js`, `frontend/dashboard.js` (WebSocket handlers)
- Docs: `docs/CHALLENGE_SYSTEM_README.md`, `docs/FEATURE-LOBBY-AND-CHALLENGES.md`

**4. WebSocket Event Protocol**
Format: `{"type": "event", "event_type": "<specific_event>", "data": {...}}`

Critical events:
- `challenge_request`, `challenge_assigned`, `challenge_completed`, `challenge_cancelled`, `challenge_expired`
- `player_joined`, `player_approved`, `player_assigned_team`, `player_role_changed`
- `game_status_changed`, `team_name_changed`, `lobby_cleared`

Handler: `websocket_manager.py` broadcasts to `active_connections[game_code]`

## Development Workflows

### Azure Deployment

**Production Site**: https://tg.pegasusesu.org.uk

**Deployment Trigger**: Git push to `main` branch triggers automatic Azure deployment

**Deployment Configuration**:
- `.deployment` file: Specifies `PROJECT=backend` subdirectory
- Startup command: `python -m uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'`
- Python version: 3.11
- App Service Plan: Linux, UK South region
- Database: Azure PostgreSQL Flexible Server

**Critical Startup Flags**:
- `--proxy-headers`: **Required** for Azure reverse proxy to route WebSocket connections correctly
- `--forwarded-allow-ips='*'`: Trust Azure's proxy headers for proper client IP detection

**Environment Variables** (set in Azure Portal):
```bash
WEBSITES_PORT=8000
POSTGRES_HOST=<azure-postgres-server>
POSTGRES_DB=trading_game
POSTGRES_USER=<username>
POSTGRES_PASSWORD=<password>
```

**CORS Configuration**:
- Application-level: FastAPI middleware in `backend/main.py`
- Platform-level: Azure CORS settings (configure via Azure Portal or `az webapp cors add`)
- Allowed origins: https://tg.pegasusesu.org.uk + Azure default domain

**Monitoring Deployment**:
```bash
# View live deployment logs
az webapp log tail --name thetradinggame --resource-group TradingGame

# Download application logs
az webapp log download --name thetradinggame --resource-group TradingGame

# Check deployment status
az webapp show --name thetradinggame --resource-group TradingGame --query state
```

**Common Deployment Issues**:
1. **"column does not exist" errors**: Migration not registered in `migrate.py`
2. **WebSocket not connecting**: Missing `--proxy-headers` flag
3. **CORS errors**: Check both application and platform-level CORS settings
4. **Scheduler failing**: Old games need cleanup, check `food_tax_scheduler.py` logs

### Server Management
```bash
# Start both servers (backend:8000, frontend:3000)
./restart-servers.sh

# View logs
tail -f /tmp/trading-game-backend.log

# Stop servers
./stop-servers.sh

# Or manual start
cd backend && python main.py  # Backend
cd frontend && python3 -m http.server 3000  # Frontend
```

### Testing
```bash
# Backend tests (pytest) - 210+ tests total
cd backend
pytest -v                              # All tests
pytest test_challenge_manager.py -v   # Specific module
pytest -m quick                        # Quick unit tests only
pytest -m integration                  # Integration tests

# Coverage
pytest --cov=challenge_manager --cov-report=html

# Quick validation before committing
pytest -q --tb=line  # Quiet mode with line-level errors
```

**Test markers** (defined in `backend/pytest.ini`):
- `quick`: Fast unit tests
- `integration`: API/database integration
- `slow`, `websocket`: Performance/WebSocket tests

**Critical Test Infrastructure Pattern**:
SQLAlchemy only creates tables/columns for models that are **imported before** `Base.metadata.create_all()`. Always import ALL model classes in:
- `backend/tests/conftest.py` (test fixtures)
- `backend/database.py` (production initialization)

Example:
```python
from models import (
    Base, User, GameSession, Player, GameConfiguration,
    Challenge, TradeOffer, PriceHistory, OAuthToken
)
```

If you add a new model or column and tests fail with "no such column" errors, check that the model is imported in both locations above.

### Database Operations
```bash
# Reset database (useful for testing)
rm backend/trading_game.db
python backend/main.py  # Auto-creates schema

# Check port conflicts
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

**Database Migrations** (`backend/migrate.py`):
Migrations run automatically on app startup via `run_migrations()`. When adding new columns:

1. Add column to model in `backend/models.py`
2. Import model in `backend/database.py` `init_db()` function
3. Create migration entry in `backend/migrate.py`:
```python
{
    "name": "00X_add_column_name",
    "description": "Add column_name to table_name",
    "sql": """
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name='table_name' AND column_name='column_name'
            ) THEN
                ALTER TABLE table_name ADD COLUMN column_name VARCHAR(50);
                RAISE NOTICE 'Added column_name column';
            END IF;
        END $$;
    """
}
```
4. Test locally with pytest (SQLite skips migrations, columns created via model imports)
5. Deploy to production (PostgreSQL runs migration on startup)

**PostgreSQL vs SQLite**:
- **PostgreSQL** (production): Uses DO blocks with IF NOT EXISTS checks
- **SQLite** (local/tests): Skips migrations, tables created with all columns via `Base.metadata.create_all()`

## Code Conventions

### Backend Patterns

**1. Async Endpoints for WebSocket Broadcasts**
All endpoints that broadcast WebSocket events MUST be `async`:
```python
@router.post("/games/{game_code}/start")
async def start_game(game_code: str, db: Session = Depends(get_db)):
    game.status = GameStatus.IN_PROGRESS
    db.commit()
    
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "game_status_changed",
        "status": "in_progress"
    })
```

**2. Service Layer for Business Logic**
Use service classes (e.g., `ChallengeManager`) for logic; API routes stay thin:
```python
# Good: In challenge_api.py
challenge_mgr = ChallengeManager(db)
challenge = await challenge_mgr.assign_challenge(challenge_id, ...)

# Avoid: Business logic in route handler
```

**3. SQLAlchemy JSON Column Mutations**
Mark modified when updating JSON columns:
```python
game.game_state['teams']['1']['resources']['food'] = 100
flag_modified(game, 'game_state')  # Required!
db.commit()
```

**4. Game Code Normalization**
Always uppercase: `game_code.upper()` in queries and WebSocket broadcasts

### Frontend Patterns

**1. Global State Management**
Key globals in `dashboard.js`:
- `currentPlayer`: `{id, name, role}`
- `currentGameCode`: 6-digit code
- `currentGameStatus`: `'waiting'|'in_progress'|'paused'|'completed'`
- `teamState`: `{resources: {}, buildings: {}}` (for player role)
- `challengeManager`: Instance of ChallengeManager class

**2. WebSocket Event Handling**
```javascript
// In dashboard.js handleGameEvent()
if (message.type === 'event') {
    const event_type = message.event_type;
    const eventData = message.data;
    
    switch (event_type) {
        case 'challenge_request':
            challengeManager.handleChallengeRequest(eventData);
            break;
        // ...
    }
}
```

**3. Role-Based UI Visibility**
```javascript
function showDashboard(role) {
    document.getElementById('host-dashboard').style.display = 
        role === 'host' ? 'block' : 'none';
    // Show/hide cards based on role AND game status
    updatePlayerCardsVisibility();  // Hides Production/Trading in WAITING state
}
```

**4. ChallengeManager Usage**
Initialize after game starts:
```javascript
challengeManager = new ChallengeManager(currentGameCode, currentPlayer, gameAPI, gameWS);
await challengeManager.initialize();  // Loads from server

// Request challenge (player)
await challengeManager.requestChallenge(playerId, 'farm', '🌾 Farm', teamNum, hasSchool);

// Assign challenge (host/banker)
await challengeManager.assignChallenge(challengeId, 'push_ups', '20 Push-ups', 20);
```

## Critical Integration Points

### Nation Type System
4 nation types cycle through teams (1-4, 5-8, etc.):
- `nation_1`: Food-producing nation (high food, low medical)
- `nation_2`: Raw materials nation
- `nation_3`: Electrical goods nation
- `nation_4`: Medical goods nation

Starting resources defined in `backend/game_constants.py` (`NATION_STARTING_RESOURCES`)

### Production Challenge Flow
1. Player clicks `📋 Request Challenge` → API call to `/api/v2/challenges/{game_code}/request`
2. Backend broadcasts `challenge_request` event → Host/Banker dashboard updates
3. Host/Banker selects challenge type (dropdown) → `/api/v2/challenges/{game_code}/{id}/assign`
4. Backend broadcasts `challenge_assigned` → Player sees challenge description
5. Player completes physical challenge → `/api/v2/challenges/{game_code}/{id}/complete`
6. Backend unlocks production, grants resources to team

**Locking behavior**:
- `has_school=false`: Entire building type locked for whole team until completion
- `has_school=true`: Only locked for individual player

### Game Duration & Pause System
- Duration: 60, 90, 120, 150, 180, 210, 240 minutes (30-min intervals)
- Set via: `/games/{game_code}/set-duration`
- Pausing: Frontend tracks `totalPausedTime` and `lastPauseTime`
- On resume: Call `/games/{game_code}/challenges/adjust-for-pause` with `pause_duration_ms`

### Historical Scenarios System (NEW)

**Purpose**: Add educational historical context and specialized game mechanics

**Available Scenarios** (defined in `backend/scenarios.py`):
1. **Silk Road Trade Routes** (easy, 90 min, 4 teams) - Ancient trade network simulation
2. **Marshall Plan Recovery** (medium, 120 min, 4 teams) - Post-WWII European recovery with aid mechanics
3. **Industrial Revolution Britain** (hard, 120 min, 4 teams) - Technological advancement and labor management
4. **Space Race Economics** (medium, 90 min, 2 teams) - USA vs USSR space competition
5. **Age of Exploration** (medium, 150 min, 5 teams) - Colonial trading and exploration
6. **Great Depression Era** (hard, 180 min, 6 teams) - Economic crisis management

**Setting a Scenario**:
```javascript
// API endpoint: POST /games/{game_code}/set-scenario
// Request body: {"scenario_id": "silk_road"}
```

**Effects of setting scenario**:
- Sets `game.scenario_id` (VARCHAR(50) column)
- Auto-configures `num_teams` based on scenario nations
- Sets `game_duration_minutes` to recommended duration
- Sets `difficulty` level (easy/medium/hard)
- Initializes `game_state.scenario` with special rules, victory conditions

**Database Schema**:
- `game_sessions.scenario_id` - Nullable VARCHAR(50), added via migration 003
- `game_sessions.difficulty` - VARCHAR(10) with CHECK constraint (easy/medium/hard)
- Index on `scenario_id` for faster queries

**Constraints**:
- Can only be set before game starts (`status = WAITING`)
- Once game starts, scenario cannot be changed
- Setting scenario returns: `scenario_id`, `scenario_name`, `num_teams`, `game_duration_minutes`, `difficulty`

**Schedulers Aware of Scenarios**:
- `food_tax_scheduler.py` - Queries games including scenario_id
- `scenario_event_scheduler.py` - Triggers historical events based on scenario and game time

### WebSocket Connection Lifecycle
```javascript
// Connect on dashboard load
gameWS = new GameWebSocket(currentGameCode, currentPlayer.id, handleGameEvent);
await gameWS.connect();

// Disconnect on unload
window.addEventListener('beforeunload', () => gameWS.disconnect());
```

## Common Pitfalls

1. **Forgetting `await` on broadcasts**: Always `async def` for WebSocket endpoints
2. **Not uppercasing game codes**: Use `.upper()` consistently
3. **Stale challenge state**: Call `challengeManager.loadFromServer()` after resume/reconnect
4. **Missing flag_modified()**: SQLAlchemy won't persist nested JSON changes without it
5. **Role string case**: Database stores lowercase (`'host'`, `'banker'`, `'player'`)
6. **Cache busting**: Increment `?v=X` query params in dashboard.html script tags after JS changes
7. **Model imports missing**: If tests fail with "no such column" error, ensure ALL models are imported in `conftest.py` and `database.py` before `Base.metadata.create_all()`
8. **PostgreSQL migrations not registered**: New columns must have migration entry in `migrate.py` migrations list for production deployment
9. **WebSocket in production**: Azure deployment requires `--proxy-headers` and `--forwarded-allow-ips='*'` flags in uvicorn startup command
10. **Player name in broadcasts**: Always include `player_name` field in WebSocket events to avoid "undefined" in UI

## Key Files Reference

- **Backend entry**: `backend/main.py` (FastAPI app, routes, WebSocket endpoint)
- **Models**: `backend/models.py` (User, GameSession, Player, Challenge, enums)
- **Game logic**: `backend/game_logic.py`, `backend/game_constants.py`
- **WebSocket**: `backend/websocket_manager.py` (ConnectionManager, broadcast methods)
- **Challenge system**: `backend/challenge_manager.py`, `backend/challenge_api.py`
- **Frontend dashboard**: `frontend/dashboard.html`, `frontend/dashboard.js`
- **Challenge manager**: `frontend/challenge-manager.js`, `frontend/game-api.js`
- **Tests**: `backend/tests/test_challenge_manager.py`, `backend/tests/conftest.py`

## Feature Documentation

All documentation files are now organized in the `docs/` directory. See [docs/README.md](../docs/README.md) for the complete documentation index.

### Getting Started Documentation
- **[QUICKSTART.md](../docs/QUICKSTART.md)**: Server management scripts, development workflow, testing
- **[OSM_OAUTH_SETUP.md](../docs/OSM_OAUTH_SETUP.md)**: OnlineScoutManager OAuth2 integration setup

### Core Feature Documentation
- **[CHALLENGE_SYSTEM_README.md](../docs/CHALLENGE_SYSTEM_README.md)**: Complete challenge architecture, multi-user support, pause-aware timing, API reference, testing guide
- **[FEATURE-LOBBY-AND-CHALLENGES.md](../docs/FEATURE-LOBBY-AND-CHALLENGES.md)**: Lobby state management, challenge request workflow, player approval system
- **[FEATURE-GAME-DURATION.md](../docs/FEATURE-GAME-DURATION.md)**: Configurable game duration (1-4 hours), game timer implementation, pause/resume behavior
- **[FEATURE-FOOD-TAX-AUTOMATION.md](../docs/FEATURE-FOOD-TAX-AUTOMATION.md)**: Automated food tax system, banker controls, penalty mechanics
- **[FOOD-TAX-QUICKSTART.md](../docs/FOOD-TAX-QUICKSTART.md)**: Quick guide for using food tax feature
- **[TRADING_FEATURE_README.md](../docs/TRADING_FEATURE_README.md)**: Resource trading system, team-to-team trading, World Bank trading
- **[BUILDING-CONSTRUCTION-SYSTEM.md](../docs/BUILDING-CONSTRUCTION-SYSTEM.md)**: Building types, construction costs, production multipliers

### Architecture & Implementation
- **[CHALLENGE-WEBSOCKET-IMPLEMENTATION.md](../docs/CHALLENGE-WEBSOCKET-IMPLEMENTATION.md)**: WebSocket event handling, real-time synchronization, event types
- **[CHALLENGE-WEBSOCKET-TESTING.md](../docs/CHALLENGE-WEBSOCKET-TESTING.md)**: WebSocket testing methodology and test cases
- **[FLOW_DIAGRAM.md](../docs/FLOW_DIAGRAM.md)**: Game flow diagrams, state transitions, gameplay sequences
- **[DOCS.md](../docs/DOCS.md)**: Technical API documentation, database schema, endpoints
- **[IMPLEMENTATION_SUMMARY.md](../docs/IMPLEMENTATION_SUMMARY.md)**: General implementation patterns and conventions
- **[IMPLEMENTATION_SUMMARY_FOOD_TAX.md](../docs/IMPLEMENTATION_SUMMARY_FOOD_TAX.md)**: Food tax implementation details
- **[TRADING_IMPLEMENTATION_SUMMARY.md](../docs/TRADING_IMPLEMENTATION_SUMMARY.md)**: Trading system implementation guide
- **[TRADING_SYSTEM_TESTING.md](../docs/TRADING_SYSTEM_TESTING.md)**: Trading system test suite and validation

### Troubleshooting & Fixes
- **[DASHBOARD_REFRESH_FIX.md](../docs/DASHBOARD_REFRESH_FIX.md)**: Dashboard refresh issues, WebSocket reconnection fixes
- **[FIX_BANKER_NOT_FOUND.md](../docs/FIX_BANKER_NOT_FOUND.md)**: Banker role detection bug fix

### UI/UX Design
- **[SCOUT_COLORS.md](../docs/SCOUT_COLORS.md)**: Scout-themed color palette, design system guidelines

## When Modifying Code

- **Adding API endpoints**: Follow v2 pattern in `challenge_api.py` (service layer + thin route)
- **New WebSocket events**: Add broadcast method to `ConnectionManager`, update `handleGameEvent()` in dashboard.js
- **Database schema changes**: Update `models.py`, delete `trading_game.db`, restart server
- **Challenge logic changes**: Update both `backend/challenge_manager.py` AND `frontend/challenge-manager.js`
- **UI changes**: Update dashboard.html + increment cache version in script tags

## CLI Tool

Located at project root:
```bash
# Start servers, view logs, manage game
./trading_game_cli.py status
./trading_game_cli.py logs backend
./trading_game_cli.py reset-db

# Registered as trading-game or tg (see pyproject.toml)
trading-game status
tg logs frontend
```
