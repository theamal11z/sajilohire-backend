"""
Sajilo Person Extend router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import PersonExtend, PersonResponse, ErrorResponse
from database import get_db
from models import ExtendedPerson
from datetime import datetime
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
        
        db.commit()
        db.refresh(person)
        
        logger.info(f"Extended person {person_id} with job {person_extend.job_id}")
        return person
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to extend person {person_id}: {e}")
        raise HTTPException(status_code=400, detail="Failed to extend person")
