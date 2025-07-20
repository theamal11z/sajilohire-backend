"""
Sajilo Person Extend router
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from schemas import PersonExtend, PersonResponse, ErrorResponse
from database import get_db
from models import ExtendedPerson
from services.resume_ingest import resume_processor
from services.github_enrichment import github_enrichment_service
from services.phantombuster_enrichment import phantombuster_enrichment_service
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/person/{person_id}/extend", response_model=PersonResponse, responses={404: {"model": ErrorResponse}})
def extend_person(person_id: int, person_extend: PersonExtend, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Extend person with job, resume, and profile data (PhantomBuster enrichment runs in background)"""
    
    try:
        # Get existing person
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Update person with extended data
        person.job_id = person_extend.job_id
        person.resume_text = person_extend.resume_text
        person.intro = person_extend.intro
        person.why_us = person_extend.why_us
        person.linkedin = person_extend.linkedin
        person.github = person_extend.github
        
        # Parse skills into tags
        if person_extend.skills:
            skills_list = [skill.strip() for skill in person_extend.skills.split(",")]
            person.skills_tags = skills_list
        
        # Process resume for additional skills and insights
        if person.resume_text:
            resume_analysis = resume_processor.process_resume(person, person.resume_text, db)
            logger.info(f"Resume analysis completed for person {person_id}: {len(resume_analysis.get('skills_detected', []))} additional skills found")
        
        # Enrich GitHub profile if provided
        if person.github:
            try:
                github_data = github_enrichment_service.enrich_profile(person.github)
                if github_data:
                    person.github_data = github_data
                    person.avatar_url = github_data.get('avatar_url')
                    
                    # Merge GitHub skills with existing skills
                    github_skills = github_data.get('skills_detected', [])
                    if github_skills and isinstance(github_skills, list):
                        existing_skills = person.skills_tags or []
                        # Ensure both are lists and combine safely
                        if isinstance(existing_skills, list):
                            # Combine and deduplicate skills
                            combined_skills = list(set(existing_skills + github_skills))
                            person.skills_tags = combined_skills[:15]  # Limit to top 15 skills
                        else:
                            person.skills_tags = github_skills[:15]
                    
                    logger.info(f"GitHub enrichment completed for person {person_id}: {github_data.get('username')} with {len(github_skills)} skills")
                else:
                    logger.warning(f"GitHub enrichment failed for person {person_id}: {person.github}")
            except Exception as e:
                logger.error(f"GitHub enrichment error for person {person_id}: {e}")
                # Don't fail the entire request if GitHub enrichment fails
        
        # Set initial enrichment status
        if person.linkedin or person.github:
            person.social_verification_status = 'processing'
            logger.info(f"Starting background PhantomBuster enrichment for person {person_id}")
            
            # Add background task for PhantomBuster enrichment (this runs asynchronously)
            background_tasks.add_task(
                background_phantombuster_enrichment,
                person_id,
                person.linkedin,
                person.github
            )
        
        db.commit()
        db.refresh(person)
        
        logger.info(f"Extended person {person_id} with job {person_extend.job_id}")
        return person
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extend person {person_id}: {e}")
        raise HTTPException(status_code=400, detail="Failed to extend person")


def background_phantombuster_enrichment(person_id: int, linkedin_url: str, github_url: str):
    """Background task for PhantomBuster enrichment"""
    from database import SessionLocal  # Import here to avoid circular imports
    
    db = SessionLocal()
    try:
        logger.info(f"Starting PhantomBuster background enrichment for person {person_id}")
        
        # Get the person record
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            logger.error(f"Person {person_id} not found for background enrichment")
            return
        
        # Update status to indicate processing
        person.social_verification_status = 'processing'
        db.commit()
        
        try:
            # Perform PhantomBuster enrichment (this may take 30s - 2 minutes)
            phantombuster_data = phantombuster_enrichment_service.enrich_candidate_profile(
                linkedin_url=linkedin_url,
                github_url=github_url
            )
            
            if phantombuster_data:
                person.phantombuster_data = phantombuster_data
                person.trust_score = phantombuster_data.get('trust_score', 0.0)
                
                # Set verification status based on trust score and risk indicators
                trust_score = phantombuster_data.get('trust_score', 0.0)
                risk_indicators = phantombuster_data.get('risk_indicators', [])
                
                if trust_score >= 0.8 and not risk_indicators:
                    person.social_verification_status = 'verified'
                elif trust_score >= 0.6 or len(risk_indicators) <= 1:
                    person.social_verification_status = 'needs_review'
                else:
                    person.social_verification_status = 'unverified'
                
                # Use LinkedIn profile image if no GitHub avatar
                linkedin_analysis = phantombuster_data.get('linkedin_analysis', {})
                linkedin_basic = linkedin_analysis.get('basic_info', {})
                if not person.avatar_url and linkedin_basic.get('profile_image_url'):
                    person.avatar_url = linkedin_basic['profile_image_url']
                
                logger.info(f"PhantomBuster background enrichment completed for person {person_id}: Trust score {trust_score:.3f}, Status: {person.social_verification_status}")
            else:
                logger.warning(f"PhantomBuster enrichment returned no data for person {person_id}")
                person.social_verification_status = 'failed'
                
        except Exception as e:
            logger.error(f"PhantomBuster background enrichment error for person {person_id}: {e}")
            person.social_verification_status = 'failed'
        
        # Final commit with results
        db.commit()
        
    finally:
        db.close()


@router.get("/person/{person_id}/enrichment-status")
def get_enrichment_status(person_id: int, db: Session = Depends(get_db)):
    """Get the current status of PhantomBuster enrichment for a person"""
    
    person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    status = person.social_verification_status or 'not_started'
    trust_score = person.trust_score
    has_enrichment_data = bool(person.phantombuster_data)
    
    return {
        "person_id": person_id,
        "enrichment_status": status,
        "trust_score": trust_score,
        "has_enrichment_data": has_enrichment_data,
        "status_descriptions": {
            "not_started": "Enrichment has not been initiated",
            "processing": "Currently analyzing LinkedIn and social profiles...",
            "verified": "Profile verified with high trust score",
            "needs_review": "Profile analyzed, manual review recommended", 
            "unverified": "Profile could not be verified",
            "failed": "Enrichment process failed, will retry later"
        },
        "estimated_completion": "1-3 minutes" if status == "processing" else None
    }
