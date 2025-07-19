"""
Enhanced Chat Engine with Advanced AI Analytics
Features: Sentiment analysis, personality detection, adaptive questioning, behavioral insights
"""

import re
from typing import Dict, Any, List, Optional
from textblob import TextBlob
from collections import Counter
import numpy as np
from datetime import datetime

class EnhancedChatAnalytics:
    """Advanced analytics for chat interactions"""
    
    def __init__(self):
        self.personality_indicators = {
            'analytical': ['analyze', 'data', 'metrics', 'measure', 'evaluate', 'systematic'],
            'creative': ['innovative', 'creative', 'design', 'imagine', 'brainstorm', 'artistic'],
            'leadership': ['lead', 'manage', 'team', 'delegate', 'mentor', 'guide', 'direct'],
            'collaborative': ['collaborate', 'together', 'team', 'share', 'communicate', 'group'],
            'detail_oriented': ['detail', 'precise', 'accurate', 'thorough', 'careful', 'exact']
        }
        
        self.stress_indicators = [
            'difficult', 'challenging', 'struggle', 'hard', 'tough', 'problem',
            'issue', 'concern', 'worry', 'stress', 'pressure'
        ]
        
        self.confidence_indicators = [
            'confident', 'sure', 'certain', 'definitely', 'absolutely', 'expert',
            'proficient', 'skilled', 'experienced', 'successful'
        ]
    
    def analyze_response_depth(self, response: str) -> Dict[str, float]:
        """Analyze the depth and quality of candidate responses"""
        
        word_count = len(response.split())
        sentence_count = len([s for s in response.split('.') if s.strip()])
        
        # Technical depth indicators
        technical_keywords = ['implement', 'architecture', 'design', 'optimize', 'scale', 
                            'performance', 'algorithm', 'framework', 'database', 'api']
        technical_score = len([word for word in technical_keywords if word.lower() in response.lower()]) / len(technical_keywords)
        
        # Specificity indicators (numbers, specific tools, dates)
        specificity_patterns = [
            r'\d+%',  # Percentages
            r'\d+ (years?|months?)',  # Time periods
            r'[A-Z][a-z]+\s?(API|SDK|DB|Framework)',  # Specific technologies
        ]
        specificity_count = sum(len(re.findall(pattern, response)) for pattern in specificity_patterns)
        
        # Story structure (beginning, middle, end)
        story_indicators = ['first', 'then', 'finally', 'result', 'outcome', 'learned']
        story_score = len([word for word in story_indicators if word.lower() in response.lower()]) / len(story_indicators)
        
        return {
            'word_count': word_count,
            'technical_depth': technical_score,
            'specificity_score': min(specificity_count / 3, 1.0),
            'story_structure': story_score,
            'overall_depth': (technical_score + story_score + min(specificity_count / 3, 1.0)) / 3
        }
    
    def detect_personality_traits(self, chat_history: List[str]) -> Dict[str, float]:
        """Detect personality traits from conversation patterns"""
        
        combined_text = ' '.join(chat_history).lower()
        trait_scores = {}
        
        for trait, keywords in self.personality_indicators.items():
            keyword_count = sum(1 for keyword in keywords if keyword in combined_text)
            trait_scores[trait] = min(keyword_count / len(keywords), 1.0)
        
        return trait_scores
    
    def analyze_communication_style(self, response: str) -> Dict[str, Any]:
        """Analyze communication style and emotional indicators"""
        
        # Sentiment analysis
        blob = TextBlob(response)
        sentiment = blob.sentiment
        
        # Confidence vs uncertainty indicators
        uncertainty_words = ['maybe', 'perhaps', 'might', 'could', 'possibly', 'not sure']
        confidence_score = len([word for word in self.confidence_indicators if word.lower() in response.lower()])
        uncertainty_score = len([word for word in uncertainty_words if word.lower() in response.lower()])
        
        # Communication clarity (sentence structure)
        sentences = response.split('.')
        avg_sentence_length = np.mean([len(s.split()) for s in sentences if s.strip()])
        
        # Stress indicators
        stress_score = len([word for word in self.stress_indicators if word.lower() in response.lower()])
        
        return {
            'sentiment_polarity': sentiment.polarity,  # -1 to 1
            'sentiment_subjectivity': sentiment.subjectivity,  # 0 to 1
            'confidence_level': confidence_score - uncertainty_score,
            'communication_clarity': min(avg_sentence_length / 15, 1.0),  # Optimal around 15 words
            'stress_indicators': stress_score,
            'overall_tone': 'positive' if sentiment.polarity > 0.1 else 'negative' if sentiment.polarity < -0.1 else 'neutral'
        }
    
    def generate_behavioral_insights(self, chat_analysis: Dict[str, Any]) -> List[str]:
        """Generate behavioral insights for HR teams"""
        insights = []
        
        # Communication style insights
        if chat_analysis.get('communication_clarity', 0) > 0.8:
            insights.append("Demonstrates clear and structured communication")
        
        # Confidence insights
        confidence = chat_analysis.get('confidence_level', 0)
        if confidence > 2:
            insights.append("Shows high confidence in abilities")
        elif confidence < -1:
            insights.append("May need confidence building in certain areas")
        
        # Technical depth insights
        if chat_analysis.get('overall_depth', 0) > 0.7:
            insights.append("Provides detailed technical explanations")
        
        # Stress handling insights
        if chat_analysis.get('stress_indicators', 0) > 3:
            insights.append("May experience stress in challenging situations")
        
        return insights

class AdaptiveQuestionEngine:
    """Generates adaptive questions based on candidate analysis"""
    
    def __init__(self):
        self.question_templates = {
            'high_confidence': [
                "You seem very confident in your {skill} abilities. Can you walk me through a time when this confidence was tested?",
                "Given your strong background in {skill}, how would you mentor someone just starting out?"
            ],
            'low_confidence': [
                "I'd like to understand your experience with {skill} better. Can you share a recent project where you used it?",
                "What aspects of {skill} do you find most interesting to work with?"
            ],
            'analytical_personality': [
                "How do you approach breaking down complex problems in your work?",
                "Walk me through your decision-making process when analyzing data or requirements."
            ],
            'creative_personality': [
                "Describe a time when you had to think outside the box to solve a problem.",
                "How do you balance creativity with technical constraints in your projects?"
            ],
            'leadership_traits': [
                "Tell me about a time when you had to influence others without formal authority.",
                "How do you handle situations where team members have conflicting ideas?"
            ]
        }
    
    def generate_adaptive_question(self, 
                                 candidate_analysis: Dict[str, Any], 
                                 job_context: Dict[str, Any],
                                 chat_history: List[Dict]) -> str:
        """Generate question adapted to candidate's profile and responses"""
        
        # Determine candidate's dominant traits
        personality_traits = candidate_analysis.get('personality_traits', {})
        dominant_trait = max(personality_traits.items(), key=lambda x: x[1])[0] if personality_traits else None
        
        # Assess confidence level
        communication_style = candidate_analysis.get('communication_style', {})
        confidence_level = communication_style.get('confidence_level', 0)
        
        # Select appropriate question template
        if confidence_level > 1:
            question_type = 'high_confidence'
        elif confidence_level < -1:
            question_type = 'low_confidence'
        elif dominant_trait and f"{dominant_trait}_personality" in self.question_templates:
            question_type = f"{dominant_trait}_personality"
        else:
            question_type = 'analytical_personality'  # Default
        
        # Get question template
        templates = self.question_templates.get(question_type, self.question_templates['analytical_personality'])
        template = np.random.choice(templates)
        
        # Fill in context from job profile
        skills = job_context.get('mandatory_skills', ['your primary technical area'])
        skill = np.random.choice(skills) if skills else 'your primary technical area'
        
        return template.format(skill=skill)

class PredictiveAnalytics:
    """Predictive models for candidate success"""
    
    def predict_job_performance(self, candidate_data: Dict[str, Any]) -> Dict[str, float]:
        """Predict likely job performance metrics"""
        
        # This would be trained ML models in production
        # For now, using heuristic scoring
        
        technical_score = candidate_data.get('technical_depth', 0.5)
        communication_score = candidate_data.get('communication_clarity', 0.5)
        confidence_score = min(abs(candidate_data.get('confidence_level', 0)) / 3, 1.0)
        consistency_score = candidate_data.get('consistency_score', 0.5)
        
        # Weighted performance prediction
        performance_score = (
            technical_score * 0.4 +
            communication_score * 0.25 +
            confidence_score * 0.2 +
            consistency_score * 0.15
        )
        
        return {
            'overall_performance_prediction': performance_score,
            'technical_performance': technical_score,
            'collaboration_success': communication_score,
            'leadership_potential': confidence_score,
            'reliability_score': consistency_score
        }
    
    def predict_cultural_fit(self, candidate_traits: Dict[str, float], company_culture: Dict[str, Any]) -> float:
        """Predict how well candidate fits company culture"""
        
        # Company culture requirements (would be derived from job profile)
        culture_requirements = {
            'analytical': company_culture.get('data_driven', 0.5),
            'creative': company_culture.get('innovation_focused', 0.5),
            'leadership': company_culture.get('leadership_opportunities', 0.5),
            'collaborative': company_culture.get('team_oriented', 0.5),
            'detail_oriented': company_culture.get('quality_focused', 0.5)
        }
        
        # Calculate alignment score
        alignment_scores = []
        for trait, candidate_level in candidate_traits.items():
            required_level = culture_requirements.get(trait, 0.5)
            # Perfect alignment when candidate level matches requirement
            alignment = 1.0 - abs(candidate_level - required_level)
            alignment_scores.append(alignment)
        
        return np.mean(alignment_scores) if alignment_scores else 0.5
    
    def generate_interview_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate specific interview recommendations for HR"""
        recommendations = []
        
        performance_pred = analysis.get('performance_prediction', {})
        
        if performance_pred.get('technical_performance', 0) < 0.6:
            recommendations.append("Focus on technical deep-dive questions to validate skills")
        
        if performance_pred.get('collaboration_success', 0) < 0.6:
            recommendations.append("Include team-based scenarios in next interview round")
        
        if performance_pred.get('leadership_potential', 0) > 0.8:
            recommendations.append("Consider for leadership track opportunities")
        
        cultural_fit = analysis.get('cultural_fit_score', 0.5)
        if cultural_fit < 0.6:
            recommendations.append("Discuss company values and culture extensively")
        
        return recommendations

# Integration with existing chat engine
enhanced_analytics = EnhancedChatAnalytics()
adaptive_engine = AdaptiveQuestionEngine()
predictive_engine = PredictiveAnalytics()
