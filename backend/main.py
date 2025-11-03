"""
The Trading Game - FastAPI Main Application
"""

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List, Dict, Any, Optional
import asyncio

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
from game_constants import NationType
from email_utils import send_registration_email

app = FastAPI(
    title="The Trading Game",
    description="Multiplayer trading game with Game Host, Banker, and Player Groups",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Initialize database on startup"""
    init_db()


@app.get("/")
def read_root():
    """Root endpoint"""
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
        print(f"Failed to send registration email: {str(e)}")
    
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
def auto_assign_groups(
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
    for player in unassigned_players:
        # Find group with fewest members
        min_group = min(group_counts.items(), key=lambda x: x[1])[0]
        player.group_number = min_group
        group_counts[min_group] += 1
        assigned_count += 1
    
    db.commit()
    
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
def start_game(
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
    
    # Initialize nation states for players
    for player in game.players:
        if player.role.value == "player" and player.group_number:
            # Map group number to nation type
            nation_map = {
                1: NationType.NATION_1_FOOD.value,
                2: NationType.NATION_2_RAW.value,
                3: NationType.NATION_3_ELEC.value,
                4: NationType.NATION_4_MED.value
            }
            nation_type = nation_map.get(player.group_number)
            if nation_type:
                player.player_state = GameLogic.initialize_nation(nation_type)
        elif player.role.value == "banker":
            player.player_state = GameLogic.initialize_banker()
    
    game.status = GameStatus.IN_PROGRESS
    db.commit()
    
    return {"message": "Game started", "game_code": game_code.upper()}


@app.post("/games/{game_code}/pause")
def pause_game(
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
    
    return {"message": "Game paused"}


@app.post("/games/{game_code}/end")
def end_game(
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
    
    return {"message": "Game ended", "scores": scores}


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
    """Create a new challenge request"""
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


@app.patch("/games/{game_code}/challenges/{challenge_id}")
def update_challenge(
    game_code: str,
    challenge_id: int,
    status: str = None,
    challenge_type: str = None,
    challenge_description: str = None,
    target_number: int = None,
    db: Session = Depends(get_db)
):
    """Update a challenge (assign, complete, cancel, etc.)"""
    from models import Challenge, ChallengeStatus
    from datetime import datetime
    
    game = db.query(GameSession).filter(GameSession.game_code == game_code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    challenge = db.query(Challenge).filter(
        Challenge.id == challenge_id,
        Challenge.game_session_id == game.id
    ).first()
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    # Update fields
    if status:
        challenge.status = ChallengeStatus(status)
        
        # Set timestamps based on status
        if status == ChallengeStatus.ASSIGNED.value and not challenge.assigned_at:
            challenge.assigned_at = datetime.utcnow()
        elif status == ChallengeStatus.COMPLETED.value and not challenge.completed_at:
            challenge.completed_at = datetime.utcnow()
    
    if challenge_type:
        challenge.challenge_type = challenge_type
    if challenge_description:
        challenge.challenge_description = challenge_description
    if target_number:
        challenge.target_number = target_number
    
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
        "requested_at": challenge.requested_at.isoformat() if challenge.requested_at else None,
        "assigned_at": challenge.assigned_at.isoformat() if challenge.assigned_at else None,
        "completed_at": challenge.completed_at.isoformat() if challenge.completed_at else None
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
