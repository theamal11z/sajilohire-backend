"""
OpenAI-based Cross-Platform Analysis Service
Analyzes consistency between LinkedIn and GitHub profiles using AI
"""

import requests
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OpenAICrossPlatformAnalyzer:
    """Cross-platform profile analysis using OpenAI GPT-4o-mini"""
    
    def __init__(self):
        self.api_key = "F0f8PjPGohraL0zjmrmWfix0ABy5iXmToB0O9fzNxGyKpP5nZkX7JQQJ99BFACHrzpqXJ3w3AAABACOGYk5Y"
        self.endpoint = "https://aqore-hackathon-openai.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2025-01-01-preview"
        self.timeout = 30
    
    def analyze_cross_platform_consistency(self, linkedin_data: Dict[str, Any], github_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze consistency between LinkedIn and GitHub profiles using OpenAI"""
        
        try:
            # Build analysis prompt
            analysis_prompt = self._build_analysis_prompt(linkedin_data, github_data)
            
            # Call OpenAI API
            response = self._call_openai_api(analysis_prompt)
            
            if response:
                # Parse OpenAI response to extract insights
                parsed_result = self._parse_analysis_response(response)
                return parsed_result
            else:
                return self._get_default_analysis()
                
        except Exception as e:
            logger.error(f"Cross-platform analysis failed: {e}")
            return self._get_default_analysis()
    
    def _build_analysis_prompt(self, linkedin_data: Dict[str, Any], github_data: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt for OpenAI"""
        
        # Extract LinkedIn details
        linkedin_info = self._extract_linkedin_info(linkedin_data) or {}
        
        # Extract GitHub details  
        github_info = self._extract_github_info(github_data) or {}
        
        prompt = f"""
You are an expert HR analyst specializing in candidate verification. Analyze the consistency between LinkedIn and GitHub profiles.

LINKEDIN PROFILE:
- Name: {linkedin_info.get('name', 'Not provided')}
- Current Position: {linkedin_info.get('current_position', 'Not provided')}
- Company: {linkedin_info.get('company', 'Not provided')}
- Location: {linkedin_info.get('location', 'Not provided')}
- Experience: {linkedin_info.get('experience_years', 'Not provided')} years
- Skills: {', '.join(linkedin_info.get('skills', []))}
- Education: {linkedin_info.get('education', 'Not provided')}
- Industry: {linkedin_info.get('industry', 'Not provided')}
- Professional Summary: {linkedin_info.get('summary', 'Not provided')[:200]}

GITHUB PROFILE:
- Username: {github_info.get('username', 'Not provided')}
- Name: {github_info.get('name', 'Not provided')}
- Company: {github_info.get('company', 'Not provided')}
- Location: {github_info.get('location', 'Not provided')}
- Bio: {github_info.get('bio', 'Not provided')}
- Public Repositories: {github_info.get('public_repos', 0)}
- Primary Languages: {', '.join(github_info.get('languages', []))}
- Repository Topics: {', '.join(github_info.get('topics', []))}
- Account Created: {github_info.get('created_at', 'Not provided')}
- Recent Activity: {github_info.get('recent_activity', 'Not provided')}

ANALYSIS TASK:
Compare these profiles and provide:
1. Consistency Score (0.0 to 1.0) - How well the profiles align
2. Specific Inconsistencies - List any discrepancies found
3. Verification Status - 'verified', 'needs_review', or 'inconsistent'
4. Professional Alignment - How well GitHub activity matches LinkedIn claims
5. Timeline Consistency - Whether career progression makes sense

Please respond in this JSON format:
{{
    "consistency_score": 0.85,
    "verification_status": "verified",
    "inconsistencies": ["List any specific inconsistencies"],
    "professional_alignment": "High/Medium/Low",
    "timeline_consistency": "Consistent/Inconsistent",
    "detailed_analysis": "Brief explanation of your assessment",
    "red_flags": ["Any concerning discrepancies"],
    "trust_indicators": ["Positive verification signals"]
}}
"""
        return prompt
    
    def _extract_linkedin_info(self, linkedin_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant information from LinkedIn data"""
        if not linkedin_data:
            return {}
            
        basic_info = linkedin_data.get('basic_info', {})
        professional = linkedin_data.get('professional_details', {})
        
        return {
            'name': basic_info.get('name'),
            'current_position': professional.get('current_position'),
            'company': professional.get('company'),
            'location': basic_info.get('location'),
            'experience_years': professional.get('experience_years'),
            'skills': professional.get('skills', []),
            'education': professional.get('education'),
            'industry': basic_info.get('industry'),
            'summary': basic_info.get('summary')
        }
    
    def _extract_github_info(self, github_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant information from GitHub data"""
        if not github_data:
            return {}
            
        # Handle different GitHub data structures
        if 'username' in github_data:  # Our enriched GitHub data format
            return {
                'username': github_data.get('username'),
                'name': github_data.get('name'),
                'company': github_data.get('company'),
                'location': github_data.get('location'),
                'bio': github_data.get('bio'),
                'public_repos': github_data.get('public_repos', 0),
                'languages': list(github_data.get('repository_analysis', {}).get('languages', {}).keys()),
                'topics': github_data.get('repository_analysis', {}).get('topics', []),
                'created_at': github_data.get('created_at'),
                'recent_activity': len(github_data.get('repository_analysis', {}).get('recent_activity', []))
            }
        else:  # Raw GitHub API data format
            return {
                'username': github_data.get('login'),
                'name': github_data.get('name'),
                'company': github_data.get('company'),
                'location': github_data.get('location'),
                'bio': github_data.get('bio'),
                'public_repos': github_data.get('public_repos', 0),
                'languages': github_data.get('languages', []),
                'topics': github_data.get('topics', []),
                'created_at': github_data.get('created_at'),
                'recent_activity': github_data.get('recent_activity', 'No recent activity data')
            }
    
    def _call_openai_api(self, prompt: str) -> Optional[str]:
        """Make API call to OpenAI"""
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        
        payload = {
            "messages": [
                {
                    "role": "system", 
                    "content": "You are an expert HR analyst specializing in candidate profile verification and consistency analysis."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 800,
            "temperature": 0.3,
            "top_p": 1.0
        }
        
        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('choices', [{}])[0].get('message', {}).get('content', '')
            else:
                logger.error(f"OpenAI API call failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"OpenAI API call exception: {e}")
            return None
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse OpenAI response to extract structured analysis"""
        
        try:
            # Try to parse JSON response
            if '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                parsed = json.loads(json_str)
                
                # Validate and normalize the response
                return {
                    'consistency_score': float(parsed.get('consistency_score', 0.5)),
                    'verification_status': parsed.get('verification_status', 'needs_review'),
                    'inconsistencies': parsed.get('inconsistencies', []),
                    'professional_alignment': parsed.get('professional_alignment', 'Medium'),
                    'timeline_consistency': parsed.get('timeline_consistency', 'Unknown'),
                    'detailed_analysis': parsed.get('detailed_analysis', 'Analysis completed'),
                    'red_flags': parsed.get('red_flags', []),
                    'trust_indicators': parsed.get('trust_indicators', []),
                    'analysis_timestamp': datetime.utcnow().isoformat()
                }
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Fallback to text parsing
            return self._parse_text_response(response)
            
        return self._get_default_analysis()
    
    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """Fallback text parsing if JSON parsing fails"""
        
        # Extract consistency score using regex
        score_match = re.search(r'(?:consistency|score)[:\s]*([0-1]\.?[0-9]*)', response.lower())
        consistency_score = float(score_match.group(1)) if score_match else 0.5
        
        # Determine verification status based on score and keywords
        if consistency_score >= 0.8 or 'verified' in response.lower():
            verification_status = 'verified'
        elif consistency_score >= 0.6 or 'review' in response.lower():
            verification_status = 'needs_review'
        else:
            verification_status = 'inconsistent'
        
        # Extract inconsistencies
        inconsistencies = []
        if 'inconsistenc' in response.lower() or 'discrepanc' in response.lower():
            inconsistencies.append("Potential inconsistencies detected in text analysis")
        
        return {
            'consistency_score': consistency_score,
            'verification_status': verification_status,
            'inconsistencies': inconsistencies,
            'professional_alignment': 'Medium',
            'timeline_consistency': 'Unknown',
            'detailed_analysis': response[:500] if response else 'Text analysis completed',
            'red_flags': [],
            'trust_indicators': [],
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Return default analysis when OpenAI analysis fails"""
        return {
            'consistency_score': 0.5,
            'verification_status': 'needs_review',
            'inconsistencies': ['Unable to complete automated analysis'],
            'professional_alignment': 'Unknown',
            'timeline_consistency': 'Unknown',
            'detailed_analysis': 'Cross-platform analysis could not be completed',
            'red_flags': ['Analysis failed - manual review recommended'],
            'trust_indicators': [],
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
    
    def generate_hr_insights(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate HR-friendly insights from the analysis"""
        insights = []
        
        consistency_score = analysis_result.get('consistency_score', 0.5)
        verification_status = analysis_result.get('verification_status', 'needs_review')
        
        # Score-based insights
        if consistency_score >= 0.9:
            insights.append("✅ Excellent profile consistency - high confidence in candidate authenticity")
        elif consistency_score >= 0.7:
            insights.append("✅ Good profile alignment - candidate appears credible")
        elif consistency_score >= 0.5:
            insights.append("⚠️ Moderate consistency - some areas may need clarification")
        else:
            insights.append("🚨 Low consistency score - recommend detailed verification")
        
        # Red flags
        red_flags = analysis_result.get('red_flags', [])
        if red_flags:
            insights.append(f"🚨 Red flags identified: {', '.join(red_flags)}")
        
        # Trust indicators
        trust_indicators = analysis_result.get('trust_indicators', [])
        if trust_indicators:
            insights.append(f"✅ Trust indicators: {', '.join(trust_indicators)}")
        
        # Professional alignment
        alignment = analysis_result.get('professional_alignment', 'Medium')
        if alignment == 'High':
            insights.append("✅ Strong alignment between claimed skills and GitHub activity")
        elif alignment == 'Low':
            insights.append("⚠️ Limited evidence of claimed skills in GitHub activity")
        
        # Timeline consistency
        timeline = analysis_result.get('timeline_consistency', 'Unknown')
        if timeline == 'Inconsistent':
            insights.append("⚠️ Timeline inconsistencies detected - verify employment dates")
        
        return insights


# Global analyzer instance
openai_cross_platform_analyzer = OpenAICrossPlatformAnalyzer()
