"""
Scoring engine for computing candidate fit scores
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from models import ExtendedPerson, CandidateSignals, CandidateScore, ChatTurn, ChatTurnRole, ChatTurnIntent
from services.job_profile_service import job_profile_analyzer
from config import settings
import logging
import re

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Engine for computing composite candidate scores"""
    
    def __init__(self):
        self.weights = settings.SCORING_WEIGHTS
        self.thresholds = settings.SCORING_THRESHOLDS
        self.fraud_penalty = settings.FRAUD_PENALTY_MULTIPLIER
    
    def compute_score(self, person: ExtendedPerson, db: Session) -> CandidateScore:
        """Compute composite fit score for candidate"""
        
        # Get job profile for enhanced scoring
        job_profile = job_profile_analyzer.get_comprehensive_job_profile(person.job_id, db)
        
        # Get or create signals
        signals = person.signals
        if not signals:
            signals = self._extract_signals(person, db, job_profile)
        
        # Compute individual components with job profile context
        role_fit = self._compute_role_fit(person, signals, job_profile)
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
    
    def _extract_signals(self, person: ExtendedPerson, db: Session, job_profile: Dict[str, Any] = None) -> CandidateSignals:
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
    
    def _compute_role_fit(self, person: ExtendedPerson, signals: CandidateSignals, job_profile: Dict[str, Any] = None) -> float:
        """Compute role fit based on skills and experience with job profile context"""
        if not job_profile:
            # Fallback to original logic
            skills_count = len(person.skills_tags) if person.skills_tags else 0
            base_fit = min(skills_count / 5.0, 1.0)
            role_fit = (base_fit + signals.depth_score) / 2.0
            return min(role_fit, 1.0)
        
        # Enhanced role fit computation using job profile
        personalization = job_profile.get('personalization_context', {})
        job_info = job_profile.get('job', {})
        analyzed_skills = job_info.get('analyzed_skills', {})
        
        candidate_skills = set((person.skills_tags or []))
        mandatory_skills = set(personalization.get('mandatory_skills', []))
        key_skills = set(personalization.get('key_skills', []))
        
        # Skill matching scores
        mandatory_match = len(candidate_skills.intersection(mandatory_skills)) / max(len(mandatory_skills), 1)
        key_skill_match = len(candidate_skills.intersection(key_skills)) / max(len(key_skills), 1)
        
        # Experience level match
        required_level = job_info.get('role_level', 'mid-level')
        experience_match = self._compute_experience_level_match(person, required_level)
        
        # Technical focus alignment
        technical_focus_alignment = self._compute_technical_alignment(person, job_info)
        
        # Weighted role fit score
        role_fit = (
            mandatory_match * 0.4 +        # 40% weight for mandatory skills
            key_skill_match * 0.25 +       # 25% weight for key skills
            experience_match * 0.20 +      # 20% weight for experience level
            technical_focus_alignment * 0.15  # 15% weight for technical alignment
        )
        
        # Boost by depth score from chat analysis
        final_fit = (role_fit * 0.8) + (signals.depth_score * 0.2)
        
        return min(final_fit, 1.0)
    
    def _compute_experience_level_match(self, person: ExtendedPerson, required_level: str) -> float:
        """Compute how well candidate's experience matches required level"""
        # Extract experience indicators from resume
        resume_text = (person.resume_text or '').lower()
        
        level_indicators = {
            'junior': ['junior', 'entry', 'associate', 'trainee', '0-2 years', '1 year'],
            'mid-level': ['mid', 'intermediate', '2-5 years', '3 years', '4 years'],
            'senior': ['senior', 'lead', 'principal', '5+ years', '6 years', '7 years', '8+ years'],
            'management': ['manager', 'director', 'head', 'vp', 'team lead']
        }
        
        candidate_level_scores = {}
        for level, keywords in level_indicators.items():
            score = sum(1 for keyword in keywords if keyword in resume_text)
            candidate_level_scores[level] = score
        
        # Find candidate's most likely level
        candidate_level = max(candidate_level_scores, key=candidate_level_scores.get)
        
        # Compute match score
        level_hierarchy = ['junior', 'mid-level', 'senior', 'management']
        
        if candidate_level == required_level:
            return 1.0
        elif abs(level_hierarchy.index(candidate_level) - level_hierarchy.index(required_level)) == 1:
            return 0.7  # Adjacent levels
        else:
            return 0.4  # Distant levels
    
    def _compute_technical_alignment(self, person: ExtendedPerson, job_info: Dict[str, Any]) -> float:
        """Compute alignment with job's technical focus areas"""
        technical_focus = job_info.get('technical_focus', [])
        candidate_skills = set((skill.lower() for skill in (person.skills_tags or [])))
        
        if not technical_focus:
            return 0.8  # Neutral if no specific focus
        
        # Define skill mappings for technical focus areas
        focus_skill_mapping = {
            'Machine Learning': ['python', 'tensorflow', 'pytorch', 'scikit-learn', 'ml', 'ai'],
            'Web Development': ['javascript', 'react', 'angular', 'vue', 'html', 'css', 'nodejs'],
            'Data Science': ['python', 'r', 'pandas', 'numpy', 'sql', 'tableau', 'spark'],
            'Devops': ['docker', 'kubernetes', 'aws', 'azure', 'jenkins', 'terraform'],
            'Mobile': ['ios', 'android', 'react native', 'flutter', 'swift', 'kotlin'],
            'Security': ['cybersecurity', 'encryption', 'penetration testing', 'security'],
            'Database': ['sql', 'nosql', 'mongodb', 'postgresql', 'mysql', 'redis']
        }
        
        alignment_scores = []
        for focus_area in technical_focus:
            relevant_skills = set(focus_skill_mapping.get(focus_area, []))
            if relevant_skills:
                overlap = len(candidate_skills.intersection(relevant_skills))
                alignment_scores.append(min(overlap / 3, 1.0))  # Normalize by 3 skills
        
        return sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0.5
    
    def _analyze_consistency(self, chat_turns: list) -> float:
        """Analyze consistency across candidate responses using advanced analysis"""
        if len(chat_turns) < 3:
            return 0.5
        
        user_turns = [turn for turn in chat_turns if turn.role == ChatTurnRole.USER]
        if not user_turns:
            return 0.5
        
        consistency_factors = []
        
        # 1. Response length consistency (avoid too much variation)
        lengths = [len(turn.content.split()) for turn in user_turns]
        if len(lengths) > 1:
            avg_length = sum(lengths) / len(lengths)
            length_variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
            length_consistency = max(0.0, 1.0 - (length_variance / (avg_length ** 2)) if avg_length > 0 else 0.5)
            consistency_factors.append(length_consistency)
        
        # 2. Vocabulary consistency (using similar complexity words)
        from collections import Counter
        all_words = []
        response_vocabularies = []
        
        for turn in user_turns:
            words = turn.content.lower().split()
            response_vocabularies.append(set(words))
            all_words.extend(words)
        
        if len(response_vocabularies) > 1:
            # Calculate vocabulary overlap between responses
            overlaps = []
            for i in range(len(response_vocabularies)):
                for j in range(i + 1, len(response_vocabularies)):
                    vocab1, vocab2 = response_vocabularies[i], response_vocabularies[j]
                    if vocab1 and vocab2:
                        overlap = len(vocab1.intersection(vocab2)) / len(vocab1.union(vocab2))
                        overlaps.append(overlap)
            
            if overlaps:
                vocab_consistency = sum(overlaps) / len(overlaps)
                consistency_factors.append(vocab_consistency)
        
        # 3. Technical detail consistency
        technical_keywords = ['implement', 'develop', 'design', 'build', 'create', 'optimize', 'scale']
        tech_densities = []
        for turn in user_turns:
            words = turn.content.lower().split()
            tech_density = len([w for w in words if w in technical_keywords]) / max(len(words), 1)
            tech_densities.append(tech_density)
        
        if len(tech_densities) > 1:
            avg_tech_density = sum(tech_densities) / len(tech_densities)
            tech_variance = sum((d - avg_tech_density) ** 2 for d in tech_densities) / len(tech_densities)
            tech_consistency = max(0.0, 1.0 - tech_variance * 10)  # Scale variance
            consistency_factors.append(tech_consistency)
        
        # Return average of all consistency factors
        return sum(consistency_factors) / len(consistency_factors) if consistency_factors else 0.6
    
    def _analyze_depth(self, chat_turns: list) -> float:
        """Analyze technical depth from responses using advanced metrics"""
        technical_turns = [
            turn for turn in chat_turns 
            if turn.role == ChatTurnRole.USER and len(turn.content) > 50
        ]
        
        if not technical_turns:
            return 0.3
        
        depth_factors = []
        
        # 1. Response length and detail (improved)
        avg_length = sum(len(turn.content) for turn in technical_turns) / len(technical_turns)
        length_score = min(avg_length / 400, 1.0)  # Normalized by 400 chars for higher bar
        depth_factors.append(length_score)
        
        # 2. Technical vocabulary sophistication
        advanced_tech_terms = [
            'architecture', 'scalability', 'optimization', 'algorithm', 'complexity',
            'performance', 'distributed', 'microservices', 'api', 'database',
            'framework', 'library', 'protocol', 'encryption', 'authentication',
            'deployment', 'monitoring', 'testing', 'debugging', 'refactoring'
        ]
        
        tech_sophistication_scores = []
        for turn in technical_turns:
            words = turn.content.lower().split()
            tech_terms_count = len([w for w in words if any(term in w for term in advanced_tech_terms)])
            sophistication = min(tech_terms_count / max(len(words) * 0.1, 1), 1.0)
            tech_sophistication_scores.append(sophistication)
        
        if tech_sophistication_scores:
            avg_sophistication = sum(tech_sophistication_scores) / len(tech_sophistication_scores)
            depth_factors.append(avg_sophistication)
        
        # 3. Specific examples and quantification
        quantification_patterns = [
            r'\d+%', r'\d+x', r'\d+ users', r'\d+ requests', r'\d+ seconds',
            r'\d+ years', r'\d+ months', r'\d+ developers', r'\d+ million',
            r'\d+k', r'\d+mb', r'\d+gb'
        ]
        
        quantification_scores = []
        for turn in technical_turns:
            content = turn.content.lower()
            quantifications = 0
            for pattern in quantification_patterns:
                quantifications += len(re.findall(pattern, content))
            
            # Normalize by response length
            words_count = len(turn.content.split())
            quantification_density = min(quantifications / max(words_count * 0.05, 1), 1.0)
            quantification_scores.append(quantification_density)
        
        if quantification_scores:
            avg_quantification = sum(quantification_scores) / len(quantification_scores)
            depth_factors.append(avg_quantification)
        
        # 4. Problem-solving structure indicators
        structure_indicators = [
            'first', 'then', 'next', 'finally', 'however', 'therefore',
            'because', 'since', 'although', 'while', 'whereas',
            'problem', 'solution', 'approach', 'strategy', 'method'
        ]
        
        structure_scores = []
        for turn in technical_turns:
            words = turn.content.lower().split()
            structure_words = [w for w in words if w in structure_indicators]
            structure_density = min(len(structure_words) / max(len(words) * 0.05, 1), 1.0)
            structure_scores.append(structure_density)
        
        if structure_scores:
            avg_structure = sum(structure_scores) / len(structure_scores)
            depth_factors.append(avg_structure)
        
        # Calculate weighted average (length gets less weight, sophistication gets more)
        if len(depth_factors) >= 4:
            weighted_depth = (
                depth_factors[0] * 0.2 +  # length
                depth_factors[1] * 0.4 +  # tech sophistication
                depth_factors[2] * 0.25 + # quantification
                depth_factors[3] * 0.15   # structure
            )
        else:
            weighted_depth = sum(depth_factors) / len(depth_factors)
        
        return min(weighted_depth, 1.0)
    
    def _analyze_motivation(self, chat_turns: list, person: ExtendedPerson) -> float:
        """Analyze motivation alignment from responses with enhanced sentiment analysis"""
        motivation_turns = [
            turn for turn in chat_turns 
            if turn.intent and 'motivation' in turn.intent.value.lower()
        ]
        
        motivation_factors = []
        
        # Analyze motivation turns from chat
        if motivation_turns:
            for turn in motivation_turns:
                if turn.role == ChatTurnRole.USER:
                    content = turn.content.lower()
                    
                    # 1. Passion indicators
                    passion_keywords = [
                        'passionate', 'excited', 'love', 'enjoy', 'fascinated',
                        'enthusiastic', 'driven', 'motivated', 'inspired', 'thrilled'
                    ]
                    passion_score = len([w for w in passion_keywords if w in content]) / 10
                    
                    # 2. Specific interest indicators
                    specific_interests = [
                        'because', 'specifically', 'particularly', 'especially',
                        'unique', 'innovative', 'cutting-edge', 'opportunity'
                    ]
                    specificity_score = len([w for w in specific_interests if w in content]) / 8
                    
                    # 3. Long-term thinking indicators
                    future_thinking = [
                        'career', 'growth', 'future', 'goals', 'aspire',
                        'develop', 'learn', 'advance', 'contribute', 'impact'
                    ]
                    future_score = len([w for w in future_thinking if w in content]) / 10
                    
                    # 4. Response depth (length and detail)
                    depth_score = min(len(turn.content) / 200, 1.0)
                    
                    turn_motivation = (
                        passion_score * 0.3 +
                        specificity_score * 0.25 +
                        future_score * 0.25 +
                        depth_score * 0.2
                    )
                    motivation_factors.append(min(turn_motivation, 1.0))
        
        # Analyze why_us field as additional data point
        if person.why_us and len(person.why_us) > 20:
            why_us_content = person.why_us.lower()
            
            # Company-specific motivation indicators
            company_specific = [
                'company', 'organization', 'team', 'culture', 'values',
                'mission', 'vision', 'reputation', 'known for', 'leader in'
            ]
            company_score = len([w for w in company_specific if w in why_us_content]) / 10
            
            # Role-specific motivation
            role_specific = [
                'position', 'role', 'opportunity', 'challenge', 'project',
                'work on', 'build', 'contribute to', 'responsible for'
            ]
            role_score = len([w for w in role_specific if w in why_us_content]) / 10
            
            # Research indicators (shows genuine interest)
            research_indicators = [
                'read about', 'learned about', 'research', 'understand',
                'aware that', 'know that', 'seen that', 'noticed'
            ]
            research_score = len([phrase for phrase in research_indicators if phrase in why_us_content]) / 8
            
            why_us_motivation = (
                company_score * 0.4 +
                role_score * 0.3 +
                research_score * 0.3
            )
            motivation_factors.append(min(why_us_motivation, 1.0))
        
        # Analyze intro field for additional motivation signals
        if person.intro and len(person.intro) > 30:
            intro_content = person.intro.lower()
            
            # Personal mission/passion in intro
            personal_passion = [
                'passionate', 'dedicated', 'committed', 'focused',
                'specialized', 'experienced', 'enjoy', 'love'
            ]
            intro_passion = len([w for w in personal_passion if w in intro_content]) / 8
            motivation_factors.append(min(intro_passion, 1.0))
        
        # Calculate overall motivation score
        if motivation_factors:
            avg_motivation = sum(motivation_factors) / len(motivation_factors)
            # Boost score if multiple sources of motivation data
            if len(motivation_factors) > 1:
                avg_motivation = min(avg_motivation * 1.1, 1.0)
            return avg_motivation
        else:
            return 0.4  # Default for no motivation data
    
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
