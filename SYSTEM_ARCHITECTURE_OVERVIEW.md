# AutoApply System Architecture Overview

**Last Updated**: April 11, 2026  
**Purpose**: Complete architectural reference for Phase 5 (Workflow Integration)  
**Status**: Phases 1-4 & 6 Complete | Phase 5 Ready to Plan

---

## 1. CORE SERVICES

### 1.1 Scraper Service
**Location**: `backend/app/services/scraper.py`  
**Class**: `JobScraper`  

**Capabilities**:
- Multi-platform job scraping using Playwright browser automation
- Supports: GitHub Jobs, with extensible architecture for LinkedIn, Indeed, Glassdoor
- Returns: List of dictionaries with title, company, location, URL, source, scraped_at

**Key Methods**:
- `async scrape_github_jobs(search_query)` - Scrape GitHub Jobs board
- Async context manager for browser lifecycle management
- Headless Chromium launch

**Output Format**:
```python
{
    "title": "Senior Backend Engineer",
    "company": "TechCorp",
    "location": "Remote",
    "url": "https://...",
    "source": "github_jobs",
    "scraped_at": "2026-04-11T10:30:00"
}
```

---

### 1.2 Job Parser Service
**Location**: `backend/app/services/job_parser.py`  
**Class**: `JobParser` (via `get_job_parser()`)  

**Capabilities**:
- Converts unstructured job descriptions into standardized, machine-readable data
- Uses Ollama LLM for intelligent extraction
- Returns `ParsedJobData` Pydantic model

**Parsed Fields** (23 fields):
- **Skills**: `required_skills[]`, `nice_to_have_skills[]`
- **Compensation**: `salary_min`, `salary_max`, `salary_currency`
- **Work Type**: `remote_type` (fully_remote|hybrid|onsite), `role_type` (Full-time|Contract|etc)
- **Level**: `seniority_level` (junior|mid|senior|lead|executive)
- **Company**: `company_size`, `company_stage`, `industry`
- **Requirements**: `experience_required_years`, `education_required`, `visa_sponsorship`
- **Details**: `location`, `tech_stack[]`, `benefits[]`, `responsibilities[]`, `growth_opportunities[]`
- **Metadata**: `travel_required`, `estimated_interview_rounds`, `confidence_score`

**Key Methods**:
- `parse_job_description(raw_jd: str) -> ParsedJobData` - Main parsing method
- Ollama API integration for LLM-based extraction
- Confidence scoring (0-1.0)

**Output Format**:
```python
ParsedJobData(
    required_skills=["Python", "FastAPI", "PostgreSQL"],
    seniority_level="mid",
    salary_min=140000,
    salary_max=180000,
    remote_type="hybrid",
    location="San Francisco, CA",
    company_size="201-1000",
    company_stage="Series C",
    confidence_score=0.92
)
```

---

### 1.3 Resume Parser Service
**Location**: `backend/app/services/resume_parser.py`  
**Class**: `ResumeParser` (via `get_resume_parser()`)  

**Capabilities**:
- Extracts structured data from resume documents (PDF/text)
- Uses Ollama LLM for intelligent extraction
- Returns `ParsedResumeData` Pydantic model

**Parsed Fields**:
- **Personal**: name, email, phone
- **Professional**: skills[], experience (companies, roles, duration)
- **Education**: degrees, schools, certifications
- **Level**: `seniority_level`, `years_of_experience`
- **Keywords**: languages, technologies, specializations

**Key Methods**:
- `parse_resume(resume_text: str) -> ParsedResumeData` - Main parsing method
- Supports JSON and PDF input (with conversion)

---

### 1.4 Job Matcher Service
**Location**: `backend/app/services/job_matcher.py`  
**Class**: `JobMatcher` (via `get_job_matcher()`)  

**Capabilities**:
- Matches parsed jobs against user resume
- Multi-dimensional scoring algorithm
- Returns `JobMatchResult` with detailed breakdown

**Scoring Weights**:
- Skill Match: **35%** (most important)
- Seniority: **20%**
- Salary: **20%**
- Remote Type: **10%**
- Industry: **10%**
- Company Size: **5%**

**Output Scores** (all 0-100):
- `match_score` - Overall composite score
- `skill_match_score` - Skill alignment
- `seniority_match_score` - Experience level fit
- `salary_match_score` - Compensation alignment
- `remote_match_score` - Work arrangement fit

**Detailed Output**:
```python
JobMatchResult(
    job_id="uuid",
    job_title="Senior Backend Engineer",
    match_score=87,
    skill_match_score=95,
    seniority_match_score=85,
    salary_match_score=78,
    remote_match_score=100,
    positive_matches=["Strong Python experience", "Familiar with FastAPI"],
    concerns=["Requires Kubernetes experience (you have basic knowledge)"],
    missing_skills=["Kubernetes"],
    skill_gaps=["AWS (required), GCP preferred"],
    salary_gap=0,
    recommendation="Excellent fit - Apply now"
)
```

**Key Methods**:
- `calculate_match(parsed_job, parsed_resume, job_title, company_name, job_id) -> JobMatchResult`
- Weighted scoring algorithm
- Generates human-readable feedback

---

### 1.5 Application Bot Service
**Location**: `backend/app/services/application_bot.py`  
**Classes**: `ApplicationBot`, `ATSDetector`, `FormExtractor`, `FormFiller`  

**Capabilities**:
- Automated job application form filling and submission
- ATS detection and platform-specific handling
- Browser automation with Playwright

**Supported ATS Platforms** (9 types):
1. **Greenhouse** - boards.greenhouse.io
2. **Lever** - lever.co
3. **Workday** - workday.com
4. **Ashby** - ashby.com
5. **SmartRecruiters** - smartrecruiters.com
6. **BambooHR** - bamboohr.com
7. **Taleo** - taleo.com
8. **iCIMS** - icims.com
9. **Generic** - Fallback for unknown platforms
10. **Direct Email** - Manual email applications

**Core Components**:

**ATSDetector**:
- Pattern matching on URL and page HTML
- Confidence scoring (0-1.0)
- Returns `ATSType` enum

**FormExtractor**:
- Platform-specific extractors (Greenhouse, Lever, Workday)
- Generic fallback extractor
- Detects: text input, email, textarea, file upload, select, radio, checkbox
- Finds submit button automatically
- Returns `ApplicationForm` with field list

**FormFiller**:
- Smart field mapping: name, email, phone, location, resume, cover letter
- Pattern-based matching for common labels
- Handles all field types
- Validates required fields before submission

**ApplicationBot** (Main Orchestrator):
- Async context manager for browser lifecycle
- End-to-end workflow:
  1. Navigate to job URL
  2. Detect ATS platform
  3. Extract form structure
  4. Fill form with candidate data
  5. Submit application
  6. Detect success indicators
  7. Capture screenshot for verification

**Key Methods**:
- `async apply_to_job(job_url, parsed_job, parsed_resume) -> ApplicationResult`
- `async detect_ats(page) -> ATSType`
- `async extract_form(page, ats_type) -> ApplicationForm`
- `async fill_form(page, form, resume_data, cover_letter) -> bool`

**Output Format**:
```python
ApplicationResult(
    success=True,
    ats_type=ATSType.GREENHOUSE,
    job_url="https://...",
    submitted_at=datetime.utcnow(),
    message="Application submitted successfully",
    errors=[],
    form_data_captured={"name": "John Doe", "email": "john@example.com"},
    screenshot_path="/screenshots/job_123_submitted.png"
)
```

---

### 1.6 Email Service
**Location**: `backend/app/services/email_service.py`  

**Capabilities**:
- Send transactional emails via Resend API
- HTML templates with Jinja2
- Email tracking and logging to database
- 5 email types

**Email Types**:
1. **APPROVAL_NEEDED** - "A job matching your profile needs approval"
2. **AUTO_APPLIED** - "We've applied to this job for you"
3. **APPLICATION_CONFIRMED** - "Your application has been submitted"
4. **MANUAL_REQUIRED** - "This application requires manual action"
5. **DAILY_DIGEST** - "Your daily job matching summary"

**Supported Recipients**: Configurable via `UserSettings.notification_email`

**Key Functions**:
- `send_email(to_email, subject, html_content, email_type, job_id, db) -> dict`
- `send_approval_email(email, job, match_score, approval_token)`
- `send_auto_applied_email(email, job, fit_score)`
- `send_application_confirmed_email(email, job)`
- `send_manual_required_email(email, job, issue_description)`
- `send_daily_digest_email(email, today_jobs, stats)`

**Logging**:
- All emails logged to `email_logs` table
- Tracks: recipient, type, job_id, resend_id, sent_at, delivery_status, opens, clicks

**Integration**:
- Resend API key from `.env` (RESEND_API_KEY)
- Email from address: `.env` (EMAIL_FROM)
- HTML templates in `backend/templates/emails/`

---

### 1.7 Cover Letter Generator Service
**Location**: `backend/app/services/cover_letter_generator.py`  
**Class**: `CoverLetterGenerator` (via `get_cover_letter_generator()`)  

**Capabilities**:
- Generates tailored cover letters using Ollama LLM
- Customized per job using parsed job and resume data

**Key Methods**:
- `generate_cover_letter(parsed_job, parsed_resume, company_name) -> str`

---

### 1.8 Resume Tailor Service
**Location**: `backend/app/services/resume_tailor.py`  
**Class**: `ResumeTailor`

**Capabilities**:
- Tailors resume to specific job posting
- Reorders experience/skills to highlight relevant items
- Uses LLM for intelligent customization

**Key Methods**:
- `tailor_resume(base_resume, parsed_job) -> TailoredResume`

---

## 2. DATABASE MODELS & SCHEMA

**Database**: PostgreSQL 15  
**ORM**: SQLAlchemy  
**Location**: `backend/app/models.py`

### 2.1 Company Model
```python
class Company(Base):
    __tablename__ = "companies"
    
    id: UUID (PK)
    name: String(255) [UNIQUE, INDEX]
    careers_url: String(500)
    ats_platform: String(100) - specific ATS used (greenhouse, lever, etc)
    ats_url: String(500)
    application_mode: String(50) - "global", "always_ask", "always_auto", "paused"
    last_scraped_at: DateTime
    created_at: DateTime
    updated_at: DateTime
```

**Purpose**: Track companies to monitor for job postings, store ATS platform info

---

### 2.2 Job Model
```python
class Job(Base):
    __tablename__ = "jobs"
    
    id: UUID (PK)
    company_id: UUID (FK) [INDEX]
    title: String(255)
    url: String(500) [UNIQUE]
    source: String(50) [INDEX] - "linkedin", "indeed", "glassdoor", "github", etc
    external_job_id: String(255) [INDEX] - ID from source platform
    location: String(255) [INDEX]
    raw_jd: Text - Original job description
    parsed_jd: JSONB - Parsed job data (ParsedJobData as JSON)
    parser_version: String(50) - Parser version used
    parsed_at: DateTime - When parsed
    match_score: Integer (0-100)
    fit_score: Integer (0-100)
    status: String(50) [DEFAULT='new']
    found_at: DateTime
    scraped_at: DateTime
    approval_token: String(500) - JWT token for email approval links
    token_expires_at: DateTime
    created_at: DateTime
    updated_at: DateTime
```

**Status Enum**:
- `NEW` - Just scraped, not yet parsed
- `PENDING_APPROVAL` - Awaiting user approval
- `APPLYING` - Application in progress
- `APPLIED` - Application submitted
- `SKIPPED` - User rejected
- `FAILED` - Application failed
- `MANUAL_NEEDED` - Requires manual intervention
- `WITHDRAWN` - User withdrew

**Purpose**: Store all discovered jobs with full parsing/matching metadata

---

### 2.3 Application Model
```python
class Application(Base):
    __tablename__ = "applications"
    
    id: UUID (PK)
    job_id: UUID (FK) [INDEX]
    resume_path: String(500)
    cover_letter: Text
    submitted_at: DateTime
    method: String(50) - "auto", "manual", "approved"
    screenshot_path: String(500)
    notes: Text
    created_at: DateTime
    updated_at: DateTime
```

**Purpose**: Track all application submission attempts with outcomes

---

### 2.4 Resume Model
```python
class Resume(Base):
    __tablename__ = "resumes"
    
    id: UUID (PK)
    base_resume: JSONB - Structured resume data {name, email, phone, skills, experience}
    resume_pdf_path: String(500)
    created_at: DateTime
    updated_at: DateTime
```

**Purpose**: Store parsed resume data in structured format for matching

---

### 2.5 UserSettings Model
```python
class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id: UUID (PK)
    notification_email: String(255)
    global_mode: String(50) [DEFAULT='approval'] - "approval" or "auto_apply"
    fit_score_threshold: Integer [DEFAULT=65] - Minimum score to show jobs
    auto_apply_threshold: Integer [DEFAULT=75] - Score to auto-apply
    target_roles: JSONB - ["Backend Engineer", "Full Stack", etc]
    excluded_keywords: JSONB - ["C++", "embedded", etc]
    min_years_experience: Integer
    daily_digest_time: String(5) - "HH:MM" format
    scrape_interval_hours: Integer [DEFAULT=6]
    created_at: DateTime
    updated_at: DateTime
```

**Purpose**: User preferences for job matching, approval workflow, and notifications

---

### 2.6 CompanyIntel Model
```python
class CompanyIntel(Base):
    __tablename__ = "company_intel"
    
    id: UUID (PK)
    company_id: UUID (FK) [INDEX]
    avg_response_days: Integer
    interview_stages: Integer
    applicant_tips: Text
    source: String(100) - "reddit", "glassdoor", "linkedin", etc
    fetched_at: DateTime
    created_at: DateTime
```

**Purpose**: Store company insights for better candidate experience prediction

---

### 2.7 EmailLog Model
```python
class EmailLog(Base):
    __tablename__ = "email_logs"
    
    id: UUID (PK)
    to_email: String(255) [INDEX]
    email_type: String(50) - APPROVAL_NEEDED, AUTO_APPLIED, APPLICATION_CONFIRMED, etc
    job_id: UUID (FK) [INDEX]
    subject: String(255)
    resend_id: String(255) - ID from Resend API
    sent_at: DateTime
    deliver_status: String(50) - "delivered", "bounced", "complained", etc
    opened_at: DateTime
    clicked_at: DateTime
    context: JSONB - Additional metadata
    created_at: DateTime
    updated_at: DateTime
```

**Purpose**: Audit trail and analytics for email campaigns

---

## 3. API ENDPOINTS

**Base URL**: `http://localhost:8000`  
**API Docs**: `http://localhost:8000/docs`  
**Prefix**: `/api/v1` (not yet implemented, routes are at root)

### 3.1 Companies Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/companies` | List all companies |
| `POST` | `/companies` | Create new company |
| `GET` | `/companies/{id}` | Get company details |
| `PUT` | `/companies/{id}` | Update company settings |
| `DELETE` | `/companies/{id}` | Delete company |

**Request/Response Examples**:
```bash
# Create company
POST /companies
{
  "name": "TechCorp Industries",
  "careers_url": "https://careers.techcorp.com",
  "ats_platform": "greenhouse",
  "ats_url": "https://boards.greenhouse.io/techcorp"
}

# Response
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "TechCorp Industries",
  "application_mode": "global",
  "last_scraped_at": null,
  "created_at": "2026-04-11T10:00:00Z"
}
```

---

### 3.2 Jobs Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/jobs` | List jobs (filterable by company_id, status) |
| `POST` | `/jobs` | Create job (manual entry) |
| `GET` | `/jobs/{id}` | Get job details with all parsing/matching metadata |
| `PUT` | `/jobs/{id}` | Update job |
| `DELETE` | `/jobs/{id}` | Delete job |
| `GET` | `/jobs/{id}/parsed` | Get parsed job data |
| `POST` | `/jobs/{id}/parse` | Trigger parsing (background) |
| `POST` | `/jobs/{id}/match` | Calculate match with resume |
| `POST` | `/jobs/seed` | Seed database with test jobs |

**Query Parameters**:
- `company_id` - Filter by company UUID
- `status` - Filter by status (new, pending_approval, applied, etc)
- `limit` - Limit results (default 100, max 1000)

**Request/Response Examples**:
```bash
# List jobs with filters
GET /jobs?company_id=550e8400-e29b-41d4-a716-446655440000&status=pending_approval&limit=50

# Response
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "company_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Senior Backend Engineer",
    "url": "https://boards.greenhouse.io/techcorp/jobs/123",
    "fit_score": 87,
    "status": "pending_approval",
    "found_at": "2026-04-10T14:30:00Z"
  }
]

# Get parsed job data
GET /jobs/550e8400-e29b-41d4-a716-446655440001/parsed

# Response
{
  "required_skills": ["Python", "FastAPI", "PostgreSQL"],
  "seniority_level": "mid",
  "salary_min": 140000,
  "salary_max": 180000,
  "remote_type": "hybrid",
  "location": "San Francisco, CA",
  "company_size": "201-1000"
}

# Calculate match with current resume
POST /jobs/550e8400-e29b-41d4-a716-446655440001/match

# Response
{
  "match_score": 87,
  "skill_match_score": 95,
  "seniority_match_score": 85,
  "salary_match_score": 78,
  "recommendation": "Excellent fit - Apply now"
}
```

---

### 3.3 Applications Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/applications` | List applications |
| `GET` | `/applications/{id}` | Get application details |
| `POST` | `/applications/{job_id}/apply` | Apply to job |
| `DELETE` | `/applications/{job_id}` | Withdraw application |
| `GET` | `/applications/stats/summary` | Get application statistics |

**Query Parameters**:
- `job_id` - Filter by job UUID
- `status` - Filter by method (auto, manual, approved)
- `limit` - Limit results (default 100, max 1000)

**Request/Response Examples**:
```bash
# Apply to job (with approval)
POST /applications/550e8400-e29b-41d4-a716-446655440001/apply?require_approval=true

# Response
{
  "status": "approval_requested",
  "message": "Approval email sent to user@example.com",
  "approval_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "approval_expires_at": "2026-04-12T10:30:00Z"
}

# Withdraw application
DELETE /applications/550e8400-e29b-41d4-a716-446655440001

# Get application stats
GET /applications/stats/summary

# Response
{
  "total_applications": 42,
  "applied_by_method": {
    "auto": 15,
    "manual": 8,
    "approved": 19
  },
  "applied_jobs": 42
}
```

---

### 3.4 Settings Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/settings` | Get user settings (or create default) |
| `POST` | `/settings` | Create user settings |
| `PUT` | `/settings/{id}` | Update settings |
| `DELETE` | `/settings/{id}` | Delete settings |

**Request/Response Examples**:
```bash
# Get settings
GET /settings

# Response
{
  "id": "550e8400-e29b-41d4-a716-446655440099",
  "notification_email": "user@example.com",
  "global_mode": "approval",
  "fit_score_threshold": 65,
  "auto_apply_threshold": 75,
  "target_roles": ["Backend Engineer", "Full Stack Developer"],
  "excluded_keywords": ["C++", "embedded"],
  "daily_digest_time": "08:00",
  "scrape_interval_hours": 6
}

# Update settings
PUT /settings/550e8400-e29b-41d4-a716-446655440099
{
  "auto_apply_threshold": 80,
  "target_roles": ["Backend Engineer", "DevOps Engineer"]
}
```

---

### 3.5 Utility Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/` | Root/welcome endpoint |
| `GET` | `/docs` | Swagger UI documentation |
| `GET` | `/redoc` | ReDoc documentation |

---

## 4. BACKGROUND TASKS & JOB QUEUE

**Current Status**: Placeholder implementation  
**Location**: `backend/tasks/scrape_jobs.py`  
**Queue System**: Redis (configured but not yet integrated)

### 4.1 Current Implementation
```python
# TODO: Implement Celery task

def scrape_jobs_task(company_id: str):
    """Celery task to scrape jobs for a company"""
    pass

def apply_to_job_task(job_id: str):
    """Celery task to apply to a job"""
    pass
```

### 4.2 Configuration Available
- **Redis URL**: Configured in `.env` (REDIS_URL)
- **Queuing Strategy**: Ready for Celery or RQ (Redis Queue)
- **Database**: PostgreSQL for result persistence

### 4.3 Planned Tasks
1. **Scraping Task** - Run scraper for each company on schedule
2. **Parsing Task** - Parse raw job descriptions in background
3. **Matching Task** - Calculate match scores
4. **Application Task** - Auto-apply to jobs
5. **Email Task** - Send batch emails
6. **Digest Task** - Generate daily summaries

### 4.4 Configuration (Ready for Implementation)
```python
# tasks.py
from celery import Celery
from app.config import get_settings

settings = get_settings()

app = Celery('autoapply', broker=settings.redis_url)
app.conf.result_backend = settings.redis_url
app.conf.broker_connection_retry_on_startup = True

@app.task(name='scrape_jobs')
def scrape_jobs_task(company_id: str):
    # Implementation pending
    pass

@app.task(name='parse_job')
def parse_job_task(job_id: str):
    # Implementation pending
    pass

@app.task(name='apply_job')
def apply_job_task(job_id: str):
    # Implementation pending
    pass
```

---

## 5. DATA FLOW BETWEEN PHASES

### 5.1 Phase 2: Job Scraping → Phase 3A: Parsing

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: JOB SCRAPER                                        │
│                                                             │
│ Playwright-based scraping of job boards                    │
│ Input: Search queries, company careers pages              │
│                                                             │
│ Output: Raw job listings                                   │
│ {title, company, location, url, source, scraped_at}       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ╔═════════════════════════════╗
         ║  Store in Job.raw_jd        ║
         ║  Set status = 'new'         ║
         ║  Queue parse task           ║
         ╚═════════════════════════════╝
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3A: JOB PARSER                                        │
│                                                             │
│ LLM-based (Ollama) parsing of raw job descriptions        │
│ Input: Job.raw_jd                                          │
│                                                             │
│ Output: Structured job data (ParsedJobData)               │
│ {skills, salary, seniority, remote_type, ...}             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ╔═════════════════════════════╗
         ║  Store in Job.parsed_jd     ║
         ║  Set parser_version         ║
         ║  Set parsed_at              ║
         ║  Queue match task           ║
         ╚═════════════════════════════╝
```

---

### 5.2 Phase 3A: Parsing → Matching

```
┌─────────────────────────────────────────────────────────────┐
│ JOB PARSER OUTPUT                                           │
│ Job.parsed_jd (ParsedJobData JSON)                          │
│ {required_skills, salary_range, remote_type, etc}          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ╔═════════════════════════════╗
         ║  Get Resume.base_resume     ║
         ║  Parse into ParsedResumeData║
         ║  Extract user skills, level ║
         ║  Extract experience, salary ║
         ╚═════════════════════════════╝
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ JOB MATCHER                                                 │
│                                                             │
│ Multi-dimensional scoring algorithm                        │
│ Compares ParsedJobData vs ParsedResumeData                │
│                                                             │
│ Output: JobMatchResult                                     │
│ {match_score: 87, skill_match: 95, recommendations: [...]} │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ╔═════════════════════════════╗
         ║  Store in Job.match_score   ║
         ║  Store recommendation logic ║
         ║  Set status based on score  ║
         ║  If score > threshold:      ║
         ║    Queue approval email     ║
         ║  Else:                      ║
         ║    Skip or store for review ║
         ╚═════════════════════════════╝
```

---

### 5.3 Approval → Application Bot → Email Notification

```
┌─────────────────────────────────────────────────────────────┐
│ USER DECISION WORKFLOW                                      │
│                                                             │
│ Job.match_score >= fit_score_threshold                      │
│                                                             │
│ Option A: Approval Mode (Default)                          │
│   └─ Match meets threshold → Send approval email            │
│      User clicks approve → Application Bot triggered        │
│   └─ User clicks skip → Job marked as skipped              │
│                                                             │
│ Option B: Auto-Apply Mode                                  │
│   └─ Match >= auto_apply_threshold → Auto-apply            │
│      Match below → Send digest notification                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ╔═════════════════════════════╗
         ║  APPLICATION BOT TRIGGERED  ║
         ║  New Application record     ║
         ║  Set status = 'applying'    ║
         ║  Get Job.url                ║
         ║  Get Resume data            ║
         ║  Get Cover Letter           ║
         ╚═════════════════════════════╝
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3B: APPLICATION BOT                                   │
│                                                             │
│ Playwright browser automation                              │
│ 1. Navigate to Job URL                                     │
│ 2. Detect ATS platform                                     │
│ 3. Extract form structure                                  │
│ 4. Fill form with resume/cover letter                      │
│ 5. Submit application                                      │
│ 6. Capture screenshot                                      │
│ 7. Detect success                                          │
│                                                             │
│ Output: ApplicationResult                                  │
│ {success: bool, ats_type, message, errors, screenshot}    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
         ╔═════════════════════════════╗
         ║  SUCCESS?                   ║
         ├─────────┬───────────────────┘
         │         │
   YES   │         │ NO
         ▼         ▼
    ╔═════════╗ ╔════════════════╗
    │APPLIED  │ │MANUAL_NEEDED / │
    │         │ │    FAILED      │
    ╚════┬════╝ ╚────────┬───────╝
         │               │
         ├───────┬───────┘
                 ▼
    ╔═════════════════════════╗
    │ Update Job.status       │
    │ Create Application      │
    │ Store screenshot_path   │
    │ Queue thank you email   │
    ╚═════════────┬───────────╝
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 4: EMAIL SERVICE                                      │
│                                                             │
│ Send transactional emails via Resend API                   │
│ Types:                                                      │
│   1. Approval needed (from Phase 3 Matching)               │
│   2. Auto-applied (from Phase 3 Application Bot)           │
│   3. Confirmation (from Phase 3 Application Bot success)   │
│   4. Manual required (from Phase 3 Application Bot failure) │
│   5. Daily digest (Scheduled email with summary)           │
│                                                             │
│ Output: EmailLog record with tracking data                 │
└─────────────────────────────────────────────────────────────┘
```

---

### 5.4 Complete End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ SCHEDULE TRIGGER (Every 6 hours or manual)                  │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
        ╔═════════════════════════════╗
        ║  Scrape Jobs (Phase 2)      ║
        │  For each company in system │
        ║  Get new job listings       ║
        ╚═════────────┬───────────────╝
                      │
                      ▼
        ╔═════════════════════════════╗
        ║  Store Raw Jobs             ║
        │  Job.status = 'new'         │
        │  Enqueue parse tasks        ║
        ╚═════────────┬───────────────╝
                      │
        ┌─────────────┴──────────────┐
        ▼                            ▼
    ┌──────────────┐          ┌──────────────┐
    │ Parse Job    │          │ Parse Resume │
    │ (Ollama LLM) │          │ (Ollama LLM) │
    └──────┬───────┘          └──────┬───────┘
           │                         │
           └──────────┬──────────────┘
                      ▼
        ╔═════════════════════════════╗
        ║  Calculate Match Score      ║
        │  Compare ParsedJobData vs   │
        │  ParsedResumeData           ║
        ║  Using weighted algorithm   ║
        ╚═════────────┬───────────────╝
                      │
    ╔─────────────────┴──────────────────╗
    │                                    │
    ▼ Score >= auto_apply_threshold     ▼ Score >= fit_score_threshold < auto_apply
    │                                    │
┌─────────────────┐                 ┌──────────────────┐
│ Auto-Apply Mode │                 │ Send Approval    │
│ Trigger App Bot │                 │ Email to User    │
└────────┬────────┘                 └────────┬─────────┘
         │                                   │
         ▼                    ┌──────────────┴──────────────┐
  ┌─────────────────┐         ▼                            ▼
  │ Submit App      │    ┌────────────┐          ┌─────────────┐
  │ (Playwright)    │    │User Approves           User Skips   │
  └────────┬────────┘    └────────┬───┘          └─────────────┘
           │                      │
      ┌────┴────┐                ▼
      │          │         ┌──────────────┐
  Success?  Failure       │ Trigger App  │
      │          │         │ Bot          │
      ▼          ▼         └──────┬───────┘
  ┌────────┐ ┌──────────┐        │
  │Applied │ │Manual    │        │
  │Status  │ │Required  │        ▼
  └───┬────┘ └────┬─────┘   ┌──────────────┐
      │           │         │Submit App    │
      │           │         │(Playwright)  │
      └─────┬─────┴─────────└──────┬───────┘
            │                      │
      ┌─────┴──────┐          ┌────┴────┐
      │             │     Success? Failure
      ▼             ▼        │          │
  ┌─────────────────────┐    ▼          ▼
  │ Send Email:         │  ┌────────┐ ┌──────────┐
  │ - Auto Applied NotificationlFailed │ Manual   │
  │ - Confirmation     │  │Applied │ │Required  │
  │ - Digest           │  │Status  │ │Status    │
  └─────────────────────┘  └────────┘ └──────────┘
                                │          │
                                └────┬─────┘
                                     ▼
                          ╔═════════════════════╗
                          ║ Send Email Notif    ║
                          ║ Confirmation or     ║
                          ║ Manual Action Req'd ║
                          ╚═════════════════════╝
```

---

## 6. INFORMATION FLOW DIAGRAM

```
                      USER SETTINGS
                 (global_mode, thresholds,
                  target_roles, keywords)
                           │
                           ▼
    ┌────────────────────────────────────────────────┐
    │  SCRAPER (Phase 2)                             │
    │  GitHub, LinkedIn, Indeed, Glassdoor, etc.    │
    └────────────┬─────────────────────────────────┘
                 │
        Raw Job Listings
        {title, company, location, url}
                 │
                 ▼
    ┌────────────────────────────────────────────────┐
    │  DATABASE: Job Model (raw_jd, status='new')   │
    └────────────┬─────────────────────────────────┘
                 │
                 ├─→ JOB PARSER (Phase 3A)
                 │   Ollama LLM → ParsedJobData
                 │   {skills, salary, remote...}
                 │
                 ├─→ RESUME PARSER
                 │   Extract user skills, experience
                 │   ParsedResumeData
                 │
                 ▼
    ┌────────────────────────────────────────────────┐
    │  JOB MATCHER                                   │
    │  Weighted scoring algorithm                    │
    │  Output: match_score (0-100)                   │
    └────────────┬─────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │ Score vs Thresholds     │
    ▼                         ▼
APPLY EMAIL              NOTIFICATION EMAIL
(Approval request)       (Daily digest, skip)
    │                         │
    ├─→ User Approval         │
    │   Click Accept/Skip      │
    │                         │
    ▼                         ▼
APPLICATION BOT          USER INBOX
(Phase 3B)               (Phase 4)
Playwright automation
Form filling & submission
    │
    ├─ Success
    │ └─→ "Applied" Status
    │     Application Email
    │
    └─ Failure
      └─→ "Manual Needed" Status
          Action Required Email
```

---

## 7. SERVICE DEPENDENCIES & INTEGRATION MAP

```
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI ROUTER                             │
│  companies.py │ jobs.py │ applications.py │ settings.py         │
└────────┬──────────────────────┬─────────────────────┬───────────┘
         │                      │                     │
         ▼                      ▼                     ▼
    ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐
    │  Company    │    │  Job         │    │  UserSettings    │
    │  Seeding    │    │  Processing  │    │  Management      │
    └──────┬──────┘    └──────┬───────┘    └──────────────────┘
           │                  │
           │    ┌─────────────┼─────────────┐
           │    │             │             │
           ▼    ▼             ▼             ▼
    ┌────────────────────────────────────────────────────────────┐
    │                   SERVICES LAYER                            │
    │                                                            │
    │  ┌──────────┐  ┌────────────┐  ┌───────────────┐          │
    │  │ Scraper  │  │Job Parser  │  │Resume Parser  │          │
    │  │ (Phase2) │  │(Phase 3A)  │  │(Built-in)     │          │
    │  └────┬─────┘  └──────┬─────┘  └───────┬───────┘          │
    │       │               │               │                   │
    │       └───────────────┼───────────────┘                   │
    │                       │                                   │
    │                       ▼                                   │
    │              ┌──────────────────┐                         │
    │              │  JobMatcher      │                         │
    │              │  (Scoring logic) │                         │
    │              └────────┬─────────┘                         │
    │                       │                                   │
    │         ┌─────────────┴──────────────┐                   │
    │         │                            │                   │
    │         ▼                            ▼                   │
    │   ┌────────────────┐         ┌──────────────────┐        │
    │   │EmailService    │         │ ApplicationBot   │        │
    │   │(Phase 4)       │         │ (Phase 3B)      │        │
    │   └────────────────┘         └──────────────────┘        │
    │                                                            │
    │   [Other Services]:                                       │
    │   - CoverLetterGenerator - ResumeTailor - ...            │
    │                                                            │
    └────────────────────────────────────────────────────────────┘
           │                                          │
           ▼                                          ▼
    ┌────────────────────────────────────────────────────────────┐
    │                   EXTERNAL SERVICES                         │
    │                                                            │
    │  ┌──────────────┐  ┌──────────┐  ┌─────────────────┐    │
    │  │  PostgreSQL  │  │  Redis   │  │  Ollama (LLM)   │    │
    │  │  (Database)  │  │ (Cache)  │  │  (Parse/Score)  │    │
    │  └──────────────┘  └──────────┘  └─────────────────┘    │
    │                                                            │
    │  ┌──────────────────────────────────────────────────────┐ │
    │  │  Resend API (Email)  │  Playwright (Browser Auto)   │ │
    │  └──────────────────────────────────────────────────────┘ │
    │                                                            │
    └────────────────────────────────────────────────────────────┘
```

---

## 8. PHASE 5: WORKFLOW INTEGRATION - ORCHESTRATION REQUIREMENTS

Phase 5 needs to orchestrate all existing services into a complete workflow. Key responsibilities:

### 8.1 Workflow States
- **Idle**: Waiting for trigger (scheduled or manual)
- **Scraping**: Running job scraper for companies
- **Parsing**: Converting raw JDs to structured data
- **Matching**: Calculating fit scores
- **Decision**: Awaiting user approval or auto-applying
- **Applying**: Submitting applications via ApplicationBot
- **Notifying**: Sending emails
- **Completed**: Workflow cycle complete

### 8.2 Trigger Points
1. **Scheduled**: Every `scrape_interval_hours` (config: 6 hours)
2. **Manual**: Via API trigger
3. **Webhook**: From external job boards (future)
4. **User Action**: Approval click, settings change

### 8.3 Error Handling & Retry Logic
- Failed scrapes: Retry with backoff
- Parser errors: Log and mark for manual review
- Application failures: Trigger manual_needed status
- Email failures: Retry with exponential backoff

### 8.4 State Persistence
- Track workflow progress in database
- Store intermediate results
- Enable resume capability after crashes

### 8.5 Monitoring & Observability
- Log each step with timestamps
- Track success/failure rates
- Generate workflow metrics/reports
- Alert on anomalies

---

## 9. CONFIGURATION & ENVIRONMENT VARIABLES

**Location**: `.env` (with `.env.example` template)

### 9.1 Core Configuration
```properties
# App
APP_NAME=AutoApply
DEBUG=False
APP_BASE_URL=http://localhost:3000

# Database
DATABASE_URL=postgresql://autoapply:autoapply_dev_password@localhost:5432/autoapply_db

# Redis (for caching & task queue)
REDIS_URL=redis://localhost:6379

# Ollama (LLM service)
OLLAMA_API_URL=http://localhost:11434

# JWT (for approval tokens)
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=48

# Email (Resend API)
RESEND_API_KEY=re_xxxxx
EMAIL_FROM=noreply@autoapply.example.com

# Preferences
SCRAPE_INTERVAL_HOURS=6
FIT_SCORE_THRESHOLD=65
AUTO_APPLY_THRESHOLD=75
APPLICATION_MODE=approval  # or auto_apply
```

---

## 10. DEVELOPMENT & DEPLOYMENT

### 10.1 Local Development
```bash
# Full setup with Docker
docker-compose up -d

# Backend only
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend only
cd frontend
npm install
npm run dev
```

### 10.2 API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 11. SUMMARY TABLE

| Component | Type | Status | Key File |
|-----------|------|--------|----------|
| **Scraper** | Service | ✅ Complete | `services/scraper.py` |
| **Job Parser** | Service | ✅ Complete | `services/job_parser.py` |
| **Resume Parser** | Service | ✅ Complete | `services/resume_parser.py` |
| **Job Matcher** | Service | ✅ Complete | `services/job_matcher.py` |
| **Application Bot** | Service | ✅ Complete | `services/application_bot.py` |
| **Email Service** | Service | ✅ Complete | `services/email_service.py` |
| **Cover Letter Gen** | Service | ✅ Complete | `services/cover_letter_generator.py` |
| **Resume Tailor** | Service | ✅ Complete | `services/resume_tailor.py` |
| **Database** | Infrastructure | ✅ Complete | `models.py` (7 tables) |
| **API Endpoints** | Integration | ✅ Complete | `api/` (4 routers, 20+ endpoints) |
| **Background Tasks** | Queue | ⏳ Pending | `tasks/scrape_jobs.py` (TODO) |
| **Workflow Orchestration** | Phase 5 | ⏳ Pending | TBD |

---

**End of System Architecture Overview**
