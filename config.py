"""
Configuration settings for SajiloHire Backend
Uses pydantic-settings for environment variable management
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./sajilohire.db"
    
    # Aqore API settings
    AQORE_API_BASE: str = "https://hackathonapi.aqore.com"
    
    # GPT/OpenAI settings
    GPT_API_KEY: str
    GPT_API_ENDPOINT: str = "https://aqore-hackathon-openai.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2025-01-01-preview"
    GPT_MODEL: str = "gpt-4o-mini"
    
    # Application settings
    SAJILO_OFFLINE_MODE: bool = False
    SECRET_KEY: str = "sajilo-hire-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Scoring configuration
    SCORING_WEIGHTS: dict = {
        "role_fit": 0.35,
        "capability_depth": 0.20,
        "motivation_alignment": 0.15,
        "reliability_inverse_turnover": 0.15,
        "data_confidence": 0.15
    }
    
    SCORING_THRESHOLDS: dict = {
        "top": 0.75,
        "borderline": 0.50
    }
    
    FRAUD_PENALTY_MULTIPLIER: float = 0.25
    
    # Chat configuration
    CHAT_MIN_TURNS: int = 5
    CHAT_INTENTS: list = [
        "skill_probe",
        "motivation", 
        "trap",
        "values",
        "scenario"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
