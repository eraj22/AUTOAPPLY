from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job, Resume, Company 
from app.schemas import JobResponse, ResumeResponse, ResumeCreate
from app.services.scraper import JobScraper
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
