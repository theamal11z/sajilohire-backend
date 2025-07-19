"""
Sajilo Job Profile router
Provides enhanced job and company profile data for better candidate matching
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import JobProfileResponse, ErrorResponse
from database import get_db
from services.job_profile_service import job_profile_analyzer
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/job-profile/{job_id}", response_model=JobProfileResponse, responses={404: {"model": ErrorResponse}})
def get_job_profile(job_id: int, db: Session = Depends(get_db)):
    """Get comprehensive job profile with company context and requirements analysis"""
    
    try:
        # Get comprehensive job profile
        job_profile = job_profile_analyzer.get_comprehensive_job_profile(job_id, db)
        
        if not job_profile:
            raise HTTPException(status_code=404, detail="Job profile not found")
        
        return JobProfileResponse(
            job=job_profile.get('job', {}),
            company=job_profile.get('company', {}),
            personalization_context=job_profile.get('personalization_context', {}),
            interview_focus=job_profile.get('interview_focus', {}),
            cultural_indicators=job_profile.get('cultural_indicators', [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job profile {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve job profile")


@router.get("/job-profile/{job_id}/context", responses={404: {"model": ErrorResponse}})
def get_personalization_context(job_id: int, db: Session = Depends(get_db)):
    """Get just the personalization context for a job (used by AI chat engine)"""
    
    try:
        job_profile = job_profile_analyzer.get_comprehensive_job_profile(job_id, db)
        
        if not job_profile:
            raise HTTPException(status_code=404, detail="Job profile not found")
        
        return {
            "job_id": job_id,
            "personalization_context": job_profile.get('personalization_context', {}),
            "interview_focus": job_profile.get('interview_focus', {}),
            "company_info": {
                "name": job_profile.get('company', {}).get('name'),
                "industry": job_profile.get('company', {}).get('industry'),
                "values": job_profile.get('company', {}).get('industry_insights', {}).get('values', [])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get personalization context for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve personalization context")


@router.get("/job-profile/{job_id}/skills-analysis", responses={404: {"model": ErrorResponse}})
def get_skills_analysis(job_id: int, db: Session = Depends(get_db)):
    """Get detailed skills analysis for a job"""
    
    try:
        job_profile = job_profile_analyzer.get_comprehensive_job_profile(job_id, db)
        
        if not job_profile:
            raise HTTPException(status_code=404, detail="Job profile not found")
        
        job_info = job_profile.get('job', {})
        
        return {
            "job_id": job_id,
            "skills": job_info.get('skills', []),
            "analyzed_skills": job_info.get('analyzed_skills', {}),
            "technical_focus": job_info.get('technical_focus', []),
            "role_level": job_info.get('role_level', 'mid-level'),
            "primary_technologies": job_info.get('analyzed_skills', {}).get('primary_technologies', [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get skills analysis for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve skills analysis")
