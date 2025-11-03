# 🎮 The Trading Game

A multiplayer web-based trading simulation game with role-based gameplay.

## Overview

The Trading Game is a real-time multiplayer simulation where players assume different roles to engage in trading activities. The game supports multiple player types with distinct capabilities and interfaces.

## Features

### 🎯 Core Features

- **Unique 6-Digit Game Codes**: Each game session gets a unique, easy-to-share code
- **User Accounts**: Create accounts to save and manage game configurations
- **Role-Based Access**: Three distinct player types with different capabilities
- **Real-Time Updates**: WebSocket support for live game state synchronization
- **Persistent Game State**: Save and resume games

### 👥 Player Roles

1. **Game Host**
   - Full access to all game settings
   - Can start/stop/pause games
   - View all player information
   - Has all capabilities of other roles

2. **Banker**
   - Operates the "World Bank"
   - Manages financial transactions
   - Oversees game economy

3. **Player Groups**
   - Numbered groups (Group 1, Group 2, etc.)
   - Trade with other groups
   - Manage team resources

## Project Structure

```
TheTradingGame/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── models.py        # Database models
│   ├── schemas.py       # Pydantic schemas
│   ├── database.py      # Database configuration
│   ├── auth.py          # Authentication utilities
│   └── utils.py         # Helper functions
├── frontend/
│   └── index.html       # Web interface
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variables template
└── README.md           # This file
```

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: SQLAlchemy with SQLite (PostgreSQL ready)
- **Authentication**: JWT tokens with OAuth2
- **WebSocket**: For real-time updates
- **Validation**: Pydantic

### Frontend
- **HTML5/CSS3/JavaScript**: Pure vanilla JS (no frameworks)
- **Responsive Design**: Mobile-friendly interface

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
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

### Running the Application

#### Quick Start (Recommended)

**Using the convenience scripts:**

```bash
# Restart both servers (kills existing and starts fresh)
./restart-servers.sh

# Stop both servers
./stop-servers.sh
```

The scripts will:
- Start backend at `http://localhost:8000`
- Start frontend at `http://localhost:3000`
- Create log files at `/tmp/trading-game-backend.log` and `/tmp/trading-game-frontend.log`

#### Manual Start

1. **Start the backend server**
   ```bash
   cd backend
   python main.py
   ```
   The API will be available at `http://localhost:8000`

2. **Start the frontend server**
   ```bash
   cd frontend
   python3 -m http.server 3000
   ```
   Then navigate to `http://localhost:3000`

3. **API Documentation**
   FastAPI provides automatic interactive API docs at:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

#### View Logs

```bash
# Backend logs
tail -f /tmp/trading-game-backend.log

# Frontend logs
tail -f /tmp/trading-game-frontend.log
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/token` - Login and get access token
- `GET /auth/me` - Get current user info

### Game Configuration
- `POST /configs` - Create game configuration
- `GET /configs` - List user's configurations
- `GET /configs/{id}` - Get specific configuration

### Game Sessions
- `POST /games` - Create new game session
- `GET /games/{game_code}` - Get game details
- `GET /games/{game_code}/players` - List players
- `POST /games/join` - Join game with code
- `GET /my-games` - List hosted games

## Database Schema

### Users
- User accounts with authentication
- Linked to game configurations and hosted games

### Game Configurations
- Saved game templates
- Customizable rules and settings
- Owned by users

### Game Sessions
- Active games with unique 6-digit codes
- Current game state
- Status tracking (waiting/in_progress/paused/completed)

### Players
- Connected players in game sessions
- Role assignments (host/banker/player)
- Group numbers for player groups
- Individual player state

### Game Events
- Audit log of game actions
- Trade history
- Transaction records

## Development

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
# If using Alembic for migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## Usage Flow

### Creating a Game
1. Register/login to your account
2. (Optional) Create a game configuration
3. Click "Create New Game"
4. Share the 6-digit game code with players

### Joining a Game
1. Get the game code from the host
2. Enter code and your name
3. Select your role (Player Group or Banker)
4. Join and wait for host to start

### Playing the Game
- **Host**: Control game flow, view all information
- **Banker**: Process transactions, manage economy
- **Players**: Trade resources, collaborate within groups

## Configuration

Key settings in `.env`:

```env
DATABASE_URL=sqlite:///./trading_game.db
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

## Security Notes

- Change `SECRET_KEY` in production
- Use HTTPS in production
- Update CORS settings for specific domains
- Use PostgreSQL or MySQL for production (not SQLite)
- Implement rate limiting for API endpoints

## Roadmap

- [ ] Implement game rules and mechanics
- [ ] Add WebSocket for real-time updates
- [ ] Create role-specific dashboards
- [ ] Add game analytics and statistics
- [ ] Implement chat functionality
- [ ] Add game replay feature
- [ ] Mobile app version

## Contributing

Please attach the game rules document to implement specific trading mechanics and gameplay logic.

## License

[Add your license here]

## Contact

[Add your contact information]
