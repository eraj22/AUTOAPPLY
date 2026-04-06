# Phase 3 Application Bot - Technical Analysis & Architecture

**Document Date**: April 6, 2026  
**Purpose**: Comprehensive codebase review for Phase 3 (Application Bot) planning

---

## 1. JOB PARSER SERVICE (`backend/app/services/job_parser.py`)

### Primary Function
`async parse_job_description(job_title, job_description, company_name)` → `ParsedJobData`

**Details**:
- **Lines**: 280+ lines
- **Pattern**: Async singleton pattern
- **Method**: Calls Ollama LLM with XML-formatted prompt
- **Parsing Strategy**: 
  - Builds structured prompt requesting JSON extraction only
  - Calls Ollama API endpoint: `POST /api/generate`
  - Extracts JSON from response (handles markdown code blocks)
  - Validates with Pydantic model
  - Caps confidence_score at 0.95 to indicate uncertainty

### ParsedJobData Model - Complete Fields

```python
class ParsedJobData(BaseModel):
    # Core qualifications
    required_skills: List[str]              # Must-have technologies
    nice_to_have_skills: List[str]          # Optional technologies
    
    # Experience level
    seniority_level: str                    # junior|mid|senior|lead|executive
    experience_required_years: Optional[int] # Years needed
    
    # Compensation
    salary_min: Optional[int]               # USD minimum
    salary_max: Optional[int]               # USD maximum
    salary_currency: str                    # Default "USD"
    
    # Work arrangements
    remote_type: str                        # fully_remote|hybrid|onsite
    location: Optional[str]                 # City, Country or "Remote"
    travel_required: Optional[int]          # % travel 0-100
    
    # Company context
    company_size: Optional[str]             # 1-50|51-200|201-1000|1001-5000|5000+
    industry: Optional[str]                 # SaaS|FinTech|Healthcare|etc
    company_stage: Optional[str]            # Pre-seed|Seed|Series A/B/C|Growth|Public
    
    # Technical stack
    tech_stack: List[str]                   # Technologies/frameworks used
    role_type: str                          # Full-time|Part-time|Contract|Freelance
    
    # Interview & logistics
    estimated_interview_rounds: Optional[int] # Interview stages expected
    education_required: Optional[str]       # Bachelor's|Master's|PhD|Bootcamp
    visa_sponsorship: Optional[bool]        # Company sponsorship available?
    
    # Role context
    title_aliases: List[str]                # Similar role titles
    responsibilities: List[str]             # Key responsibilities
    benefits: List[str]                     # Health, 401k, stock, etc
    growth_opportunities: List[str]         # Career growth areas
    
    # Quality metric
    confidence_score: float                 # 0.0-1.0 parser confidence
```

### Ollama Integration Details
- **URL**: From `settings.ollama_api_url` (configurable)
- **Model**: `tinyllama` (default, configurable)
- **Timeout**: 60 seconds per request
- **Temperature**: 0.3 (low for consistency)
- **Stream**: False (wait for complete response)

### Confidence Scoring
- Starts with value from LLM response
- Capped at 0.95 maximum
- Lower confidence (< 0.7) for estimated/interpolated values
- Zero confidence on complete parse failure

### Error Handling
- Returns `ParsedJobData(confidence_score=0.0)` on JSON decode error
- Handles empty/short job descriptions
- Logs connection failures, timeouts separately
- Batch parsing available: `async parse_batch(jobs: List[Dict])`

**Key Limitation**: No fallback parser if Ollama unavailable

---

## 2. JOB MATCHER SERVICE (`backend/app/services/job_matcher.py`)

### Core Algorithm: `calculate_match()`
Computes weighted multi-factor match between job and resume (0-100 score)

### Matching Weights (Sum = 100%)
```
SKILL_WEIGHT        = 0.35  (35%) ← Most important
SENIORITY_WEIGHT    = 0.20  (20%)
SALARY_WEIGHT       = 0.20  (20%)
REMOTE_WEIGHT       = 0.10  (10%)
INDUSTRY_WEIGHT     = 0.10  (10%)
COMPANY_SIZE_WEIGHT = 0.05  (5%)
```

### JobMatchResult Model - Complete Fields

```python
class JobMatchResult(BaseModel):
    # Identifiers
    job_id: Optional[str]                # Unique job ID reference
    job_title: str                       # Job posting title
    company_name: Optional[str]          # Hiring company
    
    # Main score (0-100 weighted average)
    match_score: int                     # Overall match 0-100
    
    # Component scores (each 0-100)
    skill_match_score: int               # Required/nice skills coverage
    seniority_match_score: int           # Experience level alignment
    salary_match_score: int              # Compensation adequacy
    remote_match_score: int              # Work arrangement fit
    
    # Skill analysis
    missing_skills: List[str]            # Required skills user lacks
    skill_gaps: List[str]                # Nice-to-have skills missing
    positive_matches: List[str]          # Reasons it's a good fit
    concerns: List[str]                  # Red flags/mismatches
    
    # Financial analysis
    salary_gap: int                      # $ below user minimum (if below)
    
    # Detailed breakdown
    reason_breakdown: List[MatchReason]  # Weighted factor explanations
    recommendation: str                  # Human-readable guidance
    
    # Example recommendations:
    # "🎯 Excellent match! Highly recommended to apply" (85+)
    # "✓ Good match, worth considering" (70-84)
    # "~ Moderate match, apply if interested" (50-69)
    # "⚠ Weak match, review carefully" (<50)
```

### Scoring Algorithms

**Skill Match (0-100)**:
- Required skill intersection: `matched_required / total_required * 100`
- Bonus for nice-to-have: +10% max if all nice-to-have matched
- Result capped at 100%

**Seniority Match (0-100)**:
- Perfect level match: 100 points
- One level off: 80 points
- Two+ levels overqualified: 60 points
- Two+ levels underqualified: 50 points
- Hierarchy: junior(1) < mid(2) < senior(3) < lead(4) < executive(5)

**Salary Match (0-100)**:
- No salary info: 75 (neutral)
- Job ≥ user minimum: 100 points
- Job < user minimum: `100 - ((gap / user_min) * 100)` (0-100)
- Gap percentage directly reduces score

**Remote Work Match (0-100)**:
- Perfect match: 100 (fully_remote→fully_remote, etc)
- Partial match (any remote combo): 85 points
- Onsite vs remote: 50 points (poor fit)

**Industry Match (0-100)**:
- No preference specified: 75 (neutral)
- Exact match: 100 points
- Partial keyword match: 70 points
- No match: 50 points

**Company Size Match (0-100)**:
- Size in preferred list: 100 points
- Size unknown: 75 (neutral)
- Size not preferred: 60 points

### Final Score Calculation
```
overall_score = (
    skill_score * 0.35 +
    seniority_score * 0.20 +
    salary_score * 0.20 +
    remote_score * 0.10 +
    industry_score * 0.10 +
    company_size_score * 0.05
)
result.match_score = round(overall_score)  # 0-100 integer
```

### MatchReason Structure
```python
class MatchReason(BaseModel):
    category: str          # "skill", "salary", "remote", "seniority", "industry"
    match_type: str        # "positive" or "negative"
    message: str           # Human readable explanation
    weight: float          # Factor weight (e.g., 0.35 for skill)
```

### Key Design Notes
- **No database queries** - Matches calculated from parsed data in memory
- **Deterministic** - Same inputs always produce same output
- **Detailed justification** - Reasons provided for every component score
- **Singleton pattern** - `get_job_matcher()` returns shared instance

---

## 3. RESUME PARSER SERVICE (`backend/app/services/resume_parser.py`)

### Primary Function
`async parse_resume(resume_text)` → `ParsedResumeData`

**Details**:
- **Lines**: 260+ lines
- **Pattern**: Async singleton pattern
- **Method**: Calls Ollama LLM to extract structured resume data
- **Parsing Strategy**: Similar to job parser - JSON extraction via LLM

### ParsedResumeData Model - Complete Fields

```python
class ParsedResumeData(BaseModel):
    # Personal information
    full_name: Optional[str]                # Candidate name
    email: Optional[str]                    # Contact email
    phone: Optional[str]                    # Contact phone
    location: Optional[str]                 # Current location
    
    # Skills inventory
    all_skills: List[str]                   # All mentioned skills
    technical_skills: List[str]             # Tech stack only
    soft_skills: List[str]                  # Communication, leadership, etc
    
    # Experience level
    seniority_level: str                    # junior|mid|senior|lead|executive
    years_of_experience: int                # Total professional years
    years_in_current_role: Optional[int]    # Current position tenure
    
    # Current employment
    current_title: Optional[str]            # Current job title
    current_company: Optional[str]          # Current employer
    
    # Career history
    past_companies: List[str]               # Previous employers
    past_titles: List[str]                  # Previous job titles
    
    # Education
    education_level: Optional[str]          # Bachelor's|Master's|PhD|Bootcamp
    university: Optional[str]               # School name
    degree_field: Optional[str]             # Major/specialization
    certifications: List[str]               # AWS, GCP, Azure, etc
    
    # Technical focus
    primary_focus_area: Optional[str]       # Backend|Frontend|Full-Stack|DevOps
    secondary_focus_areas: List[str]        # Additional specialties
    tech_stack: List[str]                   # Professional technologies
    
    # Achievement tracking
    key_achievements: List[str]             # Notable accomplishments
    
    # Online presence
    github_url: Optional[str]               # GitHub profile
    linkedin_url: Optional[str]             # LinkedIn profile
    portfolio_url: Optional[str]            # Personal website
    
    # Career status
    open_to_opportunities: bool             # Currently job hunting?
    
    # Embedded user preferences
    preferences: UserPreferences            # Salary, remote, industry targets
    
    # Quality metric
    confidence_score: float                 # 0.0-1.0 parser confidence
```

### UserPreferences Nested Model

```python
class UserPreferences(BaseModel):
    min_salary: Optional[int]               # Minimum acceptable salary USD
    max_salary: Optional[int]               # Maximum acceptable salary USD
    preferred_remote_type: str              # fully_remote|hybrid|onsite (default: hybrid)
    desired_industries: List[str]           # [SaaS, FinTech, Healthcare, ...]
    desired_company_sizes: List[str]        # [51-200, 201-1000] (defaults provided)
    willing_to_travel: int                  # 0-100% travel tolerance
    open_to_contract: bool                  # Contract/freelance roles?
    visa_sponsorship_needed: bool           # Need visa support?
    relocation_willing: bool                # Open to moving?
    desired_locations: List[str]            # Preferred cities/countries
```

### Ollama Integration
- Same as job parser: async call with temperature=0.3
- Prompt instructs extraction of personal info, skills, preferences
- Returns zero confidence on parse failure

### Confidence Scoring
- Capped at 0.95 like job parser
- Lower when person fields missing (name, email)
- Lower when skills sparse or vague

### Key Limitation
- **Preference extraction is AI-guessed** - Not from explicit user input
- Confidence score should guide usage of preference fields

---

## 4. APPLICATION MODEL (`backend/app/models.py`)

### Application Table Schema

```python
class Application(Base):
    __tablename__ = "applications"
    
    # Primary key
    id: UUID                        # Unique application UUID
    
    # Foreign key
    job_id: UUID                    # Link to Job record (FK)
    
    # Submission details
    resume_path: Optional[str]      # Path to resume PDF sent (if any)
    cover_letter: Optional[str]     # Cover letter text (if custom generated)
    submitted_at: Optional[DateTime] # When application submitted to job board
    method: Optional[str]           # "auto"|"manual"|"approved" (how it happened)
    
    # Automation tracking
    screenshot_path: Optional[str]  # Screenshot of filled form/confirmation
    notes: Optional[str]            # Any notes from submission process
    
    # Timestamps
    created_at: DateTime            # Record creation time
    updated_at: DateTime            # Last modification time
```

### No Application Statuses Table
- **Note**: Applications don't have their own status column
- **Status lives on Job model** via `Job.status` field (not here)
- Application record existence indicates "applied"

### Job Status Enum (for context)

```python
class JobStatus(str, enum.Enum):
    NEW = "new"                     # Just discovered
    PENDING_APPROVAL = "pending_approval"  # Awaiting user approval
    APPLYING = "applying"           # Currently submitting form
    APPLIED = "applied"             # Successfully applied (Application record created)
    SKIPPED = "skipped"             # User rejected
    FAILED = "failed"               # Submission failed
    MANUAL_NEEDED = "manual_needed" # Form too complex for bot
    WITHDRAWN = "withdrawn"         # User withdrew application
```

### Form Tracking Fields
- **screenshot_path**: Stores path to form confirmation screenshot
- **notes**: Custom notes about form submission (errors, prompts encountered)
- **method**: Differentiates automated vs manual submissions

### Table Relationship
```
Job (1)─── has many ──→ Application (N)
  ↓
Each Application tracks ONE job application instance
Status managed on Job, not Application
```

---

## 5. APPLICATION ENDPOINTS (`backend/app/api/applications.py`)

### Available Endpoints

#### GET /applications
- **Purpose**: List all applications
- **Response**: `List[ApplicationResponse]`
- **Order**: By `created_at DESC` (newest first)
- **Filtering**: None built-in (could add by status, job_id)

#### GET /applications/{application_id}
- **Purpose**: Get single application details
- **Response**: `ApplicationResponse`
- **Error**: 404 if not found

#### POST /applications/apply/{job_id}
- **Purpose**: Submit application to a job
- **Behavior**:
  1. Checks job exists (404 if not)
  2. Checks not already applied (400 if Application exists)
  3. Gets current resume from database
  4. Creates new Application record with:
     - `method="auto"` (hardcoded)
     - `submitted_at=datetime.utcnow()`
     - `notes="Applied at [ISO timestamp]"`
  5. Updates Job status to "applied"
  6. Returns success response with application_id

- **Response**:
  ```json
  {
    "status": "success",
    "message": "Successfully applied to {job_title}",
    "application_id": "uuid",
    "applied_at": "2024-01-15T10:30:00"
  }
  ```

#### DELETE /applications/{application_id}
- **Purpose**: Withdraw an application
- **Behavior**:
  1. Gets application record
  2. Deletes from database
  3. Resets parent Job status to "new"
  4. Returns success response

#### GET /applications/stats/summary
- **Purpose**: Application statistics dashboard
- **Returns**:
  ```json
  {
    "total_applications": 42,
    "applied_by_method": {
      "auto": 30,
      "manual": 8,
      "approved": 4
    },
    "applied_jobs": 42  // Count of jobs with status="applied"
  }
  ```

### No Auto-Apply Submission Logic
- **⚠️ CRITICAL GAP**: No form-filling mechanism implemented
- **Current State**: POST endpoint only records application in DB
- **Missing**: Actual browser automation to fill and submit forms

### ApplicationResponse Schema

```python
class ApplicationResponse(BaseModel):
    id: UUID
    job_id: UUID
    resume_path: Optional[str]
    cover_letter: Optional[str]
    submitted_at: Optional[DateTime]
    method: Optional[str]          # Would be "auto"
    screenshot_path: Optional[str]
    notes: Optional[str]
    created_at: DateTime
    updated_at: DateTime
```

---

## 6. FORM & BROWSER AUTOMATION Analysis

### Current Scraper.py Status
- **Implemented**: Multi-site scraping (GitHub, Greenhouse, Indeed, Glassdoor)
- **Technology**: Playwright async browser automation
- **No Form Filling**: Zero form submission code detected

### What EXISTS (Scraping):
```python
class JobScraper:
    async scrape_github_jobs(search_query)      # GitHub Jobs board
    async scrape_greenhouse_jobs(careers_url)   # Greenhouse ATS
    async scrape_indeed_jobs(search_query, location)  # Indeed.com
    async scrape_glassdoor_jobs(search_query, location) # Glassdoor
```

### Scraping Techniques Present:
- **Page navigation**: `await page.goto(url, wait_until="networkidle")`
- **Element waiting**: `await page.wait_for_selector()`
- **Text extraction**: `await element.text_content()`
- **Attribute reading**: `await element.get_attribute("href")`
- **Element queries**: `await page.query_selector_all()` (multiple)

### CSS Selectors Used (Scraping Only):
```
GitHub Jobs:    div.job-listing-result, a.result-title, .result-location
Greenhouse:     [class*='job-opening'], [class*='opening'], [data-test-selector='job-title']
Indeed:         div.job_seen_beacon, h2.jobTitle span, span.companyName, div.companyLocation
Glassdoor:      (code incomplete, returns before full selector list)
```

### MISSING - No Form Submission Code
- No `await page.fill()` for text input
- No `await element.click()` for buttons
- No `await page.select_option()` for dropdowns
- No screenshot capture code
- No form validation/error handling
- No ATS-specific form logic

### Playwright Available But Unused for Forms:
```python
# Available but not used:
page.fill(selector, value)        # Type text into inputs
page.click(selector)              # Click buttons
page.select_option(selector, value)  # Select dropdown
page.check(selector)              # Check checkbox
page.upload_file(selector, file)  # File upload
page.take_screenshot(path)        # Screenshot
page.wait_for_navigation()        # Wait for page load
```

---

## 7. DATABASE INTEGRATION Summary

### Job Model - Scoring Fields
```python
class Job(Base):
    match_score: Optional[int]      # 0-100 match to resume (populated by matcher)
    fit_score: Optional[int]        # 0-100 overall fit (not yet used)
    parsed_jd: Optional[JSONB]      # Stores ParsedJobData as JSON
    parser_version: Optional[str]   # Tracks parser version used
    parsed_at: Optional[DateTime]   # When job was parsed
```

### Existing Service Singletons
```python
def get_job_parser() -> JobParser      # backend/app/services/job_parser.py
def get_job_matcher() -> JobMatcher    # backend/app/services/job_matcher.py
def get_resume_parser() -> ResumeParser # backend/app/services/resume_parser.py
```

### Missing: Status Transitions in DB
- Application endpoints create records but don't fully track process
- No record of "APPLYING" state during form submission
- No error state capture in database

---

## 8. EMAIL SERVICE Integration (Context)

### Email Types (for application bot workflow)
```python
class EmailType(str, enum.Enum):
    APPROVAL_NEEDED = "approval_needed"              # Phase 3B
    AUTO_APPLIED = "auto_applied"                    # Phase 3C
    APPLICATION_CONFIRMED = "application_confirmed" # After submission
    MANUAL_REQUIRED = "manual_required"              # Complex forms
    DAILY_DIGEST = "daily_digest"                    # Summary
```

### Available Email Functions (ready to use)
```python
from app.services.email_service import (
    send_approval_email,
    send_auto_applied_email,
    send_application_confirmed_email,
    send_manual_required_email,
    send_daily_digest_email
)
```

---

## 9. CONFIDENCE SCORES & Quality Metrics

### Parser Confidence Bands
```
0.0-0.3:  Very Low   - Parse failure, missing core fields
0.3-0.6:  Low        - Partial parse, estimated values
0.6-0.8:  Medium     - Good parse, some fields inferred
0.8-0.95: High       - Complete parse, all fields extracted
0.95:     Max        - Capped ceiling (marked as uncertain)
```

### Score Interpretation Notes
- **Resume confidence** often higher than job confidence
- **Resume**: Full text available, can extract comprehensively
- **Job posting**: Often marketing copy, skills implicit
- Confidence < 0.7 should trigger manual review for match decisions

---

## 10. PHASE 3 APPLICATION BOT - Implementation Gaps

### ✅ Already Implemented (Phase 3A)
1. ✅ Job parsing (Ollama LLM)
2. ✅ Resume parsing (Ollama LLM)
3. ✅ Match scoring (multi-factor algorithm)
4. ✅ Database models & endpoints
5. ✅ Email notification framework

### ❌ NOT Implemented Yet (Phase 3B/C)
1. ❌ **Form Filling Logic** - Browser automation for job board forms
2. ❌ **ATS Detection** - Identify which ATS (Greenhouse, Lever, Workday, etc)
3. ❌ **Form Field Mapping** - Map resume fields to form inputs
4. ❌ **File Upload Handling** - Upload PDF resume to forms
5. ❌ **Multi-step Forms** - Handle paginated application flows
6. ❌ **Error Recovery** - Handle form validation errors, retries
7. ❌ **Approval Workflow** - User approval before auto-apply
8. ❌ **Status Tracking** - Track application submission status in DB
9. ❌ **Confirmation Detection** - Parse success/failure messages
10. ❌ **Fallback to Manual** - Trigger manual review on complex forms

### Existing Infrastructure Ready for Phase 3B
- Playwright browser is initialized
- Async patterns established
- Database ready for status tracking
- Email notifications ready
- API endpoints ready for submission endpoints
- Parser confidence scores can filter candidates

---

## 11. Recommended Phase 3B Architecture

### Form Submission Service (TO BUILD)
```python
# backend/app/services/form_submitter.py

class FormSubmitter:
    async def detect_ats(url: str) -> str           # Identify platform
    async def fill_form(page, form_data, template)  # Fill by ATS type
    async def submit_form(page) -> SubmissionResult # Submit & capture
    async def apply_to_job(job, resume_parsed) -> ApplicationRecord
    
    # Per-ATS implementations:
    async def _fill_greenhouse_form(page, data)
    async def _fill_lever_form(page, data)
    async def _fill_workday_form(page, data)
    async def _fill_ashby_form(page, data)
    async def _fill_generic_form(page, data)
```

### New Application State Tracking
```python
class ApplicationState(str, enum.Enum):
    PENDING = "pending"             # Awaiting approval
    APPROVED = "approved"           # User approved
    SUBMITTING = "submitting"       # Actively filling form
    SUBMITTED = "submitted"         # Form POST sent
    CONFIRMED = "confirmed"         # Success message parsed
    FAILED = "failed"               # Submission error
    MANUAL = "manual"               # Needs human review
```

### New Endpoint Needed
```python
POST /applications/auto-apply/{application_id}
# Triggers form submission for approved application
```

---

## 12. Data Flow Diagram

```
User Resume (PDF/Text)
         ↓
    Resume Parser (Ollama)
         ↓
    ParsedResumeData (cached in memory)
         ↓
    Job Listings (scraped)
         ↓
    Job Parser (Ollama)
         ↓
    ParsedJobData (stored in Job.parsed_jd)
         ↓
    Job Matcher (in-memory calculation)
         ↓
    JobMatchResult (0-100 score + breakdown)
         ↓
    Match Filter (user thresholds)
         ↓
    Strong Matches → Approval Email → User Accepts
         ↓
    [PHASE 3B] Form Submitter (NOT YET IMPLEMENTED)
         ↓
    Application Created in DB
         ↓
    Confirmation Email
```

---

## Summary Table

| Component | Status | Implementation | Gaps |
|-----------|--------|-----------------|------|
| **Job Parser** | ✅ Complete | Ollama LLM, 25+ fields | Fallback parser needed |
| **Resume Parser** | ✅ Complete | Ollama LLM, 20+ fields | Preferences are guessed |
| **Job Matcher** | ✅ Complete | 6-factor weighted | No learning/adjustment |
| **Application Model** | ⚠️ Partial | DB table exists | No status tracking on table |
| **API Endpoints** | ⚠️ Partial | CRUD only | No form submission endpoint |
| **Scraper** | ✅ Complete | Playwright, 4 sites | No form filling |
| **Email Service** | ✅ Ready | Framework ready | Not integrated to flow |
| **Form Submission** | ❌ Missing | Zero code | Entire subsystem needed |

---

## Next Steps for Phase 3B

1. **ATS Detection Module**: Identify form platform from URL/HTML
2. **Form Field Mapping**: Create CSS selector registry per ATS
3. **Form Filler Service**: Async form filling with Playwright
4. **Status Updater**: Track submission progress in database
5. **Error Handler**: Validation error detection & recovery
6. **Manual Fallback**: Route complex forms to manual queue
7. **Test Coverage**: Unit tests for each ATS form type

---

**End of Analysis**  
*For Phase 3B planning, prioritize building the FormSubmitter service and ATS detection logic.*
