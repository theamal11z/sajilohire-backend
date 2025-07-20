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
    """Enhanced background task for PhantomBuster enrichment with retry logic"""
    from database import SessionLocal  # Import here to avoid circular imports
    import time
    
    MAX_RETRIES = 3
    RETRY_DELAYS = [30, 60, 120]  # Progressive backoff in seconds
    
    db = SessionLocal()
    try:
        logger.info(f"Starting enhanced PhantomBuster enrichment for person {person_id}")
        
        # Get the person record
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            logger.error(f"Person {person_id} not found for background enrichment")
            return
        
        # Update status to indicate processing
        person.social_verification_status = 'processing'
        person.enrichment_progress = {'stage': 'phantombuster', 'progress': 0.1}
        db.commit()
        
        # Retry logic for PhantomBuster enrichment
        phantombuster_data = None
        last_error = None
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"PhantomBuster enrichment attempt {attempt + 1}/{MAX_RETRIES} for person {person_id}")
                
                # Update progress
                person.enrichment_progress = {
                    'stage': 'phantombuster',
                    'progress': 0.1 + (0.6 * (attempt + 1) / MAX_RETRIES),
                    'attempt': attempt + 1
                }
                db.commit()
                
                # Perform PhantomBuster enrichment (this may take 30s - 2 minutes)
                phantombuster_data = phantombuster_enrichment_service.enrich_candidate_profile(
                    linkedin_url=linkedin_url,
                    github_url=github_url
                )
                
                if phantombuster_data:
                    logger.info(f"PhantomBuster enrichment successful on attempt {attempt + 1} for person {person_id}")
                    break
                else:
                    logger.warning(f"PhantomBuster returned no data on attempt {attempt + 1} for person {person_id}")
                    last_error = "No data returned from PhantomBuster service"
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"PhantomBuster enrichment error on attempt {attempt + 1} for person {person_id}: {e}")
                
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.info(f"Retrying PhantomBuster enrichment in {delay} seconds...")
                    time.sleep(delay)
        
        # Process results
        if phantombuster_data:
            person.phantombuster_data = phantombuster_data
            person.trust_score = phantombuster_data.get('trust_score', 0.0)
            
            # Enhanced verification status logic
            trust_score = phantombuster_data.get('trust_score', 0.0)
            risk_indicators = phantombuster_data.get('risk_indicators', [])
            consistency_score = phantombuster_data.get('consistency_score', 0.0)
            
            if trust_score >= 0.85 and consistency_score >= 0.8 and not risk_indicators:
                person.social_verification_status = 'verified'
            elif trust_score >= 0.7 and consistency_score >= 0.6 and len(risk_indicators) <= 1:
                person.social_verification_status = 'needs_review'
            elif trust_score >= 0.5:
                person.social_verification_status = 'unverified'
            else:
                person.social_verification_status = 'suspicious'
            
            # Enhanced avatar handling
            linkedin_analysis = phantombuster_data.get('linkedin_analysis', {})
            linkedin_basic = linkedin_analysis.get('basic_info', {})
            if not person.avatar_url and linkedin_basic.get('profile_image_url'):
                person.avatar_url = linkedin_basic['profile_image_url']
            
            # Mark enrichment as ready for interview
            person.enrichment_progress = {
                'stage': 'completed',
                'progress': 1.0,
                'ready_for_interview': True,
                'completed_at': datetime.now().isoformat()
            }
            
            logger.info(f"PhantomBuster enrichment completed for person {person_id}: Trust score {trust_score:.3f}, Consistency: {consistency_score:.3f}, Status: {person.social_verification_status}")
            
        else:
            person.social_verification_status = 'failed'
            person.enrichment_progress = {
                'stage': 'failed',
                'progress': 0.0,
                'error': last_error,
                'failed_at': datetime.now().isoformat()
            }
            logger.error(f"PhantomBuster enrichment failed after {MAX_RETRIES} attempts for person {person_id}: {last_error}")
        
        # Final commit with results
        db.commit()
        
        # Trigger post-enrichment processing if successful
        if phantombuster_data:
            _trigger_post_enrichment_analysis(person_id, db)
        
    except Exception as e:
        logger.error(f"Critical error in PhantomBuster enrichment for person {person_id}: {e}")
        # Attempt to update status even if there's a critical error
        try:
            person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
            if person:
                person.social_verification_status = 'failed'
                person.enrichment_progress = {
                    'stage': 'failed',
                    'progress': 0.0,
                    'error': str(e),
                    'failed_at': datetime.now().isoformat()
                }
                db.commit()
        except:
            pass
    finally:
        db.close()


def _trigger_post_enrichment_analysis(person_id: int, db: Session):
    """Trigger comprehensive analysis after enrichment completion"""
    try:
        from services.comprehensive_analyzer import comprehensive_analyzer
        
        logger.info(f"Starting post-enrichment analysis for person {person_id}")
        
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if person:
            # Generate comprehensive candidate insights
            insights = comprehensive_analyzer.generate_candidate_insights(person, db)
            
            # Update person with enhanced insights
            if insights:
                person.comprehensive_insights = insights
                db.commit()
                logger.info(f"Comprehensive insights generated for person {person_id}")
            
    except Exception as e:
        logger.error(f"Post-enrichment analysis failed for person {person_id}: {e}")


@router.get("/person/{person_id}/enrichment-status")
def get_enrichment_status(person_id: int, db: Session = Depends(get_db)):
    """Get the current detailed status of enrichment and interview readiness for a person"""
    
    person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    status = person.social_verification_status or 'not_started'
    trust_score = person.trust_score
    has_enrichment_data = bool(person.phantombuster_data)
    progress_data = person.enrichment_progress or {}
    
    # Check interview readiness
    from services.adaptive_interview_engine import adaptive_interview_engine
    interview_ready, interview_status = adaptive_interview_engine.should_start_interview(person)
    
    # Calculate profile completeness
    profile_completeness = 0.0
    if person.profile_completeness_score:
        profile_completeness = person.profile_completeness_score
    else:
        # Calculate basic completeness
        completeness_factors = {
            'resume': 1.0 if person.resume_text and len(person.resume_text) > 200 else 0.5,
            'skills': 1.0 if person.skills_tags and len(person.skills_tags) >= 5 else 0.5,
            'social_profiles': 1.0 if (person.linkedin and person.github) else 0.5,
            'motivation': 1.0 if (person.intro and person.why_us) else 0.5
        }
        profile_completeness = sum(completeness_factors.values()) / len(completeness_factors)
    
    # Prepare comprehensive status
    response_data = {
        "person_id": person_id,
        "enrichment_status": status,
        "trust_score": trust_score,
        "profile_completeness": profile_completeness,
        "has_enrichment_data": has_enrichment_data,
        "has_comprehensive_insights": bool(person.comprehensive_insights),
        "progress": {
            "stage": progress_data.get('stage', 'not_started'),
            "progress_percentage": progress_data.get('progress', 0.0),
            "current_attempt": progress_data.get('attempt', 1),
            "completed_at": progress_data.get('completed_at'),
            "error": progress_data.get('error')
        },
        "interview_readiness": {
            "ready": interview_ready,
            "status_message": interview_status,
            "waiting_for_enrichment": not interview_ready and progress_data.get('stage') in ['processing', 'not_started']
        },
        "status_descriptions": {
            "not_started": "Enrichment has not been initiated",
            "processing": "Currently analyzing LinkedIn and social profiles...",
            "completed": "Enrichment completed successfully",
            "verified": "Profile verified with high trust score",
            "needs_review": "Profile analyzed, manual review recommended", 
            "unverified": "Profile could not be verified",
            "suspicious": "Profile shows concerning inconsistencies",
            "failed": "Enrichment process failed, will retry later"
        },
        "estimated_completion": None
    }
    
    # Set estimated completion time
    if status == "processing":
        attempt = progress_data.get('attempt', 1)
        base_time = 90  # 1.5 minutes base
        additional_time = (attempt - 1) * 60  # Add 1 minute per retry
        total_seconds = base_time + additional_time
        response_data["estimated_completion"] = f"{total_seconds//60}-{(total_seconds+60)//60} minutes"
    
    # Add enrichment insights summary if available
    if person.comprehensive_insights:
        insights = person.comprehensive_insights
        response_data["insights_summary"] = {
            "credibility_score": insights.get('credibility_assessment', {}).get('overall_score', 0.0),
            "job_fit_score": insights.get('job_fit_analysis', {}).get('overall_fit_score', 0.0),
            "red_flags_count": len(insights.get('red_flags', [])),
            "focus_areas": insights.get('interview_recommendations', {}).get('focus_areas', [])
        }
    
    return response_data
