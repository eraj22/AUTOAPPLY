# Phase 3A - WSL Ubuntu Deployment Guide

## Prerequisites for WSL

### 1. Docker Desktop for Windows (with WSL 2 Backend)
- Install Docker Desktop
- Enable WSL 2 in Docker settings
- Verify: `docker --version` in WSL terminal

### 2. Access WSL Ubuntu Terminal
```bash
# From Windows PowerShell
wsl

# Or open Ubuntu terminal directly from Start Menu
```

You should see a Linux prompt:
```
user@machine:/mnt/c/Users/...#
```

---

## Quick Deploy (5 Minutes)

### Step 1: Navigate to Project
```bash
cd /mnt/c/Users/Sher\ Zaman/autoapply
```

Or if you have the repo cloned in WSL:
```bash
cd ~/autoapply  # or wherever you cloned it
```

### Step 2: Start Containers
```bash
docker compose up -d
```

Wait 15-20 seconds ⏳

Verify all running:
```bash
docker compose ps
```

### Step 3: Run Automated Test
```bash
bash test_phase3a.sh
```

Done! Watch the results show up 🎉

---

## Files Ready for WSL

I've created WSL-native scripts:

### 1. **test_phase3a.sh** (Bash version)
Automated testing with colored output
```bash
./test_phase3a.sh
```

### 2. **QUICK_START.md**
General deployment guide (works for all platforms)

### 3. **TESTING_GUIDE.md**
Curl examples (work perfectly in WSL)

---

## Manual Testing (Optional)

### Health Check
```bash
curl http://localhost:8000/health
```

### Get Matches (Main Feature)
```bash
curl http://localhost:8000/jobs/matches | jq
```

### Monitor Logs
```bash
# All logs
docker compose logs -f

# Specific service
docker compose logs backend -f
docker compose logs ollama -f
```

---

## WSL-Specific Commands

### File Paths in WSL
```bash
# Windows path
C:\Users\Sher Zaman\autoapply

# WSL path
/mnt/c/Users/Sher\ Zaman/autoapply
```

### Docker from WSL
```bash
# Works exactly like Linux
docker ps
docker compose up -d
docker compose logs -f

# No need for PowerShell
```

### Edit Files
```bash
# From WSL terminal
nano TESTING_GUIDE.md
vim test_phase3a.sh

# Or open in VS Code from WSL
code .

# From Windows, edits sync automatically
```

---

## Testing Output Example

When you run `./test_phase3a.sh`, you'll see:

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

▶ TEST 4: Resume Management
  ✅ Test resume created

▶ TEST 5: ⭐ GET JOB MATCHES (MAIN FEATURE)
  ✅ Matching complete! (23.4s)

  📊 RESULTS: 47 jobs matched

  🏆 TOP 3 MATCHES:

  [1️⃣] Senior Backend Engineer @ Stripe
      Match Score: 95% ✅
      ✓ Has all 8 required skills
      ✓ Perfect seniority match
      💡 🎯 Excellent match!

  [2️⃣] Senior Python Developer @ TechCorp
      Match Score: 92% ✅
      ✓ Has 7/8 required skills
      💡 ✓ Good match!

  [3️⃣] Full Stack Engineer
      Match Score: 78% ⚠️
      ✓ Has 5/8 required skills
      ⚠️  Missing Docker
      💡 ~ Moderate match
```

---

## Common WSL Issues & Fixes

### "Docker command not found"
```bash
# Install Docker in WSL
sudo apt-get update
sudo apt-get install docker.io

# OR use Docker Desktop backend (better)
# Docker Desktop → Settings → Resources → WSL Integration
```

### "Cannot connect to Docker daemon"
```bash
# Check if Docker running in WSL
docker ps

# If not, start Docker
sudo service docker start

# Or use Docker Desktop (easier)
```

### "Port 8000 already in use"
```bash
# Check what's using it
sudo lsof -i :8000

# Or just kill and restart
docker compose restart backend
```

### Files not syncing
```bash
# Ensure you're editing in /mnt/c/Users
# (Windows paths automatically sync)

# Or clone repo directly in WSL (~/)
# But then only access from WSL
```

---

## Useful WSL Commands

```bash
# List running containers
docker compose ps

# View logs (live)
docker compose logs -f

# View specific service logs
docker compose logs backend -f
docker compose logs ollama -f

# Get container stats
docker stats

# Stop all containers
docker compose stop

# Start again
docker compose up -d

# Full restart
docker compose restart

# Clean (WARNING: deletes data)
docker compose down

# See database
docker compose exec postgres psql -U autoapply -d autoapply_db
```

---

## API Testing in WSL

### With curl (installed by default)
```bash
# Get health
curl http://localhost:8000/health

# Get matches
curl http://localhost:8000/jobs/matches | jq .top_matches

# Get specific job
curl "http://localhost:8000/jobs/job/{job_id}/analysis" | jq
```

### With jq (for pretty JSON)
```bash
# Install jq
sudo apt-get install jq

# Pretty print JSON
curl http://localhost:8000/jobs/matches | jq
```

### With httpie (optional, nicer output)
```bash
# Install
sudo apt-get install httpie

# Use it
http http://localhost:8000/jobs/matches
http POST http://localhost:8000/jobs/parse-resume
```

---

## Full Workflow in WSL

```bash
# 1. Enter WSL
wsl

# 2. Navigate to project
cd /mnt/c/Users/Sher\ Zaman/autoapply

# 3. Start containers
docker compose up -d

# 4. Wait for startup (15 seconds)
sleep 15

# 5. Run test script
./test_phase3a.sh

# 6. Watch results
# (test will automatically show top matches)
```

---

## Monitoring While Testing

Open **another WSL terminal** and run:

```bash
# Terminal 1: Run tests
./test_phase3a.sh

# Terminal 2: Watch logs in real-time
docker compose logs -f backend

# Terminal 3: Monitor resources
docker stats
```

---

## Advantages of WSL

✅ Native Linux Docker (faster than Windows)  
✅ No nested virtualization overhead  
✅ Direct terminal access (no WSL-specific issues)  
✅ File sharing works seamlessly  
✅ Can run Linux scripts directly  

---

## Testing in WSL Summary

| Step | Command | Time |
|------|---------|------|
| Start containers | `docker compose up -d` | 2 min |
| Wait | `sleep 15` | 15s |
| Run tests | `./test_phase3a.sh` | 3-5 min |
| **Total** | | **~6 min** |

---

## Docker in WSL vs Windows

**With WSL (you):**
- ✅ Native Linux performance
- ✅ Docker runs directly
- ✅ All Linux tools available
- ✅ No path translation delays

**Windows native (slower):**
- File path translation overhead
- Docker Desktop VM layer
- Not as performant

You already have the better setup! 🚀

---

## Quick Reference

```bash
# Start everything
docker compose up -d

# Test everything
./test_phase3a.sh

# Check health
curl http://localhost:8000/health

# Get matches
curl http://localhost:8000/jobs/matches | jq

# Monitor
docker compose logs -f

# Stop everything
docker compose down
```

---

## Next Steps

1. ✅ Run `./test_phase3a.sh` in WSL
2. ✅ See your matched jobs
3. ✅ Verify top matches have high scores
4. ✅ Phase 3A is tested and working!

---

**Ready? Just run:**

```bash
cd /mnt/c/Users/Sher\ Zaman/autoapply
docker compose up -d
./test_phase3a.sh
```

Done! 🎉
