from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job, Resume
from app.schemas import JobResponse, ResumeResponse, ResumeCreate
from typing import List, Optional
import uuid

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
