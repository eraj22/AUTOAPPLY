import resend
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import EmailLog, EmailType
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

# Setup Jinja2 environment for templates
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'emails')
jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

settings = get_settings()


def _render_template(template_name: str, context: dict) -> str:
    """Render an email template with context"""
    try:
        template = jinja_env.get_template(template_name)
        return template.render(**context)
    except Exception as e:
        logger.error(f"Error rendering template {template_name}: {e}")
        raise


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    email_type: str,
    job_id: str = None,
    db: Session = None
) -> dict:
    """
    Send email via Resend API and log the attempt
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email body
        email_type: Type of email (from EmailType enum)
        job_id: Associated job ID (optional)
        db: Database session for logging
        
    Returns:
        dict with resend_id, success status, and error message if any
    """
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured. Email not sent.")
        return {"success": False, "error": "Resend API key not configured"}
    
    resend.api_key = settings.resend_api_key
    
    try:
        response = resend.Emails.send({
            "from": settings.email_from,
            "to": to_email,
            "subject": subject,
            "html": html_content
        })
        
        resend_id = response.get("id") if isinstance(response, dict) else str(response)
        
        # Log the email in database if session provided
        if db:
            try:
                email_log = EmailLog(
                    to_email=to_email,
                    email_type=email_type,
                    job_id=job_id,
                    subject=subject,
                    resend_id=resend_id,
                    sent_at=datetime.utcnow(),
                    deliver_status="sent"
                )
                db.add(email_log)
                db.commit()
            except Exception as e:
                logger.error(f"Error logging email: {e}")
                db.rollback()
        
        logger.info(f"Email sent to {to_email} | Type: {email_type} | Resend ID: {resend_id}")
        return {"success": True, "resend_id": resend_id}
        
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        
        # Log failed attempt
        if db:
            try:
                email_log = EmailLog(
                    to_email=to_email,
                    email_type=email_type,
                    job_id=job_id,
                    subject=subject,
                    deliver_status="failed",
                    metadata={"error": str(e)}
                )
                db.add(email_log)
                db.commit()
            except Exception as log_error:
                logger.error(f"Error logging failed email: {log_error}")
                db.rollback()
        
        return {"success": False, "error": str(e)}


async def send_approval_email(
    to_email: str,
    job_title: str,
    company_name: str,
    fit_score: int,
    match_summary: str,
    approval_url: str,
    skip_url: str,
    preview_resume_url: str,
    pause_url: str,
    job_location: str = None,
    job_salary: str = None,
    job_id: str = None,
    db: Session = None
) -> dict:
    """
    Type 1: Send approval request email
    User needs to approve before application is submitted
    """
    context = {
        "company_name": company_name,
        "job_title": job_title,
        "job_location": job_location,
        "job_salary": job_salary,
        "fit_score": fit_score,
        "match_summary": match_summary,
        "approve_url": approval_url,
        "skip_url": skip_url,
        "preview_resume_url": preview_resume_url,
        "pause_url": pause_url
    }
    
    html_content = _render_template("approval_request.html", context)
    subject = f"New match at {company_name}: {job_title} — {fit_score}% fit"
    
    return await send_email(to_email, subject, html_content, EmailType.APPROVAL_NEEDED.value, job_id, db)


async def send_auto_applied_email(
    to_email: str,
    job_title: str,
    company_name: str,
    fit_score: int,
    submitted_at: str,
    resume_link: str,
    dashboard_link: str,
    withdraw_url: str,
    job_id: str = None,
    db: Session = None
) -> dict:
    """
    Type 2: Send auto-applied notification
    Application was submitted automatically (Mode 2)
    """
    context = {
        "company_name": company_name,
        "job_title": job_title,
        "fit_score": fit_score,
        "submitted_at": submitted_at,
        "resume_link": resume_link,
        "dashboard_link": dashboard_link,
        "withdraw_url": withdraw_url
    }
    
    html_content = _render_template("auto_applied.html", context)
    subject = f"Applied to {job_title} at {company_name} — {submitted_at}"
    
    return await send_email(to_email, subject, html_content, EmailType.AUTO_APPLIED.value, job_id, db)


async def send_application_confirmed_email(
    to_email: str,
    job_title: str,
    company_name: str,
    fit_score: int,
    avg_response_days: int,
    resume_link: str,
    dashboard_link: str,
    job_id: str = None,
    db: Session = None
) -> dict:
    """
    Type 3: Send application confirmed notification
    After successful form submission with proof (screenshot)
    """
    context = {
        "company_name": company_name,
        "job_title": job_title,
        "fit_score": fit_score,
        "avg_response_days": avg_response_days,
        "resume_link": resume_link,
        "dashboard_link": dashboard_link
    }
    
    html_content = _render_template("application_confirmed.html", context)
    subject = f"Confirmed: Applied to {company_name} for {job_title}"
    
    return await send_email(to_email, subject, html_content, EmailType.APPLICATION_CONFIRMED.value, job_id, db)


async def send_manual_required_email(
    to_email: str,
    job_title: str,
    company_name: str,
    issue_description: str,
    job_url: str,
    dashboard_link: str,
    job_id: str = None,
    db: Session = None
) -> dict:
    """
    Type 4: Send manual action required notification
    Bot encountered error; user needs to apply manually
    """
    context = {
        "company_name": company_name,
        "job_title": job_title,
        "issue_description": issue_description,
        "job_url": job_url,
        "dashboard_link": dashboard_link
    }
    
    html_content = _render_template("manual_required.html", context)
    subject = f"Manual action needed: {job_title} at {company_name}"
    
    return await send_email(to_email, subject, html_content, EmailType.MANUAL_REQUIRED.value, job_id, db)


async def send_daily_digest_email(
    to_email: str,
    digest_date: str,
    jobs_found: int,
    applications_submitted: int,
    pending_approval: int,
    new_jobs: list = None,
    applications: list = None,
    pending_jobs: list = None,
    dashboard_link: str = "",
    unsubscribe_link: str = "",
    db: Session = None
) -> dict:
    """
    Type 5: Send daily digest email
    Summary of all activity in the past 24 hours
    """
    context = {
        "digest_date": digest_date,
        "jobs_found": jobs_found,
        "applications_submitted": applications_submitted,
        "pending_approval": pending_approval,
        "new_jobs": new_jobs or [],
        "applications": applications or [],
        "pending_jobs": pending_jobs or [],
        "dashboard_link": dashboard_link,
        "unsubscribe_link": unsubscribe_link
    }
    
    html_content = _render_template("daily_digest.html", context)
    subject = f"AutoApply Daily Digest — {digest_date}"
    
    return await send_email(to_email, subject, html_content, EmailType.DAILY_DIGEST.value, db=db)
