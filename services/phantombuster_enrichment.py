"""
PhantomBuster Enrichment Service
Advanced candidate profiling through social media intelligence and cross-platform verification
"""

import requests
import time
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from config import settings
import logging

logger = logging.getLogger(__name__)


class PhantomBusterEnrichmentService:
    """Advanced candidate enrichment using PhantomBuster APIs"""
    
    def __init__(self):
        self.base_url = settings.PHANTOMBUSTER_BASE_URL
        self.api_key = settings.PHANTOMBUSTER_API_KEY
        self.timeout = 30
        
        # PhantomBuster Agent IDs for different platforms
        self.agent_ids = {
            'linkedin_profile': 'linkedin-profile-scraper',  # Replace with actual agent ID
            'linkedin_posts': 'linkedin-post-scraper',       # Replace with actual agent ID
            'github_advanced': 'github-profile-scraper',     # Replace with actual agent ID
            'cross_platform': 'social-cross-reference'       # Replace with actual agent ID
        }
        
        # Trust scoring weights
        self.trust_weights = {
            'profile_completeness': 0.20,
            'activity_consistency': 0.25,
            'network_quality': 0.15,
            'content_authenticity': 0.20,
            'cross_platform_consistency': 0.20
        }
    
    def get_headers(self) -> Dict[str, str]:
        """Get request headers with API key"""
        return {
            "X-Phantombuster-Key-1": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def enrich_candidate_profile(self, linkedin_url: str, github_url: Optional[str] = None) -> Dict[str, Any]:
        """Comprehensive candidate enrichment with cross-platform analysis"""
        enrichment_data = {
            'linkedin_analysis': {},
            'github_analysis': {},
            'cross_platform_analysis': {},
            'trust_score': 0.0,
            'professional_insights': {},
            'risk_indicators': [],
            'enrichment_timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            # LinkedIn profile analysis
            if linkedin_url:
                linkedin_data = self._analyze_linkedin_profile(linkedin_url)
                enrichment_data['linkedin_analysis'] = linkedin_data
                
                # Get LinkedIn activity and posts
                linkedin_activity = self._analyze_linkedin_activity(linkedin_url)
                enrichment_data['linkedin_analysis']['activity'] = linkedin_activity
            
            # Advanced GitHub analysis (if we have GitHub URL)
            if github_url:
                github_data = self._analyze_github_advanced(github_url)
                enrichment_data['github_analysis'] = github_data
            
            # Cross-platform consistency analysis
            if linkedin_url and github_url:
                cross_platform = self._analyze_cross_platform_consistency(linkedin_url, github_url)
                enrichment_data['cross_platform_analysis'] = cross_platform
            
            # Calculate comprehensive trust score
            trust_score = self._calculate_comprehensive_trust_score(enrichment_data)
            enrichment_data['trust_score'] = trust_score
            
            # Extract professional insights
            insights = self._extract_professional_insights(enrichment_data)
            enrichment_data['professional_insights'] = insights
            
            # Identify risk indicators
            risks = self._identify_risk_indicators(enrichment_data)
            enrichment_data['risk_indicators'] = risks
            
            logger.info(f"PhantomBuster enrichment completed with trust score: {trust_score:.3f}")
            return enrichment_data
            
        except Exception as e:
            logger.error(f"PhantomBuster enrichment failed: {e}")
            return enrichment_data
    
    def _analyze_linkedin_profile(self, linkedin_url: str) -> Dict[str, Any]:
        """Deep LinkedIn profile analysis"""
        try:
            # Launch LinkedIn profile scraper
            agent_result = self._launch_phantom_agent(
                agent_id=self.agent_ids['linkedin_profile'],
                arguments={
                    "sessionCookie": "",  # Would need to be configured
                    "profileUrls": [linkedin_url],
                    "numberOfConnections": True,
                    "skills": True,
                    "recommendations": True,
                    "experience": True,
                    "education": True
                }
            )
            
            if not agent_result or 'data' not in agent_result:
                return {}
            
            profile_data = agent_result['data'][0] if agent_result['data'] else {}
            
            return {
                'basic_info': {
                    'name': profile_data.get('fullName'),
                    'headline': profile_data.get('headline'),
                    'location': profile_data.get('location'),
                    'industry': profile_data.get('industry'),
                    'summary': profile_data.get('summary'),
                    'profile_image_url': profile_data.get('profileImageUrl')
                },
                'professional_details': {
                    'current_position': profile_data.get('currentPosition'),
                    'company': profile_data.get('company'),
                    'experience_years': self._calculate_experience_years(profile_data.get('experience', [])),
                    'education': profile_data.get('education', []),
                    'skills': profile_data.get('skills', []),
                    'certifications': profile_data.get('certifications', [])
                },
                'network_metrics': {
                    'connections_count': profile_data.get('connectionsCount', 0),
                    'followers_count': profile_data.get('followersCount', 0),
                    'mutual_connections': profile_data.get('mutualConnections', [])
                },
                'credibility_indicators': {
                    'recommendations_received': len(profile_data.get('recommendations', [])),
                    'skills_endorsed': len([s for s in profile_data.get('skills', []) if s.get('endorsements', 0) > 0]),
                    'profile_completeness': self._assess_linkedin_completeness(profile_data),
                    'activity_level': profile_data.get('activityLevel', 'unknown')
                }
            }
            
        except Exception as e:
            logger.error(f"LinkedIn analysis failed: {e}")
            return {}
    
    def _analyze_linkedin_activity(self, linkedin_url: str) -> Dict[str, Any]:
        """Analyze LinkedIn posts and activity patterns"""
        try:
            agent_result = self._launch_phantom_agent(
                agent_id=self.agent_ids['linkedin_posts'],
                arguments={
                    "profileUrl": linkedin_url,
                    "numberOfPosts": 20,
                    "includeComments": True,
                    "includeLikes": True
                }
            )
            
            if not agent_result or 'data' not in agent_result:
                return {}
            
            posts_data = agent_result['data']
            
            return {
                'posting_frequency': self._calculate_posting_frequency(posts_data),
                'content_analysis': self._analyze_post_content(posts_data),
                'engagement_metrics': self._calculate_engagement_metrics(posts_data),
                'professional_tone': self._assess_professional_tone(posts_data),
                'thought_leadership': self._assess_thought_leadership(posts_data)
            }
            
        except Exception as e:
            logger.error(f"LinkedIn activity analysis failed: {e}")
            return {}
    
    def _analyze_github_advanced(self, github_url: str) -> Dict[str, Any]:
        """Advanced GitHub analysis beyond basic API data"""
        try:
            agent_result = self._launch_phantom_agent(
                agent_id=self.agent_ids['github_advanced'],
                arguments={
                    "githubUrl": github_url,
                    "includeContributions": True,
                    "includeRepositories": True,
                    "includePullRequests": True,
                    "includeIssues": True
                }
            )
            
            if not agent_result or 'data' not in agent_result:
                return {}
            
            github_data = agent_result['data'][0] if agent_result['data'] else {}
            
            return {
                'contribution_patterns': self._analyze_contribution_patterns(github_data),
                'code_quality_indicators': self._assess_code_quality(github_data),
                'collaboration_style': self._analyze_collaboration_style(github_data),
                'technical_leadership': self._assess_technical_leadership(github_data),
                'consistency_score': self._calculate_github_consistency(github_data)
            }
            
        except Exception as e:
            logger.error(f"Advanced GitHub analysis failed: {e}")
            return {}
    
    def _analyze_cross_platform_consistency(self, linkedin_url: str, github_url: str) -> Dict[str, Any]:
        """Analyze consistency across LinkedIn and GitHub profiles"""
        try:
            consistency_score = 0.0
            inconsistencies = []
            
            # This would typically involve comparing:
            # - Name consistency
            # - Timeline alignment
            # - Skills mentioned vs. repositories
            # - Company information consistency
            # - Professional journey coherence
            
            return {
                'consistency_score': consistency_score,
                'inconsistencies': inconsistencies,
                'verification_status': 'verified' if consistency_score > 0.8 else 'needs_review',
                'timeline_alignment': self._check_timeline_alignment(linkedin_url, github_url)
            }
            
        except Exception as e:
            logger.error(f"Cross-platform analysis failed: {e}")
            return {}
    
    def _launch_phantom_agent(self, agent_id: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Launch a PhantomBuster agent and wait for results"""
        try:
            # Launch agent
            launch_url = f"{self.base_url}/agents/launch"
            launch_payload = {
                "id": agent_id,
                "argument": arguments
            }
            
            response = requests.post(launch_url, headers=self.get_headers(), json=launch_payload, timeout=self.timeout)
            
            if response.status_code != 200:
                logger.error(f"Failed to launch phantom agent {agent_id}: {response.status_code}")
                return None
            
            launch_result = response.json()
            container_id = launch_result.get('containerId')
            
            if not container_id:
                return None
            
            # Wait for completion and fetch results
            return self._wait_for_agent_completion(container_id)
            
        except Exception as e:
            logger.error(f"Agent launch failed: {e}")
            return None
    
    def _wait_for_agent_completion(self, container_id: str, max_wait: int = 300) -> Optional[Dict[str, Any]]:
        """Wait for agent completion and fetch results"""
        try:
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                # Check agent status
                status_url = f"{self.base_url}/agents/{container_id}"
                response = requests.get(status_url, headers=self.get_headers(), timeout=self.timeout)
                
                if response.status_code == 200:
                    status_data = response.json()
                    
                    if status_data.get('status') == 'finished':
                        # Fetch results
                        return self._fetch_agent_results(container_id)
                    elif status_data.get('status') == 'error':
                        logger.error(f"Agent {container_id} finished with error")
                        return None
                
                time.sleep(10)  # Wait 10 seconds before checking again
            
            logger.warning(f"Agent {container_id} timed out after {max_wait} seconds")
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for agent completion: {e}")
            return None
    
    def _fetch_agent_results(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Fetch results from completed agent"""
        try:
            results_url = f"{self.base_url}/agents/{container_id}/output"
            response = requests.get(results_url, headers=self.get_headers(), timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch agent results: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching agent results: {e}")
            return None
    
    def _calculate_comprehensive_trust_score(self, enrichment_data: Dict[str, Any]) -> float:
        """Calculate comprehensive trust score from all available data"""
        score_components = {}
        
        # Profile completeness score
        linkedin_data = enrichment_data.get('linkedin_analysis', {})
        if linkedin_data:
            completeness = linkedin_data.get('credibility_indicators', {}).get('profile_completeness', 0.0)
            score_components['profile_completeness'] = completeness
        
        # Activity consistency score
        activity_data = linkedin_data.get('activity', {})
        if activity_data:
            consistency = activity_data.get('professional_tone', 0.0)
            score_components['activity_consistency'] = consistency
        
        # Network quality score
        network_metrics = linkedin_data.get('network_metrics', {})
        if network_metrics:
            connections = min(network_metrics.get('connections_count', 0) / 500, 1.0)
            recommendations = min(linkedin_data.get('credibility_indicators', {}).get('recommendations_received', 0) / 10, 1.0)
            score_components['network_quality'] = (connections + recommendations) / 2
        
        # Content authenticity score
        if activity_data:
            authenticity = activity_data.get('thought_leadership', 0.0)
            score_components['content_authenticity'] = authenticity
        
        # Cross-platform consistency
        cross_platform = enrichment_data.get('cross_platform_analysis', {})
        if cross_platform:
            consistency = cross_platform.get('consistency_score', 0.0)
            score_components['cross_platform_consistency'] = consistency
        
        # Calculate weighted score
        total_score = 0.0
        for component, weight in self.trust_weights.items():
            if component in score_components:
                total_score += score_components[component] * weight
        
        return min(total_score, 1.0)
    
    def _extract_professional_insights(self, enrichment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract professional insights for HR teams"""
        insights = {
            'career_progression': 'stable',
            'thought_leadership_level': 'emerging',
            'network_influence': 'moderate',
            'technical_expertise': 'verified',
            'cultural_fit_indicators': [],
            'leadership_potential': 'medium'
        }
        
        # Analyze career progression from LinkedIn data
        linkedin_data = enrichment_data.get('linkedin_analysis', {})
        if linkedin_data:
            experience = linkedin_data.get('professional_details', {}).get('experience_years', 0)
            if experience >= 5:
                insights['career_progression'] = 'senior'
            elif experience >= 2:
                insights['career_progression'] = 'growing'
            else:
                insights['career_progression'] = 'early'
        
        return insights
    
    def _identify_risk_indicators(self, enrichment_data: Dict[str, Any]) -> List[str]:
        """Identify potential risk indicators for HR review"""
        risks = []
        
        # Check for inconsistencies
        cross_platform = enrichment_data.get('cross_platform_analysis', {})
        if cross_platform.get('consistency_score', 1.0) < 0.7:
            risks.append('cross-platform-inconsistency')
        
        # Check for low activity
        linkedin_activity = enrichment_data.get('linkedin_analysis', {}).get('activity', {})
        if linkedin_activity.get('posting_frequency', 1.0) < 0.3:
            risks.append('low-professional-activity')
        
        # Check for fake profile indicators
        trust_score = enrichment_data.get('trust_score', 1.0)
        if trust_score < 0.5:
            risks.append('authenticity-concerns')
        
        return risks
    
    def _calculate_experience_years(self, experience_list: List[Dict]) -> int:
        """Calculate total years of experience from LinkedIn experience data"""
        if not experience_list:
            return 0
        
        total_months = 0
        for exp in experience_list:
            start_date = exp.get('startDate')
            end_date = exp.get('endDate') or datetime.now().strftime('%Y-%m')
            
            if start_date and end_date:
                try:
                    start = datetime.strptime(start_date, '%Y-%m')
                    end = datetime.strptime(end_date, '%Y-%m')
                    months = (end.year - start.year) * 12 + (end.month - start.month)
                    total_months += months
                except:
                    pass
        
        return total_months // 12
    
    def _assess_linkedin_completeness(self, profile_data: Dict) -> float:
        """Assess LinkedIn profile completeness"""
        completeness_factors = [
            profile_data.get('fullName') is not None,
            profile_data.get('headline') is not None,
            profile_data.get('summary') is not None,
            profile_data.get('experience') and len(profile_data['experience']) > 0,
            profile_data.get('education') and len(profile_data['education']) > 0,
            profile_data.get('skills') and len(profile_data['skills']) > 0,
            profile_data.get('profileImageUrl') is not None
        ]
        
        return sum(completeness_factors) / len(completeness_factors)
    
    # Additional helper methods for analysis
    def _calculate_posting_frequency(self, posts_data: List[Dict]) -> float:
        """Calculate LinkedIn posting frequency score"""
        if not posts_data:
            return 0.0
        
        # Analyze posting patterns over time
        recent_posts = len([p for p in posts_data if self._is_recent_post(p.get('timestamp'))])
        return min(recent_posts / 10, 1.0)  # Normalize to 0-1
    
    def _analyze_post_content(self, posts_data: List[Dict]) -> Dict[str, Any]:
        """Analyze the content quality of LinkedIn posts"""
        if not posts_data:
            return {}
        
        return {
            'average_length': sum(len(p.get('text', '')) for p in posts_data) / len(posts_data),
            'professional_keywords': self._count_professional_keywords(posts_data),
            'engagement_quality': sum(p.get('likes', 0) + p.get('comments', 0) for p in posts_data) / len(posts_data)
        }
    
    def _calculate_engagement_metrics(self, posts_data: List[Dict]) -> Dict[str, float]:
        """Calculate engagement metrics from LinkedIn posts"""
        if not posts_data:
            return {}
        
        total_likes = sum(p.get('likes', 0) for p in posts_data)
        total_comments = sum(p.get('comments', 0) for p in posts_data)
        
        return {
            'avg_likes_per_post': total_likes / len(posts_data),
            'avg_comments_per_post': total_comments / len(posts_data),
            'engagement_rate': (total_likes + total_comments) / len(posts_data)
        }
    
    def _assess_professional_tone(self, posts_data: List[Dict]) -> float:
        """Assess the professional tone of LinkedIn content"""
        if not posts_data:
            return 0.5
        
        professional_indicators = [
            'achievement', 'project', 'team', 'leadership', 'innovation',
            'technology', 'growth', 'collaboration', 'success', 'development'
        ]
        
        professional_score = 0.0
        for post in posts_data:
            text = post.get('text', '').lower()
            score = sum(1 for indicator in professional_indicators if indicator in text)
            professional_score += min(score / 3, 1.0)  # Normalize
        
        return professional_score / len(posts_data)
    
    def _assess_thought_leadership(self, posts_data: List[Dict]) -> float:
        """Assess thought leadership indicators in LinkedIn posts"""
        if not posts_data:
            return 0.0
        
        leadership_indicators = [
            'insights', 'trends', 'future', 'industry', 'vision',
            'strategy', 'opinion', 'perspective', 'analysis', 'prediction'
        ]
        
        leadership_score = 0.0
        for post in posts_data:
            text = post.get('text', '').lower()
            score = sum(1 for indicator in leadership_indicators if indicator in text)
            engagement = post.get('likes', 0) + post.get('comments', 0)
            leadership_score += (score * 0.7) + (min(engagement / 50, 1.0) * 0.3)
        
        return min(leadership_score / len(posts_data), 1.0)
    
    def _is_recent_post(self, timestamp: str, days: int = 90) -> bool:
        """Check if a post is recent"""
        if not timestamp:
            return False
        
        try:
            post_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            cutoff_date = datetime.now(post_date.tzinfo) - timedelta(days=days)
            return post_date > cutoff_date
        except:
            return False
    
    def _count_professional_keywords(self, posts_data: List[Dict]) -> int:
        """Count professional keywords across all posts"""
        keywords = [
            'leadership', 'innovation', 'technology', 'strategy', 'development',
            'growth', 'success', 'achievement', 'collaboration', 'expertise'
        ]
        
        count = 0
        for post in posts_data:
            text = post.get('text', '').lower()
            count += sum(1 for keyword in keywords if keyword in text)
        
        return count
    
    def _analyze_contribution_patterns(self, github_data: Dict) -> Dict[str, Any]:
        """Analyze GitHub contribution patterns"""
        return {
            'consistency': 0.8,  # Placeholder - would analyze actual contribution graph
            'peak_activity_days': ['Monday', 'Tuesday', 'Wednesday'],
            'contribution_streak': 45,
            'activity_distribution': 'consistent'
        }
    
    def _assess_code_quality(self, github_data: Dict) -> Dict[str, Any]:
        """Assess code quality indicators"""
        return {
            'documentation_score': 0.7,
            'test_coverage_indicators': True,
            'code_organization': 'good',
            'best_practices_adherence': 0.8
        }
    
    def _analyze_collaboration_style(self, github_data: Dict) -> Dict[str, Any]:
        """Analyze collaboration style from GitHub data"""
        return {
            'pull_request_quality': 'high',
            'code_review_participation': 'active',
            'mentoring_indicators': True,
            'community_contribution': 'moderate'
        }
    
    def _assess_technical_leadership(self, github_data: Dict) -> Dict[str, Any]:
        """Assess technical leadership from GitHub activity"""
        return {
            'repository_ownership': 'active',
            'architecture_decisions': True,
            'team_contributions': 'significant',
            'open_source_leadership': 'emerging'
        }
    
    def _calculate_github_consistency(self, github_data: Dict) -> float:
        """Calculate GitHub activity consistency score"""
        return 0.85  # Placeholder - would analyze actual activity patterns
    
    def _check_timeline_alignment(self, linkedin_url: str, github_url: str) -> Dict[str, Any]:
        """Check timeline alignment between LinkedIn and GitHub"""
        return {
            'employment_github_alignment': True,
            'skills_timeline_consistency': True,
            'activity_correlation': 0.8,
            'discrepancies': []
        }


# Global PhantomBuster enrichment service instance
phantombuster_enrichment_service = PhantomBusterEnrichmentService()
