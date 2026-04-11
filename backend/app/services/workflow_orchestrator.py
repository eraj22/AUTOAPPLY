"""Workflow orchestrator for coordinating all AutoApply phases."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app import models
from app.tasks import background_tasks
from app.database import get_db

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"


class WorkflowMode(str, Enum):
    """Workflow execution mode."""
    AUTO_APPLY = "auto_apply"
    APPROVAL_REQUIRED = "approval_required"
    DIGEST = "digest"


class WorkflowOrchestrator:
    """
    Orchestrates the complete AutoApply workflow.
    
    Coordinates scraping, parsing, matching, and application submission
    across all jobs and users.
    """
    
    def __init__(self):
        """Initialize workflow orchestrator."""
        self.scheduler = AsyncIOScheduler()
        self._status = WorkflowStatus.IDLE
        self._workflow_history: Dict[int, dict] = {}
        
    async def start(self):
        """Start the workflow scheduler."""
        logger.info("Starting WorkflowOrchestrator")
        self.scheduler.start()
        self._status = WorkflowStatus.RUNNING
        await self._setup_schedules()
        logger.info("WorkflowOrchestrator started successfully")
        
    async def stop(self):
        """Stop the workflow scheduler."""
        logger.info("Stopping WorkflowOrchestrator")
        self.scheduler.shutdown(wait=True)
        self._status = WorkflowStatus.IDLE
        logger.info("WorkflowOrchestrator stopped")
        
    async def _setup_schedules(self):
        """Set up periodic workflow execution schedules."""
        # Get active users and their schedule preferences
        db = next(get_db())
        try:
            users = db.query(models.User).filter(
                models.User.is_active == True
            ).all()
            
            for user in users:
                user_settings = (
                    db.query(models.UserSettings)
                    .filter(models.UserSettings.user_id == user.id)
                    .first()
                )
                if not user_settings or not user_settings.scrape_interval_hours:
                    continue
                
                # Schedule workflow for this user
                trigger = CronTrigger(minute=0, hour=f"*/{user_settings.scrape_interval_hours}")
                job_id = f"workflow_user_{user.id}"
                
                self.scheduler.add_job(
                    self.execute_workflow,
                    trigger,
                    args=[user.id],
                    id=job_id,
                    name=f"Workflow for user {user.id}",
                    replace_existing=True,
                )
                
                logger.info(f"Scheduled workflow for user {user.id} with interval {user_settings.scrape_interval_hours}h")
        
        finally:
            db.close()
        
    def _parse_interval(self, interval: str) -> CronTrigger:
        """
        Parse interval string to CronTrigger.
        
        Supported formats:
        - "hourly": Every hour
        - "6h": Every 6 hours
        - "daily": Every day at midnight
        - "cron: * * * * *": Custom cron expression
        """
        if interval == "hourly":
            return CronTrigger(minute=0)
        elif interval == "daily":
            return CronTrigger(hour=0, minute=0)
        elif interval.endswith("h"):
            hours = int(interval[:-1])
            return CronTrigger(hour=f"*/{hours}", minute=0)
        elif interval.startswith("cron:"):
            cron_expr = interval.replace("cron:", "").strip()
            parts = cron_expr.split()
            return CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
            )
        else:
            # Default to daily
            return CronTrigger(hour=0, minute=0)
        
    async def execute_workflow(
        self,
        user_id: int,
        mode: Optional[str] = None,
        auto_apply_threshold: Optional[int] = None,
    ) -> dict:
        """
        Execute complete workflow for a user.
        
        Args:
            user_id: User ID
            mode: Workflow mode (auto_apply, approval_required, digest)
            auto_apply_threshold: Auto-apply threshold score (0-100)
            
        Returns:
            Workflow execution result
        """
        logger.info(f"Executing workflow for user {user_id}")
        
        try:
            db = next(get_db())
            
            # Get user settings if not provided
            user_settings = None
            if not mode or auto_apply_threshold is None:
                user_settings = (
                    db.query(models.UserSettings)
                    .filter(models.UserSettings.user_id == user_id)
                    .first()
                )
            
            if not mode:
                mode = user_settings.workflow_mode if user_settings else "approval_required"
            
            if auto_apply_threshold is None:
                auto_apply_threshold = user_settings.auto_apply_threshold if user_settings else 75
            
            # Execute workflow
            result = await background_tasks.execute_workflow_task(
                user_id=user_id,
                mode=mode,
                auto_apply_threshold=auto_apply_threshold,
                db=db,
            )
            
            # Store in history
            self._workflow_history[user_id] = {
                "result": result,
                "executed_at": datetime.utcnow().isoformat(),
            }
            
            db.close()
            return result
            
        except Exception as e:
            logger.error(f"Error executing workflow for user {user_id}: {str(e)}", exc_info=True)
            return {
                "status": "failed",
                "user_id": user_id,
                "error": str(e),
            }
        
    async def execute_workflow_for_users(
        self,
        mode: Optional[str] = None,
    ) -> dict:
        """
        Execute workflow for all active users.
        
        Args:
            mode: Workflow mode for all users
            
        Returns:
            Aggregated results for all users
        """
        logger.info("Executing workflow for all active users")
        
        db = next(get_db())
        try:
            users = db.query(models.User).filter(
                models.User.is_active == True
            ).all()
            
            results = {
                "status": "completed",
                "total_users": len(users),
                "users_executed": 0,
                "users_failed": 0,
                "total_jobs_processed": 0,
                "user_results": {},
                "started_at": datetime.utcnow().isoformat(),
            }
            
            # Execute workflow for each user
            for user in users:
                try:
                    result = await self.execute_workflow(
                        user_id=user.id,
                        mode=mode,
                    )
                    
                    results["user_results"][user.id] = result
                    
                    if result["status"] == "completed":
                        results["users_executed"] += 1
                        results["total_jobs_processed"] += result.get("summary", {}).get(
                            "total_jobs_processed", 0
                        )
                    else:
                        results["users_failed"] += 1
                        
                except Exception as e:
                    logger.error(f"Error executing workflow for user {user.id}: {str(e)}")
                    results["users_failed"] += 1
                    results["user_results"][user.id] = {
                        "status": "failed",
                        "error": str(e),
                    }
            
            results["completed_at"] = datetime.utcnow().isoformat()
            return results
            
        finally:
            db.close()
        
    async def run_scraping_phase(
        self,
        company_ids: Optional[list[int]] = None,
    ) -> dict:
        """
        Run only the scraping phase.
        
        Args:
            company_ids: Specific company IDs to scrape
            
        Returns:
            Scraping result
        """
        logger.info(f"Running scraping phase for companies: {company_ids or 'all'}")
        return await background_tasks.scrape_jobs_task(company_ids=company_ids)
        
    async def run_parsing_phase(
        self,
        job_ids: Optional[list[int]] = None,
    ) -> dict:
        """
        Run parsing for unparsed jobs.
        
        Args:
            job_ids: Specific job IDs to parse. If None, parse all NEW jobs.
            
        Returns:
            Parsing results
        """
        logger.info(f"Running parsing phase for jobs: {job_ids or 'all NEW'}")
        
        db = next(get_db())
        try:
            if job_ids:
                jobs = db.query(models.Job).filter(models.Job.id.in_(job_ids)).all()
            else:
                jobs = db.query(models.Job).filter(
                    models.Job.status == models.JobStatus.NEW
                ).limit(50).all()
            
            results = {
                "status": "completed",
                "jobs_parsed": 0,
                "jobs_skipped": 0,
                "errors": [],
            }
            
            for job in jobs:
                if job.parsed_jd:
                    results["jobs_skipped"] += 1
                    continue
                
                result = await background_tasks.parse_job_task(job.id, db=db)
                if result["status"] == "completed":
                    results["jobs_parsed"] += 1
                else:
                    results["errors"].append(result.get("error"))
            
            return results
            
        finally:
            db.close()
        
    async def run_matching_phase(
        self,
        user_id: int,
        job_ids: Optional[list[int]] = None,
    ) -> dict:
        """
        Run matching for parsed jobs.
        
        Args:
            user_id: User ID
            job_ids: Specific job IDs to match
            
        Returns:
            Matching results
        """
        logger.info(f"Running matching phase for user {user_id}, jobs: {job_ids or 'all parsed'}")
        
        db = next(get_db())
        try:
            if job_ids:
                jobs = db.query(models.Job).filter(models.Job.id.in_(job_ids)).all()
            else:
                jobs = db.query(models.Job).filter(
                    models.Job.status == models.JobStatus.PARSED
                ).limit(50).all()
            
            results = {
                "status": "completed",
                "jobs_matched": 0,
                "top_matches": [],
                "errors": [],
            }
            
            matches = []
            for job in jobs:
                result = await background_tasks.match_job_task(job.id, user_id, db=db)
                if result["status"] == "completed":
                    results["jobs_matched"] += 1
                    matches.append({
                        "job_id": job.id,
                        "score": result.get("match_score", 0),
                    })
                else:
                    results["errors"].append(result.get("error"))
            
            # Sort and get top 5
            matches.sort(key=lambda x: x["score"], reverse=True)
            results["top_matches"] = matches[:5]
            
            return results
            
        finally:
            db.close()
        
    async def run_application_phase(
        self,
        user_id: int,
        job_ids: list[int],
    ) -> dict:
        """
        Run application submission for specific jobs.
        
        Args:
            user_id: User ID
            job_ids: Job IDs to apply to
            
        Returns:
            Application results
        """
        logger.info(f"Running application phase for user {user_id}, jobs: {job_ids}")
        
        results = {
            "status": "completed",
            "applications_submitted": 0,
            "applications_failed": 0,
            "applications": [],
        }
        
        for job_id in job_ids:
            try:
                result = await background_tasks.apply_job_task(job_id, user_id)
                results["applications"].append(result)
                
                if result["status"] in ["completed", "partial_failure"]:
                    if result.get("success"):
                        results["applications_submitted"] += 1
                    else:
                        results["applications_failed"] += 1
                else:
                    results["applications_failed"] += 1
                    
            except Exception as e:
                logger.error(f"Error applying to job {job_id}: {str(e)}")
                results["applications_failed"] += 1
                results["applications"].append({
                    "status": "failed",
                    "job_id": job_id,
                    "error": str(e),
                })
        
        return results
        
    def get_status(self) -> dict:
        """Get current orchestrator status."""
        return {
            "status": self._status,
            "scheduled_jobs": len(self.scheduler.get_jobs()),
            "last_workflow_history": self._workflow_history,
        }
        
    def get_workflow_history(self, user_id: int) -> Optional[dict]:
        """Get last workflow result for a user."""
        return self._workflow_history.get(user_id)


# Global orchestrator instance
_orchestrator: Optional[WorkflowOrchestrator] = None


def get_orchestrator() -> WorkflowOrchestrator:
    """Get or create workflow orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = WorkflowOrchestrator()
    return _orchestrator


async def start_orchestrator():
    """Start the global workflow orchestrator."""
    orchestrator = get_orchestrator()
    await orchestrator.start()


async def stop_orchestrator():
    """Stop the global workflow orchestrator."""
    orchestrator = get_orchestrator()
    await orchestrator.stop()
