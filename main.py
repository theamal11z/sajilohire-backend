#!/usr/bin/env python3
"""
SajiloHire Backend API
FastAPI backend for AI-powered hiring platform
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from database import engine, Base
from routers import health, sajilo_person, sajilo_person_extend, sajilo_chat, sajilo_dashboard, sajilo_candidate, sajilo_job_profile, sajilo_insights
from services.cache_service import sync_upstream_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup - Create tables and sync data
    print("🚀 Starting SajiloHire Backend...")
    Base.metadata.create_all(bind=engine)
    
    # Sync upstream data on startup
    if not settings.SAJILO_OFFLINE_MODE:
        print("📡 Syncing upstream data from Aqore API...")
        try:
            await sync_upstream_data()
            print("✅ Upstream data sync completed")
        except Exception as e:
            print(f"⚠️ Failed to sync upstream data: {e}")
    
    yield
    
    # Shutdown
    print("👋 Shutting down SajiloHire Backend...")


# Initialize FastAPI app
app = FastAPI(
    title="SajiloHire Backend API",
    description="AI-powered hiring platform backend wrapping Aqore Hackathon API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(sajilo_person.router, prefix="/sajilo", tags=["Person"])
app.include_router(sajilo_person_extend.router, prefix="/sajilo", tags=["Person"])
app.include_router(sajilo_chat.router, prefix="/sajilo", tags=["Chat"])
app.include_router(sajilo_dashboard.router, prefix="/sajilo", tags=["Dashboard"])
app.include_router(sajilo_candidate.router, prefix="/sajilo", tags=["Candidate"])
app.include_router(sajilo_job_profile.router, prefix="/sajilo", tags=["Job Profile"])
app.include_router(sajilo_insights.router, prefix="/sajilo", tags=["Enhanced Insights"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SajiloHire Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
