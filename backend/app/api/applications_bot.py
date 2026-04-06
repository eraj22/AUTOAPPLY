"""
Applications API endpoints
Handles job applications with approval workflow and auto-apply
"""

from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job, Application, JobStatus, UserSettings, Resume
from app.services.application_bot import ApplicationBot, ApplicationResult
from app.services.job_matcher import get_job_matcher
from app.services.job_parser import get_job_parser
from app.services.resume_parser import get_resume_parser
from app.services.cover_letter_generator import get_cover_letter_generator
from app.services.email_service import send_approval_email, send_manual_required_email, send_application_confirmed_email
from typing import List, Optional
import uuid
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["applications"])


class ApplicationResponse:
    """Response model for applications"""
    pass


@router.get("")
async def list_applications(
    job_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get applications (optionally filtered by job or status)
    
    Args:
        job_id: Filter by job ID
        status: Filter by application status (submitted, approved, rejected, etc.)
        limit: Maximum results to return
    
    Returns:
        List of applications
    """
    query = db.query(Application).order_by(Application.created_at.desc()).limit(limit)
    
    if job_id:
        query = query.filter(Application.job_id == job_id)
    if status:
        query = query.filter(Application.method == status)
    
    applications = query.all()
    
    return [
        {
            "id": str(app.id),
            "job_id": str(app.job_id),
            "submitted_at": app.submitted_at,
            "method": app.method,
            "status": db.query(Job).filter(Job.id == app.job_id).first().status if app.job_id else None,
            "created_at": app.created_at,
            "updated_at": app.updated_at,
        }
        for app in applications
    ]


@router.post("/{job_id}/apply")
async def apply_to_job(
    job_id: uuid.UUID,
    require_approval: bool = Query(True, description="Send approval token first"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Request to apply to a job
    
    If require_approval=True: Send approval token to user
    If require_approval=False: Apply immediately (requires global auto-apply enabled)
    
    Args:
        job_id: Job to apply to
        require_approval: Whether to require user approval first
    
    Returns:
        Application status
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.raw_jd is None:
        raise HTTPException(status_code=400, detail="Job description not parsed yet")
    
    # Get user settings
    settings = db.query(UserSettings).first()
    if not settings:
        raise HTTPException(status_code=400, detail="User settings not configured")
    
    # Parse job if not already done
    if not job.parsed_jd:
        try:
            parser = get_job_parser()
            parsed = await parser.parse_job_description(
                job_title=job.title,
                job_description=job.raw_jd,
                company_name=None
            )
            job.parsed_jd = parsed.dict()
            job.parsed_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            logger.warning(f"Could not parse job {job_id}: {e}")
    
    # Calculate match score
    try:
        resume = db.query(Resume).first()
        if not resume:
            raise HTTPException(status_code=400, detail="No resume found")
        
        resume_parser = get_resume_parser()
        parsed_resume = await resume_parser.parse_resume(resume.base_resume)
        
        matcher = get_job_matcher()
        match_result = matcher.calculate_match(
            parsed_job=job.parsed_jd or {},
            parsed_resume=parsed_resume,
            job_title=job.title,
            job_id=str(job_id)
        )
        
        job.fit_score = match_result.match_score
        job.parsed_jd = {**(job.parsed_jd or {}), **match_result.dict()}
        db.commit()
    except Exception as e:
        logger.warning(f"Could not calculate match: {e}")
    
    # Check if auto-apply is enabled and score is above threshold
    if (
        not require_approval
        and settings.global_mode == "auto_apply"
        and job.fit_score and job.fit_score >= settings.auto_apply_threshold
    ):
        # Auto-apply immediately
        background_tasks.add_task(
            apply_job_background,
            job_id,
            db,
            auto_apply=True,
            user_email=settings.notification_email
        )
        
        job.status = JobStatus.APPLYING.value
        db.commit()
        
        return {
            "status": "applying",
            "message": "Beginning auto-application",
            "method": "auto",
            "fit_score": job.fit_score
        }
    
    # Send approval email
    if require_approval:
        # Generate approval token
        settings = db.query(UserSettings).first()
        
        background_tasks.add_task(
            send_approval_email,
            recipient=settings.notification_email if settings else "user@example.com",
            job_title=job.title,
            company_name=None,
            job_url=job.url,
            match_score=job.fit_score or 0,
            job_id=str(job_id)
        )
        
        job.status = JobStatus.PENDING_APPROVAL.value
        db.commit()
        
        return {
            "status": "approval_requested",
            "message": "Sent approval request to user email",
            "method": "approval",
            "fit_score": job.fit_score
        }
    
    raise HTTPException(status_code=400, detail="Invalid application configuration")


@router.post("/{job_id}/auto-apply")
async def auto_apply_to_job(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Trigger automatic job application (no user approval)
    
    Args:
        job_id: Job to apply to
    
    Returns:
        Application submission status
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    settings = db.query(UserSettings).first()
    if not settings:
        raise HTTPException(status_code=400, detail="User settings not configured")
    
    if settings.global_mode != "auto_apply":
        raise HTTPException(status_code=403, detail="Auto-apply mode not enabled")
    
    # Queue background task
    background_tasks.add_task(
        apply_job_background,
        job_id,
        db,
        auto_apply=True,
        user_email=settings.notification_email
    )
    
    job.status = JobStatus.APPLYING.value
    db.commit()
    
    return {
        "status": "applying",
        "message": "Starting automated application",
        "job_id": str(job_id),
        "job_url": job.url
    }


@router.post("/{job_id}/apply/approve")
async def approve_application(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    User approves job application
    
    Args:
        job_id: Job to apply to
    
    Returns:
        Application status
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.PENDING_APPROVAL.value:
        raise HTTPException(status_code=400, detail="Job not in pending approval state")
    
    settings = db.query(UserSettings).first()
    
    # Queue background task for application
    background_tasks.add_task(
        apply_job_background,
        job_id,
        db,
        auto_apply=False,
        user_email=settings.notification_email if settings else "user@example.com"
    )
    
    job.status = JobStatus.APPLYING.value
    db.commit()
    
    return {
        "status": "approved",
        "message": "Application approved, beginning submission",
        "job_id": str(job_id),
        "job_url": job.url
    }


@router.post("/{job_id}/apply/skip")
async def skip_application(
    job_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    User skips a job application
    
    Args:
        job_id: Job to skip
    
    Returns:
        Status
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.status = JobStatus.SKIPPED.value
    
    # Create application record
    app = Application(
        job_id=job_id,
        method="skipped",
        submitted_at=datetime.utcnow()
    )
    db.add(app)
    db.commit()
    
    return {
        "status": "skipped",
        "message": "Job skipped",
        "job_id": str(job_id)
    }


@router.get("/{application_id}/status")
async def get_application_status(
    application_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get application status
    
    Args:
        application_id: Application ID
    
    Returns:
        Application status and details
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = db.query(Job).filter(Job.id == app.job_id).first()
    
    return {
        "id": str(app.id),
        "job_id": str(app.job_id),
        "job_title": job.title if job else "Unknown",
        "job_url": job.url if job else None,
        "method": app.method,
        "submitted_at": app.submitted_at,
        "status": job.status if job else "unknown",
        "notes": app.notes,
        "created_at": app.created_at
    }


@router.get("/stats/summary")
async def get_application_stats(db: Session = Depends(get_db)):
    """
    Get application statistics
    
    Returns:
        Stats breakdown
    """
    from sqlalchemy import func
    
    total_apps = db.query(func.count(Application.id)).scalar() or 0
    auto_applied = db.query(func.count(Application.id)).filter(Application.method == "auto").scalar() or 0
    manual_applied = db.query(func.count(Application.id)).filter(Application.method == "manual").scalar() or 0
    approved_apps = db.query(func.count(Application.id)).filter(Application.method == "approved").scalar() or 0
    
    return {
        "total_applications": total_apps,
        "auto_applied": auto_applied,
        "manual_applied": manual_applied,
        "approved": approved_apps,
        "pending": db.query(func.count(Job.id)).filter(Job.status == "pending_approval").scalar() or 0,
    }


# Background task for application submission
async def apply_job_background(
    job_id: uuid.UUID,
    db: Session,
    auto_apply: bool = False,
    user_email: str = ""
):
    """
    Background task: Apply to job
    
    Args:
        job_id: Job to apply to
        db: Database session
        auto_apply: Whether this is auto-apply or manual
        user_email: User's email for notifications
    """
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        resume = db.query(Resume).first()
        if not resume:
            logger.error("No resume found for application")
            job.status = JobStatus.MANUAL_NEEDED.value
            db.commit()
            return
        
        # Prepare candidate data
        candidate_data = {
            "name": resume.base_resume.get("name", ""),
            "email": user_email,
            "phone": resume.base_resume.get("phone", ""),
            "location": resume.base_resume.get("location", ""),
            "linkedin_url": resume.base_resume.get("linkedin", ""),
            "github_url": resume.base_resume.get("github", ""),
            "portfolio_url": resume.base_resume.get("portfolio", ""),
            "years_experience": resume.base_resume.get("years_experience", 5),
        }
        
        # Apply to job
        async with ApplicationBot() as bot:
            result = await bot.apply_to_job(
                job_url=job.url,
                candidate_data=candidate_data,
                resume_path=resume.resume_pdf_path,
                screenshot_dir="/tmp"
            )
        
        # Create application record
        app = Application(
            job_id=job_id,
            resume_path=resume.resume_pdf_path,
            submitted_at=datetime.utcnow() if result.success else None,
            method="auto" if auto_apply else "manual",
            screenshot_path=result.screenshot_path,
            notes=json.dumps({
                "ats": result.ats_type,
                "form_data": result.form_data_captured,
                "errors": result.errors
            })
        )
        db.add(app)
        
        # Update job status
        if result.success:
            job.status = JobStatus.APPLIED.value
            
            # Send confirmation email
            await send_application_confirmed_email(
                recipient=user_email,
                job_title=job.title,
                company_name=None,
                job_url=job.url,
                ats_type=result.ats_type.value if result.ats_type else "unknown"
            )
        else:
            job.status = JobStatus.MANUAL_NEEDED.value
            
            # Send manual required email
            await send_manual_required_email(
                recipient=user_email,
                job_title=job.title,
                company_name=None,
                job_url=job.url,
                reason=result.message
            )
        
        db.commit()
        logger.info(f"Application for job {job_id} completed: {result.success}")
    
    except Exception as e:
        logger.error(f"Error applying to job {job_id}: {e}", exc_info=True)
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED.value
                db.commit()
        except:
            pass
