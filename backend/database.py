"""
Database configuration and session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress noisy Azure Monitor telemetry logs
logging.getLogger("azure.monitor.opentelemetry.exporter").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

load_dotenv()

# Check if running on Azure (Azure sets WEBSITE_SITE_NAME)
IS_AZURE = os.getenv("WEBSITE_SITE_NAME") is not None

if IS_AZURE:
    # Use PostgreSQL connection string from Azure if available, otherwise fall back to SQLite
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set, using SQLite on Azure (not recommended for production)")
        DATABASE_URL = "sqlite:///./trading_game.db"
    else:
        logger.info("Using PostgreSQL database on Azure")
else:
    # Local SQLite
    DATABASE_URL = "sqlite:///./trading_game.db"
    logger.info("Using local SQLite database")

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL (Azure)
    # Make SQL logging configurable via environment variable (default: False)
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "False").lower() in ("1", "true", "yes")
    engine = create_engine(DATABASE_URL, echo=SQLALCHEMY_ECHO)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables and run migrations"""
    logger.info("Initializing database tables...")
    try:
        # Import all models to ensure they are registered with Base
        from models import (
            Base, User, GameSession, Player, GameConfiguration,
            Challenge, TradeOffer, PriceHistory, OAuthToken, GameEventInstance
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # List created tables for verification
        logger.info(f"Created tables: {list(Base.metadata.tables.keys())}")
        
        # Run migrations to add any new columns to existing tables
        try:
            from migrate import run_migrations
            run_migrations()
        except Exception as migration_error:
            logger.warning(f"Migration warning (non-fatal): {migration_error}")
            # Don't fail initialization if migrations have issues
            
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
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
