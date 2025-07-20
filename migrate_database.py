#!/usr/bin/env python3
"""
Database Migration Script
Adds new columns to existing SajiloHire database for enhanced features
"""

import os
from database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    with engine.connect() as conn:
        result = conn.execute(text(f'PRAGMA table_info({table_name});')).fetchall()
        columns = [row[1] for row in result]
        return column_name in columns


def add_column_if_not_exists(table_name: str, column_name: str, column_definition: str):
    """Add a column to a table if it doesn't exist"""
    if not check_column_exists(table_name, column_name):
        try:
            with engine.connect() as conn:
                sql = f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition};'
                conn.execute(text(sql))
                conn.commit()
                logger.info(f"✅ Added column '{column_name}' to table '{table_name}'")
        except Exception as e:
            logger.error(f"❌ Failed to add column '{column_name}': {e}")
    else:
        logger.info(f"⏭️ Column '{column_name}' already exists in table '{table_name}'")


def migrate_database():
    """Run database migration to add new columns"""
    logger.info("🚀 Starting database migration...")
    
    # Check if database exists
    db_path = './sajilohire.db'
    if not os.path.exists(db_path):
        logger.error(f"❌ Database not found at {db_path}")
        return False
    
    try:
        # Add new columns to extended_persons table
        logger.info("📊 Adding new columns to extended_persons table...")
        
        # enrichment_progress: JSON column for tracking enrichment progress
        add_column_if_not_exists(
            'extended_persons', 
            'enrichment_progress', 
            'JSON'
        )
        
        # comprehensive_insights: JSON column for storing generated insights
        add_column_if_not_exists(
            'extended_persons', 
            'comprehensive_insights', 
            'JSON'
        )
        
        # profile_completeness_score: Float column for profile quality score
        add_column_if_not_exists(
            'extended_persons', 
            'profile_completeness_score', 
            'FLOAT'
        )
        
        # interview_plan: JSON column for storing adaptive interview plans
        add_column_if_not_exists(
            'extended_persons', 
            'interview_plan', 
            'JSON'
        )
        
        logger.info("✅ Database migration completed successfully!")
        
        # Verify all columns are present
        logger.info("🔍 Verifying migration...")
        with engine.connect() as conn:
            result = conn.execute(text('PRAGMA table_info(extended_persons);')).fetchall()
            columns = [row[1] for row in result]
            
            required_columns = [
                'enrichment_progress', 
                'comprehensive_insights', 
                'profile_completeness_score', 
                'interview_plan'
            ]
            
            missing = [col for col in required_columns if col not in columns]
            
            if missing:
                logger.error(f"❌ Still missing columns: {missing}")
                return False
            else:
                logger.info("✅ All required columns are present!")
                logger.info(f"📊 Total columns in extended_persons: {len(columns)}")
                return True
                
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    print("🗄️ SajiloHire Database Migration")
    print("=" * 40)
    
    success = migrate_database()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("✅ Database is now compatible with enhanced features")
        print("\n📋 Next steps:")
        print("   1. Restart your application server")
        print("   2. Test the enhanced features")
        print("   3. Existing data is preserved")
    else:
        print("\n❌ Migration failed!")
        print("⚠️ Please check the error messages above")
