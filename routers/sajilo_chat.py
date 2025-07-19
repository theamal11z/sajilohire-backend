"""
Sajilo Chat router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import ChatMessage, ChatResponse, ChatHistory, ErrorResponse
from database import get_db
from models import ExtendedPerson, ChatTurn
from services.chat_engine import chat_engine
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat/{person_id}", response_model=ChatResponse, responses={404: {"model": ErrorResponse}})
def chat_with_ai(person_id: int, message: ChatMessage, db: Session = Depends(get_db)):
    """Handle chat interaction with AI interviewer"""
    
    try:
        # Get person
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Get chat history
        chat_turns = db.query(ChatTurn).filter(
            ChatTurn.person_local_id == person_id
        ).order_by(ChatTurn.turn_index).all()
        
        # Generate AI response
        response = chat_engine.generate_response(
            person=person,
            user_message=message.message,
            chat_history=chat_turns,
            db=db
        )
        
        # Update person's last chat timestamp
        person.last_chat_ts = datetime.now()
        db.commit()
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat failed for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Chat processing failed")


@router.get("/chat/{person_id}/history", response_model=ChatHistory, responses={404: {"model": ErrorResponse}})
def get_chat_history(person_id: int, db: Session = Depends(get_db)):
    """Get complete chat history for a person"""
    
    try:
        # Verify person exists
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Get all chat turns
        chat_turns = db.query(ChatTurn).filter(
            ChatTurn.person_local_id == person_id
        ).order_by(ChatTurn.turn_index).all()
        
        return ChatHistory(
            person_id=person_id,
            turns=chat_turns,
            total_turns=len(chat_turns)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat history for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chat history")
