"""
Database configuration and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Check if running on Azure (Azure sets WEBSITE_SITE_NAME)
IS_AZURE = os.getenv("WEBSITE_SITE_NAME") is not None

if IS_AZURE:
    # Use PostgreSQL connection string from Azure if available, otherwise fall back to SQLite
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("WARNING: DATABASE_URL not set, using SQLite on Azure (not recommended for production)")
        DATABASE_URL = "sqlite:///./trading_game.db"
    else:
        print(f"INFO: Using PostgreSQL database on Azure")
else:
    # Local SQLite
    DATABASE_URL = "sqlite:///./trading_game.db"
    print(f"INFO: Using local SQLite database")

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL (Azure)
    engine = create_engine(DATABASE_URL, echo=True)  # echo=True for debugging

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    print("INFO: Initializing database tables...")
    try:
        # Import all models to ensure they are registered with Base
        import models
        from models import Base, User, GameSession, Player, GameConfiguration
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("INFO: Database tables created successfully")
        
        # List created tables for verification
        print(f"INFO: Created tables: {list(Base.metadata.tables.keys())}")
    except Exception as e:
        print(f"ERROR: Failed to create database tables: {e}")
        import traceback
        traceback.print_exc()
        raise

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
