"""
Scoring engine for computing candidate fit scores
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from models import ExtendedPerson, CandidateSignals, CandidateScore, ChatTurn, ChatTurnRole, ChatTurnIntent
from config import settings
import logging

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Engine for computing composite candidate scores"""
    
    def __init__(self):
        self.weights = settings.SCORING_WEIGHTS
        self.thresholds = settings.SCORING_THRESHOLDS
        self.fraud_penalty = settings.FRAUD_PENALTY_MULTIPLIER
    
    def compute_score(self, person: ExtendedPerson, db: Session) -> CandidateScore:
        """Compute composite fit score for candidate"""
        
        # Get or create signals
        signals = person.signals
        if not signals:
            signals = self._extract_signals(person, db)
        
        # Compute individual components
        role_fit = self._compute_role_fit(person, signals)
        capability_depth = signals.depth_score
        motivation_alignment = signals.motivation_alignment
        reliability = 1.0 - signals.turnover_risk  # Inverse turnover risk
        data_confidence = signals.data_confidence
        
        # Weighted composite score
        raw_score = (
            role_fit * self.weights["role_fit"] +
            capability_depth * self.weights["capability_depth"] +
            motivation_alignment * self.weights["motivation_alignment"] + 
            reliability * self.weights["reliability_inverse_turnover"] +
            data_confidence * self.weights["data_confidence"]
        )
        
        # Apply confidence multiplier
        confidence_multiplier = 0.5 + 0.5 * data_confidence
        adjusted_score = raw_score * confidence_multiplier
        
        # Apply fraud penalty if flagged
        if signals.credibility_flag:
            adjusted_score *= self.fraud_penalty
        
        # Determine fit bucket
        fit_bucket = self._determine_fit_bucket(adjusted_score)
        
        # Create or update score record
        score = person.score
        if not score:
            score = CandidateScore(
                person_local_id=person.id,
                fit_score=adjusted_score,
                fit_bucket=fit_bucket
            )
            db.add(score)
        else:
            score.fit_score = adjusted_score
            score.fit_bucket = fit_bucket
        
        db.commit()
        return score
    
    def _extract_signals(self, person: ExtendedPerson, db: Session) -> CandidateSignals:
        """Extract candidate signals from chat interactions"""
        
        # Get chat turns
        chat_turns = db.query(ChatTurn).filter(
            ChatTurn.person_local_id == person.id
        ).order_by(ChatTurn.turn_index).all()
        
        # Analyze consistency
        consistency_score = self._analyze_consistency(chat_turns)
        
        # Analyze depth
        depth_score = self._analyze_depth(chat_turns)
        
        # Analyze motivation alignment
        motivation_alignment = self._analyze_motivation(chat_turns, person)
        
        # Analyze culture alignment
        culture_alignment = self._analyze_culture_fit(chat_turns)
        
        # Compute turnover risk
        turnover_risk = self._compute_turnover_risk(person, chat_turns)
        
        # Compute data confidence
        data_confidence = self._compute_data_confidence(chat_turns, person)
        
        # Check for credibility issues
        credibility_flag = self._check_credibility(chat_turns)
        
        # Extract flags
        flags = self._extract_flags(chat_turns, person)
        
        # Create or update signals
        signals = person.signals
        if not signals:
            signals = CandidateSignals(
                person_local_id=person.id,
                consistency_score=consistency_score,
                depth_score=depth_score,
                motivation_alignment=motivation_alignment,
                culture_alignment=culture_alignment,
                turnover_risk=turnover_risk,
                data_confidence=data_confidence,
                credibility_flag=credibility_flag,
                flags=flags
            )
            db.add(signals)
        else:
            signals.consistency_score = consistency_score
            signals.depth_score = depth_score
            signals.motivation_alignment = motivation_alignment
            signals.culture_alignment = culture_alignment
            signals.turnover_risk = turnover_risk
            signals.data_confidence = data_confidence
            signals.credibility_flag = credibility_flag
            signals.flags = flags
        
        db.commit()
        return signals
    
    def _compute_role_fit(self, person: ExtendedPerson, signals: CandidateSignals) -> float:
        """Compute role fit based on skills and experience"""
        # TODO: Implement skill matching logic against job requirements
        # For now, use a simple heuristic based on skills count and depth
        skills_count = len(person.skills_tags) if person.skills_tags else 0
        base_fit = min(skills_count / 5.0, 1.0)  # Normalize to max 5 skills
        
        # Boost by depth score
        role_fit = (base_fit + signals.depth_score) / 2.0
        return min(role_fit, 1.0)
    
    def _analyze_consistency(self, chat_turns: list) -> float:
        """Analyze consistency across candidate responses"""
        if len(chat_turns) < 3:
            return 0.5
        
        # TODO: Implement more sophisticated consistency analysis
        # For now, return a mock score
        return 0.8
    
    def _analyze_depth(self, chat_turns: list) -> float:
        """Analyze technical depth from responses"""
        technical_turns = [
            turn for turn in chat_turns 
            if turn.role == ChatTurnRole.USER and len(turn.content) > 50
        ]
        
        if not technical_turns:
            return 0.3
        
        # Score based on response length and detail
        avg_length = sum(len(turn.content) for turn in technical_turns) / len(technical_turns)
        depth_score = min(avg_length / 300, 1.0)  # Normalize by 300 chars
        
        return depth_score
    
    def _analyze_motivation(self, chat_turns: list, person: ExtendedPerson) -> float:
        """Analyze motivation alignment from responses"""
        motivation_turns = [
            turn for turn in chat_turns 
            if turn.intent and 'motivation' in turn.intent.value.lower()
        ]
        
        if not motivation_turns:
            # Use why_us field as fallback
            if person.why_us and len(person.why_us) > 20:
                return 0.7
            return 0.4
        
        # TODO: Implement sentiment/content analysis
        return 0.75
    
    def _analyze_culture_fit(self, chat_turns: list) -> float:
        """Analyze culture alignment from values responses"""
        values_turns = [
            turn for turn in chat_turns 
            if turn.intent and 'values' in turn.intent.value.lower()
        ]
        
        if not values_turns:
            return 0.6
        
        # TODO: Implement values alignment analysis
        return 0.8
    
    def _compute_turnover_risk(self, person: ExtendedPerson, chat_turns: list) -> float:
        """Compute turnover risk based on career history and responses"""
        # TODO: Integrate with PersonEmployment data for job tenure analysis
        # For now, use a simple heuristic
        base_risk = 0.3
        
        # Adjust based on responses about career goals
        scenario_turns = [
            turn for turn in chat_turns 
            if turn.role == ChatTurnRole.USER and 'career' in turn.content.lower()
        ]
        
        if scenario_turns:
            # Assume detailed career planning reduces risk
            return max(base_risk - 0.1, 0.1)
        
        return base_risk
    
    def _compute_data_confidence(self, chat_turns: list, person: ExtendedPerson) -> float:
        """Compute confidence in our data assessment"""
        factors = []
        
        # Chat completeness
        chat_completeness = min(len(chat_turns) / (settings.CHAT_MIN_TURNS * 2), 1.0)
        factors.append(chat_completeness)
        
        # Resume quality
        resume_quality = 1.0 if person.resume_text and len(person.resume_text) > 100 else 0.5
        factors.append(resume_quality)
        
        # Profile completeness
        profile_fields = [person.intro, person.why_us, person.linkedin, person.github]
        profile_completeness = sum(1 for field in profile_fields if field) / len(profile_fields)
        factors.append(profile_completeness)
        
        return sum(factors) / len(factors)
    
    def _check_credibility(self, chat_turns: list) -> bool:
        """Check for credibility red flags"""
        trap_turns = [
            turn for turn in chat_turns 
            if turn.intent and turn.intent == ChatTurnIntent.TRAP
        ]
        
        for turn in trap_turns:
            # Look for responses to trap questions that indicate fabrication
            if turn.role == ChatTurnRole.USER and len(turn.content) > 20:
                # If they provided a detailed answer to our fake technology question
                return True
        
        return False
    
    def _extract_flags(self, chat_turns: list, person: ExtendedPerson) -> list:
        """Extract notable flags/tags for candidate"""
        flags = []
        
        # Performance indicators
        user_turns = [t for t in chat_turns if t.role == ChatTurnRole.USER]
        avg_response_length = sum(len(t.content) for t in user_turns) / len(user_turns) if user_turns else 0
        
        if avg_response_length > 200:
            flags.append("detailed-responses")
        
        if len(person.skills_tags) > 7:
            flags.append("diverse-skills")
        
        if person.github and person.linkedin:
            flags.append("strong-online-presence")
        
        return flags
    
    def _determine_fit_bucket(self, score: float) -> str:
        """Determine fit bucket based on score and thresholds"""
        if score >= self.thresholds["top"]:
            return "top"
        elif score >= self.thresholds["borderline"]:
            return "borderline"
        else:
            return "low"


# Global scoring engine instance
scoring_engine = ScoringEngine()
