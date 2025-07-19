"""
Enhanced Job Profile Service
Fetches and analyzes comprehensive job and company data for personalized onboarding
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from models import ExtendedJobCache, ClientCache
from aqore_client import aqore_client
from database import SessionLocal
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class JobProfileAnalyzer:
    """Service for building detailed job and company profiles for personalized onboarding"""
    
    def __init__(self):
        self.industry_insights = {
            'technology': {
                'values': ['Innovation', 'Learning', 'Growth', 'Impact'],
                'culture_keywords': ['agile', 'startup', 'innovation', 'cutting-edge', 'scalable'],
                'priorities': ['technical excellence', 'problem solving', 'continuous learning']
            },
            'healthcare': {
                'values': ['Patient Care', 'Quality', 'Compassion', 'Safety'],
                'culture_keywords': ['patient-first', 'care', 'healing', 'wellness', 'health'],
                'priorities': ['patient outcomes', 'quality care', 'compliance']
            },
            'finance': {
                'values': ['Integrity', 'Precision', 'Trust', 'Results'],
                'culture_keywords': ['compliance', 'risk', 'analytical', 'strategic', 'results-driven'],
                'priorities': ['accuracy', 'risk management', 'regulatory compliance']
            },
            'education': {
                'values': ['Learning', 'Growth', 'Impact', 'Community'],
                'culture_keywords': ['student-focused', 'learning', 'development', 'mentoring'],
                'priorities': ['student success', 'educational excellence', 'knowledge transfer']
            },
            'manufacturing': {
                'values': ['Quality', 'Safety', 'Efficiency', 'Teamwork'],
                'culture_keywords': ['safety-first', 'quality', 'efficiency', 'process improvement'],
                'priorities': ['operational excellence', 'safety standards', 'continuous improvement']
            }
        }
    
    def get_comprehensive_job_profile(self, job_id: int, db: Session) -> Dict[str, Any]:
        """Get comprehensive job profile with company context and skills analysis"""
        
        # Get cached job data
        job = db.query(ExtendedJobCache).filter(
            ExtendedJobCache.upstream_job_id == job_id
        ).first()
        
        if not job:
            logger.warning(f"Job {job_id} not found in cache, fetching fresh data")
            job = self._fetch_and_cache_job(job_id, db)
        
        if not job:
            return {}
        
        # Get client/company data
        client = db.query(ClientCache).filter(
            ClientCache.upstream_client_id == job.client_id
        ).first()
        
        # Get job skills
        job_skills = self._fetch_job_skills(job_id)
        
        # Build comprehensive profile
        profile = {
            'job': {
                'id': job.upstream_job_id,
                'title': job.title,
                'description': job.description,
                'type': job.job_type,
                'employment_type': job.employment_type,
                'status': job.status,
                'skills': job_skills,
                'analyzed_skills': self._analyze_job_skills(job_skills),
                'role_level': self._determine_role_level(job.title, job.description),
                'technical_focus': self._extract_technical_focus(job.description, job_skills),
                'growth_opportunities': self._identify_growth_opportunities(job.description)
            },
            'company': self._build_company_profile(client) if client else {},
            'personalization_context': self._build_personalization_context(job, client, job_skills),
            'interview_focus': self._determine_interview_focus(job, job_skills),
            'cultural_indicators': self._extract_cultural_indicators(job, client)
        }
        
        return profile
    
    def _fetch_and_cache_job(self, job_id: int, db: Session) -> Optional[ExtendedJobCache]:
        """Fetch job data from API and cache it"""
        try:
            # Fetch all jobs and find the one we need
            jobs = aqore_client.get_all_jobs()
            job_data = next((j for j in jobs if j.get('jobId') == job_id), None)
            
            if not job_data:
                return None
            
            # Create job cache entry
            job = ExtendedJobCache(
                upstream_job_id=job_id,
                title=job_data.get('title', 'Untitled Position'),
                description=job_data.get('description'),
                client_id=job_data.get('clientId', 0),
                job_type=job_data.get('jobType'),
                employment_type=job_data.get('employmentType'),
                status=job_data.get('status'),
                created_date=datetime.fromisoformat(job_data['createdDate']) if job_data.get('createdDate') else None,
                skills_json=[],
                cached_at=datetime.now()
            )
            
            # Get client name
            if job.client_id:
                client = db.query(ClientCache).filter(
                    ClientCache.upstream_client_id == job.client_id
                ).first()
                if client:
                    job.client_name = client.client_name
            
            db.add(job)
            db.commit()
            return job
            
        except Exception as e:
            logger.error(f"Failed to fetch job {job_id}: {e}")
            return None
    
    def _fetch_job_skills(self, job_id: int) -> List[Dict[str, Any]]:
        """Fetch job skills from API"""
        try:
            skills = aqore_client.get_job_skills_by_job_id(job_id)
            return skills or []
        except Exception as e:
            logger.error(f"Failed to fetch skills for job {job_id}: {e}")
            return []
    
    def _build_company_profile(self, client: ClientCache) -> Dict[str, Any]:
        """Build detailed company profile"""
        if not client:
            return {}
        
        industry_key = self._normalize_industry(client.industry)
        industry_info = self.industry_insights.get(industry_key, {})
        
        return {
            'name': client.client_name,
            'industry': client.industry,
            'location': {
                'city': client.city,
                'state': client.state,
                'zip': client.zip_code
            },
            'contact': {
                'email': client.email,
                'phone': client.phone
            },
            'industry_insights': industry_info,
            'company_size_estimate': self._estimate_company_size(client),
            'business_focus': self._infer_business_focus(client)
        }
    
    def _analyze_job_skills(self, skills: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze job skills for categories and priorities"""
        if not skills:
            return {}
        
        categorized_skills = {
            'mandatory': [],
            'preferred': [],
            'technical': [],
            'soft_skills': [],
            'tools': [],
            'frameworks': [],
            'languages': []
        }
        
        skill_levels = {}
        
        for skill in skills:
            skill_name = skill.get('skillName', '').lower()
            is_mandatory = skill.get('isMandatory', False)
            proficiency = skill.get('requiredProficiencyLevel') or 'intermediate'
            
            # Categorize by requirement type
            if is_mandatory:
                categorized_skills['mandatory'].append(skill_name)
            else:
                categorized_skills['preferred'].append(skill_name)
            
            # Categorize by skill type
            category = self._categorize_skill(skill_name)
            if category in categorized_skills:
                categorized_skills[category].append(skill_name)
            else:
                categorized_skills['technical'].append(skill_name)
            
            skill_levels[skill_name] = proficiency
        
        return {
            'categories': categorized_skills,
            'proficiency_requirements': skill_levels,
            'total_skills': len(skills),
            'mandatory_count': len(categorized_skills['mandatory']),
            'technical_depth': len(categorized_skills['technical']) + len(categorized_skills['frameworks']),
            'primary_technologies': self._identify_primary_technologies(skills)
        }
    
    def _categorize_skill(self, skill_name: str) -> str:
        """Categorize skill by type"""
        skill_lower = skill_name.lower()
        
        # Programming languages
        languages = ['python', 'java', 'javascript', 'c++', 'c#', 'go', 'rust', 'swift', 'kotlin']
        if any(lang in skill_lower for lang in languages):
            return 'languages'
        
        # Frameworks and libraries
        frameworks = ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'express', 'tensorflow', 'pytorch']
        if any(fw in skill_lower for fw in frameworks):
            return 'frameworks'
        
        # Tools
        tools = ['docker', 'kubernetes', 'jenkins', 'git', 'jira', 'figma', 'sketch']
        if any(tool in skill_lower for tool in tools):
            return 'tools'
        
        # Soft skills
        soft_skills = ['communication', 'leadership', 'teamwork', 'problem solving', 'analytical']
        if any(soft in skill_lower for soft in soft_skills):
            return 'soft_skills'
        
        return 'technical'
    
    def _determine_role_level(self, title: str, description: str) -> str:
        """Determine role seniority level"""
        combined_text = f"{title} {description}".lower()
        
        if any(term in combined_text for term in ['senior', 'lead', 'principal', 'staff', 'architect']):
            return 'senior'
        elif any(term in combined_text for term in ['junior', 'entry', 'associate', 'trainee']):
            return 'junior'
        elif any(term in combined_text for term in ['manager', 'director', 'head', 'vp']):
            return 'management'
        else:
            return 'mid-level'
    
    def _extract_technical_focus(self, description: str, skills: List[Dict]) -> List[str]:
        """Extract primary technical focus areas"""
        if not description:
            return []
        
        focus_areas = []
        description_lower = description.lower()
        
        # Define focus area keywords
        focus_keywords = {
            'machine_learning': ['ml', 'machine learning', 'ai', 'artificial intelligence', 'deep learning'],
            'web_development': ['web', 'frontend', 'backend', 'full-stack', 'ui/ux'],
            'data_science': ['data science', 'analytics', 'big data', 'data analysis'],
            'devops': ['devops', 'infrastructure', 'deployment', 'ci/cd', 'cloud'],
            'mobile': ['mobile', 'ios', 'android', 'react native', 'flutter'],
            'security': ['security', 'cybersecurity', 'encryption', 'penetration testing'],
            'database': ['database', 'sql', 'nosql', 'data modeling']
        }
        
        for area, keywords in focus_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                focus_areas.append(area.replace('_', ' ').title())
        
        return focus_areas[:3]  # Return top 3
    
    def _identify_growth_opportunities(self, description: str) -> List[str]:
        """Identify career growth opportunities from job description"""
        if not description:
            return []
        
        opportunities = []
        description_lower = description.lower()
        
        growth_indicators = {
            'leadership': ['lead', 'mentor', 'manage', 'guide', 'leadership'],
            'learning': ['learn', 'training', 'development', 'certification', 'growth'],
            'innovation': ['innovative', 'cutting-edge', 'research', 'experimental'],
            'scale': ['scale', 'enterprise', 'large-scale', 'high-volume'],
            'impact': ['impact', 'mission', 'transform', 'improve']
        }
        
        for opportunity, keywords in growth_indicators.items():
            if any(keyword in description_lower for keyword in keywords):
                opportunities.append(opportunity.title() + ' Development')
        
        return opportunities
    
    def _build_personalization_context(self, job: ExtendedJobCache, client: ClientCache, skills: List) -> Dict[str, Any]:
        """Build context for personalizing onboarding conversations"""
        context = {
            'company_name': client.client_name if client else 'the company',
            'role_title': job.title,
            'industry': client.industry if client else 'technology',
            'key_skills': [s.get('skillName') for s in skills[:5]],  # Top 5 skills
            'mandatory_skills': [s.get('skillName') for s in skills if s.get('isMandatory')],
            'role_focus': self._extract_technical_focus(job.description, skills),
            'seniority_level': self._determine_role_level(job.title, job.description),
            'location': f"{client.city}, {client.state}" if client and client.city else "remote/flexible"
        }
        
        return context
    
    def _determine_interview_focus(self, job: ExtendedJobCache, skills: List) -> Dict[str, Any]:
        """Determine what to focus on during AI interview"""
        mandatory_skills = [s for s in skills if s.get('isMandatory')]
        preferred_skills = [s for s in skills if not s.get('isMandatory')]
        
        focus = {
            'primary_skills_to_probe': [s.get('skillName') for s in mandatory_skills[:3]],
            'secondary_skills_to_explore': [s.get('skillName') for s in preferred_skills[:2]],
            'experience_level_to_assess': self._determine_role_level(job.title, job.description),
            'cultural_fit_areas': self._extract_cultural_indicators(job, None),
            'scenario_complexity': 'advanced' if 'senior' in job.title.lower() else 'intermediate'
        }
        
        return focus
    
    def _extract_cultural_indicators(self, job: ExtendedJobCache, client: Optional[ClientCache]) -> List[str]:
        """Extract cultural indicators from job and company data"""
        indicators = []
        
        if job.description:
            description_lower = job.description.lower()
            
            cultural_keywords = {
                'collaboration': ['team', 'collaborate', 'partnership', 'cross-functional'],
                'innovation': ['innovative', 'creative', 'cutting-edge', 'experimental'],
                'autonomy': ['independent', 'self-directed', 'ownership', 'autonomous'],
                'growth': ['growth', 'learning', 'development', 'career progression'],
                'impact': ['impact', 'mission-driven', 'meaningful', 'difference'],
                'quality': ['quality', 'excellence', 'best practices', 'standards']
            }
            
            for indicator, keywords in cultural_keywords.items():
                if any(keyword in description_lower for keyword in keywords):
                    indicators.append(indicator)
        
        return indicators[:4]  # Return top 4 indicators
    
    def _normalize_industry(self, industry: str) -> str:
        """Normalize industry string to match our insights categories"""
        if not industry:
            return 'technology'
        
        industry_lower = industry.lower()
        
        if any(term in industry_lower for term in ['tech', 'software', 'it', 'computer']):
            return 'technology'
        elif any(term in industry_lower for term in ['health', 'medical', 'pharma', 'hospital']):
            return 'healthcare'
        elif any(term in industry_lower for term in ['finance', 'bank', 'fintech', 'investment']):
            return 'finance'
        elif any(term in industry_lower for term in ['education', 'school', 'university', 'learning']):
            return 'education'
        elif any(term in industry_lower for term in ['manufacturing', 'production', 'industrial']):
            return 'manufacturing'
        else:
            return 'technology'  # Default fallback
    
    def _estimate_company_size(self, client: ClientCache) -> str:
        """Estimate company size based on available data"""
        # This is a placeholder - in reality, you'd use more sophisticated methods
        if client.notes and len(client.notes) > 500:
            return 'large'
        elif client.city and client.state:
            return 'medium'
        else:
            return 'startup'
    
    def _infer_business_focus(self, client: ClientCache) -> List[str]:
        """Infer business focus from client data"""
        focus_areas = []
        
        if client.industry:
            industry_lower = client.industry.lower()
            if 'consulting' in industry_lower:
                focus_areas.append('Consulting Services')
            elif 'product' in industry_lower:
                focus_areas.append('Product Development')
            elif 'service' in industry_lower:
                focus_areas.append('Service Delivery')
        
        if not focus_areas:
            focus_areas = ['Business Solutions']
        
        return focus_areas
    
    def _identify_primary_technologies(self, skills: List[Dict]) -> List[str]:
        """Identify primary technologies from skills list"""
        tech_skills = []
        
        for skill in skills:
            skill_name = skill.get('skillName', '')
            proficiency_level = skill.get('requiredProficiencyLevel') or ''
            if skill.get('isMandatory') or proficiency_level.lower() in ['expert', 'advanced']:
                tech_skills.append(skill_name)
        
        return tech_skills[:5]  # Return top 5


# Global instance
job_profile_analyzer = JobProfileAnalyzer()
