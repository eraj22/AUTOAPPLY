from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job, Resume, Company, JobStatus, Application
from app.schemas import JobResponse, ResumeResponse, ResumeCreate
from app.services.scraper import JobScraper
from app.services.job_parser import get_job_parser, ParsedJobData
from app.services.resume_parser import get_resume_parser, ParsedResumeData
from app.services.job_matcher import get_job_matcher, JobMatchResult
from app.services.cover_letter_generator import get_cover_letter_generator
from app.services.email_service import send_approval_email, send_auto_applied_email, send_application_confirmed_email, send_manual_required_email, send_daily_digest_email
from app.config import get_settings
from typing import List, Optional
import uuid
import logging
from datetime import datetime
import json
import jwt

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


@router.post("/generate-cover-letter/{job_id}")
async def generate_cover_letter(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Generate a personalized cover letter for a job application
    Uses AI to create a cover letter based on resume and job description
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
    if not job.parsed_jd and not job.raw_jd:
        raise HTTPException(status_code=400, detail="Job has no description")
    
    # Parse job if not already parsed
    try:
        if not job.parsed_jd:
            parser = get_job_parser()
            parsed_job_data = await parser.parse_job_description(
                job_title=job.title,
                job_description=job.raw_jd
            )
            job.parsed_jd = parsed_job_data.dict()
        else:
            parsed_job_data = ParsedJobData(**job.parsed_jd)
    except Exception as e:
        logger.warning(f"Could not parse job {job_id}: {e}")
        parsed_job_data = ParsedJobData()
    
    # Parse resume if needed
    try:
        if "parsed" not in resume.base_resume:
            resume_text = resume.base_resume.get("text") or resume.base_resume.get("content", "")
            if resume_text:
                parser = get_resume_parser()
                parsed_resume_data = await parser.parse_resume(resume_text)
                resume.base_resume["parsed"] = parsed_resume_data.dict()
            else:
                parsed_resume_data = ParsedResumeData()
        else:
            parsed_resume_data = ParsedResumeData(**resume.base_resume["parsed"])
    except Exception as e:
        logger.warning(f"Could not parse resume: {e}")
        parsed_resume_data = ParsedResumeData()
    
    # Generate cover letter
    try:
        generator = get_cover_letter_generator()
        
        # Get company name safely
        company_name = "Company"
        if job.company:
            company_name = job.company.name
        elif job.company_id:
            # Try to fetch company if not loaded
            company = db.query(Company).filter(Company.id == job.company_id).first()
            if company:
                company_name = company.name
        
        cover_letter = await generator.generate_cover_letter(
            resume_data=parsed_resume_data.dict(),
            job_data=parsed_job_data.dict(),
            job_title=job.title,
            company_name=company_name
        )
        
        logger.info(f"Generated cover letter for job {job_id}")
        
        return {
            "status": "success",
            "job_id": str(job.id),
            "job_title": job.title,
            "cover_letter": cover_letter
        }
    except Exception as e:
        logger.error(f"Error generating cover letter for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate cover letter: {str(e)}")


@router.post("/optimize-resume/{job_id}")
async def analyze_resume_for_optimization(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Analyze resume against a job and suggest keywords to improve ATS score
    Returns missing skills and estimated score improvement
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
    try:
        if not job.parsed_jd:
            parser = get_job_parser()
            parsed_job_data = await parser.parse_job_description(
                job_title=job.title,
                job_description=job.raw_jd
            )
            job.parsed_jd = parsed_job_data.dict()
        else:
            parsed_job_data = ParsedJobData(**job.parsed_jd)
    except Exception as e:
        logger.warning(f"Could not parse job with AI: {e}")
        # Fallback: extract skills manually from raw text
        parsed_job_data = _extract_skills_from_raw_text(job.raw_jd, job.title)
    
    # If still no required skills, try manual extraction
    if not parsed_job_data.required_skills and job.raw_jd:
        parsed_job_data = _extract_skills_from_raw_text(job.raw_jd, job.title)
    
    # Parse resume if needed
    try:
        if "parsed" not in resume.base_resume:
            resume_text = resume.base_resume.get("text") or resume.base_resume.get("content", "")
            if resume_text:
                parser = get_resume_parser()
                parsed_resume_data = await parser.parse_resume(resume_text)
                resume.base_resume["parsed"] = parsed_resume_data.dict()
            else:
                parsed_resume_data = ParsedResumeData()
        else:
            parsed_resume_data = ParsedResumeData(**resume.base_resume["parsed"])
    except Exception as e:
        logger.warning(f"Could not parse resume: {e}")
        parsed_resume_data = ParsedResumeData()
    
    # Calculate current match score
    matcher = get_job_matcher()
    current_match = matcher.calculate_match(
        parsed_job=parsed_job_data,
        parsed_resume=parsed_resume_data,
        job_title=job.title,
        job_id=str(job.id)
    )
    
    # Extract missing skills (required but not in resume)
    resume_skills = set(skill.lower() for skill in parsed_resume_data.all_skills or [])
    required_skills = set(skill.lower() for skill in parsed_job_data.required_skills or [])
    missing_skills = list(required_skills - resume_skills)
    
    # Calculate potential score improvement
    # If user adds all missing skills, estimate new score
    simulated_resume = parsed_resume_data.dict()
    simulated_resume["all_skills"] = list(set(simulated_resume.get("all_skills", []) or []) | required_skills)
    simulated_resume_data = ParsedResumeData(**simulated_resume)
    
    improved_match = matcher.calculate_match(
        parsed_job=parsed_job_data,
        parsed_resume=simulated_resume_data,
        job_title=job.title,
        job_id=str(job.id)
    )
    
    score_improvement = improved_match.match_score - current_match.match_score
    
    logger.info(f"Resume optimization analysis for job {job_id}: {len(missing_skills)} missing skills, {score_improvement:.1f}pt potential improvement")
    
    return {
        "status": "success",
        "job_id": str(job.id),
        "job_title": job.title,
        "current_score": current_match.match_score,
        "potential_score": improved_match.match_score,
        "score_improvement": score_improvement,
        "missing_required_skills": missing_skills,
        "nice_to_have_skills": [s.lower() for s in (parsed_job_data.nice_to_have_skills or []) if s.lower() not in resume_skills][:5],
        "total_missing": len(missing_skills)
    }


def _extract_skills_from_raw_text(raw_text: str, job_title: str = "") -> ParsedJobData:
    """
    Fallback skill extraction from raw job text using keyword matching
    """
    common_skills = {
        # Languages
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "ruby", "php", "scala", "kotlin", "swift", "objective-c", "sql",
        
        # Frameworks & Libraries
        "react", "vue", "angular", "fastapi", "django", "flask", "spring",
        "nodejs", "node.js", "express", "rails", "laravel", "asp.net",
        "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
        
        # Databases
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra",
        "dynamodb", "sqlite", "oracle", "sql server",
        
        # DevOps & Cloud
        "docker", "kubernetes", "aws", "gcp", "azure", "terraform", "ansible",
        "jenkins", "gitlab", "github", "ci/cd", "kubernetes", "linux",
        
        # Data & Analytics
        "hadoop", "spark", "kafka", "airflow", "etl", "data warehouse",
        "tableau", "power bi", "looker", "datadog", "splunk",
        
        # Testing & QA
        "junit", "pytest", "selenium", "jest", "cypress", "mockito",
        
        # Tools & Concepts
        "rest", "graphql", "microservices", "agile", "scrum", "jira",
        "git", "svn", "api", "xml", "json", "html", "css", "sass",
        "webpack", "docker compose", "grpc", "soap", "websockets",
        
        # Methodologies
        "tdd", "bdd", "ddd", "oop", "functional programming",
        "design patterns", "system design", "architecture",
    }
    
    text_lower = raw_text.lower()
    extracted_skills = []
    
    # Find skills mentioned in text
    for skill in common_skills:
        if skill in text_lower:
            extracted_skills.append(skill)
    
    # Infer some skills from job title
    title_lower = job_title.lower() if job_title else ""
    if "senior" in title_lower or "lead" in title_lower:
        extracted_skills.extend(["system design", "architecture", "mentoring"])
    if "devops" in title_lower:
        extracted_skills.extend(["docker", "kubernetes", "ci/cd"])
    if "data" in title_lower:
        extracted_skills.extend(["sql", "data analysis", "statistics"])
    if "frontend" in title_lower:
        extracted_skills.extend(["react", "javascript", "html", "css"])
    if "mobile" in title_lower:
        extracted_skills.extend(["ios", "android", "react native"])
    
    # Remove duplicates and sort
    extracted_skills = list(set(extracted_skills))
    extracted_skills.sort()
    
    logger.info(f"Extracted {len(extracted_skills)} skills from raw job text")
    
    # Return ParsedJobData with extracted skills
    return ParsedJobData(
        required_skills=extracted_skills[:10],  # Top 10 skills
        nice_to_have_skills=extracted_skills[10:15] if len(extracted_skills) > 10 else [],
        confidence_score=0.6  # Lower confidence for manual extraction
    )


@router.put("/resume")
async def update_resume(request: dict, db: Session = Depends(get_db)):
    """
    Update user's resume with new keywords/skills
    Adds skills to the resume while preserving all other content
    """
    # Get user's resume
    resume = db.query(Resume).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")
    
    try:
        # Extract new skills to add
        new_skills = request.get("skills_to_add", [])
        if not isinstance(new_skills, list):
            new_skills = [new_skills]
        
        # Get current parsed data
        if "parsed" in resume.base_resume:
            parsed_data = resume.base_resume["parsed"]
        else:
            # Parse if not already parsed
            resume_text = resume.base_resume.get("text") or resume.base_resume.get("content", "")
            if resume_text:
                parser = get_resume_parser()
                parsed = await parser.parse_resume(resume_text)
                parsed_data = parsed.dict()
            else:
                parsed_data = {}
        
        # Add new skills to all_skills (avoiding duplicates)
        current_skills = set(skill.lower() for skill in (parsed_data.get("all_skills", []) or []))
        current_skills.update(skill.lower() for skill in new_skills)
        parsed_data["all_skills"] = list(current_skills)
        
        # Update resume with new parsed data
        resume.base_resume["parsed"] = parsed_data
        resume.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(resume)
        
        logger.info(f"Resume updated with {len(new_skills)} new skills")
        
        return {
            "status": "success",
            "message": f"Resume updated with {len(new_skills)} new skills",
            "updated_skills": list(new_skills),
            "total_skills": len(parsed_data.get("all_skills", []))
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating resume: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update resume: {str(e)}")


@router.get("/approve")
async def approve_job_application(token: str = Query(...), db: Session = Depends(get_db)):
    """
    Approve a job application via email link
    Validates JWT token and marks job for application
    
    Args:
        token: Signed JWT token containing job_id and action
        
    Returns:
        Status message
    """
    settings = get_settings()
    try:
        # Decode JWT token
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        job_id = uuid.UUID(payload.get("job_id"))
        action = payload.get("action")  # Should be "approve"
        
        if action != "approve":
            raise HTTPException(status_code=400, detail="Invalid action in token")
        
        # Get job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Mark job for application
        job.status = JobStatus.APPLYING.value
        job.approval_token = None  # Clear used token
        job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
        
        logger.info(f"Job {job_id} approved for application")
        
        # TODO: Queue application bot task (Celery) to submit application
        
        return {
            "status": "approved",
            "message": f"Application for {job.title} at {job.company_id} initiating",
            "job_id": str(job.id)
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Approval link has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=400, detail="Invalid approval link")
    except Exception as e:
        logger.error(f"Error approving job: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve application")


@router.get("/skip")
async def skip_job(token: str = Query(...), db: Session = Depends(get_db)):
    """
    Skip a job application via email link
    Validates JWT token and marks job as skipped
    
    Args:
        token: Signed JWT token containing job_id and action
        
    Returns:
        Status message
    """
    settings = get_settings()
    try:
        # Decode JWT token
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        job_id = uuid.UUID(payload.get("job_id"))
        action = payload.get("action")  # Should be "skip"
        
        if action != "skip":
            raise HTTPException(status_code=400, detail="Invalid action in token")
        
        # Get job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Mark job as skipped
        job.status = JobStatus.SKIPPED.value
        job.approval_token = None  # Clear used token
        job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
        
        logger.info(f"Job {job_id} skipped by user")
        
        return {
            "status": "skipped",
            "message": f"Job {job.title} at {job.company_id} skipped",
            "job_id": str(job.id)
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Skip link has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=400, detail="Invalid skip link")
    except Exception as e:
        logger.error(f"Error skipping job: {e}")
        raise HTTPException(status_code=500, detail="Failed to skip job")


# ======================== TEST ENDPOINTS (Phase 4) ========================
# These are temporary endpoints for testing email functionality
# Remove in production or gatekeeper behind admin auth

@router.post("/test-approval-email")
async def test_send_approval_email(request: dict, db: Session = Depends(get_db)):
    """
    TEST ENDPOINT: Send a sample approval email
    For testing email integration during development
    """
    try:
        to_email = request.get("to_email")
        job_id = request.get("job_id")
        company_name = request.get("company_name", "Test Company")
        job_title = request.get("job_title", "Test Job")
        fit_score = request.get("fit_score", 85)
        match_summary = request.get("match_summary", "Great match for your profile")
        
        # Generate approval and skip URLs with JWT tokens
        settings = get_settings()
        approve_token = jwt.encode(
            {"job_id": str(job_id), "action": "approve"},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        skip_token = jwt.encode(
            {"job_id": str(job_id), "action": "skip"},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        approve_url = f"{settings.app_base_url}/approve?token={approve_token}"
        skip_url = f"{settings.app_base_url}/skip?token={skip_token}"
        preview_resume_url = f"{settings.app_base_url}/resume/preview"
        pause_url = f"{settings.app_base_url}/pause-notifications"
        
        result = await send_approval_email(
            to_email=to_email,
            job_title=job_title,
            company_name=company_name,
            fit_score=fit_score,
            match_summary=match_summary,
            approval_url=approve_url,
            skip_url=skip_url,
            preview_resume_url=preview_resume_url,
            pause_url=pause_url,
            job_id=job_id,
            db=db
        )
        
        return {
            "status": "sent" if result["success"] else "failed",
            "message": f"Approval email {'sent to' if result['success'] else 'failed to send to'} {to_email}",
            "resend_id": result.get("resend_id"),
            "error": result.get("error")
        }
    except Exception as e:
        logger.error(f"Error in test approval email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-auto-apply-email")
async def test_send_auto_apply_email(request: dict, db: Session = Depends(get_db)):
    """
    TEST ENDPOINT: Send a sample auto-applied email
    """
    try:
        to_email = request.get("to_email")
        job_id = request.get("job_id")
        company_name = request.get("company_name", "Test Company")
        job_title = request.get("job_title", "Test Job")
        fit_score = request.get("fit_score", 90)
        
        settings = get_settings()
        resume_link = f"{settings.app_base_url}/resume"
        dashboard_link = f"{settings.app_base_url}/dashboard"
        withdraw_token = jwt.encode(
            {"job_id": str(job_id), "action": "withdraw"},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        withdraw_url = f"{settings.app_base_url}/withdraw?token={withdraw_token}"
        
        result = await send_auto_applied_email(
            to_email=to_email,
            job_title=job_title,
            company_name=company_name,
            fit_score=fit_score,
            submitted_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            resume_link=resume_link,
            dashboard_link=dashboard_link,
            withdraw_url=withdraw_url,
            job_id=job_id,
            db=db
        )
        
        return {
            "status": "sent" if result["success"] else "failed",
            "message": f"Auto-applied email {'sent to' if result['success'] else 'failed to send to'} {to_email}",
            "resend_id": result.get("resend_id"),
            "error": result.get("error")
        }
    except Exception as e:
        logger.error(f"Error in test auto-apply email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-confirmation-email")
async def test_send_confirmation_email(request: dict, db: Session = Depends(get_db)):
    """
    TEST ENDPOINT: Send a sample application confirmed email
    """
    try:
        to_email = request.get("to_email")
        job_id = request.get("job_id")
        company_name = request.get("company_name", "Test Company")
        job_title = request.get("job_title", "Test Job")
        fit_score = request.get("fit_score", 88)
        avg_response_days = request.get("avg_response_days", 10)
        
        settings = get_settings()
        resume_link = f"{settings.app_base_url}/resume"
        dashboard_link = f"{settings.app_base_url}/dashboard"
        
        result = await send_application_confirmed_email(
            to_email=to_email,
            job_title=job_title,
            company_name=company_name,
            fit_score=fit_score,
            avg_response_days=avg_response_days,
            resume_link=resume_link,
            dashboard_link=dashboard_link,
            job_id=job_id,
            db=db
        )
        
        return {
            "status": "sent" if result["success"] else "failed",
            "message": f"Confirmation email {'sent to' if result['success'] else 'failed to send to'} {to_email}",
            "resend_id": result.get("resend_id"),
            "error": result.get("error")
        }
    except Exception as e:
        logger.error(f"Error in test confirmation email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-manual-email")
async def test_send_manual_email(request: dict, db: Session = Depends(get_db)):
    """
    TEST ENDPOINT: Send a sample manual action required email
    """
    try:
        to_email = request.get("to_email")
        job_id = request.get("job_id")
        company_name = request.get("company_name", "Test Company")
        job_title = request.get("job_title", "Test Job")
        issue_description = request.get("issue_description", "Form submission required manual interaction")
        
        settings = get_settings()
        job_url = f"https://example.com/jobs/test"
        dashboard_link = f"{settings.app_base_url}/dashboard"
        
        result = await send_manual_required_email(
            to_email=to_email,
            job_title=job_title,
            company_name=company_name,
            issue_description=issue_description,
            job_url=job_url,
            dashboard_link=dashboard_link,
            job_id=job_id,
            db=db
        )
        
        return {
            "status": "sent" if result["success"] else "failed",
            "message": f"Manual required email {'sent to' if result['success'] else 'failed to send to'} {to_email}",
            "resend_id": result.get("resend_id"),
            "error": result.get("error")
        }
    except Exception as e:
        logger.error(f"Error in test manual email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-digest-email")
async def test_send_digest_email(request: dict, db: Session = Depends(get_db)):
    """
    TEST ENDPOINT: Send a sample daily digest email
    """
    try:
        to_email = request.get("to_email")
        
        settings = get_settings()
        dashboard_link = f"{settings.app_base_url}/dashboard"
        unsubscribe_link = f"{settings.app_base_url}/unsubscribe"
        
        result = await send_daily_digest_email(
            to_email=to_email,
            digest_date=datetime.utcnow().strftime("%B %d, %Y"),
            jobs_found=5,
            applications_submitted=2,
            pending_approval=1,
            new_jobs=[
                {"title": "Senior Backend Engineer", "company": "TechCorp", "location": "Remote", "fit_score": 92},
                {"title": "Full Stack Developer", "company": "StartupXYZ", "location": "San Francisco", "fit_score": 87},
            ],
            applications=[
                {"title": "Backend Engineer", "company": "Google", "submitted_at": "Today at 2:30 PM"},
            ],
            pending_jobs=[
                {"title": "DevOps Engineer", "company": "Meta", "approval_link": f"{settings.app_base_url}/approve"},
            ],
            dashboard_link=dashboard_link,
            unsubscribe_link=unsubscribe_link,
            db=db
        )
        
        return {
            "status": "sent" if result["success"] else "failed",
            "message": f"Digest email {'sent to' if result['success'] else 'failed to send to'} {to_email}",
            "resend_id": result.get("resend_id"),
            "error": result.get("error")
        }
    except Exception as e:
        logger.error(f"Error in test digest email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ======================== END TEST ENDPOINTS ========================


# IMPORTANT: Generic routes must come LAST to avoid shadowing specific ones like /matches, /stats, etc
@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get job details"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found")
    return job
