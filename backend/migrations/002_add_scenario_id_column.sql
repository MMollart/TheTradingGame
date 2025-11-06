-- Migration: Add scenario_id column to game_sessions table
-- Date: 2025-11-06
-- Description: Add scenario_id column to support historical scenarios feature

-- Add scenario_id column (nullable, since not all games will use scenarios)
ALTER TABLE game_sessions ADD COLUMN scenario_id VARCHAR(50);

-- Add index for faster lookups by scenario
CREATE INDEX IF NOT EXISTS idx_game_sessions_scenario_id ON game_sessions(scenario_id);
