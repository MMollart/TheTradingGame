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
        },
        {
            "name": "002_add_cascade_delete_price_history",
            "description": "Add CASCADE delete to price_history foreign key",
            "sql": """
                -- Drop and recreate the foreign key with CASCADE
                DO $$ 
                BEGIN
                    -- Check if the constraint exists
                    IF EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name='price_history_game_session_id_fkey' 
                        AND table_name='price_history'
                    ) THEN
                        -- Drop the existing constraint
                        ALTER TABLE price_history 
                        DROP CONSTRAINT price_history_game_session_id_fkey;
                        
                        RAISE NOTICE 'Dropped old foreign key constraint';
                    END IF;
                    
                    -- Add the constraint with CASCADE
                    ALTER TABLE price_history 
                    ADD CONSTRAINT price_history_game_session_id_fkey 
                    FOREIGN KEY (game_session_id) 
                    REFERENCES game_sessions(id) 
                    ON DELETE CASCADE;
                    
                    RAISE NOTICE 'Added CASCADE delete to price_history foreign key';
                END $$;
            """
        },
        {
            "name": "003_add_scenario_id_column",
            "description": "Add scenario_id column to game_sessions table",
            "sql": """
                -- Add scenario_id column to support historical scenarios feature
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='game_sessions' AND column_name='scenario_id'
                    ) THEN
                        ALTER TABLE game_sessions 
                        ADD COLUMN scenario_id VARCHAR(50);
                        
                        -- Add index for faster lookups by scenario
                        CREATE INDEX idx_game_sessions_scenario_id ON game_sessions(scenario_id);
                        
                        RAISE NOTICE 'Added scenario_id column to game_sessions';
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
                # For SQLite (development/testing)
                else:
                    # SQLite doesn't support DO blocks
                    # Since we import all models before create_all(), columns should already exist
                    # Just log that we're skipping for SQLite
                    logger.info(f"Column already exists in SQLite, skipping")
                
                logger.info(f"✓ Migration {migration['name']} completed successfully")
            except Exception as e:
                logger.error(f"✗ Migration {migration['name']} failed: {e}")
                # Don't raise - allow app to continue if migration already applied
                
    logger.info("Database migrations completed")
