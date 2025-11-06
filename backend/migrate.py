"""
Database migration runner
Run migrations to update database schema without losing data
"""

import logging
from sqlalchemy import text
from database import engine

logger = logging.getLogger(__name__)

def run_migrations():
    """Run all pending database migrations"""
    logger.info("Starting database migrations...")
    
    migrations = [
        {
            "name": "001_add_difficulty_column",
            "description": "Add difficulty column to game_sessions table",
            "sql": """
                -- Add difficulty column with default value 'medium'
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='game_sessions' AND column_name='difficulty'
                    ) THEN
                        ALTER TABLE game_sessions 
                        ADD COLUMN difficulty VARCHAR(10) DEFAULT 'medium' NOT NULL;
                        
                        -- Add check constraint
                        ALTER TABLE game_sessions
                        ADD CONSTRAINT check_difficulty_values 
                        CHECK (difficulty IN ('easy', 'medium', 'hard'));
                        
                        RAISE NOTICE 'Added difficulty column to game_sessions';
                    END IF;
                END $$;
            """
        }
    ]
    
    with engine.connect() as conn:
        for migration in migrations:
            try:
                logger.info(f"Running migration: {migration['name']} - {migration['description']}")
                
                # For PostgreSQL
                if 'postgresql' in str(engine.url):
                    conn.execute(text(migration['sql']))
                    conn.commit()
                # For SQLite (development)
                else:
                    # SQLite doesn't support DO blocks, so use simpler approach
                    try:
                        conn.execute(text(
                            "ALTER TABLE game_sessions ADD COLUMN difficulty VARCHAR(10) DEFAULT 'medium' NOT NULL"
                        ))
                        conn.commit()
                    except Exception as e:
                        # Column might already exist
                        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                            logger.info(f"Column already exists in SQLite, skipping")
                        else:
                            raise
                
                logger.info(f"✓ Migration {migration['name']} completed successfully")
            except Exception as e:
                logger.error(f"✗ Migration {migration['name']} failed: {e}")
                # Don't raise - allow app to continue if migration already applied
                
    logger.info("Database migrations completed")
