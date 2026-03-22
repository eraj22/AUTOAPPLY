# Phase 3A Local Testing & Deployment Guide

## Prerequisites

### 1. Start Docker Desktop
On Windows: 
- Open Windows Start Menu
- Search for "Docker Desktop"
- Click to launch
- Wait for it to say "Docker is running" in the system tray

⏳ **Takes ~30 seconds**

### 2. Verify Docker is Running
```powershell
docker ps
```
Should show container list (not error about daemon not running)

## Step 1: Start the Stack

```powershell
cd "C:/Users/Sher Zaman/autoapply"
docker compose up -d
```

**Expected output:**
```
[+] Running 5/5
 ✓ postgres started
 ✓ redis   started
 ✓ ollama  started
 ✓ backend started
 ✓ frontend started
```

**Wait 15-20 seconds** for services to fully initialize.

Verify:
```powershell
docker compose ps
```

Should see all 5 containers with status "healthy" or "running":
```
NAME         STATUS              PORTS
postgres     Up 2 minutes        5433->5432/tcp
redis        Up 2 minutes        6379/tcp
ollama       Up 2 minutes        11434/tcp
backend      Up 70 seconds       8000->8000/tcp
frontend     Up 60 seconds       5173->5173/tcp
```

## Step 2: Test Backend Health

```powershell
curl http://localhost:8000/health
```

**Expected response:**
```json
{"status":"healthy","app":"AutoApply","debug":false}
```

## Step 3: Upload a Test Resume

Your resume will be used for matching. Create `test_resume.json`:

```powershell
# Create file with PowerShell
$resume = @{
    text = "John Developer. 5 years backend experience. Python, FastAPI, PostgreSQL, Docker, Kubernetes expert. Senior Backend Engineer at TechCorp. BS in Computer Science from Stanford. Seeking remote/hybrid Senior Backend role in SaaS or FinTech. Min salary $150k. GitHub: github.com/johndeveloper LinkedIn: linkedin.com/in/johndeveloper"
    metadata = @{ updated_at = Get-Date }
}

$json = $resume | ConvertTo-Json
curl -X POST http://localhost:8000/jobs/resume `
  -H "Content-Type: application/json" `
  -d $json
```

**Expected response:**
```json
{
  "id": "uuid",
  "base_resume": { "text": "..." },
  "created_at": "2026-03-23T..."
}
```

## Step 4: Scrape Some Jobs

Scrape GitHub Jobs (into database):

```powershell
curl -X POST "http://localhost:8000/jobs/scrape/github?query=python"
```

**Expected response:**
```json
{
  "status": "scraping",
  "message": "Started scraping GitHub Jobs for: python",
  "source": "github"
}
```

⏳ **Wait 30-45 seconds** while scraper runs in background

Check if jobs were saved:
```powershell
curl http://localhost:8000/jobs
```

Should see jobs array with 20+ jobs.

## Step 5: ⭐ Test Main Feature - Get Matches

This is the **magic endpoint** that shows jobs ranked by match score:

```powershell
curl http://localhost:8000/jobs/matches
```

### What to Expect

**Response structure:**
```json
{
  "total_jobs": 42,
  "top_matches": [
    {
      "match_score": 94,
      "job_title": "Senior Backend Engineer",
      "positive_matches": [
        "✓ Has all 8 required skills",
        "✓ Perfect seniority match",
        "✓ Salary $200k meets expectation"
      ],
      "recommendation": "🎯 Excellent match! Highly recommended"
    }
  ],
  "matches": [ ... ]  // All 42 jobs ranked
}
```

### Key Things to Check

✅ Jobs appear sorted by match_score (highest first)
✅ Top jobs have score 85-100 (best matches)
✅ Detailed reasoning shown for each
✅ Missing skills identified

## Step 6: Analyze Specific Job

Get deeply into why a job is/isn't a match:

```powershell
# First, get a job_id from the matches response
# Then analyze it:

curl "http://localhost:8000/jobs/job/{job_id}/analysis"
```

**Response includes:**
```json
{
  "job_id": "uuid",
  "job_title": "Senior Backend Engineer",
  "match_analysis": {
    "match_score": 94,
    "skill_match_score": 95,
    "seniority_match_score": 100,
    "salary_match_score": 100,
    "remote_match_score": 85,
    "positive_matches": [...],
    "concerns": [],
    "missing_skills": []
  },
  "parsed_job": {
    "required_skills": ["Python", "FastAPI", "PostgreSQL"],
    "nice_to_have_skills": ["Docker"],
    "seniority_level": "senior",
    "salary_min": 180000,
    "salary_max": 240000,
    // ... full parsed job data
  }
}
```

## Complete Test Script

Save as `test_phase3a.ps1`:

```powershell
Write-Host "🚀 Phase 3A Testing Script" -ForegroundColor Green
Write-Host ""

# Test 1: Health Check
Write-Host "1️⃣  Testing health endpoint..."
$health = curl http://localhost:8000/health | ConvertFrom-Json
if ($health.status -eq "healthy") {
    Write-Host "✅ Backend is healthy" -ForegroundColor Green
} else {
    Write-Host "❌ Backend health check failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Test 2: Get Jobs Count
Write-Host "2️⃣  Checking jobs in database..."
$jobs_response = curl http://localhost:8000/jobs | ConvertFrom-Json
$job_count = $jobs_response.Length
Write-Host "✅ Found $job_count jobs in database" -ForegroundColor Green

if ($job_count -eq 0) {
    Write-Host "⚠️  No jobs to match. Run scraper first:" -ForegroundColor Yellow
    Write-Host "   curl -X POST 'http://localhost:8000/jobs/scrape/github?query=python'" -ForegroundColor Yellow
}

Write-Host ""

# Test 3: Get Matches
Write-Host "3️⃣  Getting job matches (MAIN FEATURE)..."
try {
    $matches_response = curl http://localhost:8000/jobs/matches | ConvertFrom-Json
    $total = $matches_response.total_jobs
    
    if ($total -gt 0) {
        $top_match = $matches_response.top_matches[0]
        Write-Host "✅ Got $total job matches" -ForegroundColor Green
        Write-Host "   Top match: $($top_match.job_title)" -ForegroundColor Cyan
        Write-Host "   Score: $($top_match.match_score)%" -ForegroundColor Cyan
        Write-Host "   Recommendation: $($top_match.recommendation)" -ForegroundColor Cyan
    } else {
        Write-Host "⚠️  No matches found. Jobs may not be parsed yet." -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Matching failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "✨ Phase 3A testing complete!" -ForegroundColor Green
```

Run it:
```powershell
.\test_phase3a.ps1
```

## Troubleshooting

### "Cannot connect to Ollama"
- Ollama container may still be starting
- Wait 30 seconds and retry
- Check logs: `docker compose logs ollama`

### "No matches returned"
- Jobs may not be parsed yet (async process)
- Wait 10 seconds and retry
- Or manually trigger parsing: `curl -X POST "http://localhost:8000/jobs/parse-job?job_id={uuid}"`

### "Jobs not in database"
- Run scraper first: `curl -X POST "http://localhost:8000/jobs/scrape/github?query=python"`
- Wait 30-45 seconds
- Check again: `curl http://localhost:8000/jobs`

### Check Logs
```powershell
# Backend logs
docker compose logs backend -f

# Ollama logs (LLM)
docker compose logs ollama -f

# Database logs
docker compose logs postgres -f
```

## Frontend Dashboard

Open in browser:
```
http://localhost:5173
```

Currently shows jobs count, but Phase 3B will add:
- Match score visualization
- Ranked job list
- Match reason display

## Next Steps After Testing

If everything works:

1. ✅ Phase 3A deployed & tested
2. ⏭️ Phase 3B: Frontend UI for match scores
3. ⏭️ Phase 4: Resume tailoring per job
4. ⏭️ Phase 5: Auto-apply logic

## Key Metrics to Verify

| Metric | Expected | Status |
|--------|----------|--------|
| Backend health | ✓ responding | __ |
| Jobs scraped | 20+ | __ |
| Jobs parsed | 10+ | __ |
| Matches calculated | 10+ | __ |
| Top match score | 80+ | __ |
| Parsing speed | <5s per job | __ |

## API Reference Quick

```powershell
# Health check
GET http://localhost:8000/health

# Get all jobs
GET http://localhost:8000/jobs

# Get job stats
GET http://localhost:8000/jobs/stats/summary

# Upload resume
POST http://localhost:8000/jobs/resume

# Get resume
GET http://localhost:8000/jobs/resume

# Scrape GitHub
POST http://localhost:8000/jobs/scrape/github?query=python

# Parse job
POST http://localhost:8000/jobs/parse-job?job_id={uuid}

# Parse resume
POST http://localhost:8000/jobs/parse-resume

# GET MATCHES (MAIN!)
GET http://localhost:8000/jobs/matches

# Analyze specific job
GET http://localhost:8000/jobs/job/{job_id}/analysis
```

---

**Ready?** Start Docker Desktop, then follow Step 1 above!
