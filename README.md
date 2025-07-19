# SajiloHire Backend

FastAPI backend for SajiloHire: AI-powered hiring platform that wraps the Aqore Hackathon API with extended candidate data, GPT-4o-mini onboarding, and intelligent scoring.

## 🚀 Features

- **Local Candidate Management**: Store extended candidate data locally without upstream sync
- **AI Onboarding**: Interactive GPT-4o-mini chat interviews with dynamic questioning
- **Intelligent Scoring**: Composite scoring combining technical fit, motivation, and turnover risk
- **Recruiter Dashboard**: Ranked candidate lists with filtering and insights
- **Upstream Integration**: Caches jobs and client data from Aqore API on startup
- **Comprehensive Profiles**: Full candidate views with skills assessment and chat history

## 📋 Requirements

- Python 3.11+
- SQLite (default) or PostgreSQL
- Access to Aqore Hackathon API
- Azure OpenAI GPT-4o-mini endpoint

## 🛠 Installation & Setup

### 1. Clone and Install Dependencies

```bash
cd /home/theamal/r3x/aqore/sajilohire-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Aqore API Configuration
AQORE_API_BASE=https://hackathonapi.aqore.com

# GPT Configuration (Already configured for Hackathon)
GPT_API_KEY=F0f8PjPGohraL0zjmrmWfix0ABy5iXmToB0O9fzNxGyKpP5nZkX7JQQJ99BFACHrzpqXJ3w3AAABACOGYk5Y
GPT_API_ENDPOINT=https://aqore-hackathon-openai.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions?api-version=2025-01-01-preview
GPT_MODEL=gpt-4o-mini

# Database Configuration
DATABASE_URL=sqlite:///./sajilohire.db

# Application Configuration
SAJILO_OFFLINE_MODE=false
SECRET_KEY=your-secret-key-change-in-production
```

### 3. Run the Development Server

```bash
python main.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📚 API Endpoints

### Core SajiloHire Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sajilo/person` | Create new candidate |
| `POST` | `/sajilo/person/{personId}/extend` | Add job, resume, and profile data |
| `POST` | `/sajilo/chat/{personId}` | AI interview chat |
| `GET` | `/sajilo/chat/{personId}/history` | Get chat history |
| `GET` | `/sajilo/dashboard/{jobId}` | Recruiter dashboard |
| `GET` | `/sajilo/candidate/{personId}/full` | Complete candidate profile |

### System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/` | API status |

## 🔄 Workflow

### 1. Candidate Application Flow
```
1. POST /sajilo/person → Create candidate
2. POST /sajilo/person/{id}/extend → Add resume & job details
3. POST /sajilo/chat/{id} → Start AI interview (5+ turns)
4. System computes signals & scores automatically
```

### 2. Recruiter Review Flow
```
1. GET /sajilo/dashboard/{jobId} → View ranked candidates
2. GET /sajilo/candidate/{personId}/full → Detailed profile
3. Review scores, flags, and chat transcripts
```

## 🏗 Architecture

### Data Models
- **ExtendedPerson**: Local candidate data with skills, resume, social profiles
- **ChatTurn**: Individual AI interview interactions with intent tracking  
- **CandidateSignals**: Extracted assessment signals (consistency, depth, motivation)
- **CandidateScore**: Final composite scoring with fit buckets
- **ExtendedJobCache**: Cached upstream job data with skills

### Services
- **ChatEngine**: GPT-4o-mini integration with dynamic questioning
- **ScoringEngine**: Multi-factor candidate assessment
- **CacheService**: Upstream data synchronization

### Scoring Algorithm
```
Weighted Score = (
  role_fit * 0.35 +
  capability_depth * 0.20 +
  motivation_alignment * 0.15 +
  reliability_inverse_turnover * 0.15 +
  data_confidence * 0.15
) * confidence_multiplier * fraud_penalty
```

**Fit Buckets**: Top (≥75%), Borderline (≥50%), Low (<50%)

## 🤖 AI Interview Process

The AI conducts structured interviews with 5 core intents:

1. **Skill Probe**: Deep technical questions about listed skills
2. **Motivation**: Understanding interest and alignment  
3. **Trap**: Integrity check with fake technologies
4. **Values**: Priority ranking for culture fit
5. **Scenario**: Problem-solving approach assessment

## 🗄 Database Schema

### Key Relationships
```
ExtendedPerson (1) → (N) ChatTurn
ExtendedPerson (1) → (1) CandidateSignals  
ExtendedPerson (1) → (1) CandidateScore
```

### Startup Behavior
- Creates all tables automatically
- Syncs jobs and clients from Aqore API
- Ready for candidate applications

## 🧪 Development

### Running Tests
```bash
pytest
```

### Database Migrations
For schema changes:
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Adding New Endpoints
1. Create router in `routers/`
2. Add business logic to `services/`
3. Update schemas in `schemas.py`
4. Include router in `main.py`

## 🔧 Configuration

### Scoring Weights (Configurable)
```python
SCORING_WEIGHTS = {
    "role_fit": 0.35,
    "capability_depth": 0.20, 
    "motivation_alignment": 0.15,
    "reliability_inverse_turnover": 0.15,
    "data_confidence": 0.15
}
```

### Chat Configuration
```python
CHAT_MIN_TURNS = 5
CHAT_INTENTS = ["skill_probe", "motivation", "trap", "values", "scenario"]
```

## 📊 Sample Usage

### Create & Extend Candidate
```bash
# Create candidate
curl -X POST http://localhost:8000/sajilo/person \
  -H "Content-Type: application/json" \
  -d '{"first_name": "John", "last_name": "Doe", "email": "john@example.com", "job_id": 123}'

# Extend with resume  
curl -X POST http://localhost:8000/sajilo/person/1/extend \
  -H "Content-Type: application/json" \
  -d '{"job_id": 123, "resume_text": "Senior Developer with 5 years...", "skills": "React,Python,AWS"}'
```

### AI Interview
```bash
curl -X POST http://localhost:8000/sajilo/chat/1 \
  -H "Content-Type: application/json" \
  -d '{"message": "I have experience with React and built several large applications..."}'
```

### Dashboard
```bash
curl http://localhost:8000/sajilo/dashboard/123?include_borderline=false
```

## 📈 Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

Returns database and upstream API status.

### Logging
Structured logging to console with configurable levels.

## 🔒 Security Notes

- Change `SECRET_KEY` in production
- Consider API authentication for production use
- GPT API key is pre-configured for hackathon
- SQLite suitable for development, use PostgreSQL for production

## 🤝 Contributing

1. Follow existing code patterns
2. Add comprehensive error handling  
3. Update schemas for new endpoints
4. Test with various candidate scenarios
5. Document significant changes

---

**SajiloHire Backend v1.0.0** - AI-powered hiring made simple! 🎯
