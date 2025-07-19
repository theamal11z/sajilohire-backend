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
            ChatTurnIntent.SKILL_PROBE: "You listed {skill}. Describe the most complex project where you used it. What was your role and how does it relate to {role_context}?",
            ChatTurnIntent.MOTIVATION: "Why are you interested in working with {company_name} in the {industry} industry? What attracts you to this {role_title} position?",
            ChatTurnIntent.TRAP: "When configuring ElasticCacheX Timed Graph Layer in Kubernetes autoscaling, what metrics mattered most? (This is an integrity check.)",
            ChatTurnIntent.VALUES: "For a {role_level} {role_title} at {company_name}, rank these in order of importance: {company_values}.",
            ChatTurnIntent.SCENARIO: "{scenario_context}. What are your first 3 steps?"
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
            response = self._call_gpt_api(messages)
            
            # Store user message
            user_turn = ChatTurn(
                person_local_id=person.id,
                turn_index=current_turn,
                role=ChatTurnRole.USER,
                intent=ChatTurnIntent.OTHER,
                content=user_message
            )
            db.add(user_turn)
            
            # Generate appropriate AI response with job profile context
            ai_response = self._generate_ai_question(next_intent, person, job_profile)
            
            # Store AI response
            ai_turn = ChatTurn(
                person_local_id=person.id,
                turn_index=current_turn + 1,
                role=ChatTurnRole.AI,
                intent=next_intent,
                content=ai_response,
                analysis_json={"gpt_response": response}
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
        """Build system prompt with candidate and job context"""
        
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
        
        return f"""You are an AI interviewer for {company_name}, a {industry} company, conducting a professional interview for a {role_level} {role_title} position.
        
Candidate: {person.first_name} {person.last_name}
Email: {person.email}
Candidate Skills: {', '.join(person.skills_tags) if person.skills_tags else 'To be assessed'}

Job Context:
- Company: {company_name} ({industry})
- Role: {role_title} ({role_level})
- Key Technical Areas: {technical_focus or 'General technical skills'}
- Critical Skills: {mandatory_skills or 'Various technical skills'}
- Company Culture: {culture_keywords or 'Professional environment'}

Resume Summary: {person.resume_text[:500] if person.resume_text else 'Not provided'}

Your assessment goals:
1. Technical competency in {mandatory_skills or 'required skills'}
2. Cultural alignment with {company_name}'s values ({culture_keywords})
3. Motivation for {role_title} role and {industry} industry
4. Experience depth and consistency
5. Career stability and growth potential

Adapt your questions to the {role_level} level and focus on {technical_focus or 'relevant technical areas'}. Be professional, engaging, and assess both technical and cultural fit for {company_name}."""
    
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
                skill = self._select_skill_to_probe(person, job_profile)
                role_context = f"{role_title} responsibilities at {company_name}"
                return prompt_template.format(skill=skill, role_context=role_context)
                
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
    
    def _select_skill_to_probe(self, person: ExtendedPerson, job_profile: Dict[str, Any]) -> str:
        """Select most relevant skill to probe based on job requirements"""
        mandatory_skills = job_profile.get('personalization_context', {}).get('mandatory_skills', [])
        candidate_skills = person.skills_tags or []
        
        # Find intersection of candidate skills and mandatory job skills
        matching_skills = [skill for skill in candidate_skills if skill.lower() in [ms.lower() for ms in mandatory_skills]]
        
        if matching_skills:
            return matching_skills[0]  # Probe the first matching mandatory skill
        elif candidate_skills:
            return candidate_skills[0]  # Fallback to first candidate skill
        elif mandatory_skills:
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
