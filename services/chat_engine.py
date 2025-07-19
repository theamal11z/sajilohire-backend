"""
Chat engine for AI interviewing using GPT-4o-mini
"""

import requests
import json
from typing import Dict, Any, List, Optional
from config import settings
from models import ExtendedPerson, ChatTurn, ChatTurnRole, ChatTurnIntent
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class GPTChatEngine:
    """GPT-based chat engine for candidate interviews"""
    
    def __init__(self):
        self.api_key = settings.GPT_API_KEY
        self.endpoint = settings.GPT_API_ENDPOINT
        self.model = settings.GPT_MODEL
        
        # Predefined prompts for different interview intents
        self.prompts = {
            ChatTurnIntent.SKILL_PROBE: "You listed {skill}. Describe the most complex project where you used it. What was your role?",
            ChatTurnIntent.MOTIVATION: "Why are you interested in working with {company_name}?",
            ChatTurnIntent.TRAP: "When configuring ElasticCacheX Timed Graph Layer in Kubernetes autoscaling, what metrics mattered most? (This is an integrity check.)",
            ChatTurnIntent.VALUES: "Rank these in order of importance: Mission Impact, Salary, Learning Opportunities, Work-Life Balance.",
            ChatTurnIntent.SCENARIO: "Production issue at midnight blocks customers. What are your first 3 steps?"
        }
    
    def generate_response(
        self, 
        person: ExtendedPerson,
        user_message: str,
        chat_history: List[ChatTurn],
        db: Session
    ) -> Dict[str, Any]:
        """Generate AI response based on conversation context"""
        
        # Determine next intent and progress
        current_turn = len(chat_history)
        progress = min(current_turn / settings.CHAT_MIN_TURNS, 1.0)
        
        # Build conversation context
        system_prompt = self._build_system_prompt(person)
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
            
            # Generate appropriate AI response
            ai_response = self._generate_ai_question(next_intent, person)
            
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
    
    def _build_system_prompt(self, person: ExtendedPerson) -> str:
        """Build system prompt with candidate context"""
        return f"""You are an AI interviewer conducting a professional interview.
        
Candidate: {person.first_name} {person.last_name}
Email: {person.email}
Skills: {', '.join(person.skills_tags)}

Job Context: Job ID {person.job_id}
Resume Summary: {person.resume_text[:500] if person.resume_text else 'Not provided'}

Your goal is to assess:
1. Technical competency and depth
2. Motivation and cultural alignment  
3. Consistency and credibility
4. Career stability and turnover risk

Ask thoughtful, probing questions. Be professional but conversational."""
    
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
    
    def _generate_ai_question(self, intent: ChatTurnIntent, person: ExtendedPerson) -> str:
        """Generate appropriate question based on intent"""
        if intent in self.prompts:
            prompt_template = self.prompts[intent]
            
            # Fill in template variables
            if "{skill}" in prompt_template and person.skills_tags:
                skill = person.skills_tags[0] if person.skills_tags else "your primary skill"
                return prompt_template.format(skill=skill)
            elif "{company_name}" in prompt_template:
                return prompt_template.format(company_name="our company")
            else:
                return prompt_template
        
        return "Can you tell me more about your experience and what motivates you in your career?"
    
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
