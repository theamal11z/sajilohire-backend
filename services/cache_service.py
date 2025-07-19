"""
Data cache service for fetching and storing upstream API data
"""

import asyncio
from aqore_client import aqore_client
from database import SessionLocal
from models import ExtendedJobCache, ClientCache
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def sync_upstream_data() -> None:
    """Sync required upstream data from Aqore API"""
    logger.info("Syncing upstream data...")
    try:
        await sync_clients()
        await sync_jobs()
        logger.info("Sync completed successfully")
    except Exception as e:
        logger.error(f"Failed to sync upstream data: {e}")
        # Don't raise - allow app to start even if sync fails


async def sync_clients() -> None:
    """Sync client data from Aqore API"""
    logger.info("Syncing clients from Aqore API...")
    try:
        clients = aqore_client.get_all_clients()
        db = SessionLocal()
        try:
            for client_data in clients[:10]:  # Limit to first 10 for demo
                generate_client_from_upstream(client_data, db)
            db.commit()
            logger.info(f"Synced {len(clients[:10])} clients")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Client sync failed: {e}")


async def sync_jobs() -> None:
    """Sync job data from Aqore API"""
    logger.info("Syncing jobs from Aqore API...")
    try:
        jobs = aqore_client.get_all_jobs()
        db = SessionLocal()
        try:
            for job_data in jobs[:20]:  # Limit to first 20 for demo
                generate_job_from_upstream(job_data, db)
            db.commit()
            logger.info(f"Synced {len(jobs[:20])} jobs")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Job sync failed: {e}")


def generate_client_from_upstream(client_data: dict, db) -> ClientCache:
    """Create or update client cache from upstream data"""
    client_id = client_data.get("clientId")
    if not client_id:
        return None
    
    # Check if already exists
    existing = db.query(ClientCache).filter(
        ClientCache.upstream_client_id == client_id
    ).first()
    
    if existing:
        return existing
    
    # Create new client cache entry
    client_cache = ClientCache(
        upstream_client_id=client_id,
        client_name=client_data.get("clientName"),
        industry=client_data.get("industry"),
        city=client_data.get("city"),
        state=client_data.get("state"),
        zip_code=client_data.get("zipCode"),
        address1=client_data.get("address1"),
        address2=client_data.get("address2"),
        email=client_data.get("email"),
        phone=client_data.get("phone"),
        notes=client_data.get("notes"),
        created_date=datetime.fromisoformat(client_data["createdDate"]) if client_data.get("createdDate") else None,
        cached_at=datetime.now()
    )
    
    db.add(client_cache)
    return client_cache


def generate_job_from_upstream(job_data: dict, db) -> ExtendedJobCache:
    """Create or update job cache from upstream data"""
    job_id = job_data.get("jobId")
    if not job_id:
        return None
    
    # Check if already exists
    existing = db.query(ExtendedJobCache).filter(
        ExtendedJobCache.upstream_job_id == job_id
    ).first()
    
    if existing:
        return existing
    
    # Get client name if available
    client_name = None
    client_id = job_data.get("clientId")
    if client_id:
        client_cache = db.query(ClientCache).filter(
            ClientCache.upstream_client_id == client_id
        ).first()
        if client_cache:
            client_name = client_cache.client_name
    
    # Create new job cache entry
    job_cache = ExtendedJobCache(
        upstream_job_id=job_id,
        title=job_data.get("title", "Untitled Position"),
        description=job_data.get("description"),
        client_id=client_id or 0,
        client_name=client_name,
        job_type=job_data.get("jobType"),
        employment_type=job_data.get("employmentType"),
        status=job_data.get("status"),
        created_date=datetime.fromisoformat(job_data["createdDate"]) if job_data.get("createdDate") else None,
        skills_json=[],  # Will be populated separately if needed
        cached_at=datetime.now()
    )
    
    db.add(job_cache)
    return job_cache
