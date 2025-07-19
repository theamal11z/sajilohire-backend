"""
Sajilo Person router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import PersonCreate, PersonResponse, ErrorResponse
from database import get_db
from models import ExtendedPerson
from aqore_client import aqore_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/person", response_model=PersonResponse, responses={400: {"model": ErrorResponse}})
def create_person(person_in: PersonCreate, db: Session = Depends(get_db)):
    """Create a new extended person and optionally sync upstream"""
    
    try:
        # Create local ExtendedPerson
        new_person = ExtendedPerson(
            first_name=person_in.first_name,
            last_name=person_in.last_name,
            email=person_in.email,
            phone=person_in.phone,
            job_id=person_in.job_id
        )
        db.add(new_person)
        db.commit()
        db.refresh(new_person)
        
        return new_person
        
    except Exception as e:
        logger.error(f"Failed to create person: {e}")
        raise HTTPException(status_code=400, detail="Failed to create person")
