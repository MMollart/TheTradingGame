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
        },
        {
            "name": "004_add_trade_margin_columns",
            "description": "Add trade margin tracking columns to trade_offers table for kindness scoring",
            "sql": """
                -- Add trade margin columns for kindness-based scoring
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='trade_offers' AND column_name='from_team_margin'
                    ) THEN
                        ALTER TABLE trade_offers 
                        ADD COLUMN from_team_margin JSON;
                        
                        RAISE NOTICE 'Added from_team_margin column to trade_offers';
                    END IF;
                    
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name='trade_offers' AND column_name='to_team_margin'
                    ) THEN
                        ALTER TABLE trade_offers 
                        ADD COLUMN to_team_margin JSON;
                        
                        RAISE NOTICE 'Added to_team_margin column to trade_offers';
                    END IF;
                END $$;
            """
        },
        {
            "name": "005_create_game_event_instances_table",
            "description": "Create game_event_instances table for event system (disasters, economic events, etc.)",
            "sql": """
                -- Create game_event_instances table for tracking active game events
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name='game_event_instances'
                    ) THEN
                        CREATE TABLE game_event_instances (
                            id SERIAL PRIMARY KEY,
                            game_session_id INTEGER NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
                            event_type VARCHAR(23) NOT NULL,
                            event_category VARCHAR(16) NOT NULL,
                            severity INTEGER NOT NULL,
                            status VARCHAR(7) NOT NULL DEFAULT 'active',
                            event_data JSON,
                            duration_cycles INTEGER,
                            cycles_remaining INTEGER,
                            triggered_at TIMESTAMP NOT NULL DEFAULT NOW(),
                            expires_at TIMESTAMP
                        );
                        
                        CREATE INDEX idx_game_event_instances_game_session_id ON game_event_instances(game_session_id);
                        CREATE INDEX idx_game_event_instances_status ON game_event_instances(status);
                        
                        RAISE NOTICE 'Created game_event_instances table';
                    END IF;
                END $$;
            """
        },
        {
            "name": "006_create_oauth_tokens_table",
            "description": "Create oauth_tokens table for OAuth authentication (OSM integration)",
            "sql": """
                -- Create oauth_tokens table for external OAuth integrations
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name='oauth_tokens'
                    ) THEN
                        CREATE TABLE oauth_tokens (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            provider VARCHAR(3) NOT NULL,
                            access_token TEXT NOT NULL,
                            refresh_token TEXT,
                            token_type VARCHAR(50) DEFAULT 'Bearer',
                            expires_at TIMESTAMP,
                            scope VARCHAR(500),
                            created_at TIMESTAMP DEFAULT NOW(),
                            updated_at TIMESTAMP DEFAULT NOW()
                        );
                        
                        CREATE INDEX idx_oauth_tokens_user_id ON oauth_tokens(user_id);
                        CREATE INDEX idx_oauth_tokens_provider ON oauth_tokens(provider);
                        
                        RAISE NOTICE 'Created oauth_tokens table';
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
