"""
The Trading Game - FastAPI Main Application
"""

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, attributes
from sqlalchemy.orm.attributes import flag_modified
from datetime import timedelta, datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import asyncio
import logging
from pathlib import Path

from database import get_db, init_db
from models import User, GameSession, Player, GameConfiguration, GameStatus
from schemas import (
    UserCreate, UserResponse, Token,
    GameConfigCreate, GameConfigResponse,
    GameSessionCreate, GameSessionResponse,
    PlayerJoin, PlayerResponse
)
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, get_current_user_optional, ACCESS_TOKEN_EXPIRE_MINUTES
)
from utils import generate_game_code
from websocket_manager import manager
from game_logic import GameLogic
from game_constants import (
    NationType, BuildingType, BUILDING_COSTS, 
    MAX_HOSPITALS, MAX_RESTAURANTS, MAX_INFRASTRUCTURE
)
from email_utils import send_registration_email
from challenge_api import router as challenge_router_v2
from trading_api import router as trading_router_v2
from pricing_manager import PricingManager

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI(
    title="The Trading Game",
    description="Multiplayer trading game with Game Host, Banker, and Player Groups",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tg.pegasusesu.org.uk",
        "http://localhost:5173",  # For local development
    ],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (frontend)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
def on_startup():
    """Initialize database on startup"""
    init_db()


# Include v2 Challenge API routes
app.include_router(challenge_router_v2)

# Include v2 Trading API routes
app.include_router(trading_router_v2)


@app.get("/")
def read_root():
    """Serve the frontend index.html"""
    index_file = Path(__file__).parent / "static" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "The Trading Game API",
        "version": "0.1.0",
        "docs": "/docs"
    }

@app.get("/api")
def api_root():
    """API root endpoint"""
    return {
        "message": "The Trading Game API",
        "version": "0.1.0",
        "docs": "/docs"
    }


# ==================== Authentication Endpoints ====================

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account and send welcome email"""
    # Check if username exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Send welcome email (non-blocking - don't fail registration if email fails)
    try:
        send_registration_email(user.username, user.email)
    except Exception as e:
        logger.warning(f"Failed to send registration email: {str(e)}")
    
    return db_user


@app.post("/auth/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and get access token"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


# ==================== Game Configuration Endpoints ====================

@app.post("/configs", response_model=GameConfigResponse, status_code=status.HTTP_201_CREATED)
def create_game_config(
    config: GameConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new game configuration"""
    db_config = GameConfiguration(
        owner_id=current_user.id,
        name=config.name,
        description=config.description,
        config_data=config.config_data
    )
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    return db_config


@app.get("/configs", response_model=List[GameConfigResponse])
def list_game_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all game configurations for current user"""
    configs = db.query(GameConfiguration).filter(
        GameConfiguration.owner_id == current_user.id
    ).all()
    return configs


@app.get("/configs/{config_id}", response_model=GameConfigResponse)
def get_game_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific game configuration"""
    config = db.query(GameConfiguration).filter(
        GameConfiguration.id == config_id,
        GameConfiguration.owner_id == current_user.id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config


# ==================== Game Session Endpoints ====================

@app.post("/games", response_model=GameSessionResponse, status_code=status.HTTP_201_CREATED)
def create_game_session(
    game: GameSessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new game session (no authentication required for quick start)"""
    game_code = generate_game_code(db)
    
    db_game = GameSession(
        game_code=game_code,
        host_user_id=None,  # Allow creating without user account
        config_id=game.config_id,
        game_state=game.config_data or {},
        num_teams=None  # Host must set this before players can join
    )
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    
    # Note: Host player will be created when they join the game
    # This allows for simpler flow without authentication
    
    return db_game


@app.post("/games/{game_code}/set-teams")
def set_number_of_teams(
    game_code: str,
    num_teams: int,
    db: Session = Depends(get_db)
):
    """
    Set the number of teams for a game.
    Must be called by host before players can join.
    """
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if num_teams < 1 or num_teams > 20:
        raise HTTPException(status_code=400, detail="Number of teams must be between 1 and 20")
    
    game.num_teams = num_teams
    db.commit()
    db.refresh(game)
    
    return {
        "success": True,
        "message": f"Game configured for {num_teams} teams",
        "num_teams": num_teams
    }


@app.post("/games/{game_code}/set-duration")
def set_game_duration(
    game_code: str,
    duration_minutes: int,
    db: Session = Depends(get_db)
):
    """
    Set the game duration in minutes.
    Duration must be in 30-minute intervals from 60 to 240 minutes (1-4 hours).
    Valid values: 60, 90, 120, 150, 180, 210, 240
    """
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Validate duration is in 30-minute intervals between 1-4 hours
    valid_durations = [60, 90, 120, 150, 180, 210, 240]
    if duration_minutes not in valid_durations:
        raise HTTPException(
            status_code=400, 
            detail=f"Duration must be one of {valid_durations} minutes (1-4 hours in 30-minute intervals)"
        )
    
    game.game_duration_minutes = duration_minutes
    db.commit()
    db.refresh(game)
    
    hours = duration_minutes // 60
    remaining_mins = duration_minutes % 60
    duration_str = f"{hours} hour{'s' if hours != 1 else ''}"
    if remaining_mins:
        duration_str += f" {remaining_mins} minutes"
    
    return {
        "success": True,
        "message": f"Game duration set to {duration_str}",
        "game_duration_minutes": duration_minutes
    }


@app.post("/games/{game_code}/teams/{team_number}/set-name")
async def set_team_name(
    game_code: str,
    team_number: int,
    name: str,
    db: Session = Depends(get_db)
):
    """
    Set or update the name for a specific team.
    """
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Validate team number
    if game.num_teams and (team_number < 1 or team_number > game.num_teams):
        raise HTTPException(
            status_code=400, 
            detail=f"Team number must be between 1 and {game.num_teams}"
        )
    
    # Initialize game_state if needed
    if not game.game_state:
        game.game_state = {}
    
    if "teams" not in game.game_state:
        game.game_state["teams"] = {}
    
    # Update or create team configuration
    team_key = str(team_number)
    if team_key not in game.game_state["teams"]:
        game.game_state["teams"][team_key] = {
            "nation_type": f"nation_{((team_number - 1) % 4) + 1}",  # Default nation type
            "nation_name": name
        }
    else:
        game.game_state["teams"][team_key]["nation_name"] = name
    
    # Mark the column as modified for SQLAlchemy to detect the JSON change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(game, "game_state")
    
    db.commit()
    db.refresh(game)
    
    # Broadcast team name change to all players via WebSocket
    await manager.broadcast_to_game(
        game_code.upper(),
        {
            "type": "team_name_changed",
            "team_number": team_number,
            "team_name": name
        }
    )
    
    return {
        "success": True,
        "message": f"Team {team_number} renamed to '{name}'",
        "team_number": team_number,
        "team_name": name,
        "team_config": game.game_state["teams"][team_key]
    }


@app.get("/games/{game_code}", response_model=GameSessionResponse)
def get_game_session(game_code: str, db: Session = Depends(get_db)):
    """Get game session by game code"""
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@app.get("/games/{game_code}/players", response_model=List[PlayerResponse])
def list_game_players(game_code: str, db: Session = Depends(get_db)):
    """List all players in a game"""
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game.players


@app.get("/games/{game_code}/unassigned-players")
def list_unassigned_players(game_code: str, db: Session = Depends(get_db)):
    """List all players who haven't been assigned to a team yet"""
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    unassigned = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.role == "player",
        Player.group_number == None
    ).all()
    
    return {
        "unassigned_count": len(unassigned),
        "players": [{"id": p.id, "name": p.player_name, "joined_at": p.joined_at} for p in unassigned]
    }


@app.post("/games/{game_code}/create-fake-players")
def create_fake_players(
    game_code: str,
    num_players: int = 5,
    db: Session = Depends(get_db)
):
    """
    TEST MODE: Create fake players for testing team assignment.
    Creates unassigned players with generated names.
    """
    import random
    
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if num_players < 1 or num_players > 50:
        raise HTTPException(status_code=400, detail="Number of fake players must be between 1 and 50")
    
    # Fun fake player names
    first_names = [
        "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn",
        "Skylar", "Dakota", "River", "Sage", "Phoenix", "Cameron", "Emerson", "Parker",
        "Rowan", "Blake", "Charlie", "Drew", "Finley", "Harper", "Hayden", "Kendall"
    ]
    
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White"
    ]
    
    created_players = []
    
    for i in range(num_players):
        # Generate a unique fake name
        attempts = 0
        while attempts < 10:
            first = random.choice(first_names)
            last = random.choice(last_names)
            player_name = f"{first} {last}"
            
            # Check if name already exists
            existing = db.query(Player).filter(
                Player.game_session_id == game.id,
                Player.player_name == player_name
            ).first()
            
            if not existing:
                break
            attempts += 1
        else:
            # If we couldn't find a unique name, add a number
            player_name = f"{first} {last} #{i+1}"
        
        # Create the fake player
        fake_player = Player(
            game_session_id=game.id,
            player_name=player_name,
            role="player",
            group_number=None,  # Unassigned
            is_approved=True,  # Auto-approve fake players
            is_connected=False,  # Not actually connected
            player_state={}
        )
        db.add(fake_player)
        created_players.append(player_name)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Created {num_players} fake players",
        "created_count": num_players,
        "player_names": created_players
    }


@app.post("/api/join")
async def join_game(
    player_join: PlayerJoin,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Join a game session. 
    - Authenticated users join immediately with is_approved=True
    - Guest users need host approval with is_approved=False
    - All users join as 'player' role initially, host assigns roles later
    """
    
    game = db.query(GameSession).filter(
        GameSession.game_code == player_join.game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Check if player name already exists in this game
    existing_player = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.player_name == player_join.player_name
    ).first()
    
    if existing_player:
        raise HTTPException(status_code=400, detail="Player name already taken in this game")
    
    # Determine if user is authenticated and should be auto-approved
    is_authenticated = current_user is not None
    user_id = current_user.id if current_user else None
    
    # Auto-approve if: authenticated OR joining as host/banker
    is_approved = is_authenticated or player_join.role in ['host', 'banker']
    
    # Create player without group assignment
    # Authenticated users, hosts, and bankers auto-approved; regular players need host approval
    new_player = Player(
        game_session_id=game.id,
        user_id=user_id,
        player_name=player_join.player_name,
        role=player_join.role,
        group_number=None,  # No group assigned yet
        is_approved=is_approved,  # Auto-approve hosts, bankers, and authenticated users
        is_connected=True,
        player_state={}
    )
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    
    # Broadcast player joined to all connected players
    await manager.broadcast_to_game(
        game.game_code,
        {
            "type": "player_joined",
            "player_id": new_player.id,
            "player_name": new_player.player_name,
            "role": new_player.role,
            "is_approved": new_player.is_approved
        }
    )
    
    # Add needs_approval flag for client
    response = PlayerResponse.model_validate(new_player)
    response.needs_approval = not is_authenticated
    
    return response


@app.put("/games/{game_code}/players/{player_id}/assign-role")
async def assign_player_role(
    game_code: str,
    player_id: int,
    role: str,
    db: Session = Depends(get_db)
):
    """Assign a role to a player (host dashboard action)"""
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    player = db.query(Player).filter(
        Player.id == player_id,
        Player.game_session_id == game.id
    ).first()
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if role not in ["player", "banker", "host"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    player.role = role
    
    # If promoting to banker or host, remove them from any team
    if role in ["banker", "host"]:
        player.group_number = None
    
    db.commit()
    db.flush()
    db.refresh(player)
    
    # Notify player via WebSocket that their role has changed
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "player_role_changed",
        "player_id": player.id,
        "player_name": player.player_name,
        "new_role": role
    })
    
    return {"success": True, "player": player}


@app.put("/games/{game_code}/players/{player_id}/approve")
async def approve_player(
    game_code: str,
    player_id: int,
    db: Session = Depends(get_db)
):
    """Approve a pending player (host dashboard action)"""
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    player = db.query(Player).filter(
        Player.id == player_id,
        Player.game_session_id == game.id
    ).first()
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player.is_approved = True
    db.commit()
    db.flush()  # Ensure commit is fully written to database
    db.refresh(player)
    
    # Small delay to ensure database transaction completes
    await asyncio.sleep(0.1)
    
    # Notify player via WebSocket that they've been approved
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "player_approved",
        "player_id": player.id,
        "player_name": player.player_name
    })
    
    return {"success": True, "player": player}


@app.get("/games/{game_code}/pending-players")
def list_pending_players(game_code: str, db: Session = Depends(get_db)):
    """List all players waiting for host approval"""
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    pending = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.is_approved == False
    ).all()
    
    return {
        "pending_count": len(pending),
        "players": [{"id": p.id, "name": p.player_name, "joined_at": p.joined_at, "role": p.role.value} for p in pending]
    }


@app.put("/games/{game_code}/players/{player_id}/assign-group")
async def assign_player_group(
    game_code: str,
    player_id: int,
    group_number: int,
    db: Session = Depends(get_db)
):
    """Manually assign a player to a group (host dashboard action)"""
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    player = db.query(Player).filter(
        Player.id == player_id,
        Player.game_session_id == game.id
    ).first()
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    if player.role.value != "player":
        raise HTTPException(status_code=400, detail="Can only assign groups to players, not hosts or bankers")
    
    if group_number < 1 or group_number > 4:
        raise HTTPException(status_code=400, detail="Group number must be between 1 and 4")
    
    player.group_number = group_number
    db.commit()
    db.flush()
    db.refresh(player)
    
    # Notify player via WebSocket that they've been assigned to a team
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "player_assigned_team",
        "player_id": player.id,
        "player_name": player.player_name,
        "team_number": group_number
    })
    
    return {"success": True, "player": player}


@app.delete("/games/{game_code}/players/{player_id}/unassign-group")
async def unassign_player_group(
    game_code: str,
    player_id: int,
    db: Session = Depends(get_db)
):
    """Remove a player from their assigned group"""
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    player = db.query(Player).filter(
        Player.id == player_id,
        Player.game_session_id == game.id
    ).first()
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player.group_number = None
    db.commit()
    db.refresh(player)
    
    # Broadcast WebSocket event to the player who was unassigned
    await manager.broadcast_to_game(
        game_code.upper(),
        {
            "type": "player_unassigned_team",
            "player_id": player.id,
            "player_name": player.player_name
        }
    )
    
    return {"success": True, "player": player}


@app.delete("/games/{game_code}/players/{player_id}")
def remove_player_from_game(
    game_code: str,
    player_id: int,
    db: Session = Depends(get_db)
):
    """Remove a player from the game entirely (host action)"""
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    player = db.query(Player).filter(
        Player.id == player_id,
        Player.game_session_id == game.id
    ).first()
    
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Don't allow removing the host
    if player.role.value == "host":
        raise HTTPException(status_code=400, detail="Cannot remove the host from the game")
    
    player_name = player.player_name
    db.delete(player)
    db.commit()
    
    return {"success": True, "message": f"Player {player_name} removed from game"}


@app.delete("/games/{game_code}/players")
async def clear_all_players(
    game_code: str,
    db: Session = Depends(get_db)
):
    """Remove all non-host players from the game (host action to clear lobby)"""
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Get list of players to be removed (for notification)
    players_to_remove = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.role != "host"
    ).all()
    
    # Delete all players except the host
    deleted_count = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.role != "host"
    ).delete()
    
    db.commit()
    
    # Notify all players that lobby has been cleared
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "lobby_cleared",
        "message": "The host has closed the lobby. You have been removed from the game."
    })
    
    return {"success": True, "message": f"Cleared {deleted_count} players from lobby", "deleted_count": deleted_count}


@app.delete("/games/{game_code}")
async def delete_game(
    game_code: str,
    db: Session = Depends(get_db)
):
    """
    Delete a game and all associated data (players, challenges, etc.)
    This prevents the game code from being reused.
    Player names can be reused in different games.
    """
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Get player count before deletion
    player_count = db.query(Player).filter(Player.game_session_id == game.id).count()
    
    # Notify all connected players that the game is being deleted
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "game_deleted",
        "message": "This game has been deleted by the host."
    })
    
    # SQLAlchemy will cascade delete players and challenges due to relationship configuration
    # But we'll be explicit for clarity
    
    # Delete all players
    db.query(Player).filter(Player.game_session_id == game.id).delete()
    
    # Delete the game session
    db.delete(game)
    db.commit()
    
    return {
        "success": True, 
        "message": f"Game {game_code.upper()} deleted successfully",
        "deleted_players": player_count
    }


@app.post("/games/{game_code}/auto-assign-groups")
async def auto_assign_groups(
    game_code: str,
    num_teams: int = 4,
    db: Session = Depends(get_db)
):
    """
    Automatically assign unassigned players to teams evenly.
    Nation types are randomly assigned and can be duplicated across teams.
    
    Args:
        game_code: The game code
        num_teams: Number of teams to create (default 4)
    """
    import random
    
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if num_teams < 1 or num_teams > 20:
        raise HTTPException(status_code=400, detail="Number of teams must be between 1 and 20")
    
    # Get all players without group assignments
    unassigned_players = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.role == "player",
        Player.group_number == None
    ).all()
    
    if not unassigned_players:
        return {"success": True, "message": "No unassigned players found", "assigned_count": 0}
    
    # Get current group counts
    group_counts = {i: 0 for i in range(1, num_teams + 1)}
    assigned_players = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.role == "player",
        Player.group_number != None
    ).all()
    
    for player in assigned_players:
        if player.group_number and player.group_number <= num_teams:
            group_counts[player.group_number] = group_counts.get(player.group_number, 0) + 1
    
    # Assign players to groups with fewest members
    assigned_count = 0
    assigned_players_list = []
    for player in unassigned_players:
        # Find group with fewest members
        min_group = min(group_counts.items(), key=lambda x: x[1])[0]
        player.group_number = min_group
        group_counts[min_group] += 1
        assigned_count += 1
        assigned_players_list.append({
            'player_id': player.id,
            'player_name': player.player_name,
            'team_number': min_group
        })
    
    db.commit()
    
    # Broadcast WebSocket events for each assigned player
    logger.info(f"[auto_assign_groups] Broadcasting {len(assigned_players_list)} team assignments")
    for assignment in assigned_players_list:
        logger.debug(f"[auto_assign_groups] Broadcasting: player_id={assignment['player_id']}, team={assignment['team_number']}")
        await manager.broadcast_to_game(
            game_code.upper(),
            {
                "type": "player_assigned_team",
                "player_id": assignment['player_id'],
                "player_name": assignment['player_name'],
                "team_number": assignment['team_number']
            }
        )
        logger.debug(f"[auto_assign_groups] Broadcast complete for player {assignment['player_id']}")
    
    # Initialize game state with team configurations if not exists
    if not game.game_state:
        game.game_state = {}
    
    if "teams" not in game.game_state:
        game.game_state["teams"] = {}
    
    # Assign nation types ensuring all 4 types are used before repeating
    nation_types = ["nation_1", "nation_2", "nation_3", "nation_4"]
    
    # Create a shuffled pool that repeats nation types only after all are used
    nation_pool = []
    full_cycles = num_teams // len(nation_types)
    remaining = num_teams % len(nation_types)
    
    # Add complete cycles of all nation types
    for _ in range(full_cycles):
        shuffled = nation_types.copy()
        random.shuffle(shuffled)
        nation_pool.extend(shuffled)
    
    # Add remaining nations (less than a full cycle)
    if remaining > 0:
        shuffled = nation_types.copy()
        random.shuffle(shuffled)
        nation_pool.extend(shuffled[:remaining])
    
    # Assign nation types to teams
    for team_num in range(1, num_teams + 1):
        if str(team_num) not in game.game_state["teams"]:
            game.game_state["teams"][str(team_num)] = {
                "nation_type": nation_pool[team_num - 1],
                "nation_name": f"Team {team_num}"
            }
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Assigned {assigned_count} players to {num_teams} teams",
        "assigned_count": assigned_count,
        "num_teams": num_teams,
        "group_distribution": group_counts,
        "team_configurations": game.game_state["teams"]
    }


@app.get("/my-games", response_model=List[GameSessionResponse])
def list_my_games(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all games hosted by current user"""
    games = db.query(GameSession).filter(
        GameSession.host_user_id == current_user.id
    ).all()
    return games


# ==================== WebSocket Endpoint ====================

@app.websocket("/ws/{game_code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_code: str, player_id: int, db: Session = Depends(get_db)):
    """WebSocket endpoint for real-time game updates"""
    # Verify game exists
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        await websocket.close(code=1008)
        return
    
    # Verify player exists
    player = db.query(Player).filter(Player.id == player_id, Player.game_session_id == game.id).first()
    if not player:
        await websocket.close(code=1008)
        return
    
    # Connect player
    await manager.connect(websocket, game_code.upper(), player_id, player.role.value)
    
    try:
        # Send initial game state
        await websocket.send_json({
            "type": "game_state",
            "state": game.game_state or {},
            "status": game.status.value,
            "players": [
                {
                    "id": p.id,
                    "name": p.player_name,
                    "role": p.role.value,
                    "group_number": p.group_number,
                    "is_connected": p.is_connected
                }
                for p in game.players
            ]
        })
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "update_state":
                # Update game state
                game.game_state = data.get("state")
                db.commit()
                
                # Broadcast to all players
                await manager.broadcast_to_game(game_code.upper(), {
                    "type": "state_updated",
                    "state": game.game_state
                })
            
            elif data.get("type") == "update_player_state":
                # Update player state
                player.player_state = data.get("player_state")
                db.commit()
                
                # Broadcast player update
                await manager.broadcast_to_game(game_code.upper(), {
                    "type": "player_state_updated",
                    "player_id": player_id,
                    "player_state": player.player_state
                })
            
            elif data.get("type") == "trade_request":
                # Handle trade request
                await manager.broadcast_to_game(game_code.upper(), {
                    "type": "trade_request",
                    "from_player": player_id,
                    "to_player": data.get("to_player"),
                    "offer": data.get("offer")
                })
            
            elif data.get("type") == "event":
                # Broadcast game event (disasters, taxes, etc.)
                await manager.broadcast_to_game(game_code.upper(), {
                    "type": "game_event",
                    "event_type": data.get("event_type"),
                    "data": data.get("data")
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # Update player connection status
        player.is_connected = False
        db.commit()


# ==================== Game Action Endpoints ====================

@app.post("/games/{game_code}/start")
async def start_game(
    game_code: str,
    db: Session = Depends(get_db)
):
    """Start a game session (works for both authenticated and anonymous games)"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game.status != GameStatus.WAITING:
        raise HTTPException(status_code=400, detail="Game already started")
    
    # Initialize TEAM-LEVEL resources and buildings in game_state
    if not game.game_state:
        game.game_state = {}
    
    if 'teams' not in game.game_state:
        game.game_state['teams'] = {}
    
    # Get all unique team numbers
    team_numbers = set(p.group_number for p in game.players if p.role.value == "player" and p.group_number)
    
    # Initialize each team with nation-specific starting resources
    # Dynamically get all available nation types from the enum
    nation_types = [nation_type.value for nation_type in NationType]
    num_nation_types = len(nation_types)
    
    for team_number in team_numbers:
        # Cycle through nation types using modulo (team 5+ get same types as 1-4, etc.)
        nation_index = (team_number - 1) % num_nation_types
        nation_type = nation_types[nation_index]
        
        # Initialize team state with nation-specific resources
        team_state = GameLogic.initialize_nation(nation_type)
        game.game_state['teams'][str(team_number)] = {
            'resources': team_state['resources'],
            'buildings': team_state['buildings'],
            'name': team_state['name'],  # Store nation name for dynamic frontend display
            'nation_type': team_state['nation_type']  # Store nation type identifier
        }
    
    # Mark game_state as modified so SQLAlchemy knows to persist the changes
    flag_modified(game, 'game_state')
    
    # Initialize banker state (if needed for banker role)
    # Bank gets 150 of each resource per team
    num_teams = len(team_numbers)
    for player in game.players:
        if player.role.value == "banker":
            player.player_state = GameLogic.initialize_banker(num_teams=num_teams)
            flag_modified(player, 'player_state')
    
    # Initialize dynamic pricing in game_state (works without banker role)
    pricing_mgr = PricingManager(db)
    prices = pricing_mgr.initialize_bank_prices(game_code)
    game.game_state['bank_prices'] = prices
    flag_modified(game, 'game_state')
    
    game.status = GameStatus.IN_PROGRESS
    game.started_at = datetime.utcnow()
    db.commit()
    
    # Broadcast game status change to all players
    await manager.broadcast_to_game(
        game_code.upper(),
        {
            "type": "game_status_changed",
            "status": "in_progress",
            "message": "Game has started!",
            "started_at": game.started_at.isoformat(),
            "game_duration_minutes": game.game_duration_minutes or 120
        }
    )
    
    return {"message": "Game started", "game_code": game_code.upper()}


@app.post("/games/{game_code}/pause")
async def pause_game(
    game_code: str,
    db: Session = Depends(get_db)
):
    """Pause a game session (works for both authenticated and anonymous games)"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game.status = GameStatus.PAUSED
    db.commit()
    
    # Broadcast game status change to all players
    await manager.broadcast_to_game(
        game_code.upper(),
        {
            "type": "game_status_changed",
            "status": "paused",
            "message": "Game has been paused"
        }
    )
    
    return {"message": "Game paused"}


@app.post("/games/{game_code}/resume")
async def resume_game(
    game_code: str,
    db: Session = Depends(get_db)
):
    """Resume a paused game session"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    if game.status != GameStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Game is not paused")
    
    game.status = GameStatus.IN_PROGRESS
    db.commit()
    
    # Broadcast game status change to all players
    await manager.broadcast_to_game(
        game_code.upper(),
        {
            "type": "game_status_changed",
            "status": "in_progress",
            "message": "Game has been resumed"
        }
    )
    
    return {"message": "Game resumed"}


@app.post("/games/{game_code}/end")
async def end_game(
    game_code: str,
    db: Session = Depends(get_db)
):
    """End a game session and calculate scores (works for both authenticated and anonymous games)"""
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Calculate scores for each nation
    scores = {}
    banker_state = None
    
    # Find banker to get bank prices
    for player in game.players:
        if player.role.value == "banker":
            banker_state = player.player_state
            break
    
    bank_prices = banker_state.get("bank_prices", {}) if banker_state else {}
    
    for player in game.players:
        if player.role.value == "player" and player.player_state:
            score = GameLogic.calculate_score(player.player_state, bank_prices)
            scores[player.id] = {
                "player_name": player.player_name,
                "nation": player.player_state.get("name"),
                "score": score
            }
    
    game.status = GameStatus.COMPLETED
    game.game_state = {"final_scores": scores}
    db.commit()
    
    # Broadcast game status change to all players
    await manager.broadcast_to_game(
        game_code.upper(),
        {
            "type": "game_status_changed",
            "status": "completed",
            "message": "Game has ended!",
            "scores": scores
        }
    )
    
    return {"message": "Game ended", "scores": scores}


# ==================== MANUAL RESOURCE/BUILDING MANAGEMENT (HOST ONLY) ====================

class ManualResourceRequest(BaseModel):
    team_number: int
    resource_type: str
    amount: int

class ManualBuildingRequest(BaseModel):
    team_number: int
    building_type: str
    quantity: int

class BuildBuildingRequest(BaseModel):
    team_number: int
    building_type: str

@app.post("/games/{game_code}/manual-resources")
async def give_manual_resources(
    game_code: str,
    request: ManualResourceRequest,
    db: Session = Depends(get_db)
):
    """Manually give resources to a team (host only)"""
    team_number = request.team_number
    resource_type = request.resource_type
    amount = request.amount
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Validate inputs
    if team_number not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="Invalid team number (must be 1-4)")
    
    valid_resources = ['currency', 'food', 'raw_materials', 'electrical_goods', 'medical_goods']
    if resource_type not in valid_resources:
        raise HTTPException(status_code=400, detail=f"Invalid resource type. Must be one of: {valid_resources}")
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    # Initialize game_state.teams if needed
    if not game.game_state:
        game.game_state = {}
    if 'teams' not in game.game_state:
        game.game_state['teams'] = {}
    if str(team_number) not in game.game_state['teams']:
        game.game_state['teams'][str(team_number)] = {'resources': {}, 'buildings': {}}
    
    # Add resources to team
    team_state = game.game_state['teams'][str(team_number)]
    if 'resources' not in team_state:
        team_state['resources'] = {}
    
    current_amount = team_state['resources'].get(resource_type, 0)
    team_state['resources'][resource_type] = current_amount + amount
    
    # Mark as modified for SQLAlchemy
    flag_modified(game, 'game_state')
    db.commit()
    
    # Broadcast state update to all players so dashboards refresh
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "state_updated",
        "state": game.game_state
    })
    
    return {
        "message": f"Successfully gave {amount} {resource_type} to Team {team_number}",
        "team_number": team_number,
        "resource_type": resource_type,
        "new_amount": team_state['resources'][resource_type]
    }


@app.post("/games/{game_code}/manual-buildings")
async def give_manual_buildings(
    game_code: str,
    request: ManualBuildingRequest,
    db: Session = Depends(get_db)
):
    """Manually give buildings to a team (host only)"""
    team_number = request.team_number
    building_type = request.building_type
    quantity = request.quantity
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Validate inputs
    if team_number not in [1, 2, 3, 4]:
        raise HTTPException(status_code=400, detail="Invalid team number (must be 1-4)")
    
    valid_buildings = ['farm', 'mine', 'electrical_factory', 'medical_factory', 'school', 'hospital', 'restaurant', 'infrastructure']
    if building_type not in valid_buildings:
        raise HTTPException(status_code=400, detail=f"Invalid building type. Must be one of: {valid_buildings}")
    
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
    
    # Initialize game_state.teams if needed
    if not game.game_state:
        game.game_state = {}
    if 'teams' not in game.game_state:
        game.game_state['teams'] = {}
    if str(team_number) not in game.game_state['teams']:
        game.game_state['teams'][str(team_number)] = {'resources': {}, 'buildings': {}}
    
    # Add buildings to team
    team_state = game.game_state['teams'][str(team_number)]
    if 'buildings' not in team_state:
        team_state['buildings'] = {}
    
    current_count = team_state['buildings'].get(building_type, 0)
    team_state['buildings'][building_type] = current_count + quantity
    
    # Mark as modified for SQLAlchemy
    flag_modified(game, 'game_state')
    db.commit()
    
    # Broadcast state update to all players so dashboards refresh
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "state_updated",
        "state": game.game_state
    })
    
    return {
        "message": f"Successfully gave {quantity} {building_type}(s) to Team {team_number}",
        "team_number": team_number,
        "building_type": building_type,
        "new_count": team_state['buildings'][building_type]
    }


@app.post("/games/{game_code}/build-building")
async def build_building(
    game_code: str,
    request: BuildBuildingRequest,
    db: Session = Depends(get_db)
):
    """
    Build a new building by spending resources.
    Players can build production buildings (farm, mine, etc.) or optional buildings.
    """
    team_number = request.team_number
    building_type = request.building_type
    
    game = db.query(GameSession).filter(
        GameSession.game_code == game_code.upper()
    ).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Validate building type
    try:
        building = BuildingType(building_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid building type: {building_type}")
    
    # Get building cost
    if building not in BUILDING_COSTS:
        raise HTTPException(status_code=400, detail=f"No cost defined for building: {building_type}")
    
    cost = BUILDING_COSTS[building]
    
    # Initialize game_state.teams if needed
    if not game.game_state:
        game.game_state = {}
    if 'teams' not in game.game_state:
        game.game_state['teams'] = {}
    if str(team_number) not in game.game_state['teams']:
        game.game_state['teams'][str(team_number)] = {'resources': {}, 'buildings': {}}
    
    team_state = game.game_state['teams'][str(team_number)]
    
    # Initialize resources and buildings if needed
    if 'resources' not in team_state:
        team_state['resources'] = {}
    if 'buildings' not in team_state:
        team_state['buildings'] = {}
    
    # Check optional building limits
    if building in [BuildingType.HOSPITAL, BuildingType.RESTAURANT, BuildingType.INFRASTRUCTURE]:
        current_count = team_state['buildings'].get(building_type, 0)
        max_count = {
            BuildingType.HOSPITAL: MAX_HOSPITALS,
            BuildingType.RESTAURANT: MAX_RESTAURANTS,
            BuildingType.INFRASTRUCTURE: MAX_INFRASTRUCTURE
        }.get(building, 5)
        
        if current_count >= max_count:
            raise HTTPException(
                status_code=400, 
                detail=f"Maximum {building_type} limit reached ({max_count})"
            )
    
    # Check if team can afford the building
    missing_resources = []
    for resource, amount in cost.items():
        resource_key = resource.value if hasattr(resource, 'value') else resource
        current_amount = team_state['resources'].get(resource_key, 0)
        if current_amount < amount:
            missing_resources.append(f"{resource_key}: need {amount}, have {current_amount}")
    
    if missing_resources:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient resources: {', '.join(missing_resources)}"
        )
    
    # Deduct resources
    for resource, amount in cost.items():
        resource_key = resource.value if hasattr(resource, 'value') else resource
        team_state['resources'][resource_key] = team_state['resources'].get(resource_key, 0) - amount
    
    # Add building
    team_state['buildings'][building_type] = team_state['buildings'].get(building_type, 0) + 1
    
    # Mark as modified for SQLAlchemy
    flag_modified(game, 'game_state')
    db.commit()
    
    # Broadcast building constructed event
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "event",
        "event_type": "building_constructed",
        "data": {
            "team_number": team_number,
            "building_type": building_type,
            "new_count": team_state['buildings'][building_type],
            "resources": team_state['resources']
        }
    })
    
    return {
        "success": True,
        "message": f"Successfully built {building_type} for Team {team_number}",
        "team_number": team_number,
        "building_type": building_type,
        "new_count": team_state['buildings'][building_type],
        "remaining_resources": team_state['resources']
    }


@app.post("/games/{game_code}/challenges/{challenge_id}/complete")
async def complete_challenge_with_bank_transfer(
    game_code: str,
    challenge_id: int,
    request_body: dict,
    db: Session = Depends(get_db)
):
    """Complete a challenge and transfer resources from bank to team"""
    from models import Challenge, ChallengeStatus
    from datetime import datetime
    
    team_number = request_body.get('team_number')
    resource_type = request_body.get('resource_type')
    amount = request_body.get('amount')
    
    logger.debug(f"[complete_challenge] game_code={game_code}, challenge_id={challenge_id}")
    logger.debug(f"[complete_challenge] team_number={team_number}, resource_type={resource_type}, amount={amount}")
    
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Get banker or host (host can manage bank if no banker exists)
    bank_manager = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.role == "banker"
    ).first()
    
    if not bank_manager:
        # If no banker, use host as bank manager
        bank_manager = db.query(Player).filter(
            Player.game_session_id == game.id,
            Player.role == "host"
        ).first()
    
    if not bank_manager:
        raise HTTPException(status_code=404, detail="No banker or host found to manage bank inventory")
    
    logger.debug(f"[complete_challenge] Bank manager ({bank_manager.role}) found: {bank_manager.id}, player_state type: {type(bank_manager.player_state)}")
    
    # Check bank inventory
    if not bank_manager.player_state:
        bank_manager.player_state = {}
    
    # Initialize bank inventory if it doesn't exist (for hosts managing bank)
    if 'bank_inventory' not in bank_manager.player_state:
        banker_state = GameLogic.initialize_banker()
        bank_manager.player_state['bank_inventory'] = banker_state['bank_inventory']
        flag_modified(bank_manager, 'player_state')
    
    bank_inventory = bank_manager.player_state.get('bank_inventory', {})
    current_inventory = bank_inventory.get(resource_type, 0)
    
    logger.debug(f"[complete_challenge] BEFORE - Bank inventory: {bank_inventory}")
    logger.debug(f"[complete_challenge] Current {resource_type}: {current_inventory}, Requested: {amount}")
    
    if current_inventory < amount:
        raise HTTPException(
            status_code=400,
            detail=f"Bank does not have enough {resource_type}. Required: {amount}, Available: {int(current_inventory)}"
        )
    
    # Deduct from bank inventory (bank_inventory is guaranteed to exist at this point)
    bank_manager.player_state['bank_inventory'][resource_type] = current_inventory - amount
    flag_modified(bank_manager, 'player_state')
    
    logger.debug(f"[complete_challenge] AFTER - Bank inventory: {bank_manager.player_state['bank_inventory']}")
    logger.debug(f"[complete_challenge] New {resource_type}: {bank_manager.player_state['bank_inventory'][resource_type]}")
    
    # Add to team resources
    team_key = str(team_number)
    if not game.game_state:
        game.game_state = {}
    if 'teams' not in game.game_state:
        game.game_state['teams'] = {}
    if team_key not in game.game_state['teams']:
        game.game_state['teams'][team_key] = {'resources': {}, 'buildings': {}}
    
    team_state = game.game_state['teams'][team_key]
    if 'resources' not in team_state:
        team_state['resources'] = {}
    
    current_team_amount = team_state['resources'].get(resource_type, 0)
    team_state['resources'][resource_type] = current_team_amount + amount
    flag_modified(game, 'game_state')
    
    # Mark challenge as completed
    challenge = db.query(Challenge).filter(
        Challenge.id == challenge_id,
        Challenge.game_session_id == game.id
    ).first()
    
    if challenge:
        challenge.status = ChallengeStatus.COMPLETED  # type: ignore
        challenge.completed_at = datetime.utcnow()  # type: ignore
    
    db.commit()
    
    # Broadcast state update to all players so dashboards refresh
    await manager.broadcast_to_game(game_code.upper(), {
        "type": "state_updated",
        "state": game.game_state
    })
    
    return {
        "success": True,
        "message": f"Transferred {amount} {resource_type} from bank to Team {team_number}",
        "bank_remaining": int(bank_manager.player_state['bank_inventory'][resource_type]),
        "team_total": int(team_state['resources'][resource_type])
    }


# ==================== CHALLENGE ENDPOINTS ====================

@app.post("/games/{game_code}/challenges")
def create_challenge(
    game_code: str,
    player_id: int,
    building_type: str,
    building_name: str,
    team_number: int,
    has_school: bool,
    db: Session = Depends(get_db)
):
    """Create a new challenge request with bank inventory check"""
    from models import Challenge, ChallengeStatus
    
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Check if player already has an active challenge
    existing = db.query(Challenge).filter(
        Challenge.game_session_id == game.id,
        Challenge.player_id == player_id,
        Challenge.status.in_([ChallengeStatus.REQUESTED, ChallengeStatus.ASSIGNED])
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Player already has an active challenge")
    
    # Get team's building count to calculate required resources
    team_key = str(team_number)
    team_data = game.game_state.get('teams', {}).get(team_key, {})
    building_count = team_data.get('buildings', {}).get(building_type, 0)
    
    # Map building types to resources and calculate required amount
    production_grants = {
        'farm': {'resource': 'food', 'amount': 5},
        'mine': {'resource': 'raw_materials', 'amount': 5},
        'electrical_factory': {'resource': 'electrical_goods', 'amount': 5},
        'medical_factory': {'resource': 'medical_goods', 'amount': 5}
    }
    
    grant_info = production_grants.get(building_type)
    if not grant_info:
        raise HTTPException(status_code=400, detail="Invalid building type")
    
    required_resource = grant_info['resource']
    base_amount = grant_info['amount']
    # Use normal difficulty (1.0x) for calculation - actual difficulty applied at completion
    required_amount = base_amount * building_count * 1.0
    
    # Check bank inventory (check banker first, then host)
    bank_manager = db.query(Player).filter(
        Player.game_session_id == game.id,
        Player.role == "banker"
    ).first()
    
    if not bank_manager:
        bank_manager = db.query(Player).filter(
            Player.game_session_id == game.id,
            Player.role == "host"
        ).first()
    
    if bank_manager and bank_manager.player_state:
        bank_inventory = bank_manager.player_state.get('bank_inventory', {})
        current_inventory = bank_inventory.get(required_resource, 0)
        
        if current_inventory < required_amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Bank does not have enough {required_resource}. Required: {int(required_amount)}, Available: {int(current_inventory)}"
            )
    
    challenge = Challenge(
        game_session_id=game.id,
        player_id=player_id,
        building_type=building_type,
        building_name=building_name,
        team_number=team_number,
        has_school=has_school,
        status=ChallengeStatus.REQUESTED
    )
    
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    
    return {
        "id": challenge.id,
        "player_id": challenge.player_id,
        "building_type": challenge.building_type,
        "building_name": challenge.building_name,
        "team_number": challenge.team_number,
        "has_school": challenge.has_school,
        "status": challenge.status.value,
        "requested_at": challenge.requested_at.isoformat()
    }


@app.get("/games/{game_code}/challenges")
def get_challenges(
    game_code: str,
    status: str = None,
    db: Session = Depends(get_db)
):
    """Get all challenges for a game, optionally filtered by status"""
    from models import Challenge, ChallengeStatus
    
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    query = db.query(Challenge).filter(Challenge.game_session_id == game.id)
    
    if status:
        query = query.filter(Challenge.status == status)
    
    challenges = query.all()
    
    return [{
        "id": c.id,
        "player_id": c.player_id,
        "building_type": c.building_type,
        "building_name": c.building_name,
        "team_number": c.team_number,
        "has_school": c.has_school,
        "challenge_type": c.challenge_type,
        "challenge_description": c.challenge_description,
        "target_number": c.target_number,
        "status": c.status.value,
        "requested_at": c.requested_at.isoformat() if c.requested_at else None,
        "assigned_at": c.assigned_at.isoformat() if c.assigned_at else None,
        "completed_at": c.completed_at.isoformat() if c.completed_at else None
    } for c in challenges]


@app.get("/api/v2/challenges/{game_code}/active")
def get_active_challenges_v2(
    game_code: str,
    db: Session = Depends(get_db)
):
    """V2 endpoint: Get active challenges (requested or assigned status) for a game"""
    from models import Challenge, ChallengeStatus
    
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Get challenges that are requested or assigned (not completed/cancelled)
    challenges = db.query(Challenge).filter(
        Challenge.game_session_id == game.id,
        Challenge.status.in_([ChallengeStatus.REQUESTED, ChallengeStatus.ASSIGNED])
    ).all()
    
    return [{
        "id": c.id,
        "player_id": c.player_id,
        "building_type": c.building_type,
        "building_name": c.building_name,
        "team_number": c.team_number,
        "has_school": c.has_school,
        "challenge_type": c.challenge_type,
        "challenge_description": c.challenge_description,
        "target_number": c.target_number,
        "status": c.status.value,
        "requested_at": c.requested_at.isoformat() if c.requested_at else None,
        "assigned_at": c.assigned_at.isoformat() if c.assigned_at else None,
        "completed_at": c.completed_at.isoformat() if c.completed_at else None
    } for c in challenges]


@app.patch("/games/{game_code}/challenges/{challenge_id}")
async def update_challenge(
    game_code: str,
    challenge_id: int,
    update_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Update a challenge (assign, complete, cancel, etc.)"""
    from models import Challenge, ChallengeStatus
    from datetime import datetime
    
    # Extract fields from update_data
    status = update_data.get('status')
    challenge_type = update_data.get('challenge_type')
    challenge_description = update_data.get('challenge_description')
    target_number = update_data.get('target_number')
    
    logger.debug(f"[update_challenge] game_code: {game_code}, challenge_id: {challenge_id}")
    logger.debug(f"[update_challenge] Received update_data: {update_data}")
    logger.debug(f"[update_challenge] status: {status}, type: {type(status)}")
    
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        logger.warning(f"[update_challenge] Game not found: {game_code.upper()}")
        raise HTTPException(status_code=404, detail="Game not found")
    
    logger.debug(f"[update_challenge] Game found, ID: {game.id}")
    
    challenge = db.query(Challenge).filter(
        Challenge.id == challenge_id,
        Challenge.game_session_id == game.id
    ).first()
    
    if not challenge:
        logger.warning(f"[update_challenge] Challenge not found - ID: {challenge_id}, game_session_id: {game.id}")
        # Log all challenges for this game to debug
        all_challenges = db.query(Challenge).filter(Challenge.game_session_id == game.id).all()
        logger.debug(f"[update_challenge] Available challenges for this game: {[(c.id, c.player_id, c.building_type) for c in all_challenges]}")
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    logger.debug(f"[update_challenge] Challenge found: ID {challenge.id}, player_id: {challenge.player_id}, building: {challenge.building_type}")
    
    # Update fields
    if status:
        challenge.status = ChallengeStatus(status)  # type: ignore
        
        # Set timestamps based on status
        if status == ChallengeStatus.ASSIGNED.value and not challenge.assigned_at:  # type: ignore
            challenge.assigned_at = datetime.utcnow()  # type: ignore
        elif status == ChallengeStatus.COMPLETED.value and not challenge.completed_at:  # type: ignore
            challenge.completed_at = datetime.utcnow()  # type: ignore
    
    if challenge_type:
        challenge.challenge_type = challenge_type  # type: ignore
    if challenge_description:
        challenge.challenge_description = challenge_description  # type: ignore
    if target_number:
        challenge.target_number = target_number  # type: ignore
    
    db.commit()
    db.refresh(challenge)
    
    return {
        "id": challenge.id,
        "player_id": challenge.player_id,
        "building_type": challenge.building_type,
        "building_name": challenge.building_name,
        "team_number": challenge.team_number,
        "has_school": challenge.has_school,
        "challenge_type": challenge.challenge_type,
        "challenge_description": challenge.challenge_description,
        "target_number": challenge.target_number,
        "status": challenge.status.value,
        "requested_at": challenge.requested_at.isoformat() if challenge.requested_at else None,  # type: ignore
        "assigned_at": challenge.assigned_at.isoformat() if challenge.assigned_at else None,  # type: ignore
        "completed_at": challenge.completed_at.isoformat() if challenge.completed_at else None  # type: ignore
    }


@app.post("/games/{game_code}/challenges/adjust-for-pause")
async def adjust_challenge_times_for_pause(
    game_code: str,
    request_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Adjust assigned_at timestamps for all active challenges to account for pause duration.
    This extends the challenge deadline by the pause duration.
    """
    from models import Challenge, ChallengeStatus
    from datetime import datetime, timedelta
    
    pause_duration_ms = request_data.get('pause_duration_ms')
    if pause_duration_ms is None:
        raise HTTPException(status_code=422, detail="pause_duration_ms is required")
    
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Get all active (assigned) challenges for this game
    active_challenges = db.query(Challenge).filter(
        Challenge.game_session_id == game.id,
        Challenge.status == ChallengeStatus.ASSIGNED,
        Challenge.assigned_at.isnot(None)
    ).all()
    
    if not active_challenges:
        return {
            "success": True,
            "message": "No active challenges to adjust",
            "adjusted_count": 0
        }
    
    # Convert milliseconds to timedelta
    pause_duration = timedelta(milliseconds=int(pause_duration_ms))
    
    adjusted_count = 0
    for challenge in active_challenges:
        # Add the pause duration to the assigned_at time
        # This effectively extends the deadline
        new_assigned_at = challenge.assigned_at + pause_duration  # type: ignore
        challenge.assigned_at = new_assigned_at  # type: ignore
        adjusted_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Adjusted {adjusted_count} challenge(s) for pause duration",
        "adjusted_count": adjusted_count,
        "pause_duration_ms": pause_duration_ms
    }


@app.delete("/games/{game_code}/challenges/{challenge_id}")
def delete_challenge(
    game_code: str,
    challenge_id: int,
    db: Session = Depends(get_db)
):
    """Delete a challenge (for cleanup)"""
    from models import Challenge
    
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    challenge = db.query(Challenge).filter(
        Challenge.id == challenge_id,
        Challenge.game_session_id == game.id
    ).first()
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    db.delete(challenge)
    db.commit()
    
    return {"message": "Challenge deleted"}


# ==================== Static File Serving (Catch-All - Must Be Last) ====================

@app.get("/{filename:path}")
def serve_static_files(filename: str):
    """Serve static files (JS, CSS, HTML) from root path for backwards compatibility"""
    # Only serve files with common static extensions
    if filename.endswith(('.js', '.css', '.html', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico')):
        static_dir = (Path(__file__).parent / "static").resolve()
        file_path = (static_dir / filename).resolve()
        # Prevent path traversal: ensure file_path is within static_dir
        if file_path.is_file() and file_path.is_relative_to(static_dir):
            return FileResponse(str(file_path))
    # If not a static file or doesn't exist, return 404
    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
