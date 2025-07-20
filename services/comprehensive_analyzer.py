"""
Comprehensive Candidate Analysis Service
Generates deep insights after all enrichment data is collected
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from models import ExtendedPerson, ExtendedJobCache
from services.job_profile_service import job_profile_analyzer
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class ComprehensiveAnalyzer:
    """Generates comprehensive candidate insights after enrichment completion"""
    
    def __init__(self):
        self.skill_categories = {
            'programming_languages': ['python', 'java', 'javascript', 'c++', 'go', 'rust', 'typescript'],
            'frameworks': ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'express'],
            'databases': ['postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch'],
            'cloud_platforms': ['aws', 'azure', 'gcp', 'docker', 'kubernetes'],
            'data_science': ['pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn'],
            'devops': ['jenkins', 'terraform', 'ansible', 'git', 'ci/cd']
        }
    
    def generate_candidate_insights(self, person: ExtendedPerson, db: Session) -> Dict[str, Any]:
        """Generate comprehensive insights for a candidate"""
        
        try:
            logger.info(f"Generating comprehensive insights for person {person.id}")
            
            # Get job profile for context
            job_profile = job_profile_analyzer.get_comprehensive_job_profile(person.job_id, db)
            
            insights = {
                'person_id': person.id,
                'generated_at': datetime.now().isoformat(),
                'profile_analysis': self._analyze_profile_completeness(person),
                'skill_analysis': self._analyze_skills(person, job_profile),
                'experience_analysis': self._analyze_experience(person),
                'social_presence_analysis': self._analyze_social_presence(person),
                'credibility_assessment': self._assess_credibility(person),
                'job_fit_analysis': self._analyze_job_fit(person, job_profile),
                'behavioral_indicators': self._extract_behavioral_indicators(person),
                'red_flags': self._identify_red_flags(person),
                'interview_recommendations': self._generate_interview_recommendations(person, job_profile)
            }
            
            logger.info(f"Comprehensive insights generated successfully for person {person.id}")
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate comprehensive insights for person {person.id}: {e}")
            return {
                'person_id': person.id,
                'generated_at': datetime.now().isoformat(),
                'error': str(e),
                'status': 'failed'
            }
    
    def _analyze_profile_completeness(self, person: ExtendedPerson) -> Dict[str, Any]:
        """Analyze profile data completeness and quality"""
        
        completeness_factors = {
            'basic_info': 1.0,  # Always complete if person exists
            'resume_quality': 0.0,
            'skills_depth': 0.0,
            'social_profiles': 0.0,
            'motivation_clarity': 0.0
        }
        
        # Analyze resume quality
        if person.resume_text:
            resume_length = len(person.resume_text)
            if resume_length > 500:
                completeness_factors['resume_quality'] = min(resume_length / 2000, 1.0)
            else:
                completeness_factors['resume_quality'] = resume_length / 500
        
        # Analyze skills depth
        if person.skills_tags:
            skill_count = len(person.skills_tags)
            completeness_factors['skills_depth'] = min(skill_count / 8, 1.0)
        
        # Analyze social profiles
        social_score = 0
        if person.linkedin:
            social_score += 0.5
        if person.github:
            social_score += 0.5
        completeness_factors['social_profiles'] = social_score
        
        # Analyze motivation clarity
        motivation_score = 0
        if person.intro and len(person.intro) > 50:
            motivation_score += 0.5
        if person.why_us and len(person.why_us) > 50:
            motivation_score += 0.5
        completeness_factors['motivation_clarity'] = motivation_score
        
        # Calculate overall completeness
        overall_completeness = sum(completeness_factors.values()) / len(completeness_factors)
        
        return {
            'overall_score': overall_completeness,
            'factors': completeness_factors,
            'recommendations': self._generate_completeness_recommendations(completeness_factors)
        }
    
    def _analyze_skills(self, person: ExtendedPerson, job_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze candidate skills against job requirements and market standards"""
        
        candidate_skills = set(skill.lower() for skill in (person.skills_tags or []))
        
        # Categorize skills
        skill_categorization = {}
        for category, skills_list in self.skill_categories.items():
            matches = candidate_skills.intersection(set(skills_list))
            skill_categorization[category] = {
                'skills': list(matches),
                'count': len(matches),
                'coverage': len(matches) / len(skills_list) if skills_list else 0
            }
        
        # Analyze against job requirements
        job_skills_analysis = {}
        if job_profile and job_profile.get('personalization_context'):
            context = job_profile['personalization_context']
            mandatory_skills = set(skill.lower() for skill in context.get('mandatory_skills', []))
            preferred_skills = set(skill.lower() for skill in context.get('preferred_skills', []))
            
            job_skills_analysis = {
                'mandatory_match': {
                    'matched': list(candidate_skills.intersection(mandatory_skills)),
                    'missing': list(mandatory_skills - candidate_skills),
                    'coverage': len(candidate_skills.intersection(mandatory_skills)) / len(mandatory_skills) if mandatory_skills else 0
                },
                'preferred_match': {
                    'matched': list(candidate_skills.intersection(preferred_skills)),
                    'coverage': len(candidate_skills.intersection(preferred_skills)) / len(preferred_skills) if preferred_skills else 0
                }
            }
        
        # Advanced skill insights from GitHub data
        github_insights = {}
        if person.github_data:
            github_skills = person.github_data.get('skills_detected', [])
            github_insights = {
                'github_validated_skills': github_skills,
                'cross_platform_consistency': len(set(github_skills).intersection(candidate_skills)) / max(len(github_skills), 1) if github_skills else 0
            }
        
        return {
            'skill_categorization': skill_categorization,
            'job_requirements_analysis': job_skills_analysis,
            'github_insights': github_insights,
            'skill_diversity_score': len(skill_categorization),
            'total_skills_count': len(candidate_skills)
        }
    
    def _analyze_experience(self, person: ExtendedPerson) -> Dict[str, Any]:
        """Extract and analyze experience indicators from resume and profiles"""
        
        experience_indicators = {
            'years_mentioned': [],
            'leadership_signals': [],
            'project_scale_indicators': [],
            'technical_depth_signals': []
        }
        
        if person.resume_text:
            text = person.resume_text.lower()
            
            # Extract years of experience mentions
            year_patterns = [
                r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
                r'(\d+)\s*years?\s+(?:working|developing|building)',
                r'experienced?\s+(?:with\s+)?(\d+)\+?\s*years?'
            ]
            
            for pattern in year_patterns:
                matches = re.findall(pattern, text)
                experience_indicators['years_mentioned'].extend([int(m) for m in matches])
            
            # Leadership signals
            leadership_keywords = ['lead', 'manage', 'mentor', 'architect', 'senior', 'principal', 'director']
            experience_indicators['leadership_signals'] = [kw for kw in leadership_keywords if kw in text]
            
            # Project scale indicators
            scale_patterns = [
                r'(\d+)\s*(?:million|m)\s+users',
                r'(\d+)\s*(?:billion|b)\s+requests',
                r'(\d+)\s*tb\s+(?:of\s+)?data',
                r'(\d+)\s+person\s+team'
            ]
            
            for pattern in scale_patterns:
                matches = re.findall(pattern, text)
                experience_indicators['project_scale_indicators'].extend(matches)
        
        # Calculate experience level
        max_years = max(experience_indicators['years_mentioned']) if experience_indicators['years_mentioned'] else 0
        leadership_score = len(experience_indicators['leadership_signals']) / 3
        
        if max_years >= 7 or leadership_score >= 0.5:
            experience_level = 'senior'
        elif max_years >= 3 or leadership_score >= 0.3:
            experience_level = 'mid-level'
        else:
            experience_level = 'junior'
        
        return {
            'estimated_experience_level': experience_level,
            'max_years_mentioned': max_years,
            'indicators': experience_indicators,
            'leadership_score': leadership_score
        }
    
    def _analyze_social_presence(self, person: ExtendedPerson) -> Dict[str, Any]:
        """Analyze social media presence and professional brand"""
        
        social_analysis = {
            'platforms': {},
            'trust_metrics': {},
            'professional_brand_strength': 0.0
        }
        
        # GitHub analysis
        if person.github_data:
            github_data = person.github_data
            social_analysis['platforms']['github'] = {
                'username': github_data.get('username'),
                'public_repos': github_data.get('public_repos', 0),
                'followers': github_data.get('followers', 0),
                'contribution_activity': github_data.get('contribution_activity', 'low'),
                'profile_strength': min((github_data.get('public_repos', 0) * 0.1 + 
                                      github_data.get('followers', 0) * 0.05), 1.0)
            }
        
        # PhantomBuster analysis
        if person.phantombuster_data:
            pb_data = person.phantombuster_data
            social_analysis['trust_metrics'] = {
                'trust_score': pb_data.get('trust_score', 0.0),
                'consistency_score': pb_data.get('consistency_score', 0.0),
                'risk_indicators': pb_data.get('risk_indicators', []),
                'verification_status': person.social_verification_status
            }
            
            # LinkedIn analysis from PhantomBuster
            linkedin_analysis = pb_data.get('linkedin_analysis', {})
            if linkedin_analysis:
                social_analysis['platforms']['linkedin'] = linkedin_analysis.get('basic_info', {})
        
        # Calculate professional brand strength
        github_strength = social_analysis['platforms'].get('github', {}).get('profile_strength', 0)
        trust_score = social_analysis['trust_metrics'].get('trust_score', 0)
        social_analysis['professional_brand_strength'] = (github_strength + trust_score) / 2
        
        return social_analysis
    
    def _assess_credibility(self, person: ExtendedPerson) -> Dict[str, Any]:
        """Assess overall candidate credibility"""
        
        credibility_factors = {
            'social_verification': 0.0,
            'profile_consistency': 0.0,
            'data_authenticity': 0.0,
            'professional_presence': 0.0
        }
        
        # Social verification score
        if person.social_verification_status == 'verified':
            credibility_factors['social_verification'] = 1.0
        elif person.social_verification_status == 'needs_review':
            credibility_factors['social_verification'] = 0.7
        elif person.social_verification_status == 'unverified':
            credibility_factors['social_verification'] = 0.4
        else:  # suspicious or failed
            credibility_factors['social_verification'] = 0.1
        
        # Profile consistency (from PhantomBuster)
        if person.phantombuster_data:
            consistency_score = person.phantombuster_data.get('consistency_score', 0.0)
            credibility_factors['profile_consistency'] = consistency_score
        
        # Data authenticity (cross-platform skill validation)
        if person.github_data and person.skills_tags:
            github_skills = set(skill.lower() for skill in person.github_data.get('skills_detected', []))
            claimed_skills = set(skill.lower() for skill in person.skills_tags)
            if github_skills and claimed_skills:
                overlap = len(github_skills.intersection(claimed_skills))
                credibility_factors['data_authenticity'] = overlap / max(len(claimed_skills), 1)
        
        # Professional presence
        if person.linkedin and person.github:
            credibility_factors['professional_presence'] = 0.8
        elif person.linkedin or person.github:
            credibility_factors['professional_presence'] = 0.5
        
        overall_credibility = sum(credibility_factors.values()) / len(credibility_factors)
        
        return {
            'overall_score': overall_credibility,
            'factors': credibility_factors,
            'risk_level': 'low' if overall_credibility > 0.7 else 'medium' if overall_credibility > 0.4 else 'high'
        }
    
    def _analyze_job_fit(self, person: ExtendedPerson, job_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how well the candidate fits the specific job"""
        
        if not job_profile:
            return {'status': 'no_job_profile_available'}
        
        job_info = job_profile.get('job', {})
        context = job_profile.get('personalization_context', {})
        
        fit_analysis = {
            'technical_fit': 0.0,
            'experience_fit': 0.0,
            'cultural_fit': 0.0,
            'motivation_alignment': 0.0
        }
        
        # Technical fit (already calculated in skills analysis)
        candidate_skills = set(skill.lower() for skill in (person.skills_tags or []))
        mandatory_skills = set(skill.lower() for skill in context.get('mandatory_skills', []))
        if mandatory_skills:
            fit_analysis['technical_fit'] = len(candidate_skills.intersection(mandatory_skills)) / len(mandatory_skills)
        
        # Experience fit (level matching)
        required_level = job_info.get('role_level', 'mid-level')
        # This would be enhanced based on the experience analysis
        fit_analysis['experience_fit'] = 0.7  # Placeholder for now
        
        # Cultural fit (company values alignment)
        if person.why_us:
            # This would use NLP to analyze alignment with company values
            fit_analysis['cultural_fit'] = 0.6  # Placeholder for now
        
        # Motivation alignment
        if person.intro and person.why_us:
            fit_analysis['motivation_alignment'] = 0.8  # Placeholder for now
        
        overall_fit = sum(fit_analysis.values()) / len(fit_analysis)
        
        return {
            'overall_fit_score': overall_fit,
            'fit_components': fit_analysis,
            'job_match_level': 'excellent' if overall_fit > 0.8 else 'good' if overall_fit > 0.6 else 'fair' if overall_fit > 0.4 else 'poor'
        }
    
    def _extract_behavioral_indicators(self, person: ExtendedPerson) -> Dict[str, Any]:
        """Extract behavioral and personality indicators"""
        
        indicators = {
            'communication_style': 'analytical',  # Would be determined by NLP
            'detail_orientation': 'high',         # Based on resume and response quality
            'proactivity_level': 'medium',        # Based on GitHub activity, projects
            'learning_agility': 'high',           # Based on skill diversity and growth
            'collaboration_signals': []           # Team mentions, open source contributions
        }
        
        # Extract from GitHub data
        if person.github_data:
            contribution_activity = person.github_data.get('contribution_activity', 'low')
            if contribution_activity in ['high', 'very_high']:
                indicators['proactivity_level'] = 'high'
                indicators['collaboration_signals'].append('active_open_source_contributor')
        
        # Extract from resume
        if person.resume_text:
            text = person.resume_text.lower()
            if any(word in text for word in ['team', 'collaborate', 'mentor', 'lead']):
                indicators['collaboration_signals'].append('team_experience_mentioned')
        
        return indicators
    
    def _identify_red_flags(self, person: ExtendedPerson) -> List[str]:
        """Identify potential red flags in the candidate profile"""
        
        red_flags = []
        
        # Social verification red flags
        if person.social_verification_status in ['suspicious', 'failed']:
            red_flags.append('social_verification_failed')
        
        # Trust score red flags
        if person.trust_score and person.trust_score < 0.3:
            red_flags.append('low_trust_score')
        
        # Profile inconsistency red flags
        if person.phantombuster_data:
            risk_indicators = person.phantombuster_data.get('risk_indicators', [])
            red_flags.extend(risk_indicators)
        
        # Skills inconsistency
        if person.github_data and person.skills_tags:
            github_skills = set(person.github_data.get('skills_detected', []))
            claimed_skills = set(person.skills_tags)
            if github_skills and len(github_skills.intersection(claimed_skills)) / max(len(claimed_skills), 1) < 0.3:
                red_flags.append('skills_inconsistency_with_github')
        
        return red_flags
    
    def _generate_interview_recommendations(self, person: ExtendedPerson, job_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate specific interview focus areas and question recommendations"""
        
        recommendations = {
            'focus_areas': [],
            'suggested_question_types': [],
            'areas_to_probe': [],
            'strengths_to_validate': [],
            'interview_style': 'standard'
        }
        
        # Based on credibility assessment
        if person.social_verification_status in ['needs_review', 'unverified', 'suspicious']:
            recommendations['focus_areas'].append('credential_verification')
            recommendations['suggested_question_types'].append('detailed_technical_probing')
        
        # Based on skill analysis
        if person.skills_tags and len(person.skills_tags) > 10:
            recommendations['areas_to_probe'].append('skill_depth_vs_breadth')
            recommendations['suggested_question_types'].append('specific_tool_experience')
        
        # Based on experience level
        if person.resume_text and 'senior' in person.resume_text.lower():
            recommendations['suggested_question_types'].extend(['leadership_scenarios', 'architecture_decisions'])
            recommendations['interview_style'] = 'senior_level'
        
        # GitHub activity insights
        if person.github_data:
            repos = person.github_data.get('public_repos', 0)
            if repos > 10:
                recommendations['strengths_to_validate'].append('coding_portfolio')
                recommendations['suggested_question_types'].append('project_deep_dive')
        
        return recommendations
    
    def _generate_completeness_recommendations(self, factors: Dict[str, float]) -> List[str]:
        """Generate recommendations to improve profile completeness"""
        
        recommendations = []
        
        if factors['resume_quality'] < 0.7:
            recommendations.append("Request more detailed resume or work samples")
        
        if factors['skills_depth'] < 0.6:
            recommendations.append("Ask for specific skill examples during interview")
        
        if factors['social_profiles'] < 0.5:
            recommendations.append("Verify professional presence through alternative means")
        
        if factors['motivation_clarity'] < 0.5:
            recommendations.append("Focus interview on motivation and cultural fit assessment")
        
        return recommendations


# Global instance
comprehensive_analyzer = ComprehensiveAnalyzer()
