#!/usr/bin/env python3
"""
Database migration script to add AI scoring fields to CandidateScore table
"""

from sqlalchemy import text
from database import engine, get_db
import logging

logger = logging.getLogger(__name__)


def migrate_candidate_score_table():
    """Add AI analysis fields to candidate_scores table"""
    
    with engine.connect() as connection:
        # Start transaction
        trans = connection.begin()
        
        try:
            # Check if columns already exist
            result = connection.execute(text("PRAGMA table_info(candidate_scores)"))
            existing_columns = [row[1] for row in result.fetchall()]
            
            # Add ai_analysis_json column if it doesn't exist
            if 'ai_analysis_json' not in existing_columns:
                logger.info("Adding ai_analysis_json column to candidate_scores table")
                connection.execute(text("ALTER TABLE candidate_scores ADD COLUMN ai_analysis_json JSON"))
            else:
                logger.info("ai_analysis_json column already exists")
            
            # Add scoring_method column if it doesn't exist
            if 'scoring_method' not in existing_columns:
                logger.info("Adding scoring_method column to candidate_scores table")
                connection.execute(text("ALTER TABLE candidate_scores ADD COLUMN scoring_method VARCHAR(20) DEFAULT 'ai'"))
            else:
                logger.info("scoring_method column already exists")
            
            # Update existing records to have scoring_method = 'legacy'
            result = connection.execute(text("UPDATE candidate_scores SET scoring_method = 'legacy' WHERE scoring_method IS NULL"))
            logger.info(f"Updated {result.rowcount} existing records to use legacy scoring method")
            
            # Commit transaction
            trans.commit()
            logger.info("Database migration completed successfully")
            
        except Exception as e:
            # Rollback on error
            trans.rollback()
            logger.error(f"Migration failed: {e}")
            raise


def verify_migration():
    """Verify that the migration was successful"""
    
    with engine.connect() as connection:
        # Check table structure
        result = connection.execute(text("PRAGMA table_info(candidate_scores)"))
        columns = {row[1]: row[2] for row in result.fetchall()}
        
        required_columns = ['ai_analysis_json', 'scoring_method']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            logger.error(f"Migration verification failed. Missing columns: {missing_columns}")
            return False
        
        # Check data integrity
        result = connection.execute(text("SELECT COUNT(*) FROM candidate_scores WHERE scoring_method IS NULL"))
        null_count = result.fetchone()[0]
        
        if null_count > 0:
            logger.warning(f"{null_count} records have NULL scoring_method")
        
        logger.info("Migration verification successful")
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        print("🔄 Starting database migration for AI scoring...")
        migrate_candidate_score_table()
        
        print("✅ Verifying migration...")
        if verify_migration():
            print("🎉 Migration completed successfully!")
        else:
            print("❌ Migration verification failed!")
            
    except Exception as e:
        print(f"💥 Migration failed: {e}")
        exit(1)
