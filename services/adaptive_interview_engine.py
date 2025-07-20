"""
Adaptive Interview Engine
Provides comprehensive AI interviews based on enrichment insights
Waits for PhantomBuster completion and uses all gathered data
"""

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from models import ExtendedPerson, ChatTurn, ChatTurnRole, ChatTurnIntent
from services.job_profile_service import job_profile_analyzer
from services.chat_engine import chat_engine
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class AdaptiveInterviewEngine:
    """Manages comprehensive adaptive interviews based on candidate insights"""
    
    def __init__(self):
        self.min_questions = 8
        self.max_questions = 15
        self.question_categories = {
            'technical_depth': {
                'weight': 0.3,
                'min_questions': 2,
                'max_questions': 5
            },
            'experience_validation': {
                'weight': 0.25,
                'min_questions': 2,
                'max_questions': 4
            },
            'motivation_alignment': {
                'weight': 0.2,
                'min_questions': 1,
                'max_questions': 3
            },
            'behavioral_assessment': {
                'weight': 0.15,
                'min_questions': 1,
                'max_questions': 2
            },
            'culture_fit': {
                'weight': 0.1,
                'min_questions': 1,
                'max_questions': 2
            }
        }
    
    def should_start_interview(self, person: ExtendedPerson) -> Tuple[bool, str]:
        """Check if candidate is ready for interview (enrichment completed)"""
        
        # Check enrichment progress
        if not person.enrichment_progress:
            return False, "Enrichment not started"
        
        progress = person.enrichment_progress
        stage = progress.get('stage', 'unknown')
        
        if stage == 'completed' and progress.get('ready_for_interview', False):
            return True, "Ready for comprehensive interview"
        elif stage == 'processing':
            return False, f"Still processing enrichment (progress: {progress.get('progress', 0):.1%})"
        elif stage == 'failed':
            # Allow interview even if enrichment failed, but with reduced scope
            return True, "Enrichment failed - proceeding with basic interview"
        else:
            return False, f"Unknown enrichment stage: {stage}"
    
    def generate_interview_plan(self, person: ExtendedPerson, db: Session) -> Dict[str, Any]:
        """Generate comprehensive interview plan based on candidate insights"""
        
        try:
            logger.info(f"Generating interview plan for person {person.id}")
            
            # Get job profile and comprehensive insights
            job_profile = job_profile_analyzer.get_comprehensive_job_profile(person.job_id, db)
            insights = person.comprehensive_insights or {}
            
            interview_plan = {
                'person_id': person.id,
                'generated_at': datetime.now().isoformat(),
                'total_planned_questions': 0,
                'categories': {},
                'question_sequence': [],
                'focus_areas': [],
                'red_flags_to_probe': []
            }
            
            # Determine focus areas based on insights
            focus_areas = self._determine_focus_areas(person, insights, job_profile)
            interview_plan['focus_areas'] = focus_areas
            
            # Identify red flags to probe
            red_flags = insights.get('red_flags', [])
            interview_plan['red_flags_to_probe'] = red_flags
            
            # Plan questions for each category
            total_questions = 0
            
            for category, config in self.question_categories.items():
                questions_count = self._calculate_category_questions(
                    category, person, insights, job_profile, config
                )
                
                interview_plan['categories'][category] = {
                    'questions_count': questions_count,
                    'priority': self._get_category_priority(category, person, insights),
                    'specific_areas': self._get_category_specific_areas(category, person, insights, job_profile)
                }
                
                total_questions += questions_count
            
            # Ensure we're within bounds
            if total_questions < self.min_questions:
                # Add more questions to high-priority categories
                additional_needed = self.min_questions - total_questions
                interview_plan = self._add_additional_questions(interview_plan, additional_needed)
                total_questions = self.min_questions
            elif total_questions > self.max_questions:
                # Reduce questions from lower-priority categories
                interview_plan = self._reduce_questions(interview_plan, total_questions - self.max_questions)
                total_questions = self.max_questions
            
            interview_plan['total_planned_questions'] = total_questions
            
            # Generate question sequence
            interview_plan['question_sequence'] = self._generate_question_sequence(
                interview_plan, person, insights, job_profile
            )
            
            logger.info(f"Interview plan generated for person {person.id}: {total_questions} questions across {len(interview_plan['categories'])} categories")
            return interview_plan
            
        except Exception as e:
            logger.error(f"Failed to generate interview plan for person {person.id}: {e}")
            # Return basic interview plan as fallback
            return self._generate_basic_interview_plan(person)
    
    def generate_adaptive_question(
        self, 
        person: ExtendedPerson,
        interview_plan: Dict[str, Any],
        current_turn: int,
        chat_history: List[ChatTurn],
        db: Session
    ) -> Dict[str, Any]:
        """Generate next adaptive question based on interview plan and previous responses"""
        
        try:
            question_sequence = interview_plan.get('question_sequence', [])
            
            if current_turn >= len(question_sequence):
                # Interview should be complete
                return {
                    'question': None,
                    'interview_complete': True,
                    'completion_reason': 'All planned questions completed'
                }
            
            planned_question = question_sequence[current_turn]
            category = planned_question['category']
            focus = planned_question['focus']
            
            # Analyze previous responses to adapt the question
            if chat_history and len(chat_history) > 0:
                recent_responses = [t for t in chat_history[-3:] if t.role == ChatTurnRole.USER]
                adaptation_context = self._analyze_recent_responses(recent_responses)
            else:
                adaptation_context = {}
            
            # Generate the actual question
            question_data = self._generate_specific_question(
                category, focus, person, interview_plan, adaptation_context, db
            )
            
            # Add metadata
            question_data.update({
                'question_number': current_turn + 1,
                'total_questions': interview_plan.get('total_planned_questions', self.min_questions),
                'category': category,
                'focus_area': focus,
                'interview_complete': False
            })
            
            logger.info(f"Generated adaptive question {current_turn + 1} for person {person.id}: {category}/{focus}")
            return question_data
            
        except Exception as e:
            logger.error(f"Failed to generate adaptive question for person {person.id}: {e}")
            # Fallback to basic question
            return {
                'question': "Can you tell me more about your technical experience and the projects you've worked on?",
                'intent': ChatTurnIntent.SKILL_PROBE,
                'category': 'technical_depth',
                'question_number': current_turn + 1,
                'interview_complete': False
            }
    
    def _determine_focus_areas(self, person: ExtendedPerson, insights: Dict[str, Any], job_profile: Dict[str, Any]) -> List[str]:
        """Determine key focus areas for the interview"""
        
        focus_areas = []
        
        # Based on credibility assessment
        credibility = insights.get('credibility_assessment', {})
        if credibility.get('overall_score', 0.5) < 0.7:
            focus_areas.append('credential_verification')
        
        # Based on skill analysis
        skill_analysis = insights.get('skill_analysis', {})
        job_analysis = skill_analysis.get('job_requirements_analysis', {})
        if job_analysis.get('mandatory_match', {}).get('coverage', 0) < 0.8:
            focus_areas.append('skill_gap_assessment')
        
        # Based on experience analysis
        experience = insights.get('experience_analysis', {})
        if experience.get('estimated_experience_level') == 'senior' and person.resume_text:
            focus_areas.append('leadership_validation')
        
        # Based on social presence
        social_presence = insights.get('social_presence_analysis', {})
        trust_metrics = social_presence.get('trust_metrics', {})
        if trust_metrics.get('trust_score', 0.5) < 0.6:
            focus_areas.append('authenticity_check')
        
        # Based on GitHub activity
        if person.github_data and person.github_data.get('public_repos', 0) > 5:
            focus_areas.append('project_deep_dive')
        
        return focus_areas
    
    def _calculate_category_questions(
        self, 
        category: str, 
        person: ExtendedPerson, 
        insights: Dict[str, Any], 
        job_profile: Dict[str, Any],
        config: Dict[str, Any]
    ) -> int:
        """Calculate number of questions needed for a category"""
        
        base_questions = config['min_questions']
        
        # Adjust based on specific conditions
        if category == 'technical_depth':
            # More questions if many skills or senior role
            skill_count = len(person.skills_tags or [])
            if skill_count > 8:
                base_questions += 1
            
            experience = insights.get('experience_analysis', {})
            if experience.get('estimated_experience_level') == 'senior':
                base_questions += 1
        
        elif category == 'experience_validation':
            # More questions for senior candidates or those with red flags
            experience = insights.get('experience_analysis', {})
            if experience.get('estimated_experience_level') == 'senior':
                base_questions += 1
            
            red_flags = insights.get('red_flags', [])
            if red_flags:
                base_questions += 1
        
        elif category == 'motivation_alignment':
            # More questions if motivation data is sparse
            if not person.why_us or len(person.why_us) < 50:
                base_questions += 1
        
        return min(base_questions, config['max_questions'])
    
    def _get_category_priority(self, category: str, person: ExtendedPerson, insights: Dict[str, Any]) -> float:
        """Get priority score for a category"""
        
        base_priority = self.question_categories[category]['weight']
        
        # Adjust based on insights
        if category == 'technical_depth':
            # Higher priority for technical roles
            if person.skills_tags and len(person.skills_tags) > 5:
                base_priority *= 1.2
        
        elif category == 'experience_validation':
            # Higher priority if red flags exist
            red_flags = insights.get('red_flags', [])
            if red_flags:
                base_priority *= 1.5
        
        return base_priority
    
    def _get_category_specific_areas(
        self, 
        category: str, 
        person: ExtendedPerson, 
        insights: Dict[str, Any], 
        job_profile: Dict[str, Any]
    ) -> List[str]:
        """Get specific areas to focus on within a category"""
        
        if category == 'technical_depth':
            areas = ['core_skills']
            
            # Add areas based on job requirements
            if job_profile and job_profile.get('personalization_context'):
                mandatory_skills = job_profile['personalization_context'].get('mandatory_skills', [])
                if mandatory_skills:
                    areas.extend(['mandatory_skill_validation'])
            
            # Add architecture if senior
            experience = insights.get('experience_analysis', {})
            if experience.get('estimated_experience_level') == 'senior':
                areas.append('architecture_design')
                
            return areas
        
        elif category == 'experience_validation':
            areas = ['project_examples']
            
            # Add leadership if senior
            experience = insights.get('experience_analysis', {})
            if experience.get('leadership_score', 0) > 0.3:
                areas.append('leadership_examples')
            
            # Add scale validation if mentioned
            scale_indicators = experience.get('indicators', {}).get('project_scale_indicators', [])
            if scale_indicators:
                areas.append('scale_validation')
                
            return areas
        
        elif category == 'motivation_alignment':
            return ['company_interest', 'career_goals']
        
        elif category == 'behavioral_assessment':
            return ['problem_solving', 'communication_style']
        
        elif category == 'culture_fit':
            return ['values_alignment', 'team_collaboration']
        
        return ['general']
    
    def _generate_question_sequence(
        self,
        interview_plan: Dict[str, Any],
        person: ExtendedPerson,
        insights: Dict[str, Any],
        job_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate the sequence of questions for the interview"""
        
        sequence = []
        
        # Start with technical depth (warm-up with familiar topics)
        tech_questions = interview_plan['categories'].get('technical_depth', {}).get('questions_count', 0)
        tech_areas = interview_plan['categories'].get('technical_depth', {}).get('specific_areas', ['core_skills'])
        
        for i in range(tech_questions):
            focus = tech_areas[i % len(tech_areas)]
            sequence.append({
                'category': 'technical_depth',
                'focus': focus,
                'position': 'early'
            })
        
        # Add experience validation questions
        exp_questions = interview_plan['categories'].get('experience_validation', {}).get('questions_count', 0)
        exp_areas = interview_plan['categories'].get('experience_validation', {}).get('specific_areas', ['project_examples'])
        
        for i in range(exp_questions):
            focus = exp_areas[i % len(exp_areas)]
            sequence.append({
                'category': 'experience_validation',
                'focus': focus,
                'position': 'middle'
            })
        
        # Interleave motivation and behavioral questions
        motivation_questions = interview_plan['categories'].get('motivation_alignment', {}).get('questions_count', 0)
        behavioral_questions = interview_plan['categories'].get('behavioral_assessment', {}).get('questions_count', 0)
        
        motivation_areas = interview_plan['categories'].get('motivation_alignment', {}).get('specific_areas', ['company_interest'])
        behavioral_areas = interview_plan['categories'].get('behavioral_assessment', {}).get('specific_areas', ['problem_solving'])
        
        for i in range(max(motivation_questions, behavioral_questions)):
            if i < motivation_questions:
                focus = motivation_areas[i % len(motivation_areas)]
                sequence.append({
                    'category': 'motivation_alignment',
                    'focus': focus,
                    'position': 'middle'
                })
            
            if i < behavioral_questions:
                focus = behavioral_areas[i % len(behavioral_areas)]
                sequence.append({
                    'category': 'behavioral_assessment',
                    'focus': focus,
                    'position': 'middle'
                })
        
        # End with culture fit
        culture_questions = interview_plan['categories'].get('culture_fit', {}).get('questions_count', 0)
        culture_areas = interview_plan['categories'].get('culture_fit', {}).get('specific_areas', ['values_alignment'])
        
        for i in range(culture_questions):
            focus = culture_areas[i % len(culture_areas)]
            sequence.append({
                'category': 'culture_fit',
                'focus': focus,
                'position': 'late'
            })
        
        return sequence
    
    def _generate_specific_question(
        self,
        category: str,
        focus: str,
        person: ExtendedPerson,
        interview_plan: Dict[str, Any],
        adaptation_context: Dict[str, Any],
        db: Session
    ) -> Dict[str, Any]:
        """Generate a specific question based on category and focus"""
        
        # Get job profile for context
        job_profile = job_profile_analyzer.get_comprehensive_job_profile(person.job_id, db)
        
        if category == 'technical_depth':
            return self._generate_technical_question(focus, person, job_profile, adaptation_context)
        elif category == 'experience_validation':
            return self._generate_experience_question(focus, person, job_profile, adaptation_context)
        elif category == 'motivation_alignment':
            return self._generate_motivation_question(focus, person, job_profile, adaptation_context)
        elif category == 'behavioral_assessment':
            return self._generate_behavioral_question(focus, person, job_profile, adaptation_context)
        elif category == 'culture_fit':
            return self._generate_culture_question(focus, person, job_profile, adaptation_context)
        else:
            return {
                'question': "Can you tell me more about your background and experience?",
                'intent': ChatTurnIntent.OTHER
            }
    
    def _generate_technical_question(
        self, 
        focus: str, 
        person: ExtendedPerson, 
        job_profile: Dict[str, Any], 
        adaptation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate technical depth questions"""
        
        if focus == 'core_skills':
            skills = person.skills_tags or ['your primary technical skills']
            primary_skill = skills[0] if skills else 'your primary technical skill'
            
            return {
                'question': f"I'd like to understand your experience with {primary_skill} better. Can you walk me through a challenging project where you used this technology, including the specific problems you solved and the technical decisions you made?",
                'intent': ChatTurnIntent.SKILL_PROBE
            }
        
        elif focus == 'mandatory_skill_validation':
            if job_profile and job_profile.get('personalization_context'):
                mandatory_skills = job_profile['personalization_context'].get('mandatory_skills', [])
                if mandatory_skills:
                    skill = mandatory_skills[0]
                    return {
                        'question': f"This role requires strong {skill} skills. Can you describe a specific situation where you used {skill} to solve a complex problem? What was your approach and what challenges did you encounter?",
                        'intent': ChatTurnIntent.SKILL_PROBE
                    }
            
            return {
                'question': "Can you describe a specific technical challenge you've faced and how you approached solving it?",
                'intent': ChatTurnIntent.SKILL_PROBE
            }
        
        elif focus == 'architecture_design':
            return {
                'question': "Tell me about a system or application you've architected from scratch. What were the key design decisions you made, and how did you handle scalability and performance considerations?",
                'intent': ChatTurnIntent.SKILL_PROBE
            }
        
        else:
            return {
                'question': "What's a recent technical accomplishment you're particularly proud of, and what made it challenging?",
                'intent': ChatTurnIntent.SKILL_PROBE
            }
    
    def _generate_experience_question(
        self, 
        focus: str, 
        person: ExtendedPerson, 
        job_profile: Dict[str, Any], 
        adaptation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate experience validation questions"""
        
        if focus == 'project_examples':
            return {
                'question': "Can you describe the most impactful project you've worked on? What was your specific role, and what measurable outcomes did you achieve?",
                'intent': ChatTurnIntent.SCENARIO
            }
        
        elif focus == 'leadership_examples':
            return {
                'question': "Tell me about a time when you had to lead a technical initiative or mentor other developers. How did you handle challenges and ensure project success?",
                'intent': ChatTurnIntent.SCENARIO
            }
        
        elif focus == 'scale_validation':
            return {
                'question': "I noticed you've mentioned working with large-scale systems. Can you elaborate on the specific scale challenges you've dealt with and how you addressed them?",
                'intent': ChatTurnIntent.SKILL_PROBE
            }
        
        else:
            return {
                'question': "Walk me through your career progression and the key experiences that have shaped your technical expertise.",
                'intent': ChatTurnIntent.OTHER
            }
    
    def _generate_motivation_question(
        self, 
        focus: str, 
        person: ExtendedPerson, 
        job_profile: Dict[str, Any], 
        adaptation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate motivation alignment questions"""
        
        company_name = "our company"
        if job_profile and job_profile.get('company'):
            company_name = job_profile['company'].get('client_name', company_name)
        
        if focus == 'company_interest':
            return {
                'question': f"What specifically interests you about {company_name} and this role? What research have you done about us?",
                'intent': ChatTurnIntent.MOTIVATION
            }
        
        elif focus == 'career_goals':
            return {
                'question': "Where do you see your career heading in the next 3-5 years, and how does this role align with those goals?",
                'intent': ChatTurnIntent.MOTIVATION
            }
        
        else:
            return {
                'question': "What motivates you most in your work, and what kind of environment helps you do your best work?",
                'intent': ChatTurnIntent.MOTIVATION
            }
    
    def _generate_behavioral_question(
        self, 
        focus: str, 
        person: ExtendedPerson, 
        job_profile: Dict[str, Any], 
        adaptation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate behavioral assessment questions"""
        
        if focus == 'problem_solving':
            return {
                'question': "Describe a time when you encountered a problem that didn't have an obvious solution. How did you approach it, and what was the outcome?",
                'intent': ChatTurnIntent.SCENARIO
            }
        
        elif focus == 'communication_style':
            return {
                'question': "Tell me about a time when you had to explain a complex technical concept to a non-technical stakeholder. How did you ensure they understood?",
                'intent': ChatTurnIntent.SCENARIO
            }
        
        else:
            return {
                'question': "How do you handle situations when you disagree with a teammate's technical approach?",
                'intent': ChatTurnIntent.SCENARIO
            }
    
    def _generate_culture_question(
        self, 
        focus: str, 
        person: ExtendedPerson, 
        job_profile: Dict[str, Any], 
        adaptation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate culture fit questions"""
        
        if focus == 'values_alignment':
            return {
                'question': "What are the most important values to you in a workplace, and can you give me an example of how you've seen those values in action?",
                'intent': ChatTurnIntent.VALUES
            }
        
        elif focus == 'team_collaboration':
            return {
                'question': "Describe your ideal team dynamic. How do you prefer to collaborate with colleagues on projects?",
                'intent': ChatTurnIntent.VALUES
            }
        
        else:
            return {
                'question': "What kind of company culture brings out your best work?",
                'intent': ChatTurnIntent.VALUES
            }
    
    def _analyze_recent_responses(self, recent_responses: List[ChatTurn]) -> Dict[str, Any]:
        """Analyze recent responses to adapt follow-up questions"""
        
        if not recent_responses:
            return {}
        
        # Simple analysis for now - could be enhanced with NLP
        total_length = sum(len(turn.content) for turn in recent_responses)
        avg_length = total_length / len(recent_responses)
        
        # Check for depth indicators
        technical_terms = 0
        for turn in recent_responses:
            content = turn.content.lower()
            tech_keywords = ['implement', 'design', 'architecture', 'performance', 'scalability']
            technical_terms += len([kw for kw in tech_keywords if kw in content])
        
        return {
            'avg_response_length': avg_length,
            'technical_depth': technical_terms / len(recent_responses),
            'engagement_level': 'high' if avg_length > 150 else 'medium' if avg_length > 80 else 'low'
        }
    
    def _generate_basic_interview_plan(self, person: ExtendedPerson) -> Dict[str, Any]:
        """Generate basic interview plan as fallback"""
        
        return {
            'person_id': person.id,
            'generated_at': datetime.now().isoformat(),
            'total_planned_questions': 8,
            'categories': {
                'technical_depth': {'questions_count': 3, 'priority': 0.4},
                'experience_validation': {'questions_count': 2, 'priority': 0.3},
                'motivation_alignment': {'questions_count': 2, 'priority': 0.2},
                'behavioral_assessment': {'questions_count': 1, 'priority': 0.1}
            },
            'question_sequence': [
                {'category': 'technical_depth', 'focus': 'core_skills', 'position': 'early'},
                {'category': 'technical_depth', 'focus': 'core_skills', 'position': 'early'},
                {'category': 'experience_validation', 'focus': 'project_examples', 'position': 'middle'},
                {'category': 'motivation_alignment', 'focus': 'company_interest', 'position': 'middle'},
                {'category': 'technical_depth', 'focus': 'core_skills', 'position': 'middle'},
                {'category': 'experience_validation', 'focus': 'project_examples', 'position': 'middle'},
                {'category': 'motivation_alignment', 'focus': 'career_goals', 'position': 'late'},
                {'category': 'behavioral_assessment', 'focus': 'problem_solving', 'position': 'late'}
            ],
            'focus_areas': ['technical_validation'],
            'red_flags_to_probe': []
        }
    
    def _add_additional_questions(self, interview_plan: Dict[str, Any], additional_needed: int) -> Dict[str, Any]:
        """Add additional questions to reach minimum"""
        
        # Add to highest priority categories first
        categories = sorted(
            interview_plan['categories'].items(), 
            key=lambda x: x[1].get('priority', 0), 
            reverse=True
        )
        
        for category, config in categories:
            if additional_needed <= 0:
                break
            
            max_for_category = self.question_categories[category]['max_questions']
            current_questions = config['questions_count']
            
            if current_questions < max_for_category:
                additional = min(additional_needed, max_for_category - current_questions)
                config['questions_count'] += additional
                additional_needed -= additional
        
        return interview_plan
    
    def _reduce_questions(self, interview_plan: Dict[str, Any], reduction_needed: int) -> Dict[str, Any]:
        """Reduce questions to stay within maximum"""
        
        # Remove from lowest priority categories first
        categories = sorted(
            interview_plan['categories'].items(), 
            key=lambda x: x[1].get('priority', 0)
        )
        
        for category, config in categories:
            if reduction_needed <= 0:
                break
            
            min_for_category = self.question_categories[category]['min_questions']
            current_questions = config['questions_count']
            
            if current_questions > min_for_category:
                reduction = min(reduction_needed, current_questions - min_for_category)
                config['questions_count'] -= reduction
                reduction_needed -= reduction
        
        return interview_plan


# Global instance
adaptive_interview_engine = AdaptiveInterviewEngine()
