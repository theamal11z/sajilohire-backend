"""
Health check router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from database import get_db
from schemas import HealthResponse
from aqore_client import aqore_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    
    health_status = HealthResponse(
        status="ok",
        timestamp=datetime.now(),
        version="1.0.0",
        database="connected",
        upstream_api="connected"
    )
    
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        
        # Test upstream API connection  
        aqore_client.get_clients(page_number=1)
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health_status.status = "error"
        health_status.database = "error"
        health_status.upstream_api = "error"
        
        raise HTTPException(status_code=503, detail="Service unavailable")
