"""
Enhanced Sajilo Candidate Management router
Provides comprehensive candidate management with interview flow integration
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from schemas import ErrorResponse
from database import get_db
from models import ExtendedPerson, ChatTurn, ChatTurnRole
from services.adaptive_interview_engine import adaptive_interview_engine
from services.comprehensive_analyzer import comprehensive_analyzer
from services.scoring_engine import scoring_engine
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/candidate/{person_id}/status", responses={404: {"model": ErrorResponse}})
def get_candidate_comprehensive_status(person_id: int, db: Session = Depends(get_db)):
    """Get comprehensive candidate status including enrichment, interview readiness, and insights"""
    
    try:
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Get enrichment status
        enrichment_progress = person.enrichment_progress or {}
        enrichment_stage = enrichment_progress.get('stage', 'not_started')
        
        # Get interview readiness
        interview_ready, interview_status_message = adaptive_interview_engine.should_start_interview(person)
        
        # Get interview statistics
        interview_stats = _get_detailed_interview_stats(person, db)
        
        # Get comprehensive insights
        insights_available = bool(person.comprehensive_insights)
        insights_summary = {}
        if person.comprehensive_insights:
            insights_summary = _extract_candidate_insights_summary(person.comprehensive_insights)
        
        # Calculate profile completeness
        profile_completeness = person.profile_completeness_score
        if not profile_completeness:
            profile_completeness = _calculate_profile_completeness(person)
            person.profile_completeness_score = profile_completeness
            db.commit()
        
        # Get scoring status
        scoring_status = _get_scoring_status(person, db)
        
        return {
            "person_id": person_id,
            "basic_info": {
                "full_name": f"{person.first_name} {person.last_name}",
                "email": person.email,
                "applied_at": person.created_ts,
                "last_activity": person.last_chat_ts or person.created_ts
            },
            "enrichment": {
                "status": person.social_verification_status or 'not_started',
                "stage": enrichment_stage,
                "progress": enrichment_progress.get('progress', 0.0),
                "trust_score": person.trust_score,
                "error": enrichment_progress.get('error'),
                "completed_at": enrichment_progress.get('completed_at'),
                "ready_for_interview": enrichment_progress.get('ready_for_interview', False)
            },
            "profile_analysis": {
                "completeness_score": profile_completeness,
                "has_resume": bool(person.resume_text),
                "resume_length": len(person.resume_text) if person.resume_text else 0,
                "skills_count": len(person.skills_tags) if person.skills_tags else 0,
                "has_linkedin": bool(person.linkedin),
                "has_github": bool(person.github),
                "github_repos": person.github_data.get('public_repos', 0) if person.github_data else 0,
                "social_verification": person.social_verification_status
            },
            "interview": {
                "ready": interview_ready,
                "status_message": interview_status_message,
                "statistics": interview_stats,
                "has_plan": bool(person.interview_plan),
                "plan_summary": _get_interview_plan_summary(person.interview_plan) if person.interview_plan else None
            },
            "insights": {
                "available": insights_available,
                "summary": insights_summary
            },
            "scoring": scoring_status
        }
        
    except Exception as e:
        logger.error(f"Failed to get candidate status for {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve candidate status")


@router.post("/candidate/{person_id}/trigger-enrichment", responses={404: {"model": ErrorResponse}})
def trigger_candidate_enrichment(person_id: int, db: Session = Depends(get_db)):
    """Manually trigger enrichment analysis for a candidate"""
    
    try:
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Check if already in progress
        enrichment_progress = person.enrichment_progress or {}
        if enrichment_progress.get('stage') == 'processing':
            return {
                "message": "Enrichment already in progress",
                "current_progress": enrichment_progress.get('progress', 0.0)
            }
        
        # Generate comprehensive insights if PhantomBuster data is available
        if person.phantombuster_data or person.github_data:
            logger.info(f"Generating comprehensive insights for person {person_id}")
            
            try:
                insights = comprehensive_analyzer.generate_candidate_insights(person, db)
                if insights:
                    person.comprehensive_insights = insights
                    
                    # Update enrichment progress
                    person.enrichment_progress = {
                        'stage': 'completed',
                        'progress': 1.0,
                        'ready_for_interview': True,
                        'completed_at': datetime.now().isoformat(),
                        'manually_triggered': True
                    }
                    
                    # Update profile completeness
                    if not person.profile_completeness_score:
                        person.profile_completeness_score = _calculate_profile_completeness(person)
                    
                    db.commit()
                    
                    return {
                        "message": "Enrichment analysis completed successfully",
                        "insights_generated": True,
                        "ready_for_interview": True
                    }
                
            except Exception as e:
                logger.error(f"Failed to generate insights for person {person_id}: {e}")
                return {
                    "message": "Enrichment analysis failed",
                    "error": str(e),
                    "insights_generated": False
                }
        
        return {
            "message": "Insufficient data for enrichment analysis",
            "suggestion": "Ensure LinkedIn and GitHub profiles are provided and PhantomBuster enrichment is complete"
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger enrichment for {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger enrichment")


@router.get("/candidate/{person_id}/interview-readiness", responses={404: {"model": ErrorResponse}})
def check_interview_readiness(person_id: int, db: Session = Depends(get_db)):
    """Check if candidate is ready for interview and get detailed readiness information"""
    
    try:
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Check interview readiness
        interview_ready, status_message = adaptive_interview_engine.should_start_interview(person)
        
        # Get current interview progress if any
        current_interview = _get_current_interview_progress(person, db)
        
        # Generate readiness checklist
        readiness_checklist = _generate_readiness_checklist(person)
        
        # Get interview recommendations
        interview_recommendations = {}
        if person.comprehensive_insights:
            insights = person.comprehensive_insights
            interview_recommendations = insights.get('interview_recommendations', {})
        
        return {
            "person_id": person_id,
            "ready_for_interview": interview_ready,
            "status_message": status_message,
            "current_interview": current_interview,
            "readiness_checklist": readiness_checklist,
            "interview_recommendations": interview_recommendations,
            "estimated_interview_duration": "15-25 minutes",
            "interview_type": "adaptive_comprehensive" if interview_ready else "basic_fallback"
        }
        
    except Exception as e:
        logger.error(f"Failed to check interview readiness for {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to check interview readiness")


@router.post("/candidate/{person_id}/prepare-interview", responses={404: {"model": ErrorResponse}})
def prepare_candidate_interview(person_id: int, force: bool = Query(False, description="Force interview preparation even if not ready"), db: Session = Depends(get_db)):
    """Prepare interview plan and return readiness confirmation"""
    
    try:
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Check readiness
        interview_ready, status_message = adaptive_interview_engine.should_start_interview(person)
        
        if not interview_ready and not force:
            return {
                "prepared": False,
                "reason": status_message,
                "enrichment_status": person.social_verification_status,
                "suggestion": "Wait for enrichment to complete or use force=true to proceed with basic interview"
            }
        
        # Generate interview plan
        interview_plan = adaptive_interview_engine.generate_interview_plan(person, db)
        
        # Store the plan
        person.interview_plan = interview_plan
        db.commit()
        
        return {
            "prepared": True,
            "interview_plan_summary": {
                "total_questions": interview_plan.get('total_planned_questions', 8),
                "categories": list(interview_plan.get('categories', {}).keys()),
                "focus_areas": interview_plan.get('focus_areas', []),
                "red_flags_to_probe": interview_plan.get('red_flags_to_probe', [])
            },
            "interview_type": "adaptive" if interview_ready else "basic",
            "estimated_duration": f"{interview_plan.get('total_planned_questions', 8) * 2}-{interview_plan.get('total_planned_questions', 8) * 3} minutes"
        }
        
    except Exception as e:
        logger.error(f"Failed to prepare interview for {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to prepare interview")


@router.get("/candidate/{person_id}/scoring-analysis", responses={404: {"model": ErrorResponse}})
def get_candidate_scoring_analysis(person_id: int, db: Session = Depends(get_db)):
    """Get detailed scoring analysis and breakdown for a candidate"""
    
    try:
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Ensure scoring is complete
        if not person.score or not person.signals:
            scoring_engine.compute_score(person, db)
            db.refresh(person)
        
        if not person.score or not person.signals:
            return {
                "person_id": person_id,
                "scoring_available": False,
                "message": "Insufficient data for scoring analysis"
            }
        
        # Get job profile for context
        from services.job_profile_service import job_profile_analyzer
        job_profile = job_profile_analyzer.get_comprehensive_job_profile(person.job_id, db)
        
        # Detailed scoring breakdown
        scoring_breakdown = {
            "overall": {
                "fit_score": person.score.fit_score,
                "fit_bucket": person.score.fit_bucket,
                "computed_at": person.score.computed_at
            },
            "components": {
                "consistency_score": person.signals.consistency_score,
                "depth_score": person.signals.depth_score,
                "motivation_alignment": person.signals.motivation_alignment,
                "culture_alignment": person.signals.culture_alignment,
                "turnover_risk": person.signals.turnover_risk,
                "data_confidence": person.signals.data_confidence
            },
            "flags": {
                "credibility_flag": person.signals.credibility_flag,
                "flags": person.signals.flags or [],
                "risk_indicators": []
            }
        }
        
        # Add risk indicators from PhantomBuster
        if person.phantombuster_data:
            scoring_breakdown["flags"]["risk_indicators"] = person.phantombuster_data.get('risk_indicators', [])
        
        # Job-specific analysis
        job_fit_analysis = {}
        if job_profile and person.comprehensive_insights:
            insights = person.comprehensive_insights
            job_fit_analysis = insights.get('job_fit_analysis', {})
        
        # Recommendations based on scoring
        recommendations = _generate_scoring_recommendations(scoring_breakdown, job_fit_analysis)
        
        return {
            "person_id": person_id,
            "scoring_available": True,
            "breakdown": scoring_breakdown,
            "job_fit_analysis": job_fit_analysis,
            "recommendations": recommendations,
            "analysis_confidence": person.signals.data_confidence,
            "last_updated": person.signals.updated_at
        }
        
    except Exception as e:
        logger.error(f"Failed to get scoring analysis for {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scoring analysis")


def _get_detailed_interview_stats(person: ExtendedPerson, db: Session) -> Dict[str, Any]:
    """Get detailed interview statistics"""
    chat_turns = db.query(ChatTurn).filter(ChatTurn.person_local_id == person.id).all()
    
    if not chat_turns:
        return {
            "status": "not_started",
            "total_turns": 0,
            "questions_answered": 0,
            "completion_percentage": 0.0,
            "interview_type": "none",
            "planned_questions": 0,
            "avg_response_length": 0,
            "categories_covered": []
        }
    
    user_turns = [t for t in chat_turns if t.role == ChatTurnRole.USER]
    ai_turns = [t for t in chat_turns if t.role == ChatTurnRole.AI]
    
    # Calculate response statistics
    response_lengths = [len(turn.content.split()) for turn in user_turns]
    avg_response_length = sum(response_lengths) / len(response_lengths) if response_lengths else 0
    
    # Extract categories covered
    categories_covered = []
    for turn in ai_turns:
        if turn.analysis_json and isinstance(turn.analysis_json, dict):
            category = turn.analysis_json.get('category')
            if category and category not in categories_covered:
                categories_covered.append(category)
    
    # Determine interview type and progress
    if person.interview_plan:
        planned_questions = person.interview_plan.get('total_planned_questions', 10)
        interview_type = 'adaptive'
    else:
        planned_questions = 5
        interview_type = 'legacy'
    
    questions_answered = len(user_turns)
    completion_percentage = min(questions_answered / planned_questions, 1.0)
    
    if completion_percentage >= 1.0:
        status = 'completed'
    elif completion_percentage > 0:
        status = 'in_progress'
    else:
        status = 'not_started'
    
    return {
        "status": status,
        "total_turns": len(chat_turns),
        "questions_answered": questions_answered,
        "completion_percentage": completion_percentage,
        "interview_type": interview_type,
        "planned_questions": planned_questions,
        "avg_response_length": avg_response_length,
        "categories_covered": categories_covered,
        "last_interaction": chat_turns[-1].ts if chat_turns else None
    }


def _extract_candidate_insights_summary(comprehensive_insights: Dict[str, Any]) -> Dict[str, Any]:
    """Extract summary of comprehensive insights for candidate status"""
    if not comprehensive_insights:
        return {"available": False}
    
    return {
        "available": True,
        "credibility_score": comprehensive_insights.get('credibility_assessment', {}).get('overall_score', 0.0),
        "job_fit_score": comprehensive_insights.get('job_fit_analysis', {}).get('overall_fit_score', 0.0),
        "experience_level": comprehensive_insights.get('experience_analysis', {}).get('estimated_experience_level', 'unknown'),
        "red_flags_count": len(comprehensive_insights.get('red_flags', [])),
        "focus_areas": comprehensive_insights.get('interview_recommendations', {}).get('focus_areas', []),
        "generated_at": comprehensive_insights.get('generated_at', 'unknown')
    }


def _calculate_profile_completeness(person: ExtendedPerson) -> float:
    """Calculate comprehensive profile completeness score"""
    factors = {
        "basic_info": 1.0,  # Always complete
        "resume_quality": 0.0,
        "skills_depth": 0.0,
        "social_presence": 0.0,
        "motivation_clarity": 0.0,
        "enrichment_data": 0.0
    }
    
    # Resume quality
    if person.resume_text:
        resume_length = len(person.resume_text)
        factors["resume_quality"] = min(resume_length / 1500, 1.0)
    
    # Skills depth
    if person.skills_tags:
        skill_count = len(person.skills_tags)
        factors["skills_depth"] = min(skill_count / 10, 1.0)
    
    # Social presence
    social_score = 0
    if person.linkedin:
        social_score += 0.3
    if person.github:
        social_score += 0.3
    if person.github_data:
        social_score += 0.2
    if person.phantombuster_data:
        social_score += 0.2
    factors["social_presence"] = min(social_score, 1.0)
    
    # Motivation clarity
    motivation_score = 0
    if person.intro and len(person.intro) > 100:
        motivation_score += 0.5
    if person.why_us and len(person.why_us) > 100:
        motivation_score += 0.5
    factors["motivation_clarity"] = motivation_score
    
    # Enrichment data
    enrichment_score = 0
    if person.trust_score:
        enrichment_score += 0.4
    if person.comprehensive_insights:
        enrichment_score += 0.6
    factors["enrichment_data"] = enrichment_score
    
    return sum(factors.values()) / len(factors)


def _get_scoring_status(person: ExtendedPerson, db: Session) -> Dict[str, Any]:
    """Get comprehensive scoring status"""
    if not person.score:
        return {
            "available": False,
            "message": "Scoring not yet computed"
        }
    
    return {
        "available": True,
        "fit_score": person.score.fit_score,
        "fit_bucket": person.score.fit_bucket,
        "computed_at": person.score.computed_at,
        "signals_available": bool(person.signals),
        "confidence_level": person.signals.data_confidence if person.signals else 0.0
    }


def _get_interview_plan_summary(interview_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Get summary of interview plan"""
    return {
        "total_questions": interview_plan.get('total_planned_questions', 0),
        "categories": interview_plan.get('categories', {}),
        "focus_areas": interview_plan.get('focus_areas', []),
        "generated_at": interview_plan.get('generated_at', 'unknown')
    }


def _get_current_interview_progress(person: ExtendedPerson, db: Session) -> Dict[str, Any]:
    """Get current interview progress if any"""
    chat_turns = db.query(ChatTurn).filter(ChatTurn.person_local_id == person.id).all()
    
    if not chat_turns:
        return {"status": "not_started"}
    
    user_turns = [t for t in chat_turns if t.role == ChatTurnRole.USER]
    
    # Check if interview is complete
    if person.interview_plan:
        planned_questions = person.interview_plan.get('total_planned_questions', 10)
        current_progress = len(user_turns) / planned_questions
        
        if current_progress >= 1.0:
            return {
                "status": "completed",
                "questions_answered": len(user_turns),
                "total_planned": planned_questions,
                "completion_date": chat_turns[-1].ts
            }
        elif current_progress > 0:
            return {
                "status": "in_progress",
                "questions_answered": len(user_turns),
                "total_planned": planned_questions,
                "progress_percentage": current_progress,
                "next_question_category": "unknown"  # Could be enhanced
            }
    
    return {"status": "started_but_no_plan"}


def _generate_readiness_checklist(person: ExtendedPerson) -> Dict[str, Any]:
    """Generate interview readiness checklist"""
    checklist = {
        "enrichment_complete": False,
        "profile_data_sufficient": False,
        "insights_generated": False,
        "scoring_possible": False,
        "ready_items": [],
        "pending_items": []
    }
    
    # Check enrichment
    enrichment_progress = person.enrichment_progress or {}
    if enrichment_progress.get('stage') == 'completed':
        checklist["enrichment_complete"] = True
        checklist["ready_items"].append("Profile enrichment completed")
    else:
        checklist["pending_items"].append("Waiting for profile enrichment to complete")
    
    # Check profile data
    profile_score = person.profile_completeness_score or _calculate_profile_completeness(person)
    if profile_score >= 0.6:
        checklist["profile_data_sufficient"] = True
        checklist["ready_items"].append("Profile data is sufficient for interview")
    else:
        checklist["pending_items"].append("Profile data needs improvement")
    
    # Check insights
    if person.comprehensive_insights:
        checklist["insights_generated"] = True
        checklist["ready_items"].append("Comprehensive insights available")
    else:
        checklist["pending_items"].append("Comprehensive insights not yet generated")
    
    # Check scoring capability
    if person.resume_text and person.skills_tags:
        checklist["scoring_possible"] = True
        checklist["ready_items"].append("Sufficient data for scoring")
    else:
        checklist["pending_items"].append("Need resume and skills data for scoring")
    
    return checklist


def _generate_scoring_recommendations(scoring_breakdown: Dict[str, Any], job_fit_analysis: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on scoring analysis"""
    recommendations = []
    
    components = scoring_breakdown.get('components', {})
    overall = scoring_breakdown.get('overall', {})
    
    # Overall fit recommendations
    fit_score = overall.get('fit_score', 0)
    if fit_score >= 0.8:
        recommendations.append("Strong candidate - recommend for next round")
    elif fit_score >= 0.6:
        recommendations.append("Good candidate - consider for interview")
    else:
        recommendations.append("Below threshold - review carefully")
    
    # Specific component recommendations
    if components.get('depth_score', 0) < 0.5:
        recommendations.append("Ask more detailed technical questions in interview")
    
    if components.get('consistency_score', 0) < 0.6:
        recommendations.append("Probe for consistency in experience claims")
    
    if components.get('motivation_alignment', 0) < 0.6:
        recommendations.append("Focus on motivation and cultural fit questions")
    
    if components.get('turnover_risk', 0) > 0.7:
        recommendations.append("Assess long-term commitment and career stability")
    
    # Credibility flags
    if scoring_breakdown.get('flags', {}).get('credibility_flag', False):
        recommendations.append("⚠️ Verify credentials and experience claims")
    
    risk_indicators = scoring_breakdown.get('flags', {}).get('risk_indicators', [])
    if risk_indicators:
        recommendations.append(f"⚠️ Address risk indicators: {', '.join(risk_indicators[:3])}")
    
    return recommendations
