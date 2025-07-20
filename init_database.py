#!/usr/bin/env python3
"""
Database initialization script to create all tables with the latest schema
"""

import os
import sys
import logging
from pathlib import Path

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database():
    """Create database and all tables"""
    try:
        # Import our modules
        from database import engine, Base
        from models import (
            ExtendedPerson, 
            ExtendedJobCache, 
            ChatTurn, 
            CandidateSignals, 
            CandidateScore, 
            ClientCache
        )
        
        logger.info("🗄️  Creating database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Database tables created successfully!")
        
        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'extended_persons',
            'extended_job_cache', 
            'chat_turns',
            'candidate_signals',
            'candidate_scores',
            'client_cache'
        ]
        
        logger.info(f"📋 Created tables: {tables}")
        
        missing_tables = [table for table in expected_tables if table not in tables]
        if missing_tables:
            logger.error(f"❌ Missing tables: {missing_tables}")
            return False
        
        # Verify AI analysis columns in candidate_scores
        columns = inspector.get_columns('candidate_scores')
        column_names = [col['name'] for col in columns]
        
        ai_columns = ['ai_analysis_json', 'scoring_method']
        missing_ai_columns = [col for col in ai_columns if col not in column_names]
        
        if missing_ai_columns:
            logger.error(f"❌ Missing AI columns in candidate_scores: {missing_ai_columns}")
            return False
        
        logger.info(f"✅ AI analysis columns confirmed: {ai_columns}")
        logger.info(f"📊 candidate_scores columns: {column_names}")
        
        return True
        
    except Exception as e:
        logger.error(f"💥 Database creation failed: {e}")
        return False

def populate_initial_data():
    """Populate with initial/sample data if needed"""
    try:
        from database import get_db
        
        # This could be expanded to add sample data
        logger.info("🌱 Ready for data population...")
        return True
        
    except Exception as e:
        logger.error(f"💥 Data population failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Initializing SajiloHire Database...")
    
    # Check if database file exists
    db_path = "sajilohire.db"
    if os.path.exists(db_path):
        print(f"⚠️  Database {db_path} already exists!")
        response = input("Do you want to delete and recreate it? (y/N): ")
        if response.lower() != 'y':
            print("❌ Aborted")
            sys.exit(1)
        os.remove(db_path)
        print(f"🗑️  Deleted existing database")
    
    # Create database
    if create_database():
        print("🎉 Database initialization completed successfully!")
        
        # Try to populate initial data
        if populate_initial_data():
            print("✅ All setup completed!")
        else:
            print("⚠️  Database created but data population failed")
    else:
        print("❌ Database initialization failed!")
        sys.exit(1)
