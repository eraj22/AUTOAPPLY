# Resume API & Infrastructure Analysis

## Overview
The AutoApply backend has basic resume support but **lacks file upload functionality**. Currently, resumes are stored as JSON in the database without PDF file handling.

---

## 1. Resume Database Model

### Location: [backend/app/models.py](backend/app/models.py#L70-L77)

```python
class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_resume = Column(JSONB, nullable=False)  # {name, email, phone, skills, experience, etc}
    resume_pdf_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Key Points:**
- **Single resume per system** (no user_id field - TODO comment indicates multi-user support planned)
- `base_resume`: Stores parsed resume data as JSONB
- `resume_pdf_path`: Column exists but is unused (NULL values)
- No actual PDF file storage implemented
- Timestamps for tracking updates

---

## 2. Resume API Endpoints

### Location: [backend/app/api/jobs.py](backend/app/api/jobs.py#L155-L169)

### Endpoints Defined:

#### **POST `/jobs/resume` - Upload/Update Resume**
```python
@router.post("/jobs/resume", response_model=ResumeResponse)
async def upload_resume(resume: ResumeCreate, db: Session = Depends(get_db)):
    """Upload or update resume"""
    # For now, store only one resume (single user)
    # TODO: If multi-user, add user_id
    existing = db.query(Resume).first()
    
    if existing:
        existing.base_resume = resume.base_resume
        db.commit()
        db.refresh(existing)
        return existing
    else:
        db_resume = Resume(**resume.dict())
        db.add(db_resume)
        db.commit()
        db.refresh(db_resume)
        return db_resume
```

**Issues:**
- Expects pre-parsed JSON via `ResumeCreate` schema
- No actual file upload handling (no `UploadFile` parameter)
- No PDF extraction/parsing logic
- Creates or updates single resume only

#### **GET `/jobs/resume` - Retrieve Resume**
```python
@router.get("/jobs/resume", response_model=Optional[ResumeResponse])
async def get_resume(db: Session = Depends(get_db)):
    """Get user's resume"""
    resume = db.query(Resume).first()
    return resume
```

#### **POST `/jobs/parse-resume` - Parse Resume**
```python
@router.post("/jobs/parse-resume")
async def parse_resume_endpoint(db: Session = Depends(get_db)):
    """Parse user's resume with AI"""
    # Extracts structured data from resume text
```

---

## 3. Resume Schema

### Location: [backend/app/schemas.py](backend/app/schemas.py#L6-L20)

```python
class ResumeCreate(BaseModel):
    base_resume: Dict[str, Any]

class ResumeResponse(BaseModel):
    id: uuid.UUID
    base_resume: Dict[str, Any]
    resume_pdf_path: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

**Current State:**
- Only accepts pre-parsed JSON dictionary
- No file/binary data support
- `resume_pdf_path` can be returned but never populated

---

## 4. Resume Parser Service

### Location: [backend/app/services/resume_parser.py](backend/app/services/resume_parser.py)

### ParsedResumeData Schema
Extracts and structures resume information into:

```python
class ParsedResumeData(BaseModel):
    full_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    
    all_skills: List[str]
    technical_skills: List[str]
    soft_skills: List[str]
    
    seniority_level: str  # junior|mid|senior|lead|executive
    years_of_experience: int
    years_in_current_role: Optional[int]
    
    current_title: Optional[str]
    current_company: Optional[str]
    
    past_companies: List[str]
    past_titles: List[str]
    
    education_level: Optional[str]  # Bachelor's|Master's|PhD|Bootcamp
    university: Optional[str]
    degree_field: Optional[str]
    
    certifications: List[str]
    
    primary_focus_area: Optional[str]  # Backend|Frontend|Full-Stack|DevOps|etc
    secondary_focus_areas: List[str]
    
    tech_stack: List[str]
    key_achievements: List[str]
    
    github_url: Optional[str]
    linkedin_url: Optional[str]
    portfolio_url: Optional[str]
    
    open_to_opportunities: bool
    
    preferences: UserPreferences
    confidence_score: float  # 0-1.0
```

### Parser Implementation

The `ResumeParser` class uses **Ollama LLM** for parsing:

```python
class ResumeParser:
    """Parse resume text using Ollama LLM"""
    
    def __init__(self, ollama_url: Optional[str] = None, model: str = "tinyllama"):
        self.ollama_url = ollama_url or settings.ollama_api_url
        self.model = model
        self.timeout = 60.0
    
    async def parse_resume(self, resume_text: str) -> ParsedResumeData:
        """
        Parse resume text and extract structured data
        """
        # 1. Validate text
        if not resume_text or len(resume_text.strip()) < 10:
            logger.warning("Resume text too short or empty")
            return ParsedResumeData(confidence_score=0.0)
        
        # 2. Build prompt for LLM
        prompt = self._build_parsing_prompt(resume_text)
        
        # 3. Call Ollama API
        response = await self._call_ollama(prompt)
        
        # 4. Extract and validate JSON
        parsed_data = self._extract_json_response(response)
        
        # 5. Return structured data
        result = ParsedResumeData(**parsed_data)
        return result
```

**Key Features:**
- Uses **Ollama API** (local LLM) at `http://localhost:11434`
- Model: `tinyllama` (configurable)
- Async processing with 60s timeout
- Returns confidence score (0-1.0)
- Extractsjson from LLM response with fallback parsing

**Limitations:**
- Expects **plain text** input only
- No PDF extraction
- No automatic text detection from files

---

## 5. Resume Data Flow

### Current Resume Lifecycle:

```
1. User provides resume text/JSON
   ↓
2. POST /jobs/resume with ResumeCreate { base_resume: {...} }
   ↓
3. Stored as JSONB in database (Resume table)
   ↓
4. On demand: POST /jobs/parse-resume
   ↓
5. ResumeParser.parse_resume() extracts text from base_resume
   ↓
6. Calls Ollama API to parse text → ParsedResumeData
   ↓
7. Stored in resume.base_resume["parsed"]
   ↓
8. Used for job matching: GET /jobs/matches
```

**Data Structure Example:**
```python
{
    "id": "uuid",
    "base_resume": {
        # Original data provided by user
        "text": "...",
        "content": "...",
        
        # After parsing
        "parsed": {
            "full_name": "John Developer",
            "email": "john@example.com",
            "technical_skills": ["Python", "FastAPI"],
            "years_of_experience": 5,
            ...
        }
    },
    "resume_pdf_path": null,  # Unused
    "created_at": "2026-03-24T...",
    "updated_at": "2026-03-24T..."
}
```

---

## 6. Job Matching Flow

### Location: [backend/app/services/job_matcher.py](backend/app/services/job_matcher.py)

The `JobMatcher` uses parsed resume data to score jobs:

```python
class JobMatcher:
    # Scoring weights
    SKILL_WEIGHT = 0.35       # Most important
    SENIORITY_WEIGHT = 0.20
    SALARY_WEIGHT = 0.20
    REMOTE_WEIGHT = 0.10
    INDUSTRY_WEIGHT = 0.10
    COMPANY_SIZE_WEIGHT = 0.05
    
    def calculate_match(self,
                       parsed_job: ParsedJobData,
                       parsed_resume: ParsedResumeData,
                       job_title: str,
                       company_name: Optional[str],
                       job_id: Optional[str]) -> JobMatchResult:
        """Calculate match score 0-100"""
```

**Match Result:**
```python
class JobMatchResult(BaseModel):
    job_id: Optional[str]
    job_title: str
    match_score: int  # 0-100
    
    skill_match_score: int
    seniority_match_score: int
    salary_match_score: int
    remote_match_score: int
    
    positive_matches: List[str]
    concerns: List[str]
    missing_skills: List[str]
    skill_gaps: List[str]
    
    recommendation: str
```

---

## 7. File Upload Handling - MISSING ⚠️

**Current State:** NO FILE UPLOAD SUPPORT

**What doesn't exist:**
- No `UploadFile` endpoints
- No PDF parsing/extraction library (PyPDF2, pdfplumber, etc.)
- No file storage mechanism (local filesystem, S3, etc.)
- No multipart/form-data handling
- `resume_pdf_path` column in database is unused

**What would be needed to add file upload:**

1. **PDF Extraction Library**
   - Option: `PyPDF2` or `pdfplumber`
   - Needs to be added to `requirements.txt`

2. **File Storage**
   - Option: Store in `/backend/uploads/resumes/` directory with UUID filename
   - Option: Use S3/cloud storage

3. **API Endpoint**
   ```python
   @router.post("/jobs/resume/upload")
   async def upload_resume_file(
       file: UploadFile = File(...),
       db: Session = Depends(get_db)
   ):
       # 1. Validate file is PDF
       # 2. Extract text from PDF
       # 3. Save file to storage
       # 4. Store path in database
       # 5. Parse extracted text with LLM
       # 6. Save parsed data
   ```

4. **Dependencies to add**
   - `python-multipart` - For file upload handling
   - `PyPDF2` or `pdfplumber` - For PDF text extraction

---

## 8. Current Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
└──────────────────────┬──────────────────────────────────┘
                       │  POST /jobs/resume (JSON)
                       ↓
┌─────────────────────────────────────────────────────────┐
│              FastAPI Backend (main.py)                   │
├─────────────────────────────────────────────────────────┤
│  Routers:                                               │
│  ├─ /companies     (companies.py)                       │
│  ├─ /jobs          (jobs.py)         ← Resume endpoints │
│  └─ /settings      (applications.py)                    │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
    ┌────────┐    ┌────────┐    ┌──────────────┐
    │Database│    │ Resume │    │Ollama (LLM)  │
    │(Postgres)   │ Parser │    │              │
    │        │    │Service │    │ tinyllama    │
    └────────┘    └────────┘    └──────────────┘
       JSONB
       Resume
       Table
```

---

## Recommendations for Resume Upload Feature

### Priority 1 (Core Functionality):
1. Add PDF extraction library (`pdfplumber` recommended)
2. Create file upload endpoint with `UploadFile`
3. Implement local file storage in `backend/uploads/resumes/`
4. Update Resume schema to accept file uploads
5. Extract text → Store PDF → Parse with Ollama → Save parsed data

### Priority 2 (Enhancement):
1. Add file validation (size, format)
2. Support multiple file formats (PDF, DOCX, etc.)
3. Store file upload metadata
4. Add resume versioning/history

### Priority 3 (Optional):
1. Cloud storage (S3 AWS, Google Cloud, etc.)
2. Multiple resume support (for different roles)
3. Resume editing/updating UI
4. Resume download functionality

---

## Configuration & Environment

### Location: [backend/app/config.py](backend/app/config.py)

**Key Settings:**
```python
ollama_api_url: str = "http://localhost:11434"  # Ollama API endpoint
database_url: str = "postgresql://..."           # PostgreSQL connection
```

**Docker Setup:**
- Ollama runs in separate container (`ollama:latest`)
- Model pulled: `tinyllama`
- PostgreSQL for data storage

---

## SQL Schema (Resume Table)

From PostgreSQL initialization:

```sql
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    base_resume JSONB NOT NULL,
    resume_pdf_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Summary

| Aspect | Status | Details |
|--------|--------|---------|
| **Resume Endpoints** | ✅ Exists | POST/GET `/jobs/resume` - JSON only |
| **Database Model** | ✅ Exists | SQLAlchemy ORM with JSONB storage |
| **Resume Parser** | ✅ Exists | Ollama LLM integration, text → structured data |
| **Job Matching** | ✅ Exists | Weighted scoring algorithm |
| **File Upload** | ❌ Missing | No PDF/file handling |
| **PDF Extraction** | ❌ Missing | No PDF text extraction |
| **File Storage** | ❌ Missing | `resume_pdf_path` unused |
| **Multipart Upload** | ❌ Missing | No `UploadFile` support |

