"""
Sajilo Jobs router
Provides job listings for the frontend
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from database import get_db
from models import ExtendedJobCache, ClientCache
from schemas import ErrorResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/jobs", responses={500: {"model": ErrorResponse}})
def get_jobs(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get all available jobs for the frontend"""
    
    try:
        # Get all jobs from cache
        jobs = db.query(ExtendedJobCache).all()
        
        # Format jobs for frontend
        job_list = []
        for job in jobs:
            # Get company name from client cache if available
            client = None
            if job.client_id:
                client = db.query(ClientCache).filter(
                    ClientCache.upstream_client_id == job.client_id
                ).first()
            
            # Format job data for frontend
            job_data = {
                "id": job.upstream_job_id,
                "title": job.title or "Untitled Position",
                "company": job.client_name or (client.client_name if client else "Unknown Company"),
                "location": (f"{client.city}, {client.state}" if client and client.city and client.state 
                           else client.city if client and client.city 
                           else "Remote"),
                "type": job.employment_type or "Full-time",
                "salary": job.salary if job.salary else "Competitive",
                "description": job.description or "No description available",
                "requirements": _extract_requirements(job.skills_json),
                "posted": job.created_date.strftime("%B %d, %Y") if job.created_date else "Recently"
            }
            job_list.append(job_data)
        
        # Sort by ID descending (most recent first)
        job_list.sort(key=lambda x: x["id"], reverse=True)
        
        return job_list
        
    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve jobs")


def _extract_requirements(skills_json: List[Dict[str, Any]]) -> List[str]:
    """Extract skill requirements from job skills JSON"""
    if not skills_json:
        return []
    
    requirements = []
    for skill in skills_json:
        skill_name = skill.get("skillName")
        if skill_name:
            requirements.append(skill_name)
    
    # Limit to top 5 skills
    return requirements[:5]
