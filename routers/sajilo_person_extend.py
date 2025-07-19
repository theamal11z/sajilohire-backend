"""
Sajilo Person Extend router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import PersonExtend, PersonResponse, ErrorResponse
from database import get_db
from models import ExtendedPerson
from services.resume_ingest import resume_processor
from services.github_enrichment import github_enrichment_service
from services.phantombuster_enrichment import phantombuster_enrichment_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/person/{person_id}/extend", response_model=PersonResponse, responses={404: {"model": ErrorResponse}})
def extend_person(person_id: int, person_extend: PersonExtend, db: Session = Depends(get_db)):
    """Extend person with job, resume, and profile data"""
    
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
                    if github_skills:
                        existing_skills = person.skills_tags or []
                        # Combine and deduplicate skills
                        combined_skills = list(set(existing_skills + github_skills))
                        person.skills_tags = combined_skills[:15]  # Limit to top 15 skills
                    
                    logger.info(f"GitHub enrichment completed for person {person_id}: {github_data.get('username')} with {len(github_skills)} skills")
                else:
                    logger.warning(f"GitHub enrichment failed for person {person_id}: {person.github}")
            except Exception as e:
                logger.error(f"GitHub enrichment error for person {person_id}: {e}")
                # Don't fail the entire request if GitHub enrichment fails
        
        # Advanced social media enrichment with PhantomBuster
        if person.linkedin or person.github:
            try:
                phantombuster_data = phantombuster_enrichment_service.enrich_candidate_profile(
                    linkedin_url=person.linkedin,
                    github_url=person.github
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
                    
                    logger.info(f"PhantomBuster enrichment completed for person {person_id}: Trust score {trust_score:.3f}, Status: {person.social_verification_status}")
                else:
                    logger.warning(f"PhantomBuster enrichment returned no data for person {person_id}")
                    
            except Exception as e:
                logger.error(f"PhantomBuster enrichment error for person {person_id}: {e}")
                # Don't fail the entire request if PhantomBuster enrichment fails
        
        db.commit()
        db.refresh(person)
        
        logger.info(f"Extended person {person_id} with job {person_extend.job_id}")
        return person
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extend person {person_id}: {e}")
        raise HTTPException(status_code=400, detail="Failed to extend person")
