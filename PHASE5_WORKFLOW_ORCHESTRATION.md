# Phase 5: Workflow Integration & Orchestration

## Overview

Phase 5 orchestrates all previous phases (Job Scraping, Parsing & Matching, Application Bot) into a unified, intelligent workflow that automatically processes jobs from discovery through application submission. This phase implements:

1. **Background Task System** - Distributed task processing for long-running operations
2. **Workflow Orchestrator** - Coordinates all phases with error handling and retries
3. **Scheduling Engine** - Periodic workflow execution based on user preferences
4. **Decision Logic** - Smart rules for auto-apply vs approval-required workflows
5. **Error Recovery** - Graceful handling of failures with logging and diagnostics

## Architecture

### Workflow Flow

```
User Setup (Initial)
  ↓
Periodic Scheduler Trigger (6h, 12h, daily, etc.)
  ↓
Phase 1: Scraping
  • JobScraper queries configured job boards
  • Deduplicates jobs based on URL + external ID
  • Stores raw jobs with status=NEW
  ↓
Phase 2: Parsing
  • JobParser processes raw job descriptions with LLM
  • Extracts: title, salary, skills, seniority, remote status, etc
  • Stores parsed_jd and parser_version
  ↓
Phase 3: Matching
  • JobMatcher calculates fit score vs user resume
  • Considers: skills match, experience level, salary range, preferences
  • Returns score 0-100
  ↓
Phase 4: Decision
  • Auto-Apply Mode: score >= threshold → auto-apply
  • Approval Mode: score >= threshold - 10 → send email request
  • Digest Mode: compile daily digest, no immediate action
  ↓
Phase 5: Application
  • ApplicationBot submits form via Playwright
  • Detects ATS platform (Greenhouse, Lever, Workday, etc)
  • Fills form fields intelligently
  • Captures screenshot for verification
  ↓
Phase 6: Notification
  • EmailService sends confirmation/failure email
  • Updates application record with status
  • Logs to EmailLog for audit trail
  ↓
User Reviews Results
  • Dashboard shows all applications
  • Metrics: auto-applied %, match scores, company stats
  • Can adjust settings and re-trigger workflow
```

### System Components

#### 1. Background Tasks (`backend/app/tasks/background_tasks.py`)

**scrape_jobs_task(company_ids, db)**
- Scrapes all active companies for new jobs
- Parameters:
  - `company_ids`: Optional list of specific company IDs
  - `db`: Database session
- Returns: `{status, jobs_found, companies_scraped, errors}`
- Error handling: Continues with next company on failure
- Idempotent: Deduplicates jobs before saving

**parse_job_task(job_id, db)**
- Parses single job using Ollama LLM
- Parameters:
  - `job_id`: Job to parse
  - `db`: Database session
- Returns: `{status, job_id, parsed_data_keys}`
- Stores `parsed_jd` JSONB blob with 23 structured fields
- Skips: Already parsed jobs (checks `parsed_jd` != null)

**match_job_task(job_id, user_id, db)**
- Calculates match score between job and resume
- Parameters:
  - `job_id`: Job to match
  - `user_id`: User ID
  - `db`: Database session
- Returns: `{status, job_id, match_score}`
- Uses 6-factor algorithm: skills, experience, salary, remote, industry, size
- Stores in Job.match_score (0-100)

**apply_job_task(job_id, user_id, db)**
- Applies to job using ApplicationBot
- Parameters:
  - `job_id`: Job to apply to
  - `user_id`: User who is applying
  - `db`: Database session
- Returns: `{status, success, ats_type, message}`
- Creates Application record
- Updates Job.status to APPLIED or MANUAL_NEEDED
- Captures screenshot for verification

**send_notification_task(notification_type, recipient_email, subject, data, db)**
- Sends email via Resend API
- Parameters:
  - `notification_type`: "approval_request", "application_confirmation", "daily_digest"
  - `recipient_email`: Recipient email
  - `subject`: Email subject
  - `data`: Template variables
  - `db`: Database session
- Returns: `{status, recipient, resend_id}`
- Logs all emails to EmailLog table

**execute_workflow_task(user_id, mode, auto_apply_threshold, db)**
- Orchestrates complete workflow: scrape → parse → match → decide → apply → notify
- Parameters:
  - `user_id`: User ID
  - `mode`: "auto_apply", "approval_required", or "digest"
  - `auto_apply_threshold`: Score threshold for auto-apply (0-100)
  - `db`: Database session
- Returns:
  ```json
  {
    "status": "completed" | "partial_failure" | "failed",
    "user_id": <int>,
    "started_at": <ISO timestamp>,
    "completed_at": <ISO timestamp>,
    "duration_seconds": <float>,
    "phases": {
      "scrape": {...},
      "parse": [...],
      "match": [...],
      "decide": [...],
      "apply": [...],
      "notify": [...]
    },
    "summary": {
      "total_jobs_processed": <int>,
      "jobs_scraped": <int>,
      "jobs_parsed": <int>,
      "jobs_matched": <int>,
      "auto_applied": <int>,
      "pending_approval": <int>,
      "manual_required": <int>,
      "errors": [...]
    }
  }
  ```

#### 2. Workflow Orchestrator (`backend/app/services/workflow_orchestrator.py`)

**WorkflowOrchestrator** - Main orchestration service

Methods:
- `async start()` - Start scheduler and setup schedules
- `async stop()` - Stop scheduler cleanly
- `async execute_workflow(user_id, mode, auto_apply_threshold)` - Execute workflow for single user
- `async execute_workflow_for_users(mode)` - Execute for all active users
- `async run_scraping_phase(company_ids)` - Run only scraping
- `async run_parsing_phase(job_ids)` - Run only parsing
- `async run_matching_phase(user_id, job_ids)` - Run only matching
- `async run_application_phase(user_id, job_ids)` - Run only applications
- `get_status()` - Get current orchestrator status
- `get_workflow_history(user_id)` - Get last workflow for user

Features:
- **Async/await**: Non-blocking background processing
- **APScheduler**: Cron-based job scheduling
- **Error Recovery**: Graceful error handling with retry capability
- **Workflow History**: Tracks execution results for audit trail
- **Per-User Scheduling**: Different intervals per user
- **Dynamic Scheduling**: Adjusts based on UserSettings

#### 3. Workflow API Endpoints (`backend/app/api/workflows.py`)

All endpoints are under `/workflows` prefix.

**POST /workflows/execute**
- Execute workflow for single user
- Query parameters:
  - `user_id` (required): User ID
  - `mode` (optional): "auto_apply", "approval_required", "digest"
  - `auto_apply_threshold` (optional): Score threshold (0-100)
- Returns: Complete workflow result
- Example:
  ```bash
  curl -X POST "http://localhost:8000/workflows/execute?user_id=123&mode=auto_apply&auto_apply_threshold=80"
  ```

**POST /workflows/execute-all**
- Execute workflow for all active users
- Query parameters:
  - `mode` (optional): Apply mode to all users
- Returns: Aggregated results with per-user details
- Example:
  ```bash
  curl -X POST "http://localhost:8000/workflows/execute-all?mode=approval_required"
  ```

**POST /workflows/scrape**
- Run only scraping phase
- Query parameters:
  - `company_ids` (optional): Specific companies to scrape
- Returns: Scraping results (jobs_found, companies_scraped, errors)
- Example:
  ```bash
  curl -X POST "http://localhost:8000/workflows/scrape?company_ids=1&company_ids=2"
  ```

**POST /workflows/parse**
- Run only parsing phase
- Query parameters:
  - `job_ids` (optional): Specific jobs to parse
- Returns: Parsing results (jobs_parsed, jobs_skipped, errors)
- Example:
  ```bash
  curl -X POST "http://localhost:8000/workflows/parse?job_ids=1&job_ids=2"
  ```

**POST /workflows/match**
- Run only matching phase
- Query parameters:
  - `user_id` (required): User ID
  - `job_ids` (optional): Specific jobs to match
- Returns: Matching results with top 5 matches
- Example:
  ```bash
  curl -X POST "http://localhost:8000/workflows/match?user_id=123"
  ```

**POST /workflows/apply/{job_id}**
- Apply to specific job immediately
- Path: `job_id`
- Query: `user_id` (required)
- Returns: Application result
- Example:
  ```bash
  curl -X POST "http://localhost:8000/workflows/apply/456?user_id=123"
  ```

**GET /workflows/status**
- Get orchestrator status
- Returns: `{status, scheduled_jobs, last_workflow_history}`
- Example:
  ```bash
  curl http://localhost:8000/workflows/status
  ```

**GET /workflows/history/{user_id}**
- Get last workflow for user
- Path: `user_id`
- Returns: Last execution result and timestamp
- Example:
  ```bash
  curl http://localhost:8000/workflows/history/123
  ```

**GET /workflows/jobs/pending/{user_id}**
- Get pending jobs at various workflow stages
- Path: `user_id`
- Query:
  - `status` (optional): Filter by status (NEW, PARSED, MATCHED, PENDING_APPROVAL, etc)
  - `limit` (optional, default 20): Max results (1-100)
  - `offset` (optional, default 0): Pagination offset
- Returns: `{total, limit, offset, jobs[]}`
- Example:
  ```bash
  curl "http://localhost:8000/workflows/jobs/pending/123?status=NEW&limit=50"
  ```

**POST /workflows/resume/update/{user_id}**
- Trigger re-matching after resume update
- Path: `user_id`
- Returns: `{status, jobs_rematched, top_new_matches[]}`
- Example:
  ```bash
  curl -X POST "http://localhost:8000/workflows/resume/update/123"
  ```

**GET /workflows/metrics**
- Get workflow metrics and statistics
- Query:
  - `user_id` (optional): Filter metrics for single user
- Returns:
  ```json
  {
    "total_jobs_scraped": <int>,
    "total_applications": <int>,
    "auto_applied_count": <int>,
    "manual_approved_count": <int>,
    "average_match_score": <float>,
    "scope": "single_user" | "all_users"
  }
  ```
- Example:
  ```bash
  curl "http://localhost:8000/workflows/metrics?user_id=123"
  ```

## Use Cases

### Use Case 1: Initial Setup (Auto-Apply Mode)

```bash
# User sets up with auto-apply threshold of 75
# User adds target companies to database
# Trigger one-time workflow execution

curl -X POST "http://localhost:8000/workflows/execute?user_id=123&mode=auto_apply&auto_apply_threshold=75"

# Response:
{
  "status": "completed",
  "summary": {
    "jobs_scraped": 45,
    "jobs_parsed": 38,
    "jobs_matched": 32,
    "auto_applied": 8,
    "pending_approval": 11,
    "manual_required": 5
  }
}

# 8 jobs were auto-applied immediately
# 11 jobs sent approval emails (user can approve from email)
# 5 jobs failed (manual intervention needed)
# Backend automatically sent confirmation emails for successful applications
```

### Use Case 2: Scheduled Workflow (Approval-Required Mode)

```bash
# User settings:
# - scrape_interval_hours: 6
# - workflow_mode: "approval_required"
# - auto_apply_threshold: 75

# Orchestrator automatically runs every 6 hours (via APScheduler)

# Workflow execution:
# 1. Scrapes: 10 new jobs found
# 2. Parses: All 10 jobs parsed successfully
# 3. Matches: 
#    - 3 jobs scored 82-90 (high match)
#    - 5 jobs scored 65-74 (medium match)
#    - 2 jobs scored <65 (low match)
# 4. Decision:
#    - High match (≥75): Email approval request (3 jobs)
#    - Medium match (65-74): Email approval request (5 jobs)
#    - Low match (<65): Skip (2 jobs)
# 5. Notification: 8 approval emails sent

# User receives email with job details and approve/skip links

# User clicks "Approve" link in email
# Backend:
# 1. Verifies approval token (48-hour expiration)
# 2. Triggers application_bot for that job
# 3. Sends confirmation email with result

# Result: Job application submitted, confirmation sent
```

### Use Case 3: Manual Override - Re-Scrape Company

```bash
# User finds new tech company to target
# Adds company to database
# Manually triggers scrape for that company

curl -X POST "http://localhost:8000/workflows/scrape?company_ids=789"

# Response:
{
  "status": "completed",
  "jobs_found": 23,
  "companies_scraped": 1,
  "errors": []
}

# Next scheduled workflow will parse and match these 23 jobs
# Or user can manually trigger parse phase:

curl -X POST "http://localhost:8000/workflows/parse"

# This parses all unparsed (NEW status) jobs
```

### Use Case 4: Post-Resume Update

```bash
# User updates their resume with new skills
# Uploads new resume to system
# Wants to re-match old jobs against new resume

curl -X POST "http://localhost:8000/workflows/resume/update/123"

# Response:
{
  "status": "completed",
  "jobs_rematched": 127,
  "top_new_matches": [
    {"job_id": "abc123", "score": 92},
    {"job_id": "def456", "score": 88},
    {"job_id": "ghi789", "score": 87}
  ]
}

# Old jobs that didn't match before might now match better
# User can review and approve applications for newly matched jobs
```

### Use Case 5: Check Workflow Status

```bash
# User wants to see system status

curl http://localhost:8000/workflows/status

# Response:
{
  "status": "running",
  "scheduled_jobs": 3,
  "last_workflow_history": {
    "user_123": {
      "result": {...},
      "executed_at": "2026-04-11T14:30:00"
    },
    "user_456": {
      "result": {...},
      "executed_at": "2026-04-11T14:25:00"
    }
  }
}

# Get metrics for all users
curl http://localhost:8000/workflows/metrics

# Response:
{
  "total_jobs_scraped": 1247,
  "total_applications": 342,
  "auto_applied_count": 156,
  "manual_approved_count": 186,
  "average_match_score": 71.3,
  "scope": "all_users"
}
```

## Database Schema Changes

### New Models

**User** model (new)
```python
- id: UUID (primary key)
- email: String (unique)
- name: String
- is_active: Boolean
- created_at: DateTime
- updated_at: DateTime
```

### Modified Models

**Company**
- Added: `user_id` (foreign key to User)
- Added: `search_query` (for scraper)
- Added: `is_active` (Boolean)

**Job**
- Added: `user_id` (foreign key to User)
- Added: `external_url` (URL from job board)
- Added: `match_details` (JSONB with breakdown)

**Application**
- Added: `user_id` (foreign key to User)
- Added: `resume_id` (foreign key to Resume)

**Resume**
- Added: `user_id` (foreign key to User)
- Added: `parsed_resume` (JSONB with normalized data)

**UserSettings**
- Added: `user_id` (foreign key)
- Added: `workflow_mode` (auto_apply, approval_required, digest)

**EmailLog**
- Added: `user_id` (foreign key)
- Changed: `deliver_status` → `delivery_status`

## Configuration

### UserSettings Defaults

```python
auto_apply_threshold = 75  # Apply if match score >= 75
fit_score_threshold = 65   # Send approval email if >= 65
scrape_interval_hours = 6  # Run workflow every 6 hours
workflow_mode = "approval_required"  # Default mode
```

### Workflow Mode Behaviors

| Mode | Behavior |
|------|----------|
| `auto_apply` | score >= threshold → auto-apply; no email approval |
| `approval_required` | score >= (threshold - 10) → send email; user clicks to apply |
| `digest` | Daily digest email at 8 AM; no immediate action |

### Job Status Transitions

```
NEW → PARSED → MATCHED → PENDING_APPROVAL
                ├→ APPLYING → APPLIED
                └→ SKIPPED
                ├→ MANUAL_NEEDED
                └→ FAILED
```

## Error Handling & Recovery

### Retry Strategy

- **Task Failures**: Logged but don't stop workflow (continues with next jobs)
- **Database Errors**: Rolled back, task marked failed
- **Network Errors**: Logged, job marked as MANUAL_NEEDED (user can retry)
- **Unknown Errors**: Caught, logged to database, dashboard alerts

### Error Scenarios

1. **Scraper fails for company**
   - Logged in error list
   - Other companies continue
   - User notified in summary

2. **LLM parser fails**
   - Job marked as PARSED with error
   - Remains available for manual review
   - Task can be retried

3. **Job matching fails**
   - Specific job marked with error
   - Other jobs continue
   - Job marked as MANUAL_NEEDED

4. **Application bot fails**
   - Captured error and ATS type
   - Job marked as MANUAL_NEEDED
   - Screenshot saved for diagnosis
   - User notified to apply manually

5. **Email send fails**
   - Logged to EmailLog with error
   - Can be retried via API

## Performance Characteristics

### Typical Execution Times

| Phase | Time | Notes |
|-------|------|-------|
| Scraping | 30-60s | Depends on job board responsiveness |
| Parsing (10 jobs) | 15-30s | LLM processing uses Ollama |
| Matching (10 jobs) | 2-5s | Local algorithm |
| Application (1 job) | 10-20s | Depends on form complexity |
| Full workflow (50 jobs) | 3-5 min | Varies by ATS complexity |

### Concurrency

- **Single-user workflow**: Sequential (one job at a time)
- **Multi-user workflows**: APScheduler runs in parallel for different users
- **Bottleneck**: Database connections (configured via pool)

## Monitoring & Debugging

### Logging

```python
# All tasks log to app.log with structured format:
# [timestamp] [level] [phase] [job_id/user_id] message
# Example:
# 2026-04-11 14:30:00 INFO scrape user_123 Scraped 10 new jobs
# 2026-04-11 14:31:15 ERROR parse job_456 LLM parsing failed: timeout
# 2026-04-11 14:31:16 WARN apply job_456 Manual action required: CAPTCHA
```

### Database Audit Trail

- **EmailLog**: All emails sent (with status, open rate)
- **Application**: All applications (with method, screenshot, notes)
- **Job**: Status transitions with timestamps

### API Debugging

```bash
# Get full workflow history
curl http://localhost:8000/workflows/history/123 | jq '.result.phases'

# Get all jobs in MANUAL_NEEDED status
curl "http://localhost:8000/workflows/jobs/pending/123?status=MANUAL_NEEDED"

# Check for failures
curl http://localhost:8000/workflows/history/123 | jq '.result.summary.errors'
```

## Limitations & Future Enhancements

### Current Limitations

1. **No Resume Tailoring**: Sends generic resume
   - Future: Auto-tailor resume for each job
2. **No Cover Letter**: Doesn't generate custom cover letters
   - Future: LLM-based cover letter generation
3. **Limited Company Intel**: Basic company detection
   - Future: Glassdoor/Blind integration for ratings
4. **No Interview Prep**: No tracking of interview process
   - Future: Interview scheduling and prep materials

### Future Enhancements

1. **Phase 6**: Add interview tracking and prep
2. **Phase 7**: Analytics dashboard with success metrics
3. **Phase 8**: Integration with calendar (automate interview scheduling)
4. **Advanced Matching**: Machine learning model instead of rule-based
5. **Multi-app Support**: Support for other job boards

## Testing Phase 5

### Unit Tests

```python
# Test individual tasks
async def test_parse_job_task():
    result = await parse_job_task(job_id=1)
    assert result["status"] == "completed"
    assert "parsed_data_keys" in result

async def test_match_job_task():
    result = await match_job_task(job_id=1, user_id=1)
    assert 0 <= result["match_score"] <= 100

async def test_execute_workflow():
    result = await execute_workflow_task(user_id=1, mode="auto_apply")
    assert result["status"] in ["completed", "partial_failure"]
    assert "summary" in result
```

### Integration Tests

```bash
# Full workflow with test data
curl -X POST "http://localhost:8000/workflows/execute?user_id=1&mode=auto_apply"

# Verify at each stage
curl "http://localhost:8000/workflows/jobs/pending/1?status=PARSED"
curl "http://localhost:8000/workflows/jobs/pending/1?status=APPLIED"
curl "http://localhost:8000/workflows/metrics?user_id=1"
```

### Manual Testing Checklist

- [ ] Scraper finds jobs
- [ ] Parser extracts job details
- [ ] Matcher calculates scores
- [ ] Decision dispatches correctly (auto vs approval)
- [ ] Auto-apply submissions succeed
- [ ] Approval emails send with valid tokens
- [ ] Application confirmations send
- [ ] Metrics update correctly
- [ ] Error jobs marked MANUAL_NEEDED
- [ ] History tracks all executions

## Conclusion

Phase 5 completes the AutoApply automation system by orchestrating all individual components into a cohesive, intelligent workflow. Users can now set it and forget it - the system automatically processes jobs from discovery to application submission with minimal manual intervention.

The modular design allows each phase to be tested, debugged, and improved independently while maintaining data integrity through the entire pipeline.
