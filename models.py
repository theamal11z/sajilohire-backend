"""
SQLAlchemy ORM Models for SajiloHire Backend
"""

from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from enum import Enum as PyEnum
from datetime import datetime


class ChatTurnRole(PyEnum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


class ChatTurnIntent(PyEnum):
    SKILL_PROBE = "skill_probe"
    MOTIVATION = "motivation"
    TRAP = "trap"
    VALUES = "values"
    SCENARIO = "scenario"
    OTHER = "other"


class ExtendedPerson(Base):
    """Extended person model storing local candidate data"""
    __tablename__ = "extended_persons"
    
    id = Column(Integer, primary_key=True, index=True)
    upstream_person_id = Column(Integer, nullable=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(20), nullable=True)
    job_id = Column(Integer, nullable=False, index=True)
    skills_tags = Column(JSON, default=list)
    resume_text = Column(Text, nullable=True)
    intro = Column(Text, nullable=True)
    why_us = Column(Text, nullable=True)
    linkedin = Column(String(255), nullable=True)
    github = Column(String(255), nullable=True)
    github_data = Column(JSON, nullable=True)  # Enriched GitHub profile data
    avatar_url = Column(String(500), nullable=True)  # Profile image URL from GitHub
    phantombuster_data = Column(JSON, nullable=True)  # PhantomBuster social intelligence data
    trust_score = Column(Float, nullable=True)  # Cross-platform trust score
    social_verification_status = Column(String(50), nullable=True)  # verified/needs_review/unverified/suspicious
    enrichment_progress = Column(JSON, nullable=True)  # Real-time enrichment progress tracking
    comprehensive_insights = Column(JSON, nullable=True)  # Generated insights after enrichment
    profile_completeness_score = Column(Float, nullable=True)  # Profile data quality score
    interview_plan = Column(JSON, nullable=True)  # Adaptive interview plan
    created_ts = Column(DateTime, default=func.now())
    last_chat_ts = Column(DateTime, nullable=True)
    
    # Relationships
    chat_turns = relationship("ChatTurn", back_populates="person")
    signals = relationship("CandidateSignals", back_populates="person", uselist=False)
    score = relationship("CandidateScore", back_populates="person", uselist=False)


class ExtendedJobCache(Base):
    """Cached job data from upstream Aqore API"""
    __tablename__ = "extended_job_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    upstream_job_id = Column(Integer, unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    client_id = Column(Integer, nullable=False)
    client_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    salary = Column(String(100), nullable=True)
    remote = Column(Boolean, nullable=True)
    skills_json = Column(JSON, default=list)
    job_type = Column(String(50), nullable=True)
    employment_type = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)
    created_date = Column(DateTime, nullable=True)
    cached_at = Column(DateTime, default=func.now())


class ChatTurn(Base):
    """Individual chat turn in AI interview"""
    __tablename__ = "chat_turns"
    
    id = Column(Integer, primary_key=True, index=True)
    person_local_id = Column(Integer, ForeignKey("extended_persons.id"), index=True)
    turn_index = Column(Integer, nullable=False)
    role = Column(Enum(ChatTurnRole), nullable=False)
    intent = Column(Enum(ChatTurnIntent), default=ChatTurnIntent.OTHER)
    content = Column(Text, nullable=False)
    analysis_json = Column(JSON, nullable=True)
    ts = Column(DateTime, default=func.now())
    
    # Relationships
    person = relationship("ExtendedPerson", back_populates="chat_turns")


class CandidateSignals(Base):
    """Extracted signals from candidate interactions"""
    __tablename__ = "candidate_signals"
    
    id = Column(Integer, primary_key=True, index=True)
    person_local_id = Column(Integer, ForeignKey("extended_persons.id"), unique=True, index=True)
    consistency_score = Column(Float, default=0.0)
    depth_score = Column(Float, default=0.0)
    motivation_alignment = Column(Float, default=0.0)
    culture_alignment = Column(Float, default=0.0)
    turnover_risk = Column(Float, default=0.5)
    data_confidence = Column(Float, default=0.0)
    credibility_flag = Column(Boolean, default=False)
    flags = Column(JSON, default=list)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    person = relationship("ExtendedPerson", back_populates="signals")


class CandidateScore(Base):
    """Final composite score for candidates"""
    __tablename__ = "candidate_scores"
    
    person_local_id = Column(Integer, ForeignKey("extended_persons.id"), primary_key=True, index=True)
    fit_score = Column(Float, nullable=False)
    fit_bucket = Column(String(20), nullable=False)  # 'top', 'borderline', 'low'
    computed_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    person = relationship("ExtendedPerson", back_populates="score")


class ClientCache(Base):
    """Cached client data from upstream Aqore API"""
    __tablename__ = "client_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    upstream_client_id = Column(Integer, unique=True, index=True)
    client_name = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    address1 = Column(String(255), nullable=True)
    address2 = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    created_date = Column(DateTime, nullable=True)
    cached_at = Column(DateTime, default=func.now())
