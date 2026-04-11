"""Background task implementations for workflow orchestration."""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas, services
from app.config import settings

logger = logging.getLogger(__name__)


async def scrape_jobs_task(
    company_ids: Optional[list[int]] = None,
    db: Optional[Session] = None,
) -> dict:
    """
    Scrape jobs from configured job boards.
    
    Args:
        company_ids: Specific company IDs to scrape. If None, scrape all active companies.
        db: Database session
        
    Returns:
        Task result with status, jobs_found, errors
    """
    if db is None:
        db = next(get_db())
    
    try:
        logger.info(f"Starting job scrape task. Companies: {company_ids or 'all'}")
        
        # Get active companies to scrape
        query = db.query(models.Company)
        if company_ids:
            query = query.filter(models.Company.id.in_(company_ids))
        
        companies = query.filter(models.Company.is_active == True).all()
        
        if not companies:
            logger.warning("No active companies found to scrape")
            return {
                "status": "completed",
                "jobs_found": 0,
                "companies_scraped": 0,
                "errors": [],
            }
        
        total_jobs_found = 0
        errors = []
        
        # Scrape each company
        for company in companies:
            try:
                scraper = services.JobScraper()
                
                # Scrape based on company ATS or search terms
                jobs_data = await scraper.scrape_for_company(
                    search_query=company.search_query or company.name,
                    source="github_jobs",  # Default source
                )
                
                # Save jobs to database
                for job_data in jobs_data:
                    try:
                        job = models.Job(
                            company_id=company.id,
                            title=job_data.get("title"),
                            description=job_data.get("description"),
                            raw_jd=job_data.get("description"),
                            external_job_id=job_data.get("external_id"),
                            external_url=job_data.get("url"),
                            source=job_data.get("source", "github_jobs"),
                            status=models.JobStatus.NEW,
                        )
                        db.add(job)
                        total_jobs_found += 1
                    except Exception as e:
                        logger.error(f"Error saving job from {company.name}: {str(e)}")
                        errors.append(f"Save error for {company.name}: {str(e)}")
                
                db.commit()
                company.last_scraped_at = datetime.utcnow()
                db.commit()
                
                logger.info(f"Scraped {len(jobs_data)} jobs for {company.name}")
                
            except Exception as e:
                logger.error(f"Error scraping {company.name}: {str(e)}")
                errors.append(f"Scrape error for {company.name}: {str(e)}")
        
        logger.info(f"Scrape task completed. Jobs found: {total_jobs_found}")
        
        return {
            "status": "completed",
            "jobs_found": total_jobs_found,
            "companies_scraped": len(companies),
            "errors": errors,
        }
        
    except Exception as e:
        logger.error(f"Fatal error in scrape_jobs_task: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "jobs_found": 0,
            "errors": [str(e)],
        }


async def parse_job_task(
    job_id: int,
    db: Optional[Session] = None,
) -> dict:
    """
    Parse a job description using LLM.
    
    Args:
        job_id: ID of job to parse
        db: Database session
        
    Returns:
        Task result with status, parsed_data
    """
    if db is None:
        db = next(get_db())
    
    try:
        logger.info(f"Parsing job {job_id}")
        
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            return {
                "status": "failed",
                "error": f"Job {job_id} not found",
            }
        
        if not job.raw_jd:
            return {
                "status": "failed",
                "error": f"Job {job_id} has no raw job description",
            }
        
        # Parse job description
        parser = services.JobParser()
        parsed_data = await parser.parse_job_description(job.raw_jd)
        
        # Update job with parsed data
        job.parsed_jd = parsed_data.model_dump()
        job.status = models.JobStatus.PARSED
        
        db.commit()
        logger.info(f"Successfully parsed job {job_id}")
        
        return {
            "status": "completed",
            "job_id": job_id,
            "parsed_data_keys": list(parsed_data.model_dump().keys()),
        }
        
    except Exception as e:
        logger.error(f"Error parsing job {job_id}: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(e),
        }


async def match_job_task(
    job_id: int,
    user_id: int,
    db: Optional[Session] = None,
) -> dict:
    """
    Calculate match score between job and user resume.
    
    Args:
        job_id: ID of job to match
        user_id: ID of user
        db: Database session
        
    Returns:
        Task result with match_score
    """
    if db is None:
        db = next(get_db())
    
    try:
        logger.info(f"Matching job {job_id} for user {user_id}")
        
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job or not job.parsed_jd:
            return {
                "status": "failed",
                "error": "Job not found or not parsed",
            }
        
        # Get user's resume
        resume = db.query(models.Resume).filter(models.Resume.user_id == user_id).first()
        if not resume:
            return {
                "status": "failed",
                "error": f"No resume found for user {user_id}",
            }
        
        # Calculate match score
        matcher = services.JobMatcher()
        match_score, match_details = matcher.match_job_to_resume(job.parsed_jd, resume.parsed_resume)
        
        # Update job
        job.match_score = match_score
        job.match_details = match_details
        job.status = models.JobStatus.MATCHED
        db.commit()
        
        logger.info(f"Job {job_id} matched with score {match_score}")
        
        return {
            "status": "completed",
            "job_id": job_id,
            "match_score": match_score,
        }
        
    except Exception as e:
        logger.error(f"Error matching job {job_id}: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(e),
        }


async def apply_job_task(
    job_id: int,
    user_id: int,
    db: Optional[Session] = None,
) -> dict:
    """
    Apply to a job using the application bot.
    
    Args:
        job_id: ID of job to apply to
        user_id: ID of user
        db: Database session
        
    Returns:
        Task result with application status
    """
    if db is None:
        db = next(get_db())
    
    try:
        logger.info(f"Applying to job {job_id} for user {user_id}")
        
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if not job:
            return {
                "status": "failed",
                "error": f"Job {job_id} not found",
            }
        
        resume = db.query(models.Resume).filter(models.Resume.user_id == user_id).first()
        if not resume:
            return {
                "status": "failed",
                "error": f"No resume found for user {user_id}",
            }
        
        # Apply using application bot
        bot = services.ApplicationBot()
        async with bot.browser as browser:
            result = await bot.apply_to_job(
                job_url=job.external_url,
                candidate_data=resume.get_candidate_data(),
            )
        
        # Create application record
        application = models.Application(
            job_id=job_id,
            user_id=user_id,
            resume_id=resume.id,
            method="auto_apply" if result.success else "manual_needed",
            submitted_at=result.submitted_at if result.success else None,
            screenshot_path=result.screenshot_path,
            notes=result.message,
        )
        db.add(application)
        
        # Update job status
        if result.success:
            job.status = models.JobStatus.APPLIED
        else:
            job.status = models.JobStatus.MANUAL_NEEDED
        
        db.commit()
        logger.info(f"Application result for job {job_id}: {result.success}")
        
        return {
            "status": "completed" if result.success else "partial_failure",
            "job_id": job_id,
            "success": result.success,
            "message": result.message,
            "ats_type": result.ats_type,
        }
        
    except Exception as e:
        logger.error(f"Error applying to job {job_id}: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(e),
        }


async def send_notification_task(
    notification_type: str,
    recipient_email: str,
    subject: str,
    data: dict,
    db: Optional[Session] = None,
) -> dict:
    """
    Send notification email.
    
    Args:
        notification_type: Type of notification (approval_request, application_confirmation, etc)
        recipient_email: Email recipient
        subject: Email subject
        data: Email template data
        db: Database session
        
    Returns:
        Task result with send status
    """
    if db is None:
        db = next(get_db())
    
    try:
        logger.info(f"Sending {notification_type} notification to {recipient_email}")
        
        email_service = services.EmailService()
        result = await email_service.send_email(
            to=recipient_email,
            subject=subject,
            template_type=notification_type,
            template_data=data,
        )
        
        # Log email in database
        email_log = models.EmailLog(
            email_type=notification_type,
            recipient_email=recipient_email,
            subject=subject,
            job_id=data.get("job_id"),
            resend_id=result.get("id"),
            delivery_status="sent",
        )
        db.add(email_log)
        db.commit()
        
        logger.info(f"Notification sent successfully to {recipient_email}")
        
        return {
            "status": "completed",
            "recipient": recipient_email,
            "resend_id": result.get("id"),
        }
        
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "recipient": recipient_email,
            "error": str(e),
        }


async def execute_workflow_task(
    user_id: int,
    mode: str = "approval_required",
    auto_apply_threshold: int = 75,
    db: Optional[Session] = None,
) -> dict:
    """
    Execute complete workflow: scrape → parse → match → decide → apply → notify.
    
    This is the main orchestration task that coordinates all phases.
    
    Args:
        user_id: ID of user
        mode: Approval workflow mode (approval_required, auto_apply, digest)
        auto_apply_threshold: Global auto-apply threshold (0-100)
        db: Database session
        
    Returns:
        Complete workflow result with summary
    """
    if db is None:
        db = next(get_db())
    
    workflow_start = datetime.utcnow()
    workflow_results = {
        "status": "in_progress",
        "user_id": user_id,
        "started_at": workflow_start.isoformat(),
        "phases": {
            "scrape": None,
            "parse": [],
            "match": [],
            "decide": [],
            "apply": [],
            "notify": [],
        },
        "summary": {
            "total_jobs_processed": 0,
            "jobs_scraped": 0,
            "jobs_parsed": 0,
            "jobs_matched": 0,
            "auto_applied": 0,
            "pending_approval": 0,
            "manual_required": 0,
            "errors": [],
        },
    }
    
    try:
        logger.info(f"Starting workflow execution for user {user_id}")
        
        # Phase 1: Scrape jobs
        logger.info("Phase 1: Scraping jobs...")
        scrape_result = await scrape_jobs_task(db=db)
        workflow_results["phases"]["scrape"] = scrape_result
        workflow_results["summary"]["jobs_scraped"] = scrape_result.get("jobs_found", 0)
        
        if scrape_result["status"] == "failed":
            workflow_results["summary"]["errors"].append("Scraping failed")
            # Continue anyway - maybe there are old jobs to process
        
        # Get jobs to process
        jobs_to_process = (
            db.query(models.Job)
            .filter(models.Job.status == models.JobStatus.NEW)
            .limit(50)
            .all()
        )
        
        if not jobs_to_process:
            logger.info("No new jobs to process")
            workflow_results["status"] = "completed"
            workflow_results["summary"]["total_jobs_processed"] = 0
            return workflow_results
        
        logger.info(f"Processing {len(jobs_to_process)} jobs")
        
        # Phase 2: Parse and match jobs
        for job in jobs_to_process:
            try:
                # Parse job
                if not job.parsed_jd:
                    parse_result = await parse_job_task(job.id, db=db)
                    workflow_results["phases"]["parse"].append(parse_result)
                    if parse_result["status"] != "completed":
                        workflow_results["summary"]["errors"].append(
                            f"Parse error for job {job.id}: {parse_result.get('error')}"
                        )
                        continue
                    workflow_results["summary"]["jobs_parsed"] += 1
                
                # Match job
                match_result = await match_job_task(job.id, user_id, db=db)
                workflow_results["phases"]["match"].append(match_result)
                if match_result["status"] == "completed":
                    workflow_results["summary"]["jobs_matched"] += 1
                else:
                    workflow_results["summary"]["errors"].append(
                        f"Match error for job {job.id}: {match_result.get('error')}"
                    )
                    continue
                
                # Phase 3: Decision logic
                match_score = match_result.get("match_score", 0)
                user_settings = (
                    db.query(models.UserSettings)
                    .filter(models.UserSettings.user_id == user_id)
                    .first()
                )
                
                apply_threshold = user_settings.auto_apply_threshold if user_settings else auto_apply_threshold
                
                decision = {
                    "job_id": job.id,
                    "match_score": match_score,
                    "action": None,
                }
                
                if mode == "auto_apply" or match_score >= apply_threshold:
                    decision["action"] = "auto_apply"
                    workflow_results["summary"]["auto_applied"] += 1
                    
                    # Phase 4: Apply
                    apply_result = await apply_job_task(job.id, user_id, db=db)
                    workflow_results["phases"]["apply"].append(apply_result)
                    
                    # Phase 5: Send confirmation email
                    if apply_result["status"] in ["completed", "partial_failure"]:
                        notify_result = await send_notification_task(
                            notification_type="application_confirmation",
                            recipient_email=user_settings.notification_email if user_settings else "",
                            subject=f"Application Submitted: {job.title}",
                            data={
                                "job_id": job.id,
                                "job_title": job.title,
                                "company": job.company.name if job.company else "Unknown",
                                "success": apply_result.get("success", False),
                                "message": apply_result.get("message", ""),
                            },
                            db=db,
                        )
                        workflow_results["phases"]["notify"].append(notify_result)
                
                elif mode == "approval_required" and match_score >= (apply_threshold - 10):
                    decision["action"] = "approval_required"
                    workflow_results["summary"]["pending_approval"] += 1
                    
                    # Send approval request email
                    approval_token = job.approval_token or "temp_token"
                    notify_result = await send_notification_task(
                        notification_type="approval_request",
                        recipient_email=user_settings.notification_email if user_settings else "",
                        subject=f"Job Match Found: {job.title}",
                        data={
                            "job_id": job.id,
                            "job_title": job.title,
                            "company": job.company.name if job.company else "Unknown",
                            "match_score": match_score,
                            "approval_link": f"https://autoapply.app/approve/{approval_token}",
                        },
                        db=db,
                    )
                    workflow_results["phases"]["notify"].append(notify_result)
                
                else:
                    decision["action"] = "skip"
                    job.status = models.JobStatus.SKIPPED
                    db.commit()
                
                workflow_results["phases"]["decide"].append(decision)
                workflow_results["summary"]["total_jobs_processed"] += 1
                
            except Exception as e:
                logger.error(f"Error processing job {job.id}: {str(e)}", exc_info=True)
                workflow_results["summary"]["errors"].append(f"Job {job.id} processing error: {str(e)}")
        
        workflow_results["status"] = "completed"
        workflow_end = datetime.utcnow()
        workflow_results["completed_at"] = workflow_end.isoformat()
        workflow_results["duration_seconds"] = (workflow_end - workflow_start).total_seconds()
        
        logger.info(f"Workflow completed for user {user_id}. Summary: {workflow_results['summary']}")
        
        return workflow_results
        
    except Exception as e:
        logger.error(f"Fatal error in workflow execution: {str(e)}", exc_info=True)
        workflow_results["status"] = "failed"
        workflow_results["summary"]["errors"].append(f"Fatal error: {str(e)}")
        return workflow_results
