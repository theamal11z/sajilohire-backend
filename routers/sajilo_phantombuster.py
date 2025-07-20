"""
PhantomBuster Analysis Router
Handles comprehensive candidate analysis using PhantomBuster data and OpenAI insights
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from database import get_db
from models import ExtendedPerson
from services.phantombuster_enrichment import phantombuster_enrichment_service
from services.comprehensive_analyzer import ComprehensiveAnalyzer
from services.openai_cross_platform_analyzer import openai_cross_platform_analyzer
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()
comprehensive_analyzer = ComprehensiveAnalyzer()


@router.get("/phantombuster-analysis/{person_id}")
async def get_phantombuster_analysis(
    person_id: int,
    refresh: bool = Query(False, description="Force refresh of PhantomBuster data"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive PhantomBuster analysis for a candidate
    Includes social intelligence, cross-platform verification, and AI insights
    """
    try:
        # Get person from database
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Check if we need to refresh PhantomBuster data
        should_refresh = refresh or not person.phantombuster_data
        
        if should_refresh:
            logger.info(f"Refreshing PhantomBuster data for person {person_id}")
            
            # Enrich with PhantomBuster data
            enrichment_data = phantombuster_enrichment_service.enrich_candidate_profile(
                linkedin_url=person.linkedin,
                github_url=person.github
            )
            
            # Update person with new data
            person.phantombuster_data = enrichment_data
            person.trust_score = enrichment_data.get('trust_score', 0.5)
            person.social_verification_status = _determine_verification_status(enrichment_data)
            
            db.commit()
            logger.info(f"PhantomBuster data refreshed for person {person_id}")
        
        # Generate comprehensive insights
        comprehensive_insights = comprehensive_analyzer.generate_candidate_insights(person, db)
        
        # Generate AI-powered detailed analysis using OpenAI
        ai_analysis = await _generate_ai_detailed_analysis(person, comprehensive_insights)
        
        return {
            "person_id": person_id,
            "candidate_info": {
                "name": f"{person.first_name} {person.last_name}",
                "email": person.email,
                "linkedin": person.linkedin,
                "github": person.github,
                "trust_score": person.trust_score,
                "verification_status": person.social_verification_status
            },
            "phantombuster_data": person.phantombuster_data or {},
            "comprehensive_insights": comprehensive_insights,
            "ai_detailed_analysis": ai_analysis,
            "conversation_history": _get_conversation_summary(person),
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "recommendations": _generate_hr_recommendations(person, comprehensive_insights, ai_analysis)
        }
        
    except Exception as e:
        logger.error(f"PhantomBuster analysis failed for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/phantombuster-analysis/{person_id}/trigger-enrichment")
async def trigger_phantombuster_enrichment(
    person_id: int,
    background_tasks: BackgroundTasks,
    force_refresh: bool = Query(False, description="Force refresh even if data exists"),
    db: Session = Depends(get_db)
):
    """
    Trigger PhantomBuster enrichment for a candidate in the background
    """
    try:
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Add background task for enrichment
        background_tasks.add_task(
            _background_phantombuster_enrichment,
            person_id, force_refresh, db
        )
        
        return {
            "message": "PhantomBuster enrichment triggered",
            "person_id": person_id,
            "status": "processing",
            "estimated_completion": "2-5 minutes"
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger PhantomBuster enrichment for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Enrichment trigger failed: {str(e)}")


@router.get("/phantombuster-analysis/{person_id}/status")
async def get_enrichment_status(
    person_id: int,
    db: Session = Depends(get_db)
):
    """
    Get current enrichment status for a candidate
    """
    try:
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        has_phantombuster_data = bool(person.phantombuster_data)
        enrichment_progress = person.enrichment_progress or {}
        
        return {
            "person_id": person_id,
            "enrichment_status": "completed" if has_phantombuster_data else "not_started",
            "has_phantombuster_data": has_phantombuster_data,
            "trust_score": person.trust_score,
            "verification_status": person.social_verification_status,
            "enrichment_progress": enrichment_progress,
            "last_updated": person.created_ts.isoformat() if person.created_ts else None
        }
        
    except Exception as e:
        logger.error(f"Failed to get enrichment status for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


async def _generate_ai_detailed_analysis(person: ExtendedPerson, comprehensive_insights: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate detailed AI analysis combining all available data
    """
    try:
        # Prepare comprehensive data for AI analysis
        analysis_data = {
            "basic_info": {
                "name": f"{person.first_name} {person.last_name}",
                "email": person.email,
                "linkedin": person.linkedin,
                "github": person.github
            },
            "resume_analysis": person.resume_text[:1000] if person.resume_text else "",
            "skills": person.skills_tags or [],
            "motivation": {
                "intro": person.intro or "",
                "why_us": person.why_us or ""
            },
            "phantombuster_data": person.phantombuster_data or {},
            "comprehensive_insights": comprehensive_insights,
            "conversation_history": _get_conversation_summary(person)
        }
        
        # Build comprehensive analysis prompt
        prompt = _build_comprehensive_analysis_prompt(analysis_data)
        
        # Call OpenAI for detailed analysis
        response = openai_cross_platform_analyzer._call_openai_api(prompt)
        
        if response:
            return _parse_ai_analysis_response(response)
        else:
            return _get_default_ai_analysis()
            
    except Exception as e:
        logger.error(f"AI detailed analysis failed: {e}")
        return _get_default_ai_analysis()


def _build_comprehensive_analysis_prompt(analysis_data: Dict[str, Any]) -> str:
    """
    Build comprehensive analysis prompt for OpenAI
    """
    basic_info = analysis_data.get("basic_info", {})
    phantombuster = analysis_data.get("phantombuster_data", {})
    insights = analysis_data.get("comprehensive_insights", {})
    conversation = analysis_data.get("conversation_history", {})
    
    prompt = f"""
You are an expert HR analyst and recruitment consultant. Provide a comprehensive analysis of this candidate based on all available data sources.

CANDIDATE PROFILE:
- Name: {basic_info.get('name', 'Not provided')}
- Email: {basic_info.get('email', 'Not provided')}
- LinkedIn: {basic_info.get('linkedin', 'Not provided')}
- GitHub: {basic_info.get('github', 'Not provided')}

RESUME SUMMARY:
{analysis_data.get('resume_analysis', 'No resume available')[:500]}

SKILLS:
{', '.join(analysis_data.get('skills', []))}

MOTIVATION & PERSONALITY:
- Introduction: {analysis_data.get('motivation', {}).get('intro', 'Not provided')[:200]}
- Why this company: {analysis_data.get('motivation', {}).get('why_us', 'Not provided')[:200]}

SOCIAL INTELLIGENCE DATA:
- Trust Score: {phantombuster.get('trust_score', 'Not available')}
- Professional Insights: {phantombuster.get('professional_insights', {})}
- Risk Indicators: {phantombuster.get('risk_indicators', [])}

COMPREHENSIVE INSIGHTS:
- Profile Completeness: {insights.get('profile_analysis', {}).get('overall_score', 'Not available')}
- Skill Analysis: {insights.get('skill_analysis', {})}
- Experience Analysis: {insights.get('experience_analysis', {})}
- Credibility Assessment: {insights.get('credibility_assessment', {})}

CONVERSATION HISTORY SUMMARY:
- Total Messages: {conversation.get('total_messages', 0)}
- Key Topics Discussed: {conversation.get('topics', [])}
- Candidate Responses Quality: {conversation.get('response_quality', 'Not assessed')}

ANALYSIS TASK:
Provide a comprehensive hiring recommendation covering:
1. Overall Candidate Assessment (score 0-100)
2. Strengths and Key Advantages
3. Potential Concerns or Red Flags
4. Technical Competency Assessment
5. Cultural Fit Evaluation
6. Personality and Motivation Analysis
7. Interview Recommendations
8. Final Hiring Recommendation (Strong Hire / Hire / No Hire / Strong No Hire)

Please structure your response as detailed, actionable insights that an HR manager can use to make informed hiring decisions.
"""
    return prompt


def _parse_ai_analysis_response(response: str) -> Dict[str, Any]:
    """
    Parse AI analysis response into structured format
    """
    return {
        "overall_assessment": _extract_section(response, "Overall Candidate Assessment"),
        "strengths": _extract_section(response, "Strengths"),
        "concerns": _extract_section(response, "Concerns", "Red Flags"),
        "technical_competency": _extract_section(response, "Technical Competency"),
        "cultural_fit": _extract_section(response, "Cultural Fit"),
        "personality_analysis": _extract_section(response, "Personality", "Motivation"),
        "interview_recommendations": _extract_section(response, "Interview Recommendations"),
        "final_recommendation": _extract_section(response, "Final", "Hiring Recommendation"),
        "raw_analysis": response,
        "analysis_timestamp": datetime.utcnow().isoformat()
    }


def _extract_section(text: str, *keywords) -> str:
    """
    Extract specific section from AI response
    """
    text_lower = text.lower()
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in text_lower:
            start_idx = text_lower.find(keyword_lower)
            # Find next section or end of text
            next_section_start = len(text)
            for next_keyword in ["strengths", "concerns", "technical", "cultural", "personality", "interview", "final"]:
                if next_keyword != keyword_lower:
                    next_idx = text_lower.find(next_keyword, start_idx + len(keyword_lower))
                    if next_idx > start_idx and next_idx < next_section_start:
                        next_section_start = next_idx
            
            section_text = text[start_idx:next_section_start].strip()
            return section_text[:500]  # Limit length
    
    return "Analysis not available"


def _get_default_ai_analysis() -> Dict[str, Any]:
    """
    Default analysis when AI analysis fails
    """
    return {
        "overall_assessment": "AI analysis unavailable - manual review recommended",
        "strengths": "Unable to determine automatically",
        "concerns": "Manual verification required",
        "technical_competency": "Requires technical interview",
        "cultural_fit": "Needs behavioral assessment",
        "personality_analysis": "In-person evaluation recommended",
        "interview_recommendations": "Standard technical and behavioral interview",
        "final_recommendation": "Manual review required",
        "raw_analysis": "AI analysis service unavailable",
        "analysis_timestamp": datetime.utcnow().isoformat()
    }


def _get_conversation_summary(person: ExtendedPerson) -> Dict[str, Any]:
    """
    Summarize conversation history for analysis
    """
    if not person.chat_turns:
        return {"total_messages": 0, "topics": [], "response_quality": "No conversation data"}
    
    total_messages = len(person.chat_turns)
    user_messages = [turn for turn in person.chat_turns if turn.role.value == "user"]
    
    topics = []
    for turn in user_messages:
        if turn.intent and turn.intent.value != "other":
            topics.append(turn.intent.value)
    
    return {
        "total_messages": total_messages,
        "user_responses": len(user_messages),
        "topics": list(set(topics)),
        "response_quality": "Good" if len(user_messages) > 3 else "Limited",
        "last_interaction": person.last_chat_ts.isoformat() if person.last_chat_ts else None
    }


def _determine_verification_status(enrichment_data: Dict[str, Any]) -> str:
    """
    Determine verification status based on enrichment data
    """
    trust_score = enrichment_data.get('trust_score', 0.0)
    risk_indicators = enrichment_data.get('risk_indicators', [])
    
    if trust_score >= 0.8 and len(risk_indicators) == 0:
        return "verified"
    elif trust_score >= 0.6 and len(risk_indicators) <= 1:
        return "needs_review"
    elif len(risk_indicators) > 2:
        return "suspicious"
    else:
        return "unverified"


def _generate_hr_recommendations(person: ExtendedPerson, insights: Dict[str, Any], ai_analysis: Dict[str, Any]) -> List[str]:
    """
    Generate actionable HR recommendations
    """
    recommendations = []
    
    trust_score = person.trust_score or 0.0
    
    if trust_score >= 0.8:
        recommendations.append("✅ High trust score - proceed with technical interview")
    elif trust_score >= 0.6:
        recommendations.append("⚠️ Moderate trust - verify key claims during interview")
    else:
        recommendations.append("🚨 Low trust score - conduct thorough background check")
    
    # Add specific recommendations based on insights
    profile_score = insights.get('profile_analysis', {}).get('overall_score', 0)
    if profile_score < 0.7:
        recommendations.append("📝 Request additional portfolio/work samples")
    
    skill_analysis = insights.get('skill_analysis', {})
    if skill_analysis.get('job_requirements_analysis', {}).get('mandatory_match', {}).get('coverage', 0) < 0.8:
        recommendations.append("🔧 Focus technical interview on missing mandatory skills")
    
    conversation_summary = _get_conversation_summary(person)
    if conversation_summary.get('total_messages', 0) < 5:
        recommendations.append("💬 Conduct extended behavioral interview - limited conversation data")
    
    return recommendations


async def _background_phantombuster_enrichment(person_id: int, force_refresh: bool, db: Session):
    """
    Background task for PhantomBuster enrichment
    """
    try:
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            return
        
        if not force_refresh and person.phantombuster_data:
            return
        
        # Update enrichment progress
        person.enrichment_progress = {"status": "processing", "started_at": datetime.utcnow().isoformat()}
        db.commit()
        
        # Perform enrichment
        enrichment_data = phantombuster_enrichment_service.enrich_candidate_profile(
            linkedin_url=person.linkedin,
            github_url=person.github
        )
        
        # Update person with enriched data
        person.phantombuster_data = enrichment_data
        person.trust_score = enrichment_data.get('trust_score', 0.5)
        person.social_verification_status = _determine_verification_status(enrichment_data)
        person.enrichment_progress = {
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat()
        }
        
        db.commit()
        logger.info(f"Background PhantomBuster enrichment completed for person {person_id}")
        
    except Exception as e:
        logger.error(f"Background PhantomBuster enrichment failed for person {person_id}: {e}")
        person.enrichment_progress = {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat()
        }
        db.commit()
