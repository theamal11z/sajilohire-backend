"""
Pydantic schemas for request/response models
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class ChatTurnRole(str, Enum):
    USER = "user"
    AI = "ai" 
    SYSTEM = "system"


class ChatTurnIntent(str, Enum):
    SKILL_PROBE = "skill_probe"
    MOTIVATION = "motivation"
    TRAP = "trap"
    VALUES = "values"
    SCENARIO = "scenario"
    OTHER = "other"


class FitBucket(str, Enum):
    TOP = "top"
    BORDERLINE = "borderline"
    LOW = "low"


# Person schemas
class PersonBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = None


class PersonCreate(PersonBase):
    job_id: int = Field(..., gt=0)


class PersonExtend(BaseModel):
    job_id: int = Field(..., gt=0)
    resume_text: str = Field(..., min_length=10)
    skills: Optional[str] = None  # Comma-separated skills
    intro: Optional[str] = None
    why_us: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None


class PersonResponse(PersonBase):
    id: int
    upstream_person_id: Optional[int] = None
    job_id: int
    skills_tags: List[str] = []
    resume_text: Optional[str] = None
    intro: Optional[str] = None
    why_us: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    github_data: Optional[Dict[str, Any]] = None
    avatar_url: Optional[str] = None
    phantombuster_data: Optional[Dict[str, Any]] = None
    trust_score: Optional[float] = None
    social_verification_status: Optional[str] = None
    created_ts: datetime
    last_chat_ts: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Chat schemas
class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class ChatTurnResponse(BaseModel):
    id: int
    turn_index: int
    role: ChatTurnRole
    intent: ChatTurnIntent
    content: str
    analysis_json: Optional[Dict[str, Any]] = None
    ts: datetime
    
    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    agent_reply: str
    progress: float = Field(..., ge=0.0, le=1.0)
    turn_count: int
    is_complete: bool = False
    interview_metadata: Optional[Dict[str, Any]] = None
    final_score: Optional[Dict[str, Any]] = None


class ChatHistory(BaseModel):
    person_id: int
    turns: List[ChatTurnResponse]
    total_turns: int


# Scoring schemas
class CandidateSignalsResponse(BaseModel):
    consistency_score: float
    depth_score: float
    motivation_alignment: float
    culture_alignment: float
    turnover_risk: float
    data_confidence: float
    credibility_flag: bool
    flags: List[str] = []
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CandidateScoreResponse(BaseModel):
    fit_score: float
    fit_bucket: FitBucket
    computed_at: datetime
    
    class Config:
        from_attributes = True


# Dashboard schemas
class DashboardCandidate(BaseModel):
    person_id: int
    full_name: str
    email: str
    avatar_url: Optional[str] = None
    fit_score: float
    fit_bucket: FitBucket
    turnover_risk: float
    flags: List[str] = []
    github_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    trust_score: Optional[float] = None
    social_verification_status: Optional[str] = None
    professional_insights: Optional[Dict[str, Any]] = None
    risk_indicators: List[str] = []
    applied_at: datetime
    # Enhanced fields
    enrichment_status: Optional[str] = None
    enrichment_progress: float = 0.0
    interview_ready: bool = False
    interview_status: Optional[str] = None
    profile_completeness: float = 0.0
    github_repos: int = 0
    interview_stats: Dict[str, Any] = {}
    comprehensive_insights: Dict[str, Any] = {}
    last_activity: Optional[datetime] = None


class DashboardResponse(BaseModel):
    job_id: int
    job_title: str
    candidates: List[DashboardCandidate]
    total_count: int
    high_fit_count: int
    borderline_count: int = 0
    analytics: Dict[str, Any] = {}
    job_requirements_summary: Dict[str, Any] = {}


# Full candidate profile schemas
class JobSkillMatch(BaseModel):
    skill_name: str
    required_level: Optional[str] = None
    candidate_level: Optional[str] = None
    is_mandatory: bool = False
    match_score: Optional[float] = None


# Job Profile schemas
class CompanyProfile(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    industry_insights: Optional[Dict[str, Any]] = None
    company_size_estimate: Optional[str] = None
    business_focus: List[str] = []


class JobProfile(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    role_level: str
    technical_focus: List[str] = []
    growth_opportunities: List[str] = []
    analyzed_skills: Optional[Dict[str, Any]] = None


class JobProfileResponse(BaseModel):
    job: JobProfile
    company: CompanyProfile
    personalization_context: Dict[str, Any] = {}
    interview_focus: Dict[str, Any] = {}
    cultural_indicators: List[str] = []


class FullCandidateResponse(BaseModel):
    person: PersonResponse
    signals: Optional[CandidateSignalsResponse] = None
    score: Optional[CandidateScoreResponse] = None
    chat_history: List[ChatTurnResponse] = []
    job_skills: List[JobSkillMatch] = []
    job_profile: Optional[JobProfileResponse] = None
    upstream_data: Optional[Dict[str, Any]] = None


# Job cache schemas
class JobCacheResponse(BaseModel):
    id: int
    upstream_job_id: int
    title: str
    description: Optional[str] = None
    client_id: int
    client_name: Optional[str] = None
    location: Optional[str] = None
    salary: Optional[str] = None
    remote: Optional[bool] = None
    skills_json: List[Dict[str, Any]] = []
    job_type: Optional[str] = None
    employment_type: Optional[str] = None
    status: Optional[str] = None
    
    class Config:
        from_attributes = True


# Error schemas
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


# Health check schema
class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: datetime
    version: str = "1.0.0"
    database: str = "connected"
    upstream_api: str = "connected"
