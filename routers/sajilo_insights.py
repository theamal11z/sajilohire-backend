"""
Sajilo Enhanced Insights Router
Advanced candidate insights powered by PhantomBuster social intelligence
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from schemas import ErrorResponse
from database import get_db
from models import ExtendedPerson
from services.phantombuster_enrichment import phantombuster_enrichment_service
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/insights/{person_id}/social-intelligence", responses={404: {"model": ErrorResponse}})
def get_social_intelligence(person_id: int, db: Session = Depends(get_db)):
    """Get comprehensive social intelligence analysis for a candidate"""
    
    try:
        # Get person
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        phantombuster_data = person.phantombuster_data or {}
        
        return {
            "person_id": person_id,
            "trust_score": person.trust_score or 0.0,
            "verification_status": person.social_verification_status or "unverified",
            "linkedin_analysis": phantombuster_data.get('linkedin_analysis', {}),
            "github_analysis": phantombuster_data.get('github_analysis', {}),
            "cross_platform_analysis": phantombuster_data.get('cross_platform_analysis', {}),
            "professional_insights": phantombuster_data.get('professional_insights', {}),
            "risk_indicators": phantombuster_data.get('risk_indicators', []),
            "enrichment_timestamp": phantombuster_data.get('enrichment_timestamp')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get social intelligence for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve social intelligence")


@router.get("/insights/{person_id}/professional-summary", responses={404: {"model": ErrorResponse}})
def get_professional_summary(person_id: int, db: Session = Depends(get_db)):
    """Get AI-generated professional summary combining all enrichment data"""
    
    try:
        # Get person
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        # Combine all enrichment data
        summary = {
            "candidate_overview": {
                "name": f"{person.first_name} {person.last_name}",
                "email": person.email,
                "avatar_url": person.avatar_url,
                "skills": person.skills_tags or [],
                "social_profiles": {
                    "linkedin": person.linkedin,
                    "github": person.github
                }
            },
            "trust_assessment": {
                "overall_trust_score": person.trust_score or 0.0,
                "verification_status": person.social_verification_status or "unverified",
                "risk_indicators": []
            },
            "professional_highlights": [],
            "technical_expertise": {},
            "career_insights": {},
            "red_flags": []
        }
        
        # Extract data from PhantomBuster analysis
        if person.phantombuster_data:
            pb_data = person.phantombuster_data
            
            # Risk indicators
            summary["trust_assessment"]["risk_indicators"] = pb_data.get('risk_indicators', [])
            
            # Professional insights
            insights = pb_data.get('professional_insights', {})
            summary["career_insights"] = {
                "career_progression": insights.get('career_progression', 'unknown'),
                "thought_leadership": insights.get('thought_leadership_level', 'emerging'),
                "network_influence": insights.get('network_influence', 'moderate'),
                "leadership_potential": insights.get('leadership_potential', 'medium')
            }
            
            # LinkedIn highlights
            linkedin_data = pb_data.get('linkedin_analysis', {})
            if linkedin_data:
                basic_info = linkedin_data.get('basic_info', {})
                professional_details = linkedin_data.get('professional_details', {})
                
                if basic_info.get('headline'):
                    summary["professional_highlights"].append(f"Current Role: {basic_info['headline']}")
                
                if professional_details.get('experience_years'):
                    years = professional_details['experience_years']
                    summary["professional_highlights"].append(f"Experience: {years} years")
                
                if professional_details.get('skills'):
                    top_skills = professional_details['skills'][:5]
                    summary["professional_highlights"].append(f"Top Skills: {', '.join(top_skills)}")
            
            # GitHub technical expertise
            github_data = pb_data.get('github_analysis', {})
            if github_data:
                technical_profile = github_data.get('technical_profile', {})
                summary["technical_expertise"] = {
                    "code_quality": github_data.get('code_quality_indicators', {}),
                    "collaboration_style": github_data.get('collaboration_style', {}),
                    "technical_leadership": github_data.get('technical_leadership', {}),
                    "contribution_consistency": github_data.get('consistency_score', 0.0)
                }
        
        # Extract data from GitHub basic enrichment
        if person.github_data:
            github_data = person.github_data
            
            if github_data.get('public_repos'):
                summary["professional_highlights"].append(f"Public Repositories: {github_data['public_repos']}")
            
            if github_data.get('followers'):
                summary["professional_highlights"].append(f"GitHub Followers: {github_data['followers']}")
            
            trust_indicators = github_data.get('trust_indicators', [])
            if 'established-account' in str(trust_indicators):
                summary["professional_highlights"].append("Established GitHub presence")
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate professional summary for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate professional summary")


@router.get("/insights/{person_id}/hr-recommendations", responses={404: {"model": ErrorResponse}})
def get_hr_recommendations(person_id: int, db: Session = Depends(get_db)):
    """Get AI-generated HR recommendations based on comprehensive analysis"""
    
    try:
        # Get person
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        recommendations = {
            "hiring_recommendation": "needs_review",
            "confidence_level": "medium",
            "key_strengths": [],
            "areas_of_concern": [],
            "interview_focus_areas": [],
            "reference_check_priorities": [],
            "cultural_fit_assessment": "good",
            "overall_assessment": ""
        }
        
        # Base assessment on trust score and verification status
        trust_score = person.trust_score or 0.0
        verification_status = person.social_verification_status or "unverified"
        
        if trust_score >= 0.8 and verification_status == "verified":
            recommendations["hiring_recommendation"] = "recommend"
            recommendations["confidence_level"] = "high"
        elif trust_score >= 0.6 and verification_status in ["verified", "needs_review"]:
            recommendations["hiring_recommendation"] = "conditional_recommend"
            recommendations["confidence_level"] = "medium"
        elif trust_score < 0.4 or verification_status == "unverified":
            recommendations["hiring_recommendation"] = "not_recommend"
            recommendations["confidence_level"] = "low"
        
        # Extract specific recommendations from PhantomBuster data
        if person.phantombuster_data:
            pb_data = person.phantombuster_data
            
            # Professional insights
            insights = pb_data.get('professional_insights', {})
            
            # Strengths
            if insights.get('thought_leadership_level') in ['established', 'emerging']:
                recommendations["key_strengths"].append("Demonstrates thought leadership in their field")
            
            if insights.get('network_influence') in ['high', 'moderate']:
                recommendations["key_strengths"].append("Well-connected professional network")
            
            if insights.get('technical_expertise') == 'verified':
                recommendations["key_strengths"].append("Verified technical expertise through code contributions")
            
            # Areas of concern from risk indicators
            risk_indicators = pb_data.get('risk_indicators', [])
            for risk in risk_indicators:
                if risk == 'cross-platform-inconsistency':
                    recommendations["areas_of_concern"].append("Inconsistencies between social profiles need verification")
                elif risk == 'low-professional-activity':
                    recommendations["areas_of_concern"].append("Limited recent professional social media activity")
                elif risk == 'authenticity-concerns':
                    recommendations["areas_of_concern"].append("Profile authenticity requires additional verification")
            
            # Interview focus areas
            linkedin_data = pb_data.get('linkedin_analysis', {})
            if linkedin_data:
                professional_details = linkedin_data.get('professional_details', {})
                if professional_details.get('experience_years', 0) > 5:
                    recommendations["interview_focus_areas"].append("Leadership and mentoring experience")
                else:
                    recommendations["interview_focus_areas"].append("Growth potential and learning agility")
            
            # Reference check priorities
            if 'cross-platform-inconsistency' in risk_indicators:
                recommendations["reference_check_priorities"].append("Verify employment timeline and responsibilities")
            
            if trust_score < 0.7:
                recommendations["reference_check_priorities"].append("Validate technical skills and project claims")
        
        # Overall assessment
        if recommendations["hiring_recommendation"] == "recommend":
            recommendations["overall_assessment"] = "Strong candidate with verified professional presence and consistent track record. Proceed with confidence."
        elif recommendations["hiring_recommendation"] == "conditional_recommend":
            recommendations["overall_assessment"] = "Promising candidate with some areas requiring clarification. Recommend thorough interview process."
        else:
            recommendations["overall_assessment"] = "Candidate requires additional verification before proceeding. Consider alternative candidates."
        
        return recommendations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate HR recommendations for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate HR recommendations")


@router.post("/insights/{person_id}/refresh-enrichment", responses={404: {"model": ErrorResponse}})
def refresh_enrichment(person_id: int, db: Session = Depends(get_db)):
    """Refresh PhantomBuster enrichment data for a candidate"""
    
    try:
        # Get person
        person = db.query(ExtendedPerson).filter(ExtendedPerson.id == person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")
        
        if not person.linkedin and not person.github:
            raise HTTPException(status_code=400, detail="No social profiles available for enrichment")
        
        # Refresh PhantomBuster enrichment
        phantombuster_data = phantombuster_enrichment_service.enrich_candidate_profile(
            linkedin_url=person.linkedin,
            github_url=person.github
        )
        
        if phantombuster_data:
            person.phantombuster_data = phantombuster_data
            person.trust_score = phantombuster_data.get('trust_score', 0.0)
            
            # Update verification status
            trust_score = phantombuster_data.get('trust_score', 0.0)
            risk_indicators = phantombuster_data.get('risk_indicators', [])
            
            if trust_score >= 0.8 and not risk_indicators:
                person.social_verification_status = 'verified'
            elif trust_score >= 0.6 or len(risk_indicators) <= 1:
                person.social_verification_status = 'needs_review'
            else:
                person.social_verification_status = 'unverified'
            
            db.commit()
            
            return {
                "message": "Enrichment refreshed successfully",
                "trust_score": person.trust_score,
                "verification_status": person.social_verification_status,
                "risk_indicators": phantombuster_data.get('risk_indicators', [])
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to refresh enrichment data")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh enrichment for person {person_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh enrichment")
