"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from models import PlayerRole, GameStatus


# User schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


# Game Configuration schemas
class GameConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    config_data: Dict[str, Any]


class GameConfigResponse(BaseModel):
    id: int
    owner_id: int
    name: str
    description: Optional[str]
    config_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Game Session schemas
class GameSessionCreate(BaseModel):
    config_id: Optional[int] = None
    config_data: Optional[Dict[str, Any]] = None


class GameSessionResponse(BaseModel):
    id: int
    game_code: str
    host_user_id: Optional[int]  # Allow None for anonymous game creation
    config_id: Optional[int]
    status: GameStatus
    game_state: Optional[Dict[str, Any]]
    num_teams: Optional[int]  # Number of teams configured by host
    game_duration_minutes: Optional[int]  # Game duration in minutes (60-240 in 30min intervals)
    created_at: datetime
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Player schemas
class PlayerJoin(BaseModel):
    game_code: str = Field(..., min_length=6, max_length=6)
    player_name: str = Field(..., min_length=1, max_length=100)
    role: PlayerRole
    # Group number removed - will be assigned by host from dashboard or automatically


class PlayerResponse(BaseModel):
    id: int
    game_session_id: int
    user_id: Optional[int]
    player_name: str
    role: PlayerRole
    group_number: Optional[int]
    is_approved: bool
    is_connected: bool
    player_state: Optional[Dict[str, Any]]
    joined_at: datetime
    needs_approval: Optional[bool] = None  # Client-side field
    
    class Config:
        from_attributes = True


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Game Event schemas
class GameEventCreate(BaseModel):
    event_type: str
    event_data: Dict[str, Any]
    player_id: Optional[int] = None


class GameEventResponse(BaseModel):
    id: int
    game_session_id: int
    player_id: Optional[int]
    event_type: str
    event_data: Dict[str, Any]
    timestamp: datetime
    
    class Config:
        from_attributes = True
