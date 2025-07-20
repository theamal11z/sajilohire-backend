"""
AI-powered scoring engine using OpenAI for comprehensive candidate evaluation
"""

import json
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from openai import AzureOpenAI

from models import ExtendedPerson, CandidateSignals, CandidateScore, ChatTurn, ChatTurnRole
from services.job_profile_service import job_profile_analyzer
from config import settings

logger = logging.getLogger(__name__)


class AIScoreEngine:
    """AI-powered scoring engine using OpenAI for comprehensive evaluation"""
    
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=settings.GPT_API_ENDPOINT.split('/openai')[0],
            api_key=settings.GPT_API_KEY,
            api_version="2025-01-01-preview"
        )
        self.model = settings.GPT_MODEL
        
    def compute_ai_score(self, person: ExtendedPerson, db: Session) -> CandidateScore:
        """Compute comprehensive AI-powered fit score for candidate"""
        
        # Gather all available data about the candidate
        candidate_data = self._gather_candidate_data(person, db)
        
        # Get job profile for context
        job_profile = job_profile_analyzer.get_comprehensive_job_profile(person.job_id, db)
        
        # Create comprehensive prompt for AI analysis
        analysis_prompt = self._create_scoring_prompt(candidate_data, job_profile)
        
        try:
            # Get AI analysis
            ai_response = self._call_openai_for_scoring(analysis_prompt)
            
            # Parse the structured response
            scoring_result = self._parse_ai_scoring_response(ai_response)
            
            # Create or update score record
            score = self._save_score_to_database(person, scoring_result, db)
            
            # Also update signals based on AI analysis
            self._update_signals_from_ai_analysis(person, scoring_result, db)
            
            logger.info(f"AI scoring completed for person {person.id}: {scoring_result['overall_fit_score']:.3f}")
            return score
            
        except Exception as e:
            logger.error(f"AI scoring failed for person {person.id}: {e}")
            # Fallback to basic scoring if AI fails
            return self._fallback_basic_score(person, db)
    
    def _gather_candidate_data(self, person: ExtendedPerson, db: Session) -> Dict[str, Any]:
        """Gather comprehensive candidate data for AI analysis"""
        
        # Basic profile data
        profile_data = {
            "basic_info": {
                "name": f"{person.first_name} {person.last_name}",
                "email": person.email,
                "phone": person.phone,
                "job_id": person.job_id
            },
            "profile_content": {
                "resume_text": person.resume_text or "",
                "intro": person.intro or "",
                "why_us": person.why_us or "",
                "skills_tags": person.skills_tags or []
            },
            "social_profiles": {
                "linkedin": person.linkedin,
                "github": person.github,
                "github_data": person.github_data,
                "avatar_url": person.avatar_url
            },
            "trust_metrics": {
                "trust_score": person.trust_score,
                "social_verification_status": person.social_verification_status
            }
        }
        
        # Chat conversation data
        chat_turns = db.query(ChatTurn).filter(
            ChatTurn.person_local_id == person.id
        ).order_by(ChatTurn.turn_index).all()
        
        conversation_data = []
        for turn in chat_turns:
            conversation_data.append({
                "role": turn.role.value if turn.role else "unknown",
                "intent": turn.intent.value if turn.intent else "other",
                "content": turn.content,
                "timestamp": turn.ts.isoformat() if turn.ts else None,
                "analysis": turn.analysis_json
            })
        
        # PhantomBuster enrichment data
        phantombuster_data = {}
        if person.phantombuster_data:
            phantombuster_data = person.phantombuster_data
        
        # Existing signals (if any)
        existing_signals = None
        if person.signals:
            existing_signals = {
                "consistency_score": person.signals.consistency_score,
                "depth_score": person.signals.depth_score,
                "motivation_alignment": person.signals.motivation_alignment,
                "culture_alignment": person.signals.culture_alignment,
                "turnover_risk": person.signals.turnover_risk,
                "data_confidence": person.signals.data_confidence,
                "credibility_flag": person.signals.credibility_flag,
                "flags": person.signals.flags
            }
        
        return {
            "profile": profile_data,
            "conversation": conversation_data,
            "phantombuster_enrichment": phantombuster_data,
            "existing_signals": existing_signals,
            "application_timestamp": person.created_ts.isoformat() if person.created_ts else None,
            "last_chat_timestamp": person.last_chat_ts.isoformat() if person.last_chat_ts else None
        }
    
    def _create_scoring_prompt(self, candidate_data: Dict[str, Any], job_profile: Dict[str, Any]) -> str:
        """Create comprehensive prompt for AI scoring analysis"""
        
        prompt = f"""
You are an expert AI recruiter tasked with comprehensively evaluating a candidate's fit for a specific job position. 

**JOB CONTEXT:**
{json.dumps(job_profile, indent=2)}

**CANDIDATE DATA:**
{json.dumps(candidate_data, indent=2)}

**EVALUATION TASK:**
Analyze this candidate comprehensively across multiple dimensions and provide a structured assessment. Consider:

1. **Technical Competency**: Skills match, experience level, technical depth, problem-solving ability
2. **Cultural Alignment**: Values, work style, team fit, communication style  
3. **Motivation & Engagement**: Genuine interest, career alignment, long-term potential
4. **Professional Credibility**: Consistency, authenticity, reliability indicators
5. **Growth Potential**: Learning ability, adaptability, leadership potential
6. **Risk Assessment**: Turnover risk, red flags, stability indicators

**SCORING REQUIREMENTS:**
- Analyze ALL available data sources (resume, chat conversations, social profiles, PhantomBuster data)
- Provide scores from 0.0 to 1.0 for each dimension
- Consider job-specific requirements and company context
- Identify specific strengths and concerns
- Provide actionable recommendations for hiring decision

**OUTPUT FORMAT (JSON):**
{{
    "overall_fit_score": 0.85,
    "dimension_scores": {{
        "technical_competency": 0.88,
        "cultural_alignment": 0.82,
        "motivation_engagement": 0.90,
        "professional_credibility": 0.85,
        "growth_potential": 0.87,
        "risk_assessment": 0.78
    }},
    "fit_bucket": "top|borderline|low",
    "confidence_level": 0.92,
    "key_strengths": ["strength1", "strength2", "strength3"],
    "key_concerns": ["concern1", "concern2"],
    "red_flags": ["flag1", "flag2"],
    "interview_focus_areas": ["area1", "area2", "area3"],
    "hiring_recommendation": "strong_hire|hire|borderline|no_hire",
    "detailed_analysis": {{
        "technical_assessment": "Detailed technical evaluation...",
        "cultural_fit_analysis": "Cultural alignment assessment...",
        "motivation_analysis": "Motivation and engagement evaluation...",
        "credibility_assessment": "Professional credibility review...",
        "growth_potential_analysis": "Growth and development potential...",
        "risk_analysis": "Risk factors and mitigation strategies..."
    }},
    "evidence_sources": {{
        "resume_insights": ["insight1", "insight2"],
        "conversation_insights": ["insight1", "insight2"],
        "social_profile_insights": ["insight1", "insight2"],
        "enrichment_insights": ["insight1", "insight2"]
    }},
    "next_steps": ["action1", "action2", "action3"]
}}

Provide your comprehensive analysis in the exact JSON format above. Be thorough, data-driven, and specific in your assessment.
"""
        return prompt
    
    def _call_openai_for_scoring(self, prompt: str) -> str:
        """Call OpenAI API for candidate scoring analysis"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert AI recruiter with deep experience in candidate evaluation across technical and non-technical dimensions. You provide comprehensive, data-driven assessments that help hiring teams make informed decisions."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=4000,
                temperature=0.3,  # Lower temperature for consistent analysis
                response_format={"type": "json_object"}
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise e
    
    def _parse_ai_scoring_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse and validate AI scoring response"""
        
        try:
            result = json.loads(ai_response)
            
            # Validate required fields
            required_fields = [
                "overall_fit_score", "dimension_scores", "fit_bucket", 
                "confidence_level", "hiring_recommendation"
            ]
            
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            # Ensure scores are within valid range
            result["overall_fit_score"] = max(0.0, min(1.0, result["overall_fit_score"]))
            result["confidence_level"] = max(0.0, min(1.0, result["confidence_level"]))
            
            for dimension, score in result["dimension_scores"].items():
                result["dimension_scores"][dimension] = max(0.0, min(1.0, score))
            
            # Validate fit bucket
            valid_buckets = ["top", "borderline", "low"]
            if result["fit_bucket"] not in valid_buckets:
                # Determine bucket based on score
                score = result["overall_fit_score"]
                if score >= 0.75:
                    result["fit_bucket"] = "top"
                elif score >= 0.50:
                    result["fit_bucket"] = "borderline"
                else:
                    result["fit_bucket"] = "low"
            
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise e
    
    def _save_score_to_database(self, person: ExtendedPerson, scoring_result: Dict[str, Any], db: Session) -> CandidateScore:
        """Save AI scoring results to database"""
        
        # Create or update score record
        score = person.score
        if not score:
            score = CandidateScore(
                person_local_id=person.id,
                fit_score=scoring_result["overall_fit_score"],
                fit_bucket=scoring_result["fit_bucket"]
            )
            db.add(score)
        else:
            score.fit_score = scoring_result["overall_fit_score"]
            score.fit_bucket = scoring_result["fit_bucket"]
        
        # Store full AI analysis in a JSON field (if your model supports it)
        # You might need to add this field to your CandidateScore model
        if hasattr(score, 'ai_analysis_json'):
            score.ai_analysis_json = scoring_result
        
        db.commit()
        return score
    
    def _update_signals_from_ai_analysis(self, person: ExtendedPerson, scoring_result: Dict[str, Any], db: Session):
        """Update candidate signals based on AI analysis"""
        
        dimension_scores = scoring_result.get("dimension_scores", {})
        
        # Create or update signals
        signals = person.signals
        if not signals:
            signals = CandidateSignals(person_local_id=person.id)
            db.add(signals)
        
        # Map AI dimensions to existing signal fields
        signals.consistency_score = dimension_scores.get("professional_credibility", 0.7)
        signals.depth_score = dimension_scores.get("technical_competency", 0.7)
        signals.motivation_alignment = dimension_scores.get("motivation_engagement", 0.7)
        signals.culture_alignment = dimension_scores.get("cultural_alignment", 0.7)
        signals.turnover_risk = 1.0 - dimension_scores.get("risk_assessment", 0.3)
        signals.data_confidence = scoring_result.get("confidence_level", 0.8)
        
        # Check for credibility flags
        red_flags = scoring_result.get("red_flags", [])
        signals.credibility_flag = len(red_flags) > 0
        
        # Update flags with AI insights
        ai_flags = []
        if scoring_result.get("hiring_recommendation") == "strong_hire":
            ai_flags.append("ai-strong-recommendation")
        
        key_strengths = scoring_result.get("key_strengths", [])
        if "technical" in str(key_strengths).lower():
            ai_flags.append("strong-technical-skills")
        if "leadership" in str(key_strengths).lower():
            ai_flags.append("leadership-potential")
        if "communication" in str(key_strengths).lower():
            ai_flags.append("strong-communication")
        
        signals.flags = ai_flags
        
        db.commit()
    
    def _fallback_basic_score(self, person: ExtendedPerson, db: Session) -> CandidateScore:
        """Fallback to basic scoring if AI fails"""
        
        # Simple fallback logic
        skills_count = len(person.skills_tags) if person.skills_tags else 0
        base_score = min(skills_count / 5.0, 0.8)
        
        if person.resume_text and len(person.resume_text) > 100:
            base_score += 0.1
        if person.linkedin:
            base_score += 0.05
        if person.github:
            base_score += 0.05
        
        final_score = min(base_score, 1.0)
        
        # Determine bucket
        if final_score >= 0.75:
            bucket = "top"
        elif final_score >= 0.50:
            bucket = "borderline"
        else:
            bucket = "low"
        
        # Create or update score record
        score = person.score
        if not score:
            score = CandidateScore(
                person_local_id=person.id,
                fit_score=final_score,
                fit_bucket=bucket
            )
            db.add(score)
        else:
            score.fit_score = final_score
            score.fit_bucket = bucket
        
        db.commit()
        return score
    
    def get_detailed_ai_analysis(self, person: ExtendedPerson, db: Session) -> Dict[str, Any]:
        """Get detailed AI analysis without recomputing score"""
        
        if hasattr(person.score, 'ai_analysis_json') and person.score.ai_analysis_json:
            return person.score.ai_analysis_json
        
        # If no stored analysis, generate it
        return self.compute_ai_score(person, db)


# Global AI scoring engine instance
ai_scoring_engine = AIScoreEngine()
