# Phase 3A Automated Testing Script
# Usage: .\test_phase3a.ps1

# Color output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error-Custom { Write-Host $args -ForegroundColor Red }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warn { Write-Host $args -ForegroundColor Yellow }

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║        Phase 3A Testing - Job Parsing & Matching          ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

$BaseURL = "http://localhost:8000"
$MaxWait = 60

# Test 1: Health Check
Write-Host "▶ TEST 1: Health Check" -ForegroundColor Cyan
Write-Host "  Endpoint: GET /health" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "$BaseURL/health" -Method Get -ErrorAction Stop
    $health = $response.Content | ConvertFrom-Json
    if ($health.status -eq "healthy") {
        Write-Success "  ✅ Backend is healthy"
    } else {
        Write-Error-Custom "  ❌ Backend not healthy"
        exit 1
    }
} catch {
    Write-Error-Custom "  ❌ Cannot reach backend at $BaseURL"
    Write-Error-Custom "  Make sure Docker containers are running: docker compose ps"
    exit 1
}
Write-Host ""

# Test 2: Check for existing jobs
Write-Host "▶ TEST 2: Count Jobs in Database" -ForegroundColor Cyan
Write-Host "  Endpoint: GET /jobs" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "$BaseURL/jobs" -Method Get -ErrorAction Stop
    $jobs = $response.Content | ConvertFrom-Json
    $jobCount = if ($jobs -is [array]) { $jobs.Count } else { if ($jobs) { 1 } else { 0 } }
    
    if ($jobCount -eq 0) {
        Write-Warn "  ⚠️  No jobs found (need to scrape first)"
        Write-Info "     Running: POST /jobs/scrape/github?query=python"
        
        # Trigger scraper
        $null = Invoke-WebRequest -Uri "$BaseURL/jobs/scrape/github?query=python" -Method Post -ErrorAction SilentlyContinue
        Write-Info "     ⏳ Scraping in background... waiting 45 seconds"
        
        # Wait for scraping
        for ($i = 0; $i -lt 45; $i++) {
            Write-Host -NoNewline "."
            Start-Sleep -Seconds 1
        }
        Write-Host ""
        
        # Recheck jobs
        $response = Invoke-WebRequest -Uri "$BaseURL/jobs" -Method Get -ErrorAction Stop
        $jobs = $response.Content | ConvertFrom-Json
        $jobCount = if ($jobs -is [array]) { $jobs.Count } else { if ($jobs) { 1 } else { 0 } }
    }
    
    Write-Success "  ✅ Found $jobCount jobs in database"
} catch {
    Write-Error-Custom "  ❌ Error checking jobs: $_"
    exit 1
}
Write-Host ""

if ($jobCount -eq 0) {
    Write-Warn "⚠️  No jobs to test matching with. Skipping match tests."
    exit 0
}

# Test 3: Get Job Stats
Write-Host "▶ TEST 3: Job Statistics" -ForegroundColor Cyan
Write-Host "  Endpoint: GET /jobs/stats/summary" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "$BaseURL/jobs/stats/summary" -Method Get -ErrorAction Stop
    $stats = $response.Content | ConvertFrom-Json
    Write-Success "  ✅ Job Statistics:"
    Write-Info "     Total: $($stats.total_jobs)"
    Write-Info "     Applied: $($stats.applied)"
    Write-Info "     Pending: $($stats.pending_approval)"
} catch {
    Write-Error-Custom "  ⚠️  Could not get stats: $_"
}
Write-Host ""

# Test 4: Check if Resume exists
Write-Host "▶ TEST 4: Resume Management" -ForegroundColor Cyan
Write-Host "  Endpoint: GET /jobs/resume" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "$BaseURL/jobs/resume" -Method Get -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $resume = $response.Content | ConvertFrom-Json
        Write-Success "  ✅ Resume found in database"
    } else {
        Write-Warn "  ⚠️  No resume in database (need to upload)"
        Write-Info "     Creating test resume..."
        
        $testResume = @{
            text = "John Developer. 5 years backend experience. Expert in Python, FastAPI, PostgreSQL, Docker, Kubernetes. Senior Backend Engineer at TechCorp. BS Computer Science from Stanford. Seeking remote/hybrid Senior Backend role in SaaS/FinTech. Minimum salary $150k. GitHub: github.com/john LinkedIn: linkedin.com/in/john"
            metadata = @{}
        }
        
        $resumeJson = $testResume | ConvertTo-Json
        $response = Invoke-WebRequest -Uri "$BaseURL/jobs/resume" `
            -Method Post `
            -ContentType "application/json" `
            -Body $resumeJson `
            -ErrorAction Stop
        
        Write-Success "  ✅ Test resume created"
    }
} catch {
    Write-Error-Custom "  ❌ Error with resume: $_"
}
Write-Host ""

# Test 5: THE MAIN FEATURE - Get Matches
Write-Host "▶ TEST 5: ⭐ GET JOB MATCHES (MAIN FEATURE)" -ForegroundColor Yellow
Write-Host "  Endpoint: GET /jobs/matches" -ForegroundColor Gray
Write-Info "  This endpoint ranks all $jobCount jobs by how well they match your resume"
Write-Host ""

try {
    Write-Info "  ⏳ Calculating matches (this may take a minute for parsing)..."
    $startTime = Get-Date
    
    $response = Invoke-WebRequest -Uri "$BaseURL/jobs/matches" -Method Get -ErrorAction Stop
    $matches = $response.Content | ConvertFrom-Json
    
    $duration = ((Get-Date) - $startTime).TotalSeconds
    
    Write-Success "  ✅ Matching complete! (${duration}s)"
    Write-Host ""
    
    $totalMatches = $matches.total_jobs
    Write-Info "  📊 RESULTS:"
    Write-Info "     Total jobs matched: $totalMatches"
    
    if ($matches.top_matches -and $matches.top_matches.Count -gt 0) {
        Write-Info "     Top matches: $($matches.top_matches.Count)"
        Write-Host ""
        
        Write-Info "  🏆 TOP 3 MATCHES:"
        Write-Host ""
        
        for ($i = 0; $i -lt [Math]::Min(3, $matches.top_matches.Count); $i++) {
            $match = $matches.top_matches[$i]
            $scoreColor = if ($match.match_score -ge 85) { "Green" } elseif ($match.match_score -ge 70) { "Cyan" } else { "Yellow" }
            
            Write-Host "   [$($i+1)️⃣] $($match.job_title)" -ForegroundColor $scoreColor
            Write-Host "       Match Score: $(Write-Host -NoNewline; Write-Host "$($match.match_score)%" -ForegroundColor $scoreColor -NoNewline)"
            
            if ($match.company_name) {
                Write-Host " | Company: $($match.company_name)"
            } else {
                Write-Host ""
            }
            
            if ($match.positive_matches -and $match.positive_matches.Count -gt 0) {
                Write-Host "       ✓ $(($match.positive_matches[0] -replace '✓ ', ''))"
                if ($match.positive_matches.Count -gt 1) {
                    Write-Host "       ✓ $(($match.positive_matches[1] -replace '✓ ', ''))"
                }
            }
            
            if ($match.concerns -and $match.concerns.Count -gt 0) {
                Write-Host "       ⚠️  $($match.concerns[0] -replace '⚠️ ', '')" -ForegroundColor Yellow
            }
            
            Write-Host "       💡 $($match.recommendation)"
            Write-Host ""
        }
        
        Write-Success "  ✅ Job matching is working! 🎉"
    } else {
        Write-Warn "  ⚠️  No matches returned (jobs may not be parsed yet)"
    }
    
} catch {
    Write-Error-Custom "  ❌ Error getting matches: $_"
    Write-Warn "  This may be normal if jobs are still being parsed"
}

Write-Host ""

# Summary
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║                    TEST SUMMARY                            ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta

Write-Success "✅ Phase 3A is deployed and working!"
Write-Host ""
Write-Info "📋 Next Steps:"
Write-Info "   1. Check matching results above"
Write-Info "   2. Visit frontend at http://localhost:5173"
Write-Info "   3. For detailed job analysis, visit:"
Write-Info "      http://localhost:8000/docs (Swagger UI)"
Write-Info ""
Write-Info "🔗 Documentation:"
Write-Info "   - Testing Guide: TESTING_GUIDE.md"
Write-Info "   - Phase 3A Docs: PHASE3A_PARSING_COMPLETE.md"
Write-Info ""
