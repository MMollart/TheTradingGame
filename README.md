# 🎮 The Trading Game

A real-time multiplayer resource trading and building simulation game with physical challenges, role-based gameplay, and WebSocket synchronization.

## Overview

The Trading Game is an interactive multiplayer experience where teams compete to build infrastructure and produce resources. Players must complete physical challenges (push-ups, burpees, etc.) to earn production rights, trade resources with other teams, and strategically build their nation's economy. The game features real-time updates via WebSockets, pause-aware challenge timing, and comprehensive host/banker oversight tools.

## ✨ Features

### 🎯 Core Gameplay

- **Resource Management**: Four resource types (Food, Raw Materials, Electrical Goods, Medical Goods) plus currency
- **Building System**: Eight building types (Farm, Mine, Electrical Factory, Medical Factory, School, Hospital, Restaurant, Infrastructure) with production bonuses
- **Physical Challenges**: Players complete real-world exercises (push-ups, burpees, planks, sit-ups, squats, lunges, star jumps, jumping jacks) to earn production rights
- **Challenge Request System**: Banker/Host assigns custom challenges with configurable targets and types
- **Trading System**: Teams trade resources with each other and the World Bank
- **Automated Food Tax**: Configurable automated taxation system with banker controls and penalty mechanics
- **Game Difficulty Modes**: Three difficulty levels (Easy: +25% resources, Medium: baseline, Hard: -25% resources) affecting starting resources only
- **Pause-Aware Timing**: Challenge timers freeze during game pauses, extending deadlines fairly
- **Challenge Locking**: School buildings enable simultaneous challenges for team members
- **External Integrations**: OAuth2 framework for OnlineScoutManager API integration

### 🎮 Game Management

- **Unique 6-Digit Game Codes**: Easy-to-share game codes for quick joining
- **Configurable Duration**: Set game length from 1-4 hours in 30-minute intervals (60, 90, 120, 150, 180, 210, 240 minutes)
- **Difficulty Settings**: Choose from Easy, Medium, or Hard difficulty modes with resource modifiers
- **Real-Time Synchronization**: WebSocket updates for all players instantly across all connected clients
- **Game Controls**: Start, pause, resume, and end games with proper state management
- **Guest Approval System**: Host approves players before they join the game
- **Drag-and-Drop Team Assignment**: Visual interface for organizing players into teams (1-4 nations)
- **Food Tax Automation**: Scheduled automated food tax collection with configurable rates and banker controls

### 👥 Player Roles

1. **Game Host**
   - Full administrative control over game settings
   - Start/pause/resume/end game functionality
   - Assign players to teams via drag-and-drop
   - Approve or reject guest players
   - Assign challenges to players
   - View all game statistics and player states
   - Manage trading transactions

2. **Banker (World Bank Operator)**
   - Manages the World Bank inventory and prices
   - Assigns physical challenges to players
   - Processes trading requests
   - Views all active challenges
   - Monitors game economy
   - Controls food tax automation (enable/disable, adjust rates)
   - Same challenge assignment powers as host

3. **Players (Team Members)**
   - Organized into teams (1-4 nations)
   - Build infrastructure for their nation
   - Request and complete physical challenges
   - Produce resources using buildings
   - Trade with other teams and the bank
   - Collaborate with teammates
   - View team resources and buildings

## 📁 Project Structure

```
TheTradingGame/
├── backend/
│   ├── main.py                  # FastAPI application & API endpoints
│   ├── models.py                # SQLAlchemy database models
│   ├── schemas.py               # Pydantic validation schemas
│   ├── database.py              # Database configuration
│   ├── auth.py                  # JWT authentication
│   ├── challenge_manager.py     # Challenge business logic
│   ├── challenge_api.py         # Challenge API endpoints (v2)
│   ├── food_tax_api.py          # Food tax automation API
│   ├── food_tax_scheduler.py    # Automated tax scheduling
│   ├── websocket_manager.py     # WebSocket connection management
│   ├── game_logic.py            # Game rules and mechanics
│   ├── game_constants.py        # Building types, resources, difficulty
│   ├── utils.py                 # Helper functions
│   └── tests/                   # Pytest test suite (90+ tests)
│       ├── conftest.py
│       ├── test_authentication.py
│       ├── test_challenge_manager.py
│       ├── test_challenge_locking.py
│       ├── test_game_duration.py
│       ├── test_game_management.py
│       ├── test_player_management.py
│       └── test_team_assignment.py
├── backend/
│   ├── static/                  # Frontend files (HTML, JS, CSS)
│   │   ├── index.html           # Landing page
│   │   ├── dashboard.html       # Main game interface
│   │   ├── game-settings.html   # Game configuration
│   │   ├── dashboard-styles.css # Game interface styles
│   │   ├── game-api.js          # API client wrapper
│   │   ├── dashboard.js         # Main game logic
│   │   ├── challenge-manager.js # Frontend challenge state management
│   │   ├── food-tax-manager.js  # Food tax frontend logic
│   │   └── trading-manager.js   # Trading system frontend
│   ├── requirements.txt         # Production dependencies
│   └── requirements-test.txt    # Test dependencies
├── .env.example                 # Environment template
├── restart-servers.sh           # Dev server management
├── stop-servers.sh              # Stop all servers
└── README.md                    # This file
```

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI 0.104+ (Python 3.8+)
- **Database**: SQLAlchemy with SQLite (production-ready for PostgreSQL/MySQL)
- **Authentication**: JWT tokens with OAuth2 password flow
- **WebSocket**: Starlette WebSocket with custom connection manager
- **Validation**: Pydantic v2 models
- **Testing**: Pytest with 90+ tests (comprehensive coverage)
- **Async Support**: Full async/await throughout challenge and food tax systems
- **Scheduling**: APScheduler for automated game events (food tax collection)

### Frontend
- **Pure Vanilla JavaScript**: No frameworks, lightweight and fast
- **HTML5/CSS3**: Modern responsive design
- **WebSocket Client**: Custom event-driven architecture
- **State Management**: Centralized challenge manager with database sync
- **UI Components**: Drag-and-drop, modals, real-time updates

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   cd TheTradingGame
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

### Running the Application

#### Quick Start (Recommended)

```bash
# Start/restart both servers (kills existing processes)
./restart-servers.sh

# Stop all servers
./stop-servers.sh

# View logs in real-time
tail -f /tmp/trading-game-backend.log   # API logs
tail -f /tmp/trading-game-frontend.log  # Frontend logs
```

**URLs:**
- Application: http://localhost:8000 (frontend + backend unified)
- API Docs (Swagger): http://localhost:8000/docs
- API Docs (ReDoc): http://localhost:8000/redoc

#### Manual Start (Development)

**Single Terminal:**
```bash
cd backend
python main.py
```

The backend serves frontend files from `backend/static/` automatically.
Access the app at: http://localhost:8000

#### Running Tests

```bash
# Run all tests
cd backend
pytest -v

# Run specific test file
pytest tests/test_challenge_manager.py -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run tests matching pattern
pytest -k "test_challenge" -v
```

**Test Results:** 90+ tests passing with comprehensive coverage

## 🔌 API Endpoints

### Game Management
- `POST /games` - Create new game with unique code
- `GET /games/{game_code}` - Get game details
- `POST /games/{game_code}/set-duration` - Set game duration (60, 90, 120, 150, 180, 210, 240 minutes)
- `POST /games/{game_code}/set-difficulty` - Set game difficulty (easy, medium, hard)
- `POST /games/{game_code}/start` - Start game
- `POST /games/{game_code}/pause` - Pause game
- `POST /games/{game_code}/resume` - Resume game
- `POST /games/{game_code}/end` - End game

### Player Management
- `POST /api/join` - Join game with code and player name
- `GET /games/{game_code}/players` - List all players
- `GET /games/{game_code}/unassigned-players` - Get players without teams
- `PUT /games/{game_code}/players/{player_id}/approve` - Approve guest player
- `PUT /games/{game_code}/players/{player_id}/assign-group` - Assign player to team
- `PUT /games/{game_code}/players/{player_id}/assign-role` - Change player role
- `DELETE /games/{game_code}/players/{player_id}` - Remove player
- `POST /games/{game_code}/auto-assign-groups` - Auto-assign players to teams

### Challenge System (v2)
- `POST /api/v2/challenges/{game_code}/request` - Player requests challenge
- `POST /api/v2/challenges/{game_code}/{challenge_id}/assign` - Assign challenge with type/target
- `POST /api/v2/challenges/{game_code}/{challenge_id}/complete` - Complete challenge
- `POST /api/v2/challenges/{game_code}/{challenge_id}/cancel` - Cancel challenge
- `POST /api/v2/challenges/{game_code}/adjust-for-pause` - Adjust times after pause
- `GET /api/v2/challenges/{game_code}/active` - Get all active challenges
- `GET /api/v2/challenges/{game_code}/check-lock` - Check if player is locked

### Production & Trading
- `POST /games/{game_code}/produce` - Produce resources
- `POST /games/{game_code}/build` - Build structure
- `POST /games/{game_code}/trade` - Execute trade

### Food Tax System (v2)
- `POST /api/v2/food-tax/{game_code}/enable` - Enable automated food tax
- `POST /api/v2/food-tax/{game_code}/disable` - Disable automated food tax
- `POST /api/v2/food-tax/{game_code}/set-rate` - Set tax rate (percentage)
- `POST /api/v2/food-tax/{game_code}/set-interval` - Set collection interval (minutes)
- `POST /api/v2/food-tax/{game_code}/collect-now` - Manually trigger tax collection
- `GET /api/v2/food-tax/{game_code}/status` - Get current tax configuration and status

### WebSocket
- `WS /ws/{game_code}/{player_id}` - Real-time game events connection

**Full API documentation:** http://localhost:8000/docs

## 📊 Database Schema

### GameSession
- `game_code` (unique 6-digit code)
- `status` (waiting/in_progress/paused/completed)
- `game_duration_minutes` (60-240 in 30-min intervals)
- `difficulty` (easy/medium/hard) - affects starting resources
- `started_at`, `paused_at`, `ended_at` timestamps
- `game_state` (JSON: bank inventory, prices, food tax settings, team states)

### Player
- `player_name`, `role` (host/banker/player)
- `group_number` (1-4 for team assignment)
- `is_approved` (guest approval system)
- `is_connected` (WebSocket status)
- `player_state` (JSON: resources, buildings, inventory)
- Links to `game_session_id`

### Challenge
- `player_id`, `building_type`, `building_name`
- `team_number`, `has_school` (for challenge locking)
- `status` (REQUESTED/ASSIGNED/COMPLETED/CANCELLED/EXPIRED)
- `challenge_type`, `challenge_description`, `target_number`
- `requested_at`, `assigned_at`, `completed_at` timestamps
- Links to `game_session_id`

### GameEvent (Audit Log)
- `event_type`, `event_data` (JSON)
- `timestamp`, `player_id`
- Full history of all game actions

## 🎯 Gameplay Flow

### 1. Game Setup (Host)
1. Create game → receives unique 6-digit code
2. Configure game settings:
   - Game duration (1-4 hours in 30-minute intervals)
   - Difficulty level (Easy: +25% resources, Medium: baseline, Hard: -25% resources)
3. Share game code with players
4. Approve joining players (guest approval)
5. Assign players to teams via drag-and-drop (1-4 nations)
6. Start game

### 2. Resource Production (Players)
1. Player clicks "Request Challenge" for a building
2. Request appears in Banker/Host's dashboard
3. Banker assigns challenge type (push-ups, burpees, etc.) with target number
4. Player receives challenge (e.g., "20 Push-ups")
5. Player performs physical challenge
6. Player clicks "Complete Challenge"
7. Resources are produced based on building multipliers
8. Challenge expires after 10 minutes of active game time

### 3. Trading (All Players)
1. View available resources and prices
2. Initiate trade with another team or the bank
3. Trade is processed if both parties have resources
4. Resources update in real-time via WebSocket

### 4. Building (Players)
1. Spend resources to construct buildings
2. Buildings provide production multipliers
3. School buildings enable simultaneous challenges for teammates
4. Strategic building placement affects team economy

### 5. Game Control (Host/Banker)
- **Pause**: Freezes all challenge timers, extends deadlines, pauses food tax collection
- **Resume**: Adjusts all active challenge deadlines by pause duration, resumes tax collection
- **End**: Finalizes game, shows statistics
- **Food Tax Control** (Banker): Enable/disable automated tax, adjust rate and collection interval

## 🧪 Challenge System Details

### Challenge Types & Defaults
- **Push-ups**: 20 reps
- **Sit-ups**: 30 reps
- **Burpees**: 15 reps
- **Star Jumps**: 25 reps
- **Squats**: 20 reps
- **Lunges**: 20 reps (10 per leg)
- **Plank**: 60 seconds
- **Jumping Jacks**: 30 reps

### Challenge Locking Rules
**Without School:**
- One challenge per player at a time
- Same team cannot have multiple simultaneous challenges

**With School:**
- Multiple team members can have simultaneous challenges
- Each player still limited to one challenge at a time
- Enables faster team production

### Pause-Aware Timing
- Challenges valid for exactly 10 minutes of *active* gameplay
- When paused: timers freeze on frontend
- When resumed: all `assigned_at` timestamps adjust by pause duration
- Players always get full 10 minutes to complete challenges

**Example:**
```
Challenge assigned: 10:00 AM
Game paused: 10:03 AM (3 min elapsed, 7 min remaining)
Pause duration: 12 minutes
Game resumed: 10:15 AM
New deadline: 10:22 AM (original 10:10 + 12 min pause)
Result: Player still has 7 minutes remaining
```

## 🔧 Development

### Project Setup
```bash
# Clone and setup
git clone <repository>
cd TheTradingGame

# Install Python dependencies
pip install -r backend/requirements.txt
pip install -r backend/requirements-test.txt  # For testing

# Configure environment
cp backend/.env.example backend/.env
# Edit .env with your settings (SECRET_KEY, etc.)

# Start development servers
./restart-servers.sh
```

### Testing
```bash
cd backend

# Run all tests (82 tests)
pytest -v

# Run with coverage report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Run specific test categories
pytest tests/test_challenge_manager.py -v    # Challenge system
pytest tests/test_authentication.py -v       # Auth & roles
pytest tests/test_game_duration.py -v        # Game settings

# Run tests matching keyword
pytest -k "challenge" -v
```

### Code Quality
```bash
# Format code
black backend/

# Lint
flake8 backend/ --max-line-length=120

# Type checking (if using mypy)
mypy backend/

# Run specific test suites
pytest tests/test_food_tax.py -v              # Food tax system
pytest tests/test_game_difficulty.py -v       # Difficulty system
```

### Database Management
```bash
# Reset database (dev only)
rm backend/trading_game.db
./restart-servers.sh  # Will recreate database

# Inspect database
sqlite3 backend/trading_game.db
.tables
.schema game_sessions
SELECT * FROM challenges;
```

### Debugging
```bash
# View real-time logs
tail -f /tmp/trading-game-backend.log

# Check for errors
grep -i error /tmp/trading-game-backend.log

# Check active processes
ps aux | grep -E "(python main.py|http.server 3000)"

# Kill stuck processes
pkill -f "python main.py"
pkill -f "http.server 3000"
```

## ⚙️ Configuration

### Environment Variables (`.env`)
```env
# Database
DATABASE_URL=sqlite:///./trading_game.db

# Security
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server
DEBUG=True
HOST=0.0.0.0
PORT=8000

# CORS (update for production)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Game Constants (`backend/game_constants.py`)
- Resource types and initial quantities per nation type
- Building types, costs, and production multipliers
- Challenge duration (10 minutes)
- Challenge types with default targets
- Difficulty modifiers (Easy: 1.25x, Medium: 1.0x, Hard: 0.75x)
- Trading rules and bank pricing
- Food tax default settings (rate, interval, penalty multipliers)

## 🔒 Security Notes

### Production Deployment Checklist
- [ ] Change `SECRET_KEY` to a secure random string
- [ ] Enable HTTPS/TLS
- [ ] Update CORS `ALLOWED_ORIGINS` to your domain
- [ ] Use PostgreSQL/MySQL instead of SQLite
- [ ] Implement rate limiting on API endpoints
- [ ] Add request logging and monitoring
- [ ] Enable CSRF protection for state-changing operations
- [ ] Use secure WebSocket (wss://)
- [ ] Implement proper session management
- [ ] Add input sanitization for player names

## 🚀 Deployment

### Production Database
```python
# Update DATABASE_URL in .env
DATABASE_URL=postgresql://user:password@localhost/trading_game
# or
DATABASE_URL=mysql://user:password@localhost/trading_game
```

### Dockerization (Optional)
```dockerfile
# Example Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./backend/
RUN pip install -r backend/requirements.txt
COPY backend/ ./backend/
CMD ["python", "backend/main.py"]
```

## 🗺️ Roadmap & Future Features

### Completed ✅
- [x] Challenge request/assignment system
- [x] Pause-aware challenge timing
- [x] Challenge locking with school buildings
- [x] Configurable game duration (1-4 hours in 30-min intervals)
- [x] Game difficulty modes (Easy/Medium/Hard with resource modifiers)
- [x] Automated food tax system with banker controls
- [x] Real-time WebSocket synchronization
- [x] Multi-user support (host + banker)
- [x] Guest approval system
- [x] Drag-and-drop team assignment
- [x] Comprehensive test suite (90+ tests)
- [x] Four nation types with distinct starting resources
- [x] Eight building types with production multipliers

### In Progress 🚧
- [ ] Trading system UI improvements
- [ ] Advanced game statistics dashboard
- [ ] Game event audit log UI
- [ ] Food tax penalty escalation system

### Planned 📋
- [ ] Challenge history and analytics
- [ ] Leaderboard and team rankings
- [ ] In-game chat system
- [ ] Game replay feature
- [ ] Mobile-responsive UI improvements
- [ ] Admin dashboard for multi-game management
- [ ] Challenge photo/video verification
- [ ] Custom challenge templates
- [ ] Tournament mode
- [ ] Achievement system

## 📝 Documentation

- **[README.md](README.md)**: This file - complete project overview
- **[Documentation Index](docs/README.md)**: Complete documentation catalog with 20+ technical documents
- **[PLAYER_INSTRUCTIONS_QUICK.md](docs/PLAYER_INSTRUCTIONS_QUICK.md)**: 📄 **2-page quick player guide - print this for your game sessions!**
- **[PLAYER_INSTRUCTIONS.md](docs/PLAYER_INSTRUCTIONS.md)**: 📋 Complete player guide (detailed, 15-20 pages)

### Quick Access to Key Documentation:
- **[PLAYER_INSTRUCTIONS_QUICK.md](docs/PLAYER_INSTRUCTIONS_QUICK.md)**: 2-page quick reference for players (BEST for printing!)
- **[PLAYER_INSTRUCTIONS.md](docs/PLAYER_INSTRUCTIONS.md)**: Comprehensive gameplay guide for players (detailed reference)
- **[QUICKSTART.md](docs/QUICKSTART.md)**: Server management and development workflow
- **[CHALLENGE_SYSTEM_README.md](docs/CHALLENGE_SYSTEM_README.md)**: Challenge architecture and API reference
- **[FEATURE-GAME-DURATION.md](docs/FEATURE-GAME-DURATION.md)**: Configurable game duration feature
- **[FEATURE-FOOD-TAX-AUTOMATION.md](docs/FEATURE-FOOD-TAX-AUTOMATION.md)**: Automated food tax system
- **[FOOD-TAX-QUICKSTART.md](docs/FOOD-TAX-QUICKSTART.md)**: Quick guide to food tax feature
- **[TRADING_FEATURE_README.md](docs/TRADING_FEATURE_README.md)**: Resource trading system
- **[BUILDING-CONSTRUCTION-SYSTEM.md](docs/BUILDING-CONSTRUCTION-SYSTEM.md)**: Building mechanics
- **[CHALLENGE-WEBSOCKET-IMPLEMENTATION.md](docs/CHALLENGE-WEBSOCKET-IMPLEMENTATION.md)**: WebSocket events
- **[OSM_OAUTH_SETUP.md](docs/OSM_OAUTH_SETUP.md)**: OAuth2 integration guide
- **API Docs**: http://localhost:8000/docs (interactive Swagger UI)

## 🐛 Troubleshooting

### Port Already in Use
```bash
lsof -ti:8000 | xargs kill -9  # Kill server
./restart-servers.sh
```

### Database Locked
```bash
# Close all connections to database
pkill -f "python main.py"
rm backend/trading_game.db  # WARNING: Deletes all data
./restart-servers.sh
```

### WebSocket Not Connecting
- Check browser console for errors
- Verify game code and player ID are correct
- Ensure backend server is running
- Check firewall settings

### Challenges Not Syncing
- Call `challengeManager.loadFromServer()` to force refresh
- Check WebSocket connection status
- Verify challenge exists in database
- Review backend logs for errors

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 👤 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/MMollart/TheTradingGame/issues)
- **Discussions**: [GitHub Discussions](https://github.com/MMollart/TheTradingGame/discussions)

---

**Built with ❤️ using FastAPI, WebSockets, and Vanilla JavaScript**
