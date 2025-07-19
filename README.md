# SajiloHire Backend

FastAPI backend for SajiloHire: **Next-generation AI-powered hiring platform** with deeply personalized onboarding that adapts to each company, role, and candidate. Features comprehensive job profile analysis, company-aware AI interviews, and intelligent scoring using the Aqore Hackathon API with GPT-4o-mini.

## 🚀 Enhanced Features

### **🎯 Personalized AI Onboarding**
- **Company-Aware Conversations**: AI adapts to specific company industry, culture, and values
- **Role-Specific Questioning**: Dynamic questions based on job level (junior/mid/senior) and technical focus
- **Smart Skill Probing**: Targeted technical questions matching job requirements and candidate background
- **Industry Context**: Healthcare, Finance, Tech, Education-specific conversation flows
- **Adaptive Scenarios**: Role-appropriate problem-solving questions (ML, Web Dev, Data Science, etc.)

### **📊 Advanced Job Intelligence**
- **Comprehensive Job Profiles**: Deep analysis of job requirements, company context, and cultural fit
- **Skills Categorization**: Automatic classification (mandatory/preferred, technical/soft, frameworks/languages)
- **Technical Focus Detection**: ML, Web Dev, Data Science, DevOps, Mobile, Security focus identification
- **Growth Opportunity Analysis**: Career advancement potential extraction from job descriptions
- **Company Insights**: Industry-specific values, priorities, and cultural indicators

### **🧠 Enhanced Scoring Engine**
- **Precision Matching**: 40% mandatory skills + 25% key skills + 20% experience + 15% technical alignment
- **Experience Level Assessment**: Proper junior/mid/senior/management level matching
- **Cultural Fit Scoring**: Industry-appropriate values and cultural alignment assessment
- **Technical Depth Analysis**: Role-specific technical competency evaluation
- **Fraud Detection**: Integrity checks with fake technology trap questions

### **💼 Recruiter Intelligence**
- **Smart Dashboards**: Company and role-contextualized candidate rankings
- **Detailed Profiles**: Rich candidate insights with job-specific analysis
- **Skills Gap Analysis**: Visual mapping of candidate skills vs job requirements
- **Interview Insights**: AI conversation analysis with personalization context

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

### **🎯 Core SajiloHire Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sajilo/person` | Create new candidate |
| `POST` | `/sajilo/person/{personId}/extend` | Add job, resume, and profile data |
| `POST` | `/sajilo/chat/{personId}` | **Enhanced** AI interview chat with personalization |
| `GET` | `/sajilo/chat/{personId}/history` | Get chat history |
| `GET` | `/sajilo/dashboard/{jobId}` | **Enhanced** recruiter dashboard with job context |
| `GET` | `/sajilo/candidate/{personId}/full` | **Enhanced** complete candidate profile with job analysis |

### **🏢 Job Profile Intelligence** *(NEW)*

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/sajilo/job-profile/{jobId}` | Complete job and company profile analysis |
| `GET` | `/sajilo/job-profile/{jobId}/context` | Personalization context for AI chat |
| `GET` | `/sajilo/job-profile/{jobId}/skills-analysis` | Detailed skills breakdown and analysis |

### **⚙️ System Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/` | API status |

## 🔄 Enhanced Workflow

### **1. 🎯 Personalized Candidate Application Flow**
```
1. POST /sajilo/person → Create candidate
2. POST /sajilo/person/{id}/extend → Add resume & job details
3. 🧠 System analyzes job profile (company, role, skills, culture)
4. POST /sajilo/chat/{id} → Start personalized AI interview
   - Questions adapt to company industry & culture
   - Technical probing matches job requirements  
   - Scenarios appropriate to role level & focus
5. 📊 Enhanced scoring with job-specific criteria
```

### **2. 💼 Intelligent Recruiter Review Flow**
```
1. GET /sajilo/job-profile/{jobId} → Understand job context & requirements
2. GET /sajilo/dashboard/{jobId} → View candidates ranked by job-specific criteria
3. GET /sajilo/candidate/{personId}/full → Detailed profile with job alignment
4. Review personalized scores, cultural fit, and contextual chat analysis
```

### **3. 🔍 Job Profile Analysis Flow** *(NEW)*
```
1. System fetches job + company + skills data from Aqore API
2. Analyzes industry context, technical focus, role level
3. Identifies mandatory vs preferred skills, cultural indicators
4. Builds personalization context for AI conversations
5. Creates enhanced scoring criteria specific to role
```

## 🏧 Enhanced Architecture

### **📊 Data Models**
- **ExtendedPerson**: Local candidate data with skills, resume, social profiles
- **ChatTurn**: Individual AI interview interactions with intent tracking  
- **CandidateSignals**: Extracted assessment signals (consistency, depth, motivation)
- **CandidateScore**: Final composite scoring with fit buckets
- **ExtendedJobCache**: Cached upstream job data with skills analysis
- **ClientCache**: Company information with industry insights *(Enhanced)*

### **⚙️ Core Services**
- **JobProfileAnalyzer**: 🎯 *NEW* - Comprehensive job & company analysis engine
- **ChatEngine**: 🧠 *Enhanced* - Personalized GPT-4o-mini integration with job context
- **ScoringEngine**: 📊 *Enhanced* - Multi-factor assessment with job-specific criteria
- **CacheService**: 🔄 *Enhanced* - Upstream data sync with skills fetching
- **ResumeProcessor**: 📝 Smart resume parsing and skills extraction

### **📊 Enhanced Scoring Algorithm**
```
# Overall Weighted Score
Weighted Score = (
  enhanced_role_fit * 0.35 +
  capability_depth * 0.20 +
  motivation_alignment * 0.15 +
  reliability_inverse_turnover * 0.15 +
  data_confidence * 0.15
) * confidence_multiplier * fraud_penalty

# Enhanced Role Fit Breakdown (NEW)
enhanced_role_fit = (
  mandatory_skills_match * 0.40 +     # Must-have skills alignment
  key_skills_match * 0.25 +           # Important skills alignment  
  experience_level_match * 0.20 +     # Junior/Mid/Senior level fit
  technical_focus_alignment * 0.15    # ML/Web/Data Science focus fit
)
```

**📦 Fit Buckets**: Top (≥75%), Borderline (≥50%), Low (<50%)
**🔍 Skills Matching**: Precision matching of candidate skills vs job requirements
**🎆 Experience Fit**: Role level compatibility (Junior/Mid/Senior/Management)
**🔧 Technical Alignment**: Specialization area matching (ML, Web Dev, Data Science, etc.)

## 🤖 Enhanced AI Interview Process

The AI conducts **personalized interviews** adapted to company, role, and candidate context:

### **🎯 Core Interview Intents**
1. **🔍 Skill Probe**: Job-specific technical questions matching requirements
   - *Example*: "You listed Python for this ML Engineer role at TechCorp. Describe your most complex deep learning project."

2. **💫 Motivation**: Company and industry-aware interest assessment
   - *Example*: "Why are you interested in working with HealthPlus in the healthcare industry?"

3. **⚠️ Trap**: Integrity check with fake technologies  
   - *Example*: "How would you configure ElasticCacheX Timed Graph Layer for this role?"

4. **⚖️ Values**: Industry-specific cultural alignment
   - *Tech*: "Rank: Innovation, Learning, Growth, Impact"
   - *Healthcare*: "Rank: Patient Care, Quality, Safety, Growth"

5. **🎢 Scenario**: Role and level-appropriate problem-solving
   - *Senior ML*: "Your model affects 100K+ users and performance is degrading..."
   - *Junior Dev*: "Your web app is loading slowly and users are complaining..."

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
