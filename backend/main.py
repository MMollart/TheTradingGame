"""
The Trading Game - FastAPI Main Application
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List

from backend.database import get_db, init_db
from backend.models import User, GameSession, Player, GameConfiguration
from backend.schemas import (
    UserCreate, UserResponse, Token,
    GameConfigCreate, GameConfigResponse,
    GameSessionCreate, GameSessionResponse,
    PlayerJoin, PlayerResponse
)
from backend.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from backend.utils import generate_game_code

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
    """Register a new user account"""
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new game session"""
    game_code = generate_game_code(db)
    
    db_game = GameSession(
        game_code=game_code,
        host_user_id=current_user.id,
        config_id=game.config_id,
        game_state=game.config_data or {}
    )
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    
    # Create host player
    host_player = Player(
        game_session_id=db_game.id,
        player_name=current_user.username,
        role="host",
        is_connected=True
    )
    db.add(host_player)
    db.commit()
    
    return db_game


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


@app.post("/games/join", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
def join_game(player_join: PlayerJoin, db: Session = Depends(get_db)):
    """Join a game session"""
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
    
    # Create player
    new_player = Player(
        game_session_id=game.id,
        player_name=player_join.player_name,
        role=player_join.role,
        group_number=player_join.group_number,
        is_connected=True,
        player_state={}
    )
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    
    return new_player


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
