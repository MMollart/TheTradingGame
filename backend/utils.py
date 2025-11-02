"""
Utility functions for game management
"""

import random
import string
from sqlalchemy.orm import Session
from backend.models import GameSession


def generate_game_code(db: Session) -> str:
    """
    Generate a unique 6-digit game code
    Format: 6 uppercase alphanumeric characters (excluding confusing chars like O, 0, I, 1)
    """
    # Use characters that are easy to read and distinguish
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    
    max_attempts = 100
    for _ in range(max_attempts):
        code = ''.join(random.choices(chars, k=6))
        
        # Check if code already exists
        existing = db.query(GameSession).filter(GameSession.game_code == code).first()
        if not existing:
            return code
    
    raise ValueError("Unable to generate unique game code after maximum attempts")


def validate_game_code(code: str) -> bool:
    """Validate game code format"""
    if len(code) != 6:
        return False
    if not code.isalnum():
        return False
    return code.isupper()
