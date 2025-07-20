"""
Sajilo Adaptive Interview router
Manages the enhanced interview flow that waits for enrichment completion
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas import ChatMessage, ChatResponse, ErrorResponse
from database import get_db
from models import ExtendedPerson, ChatTurn, ChatTurnRole, ChatTurnIntent
from services.adaptive_interview_engine import adaptive_interview_engine
from services.chat_engine import chat_engine
from datetime import datetime
from typing import Dict, List
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/interview/{person_id}/start", response_model=ChatResponse, responses={404: {"model": ErrorResponse}})
def start_adaptive_interview(person_id: int, db: Session = Depends(get_db)):
    """Start the adaptive AI interview after enrichment completion"""
    
    try:
        # Get person
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Check if enrichment is ready
        interview_ready, status_message = adaptive_interview_engine.should_start_interview(person)
        
        if not interview_ready:
            raise HTTPException(
                status_code=425, 
                detail={
                    "message": "Interview cannot start yet",
                    "reason": status_message,
                    "enrichment_status": person.social_verification_status,
                    "progress": person.enrichment_progress
                }
            )
        
        # Check if interview already started
        existing_turns = db.query(ChatTurn).filter(
            ChatTurn.person_local_id == person_id
        ).count()
        
        if existing_turns > 0:
            return ChatResponse(
                agent_reply="Interview already in progress. You can continue with the next question.",
                progress=min(existing_turns / 12.0, 1.0),  # Assuming ~12 questions
                turn_count=existing_turns,
                is_complete=existing_turns >= 12
            )
        
        # Generate comprehensive interview plan
        interview_plan = adaptive_interview_engine.generate_interview_plan(person, db)
        
        # Store interview plan in person record for reference
        person.interview_plan = interview_plan
        db.commit()
        
        # Generate initial greeting with context
        greeting = _generate_contextual_greeting(person, interview_plan)
        
        # Create initial AI turn
        initial_turn = ChatTurn(
            person_local_id=person.id,
            turn_index=0,
            role=ChatTurnRole.AI,
            intent=ChatTurnIntent.OTHER,
            content=greeting,
            analysis_json={
                "interview_started": True,
                "planned_questions": interview_plan.get('total_planned_questions', 10),
                "focus_areas": interview_plan.get('focus_areas', [])
            },
            ts=datetime.now()
        )
        
        db.add(initial_turn)
        db.commit()
        
        logger.info(f"Adaptive interview started for person {person_id} with {interview_plan.get('total_planned_questions', 10)} planned questions")
        
        return ChatResponse(
            agent_reply=greeting,
            progress=0.1,
            turn_count=1,
            is_complete=False,
            interview_metadata={
                "total_planned_questions": interview_plan.get('total_planned_questions', 10),
                "focus_areas": interview_plan.get('focus_areas', []),
                "interview_style": "adaptive_comprehensive"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start adaptive interview for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start interview")


@router.post("/interview/{person_id}/continue", response_model=ChatResponse, responses={404: {"model": ErrorResponse}})
def continue_adaptive_interview(person_id: int, message: ChatMessage, db: Session = Depends(get_db)):
    """Continue the adaptive interview with the next question"""
    
    try:
        # Get person
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Get interview plan
        interview_plan = getattr(person, 'interview_plan', None)
        if not interview_plan:
            # Fallback to generating a new plan
            interview_plan = adaptive_interview_engine.generate_interview_plan(person, db)
            person.interview_plan = interview_plan
            db.commit()
        
        # Get chat history
        chat_turns = db.query(ChatTurn).filter(
            ChatTurn.person_local_id == person_id
        ).order_by(ChatTurn.turn_index).all()
        
        # Record user response
        user_turn_index = len(chat_turns)
        user_turn = ChatTurn(
            person_local_id=person.id,
            turn_index=user_turn_index,
            role=ChatTurnRole.USER,
            intent=ChatTurnIntent.OTHER,  # Will be determined by analysis
            content=message.message,
            ts=datetime.now()
        )
        
        db.add(user_turn)
        db.flush()  # Get the ID without committing
        
        # Determine current question number (excluding initial greeting)
        ai_turns = [t for t in chat_turns if t.role == ChatTurnRole.AI]
        current_question_number = len(ai_turns) - 1  # Subtract 1 for initial greeting
        
        # Generate next adaptive question
        question_data = adaptive_interview_engine.generate_adaptive_question(
            person, interview_plan, current_question_number, chat_turns + [user_turn], db
        )
        
        if question_data.get('interview_complete', False):
            # Interview is complete
            completion_message = _generate_completion_message(person, interview_plan, chat_turns)
            
            ai_turn = ChatTurn(
                person_local_id=person.id,
                turn_index=user_turn_index + 1,
                role=ChatTurnRole.AI,
                intent=ChatTurnIntent.OTHER,
                content=completion_message,
                analysis_json={
                    "interview_completed": True,
                    "completion_reason": question_data.get('completion_reason', 'All questions completed'),
                    "total_questions_asked": current_question_number + 1
                },
                ts=datetime.now()
            )
            
            db.add(ai_turn)
            
            # Trigger final AI scoring
            from services.ai_scoring_engine import ai_scoring_engine
            final_score = ai_scoring_engine.compute_ai_score(person, db)
            
            # Update person's last chat timestamp
            person.last_chat_ts = datetime.now()
            db.commit()
            
            return ChatResponse(
                agent_reply=completion_message,
                progress=1.0,
                turn_count=len(chat_turns) + 2,
                is_complete=True,
                final_score={
                    "fit_score": final_score.fit_score,
                    "fit_bucket": final_score.fit_bucket
                }
            )
        
        # Generate next question
        next_question = question_data.get('question', 'Thank you for your response. Can you elaborate further?')
        question_intent = question_data.get('intent', ChatTurnIntent.OTHER)
        
        # Create AI turn with next question
        ai_turn = ChatTurn(
            person_local_id=person.id,
            turn_index=user_turn_index + 1,
            role=ChatTurnRole.AI,
            intent=question_intent,
            content=next_question,
            analysis_json={
                "question_number": question_data.get('question_number', current_question_number + 2),
                "category": question_data.get('category', 'general'),
                "focus_area": question_data.get('focus_area', 'general'),
                "adaptive_context": question_data.get('adaptation_context', {})
            },
            ts=datetime.now()
        )
        
        db.add(ai_turn)
        
        # Update person's last chat timestamp
        person.last_chat_ts = datetime.now()
        db.commit()
        
        # Calculate progress
        total_planned = interview_plan.get('total_planned_questions', 10)
        current_progress = min((current_question_number + 2) / (total_planned + 1), 0.95)  # Never show 100% until complete
        
        logger.info(f"Adaptive interview continued for person {person_id}: question {current_question_number + 2}/{total_planned}")
        
        return ChatResponse(
            agent_reply=next_question,
            progress=current_progress,
            turn_count=len(chat_turns) + 2,
            is_complete=False,
            interview_metadata={
                "current_question": current_question_number + 2,
                "total_planned_questions": total_planned,
                "category": question_data.get('category', 'general'),
                "focus_area": question_data.get('focus_area', 'general')
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Adaptive interview continuation failed for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Interview continuation failed")


@router.get("/interview/{person_id}/plan", responses={404: {"model": ErrorResponse}})
def get_interview_plan(person_id: int, db: Session = Depends(get_db)):
    """Get the current interview plan for a person"""
    
    try:
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        interview_plan = getattr(person, 'interview_plan', None)
        if not interview_plan:
            # Generate plan if not exists
            interview_plan = adaptive_interview_engine.generate_interview_plan(person, db)
        
        return {
            "person_id": person_id,
            "interview_plan": interview_plan,
            "interview_ready": adaptive_interview_engine.should_start_interview(person)[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get interview plan for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve interview plan")


def _generate_contextual_greeting(person: ExtendedPerson, interview_plan: Dict) -> str:
    """Generate personalized greeting based on candidate insights"""
    
    name = person.first_name
    focus_areas = interview_plan.get('focus_areas', [])
    total_questions = interview_plan.get('total_planned_questions', 10)
    
    greeting = f"Hello {name}! Thank you for taking the time to speak with me today. "
    
    # Add context based on enrichment data
    if person.social_verification_status == 'verified':
        greeting += "I've had a chance to review your LinkedIn and GitHub profiles, and I'm impressed by your background. "
    elif person.github_data and person.github_data.get('public_repos', 0) > 5:
        greeting += "I noticed you have an active GitHub presence with some interesting projects. "
    
    # Mention focus areas
    if 'project_deep_dive' in focus_areas:
        greeting += "I'm particularly interested in learning more about the technical projects you've worked on. "
    elif 'leadership_validation' in focus_areas:
        greeting += "Given your experience level, I'd love to hear about your leadership and mentoring experiences. "
    
    greeting += f"I have about {total_questions} questions planned for our conversation today, and I'll be adapting them based on your responses to get the best understanding of your experience and fit for this role. "
    
    greeting += "Let's start with an overview - can you tell me about yourself and what drew you to apply for this position?"
    
    return greeting


def _generate_completion_message(person: ExtendedPerson, interview_plan: Dict, chat_turns: List) -> str:
    """Generate interview completion message"""
    
    name = person.first_name
    questions_asked = len([t for t in chat_turns if t.role == ChatTurnRole.AI and t.turn_index > 0])
    
    completion_message = f"Thank you, {name}! That concludes our interview. "
    completion_message += f"We covered {questions_asked} questions today, and I really appreciate the depth and thoughtfulness of your responses. "
    
    # Add personalized closing based on insights
    if person.comprehensive_insights:
        insights = person.comprehensive_insights
        credibility_score = insights.get('credibility_assessment', {}).get('overall_score', 0.5)
        
        if credibility_score > 0.8:
            completion_message += "Your background and experience come through very clearly, "
        elif credibility_score > 0.6:
            completion_message += "I have a good sense of your technical capabilities, "
        
        job_fit = insights.get('job_fit_analysis', {}).get('overall_fit_score', 0.5)
        if job_fit > 0.7:
            completion_message += "and you seem like you'd be a strong fit for this role. "
        else:
            completion_message += "and I appreciate you taking the time to share your experiences. "
    else:
        completion_message += "Your responses have given me valuable insights into your experience and approach. "
    
    completion_message += "The next steps will be communicated to you by our recruiting team. Have a great day!"
    
    return completion_message
