from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job, Resume, Company 
from app.schemas import JobResponse, ResumeResponse, ResumeCreate
from app.services.scraper import JobScraper
from app.services.job_parser import get_job_parser, ParsedJobData
from app.services.resume_parser import get_resume_parser, ParsedResumeData
from app.services.job_matcher import get_job_matcher, JobMatchResult
from typing import List, Optional
import uuid
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    company_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get jobs (optionally filtered by company or status)"""
    query = db.query(Job)
    
    if company_id:
        query = query.filter(Job.company_id == company_id)
    if status:
        query = query.filter(Job.status == status)
    
    return query.all()


@router.post("/seed")
async def seed_diverse_jobs(db: Session = Depends(get_db)):
    """
    Seed database with 20+ diverse test jobs for demonstration
    Useful for showing variety in job matching
    """
    # Get or create TechCorp company
    company = db.query(Company).filter(Company.name == "TechCorp Industries").first()
    if not company:
        company = Company(
            name="TechCorp Industries",
            careers_url="https://careers.techcorp.example.com",
            description="Enterprise software company"
        )
        db.add(company)
        db.flush()
    
    company_id = company.id
    
    # Diverse job listings with varied requirements
    jobs_data = [
        # Senior Backend positions (high match)
        {
            "title": "Senior Backend Engineer",
            "url": "https://example.com/jobs/senior-backend-1",
            "raw_jd": """Senior Backend Engineer - Remote
Requirements:
- 6+ years backend development
- Python, FastAPI, Django expertise
- PostgreSQL, Redis, Elasticsearch
- DDD, microservices architecture
- AWS/GCP expertise
Salary: $160k-$200k
Remote: 100%
Experience: Senior"""
        },
        {
            "title": "Backend Architect",
            "url": "https://example.com/jobs/backend-architect",
            "raw_jd": """Backend Architect - San Francisco (Hybrid)
Requirements:
- 8+ years backend development
- Python, Go, Java experience
- System design and architecture
- Team leadership
- Cloud infrastructure (AWS)
Salary: $180k-$250k
Remote: Hybrid
Experience: Senior"""
        },
        
        # Mid-level Backend (good match)
        {
            "title": "Backend Developer",
            "url": "https://example.com/jobs/backend-mid-1",
            "raw_jd": """Backend Developer - Remote
Requirements:
- 4+ years Python development
- FastAPI or Django
- PostgreSQL, MongoDB
- REST APIs, microservices
- Docker, Kubernetes
Salary: $130k-$170k
Remote: 100%
Experience: Mid-level"""
        },
        {
            "title": "Python Backend Engineer",
            "url": "https://example.com/jobs/python-backend",
            "raw_jd": """Python Backend Engineer - Remote
Requirements:
- 3+ years Python
- FastAPI, Flask, or Django
- SQL/NoSQL databases
- REST API development
- Problem solving
Salary: $110k-$150k
Remote: 100%
Experience: Mid-level"""
        },
        
        # Junior Developer (partial match)
        {
            "title": "Junior Python Developer",
            "url": "https://example.com/jobs/junior-python",
            "raw_jd": """Junior Python Developer - New York (Onsite)
Requirements:
- 1+ years Python experience
- Flask or FastAPI exposure
- Learning mindset
- Team player
- CS degree or bootcamp
Salary: $70k-$100k
Remote: Onsite
Experience: Junior"""
        },
        {
            "title": "Entry Level Backend Intern",
            "url": "https://example.com/jobs/backend-intern",
            "raw_jd": """Backend Intern - Los Angeles (Onsite)
Requirements:
- Python basics
- Database concepts
- Web development fundamentals
- Currently in school or recent grad
Salary: $25-30/hr
Remote: Onsite
Experience: Intern"""
        },
        
        # Frontend positions (low match for backend engineer)
        {
            "title": "Senior Frontend Engineer",
            "url": "https://example.com/jobs/senior-frontend",
            "raw_jd": """Senior Frontend Engineer - Remote
Requirements:
- 6+ years React/Vue/Angular
- TypeScript, testing
- UI/UX principles
- Performance optimization
Salary: $150k-$200k
Remote: 100%
Tech Stack: React, TypeScript, TailwindCSS"""
        },
        {
            "title": "React Developer",
            "url": "https://example.com/jobs/react-dev",
            "raw_jd": """React Developer - Berlin (Remote)
Requirements:
- 3+ years React
- JavaScript/TypeScript
- CSS, responsive design
- State management
Salary: €80k-€120k
Remote: 100%
Tech Stack: React, Redux, Webpack"""
        },
        
        # DevOps/Infrastructure (partial match)
        {
            "title": "DevOps Engineer",
            "url": "https://example.com/jobs/devops-senior",
            "raw_jd": """Senior DevOps Engineer - Austin (Hybrid)
Requirements:
- 5+ years DevOps/SRE
- Kubernetes, Docker
- AWS/GCP/Azure
- Terraform, IaC
- CI/CD pipelines
Salary: $140k-$190k
Remote: Hybrid
Experience: Senior"""
        },
        {
            "title": "Infrastructure Engineer",
            "url": "https://example.com/jobs/infra-engineer",
            "raw_jd": """Infrastructure Engineer - Remote
Requirements:
- 4+ years infrastructure
- Kubernetes, Docker
- AWS or GCP
- IaC (Terraform, CloudFormation)
- Monitoring and logging
Salary: $130k-$170k
Remote: 100%
Experience: Mid-level"""
        },
        {
            "title": "SRE Engineer",
            "url": "https://example.com/jobs/sre",
            "raw_jd": """Site Reliability Engineer - London (Remote)
Requirements:
- 3+ years SRE/DevOps
- Linux, scripting (Python/Bash)
- Monitoring (Prometheus, ELK)
- On-call rotations
Salary: £100k-£150k
Remote: 100%
Experience: Mid-level"""
        },
        
        # Full Stack positions
        {
            "title": "Full Stack Engineer",
            "url": "https://example.com/jobs/fullstack-senior",
            "raw_jd": """Senior Full Stack Engineer - Toronto (Hybrid)
Requirements:
- 6+ years full stack
- Backend: Python, Node.js
- Frontend: React, Vue, Angular
- PostgreSQL, MongoDB
- AWS, Docker
Salary: CAD $150k-$200k
Remote: Hybrid
Experience: Senior"""
        },
        {
            "title": "Full Stack Developer",
            "url": "https://example.com/jobs/fullstack-mid",
            "raw_jd": """Full Stack Developer - Singapore (Remote)
Requirements:
- 3+ years full stack
- Python or Node.js backend
- React/Vue frontend
- PostgreSQL
- Docker basics
Salary: SGD $100k-$150k
Remote: 100%
Experience: Mid-level"""
        },
        
        # Data Engineering (partial match - Python focus)
        {
            "title": "Senior Data Engineer",
            "url": "https://example.com/jobs/data-engineer-senior",
            "raw_jd": """Senior Data Engineer - Remote
Requirements:
- 6+ years data engineering
- Python, Scala, or Java
- SQL, data warehousing
- Spark, Hadoop, Kafka
- AWS/GCP data services
Salary: $150k-$210k
Remote: 100%
Experience: Senior"""
        },
        {
            "title": "Data Engineer",
            "url": "https://example.com/jobs/data-engineer",
            "raw_jd": """Data Engineer - Amsterdam (Hybrid)
Requirements:
- 3+ years data engineering
- Python, SQL
- ETL/ELT pipelines
- Apache Spark, Airflow
- Data warehousing
Salary: €90k-€130k
Remote: Hybrid
Experience: Mid-level"""
        },
        
        # Mobile positions (low match)
        {
            "title": "Senior iOS Developer",
            "url": "https://example.com/jobs/ios-senior",
            "raw_jd": """Senior iOS Developer - Cupertino (Onsite)
Requirements:
- 6+ years iOS development
- Swift, Objective-C
- SwiftUI, Core Data
- App Store deployment
- Team leadership
Salary: $170k-$240k
Remote: Onsite
Tech Stack: Swift, SwiftUI"""
        },
        {
            "title": "Android Developer",
            "url": "https://example.com/jobs/android",
            "raw_jd": """Android Developer - São Paulo (Remote)
Requirements:
- 4+ years Android
- Kotlin, Java
- Material Design
- Android Studio
- Firebase
Salary: R$150k-R$250k
Remote: 100%
Tech Stack: Kotlin, Android Studio"""
        },
        
        # Niche technical roles
        {
            "title": "Machine Learning Engineer",
            "url": "https://example.com/jobs/ml-engineer",
            "raw_jd": """Machine Learning Engineer - Remote
Requirements:
- 4+ years ML/AI
- Python, TensorFlow/PyTorch
- Data science fundamentals
- Recommendation systems or NLP
- Cloud ML services
Salary: $140k-$200k
Remote: 100%
Experience: Mid-level"""
        },
        {
            "title": "Security Engineer",
            "url": "https://example.com/jobs/security",
            "raw_jd": """Security Engineer - Remote
Requirements:
- 4+ years cybersecurity
- Python, Go scripting
- Network security, cryptography
- Penetration testing
- OWASP, CIS frameworks
Salary: $130k-$180k
Remote: 100%
Experience: Mid-level"""
        },
        {
            "title": "Database Administrator",
            "url": "https://example.com/jobs/dba",
            "raw_jd": """Senior Database Administrator - Chicago (Hybrid)
Requirements:
- 6+ years DBA experience
- PostgreSQL, MySQL, Oracle
- Query optimization
- Backup and recovery
- Performance tuning
Salary: $120k-$160k
Remote: Hybrid
Experience: Senior"""
        },
        {
            "title": "Solutions Architect",
            "url": "https://example.com/jobs/solutions-architect",
            "raw_jd": """Solutions Architect - Seattle (Hybrid)
Requirements:
- 7+ years system design
- Python, Java, Go
- Cloud platforms (AWS/Azure/GCP)
- Enterprise architecture
- Customer engagement
Salary: $160k-$220k
Remote: Hybrid
Experience: Senior"""
        },
    ]
    
    # Insert jobs, avoiding duplicates
    added_count = 0
    
    for job_data in jobs_data:
        existing = db.query(Job).filter(Job.url == job_data["url"]).first()
        if existing:
            continue
        
        job = Job(
            company_id=company_id,
            title=job_data["title"],
            url=job_data["url"],
            raw_jd=job_data["raw_jd"],
            status="new",
            found_at=datetime.utcnow()
        )
        db.add(job)
        added_count += 1
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Seeded {added_count} diverse jobs",
        "total_jobs": db.query(Job).count()
    }


@router.get("/stats/summary")
async def get_job_stats(db: Session = Depends(get_db)):
    """Get job statistics"""
    from sqlalchemy import func
    
    stats = {
        "total_jobs": db.query(func.count(Job.id)).scalar() or 0,
        "applied": db.query(func.count(Job.id)).filter(Job.status == "applied").scalar() or 0,
        "pending_approval": db.query(func.count(Job.id)).filter(Job.status == "pending_approval").scalar() or 0,
        "skipped": db.query(func.count(Job.id)).filter(Job.status == "skipped").scalar() or 0,
        "failed": db.query(func.count(Job.id)).filter(Job.status == "failed").scalar() or 0,
    }
    return stats


# Scraping endpoints
@router.post("/scrape/github")
async def scrape_github_jobs(query: str = Query(...), background_tasks: BackgroundTasks = BackgroundTasks(), db: Session = Depends(get_db)):
    """
    Trigger GitHub Jobs scraping
    
    Args:
        query: Search query (e.g., "python developer")
    
    Returns:
        Status message with job count
    """
    background_tasks.add_task(run_github_scraper, query, db)
    return {
        "status": "scraping",
        "message": f"Started scraping GitHub Jobs for: {query}",
        "source": "github"
    }


@router.post("/scrape/greenhouse")
async def scrape_greenhouse_jobs(company_id: uuid.UUID, background_tasks: BackgroundTasks = BackgroundTasks(), db: Session = Depends(get_db)):
    """
    Trigger Greenhouse scraping for a company
    
    Args:
        company_id: Company ID with Greenhouse setup
    
    Returns:
        Status message with job count
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company or not company.careers_url:
        return {"error": "Company not found or has no careers URL"}
    
    background_tasks.add_task(run_greenhouse_scraper, company.careers_url, company_id, db)
    return {
        "status": "scraping",
        "message": f"Started scraping Greenhouse jobs for: {company.name}",
        "source": "greenhouse",
        "company_id": str(company_id)
    }


async def run_github_scraper(query: str, db: Session):
    """Background task: Scrape GitHub and save jobs"""
    try:
        async with JobScraper() as scraper:
            jobs = await scraper.scrape_github_jobs(query)
            
            # Save to database
            for job_data in jobs:
                # Check if job already exists (by URL)
                existing = db.query(Job).filter(Job.source_url == job_data.get("url")).first()
                if existing:
                    continue
                
                db_job = Job(
                    title=job_data.get("title"),
                    company=job_data.get("company"),
                    location=job_data.get("location"),
                    source_url=job_data.get("url"),
                    source="github_jobs",
                    status="new",
                    scraped_at=datetime.now(),
                    job_description=json.dumps(job_data)
                )
                db.add(db_job)
            
            db.commit()
            logger.info(f"Saved {len(jobs)} jobs from GitHub")
    except Exception as e:
        logger.error(f"GitHub scraper error: {e}")


async def run_greenhouse_scraper(careers_url: str, company_id: uuid.UUID, db: Session):
    """Background task: Scrape Greenhouse and save jobs"""
    try:
        async with JobScraper() as scraper:
            jobs = await scraper.scrape_greenhouse_jobs(careers_url)
            
            # Save to database
            for job_data in jobs:
                # Check if job already exists (by job_id)
                existing = db.query(Job).filter(Job.external_id == job_data.get("job_id")).first()
                if existing:
                    continue
                
                db_job = Job(
                    company_id=company_id,
                    title=job_data.get("title"),
                    location=job_data.get("location"),
                    source_url=job_data.get("url"),
                    source="greenhouse",
                    status="new",
                    external_id=job_data.get("job_id"),
                    scraped_at=datetime.now(),
                    job_description=json.dumps(job_data)
                )
                db.add(db_job)
            
            db.commit()
            logger.info(f"Saved {len(jobs)} jobs from Greenhouse for company {company_id}")
    except Exception as e:
        logger.error(f"Greenhouse scraper error: {e}")


# Resume endpoints
@router.post("/resume", response_model=ResumeResponse)
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


@router.get("/resume", response_model=Optional[ResumeResponse])
async def get_resume(db: Session = Depends(get_db)):
    """Get user's resume"""
    resume = db.query(Resume).first()
    return resume


# AI Parsing & Matching Endpoints
@router.post("/parse-job")
async def parse_job_endpoint(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Parse a job posting with AI
    Extracts structured data from job description
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if not job.raw_jd:
        raise HTTPException(status_code=400, detail="Job has no description to parse")
    
    try:
        parser = get_job_parser()
        parsed = await parser.parse_job_description(
            job_title=job.title,
            job_description=job.raw_jd,
            company_name=None
        )
        
        # Save parsed data to database
        job.parsed_jd = parsed.dict()
        job.parser_version = "v1.0"
        job.parsed_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "success",
            "job_id": str(job.id),
            "parsed_data": parsed.dict(),
            "confidence": parsed.confidence_score
        }
    except Exception as e:
        logger.error(f"Error parsing job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


@router.post("/parse-resume")
async def parse_resume_endpoint(db: Session = Depends(get_db)):
    """
    Parse user's resume with AI
    Extracts structured data from resume text
    """
    resume = db.query(Resume).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")
    
    resume_text = resume.base_resume.get("text") or resume.base_resume.get("content", "")
    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume has no text content")
    
    try:
        parser = get_resume_parser()
        parsed = await parser.parse_resume(resume_text)
        
        # Store parsed resume data for reuse
        resume.base_resume["parsed"] = parsed.dict()
        resume.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "success",
            "parsed_data": parsed.dict(),
            "confidence": parsed.confidence_score
        }
    except Exception as e:
        logger.error(f"Error parsing resume: {e}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


@router.post("/parse-resume-text")
async def parse_resume_text(request: dict):
    """
    Parse resume text directly (without needing it in database first)
    Used for preview before saving
    """
    resume_text = request.get("resume_text", "").strip()
    if not resume_text:
        raise HTTPException(status_code=400, detail="resume_text is required")
    
    try:
        parser = get_resume_parser()
        parsed = await parser.parse_resume(resume_text)
        
        return {
            "status": "success",
            "parsed_data": parsed.dict(),
            "confidence": parsed.confidence_score
        }
    except Exception as e:
        logger.error(f"Error parsing resume text: {e}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


@router.get("/matches")
async def get_job_matches(db: Session = Depends(get_db)):
    """
    Get all jobs ranked by match to user's resume
    Shows best matches first
    """
    # Get user's resume
    resume = db.query(Resume).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")
    
    # Parse resume if not already parsed
    if "parsed" not in resume.base_resume:
        parser = get_resume_parser()
        resume_text = resume.base_resume.get("text") or resume.base_resume.get("content", "")
        if resume_text:
            parsed_resume_data = await parser.parse_resume(resume_text)
            resume.base_resume["parsed"] = parsed_resume_data.dict()
        else:
            raise HTTPException(status_code=400, detail="Resume has no text content")
    else:
        parsed_resume_data = ParsedResumeData(**resume.base_resume["parsed"])
    
    # Get all new jobs
    jobs = db.query(Job).filter(Job.status == "new").all()
    
    matches = []
    matcher = get_job_matcher()
    
    for job in jobs:
        # Parse job if not already parsed
        if not job.parsed_jd:
            if job.raw_jd:
                parser = get_job_parser()
                try:
                    parsed_job_data = await parser.parse_job_description(
                        job_title=job.title,
                        job_description=job.raw_jd
                    )
                    job.parsed_jd = parsed_job_data.dict()
                    job.parsed_at = datetime.utcnow()
                except:
                    logger.warning(f"Could not parse job {job.id}")
                    continue
            else:
                continue
        
        # Calculate match
        parsed_job_data = ParsedJobData(**job.parsed_jd)
        match_result = matcher.calculate_match(
            parsed_job=parsed_job_data,
            parsed_resume=parsed_resume_data,
            job_title=job.title,
            job_id=str(job.id)
        )
        
        # Update job with match score
        job.match_score = match_result.match_score
        
        matches.append(match_result)
    
    db.commit()
    
    # Sort by match score descending
    matches.sort(key=lambda x: x.match_score, reverse=True)
    
    return {
        "total_jobs": len(matches),
        "matches": matches,
        "top_matches": matches[:5] if len(matches) > 5 else matches
    }


@router.get("/job/{job_id}/analysis")
async def analyze_job_match(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Detailed analysis of why a job is/isn't a match
    """
    # Get job
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get user's resume
    resume = db.query(Resume).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")
    
    # Parse job if needed
    if not job.parsed_jd or not job.raw_jd:
        raise HTTPException(status_code=400, detail="Job not fully parsed")
    
    # Parse resume if needed
    if "parsed" not in resume.base_resume:
        raise HTTPException(status_code=400, detail="Resume not parsed")
    
    # Get parsed data
    parsed_job_data = ParsedJobData(**job.parsed_jd)
    parsed_resume_data = ParsedResumeData(**resume.base_resume["parsed"])
    
    # Calculate detailed match
    matcher = get_job_matcher()
    match_result = matcher.calculate_match(
        parsed_job=parsed_job_data,
        parsed_resume=parsed_resume_data,
        job_title=job.title,
        job_id=str(job.id)
    )
    
    return {
        "job_id": str(job.id),
        "job_title": job.title,
        "match_analysis": match_result.dict(),
        "parsed_job": parsed_job_data.dict(),
        "recommendation": match_result.recommendation
    }


# IMPORTANT: Generic routes must come LAST to avoid shadowing specific ones like /matches, /stats, etc
@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get job details"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found")
    return job
