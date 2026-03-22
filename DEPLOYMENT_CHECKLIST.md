# Phase 3A Deployment Checklist

## Pre-Deployment Checklist

### System Requirements
- [ ] Windows/Mac/Linux with Docker Desktop installed
- [ ] 8GB+ RAM available
- [ ] ~5GB free disk space (for containers and data)
- [ ] PowerShell or terminal access

### Verification
- [ ] Docker Desktop is installed
- [ ] Docker daemon is running (check system tray icon)
- [ ] Current directory: `C:/Users/Sher Zaman/autoapply`
- [ ] Git is committed and pushed (Phase 3A code in GitHub)

---

## Deployment Steps

### 1️⃣ Start Docker Desktop
**Time: ~30 seconds**

1. Open Windows Start Menu
2. Search "Docker Desktop"
3. Click to launch
4. Wait for system tray icon to show "Docker is running"

### 2️⃣ Start Containers
**Time: ~2 minutes**

```powershell
cd "C:/Users/Sher Zaman/autoapply"
docker compose up -d
```

Wait 15-20 seconds for initialization.

Verify all containers running:
```powershell
docker compose ps
```

Expected output (all showing "Up" or "healthy"):
```
NAME      STATUS              PORTS
postgres  Up X minutes        5433->5432/tcp
redis     Up X minutes        6379->6379/tcp
ollama    Up X minutes        11434->11434/tcp
backend   Up X seconds        8000->8000/tcp
frontend  Up X seconds        5173->5173/tcp
```

- [ ] All 5 containers running

### 3️⃣ Verify Backend is Responsive
**Time: ~1 minute**

```powershell
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"healthy","app":"AutoApply","debug":false}
```

OR use browser: `http://localhost:8000/health`

- [ ] Backend responding to requests

### 4️⃣ Run Automated Tests
**Time: ~3-5 minutes (includes scraping + matching)**

```powershell
# From autoapply root directory
.\test_phase3a.ps1
```

This script will:
1. ✅ Check backend health
2. ✅ Count existing jobs
3. ✅ Scrape GitHub Jobs if needed (45 seconds)
4. ✅ Parse jobs and calculate match scores
5. ✅ Display top 3 matching jobs

Expected test output:
```
╔════════════════════════════════════════════════════════════╗
║        Phase 3A Testing - Job Parsing & Matching          ║
╚════════════════════════════════════════════════════════════╝

▶ TEST 1: Health Check
  ✅ Backend is healthy

▶ TEST 2: Count Jobs in Database
  ✅ Found 47 jobs in database

▶ TEST 3: Job Statistics
  ✅ Job Statistics:
     Total: 47
     Applied: 0
     Pending: 0

▶ TEST 4: Resume Management
  ✅ Resume found in database

▶ TEST 5: ⭐ GET JOB MATCHES (MAIN FEATURE)
  ✅ Matching complete! (23.4s)

  📊 RESULTS:
     Total jobs matched: 47
     Top matches: 5

  🏆 TOP 3 MATCHES:

   [1️⃣] Senior Backend Engineer
       Match Score: 95% | Company: Stripe
       ✓ Has all 8 required skills
       ✓ Perfect seniority match
       💡 🎯 Excellent match! Highly recommended to apply

   [2️⃣] Senior Python Developer
       Match Score: 92% | Company: TechCorp
       ✓ Has 7/8 required skills
       ✓ Seniority close match
       💡 ✓ Good match, worth considering

   [3️⃣] Full Stack Engineer
       Match Score: 78%
       ✓ Has 5/8 required skills
       ⚠️  Missing Docker experience
       💡 ~ Moderate match, apply if interested

✅ Phase 3A is deployed and working! 🎉
```

- [ ] Test script passes (or mostly passes)
- [ ] Match scores calculated for jobs
- [ ] Top matches displayed with reasoning

### 5️⃣ Manual Testing (Optional)

Test individual endpoints:

**Get matches (main feature):**
```powershell
curl http://localhost:8000/jobs/matches | ConvertFrom-Json
```

**Get job stats:**
```powershell
curl http://localhost:8000/jobs/stats/summary
```

**List jobs:**
```powershell
curl http://localhost:8000/jobs | ConvertFrom-Json | Select-Object -First 3
```

**Analyze specific job:**
```powershell
# Replace {job_id} with real ID from matches response
curl "http://localhost:8000/jobs/job/{job_id}/analysis"
```

- [ ] Can fetch matches
- [ ] Can get job analysis
- [ ] Response times reasonable (~2-5 seconds per job)

### 6️⃣ Visit Frontend (Optional)

Open browser:
```
http://localhost:5173
```

Currently shows basic dashboard (Phase 3B will add match visualization)

- [ ] Frontend loads without errors

---

## Deployment Validation

### Performance Benchmarks

| Component | Target | Status |
|-----------|--------|--------|
| Backend health check | <200ms | __ |
| Get 47 jobs | <500ms | __ |
| Calculate matches | <30s | __ |
| Per-job parsing | 2-5s | __ |
| Match recommendation | instant | __ |

### Data Validation

| Metric | Expected | Status |
|--------|----------|--------|
| Jobs in database | 20+ | __ |
| Jobs with parsed data | 10+ | __ |
| Top match score | 80+ | __ |
| Match accuracy | Subjective | __ |
| No crashes | ✅ | __ |

---

## Troubleshooting

### ❌ "Cannot connect to backend"
**Problem**: Docker container not reachable at localhost:8000

**Solution**:
1. Check container is running: `docker compose ps backend`
2. Check logs: `docker compose logs backend`
3. Restart: `docker compose restart backend`

### ❌ "Parse timeout after 60s"
**Problem**: Ollama is taking too long to respond

**Solution**:
1. May be first run (model loading) - wait longer
2. Check Ollama container: `docker compose logs ollama`
3. Check disk space: `docker system df`

### ❌ "No matches returned"
**Problem**: Jobs not being parsed

**Solution**:
1. Wait longer (parsing happens in background)
2. Check backend logs: `docker compose logs backend -f`
3. Manually trigger: `curl -X POST "http://localhost:8000/jobs/parse-job?job_id={uuid}"`

### ❌ "Database error"
**Problem**: PostgreSQL connection failed

**Solution**:
1. Restart containers: `docker compose restart`
2. Wait 30 seconds for DB to initialize
3. Check PostgreSQL logs: `docker compose logs postgres`

### ⚠️ Slow performance
**Problem**: Takes >10s per match

**Solutions**:
- Normal for first run (LLM warming up)
- Increase Docker resource allocation
- Reduce number of jobs (test with 5 jobs first)

---

## Post-Deployment

### What's Working Now ✅
- ✅ Job scraping (GitHub Jobs, Greenhouse)
- ✅ Job parsing with AI
- ✅ Resume parsing with AI
- ✅ Job matching algorithm
- ✅ Match score calculation (0-100)
- ✅ Detailed match reasoning
- ✅ Missing skills identification

### What's Next (Phase 3B/4/5) ⏳
- Frontend UI for match scores
- Resume tailoring per job
- Auto-apply logic
- Approval workflow

### Quick Links
- Tests: `.\test_phase3a.ps1`
- Docs: `PHASE3A_PARSING_COMPLETE.md`
- Testing guide: `TESTING_GUIDE.md`
- API docs: `http://localhost:8000/docs`
- GitHub: `https://github.com/eraj22/AUTOAPPLY`

### Monitoring
```powershell
# View all logs
docker compose logs -f

# View specific service
docker compose logs backend -f
docker compose logs ollama -f
docker compose logs postgres -f

# Check resource usage
docker stats

# Stop all
docker compose down

# Clean (remove volumes)
docker compose down -v
```

---

## Success Criteria

✅ Phase 3A is successfully deployed if:

1. **Backend Health**: `GET /health` returns 200 OK
2. **Jobs Loaded**: `GET /jobs` returns 20+ jobs
3. **Matching Works**: `GET /jobs/matches` returns rankings
4. **High Scores**: Top matches have 80+ score
5. **Matches Detailed**: Each match has positive/negative reasons
6. **No Crashes**: All endpoints stable for 5 minutes

---

## Estimated Time

| Step | Time |
|------|------|
| Start Docker | 30s |
| Start containers | 2 min |
| Verify backend | 1 min |
| Run tests | 3-5 min |
| **Total** | **~10 minutes** |

---

**Ready to deploy?** 

1. Start Docker Desktop
2. Run: `docker compose up -d`
3. Run: `.\test_phase3a.ps1`
4. Check results and celebrate! 🎉
