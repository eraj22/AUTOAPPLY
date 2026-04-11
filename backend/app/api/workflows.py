"""Workflow API endpoints for orchestrating job automation pipeline."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app import models, schemas
from app.services.workflow_orchestrator import (
    get_orchestrator,
    WorkflowMode,
)

router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
    responses={404: {"description": "Not found"}},
)


@router.post("/execute")
async def execute_workflow(
    user_id: int = Query(..., description="User ID"),
    mode: Optional[str] = Query(
        None,
        description="Workflow mode: auto_apply, approval_required, or digest",
    ),
    auto_apply_threshold: Optional[int] = Query(
        None,
        ge=0,
        le=100,
        description="Auto-apply threshold (0-100)",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Execute complete workflow for a user.
    
    Orchestrates: scrape → parse → match → decide → apply → notify
    
    Query Parameters:
    - user_id: ID of user (required)
    - mode: Workflow mode (auto_apply, approval_required, digest)
    - auto_apply_threshold: Match score threshold for auto-applying (0-100)
    
    Returns:
    - status: completed, failed, or in_progress
    - summary: aggregated results with counters
    - phases: results for each phase (scrape, parse, match, decide, apply, notify)
    - duration_seconds: execution time
    """
    # Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    orchestrator = get_orchestrator()
    result = await orchestrator.execute_workflow(
        user_id=user_id,
        mode=mode,
        auto_apply_threshold=auto_apply_threshold,
    )
    
    return result


@router.post("/execute-all")
async def execute_workflow_all(
    mode: Optional[str] = Query(None, description="Workflow mode for all users"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Execute workflow for all active users.
    
    Query Parameters:
    - mode: Workflow mode to apply to all users (auto_apply, approval_required, digest)
    
    Returns:
    - status: completed or failed
    - total_users: number of active users
    - users_executed: successful executions
    - users_failed: failed executions
    - total_jobs_processed: aggregate job count
    - user_results: detailed results per user
    """
    orchestrator = get_orchestrator()
    result = await orchestrator.execute_workflow_for_users(mode=mode)
    
    return result


@router.post("/scrape")
async def run_scraping(
    company_ids: Optional[list[int]] = Query(
        None,
        description="Specific company IDs to scrape. If omitted, scrape all active companies.",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Run only the scraping phase.
    
    Query Parameters:
    - company_ids: Optional list of company IDs to scrape
    
    Returns:
    - status: completed or failed
    - jobs_found: number of new jobs discovered
    - companies_scraped: number of companies processed
    - errors: list of any errors encountered
    """
    orchestrator = get_orchestrator()
    result = await orchestrator.run_scraping_phase(company_ids=company_ids)
    
    return result


@router.post("/parse")
async def run_parsing(
    job_ids: Optional[list[int]] = Query(
        None,
        description="Specific job IDs to parse. If omitted, parse all unparsed jobs.",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Run only the parsing phase.
    
    Extracts structured data from raw job descriptions using LLM.
    
    Query Parameters:
    - job_ids: Optional list of job IDs to parse
    
    Returns:
    - status: completed or failed
    - jobs_parsed: successfully parsed
    - jobs_skipped: already parsed
    - errors: parsing errors
    """
    orchestrator = get_orchestrator()
    result = await orchestrator.run_parsing_phase(job_ids=job_ids)
    
    return result


@router.post("/match")
async def run_matching(
    user_id: int = Query(..., description="User ID"),
    job_ids: Optional[list[int]] = Query(
        None,
        description="Specific job IDs to match. If omitted, match all parsed jobs.",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Run only the matching phase.
    
    Calculates match scores between jobs and user resume.
    
    Query Parameters:
    - user_id: ID of user (required)
    - job_ids: Optional list of job IDs to match
    
    Returns:
    - status: completed or failed
    - jobs_matched: successfully matched
    - top_matches: top 5 matching jobs with scores
    - errors: matching errors
    """
    orchestrator = get_orchestrator()
    result = await orchestrator.run_matching_phase(user_id=user_id, job_ids=job_ids)
    
    return result


@router.post("/apply/{job_id}")
async def apply_to_job(
    job_id: int,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Apply to a specific job immediately.
    
    Path Parameters:
    - job_id: Job to apply to
    
    Query Parameters:
    - user_id: User applying (required)
    
    Returns:
    - status: completed, partial_failure, or failed
    - success: whether application was submitted
    - ats_type: detected ATS platform
    - message: status message
    """
    db = next(iter(get_db()))
    
    # Verify job and user exist
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    from app.tasks import background_tasks
    result = await background_tasks.apply_job_task(job_id, user_id, db=db)
    
    return result


@router.get("/status")
async def get_orchestrator_status() -> dict:
    """
    Get current workflow orchestrator status.
    
    Returns:
    - status: IDLE, RUNNING, PAUSED, FAILED, or COMPLETED
    - scheduled_jobs: number of scheduled workflow tasks
    - last_workflow_history: recent workflow executions
    """
    orchestrator = get_orchestrator()
    return orchestrator.get_status()


@router.get("/history/{user_id}")
async def get_workflow_history(
    user_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Get last workflow execution history for a user.
    
    Path Parameters:
    - user_id: User ID
    
    Returns:
    - result: last workflow result with phase details
    - executed_at: timestamp of last execution
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    orchestrator = get_orchestrator()
    history = orchestrator.get_workflow_history(user_id)
    
    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"No workflow history found for user {user_id}",
        )
    
    return history


@router.get("/jobs/pending/{user_id}")
async def get_pending_jobs(
    user_id: int,
    status: Optional[str] = Query(
        None,
        description="Filter by status: NEW, PARSED, MATCHED, PENDING_APPROVAL, etc",
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    """
    Get pending jobs for a user at various workflow stages.
    
    Path Parameters:
    - user_id: User ID
    
    Query Parameters:
    - status: Filter by job status
    - limit: Max results (1-100)
    - offset: Pagination offset
    
    Returns:
    - total: total matching jobs
    - jobs: list of jobs with status and match scores
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    query = db.query(models.Job)
    
    if status:
        try:
            job_status = models.JobStatus[status.upper()]
            query = query.filter(models.Job.status == job_status)
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}",
            )
    
    total = query.count()
    jobs = query.limit(limit).offset(offset).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "jobs": [
            {
                "id": job.id,
                "title": job.title,
                "company": job.company.name if job.company else None,
                "status": job.status.value,
                "match_score": job.match_score,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }
            for job in jobs
        ],
    }


@router.post("/resume/update/{user_id}")
async def trigger_resume_rematching(
    user_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Trigger re-matching of all existing jobs against updated resume.
    
    Use this after updating your resume to recalculate match scores.
    
    Path Parameters:
    - user_id: User ID
    
    Returns:
    - status: completed or failed
    - jobs_rematched: number of jobs with recalculated scores
    - top_new_matches: newly discovered high-match jobs
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    orchestrator = get_orchestrator()
    result = await orchestrator.run_matching_phase(user_id=user_id)
    
    return {
        "status": result.get("status"),
        "jobs_rematched": result.get("jobs_matched", 0),
        "top_new_matches": result.get("top_matches", []),
    }


@router.get("/metrics")
async def get_workflow_metrics(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Get workflow execution metrics and statistics.
    
    Query Parameters:
    - user_id: Optional user ID to filter metrics
    
    Returns:
    - total_jobs_scraped: lifetime count
    - total_applications: submitted
    - auto_applied_count: auto-submitted applications
    - approval_required_count: pending user action
    - average_match_score: aggregate stat
    - top_companies: companies with most applications
    """
    if user_id:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    # Calculate metrics
    jobs_query = db.query(models.Job)
    if user_id:
        jobs_query = jobs_query.filter(models.Job.user_id == user_id)
    
    applications_query = db.query(models.Application)
    if user_id:
        applications_query = applications_query.filter(
            models.Application.job.has(user_id=user_id)
        )
    
    total_jobs_scraped = jobs_query.count()
    total_applications = applications_query.count()
    auto_applied = applications_query.filter(
        models.Application.method == "auto_apply"
    ).count()
    
    # Average match score
    avg_match = db.query(models.Job.match_score).filter(
        models.Job.match_score.isnot(None)
    )
    if user_id:
        avg_match = avg_match.filter(models.Job.user_id == user_id)
    
    avg_match_score = 0
    if total_jobs_scraped > 0:
        match_result = db.query(
            db.func.avg(models.Job.match_score)
        ).filter(models.Job.match_score.isnot(None))
        if user_id:
            match_result = match_result.filter(models.Job.user_id == user_id)
        
        avg_match_score = float(match_result.scalar() or 0)
    
    return {
        "total_jobs_scraped": total_jobs_scraped,
        "total_applications": total_applications,
        "auto_applied_count": auto_applied,
        "manual_approved_count": total_applications - auto_applied,
        "average_match_score": round(avg_match_score, 1),
        "scope": "single_user" if user_id else "all_users",
    }
