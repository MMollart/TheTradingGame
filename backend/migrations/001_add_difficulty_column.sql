-- Migration: Add difficulty column to game_sessions table
-- Date: 2025-11-06
-- Description: Adds game difficulty setting (easy/medium/hard) to control starting resources

-- Add difficulty column with default value 'medium'
ALTER TABLE game_sessions 
ADD COLUMN IF NOT EXISTS difficulty VARCHAR(10) DEFAULT 'medium' NOT NULL;

-- Update any existing records to have 'medium' difficulty
UPDATE game_sessions 
SET difficulty = 'medium' 
WHERE difficulty IS NULL;

-- Add check constraint to ensure only valid difficulty values
ALTER TABLE game_sessions
DROP CONSTRAINT IF EXISTS check_difficulty_values;

ALTER TABLE game_sessions
ADD CONSTRAINT check_difficulty_values 
CHECK (difficulty IN ('easy', 'medium', 'hard'));
