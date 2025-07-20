"""
GitHub Profile Enrichment Service
Fetches GitHub profile data to enhance candidate profiles for HR teams
"""

import requests
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class GitHubEnrichmentService:
    """Service for fetching and analyzing GitHub profile data"""
    
    def __init__(self):
        self.base_api_url = "https://api.github.com"
        self.timeout = 10
        
        # Programming language mappings
        self.language_skills = {
            'Python': ['python', 'django', 'flask', 'fastapi'],
            'JavaScript': ['javascript', 'nodejs', 'react', 'vue', 'angular'],
            'TypeScript': ['typescript', 'angular', 'react'],
            'Java': ['java', 'spring', 'maven'],
            'Go': ['go', 'golang'],
            'Rust': ['rust'],
            'C++': ['cpp', 'c++'],
            'C#': ['csharp', 'dotnet'],
            'PHP': ['php', 'laravel', 'symfony'],
            'Ruby': ['ruby', 'rails'],
            'Swift': ['swift', 'ios'],
            'Kotlin': ['kotlin', 'android'],
            'HTML': ['html', 'css'],
            'CSS': ['css', 'scss', 'sass']
        }
    
    def extract_github_username(self, github_url: str) -> Optional[str]:
        """Extract GitHub username from various URL formats"""
        if not github_url:
            return None
        
        # Handle different GitHub URL formats
        patterns = [
            r'github\.com/([a-zA-Z0-9-]+)(?:/.*)?$',  # https://github.com/username or with paths
            r'^([a-zA-Z0-9-]+)$'  # Just username
        ]
        
        for pattern in patterns:
            match = re.search(pattern, github_url.strip('/'))
            if match:
                username = match.group(1)
                # Filter out common GitHub paths that aren't usernames
                if username.lower() not in ['orgs', 'organizations', 'explore', 'marketplace', 'pricing', 'features']:
                    return username
        
        return None
    
    def enrich_profile(self, github_url: str) -> Dict[str, Any]:
        """Fetch comprehensive GitHub profile data"""
        username = self.extract_github_username(github_url)
        if not username:
            logger.warning(f"Could not extract username from GitHub URL: {github_url}")
            return {}
        
        try:
            # Get user profile
            profile_data = self._fetch_user_profile(username)
            if not profile_data:
                return {}
            
            # Get repositories
            repos_data = self._fetch_repositories(username)
            
            # Analyze repositories
            repo_analysis = self._analyze_repositories(repos_data)
            
            # Build comprehensive profile
            enriched_profile = {
                'username': username,
                'profile_url': f"https://github.com/{username}",
                'avatar_url': profile_data.get('avatar_url'),
                'name': profile_data.get('name'),
                'bio': profile_data.get('bio'),
                'company': profile_data.get('company'),
                'location': profile_data.get('location'),
                'blog': profile_data.get('blog'),
                'twitter_username': profile_data.get('twitter_username'),
                'public_repos': profile_data.get('public_repos', 0),
                'followers': profile_data.get('followers', 0),
                'following': profile_data.get('following', 0),
                'created_at': profile_data.get('created_at'),
                'updated_at': profile_data.get('updated_at'),
                
                # Repository analysis
                'repository_analysis': repo_analysis,
                'skills_detected': list(repo_analysis.get('languages', {}).keys()),
                'activity_score': self._calculate_activity_score(profile_data, repos_data),
                'trust_indicators': self._extract_trust_indicators(profile_data, repos_data),
                'technical_profile': self._build_technical_profile(repo_analysis),
                'enrichment_timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Successfully enriched GitHub profile for {username}")
            return enriched_profile
            
        except Exception as e:
            logger.error(f"Failed to enrich GitHub profile for {github_url}: {e}")
            return {}
    
    def _fetch_user_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch user profile from GitHub API"""
        try:
            url = f"{self.base_api_url}/users/{username}"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"GitHub user not found: {username}")
                return None
            else:
                logger.error(f"GitHub API error for user {username}: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching GitHub user {username}: {e}")
            return None
    
    def _fetch_repositories(self, username: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch user's public repositories"""
        try:
            url = f"{self.base_api_url}/users/{username}/repos"
            params = {
                'type': 'owner',
                'sort': 'updated',
                'per_page': min(limit, 100)
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Could not fetch repositories for {username}: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching repositories for {username}: {e}")
            return []
    
    def _analyze_repositories(self, repos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze repositories for technical insights"""
        if not repos:
            return {}
        
        analysis = {
            'total_repos': len(repos),
            'languages': {},
            'topics': set(),
            'frameworks': set(),
            'recent_activity': [],
            'repo_stats': {
                'total_stars': 0,
                'total_forks': 0,
                'avg_stars': 0,
                'has_readme': 0,
                'has_tests': 0
            },
            'notable_repos': []
        }
        
        for repo in repos:
            # Language analysis
            if repo.get('language'):
                lang = repo['language']
                analysis['languages'][lang] = analysis['languages'].get(lang, 0) + 1
            
            # Topics and frameworks
            if repo.get('topics'):
                analysis['topics'].update(repo['topics'])
            
            # Repository stats
            analysis['repo_stats']['total_stars'] += repo.get('stargazers_count', 0)
            analysis['repo_stats']['total_forks'] += repo.get('forks_count', 0)
            
            if repo.get('description'):
                analysis['repo_stats']['has_readme'] += 1
            
            # Notable repositories (high stars or recent activity)
            if (repo.get('stargazers_count', 0) > 5 or 
                self._is_recently_active(repo.get('updated_at'))):
                analysis['notable_repos'].append({
                    'name': repo['name'],
                    'description': repo.get('description', ''),
                    'language': repo.get('language'),
                    'stars': repo.get('stargazers_count', 0),
                    'forks': repo.get('forks_count', 0),
                    'updated_at': repo.get('updated_at'),
                    'url': repo.get('html_url')
                })
            
            # Recent activity
            if self._is_recently_active(repo.get('updated_at'), days=30):
                analysis['recent_activity'].append({
                    'repo': repo['name'],
                    'updated_at': repo.get('updated_at'),
                    'language': repo.get('language')
                })
        
        # Calculate averages
        if analysis['total_repos'] > 0:
            analysis['repo_stats']['avg_stars'] = analysis['repo_stats']['total_stars'] / analysis['total_repos']
        
        # Convert sets to lists for JSON serialization
        analysis['topics'] = list(analysis['topics'])
        analysis['frameworks'] = list(analysis['frameworks'])
        
        # Sort languages by frequency
        analysis['languages'] = dict(sorted(analysis['languages'].items(), key=lambda x: x[1], reverse=True))
        
        # Sort notable repos by stars
        analysis['notable_repos'] = sorted(analysis['notable_repos'], key=lambda x: x['stars'], reverse=True)[:10]
        
        return analysis
    
    def _is_recently_active(self, updated_at: str, days: int = 90) -> bool:
        """Check if repository was updated recently"""
        if not updated_at:
            return False
        
        try:
            update_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            cutoff_time = datetime.now(update_time.tzinfo) - timedelta(days=days)
            return update_time > cutoff_time
        except:
            return False
    
    def _calculate_activity_score(self, profile: Dict[str, Any], repos: List[Dict[str, Any]]) -> float:
        """Calculate developer activity score (0.0 to 1.0)"""
        if not profile or not repos:
            return 0.0
        
        score = 0.0
        
        # Repository count (normalized)
        repo_count = min(profile.get('public_repos', 0) / 20, 1.0) * 0.3
        score += repo_count
        
        # Followers (social proof)
        followers = min(profile.get('followers', 0) / 100, 1.0) * 0.2
        score += followers
        
        # Recent activity (last 90 days)
        recent_repos = sum(1 for repo in repos if self._is_recently_active(repo.get('updated_at')))
        recent_activity = min(recent_repos / 5, 1.0) * 0.3
        score += recent_activity
        
        # Repository engagement (stars + forks)
        total_engagement = sum(repo.get('stargazers_count', 0) + repo.get('forks_count', 0) for repo in repos)
        engagement = min(total_engagement / 50, 1.0) * 0.2
        score += engagement
        
        return min(score, 1.0)
    
    def _extract_trust_indicators(self, profile: Dict[str, Any], repos: List[Dict[str, Any]]) -> List[str]:
        """Extract trust and credibility indicators"""
        indicators = []
        
        if not profile:
            return indicators
        
        # Account age
        created_at = profile.get('created_at')
        if created_at:
            try:
                create_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                age_years = (datetime.now(create_time.tzinfo) - create_time).days / 365
                if age_years >= 2:
                    indicators.append(f"established-account-{int(age_years)}years")
            except:
                pass
        
        # Repository count
        repo_count = profile.get('public_repos', 0)
        if repo_count >= 10:
            indicators.append("active-contributor")
        if repo_count >= 50:
            indicators.append("prolific-developer")
        
        # Social proof
        followers = profile.get('followers', 0)
        if followers >= 10:
            indicators.append("community-recognized")
        if followers >= 100:
            indicators.append("influential-developer")
        
        # Profile completeness
        if profile.get('name'):
            indicators.append("complete-profile")
        if profile.get('bio'):
            indicators.append("detailed-bio")
        if profile.get('company'):
            indicators.append("professional-affiliation")
        
        # Repository quality
        if repos:
            avg_stars = sum(repo.get('stargazers_count', 0) for repo in repos) / len(repos)
            if avg_stars >= 2:
                indicators.append("quality-projects")
        
        # Recent activity
        recent_activity = any(self._is_recently_active(repo.get('updated_at'), 30) for repo in repos)
        if recent_activity:
            indicators.append("recently-active")
        
        return indicators
    
    def _build_technical_profile(self, repo_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Build technical profile from repository analysis"""
        languages = repo_analysis.get('languages', {})
        topics = repo_analysis.get('topics', [])
        
        # Map languages to broader skill categories
        skill_categories = {
            'backend': ['Python', 'Java', 'Go', 'Rust', 'PHP', 'Ruby', 'C#'],
            'frontend': ['JavaScript', 'TypeScript', 'HTML', 'CSS'],
            'mobile': ['Swift', 'Kotlin', 'Java'],
            'systems': ['C', 'C++', 'Rust', 'Go'],
            'data': ['Python', 'R', 'Jupyter Notebook']
        }
        
        profile = {
            'primary_languages': list(languages.keys())[:5],
            'language_diversity': len(languages),
            'specializations': [],
            'experience_indicators': {}
        }
        
        # Determine specializations
        for category, category_langs in skill_categories.items():
            if any(lang in languages for lang in category_langs):
                profile['specializations'].append(category)
        
        # Experience indicators from topics
        for topic in topics:
            topic_lower = topic.lower()
            if any(keyword in topic_lower for keyword in ['machine-learning', 'ai', 'ml']):
                profile['experience_indicators']['machine_learning'] = True
            elif any(keyword in topic_lower for keyword in ['web', 'api', 'rest']):
                profile['experience_indicators']['web_development'] = True
            elif any(keyword in topic_lower for keyword in ['devops', 'docker', 'kubernetes']):
                profile['experience_indicators']['devops'] = True
            elif any(keyword in topic_lower for keyword in ['mobile', 'android', 'ios']):
                profile['experience_indicators']['mobile_development'] = True
        
        return profile


# Global GitHub enrichment service instance
github_enrichment_service = GitHubEnrichmentService()
