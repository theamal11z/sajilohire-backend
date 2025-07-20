"""
Chat engine for AI interviewing using GPT-4o-mini
"""

import requests
import json
from typing import Dict, Any, List, Optional
from config import settings
from models import ExtendedPerson, ChatTurn, ChatTurnRole, ChatTurnIntent
from services.job_profile_service import job_profile_analyzer
from sqlalchemy.orm import Session
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GPTChatEngine:
    """GPT-based chat engine for candidate interviews"""
    
    def __init__(self):
        self.api_key = settings.GPT_API_KEY
        self.endpoint = settings.GPT_API_ENDPOINT
        self.model = settings.GPT_MODEL
        
        # Base prompts - will be enhanced with job profile data
        self.base_prompts = {
            ChatTurnIntent.SKILL_PROBE: "{skill_question}",  # Will be dynamically generated based on profile
            ChatTurnIntent.MOTIVATION: "Why are you interested in working with {company_name} in the {industry} industry? What attracts you to this {role_title} position?",
            ChatTurnIntent.TRAP: "When configuring ElasticCacheX Timed Graph Layer in Kubernetes autoscaling, what metrics mattered most? (This is an integrity check.)",
            ChatTurnIntent.VALUES: "For a {role_level} {role_title} at {company_name}, rank these in order of importance: {company_values}.",
            ChatTurnIntent.SCENARIO: "{scenario_context}. What are your first 3 steps?"
        }
    
    def start_conversation(
        self,
        person: ExtendedPerson,
        db: Session
    ) -> Dict[str, Any]:
        """Start the conversation with an initial AI greeting"""
        
        # Get comprehensive job profile for personalization
        job_profile = job_profile_analyzer.get_comprehensive_job_profile(person.job_id, db)
        if not job_profile:
            logger.warning(f"No job profile found for job_id {person.job_id}, using defaults")
            job_profile = {'job': {}, 'company': {}, 'personalization_context': {}}
        
        # Extract context
        company_info = job_profile.get('company', {})
        job_info = job_profile.get('job', {})
        company_name = company_info.get('name', 'our company')
        role_title = job_info.get('title', 'this role')
        
        # Create personalized greeting with enriched context
        greeting = self._build_personalized_greeting(person, company_name, role_title, job_profile)
        
        # Store AI greeting as first message
        ai_turn = ChatTurn(
            person_local_id=person.id,
            turn_index=0,
            role=ChatTurnRole.AI,
            intent=ChatTurnIntent.OTHER,
            content=greeting
        )
        db.add(ai_turn)
        
        # Update person's last chat timestamp
        person.last_chat_ts = datetime.now()
        db.commit()
        
        return {
            "agent_reply": greeting,
            "progress": 0.0,
            "turn_count": 1,
            "is_complete": False
        }
    
    def generate_response(
        self, 
        person: ExtendedPerson,
        user_message: str,
        chat_history: List[ChatTurn],
        db: Session
    ) -> Dict[str, Any]:
        """Generate AI response based on conversation context"""
        
        # Get comprehensive job profile for personalization
        job_profile = job_profile_analyzer.get_comprehensive_job_profile(person.job_id, db)
        if not job_profile:
            logger.warning(f"No job profile found for job_id {person.job_id}, using defaults")
            job_profile = {'job': {}, 'company': {}, 'personalization_context': {}}
        
        # Determine next intent and progress
        current_turn = len(chat_history)
        progress = min(current_turn / settings.CHAT_MIN_TURNS, 1.0)
        
        # Build conversation context with job profile
        system_prompt = self._build_system_prompt(person, job_profile)
        messages = self._build_message_history(chat_history, user_message, system_prompt)
        
        # Determine next question intent
        next_intent = self._determine_next_intent(chat_history)
        
        try:
            # Call GPT API
            gpt_response = self._call_gpt_api(messages)
            
            # Extract AI response from GPT
            ai_response = gpt_response.get('choices', [{}])[0].get('message', {}).get('content', 'Sorry, I had trouble processing your response. Could you please try again?')
            
            # Store user message
            user_turn = ChatTurn(
                person_local_id=person.id,
                turn_index=current_turn,
                role=ChatTurnRole.USER,
                intent=ChatTurnIntent.OTHER,
                content=user_message
            )
            db.add(user_turn)
            
            # Store AI response
            ai_turn = ChatTurn(
                person_local_id=person.id,
                turn_index=current_turn + 1,
                role=ChatTurnRole.AI,
                intent=next_intent,
                content=ai_response,
                analysis_json={"gpt_response": gpt_response}
            )
            db.add(ai_turn)
            db.commit()
            
            return {
                "agent_reply": ai_response,
                "progress": progress,
                "turn_count": current_turn + 2,
                "is_complete": progress >= 1.0
            }
            
        except Exception as e:
            logger.error(f"Failed to generate chat response: {e}")
            raise
    
    def _build_system_prompt(self, person: ExtendedPerson, job_profile: Dict[str, Any]) -> str:
        """Build system prompt with candidate and job context including enriched data"""
        
        # Extract job profile details
        company_info = job_profile.get('company', {})
        job_info = job_profile.get('job', {})
        personalization = job_profile.get('personalization_context', {})
        interview_focus = job_profile.get('interview_focus', {})
        cultural_indicators = job_profile.get('cultural_indicators', [])
        
        company_name = company_info.get('name', 'the company')
        industry = company_info.get('industry', 'technology')
        role_title = job_info.get('title', 'this role')
        role_level = job_info.get('role_level', 'mid-level')
        technical_focus = ', '.join(job_info.get('technical_focus', []))
        mandatory_skills = ', '.join(personalization.get('mandatory_skills', [])[:3])
        culture_keywords = ', '.join(cultural_indicators[:3])
        
        # Extract enriched insights for personalized conversation
        enriched_context = self._build_enriched_context(person)
        
        base_prompt = f"""You are an AI interviewer for {company_name}, a {industry} company, conducting a professional interview for a {role_level} {role_title} position.

Candidate: {person.first_name} {person.last_name}
Email: {person.email}
Candidate Skills: {', '.join(person.skills_tags) if person.skills_tags else 'To be assessed'}

Job Context:
- Company: {company_name} ({industry})
- Role: {role_title} ({role_level})
- Key Technical Areas: {technical_focus or 'General technical skills'}
- Critical Skills: {mandatory_skills or 'Various technical skills'}
- Company Culture: {culture_keywords or 'Professional environment'}

Resume Summary: {person.resume_text[:500] if person.resume_text else 'Not provided'}"""
        
        # Add enriched insights if available
        if enriched_context:
            base_prompt += f"\n\n{enriched_context}"
        
        base_prompt += f"""\n\nCONDUCT A NATURAL, PERSONALIZED CONVERSATION:
1. Reference specific projects, skills, or experiences you know about the candidate to show you've done your research
2. Ask thoughtful follow-up questions based on their actual background and achievements
3. Probe deeper into their experience with {mandatory_skills or 'relevant skills'}, referencing their real work
4. Assess cultural fit for {company_name} and motivation for this {role_title} role
5. Keep responses conversational but professional (2-3 sentences max)
6. Ask ONE focused question at a time
7. Build on what they just told you AND what you already know about them
8. Show genuine interest in their projects and accomplishments

Your goal is to have a natural, personalized interview conversation that demonstrates you understand the candidate's background. Make them feel like you've genuinely reviewed their profile and are interested in their specific experience."""
        
        return base_prompt
    
    def _build_enriched_context(self, person: ExtendedPerson) -> str:
        """Build enriched context from GitHub and social intelligence data"""
        context_parts = []
        
        # GitHub profile insights
        if person.github_data:
            github_context = self._extract_github_context(person.github_data)
            if github_context:
                context_parts.append(f"GitHub Profile Insights:\n{github_context}")
        
        # Social intelligence from PhantomBuster
        if person.phantombuster_data:
            social_context = self._extract_social_context(person.phantombuster_data)
            if social_context:
                context_parts.append(f"Professional Profile Analysis:\n{social_context}")
        
        # Trust and verification status
        if person.trust_score is not None:
            trust_context = self._extract_trust_context(person)
            if trust_context:
                context_parts.append(f"Profile Credibility:\n{trust_context}")
        
        return "\n\n".join(context_parts) if context_parts else ""
    
    def _extract_github_context(self, github_data: Dict[str, Any]) -> str:
        """Extract meaningful context from GitHub data"""
        context_lines = []
        
        # Basic GitHub info
        username = github_data.get('username')
        if username:
            context_lines.append(f"- GitHub: @{username}")
        
        # Repository analysis
        repo_analysis = github_data.get('repository_analysis', {})
        if repo_analysis:
            total_repos = repo_analysis.get('total_repos', 0)
            if total_repos > 0:
                context_lines.append(f"- {total_repos} public repositories")
            
            # Primary languages
            languages = repo_analysis.get('languages', {})
            if languages:
                top_langs = list(languages.keys())[:3]
                context_lines.append(f"- Primary languages: {', '.join(top_langs)}")
            
            # Notable projects
            notable_repos = repo_analysis.get('notable_repos', [])
            if notable_repos:
                top_repo = notable_repos[0]
                repo_name = top_repo.get('name', '')
                stars = top_repo.get('stars', 0)
                language = top_repo.get('language', '')
                if stars > 5:
                    context_lines.append(f"- Notable project: '{repo_name}' ({language}, {stars} stars)")
                elif repo_name:
                    context_lines.append(f"- Recent project: '{repo_name}' ({language})")
        
        # Technical profile
        tech_profile = github_data.get('technical_profile', {})
        specializations = tech_profile.get('specializations', [])
        if specializations:
            context_lines.append(f"- Technical focus: {', '.join(specializations[:2])}")
        
        # Activity and trust indicators
        activity_score = github_data.get('activity_score', 0)
        if activity_score > 0.7:
            context_lines.append("- Highly active developer")
        elif activity_score > 0.4:
            context_lines.append("- Moderately active developer")
        
        trust_indicators = github_data.get('trust_indicators', [])
        if 'established-account' in str(trust_indicators):
            context_lines.append("- Well-established GitHub presence")
        
        return "\n".join(context_lines) if context_lines else ""
    
    def _extract_social_context(self, phantombuster_data: Dict[str, Any]) -> str:
        """Extract meaningful context from PhantomBuster social intelligence"""
        context_lines = []
        
        # LinkedIn analysis
        linkedin_analysis = phantombuster_data.get('linkedin_analysis', {})
        if linkedin_analysis:
            basic_info = linkedin_analysis.get('basic_info', {})
            professional = linkedin_analysis.get('professional_details', {})
            
            # Current position
            current_position = professional.get('current_position')
            company = professional.get('company')
            if current_position and company:
                context_lines.append(f"- Current: {current_position} at {company}")
            elif current_position:
                context_lines.append(f"- Current position: {current_position}")
            
            # Experience years
            exp_years = professional.get('experience_years', 0)
            if exp_years > 0:
                context_lines.append(f"- {exp_years} years of professional experience")
            
            # Location
            location = basic_info.get('location')
            if location:
                context_lines.append(f"- Located in {location}")
            
            # Network strength
            network_metrics = linkedin_analysis.get('network_metrics', {})
            connections = network_metrics.get('connections_count', 0)
            if connections > 500:
                context_lines.append("- Strong professional network (500+ connections)")
            elif connections > 100:
                context_lines.append("- Good professional network (100+ connections)")
        
        # Professional insights from comprehensive analysis
        prof_insights = phantombuster_data.get('professional_insights', {})
        if prof_insights:
            career_trajectory = prof_insights.get('career_trajectory')
            if career_trajectory == 'ascending':
                context_lines.append("- Demonstrated career growth")
            
            industry_expertise = prof_insights.get('industry_expertise', [])
            if industry_expertise:
                context_lines.append(f"- Industry expertise: {', '.join(industry_expertise[:2])}")
        
        return "\n".join(context_lines) if context_lines else ""
    
    def _extract_trust_context(self, person: ExtendedPerson) -> str:
        """Extract trust and credibility context"""
        context_lines = []
        
        trust_score = person.trust_score or 0
        if trust_score >= 0.8:
            context_lines.append("- High credibility score across platforms")
        elif trust_score >= 0.6:
            context_lines.append("- Good profile consistency")
        
        verification_status = person.social_verification_status
        if verification_status == 'verified':
            context_lines.append("- Cross-platform identity verified")
        elif verification_status == 'needs_review':
            context_lines.append("- Profile under verification")
        
        # Risk indicators from PhantomBuster
        if person.phantombuster_data:
            risk_indicators = person.phantombuster_data.get('risk_indicators', [])
            if not risk_indicators or len(risk_indicators) == 0:
                context_lines.append("- No red flags identified")
        
        return "\n".join(context_lines) if context_lines else ""
    
    def _build_personalized_greeting(self, person: ExtendedPerson, company_name: str, role_title: str, job_profile: Dict[str, Any]) -> str:
        """Build personalized greeting using enriched candidate data"""
        
        # Start with basic greeting
        greeting = f"Hello {person.first_name}! Welcome to the AI interview process for the {role_title} position at {company_name}."
        
        # Add personalized elements based on available data
        personal_details = []
        
        # GitHub insights
        if person.github_data:
            github_insights = self._get_github_greeting_insights(person.github_data)
            if github_insights:
                personal_details.extend(github_insights)
        
        # LinkedIn/Social insights  
        if person.phantombuster_data:
            social_insights = self._get_social_greeting_insights(person.phantombuster_data)
            if social_insights:
                personal_details.extend(social_insights)
        
        # Add personalized context to greeting
        if personal_details:
            greeting += f" I've had a chance to review your profile and I'm impressed by {', '.join(personal_details)}."
        
        # Professional transition
        greeting += " I'm excited to learn more about your background and discuss how your experience aligns with this role."
        
        # Conversational starter
        if personal_details:
            greeting += " Let's start by having you walk me through your journey and what led you to apply for this position."
        else:
            greeting += " Let's start with a brief introduction - can you tell me about yourself and your relevant experience?"
        
        return greeting
    
    def _get_github_greeting_insights(self, github_data: Dict[str, Any]) -> List[str]:
        """Extract noteworthy GitHub insights for greeting"""
        insights = []
        
        # Notable repositories
        repo_analysis = github_data.get('repository_analysis', {})
        notable_repos = repo_analysis.get('notable_repos', [])
        if notable_repos:
            top_repo = notable_repos[0]
            stars = top_repo.get('stars', 0)
            repo_name = top_repo.get('name', '')
            if stars > 10:
                insights.append(f"your '{repo_name}' project with {stars} stars")
            elif repo_name:
                insights.append(f"your recent work on '{repo_name}'")
        
        # Technical breadth
        languages = repo_analysis.get('languages', {})
        if len(languages) >= 3:
            top_langs = list(languages.keys())[:2]
            insights.append(f"your expertise in {' and '.join(top_langs)}")
        
        # Activity level
        activity_score = github_data.get('activity_score', 0)
        if activity_score > 0.7:
            insights.append("your active contributions to the developer community")
        
        return insights
    
    def _get_social_greeting_insights(self, phantombuster_data: Dict[str, Any]) -> List[str]:
        """Extract noteworthy social/professional insights for greeting"""
        insights = []
        
        linkedin_analysis = phantombuster_data.get('linkedin_analysis', {})
        if linkedin_analysis:
            professional = linkedin_analysis.get('professional_details', {})
            
            # Current role
            current_position = professional.get('current_position')
            company = professional.get('company')
            if current_position and company:
                insights.append(f"your experience as {current_position} at {company}")
            
            # Professional network
            network_metrics = linkedin_analysis.get('network_metrics', {})
            connections = network_metrics.get('connections_count', 0)
            if connections > 500:
                insights.append("your strong professional network")
            
            # Experience level
            exp_years = professional.get('experience_years', 0)
            if exp_years >= 5:
                insights.append(f"your {exp_years} years of professional experience")
        
        # Professional insights
        prof_insights = phantombuster_data.get('professional_insights', {})
        career_trajectory = prof_insights.get('career_trajectory')
        if career_trajectory == 'ascending':
            insights.append("your demonstrated career growth")
        
        return insights
    
    def _build_message_history(
        self, 
        chat_history: List[ChatTurn], 
        user_message: str,
        system_prompt: str
    ) -> List[Dict[str, str]]:
        """Build message history for GPT API"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add historical turns
        for turn in chat_history[-10:]:  # Last 10 turns for context
            role = "assistant" if turn.role == ChatTurnRole.AI else "user"
            messages.append({"role": role, "content": turn.content})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def _determine_next_intent(self, chat_history: List[ChatTurn]) -> ChatTurnIntent:
        """Determine the next question intent based on conversation flow"""
        intent_sequence = settings.CHAT_INTENTS
        current_index = len([t for t in chat_history if t.role == ChatTurnRole.AI])
        
        if current_index < len(intent_sequence):
            intent_name = intent_sequence[current_index]
            return ChatTurnIntent(intent_name)
        
        return ChatTurnIntent.OTHER
    
    def _generate_ai_question(self, intent: ChatTurnIntent, person: ExtendedPerson, job_profile: Dict[str, Any]) -> str:
        """Generate appropriate question based on intent and job profile"""
        
        # Extract context from job profile
        company_info = job_profile.get('company', {})
        job_info = job_profile.get('job', {})
        personalization = job_profile.get('personalization_context', {})
        interview_focus = job_profile.get('interview_focus', {})
        
        company_name = company_info.get('name', 'our company')
        industry = company_info.get('industry', 'technology')
        role_title = job_info.get('title', 'this role')
        role_level = job_info.get('role_level', 'mid-level')
        
        if intent in self.base_prompts:
            prompt_template = self.base_prompts[intent]
            
            # Fill in template variables based on intent
            if intent == ChatTurnIntent.SKILL_PROBE:
                skill_question = self._generate_personalized_skill_question(person, job_profile, company_name, role_title)
                return prompt_template.format(skill_question=skill_question)
                
            elif intent == ChatTurnIntent.MOTIVATION:
                return prompt_template.format(
                    company_name=company_name,
                    industry=industry,
                    role_title=role_title
                )
                
            elif intent == ChatTurnIntent.VALUES:
                company_values = self._get_company_values(company_info)
                return prompt_template.format(
                    role_level=role_level,
                    role_title=role_title,
                    company_name=company_name,
                    company_values=company_values
                )
                
            elif intent == ChatTurnIntent.SCENARIO:
                scenario = self._generate_role_specific_scenario(job_info, role_level)
                return prompt_template.format(scenario_context=scenario)
                
            else:
                return prompt_template
        
        return f"Can you tell me more about your experience and what motivates you to work as a {role_title} at {company_name}?"
    
    def _generate_personalized_skill_question(self, person: ExtendedPerson, job_profile: Dict[str, Any], company_name: str, role_title: str) -> str:
        """Generate personalized skill question based on candidate's actual experience and projects"""
        
        # Get skill to probe
        skill = self._select_skill_to_probe(person, job_profile)
        
        # Try to find specific project/experience to reference
        project_reference = self._find_relevant_project_reference(person, skill)
        professional_reference = self._find_professional_reference(person, skill)
        
        # Build personalized question
        if project_reference:
            return f"I noticed your '{project_reference['name']}' project using {skill}. Can you walk me through the technical challenges you faced and how you solved them? How does this experience relate to the {role_title} responsibilities at {company_name}?"
        elif professional_reference:
            return f"I see you've worked with {skill} in your role as {professional_reference}. Tell me about the most complex implementation you've worked on and how it prepared you for this {role_title} position."
        else:
            # Fallback to more generic but still personal question
            return f"You listed {skill} as one of your skills. Describe the most challenging project where you used it extensively. What was your role and how does it relate to {role_title} responsibilities at {company_name}?"
    
    def _find_relevant_project_reference(self, person: ExtendedPerson, skill: str) -> Optional[Dict[str, Any]]:
        """Find GitHub project that uses the specified skill"""
        if not person.github_data:
            return None
        
        repo_analysis = person.github_data.get('repository_analysis', {})
        notable_repos = repo_analysis.get('notable_repos', [])
        
        # Look for repos that use the skill (language match)
        skill_lower = skill.lower()
        for repo in notable_repos[:5]:  # Check top 5 repos
            repo_lang = repo.get('language', '').lower()
            repo_name = repo.get('name', '')
            
            # Direct language match
            if skill_lower == repo_lang:
                return {'name': repo_name, 'language': repo_lang, 'stars': repo.get('stars', 0)}
            
            # Check if skill is mentioned in repo topics or description
            description = repo.get('description', '').lower()
            if skill_lower in description and repo_name:
                return {'name': repo_name, 'language': repo_lang, 'stars': repo.get('stars', 0)}
        
        # If no specific repo found, return the most notable one if it exists
        if notable_repos:
            top_repo = notable_repos[0]
            return {
                'name': top_repo.get('name', 'recent project'), 
                'language': top_repo.get('language', skill), 
                'stars': top_repo.get('stars', 0)
            }
        
        return None
    
    def _find_professional_reference(self, person: ExtendedPerson, skill: str) -> Optional[str]:
        """Find professional experience reference for the skill"""
        if not person.phantombuster_data:
            return None
        
        linkedin_analysis = person.phantombuster_data.get('linkedin_analysis', {})
        if linkedin_analysis:
            professional = linkedin_analysis.get('professional_details', {})
            current_position = professional.get('current_position')
            company = professional.get('company')
            
            if current_position and company:
                return f"{current_position} at {company}"
            elif current_position:
                return current_position
        
        return None
    
    def _select_skill_to_probe(self, person: ExtendedPerson, job_profile: Dict[str, Any]) -> str:
        """Select most relevant skill to probe based on job requirements"""
        mandatory_skills = job_profile.get('personalization_context', {}).get('mandatory_skills', [])
        candidate_skills = person.skills_tags or []
        
        # Find intersection of candidate skills and mandatory job skills
        matching_skills = [skill for skill in candidate_skills if skill and skill.lower() in [ms.lower() for ms in mandatory_skills if ms]]
        
        if matching_skills:
            return matching_skills[0]  # Probe the first matching mandatory skill
        elif candidate_skills:
            return candidate_skills[0]  # Fallback to first candidate skill
        elif mandatory_skills and mandatory_skills[0]:
            return mandatory_skills[0]  # Ask about required skill they didn't mention
        else:
            return "your primary technical skill"
    
    def _get_company_values(self, company_info: Dict[str, Any]) -> str:
        """Get company values for ranking exercise"""
        industry_insights = company_info.get('industry_insights', {})
        values = industry_insights.get('values', ['Mission Impact', 'Learning Opportunities', 'Work-Life Balance', 'Compensation'])
        return ', '.join(values)
    
    def _generate_role_specific_scenario(self, job_info: Dict[str, Any], role_level: str) -> str:
        """Generate role-specific scenario based on job context"""
        technical_focus = job_info.get('technical_focus', [])
        role_title = job_info.get('title', 'technical role')
        
        # Generate scenario based on technical focus
        if 'Machine Learning' in technical_focus:
            if role_level == 'senior':
                return "Your ML model in production is showing degraded performance affecting 100K+ users"
            else:
                return "Your machine learning model's accuracy has dropped from 95% to 80% in production"
                
        elif 'Web Development' in technical_focus:
            if role_level == 'senior':
                return "Your e-commerce platform is experiencing 500% traffic surge during Black Friday"
            else:
                return "Your web application is loading slowly and users are complaining"
                
        elif 'Data Science' in technical_focus:
            if role_level == 'senior':
                return "Executive team questions your data analysis results that contradict their assumptions"
            else:
                return "Your data pipeline breaks and tomorrow's executive report depends on it"
                
        else:
            # Generic scenario
            if role_level == 'senior':
                return "Critical system failure at midnight affects thousands of customers"
            else:
                return "Production issue at midnight blocks customers"
    
    
    def _call_gpt_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Make API call to GPT endpoint"""
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        
        payload = {
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.7,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        
        response = requests.post(
            self.endpoint,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()


# Global chat engine instance
chat_engine = GPTChatEngine()
