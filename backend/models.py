"""
Database models for The Trading Game
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text, JSON
from sqlalchemy.orm import declarative_base, relationship
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
    hashed_password = Column(String(255), nullable=True)  # Nullable for OSM OAuth users
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
    host_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Allow anonymous game creation
    config_id = Column(Integer, ForeignKey("game_configurations.id"), nullable=True)
    
    status = Column(Enum(GameStatus), default=GameStatus.WAITING)
    game_state = Column(JSON)  # Store current game state
    num_teams = Column(Integer, nullable=True)  # Number of teams configured by host
    game_duration_minutes = Column(Integer, nullable=True)  # Game duration in minutes (60, 90, 120, 150, 180, 210, 240)
    difficulty = Column(String(10), default="medium", nullable=False)  # Game difficulty: easy, medium, hard
    scenario_id = Column(String(50), nullable=True)  # Historical scenario identifier (e.g., 'marshall_plan')
    
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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Link to authenticated user
    
    # Player identity
    player_name = Column(String(100), nullable=False)
    role = Column(Enum(PlayerRole), nullable=False)
    
    # For player groups - maps to nation types (1-4)
    # Nation 1 = Food, Nation 2 = Raw Materials, Nation 3 = Electrical, Nation 4 = Medical
    group_number = Column(Integer, nullable=True)
    
    # Approval system for guest users
    is_approved = Column(Boolean, default=False)  # Requires host approval if not authenticated
    
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


class ChallengeStatus(str, enum.Enum):
    """Challenge lifecycle status"""
    REQUESTED = "requested"  # Challenge requested, awaiting assignment
    ASSIGNED = "assigned"    # Challenge assigned and active
    COMPLETED = "completed"  # Challenge completed successfully
    CANCELLED = "cancelled"  # Challenge cancelled by host/banker
    DISMISSED = "dismissed"  # Challenge request dismissed
    EXPIRED = "expired"      # Challenge expired (10 min timeout)


class Challenge(Base):
    """Active production challenges"""
    __tablename__ = "challenges"
    
    id = Column(Integer, primary_key=True, index=True)
    game_session_id = Column(Integer, ForeignKey("game_sessions.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    
    # Challenge details
    building_type = Column(String(50), nullable=False)  # farm, mine, electrical_factory, medical_factory
    building_name = Column(String(100), nullable=False)  # Formatted name with emoji
    team_number = Column(Integer, nullable=False)
    has_school = Column(Boolean, default=False)  # Whether team has a school (individual vs team-wide lock)
    
    # Challenge assignment details
    challenge_type = Column(String(50), nullable=True)  # push_ups, sit_ups, etc.
    challenge_description = Column(String(200), nullable=True)  # "20 Push-ups"
    target_number = Column(Integer, nullable=True)
    
    # Lifecycle
    status = Column(Enum(ChallengeStatus), default=ChallengeStatus.REQUESTED, nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    game_session = relationship("GameSession")
    player = relationship("Player")


class TradeOfferStatus(str, enum.Enum):
    """Trade offer status between teams"""
    PENDING = "pending"          # Initial offer, awaiting response
    COUNTER_OFFERED = "counter_offered"  # Counter-offer made
    ACCEPTED = "accepted"        # Trade accepted and completed
    REJECTED = "rejected"        # Trade rejected
    CANCELLED = "cancelled"      # Cancelled by initiator


class TradeOffer(Base):
    """Team-to-team trade offers"""
    __tablename__ = "trade_offers"
    
    id = Column(Integer, primary_key=True, index=True)
    game_session_id = Column(Integer, ForeignKey("game_sessions.id"), nullable=False)
    
    # Parties involved
    from_team_number = Column(Integer, nullable=False)
    to_team_number = Column(Integer, nullable=False)
    initiated_by_player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    
    # Trade details - what initiator offers
    offered_resources = Column(JSON, nullable=False)  # {"food": 10, "currency": 50}
    # Trade details - what initiator requests
    requested_resources = Column(JSON, nullable=False)  # {"raw_materials": 20}
    
    # Counter offer (if any)
    counter_offered_resources = Column(JSON, nullable=True)
    counter_requested_resources = Column(JSON, nullable=True)
    counter_offered_by_player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    counter_offered_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(Enum(TradeOfferStatus), default=TradeOfferStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    game_session = relationship("GameSession")
    initiated_by = relationship("Player", foreign_keys=[initiated_by_player_id])
    counter_offered_by = relationship("Player", foreign_keys=[counter_offered_by_player_id])


class PriceHistory(Base):
    """Track bank prices over time for charting"""
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    game_session_id = Column(Integer, ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False)
    
    # Price snapshot
    resource_type = Column(String(50), nullable=False)  # food, raw_materials, etc.
    buy_price = Column(Integer, nullable=False)  # Price bank sells at (higher)
    sell_price = Column(Integer, nullable=False)  # Price bank buys at (lower)
    baseline_price = Column(Integer, nullable=False)  # Original fixed price
    
    # Context
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    triggered_by_trade = Column(Boolean, default=False)  # Was this update caused by a trade?
    
    # Relationships
    game_session = relationship("GameSession")


class OAuthProvider(str, enum.Enum):
    """OAuth provider types"""
    OSM = "osm"  # OnlineScoutManager


class OAuthToken(Base):
    """Store OAuth tokens for external integrations"""
    __tablename__ = "oauth_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(Enum(OAuthProvider), nullable=False)
    
    # OAuth tokens
    access_token = Column(Text, nullable=False)  # Encrypted in production
    refresh_token = Column(Text, nullable=True)
    token_type = Column(String(50), default="Bearer")
    expires_at = Column(DateTime, nullable=True)  # When access_token expires
    
    # OAuth metadata
    scope = Column(String(500), nullable=True)  # Space-separated scopes
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="oauth_tokens")
