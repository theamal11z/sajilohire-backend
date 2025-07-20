-- Migration script to add AI analysis columns to candidate_scores table
-- Run this with: sqlite3 sajilohire.db < migrate_database.sql

-- Check if columns exist and add them if they don't
BEGIN TRANSACTION;

-- Add ai_analysis_json column if it doesn't exist
ALTER TABLE candidate_scores ADD COLUMN ai_analysis_json TEXT;

-- Add scoring_method column if it doesn't exist  
ALTER TABLE candidate_scores ADD COLUMN scoring_method VARCHAR(20) DEFAULT 'ai';

-- Update existing records to use 'legacy' scoring method
UPDATE candidate_scores SET scoring_method = 'legacy' WHERE scoring_method IS NULL OR scoring_method = '';

COMMIT;

-- Verify the changes
PRAGMA table_info(candidate_scores);

SELECT 'Migration completed successfully' as status;
