"""
Database models for The Trading Game
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class PlayerRole(str, enum.Enum):
    """Player roles in the game"""
    HOST = "host"
    BANKER = "banker"
    PLAYER = "player"


class GameStatus(str, enum.Enum):
    """Game session status"""
    WAITING = "waiting"  # Waiting for players to join
    IN_PROGRESS = "in_progress"  # Game is active
    PAUSED = "paused"  # Game is paused
    COMPLETED = "completed"  # Game has ended


class User(Base):
    """User accounts for saving game configurations"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    hosted_games = relationship("GameSession", back_populates="host_user")
    game_configs = relationship("GameConfiguration", back_populates="owner")


class GameConfiguration(Base):
    """Saved game configurations (templates)"""
    __tablename__ = "game_configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    config_data = Column(JSON, nullable=False)  # Store game rules, starting resources, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="game_configs")


class GameSession(Base):
    """Active game sessions"""
    __tablename__ = "game_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    game_code = Column(String(6), unique=True, index=True, nullable=False)  # 6-digit code
    host_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    config_id = Column(Integer, ForeignKey("game_configurations.id"), nullable=True)
    
    status = Column(Enum(GameStatus), default=GameStatus.WAITING)
    game_state = Column(JSON)  # Store current game state
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    
    # Relationships
    host_user = relationship("User", back_populates="hosted_games")
    config = relationship("GameConfiguration")
    players = relationship("Player", back_populates="game_session", cascade="all, delete-orphan")


class Player(Base):
    """Players in a game session"""
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, index=True)
    game_session_id = Column(Integer, ForeignKey("game_sessions.id"), nullable=False)
    
    # Player identity
    player_name = Column(String(100), nullable=False)
    role = Column(Enum(PlayerRole), nullable=False)
    
    # For player groups - maps to nation types (1-4)
    # Nation 1 = Food, Nation 2 = Raw Materials, Nation 3 = Electrical, Nation 4 = Medical
    group_number = Column(Integer, nullable=True)
    
    # Player state (stores resources, buildings, etc. for nations)
    # For banker: stores bank prices and inventory
    # Format: {
    #   "resources": {"food": 30, "currency": 50, ...},
    #   "buildings": {"farm": 3, "mine": 1, ...},
    #   "optional_buildings": {"hospital": 2, "restaurant": 1, ...}
    # }
    is_connected = Column(Boolean, default=False)
    player_state = Column(JSON)
    
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    game_session = relationship("GameSession", back_populates="players")


class GameEvent(Base):
    """Log of game events (trades, transactions, etc.)"""
    __tablename__ = "game_events"
    
    id = Column(Integer, primary_key=True, index=True)
    game_session_id = Column(Integer, ForeignKey("game_sessions.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    
    event_type = Column(String(50), nullable=False)  # trade, bank_transaction, etc.
    event_data = Column(JSON, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    game_session = relationship("GameSession")
    player = relationship("Player")
