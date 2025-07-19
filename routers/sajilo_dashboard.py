"""
Sajilo Dashboard router
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from schemas import DashboardResponse, DashboardCandidate, ErrorResponse
from database import get_db
from models import ExtendedPerson, CandidateScore, ExtendedJobCache
from services.scoring_engine import scoring_engine
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard/{job_id}", response_model=DashboardResponse, responses={404: {"model": ErrorResponse}})
def get_dashboard(
    job_id: int, 
    include_borderline: bool = Query(False, description="Include borderline candidates"),
    db: Session = Depends(get_db)
):
    """Get recruiter dashboard with ranked candidates for a job"""
    
    try:
        # Verify job exists in cache
        job = db.query(ExtendedJobCache).filter(
            ExtendedJobCache.upstream_job_id == job_id
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get candidates for this job
        query = db.query(ExtendedPerson).filter(ExtendedPerson.job_id == job_id)
        
        # Filter by score if needed
        if not include_borderline:
            query = query.join(CandidateScore).filter(
                CandidateScore.fit_bucket.in_(["top", "borderline"])
            )
        
        candidates = query.all()
        
        # Ensure all candidates have scores
        for candidate in candidates:
            if not candidate.score:
                scoring_engine.compute_score(candidate, db)
        
        # Build dashboard candidates
        dashboard_candidates = []
        for person in candidates:
            if person.score and person.signals:
                dashboard_candidate = DashboardCandidate(
                    person_id=person.id,
                    full_name=f"{person.first_name} {person.last_name}",
                    email=person.email,
                    fit_score=person.score.fit_score,
                    fit_bucket=person.score.fit_bucket,
                    turnover_risk=person.signals.turnover_risk,
                    flags=person.signals.flags or [],
                    applied_at=person.created_ts
                )
                dashboard_candidates.append(dashboard_candidate)
        
        # Sort by fit score descending
        dashboard_candidates.sort(key=lambda x: x.fit_score, reverse=True)
        
        # Count high-fit candidates
        high_fit_count = len([c for c in dashboard_candidates if c.fit_bucket == "top"])
        
        return DashboardResponse(
            job_id=job_id,
            job_title=job.title,
            candidates=dashboard_candidates,
            total_count=len(dashboard_candidates),
            high_fit_count=high_fit_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard failed for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")
