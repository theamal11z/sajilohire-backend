"""
Resume ingestion and processing service
"""

import re
from typing import List, Dict, Any
from models import ExtendedPerson
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class ResumeProcessor:
    """Service for processing and extracting data from resume text"""
    
    def __init__(self):
        # Common skill patterns
        self.skill_patterns = {
            'programming': ['python', 'java', 'javascript', 'c++', 'c#', 'go', 'rust', 'swift'],
            'web': ['react', 'angular', 'vue', 'html', 'css', 'nodejs', 'express', 'django', 'flask'],
            'database': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch'],
            'cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform'],
            'tools': ['git', 'jenkins', 'jira', 'confluence', 'slack', 'figma'],
        }
        
        # Experience level indicators
        self.experience_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp)',
            r'(?:over|more than)\s*(\d+)\s*years?',
            r'(\d+)-(\d+)\s*years?\s*(?:experience|exp)'
        ]
    
    def process_resume(self, person: ExtendedPerson, resume_text: str, db: Session) -> Dict[str, Any]:
        """Process resume text and extract structured data"""
        
        analysis = {
            'skills_detected': [],
            'experience_years': 0,
            'education_level': None,
            'key_achievements': [],
            'contact_info': {},
            'summary_quality': 0.0
        }
        
        if not resume_text:
            return analysis
        
        resume_lower = resume_text.lower()
        
        # Extract skills
        analysis['skills_detected'] = self._extract_skills(resume_lower)
        
        # Extract experience years
        analysis['experience_years'] = self._extract_experience_years(resume_lower)
        
        # Extract education level
        analysis['education_level'] = self._extract_education_level(resume_lower)
        
        # Extract achievements
        analysis['key_achievements'] = self._extract_achievements(resume_text)
        
        # Extract contact information
        analysis['contact_info'] = self._extract_contact_info(resume_text)
        
        # Assess summary quality
        analysis['summary_quality'] = self._assess_quality(resume_text)
        
        # Update person skills if not already set
        if not person.skills_tags and analysis['skills_detected']:
            person.skills_tags = analysis['skills_detected'][:10]  # Limit to top 10
            db.commit()
        
        logger.info(f"Processed resume for person {person.id}: {len(analysis['skills_detected'])} skills detected")
        return analysis
    
    def _extract_skills(self, resume_text: str) -> List[str]:
        """Extract technical skills from resume text"""
        detected_skills = []
        
        for category, skills in self.skill_patterns.items():
            for skill in skills:
                # Look for skill mentions (whole word matches)
                pattern = r'\b' + re.escape(skill.lower()) + r'\b'
                if re.search(pattern, resume_text):
                    detected_skills.append(skill)
        
        # Remove duplicates and return
        return list(set(detected_skills))
    
    def _extract_experience_years(self, resume_text: str) -> int:
        """Extract years of experience from resume text"""
        max_years = 0
        
        for pattern in self.experience_patterns:
            matches = re.findall(pattern, resume_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Range pattern like "3-5 years"
                    years = int(match[1])  # Take upper bound
                else:
                    years = int(match)
                
                max_years = max(max_years, years)
        
        return max_years
    
    def _extract_education_level(self, resume_text: str) -> str:
        """Extract education level from resume text"""
        education_keywords = {
            'phd': ['ph.d', 'phd', 'doctorate', 'doctoral'],
            'masters': ['master', 'mba', 'm.s', 'ms ', 'm.a', 'ma ', 'meng'],
            'bachelors': ['bachelor', 'b.s', 'bs ', 'b.a', 'ba ', 'b.tech', 'btech'],
            'associates': ['associate', 'a.a', 'aa ', 'a.s', 'as ']
        }
        
        for level, keywords in education_keywords.items():
            for keyword in keywords:
                if keyword in resume_text:
                    return level
        
        return 'other'
    
    def _extract_achievements(self, resume_text: str) -> List[str]:
        """Extract key achievements from resume text"""
        achievements = []
        
        # Look for bullet points or achievement indicators
        achievement_patterns = [
            r'[•\*\-]\s*(.+?)(?:\n|$)',
            r'(?:achieved|delivered|implemented|led|managed|increased|decreased|improved)\s+(.+?)(?:\.|,|\n|$)'
        ]
        
        for pattern in achievement_patterns:
            matches = re.findall(pattern, resume_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, str) and len(match.strip()) > 20:
                    achievements.append(match.strip()[:200])  # Limit length
        
        return achievements[:5]  # Limit to top 5
    
    def _extract_contact_info(self, resume_text: str) -> Dict[str, str]:
        """Extract contact information from resume text"""
        contact_info = {}
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, resume_text)
        if email_match:
            contact_info['email'] = email_match.group()
        
        # Phone pattern
        phone_pattern = r'(\+?1?[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phone_match = re.search(phone_pattern, resume_text)
        if phone_match:
            contact_info['phone'] = phone_match.group()
        
        # LinkedIn pattern
        linkedin_pattern = r'linkedin\.com/in/([a-zA-Z0-9-]+)'
        linkedin_match = re.search(linkedin_pattern, resume_text, re.IGNORECASE)
        if linkedin_match:
            contact_info['linkedin'] = f"https://linkedin.com/in/{linkedin_match.group(1)}"
        
        # GitHub pattern
        github_pattern = r'github\.com/([a-zA-Z0-9-]+)'
        github_match = re.search(github_pattern, resume_text, re.IGNORECASE)
        if github_match:
            contact_info['github'] = f"https://github.com/{github_match.group(1)}"
        
        return contact_info
    
    def _assess_quality(self, resume_text: str) -> float:
        """Assess overall quality of resume text"""
        if not resume_text:
            return 0.0
        
        quality_score = 0.0
        
        # Length check
        if len(resume_text) > 200:
            quality_score += 0.2
        if len(resume_text) > 500:
            quality_score += 0.2
        
        # Structure indicators
        structure_indicators = ['experience', 'education', 'skills', 'projects']
        for indicator in structure_indicators:
            if indicator.lower() in resume_text.lower():
                quality_score += 0.1
        
        # Professional language indicators
        professional_terms = ['responsible for', 'managed', 'developed', 'implemented', 'collaborated']
        for term in professional_terms:
            if term.lower() in resume_text.lower():
                quality_score += 0.05
        
        # Quantifiable achievements
        if re.search(r'\d+%', resume_text):  # Percentages
            quality_score += 0.1
        if re.search(r'\$\d+', resume_text):  # Dollar amounts
            quality_score += 0.1
        
        return min(quality_score, 1.0)


# Global resume processor instance
resume_processor = ResumeProcessor()
