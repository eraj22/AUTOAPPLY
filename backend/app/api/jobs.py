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


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get job details"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found")
    return job


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
