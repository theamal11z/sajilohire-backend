"""
Sajilo Candidate router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import FullCandidateResponse, JobSkillMatch, ErrorResponse
from database import get_db
from models import ExtendedPerson, ChatTurn
from services.ai_scoring_engine import ai_scoring_engine
from services.job_profile_service import job_profile_analyzer
from aqore_client import aqore_client
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/candidate/{person_id}/full", response_model=FullCandidateResponse, responses={404: {"model": ErrorResponse}})
def get_full_candidate(person_id: int, db: Session = Depends(get_db)):
    """Get complete candidate profile with scores, signals, and chat history"""
    
    try:
        # Get person
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Get job profile for enhanced context
        job_profile = None
        if person.job_id:
            job_profile = job_profile_analyzer.get_comprehensive_job_profile(person.job_id, db)
        
        # Ensure scores are computed using AI
        if not person.score:
            ai_scoring_engine.compute_ai_score(person, db)
        
        # Get chat history
        chat_turns = db.query(ChatTurn).filter(
            ChatTurn.person_local_id == person_id
        ).order_by(ChatTurn.turn_index).all()
        
        # Get job skills for comparison
        job_skills = []
        try:
            if person.job_id:
                upstream_job_skills = aqore_client.get_job_skills_by_job_id(person.job_id)
                job_skills = [
                    JobSkillMatch(
                        skill_name=skill.get("skillName") or "",
                        required_level=skill.get("requiredProficiencyLevel") or "",
                        is_mandatory=bool(skill.get("isMandatory", False)),
                        # TODO: Compute candidate skill level and match score
                        candidate_level=None,
                        match_score=None
                    )
                    for skill in upstream_job_skills
                ]
        except Exception as e:
            logger.warning(f"Failed to fetch job skills for person {person_id}: {e}")
        
        # Get upstream person data if available
        upstream_data = None
        if person.upstream_person_id:
            try:
                upstream_data = {
                    "person": aqore_client.get_person_by_id(person.upstream_person_id),
                    "resume": aqore_client.get_person_resume_by_person_id(person.upstream_person_id),
                    "skills": aqore_client.get_person_skill_by_person_id(person.upstream_person_id),
                    "education": aqore_client.get_person_education_by_person_id(person.upstream_person_id),
                    "employment": aqore_client.get_person_employment_by_person_id(person.upstream_person_id)
                }
            except Exception as e:
                logger.warning(f"Failed to fetch upstream data for person {person_id}: {e}")
        
        return FullCandidateResponse(
            person=person,
            signals=person.signals,
            score=person.score,
            chat_history=chat_turns,
            job_skills=job_skills,
            job_profile=job_profile,
            upstream_data=upstream_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get full candidate {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve candidate profile")


@router.get("/candidate/{person_id}/ai-analysis", responses={404: {"model": ErrorResponse}})
def get_candidate_ai_analysis(person_id: int, db: Session = Depends(get_db)):
    """Get detailed AI analysis for candidate"""
    
    try:
        # Get person
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Get AI analysis (will compute if not exists)
        ai_analysis = ai_scoring_engine.get_detailed_ai_analysis(person, db)
        
        return {
            "person_id": person_id,
            "analysis_timestamp": person.score.computed_at.isoformat() if person.score else None,
            "scoring_method": person.score.scoring_method if person.score else "ai",
            "ai_analysis": ai_analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get AI analysis for candidate {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve AI analysis")


@router.post("/candidate/{person_id}/recompute-score", responses={404: {"model": ErrorResponse}})
def recompute_candidate_score(person_id: int, db: Session = Depends(get_db)):
    """Force recompute candidate score using AI"""
    
    try:
        # Get person
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Force recompute with AI
        score = ai_scoring_engine.compute_ai_score(person, db)
        
        return {
            "person_id": person_id,
            "message": "Score recomputed successfully",
            "fit_score": score.fit_score,
            "fit_bucket": score.fit_bucket,
            "computed_at": score.computed_at.isoformat(),
            "scoring_method": score.scoring_method
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to recompute score for candidate {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to recompute candidate score")
