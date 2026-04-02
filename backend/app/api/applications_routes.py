from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Application, Job, Resume
from app.schemas import ApplicationResponse
from typing import List
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=List[ApplicationResponse])
async def list_applications(db: Session = Depends(get_db)):
    """Get all applications"""
    applications = db.query(Application).order_by(Application.created_at.desc()).all()
    return applications


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(application_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get single application by ID"""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.post("/apply/{job_id}")
async def apply_to_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Apply to a job
    Creates an Application record and marks job as applied
    """
    # Get the job
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if already applied
    existing_app = db.query(Application).filter(Application.job_id == job_id).first()
    if existing_app:
        raise HTTPException(status_code=400, detail="Already applied to this job")
    
    # Get the current resume
    resume = db.query(Resume).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No resume found")
    
    try:
        # Create application record
        application = Application(
            job_id=job_id,
            resume_path=None,  # Not storing file path yet
            method="auto",  # Mark as auto-applied
            submitted_at=datetime.utcnow(),
            notes=f"Applied at {datetime.utcnow().isoformat()}"
        )
        db.add(application)
        
        # Update job status to "applied"
        job.status = "applied"
        job.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(application)
        
        logger.info(f"Application created for job {job_id} - Application ID: {application.id}")
        
        return {
            "status": "success",
            "message": f"Successfully applied to {job.title}",
            "application_id": str(application.id),
            "applied_at": application.submitted_at
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error applying to job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to apply: {str(e)}")


@router.delete("/{application_id}")
async def withdraw_application(application_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Withdraw an application
    Removes application record and resets job status to "new"
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    try:
        job_id = application.job_id
        job = db.query(Job).filter(Job.id == job_id).first()
        
        # Delete application
        db.delete(application)
        
        # Reset job status
        if job:
            job.status = "new"
            job.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Application {application_id} withdrawn")
        
        return {
            "status": "success",
            "message": "Application withdrawn"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error withdrawing application: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to withdraw: {str(e)}")


@router.get("/stats/summary")
async def get_application_stats(db: Session = Depends(get_db)):
    """Get application statistics"""
    stats = {
        "total_applications": db.query(func.count(Application.id)).scalar() or 0,
        "applied_by_method": {
            "auto": db.query(func.count(Application.id)).filter(
                Application.method == "auto"
            ).scalar() or 0,
            "manual": db.query(func.count(Application.id)).filter(
                Application.method == "manual"
            ).scalar() or 0,
            "approved": db.query(func.count(Application.id)).filter(
                Application.method == "approved"
            ).scalar() or 0,
        },
        "applied_jobs": db.query(func.count(Job.id)).filter(
            Job.status == "applied"
        ).scalar() or 0,
    }
    return stats
