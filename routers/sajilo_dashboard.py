"""
Sajilo Dashboard router
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from schemas import DashboardResponse, DashboardCandidate, ErrorResponse
from database import get_db
from models import ExtendedPerson, ExtendedJobCache, CandidateScore
from services.ai_scoring_engine import ai_scoring_engine
from services.job_profile_service import job_profile_analyzer
from services.adaptive_interview_engine import adaptive_interview_engine
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard/{job_id}", response_model=DashboardResponse, responses={404: {"model": ErrorResponse}})
def get_dashboard(
    job_id: int, 
    include_borderline: bool = Query(False, description="Include borderline candidates"),
    db: Session = Depends(get_db)
):
    """Get recruiter dashboard with ranked candidates for a job"""
    
    try:
        # Get comprehensive job profile for enhanced dashboard
        job_profile = job_profile_analyzer.get_comprehensive_job_profile(job_id, db)
        
        # Verify job exists in cache
        job = db.query(ExtendedJobCache).filter(
            ExtendedJobCache.upstream_job_id == job_id
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Get candidates for this job
        query = db.query(ExtendedPerson).filter(ExtendedPerson.job_id == job_id)
        
        # Filter by score if needed
        if not include_borderline:
            query = query.join(CandidateScore).filter(
                CandidateScore.fit_bucket.in_(["top", "borderline"])
            )
        
        candidates = query.all()
        
        # Ensure all candidates have scores using AI
        for candidate in candidates:
            if not candidate.score:
                ai_scoring_engine.compute_ai_score(candidate, db)
        
        # Build enhanced dashboard candidates with comprehensive data
        dashboard_candidates = []
        for person in candidates:
            # Get enrichment and interview status
            interview_ready, interview_status = adaptive_interview_engine.should_start_interview(person)
            enrichment_progress = person.enrichment_progress or {}
            comprehensive_insights = person.comprehensive_insights or {}
            
            # Calculate profile completeness
            profile_completeness = person.profile_completeness_score or _calculate_basic_completeness(person)
            
            # Extract GitHub data
            github_username = None
            github_repos = 0
            if person.github_data:
                github_username = person.github_data.get('username')
                github_repos = person.github_data.get('public_repos', 0)
            
            # Extract PhantomBuster insights
            professional_insights = {}
            risk_indicators = []
            if person.phantombuster_data:
                professional_insights = person.phantombuster_data.get('professional_insights', {})
                risk_indicators = person.phantombuster_data.get('risk_indicators', [])
            
            # Get interview statistics
            interview_stats = _get_interview_statistics(person, db)
            
            # Get comprehensive insights summary
            insights_summary = _extract_insights_summary(comprehensive_insights)
            
            # Ensure scoring is complete using AI
            if not person.score:
                ai_scoring_engine.compute_ai_score(person, db)
            
            if person.score:
                dashboard_candidate = DashboardCandidate(
                    person_id=person.id,
                    full_name=f"{person.first_name} {person.last_name}",
                    email=person.email,
                    avatar_url=person.avatar_url,
                    fit_score=person.score.fit_score,
                    fit_bucket=person.score.fit_bucket,
                    turnover_risk=person.signals.turnover_risk if person.signals else 0.5,
                    flags=person.signals.flags if person.signals else [],
                    github_username=github_username,
                    linkedin_url=person.linkedin,
                    trust_score=person.trust_score,
                    social_verification_status=person.social_verification_status,
                    professional_insights=professional_insights,
                    risk_indicators=risk_indicators,
                    applied_at=person.created_ts,
                    # Enhanced fields
                    enrichment_status=person.social_verification_status or 'not_started',
                    enrichment_progress=enrichment_progress.get('progress', 0.0),
                    interview_ready=interview_ready,
                    interview_status=interview_status,
                    profile_completeness=profile_completeness,
                    github_repos=github_repos,
                    interview_stats=interview_stats,
                    comprehensive_insights=insights_summary,
                    last_activity=person.last_chat_ts or person.created_ts
                )
                dashboard_candidates.append(dashboard_candidate)
        
        # Sort by fit score descending
        dashboard_candidates.sort(key=lambda x: x.fit_score, reverse=True)
        
        # Enhanced analytics
        analytics = _generate_dashboard_analytics(dashboard_candidates, job_profile)
        
        # Count high-fit candidates
        high_fit_count = len([c for c in dashboard_candidates if c.fit_bucket == "top"])
        borderline_count = len([c for c in dashboard_candidates if c.fit_bucket == "borderline"])
        
        return DashboardResponse(
            job_id=job_id,
            job_title=job.title,
            candidates=dashboard_candidates,
            total_count=len(dashboard_candidates),
            high_fit_count=high_fit_count,
            borderline_count=borderline_count,
            analytics=analytics,
            job_requirements_summary=_extract_job_requirements_summary(job_profile)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard failed for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard")


def _calculate_basic_completeness(person: ExtendedPerson) -> float:
    """Calculate basic profile completeness if not already computed"""
    completeness_factors = {
        'resume': 1.0 if person.resume_text and len(person.resume_text) > 200 else 0.5,
        'skills': 1.0 if person.skills_tags and len(person.skills_tags) >= 5 else 0.5,
        'social_profiles': 1.0 if (person.linkedin and person.github) else 0.5,
        'motivation': 1.0 if (person.intro and person.why_us) else 0.5
    }
    return sum(completeness_factors.values()) / len(completeness_factors)


def _get_interview_statistics(person: ExtendedPerson, db: Session) -> Dict[str, Any]:
    """Get interview statistics for a candidate"""
    from models import ChatTurn, ChatTurnRole
    
    chat_turns = db.query(ChatTurn).filter(
        ChatTurn.person_local_id == person.id
    ).all()
    
    if not chat_turns:
        return {
            'status': 'not_started',
            'total_turns': 0,
            'questions_answered': 0,
            'completion_percentage': 0.0,
            'interview_type': 'none'
        }
    
    user_turns = [t for t in chat_turns if t.role == ChatTurnRole.USER]
    ai_turns = [t for t in chat_turns if t.role == ChatTurnRole.AI]
    
    # Check if using adaptive interview
    interview_plan = person.interview_plan
    if interview_plan:
        planned_questions = interview_plan.get('total_planned_questions', 10)
        questions_answered = len(user_turns)
        completion_percentage = min(questions_answered / planned_questions, 1.0)
        interview_type = 'adaptive'
    else:
        # Legacy interview system
        questions_answered = len(user_turns)
        planned_questions = 5  # Old system default
        completion_percentage = min(questions_answered / planned_questions, 1.0)
        interview_type = 'legacy'
    
    # Determine status
    if completion_percentage >= 1.0:
        status = 'completed'
    elif completion_percentage > 0:
        status = 'in_progress'
    else:
        status = 'not_started'
    
    return {
        'status': status,
        'total_turns': len(chat_turns),
        'questions_answered': questions_answered,
        'completion_percentage': completion_percentage,
        'interview_type': interview_type,
        'planned_questions': planned_questions
    }


def _extract_insights_summary(comprehensive_insights: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key insights for dashboard display"""
    if not comprehensive_insights:
        return {
            'available': False,
            'credibility_score': 0.0,
            'job_fit_score': 0.0,
            'red_flags_count': 0,
            'focus_areas': [],
            'experience_level': 'unknown'
        }
    
    credibility = comprehensive_insights.get('credibility_assessment', {})
    job_fit = comprehensive_insights.get('job_fit_analysis', {})
    experience = comprehensive_insights.get('experience_analysis', {})
    interview_recs = comprehensive_insights.get('interview_recommendations', {})
    
    return {
        'available': True,
        'credibility_score': credibility.get('overall_score', 0.0),
        'job_fit_score': job_fit.get('overall_fit_score', 0.0),
        'red_flags_count': len(comprehensive_insights.get('red_flags', [])),
        'focus_areas': interview_recs.get('focus_areas', []),
        'experience_level': experience.get('estimated_experience_level', 'unknown'),
        'risk_level': credibility.get('risk_level', 'unknown'),
        'strengths_to_validate': interview_recs.get('strengths_to_validate', []),
        'areas_to_probe': interview_recs.get('areas_to_probe', [])
    }


def _generate_dashboard_analytics(candidates: List[DashboardCandidate], job_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Generate analytics for the dashboard"""
    if not candidates:
        return {
            'total_candidates': 0,
            'enrichment_status_breakdown': {},
            'interview_readiness_stats': {},
            'skill_gap_analysis': {},
            'quality_metrics': {}
        }
    
    # Enrichment status breakdown
    enrichment_statuses = {}
    interview_ready_count = 0
    completed_interviews = 0
    in_progress_interviews = 0
    
    trust_scores = []
    profile_completeness_scores = []
    fit_scores = []
    
    for candidate in candidates:
        # Enrichment status
        status = candidate.enrichment_status or 'not_started'
        enrichment_statuses[status] = enrichment_statuses.get(status, 0) + 1
        
        # Interview readiness
        if candidate.interview_ready:
            interview_ready_count += 1
        
        # Interview progress
        interview_status = candidate.interview_stats.get('status', 'not_started')
        if interview_status == 'completed':
            completed_interviews += 1
        elif interview_status == 'in_progress':
            in_progress_interviews += 1
        
        # Quality metrics
        if candidate.trust_score is not None:
            trust_scores.append(candidate.trust_score)
        if candidate.profile_completeness is not None:
            profile_completeness_scores.append(candidate.profile_completeness)
        fit_scores.append(candidate.fit_score)
    
    # Calculate averages
    avg_trust_score = sum(trust_scores) / len(trust_scores) if trust_scores else 0.0
    avg_profile_completeness = sum(profile_completeness_scores) / len(profile_completeness_scores) if profile_completeness_scores else 0.0
    avg_fit_score = sum(fit_scores) / len(fit_scores) if fit_scores else 0.0
    
    # Skill gap analysis
    skill_gaps = _analyze_skill_gaps(candidates, job_profile)
    
    return {
        'total_candidates': len(candidates),
        'enrichment_status_breakdown': enrichment_statuses,
        'interview_readiness_stats': {
            'ready_for_interview': interview_ready_count,
            'completed_interviews': completed_interviews,
            'in_progress_interviews': in_progress_interviews,
            'not_started': len(candidates) - completed_interviews - in_progress_interviews
        },
        'quality_metrics': {
            'avg_trust_score': avg_trust_score,
            'avg_profile_completeness': avg_profile_completeness,
            'avg_fit_score': avg_fit_score,
            'high_trust_candidates': len([s for s in trust_scores if s >= 0.8]),
            'verified_profiles': len([c for c in candidates if c.social_verification_status == 'verified'])
        },
        'skill_gap_analysis': skill_gaps,
        'generated_at': datetime.now().isoformat()
    }


def _analyze_skill_gaps(candidates: List[DashboardCandidate], job_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze skill gaps across candidate pool"""
    if not job_profile or not job_profile.get('personalization_context'):
        return {'available': False, 'message': 'No job profile available'}
    
    context = job_profile['personalization_context']
    mandatory_skills = set(skill.lower() for skill in context.get('mandatory_skills', []))
    preferred_skills = set(skill.lower() for skill in context.get('preferred_skills', []))
    
    skill_coverage = {}
    candidates_with_insights = 0
    
    for candidate in candidates:
        if candidate.comprehensive_insights.get('available', False):
            candidates_with_insights += 1
            insights = candidate.comprehensive_insights
            skill_analysis = insights.get('skill_analysis', {}) if isinstance(insights, dict) else {}
            job_analysis = skill_analysis.get('job_requirements_analysis', {})
            
            if job_analysis:
                mandatory_match = job_analysis.get('mandatory_match', {})
                matched_mandatory = mandatory_match.get('matched', [])
                
                for skill in matched_mandatory:
                    skill_lower = skill.lower()
                    if skill_lower in mandatory_skills:
                        skill_coverage[skill_lower] = skill_coverage.get(skill_lower, 0) + 1
    
    # Calculate coverage percentages
    skill_coverage_percentages = {}
    if candidates_with_insights > 0:
        for skill in mandatory_skills:
            coverage_count = skill_coverage.get(skill, 0)
            skill_coverage_percentages[skill] = coverage_count / candidates_with_insights
    
    # Find most and least covered skills
    if skill_coverage_percentages:
        most_covered = max(skill_coverage_percentages.items(), key=lambda x: x[1])
        least_covered = min(skill_coverage_percentages.items(), key=lambda x: x[1])
    else:
        most_covered = ('N/A', 0)
        least_covered = ('N/A', 0)
    
    return {
        'available': True,
        'candidates_analyzed': candidates_with_insights,
        'mandatory_skills_count': len(mandatory_skills),
        'skill_coverage_percentages': skill_coverage_percentages,
        'most_covered_skill': {'skill': most_covered[0], 'coverage': most_covered[1]},
        'least_covered_skill': {'skill': least_covered[0], 'coverage': least_covered[1]},
        'avg_mandatory_coverage': sum(skill_coverage_percentages.values()) / len(skill_coverage_percentages) if skill_coverage_percentages else 0.0
    }


def _extract_job_requirements_summary(job_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Extract job requirements summary for dashboard"""
    if not job_profile:
        return {'available': False}
    
    job_info = job_profile.get('job', {})
    context = job_profile.get('personalization_context', {})
    
    return {
        'available': True,
        'role_level': job_info.get('role_level', 'unknown'),
        'technical_focus': job_info.get('technical_focus', []),
        'mandatory_skills': context.get('mandatory_skills', []),
        'preferred_skills': context.get('preferred_skills', []),
        'total_skills_required': len(context.get('mandatory_skills', [])) + len(context.get('preferred_skills', [])),
        'growth_opportunities': job_info.get('growth_opportunities', []),
        'cultural_indicators': job_profile.get('cultural_indicators', [])
    }


@router.get("/dashboard/{job_id}/analytics", responses={404: {"model": ErrorResponse}})
def get_dashboard_analytics(job_id: int, db: Session = Depends(get_db)):
    """Get detailed analytics for a job's candidate pool"""
    
    try:
        # Get job profile and candidates
        job_profile = job_profile_analyzer.get_comprehensive_job_profile(job_id, db)
        candidates = db.query(ExtendedPerson).filter(ExtendedPerson.job_id == job_id).all()
        
        if not candidates:
            return {
                'job_id': job_id,
                'analytics': {
                    'total_candidates': 0,
                    'message': 'No candidates found for this job'
                }
            }
        
        # Build candidate list for analytics
        dashboard_candidates = []
        for person in candidates:
            interview_ready, interview_status = adaptive_interview_engine.should_start_interview(person)
            enrichment_progress = person.enrichment_progress or {}
            comprehensive_insights = person.comprehensive_insights or {}
            
            profile_completeness = person.profile_completeness_score or _calculate_basic_completeness(person)
            interview_stats = _get_interview_statistics(person, db)
            insights_summary = _extract_insights_summary(comprehensive_insights)
            
            if person.score:  # Only include scored candidates
                dashboard_candidate = DashboardCandidate(
                    person_id=person.id,
                    full_name=f"{person.first_name} {person.last_name}",
                    email=person.email,
                    avatar_url=person.avatar_url,
                    fit_score=person.score.fit_score,
                    fit_bucket=person.score.fit_bucket,
                    turnover_risk=person.signals.turnover_risk if person.signals else 0.5,
                    flags=person.signals.flags if person.signals else [],
                    github_username=person.github_data.get('username') if person.github_data else None,
                    linkedin_url=person.linkedin,
                    trust_score=person.trust_score,
                    social_verification_status=person.social_verification_status,
                    professional_insights=person.phantombuster_data.get('professional_insights', {}) if person.phantombuster_data else {},
                    risk_indicators=person.phantombuster_data.get('risk_indicators', []) if person.phantombuster_data else [],
                    applied_at=person.created_ts,
                    enrichment_status=person.social_verification_status or 'not_started',
                    enrichment_progress=enrichment_progress.get('progress', 0.0),
                    interview_ready=interview_ready,
                    interview_status=interview_status,
                    profile_completeness=profile_completeness,
                    github_repos=person.github_data.get('public_repos', 0) if person.github_data else 0,
                    interview_stats=interview_stats,
                    comprehensive_insights=insights_summary,
                    last_activity=person.last_chat_ts or person.created_ts
                )
                dashboard_candidates.append(dashboard_candidate)
        
        # Generate comprehensive analytics
        analytics = _generate_dashboard_analytics(dashboard_candidates, job_profile)
        
        return {
            'job_id': job_id,
            'analytics': analytics,
            'job_requirements_summary': _extract_job_requirements_summary(job_profile),
            'candidates_summary': {
                'total': len(dashboard_candidates),
                'top_fit': len([c for c in dashboard_candidates if c.fit_bucket == 'top']),
                'borderline': len([c for c in dashboard_candidates if c.fit_bucket == 'borderline']),
                'low_fit': len([c for c in dashboard_candidates if c.fit_bucket == 'low'])
            }
        }
        
    except Exception as e:
        logger.error(f"Analytics failed for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate analytics")
