from sqlalchemy import Column, String, Integer, Text, DateTime, Enum, Boolean, Float, UUID as SQLUUID
from sqlalchemy.dialects.postgresql import JSON, JSONB
import uuid
from datetime import datetime
from app.database import Base
import enum


class Company(Base):
    __tablename__ = "companies"
    
    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    careers_url = Column(String(500), nullable=False)
    ats_platform = Column(String(100), nullable=True)  # greenhouse, lever, workday, ashby, etc
    ats_url = Column(String(500), nullable=True)
    application_mode = Column(String(50), nullable=False, default="global")  # global, always_ask, always_auto, paused
    last_scraped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JobStatus(str, enum.Enum):
    NEW = "new"
    PENDING_APPROVAL = "pending_approval"
    APPLYING = "applying"
    APPLIED = "applied"
    SKIPPED = "skipped"
    FAILED = "failed"
    MANUAL_NEEDED = "manual_needed"
    WITHDRAWN = "withdrawn"


class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(SQLUUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    source = Column(String(50), nullable=True, index=True)  # linkedin, indeed, glassdoor, github, greenhouse, etc
    external_job_id = Column(String(255), nullable=True, index=True)  # ID from source platform
    location = Column(String(255), nullable=True, index=True)  # Explicit location field
    raw_jd = Column(Text, nullable=True)
    parsed_jd = Column(JSONB, nullable=True)  # Structured job data from AI parser
    parser_version = Column(String(50), nullable=True)  # Parser version used
    parsed_at = Column(DateTime, nullable=True)  # When job was parsed
    match_score = Column(Integer, nullable=True)  # 0-100 match to user resume
    fit_score = Column(Integer, nullable=True)  # 0-100 overall fit
    status = Column(String(50), default=JobStatus.NEW.value, nullable=False)
    found_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    scraped_at = Column(DateTime, nullable=True)  # When job was scraped
    approval_token = Column(String(500), nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Application(Base):
    __tablename__ = "applications"
    
    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(SQLUUID(as_uuid=True), nullable=False, index=True)
    resume_path = Column(String(500), nullable=True)
    cover_letter = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    method = Column(String(50), nullable=True)  # auto, manual, approved
    screenshot_path = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_resume = Column(JSONB, nullable=False)  # {name, email, phone, skills, experience, etc}
    resume_pdf_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_email = Column(String(255), nullable=False)
    global_mode = Column(String(50), default="approval", nullable=False)  # approval or auto_apply
    fit_score_threshold = Column(Integer, default=65, nullable=False)
    auto_apply_threshold = Column(Integer, default=75, nullable=False)
    target_roles = Column(JSONB, nullable=True)  # ["Backend Engineer", "Full Stack", etc]
    excluded_keywords = Column(JSONB, nullable=True)  # ["C++", "embedded", etc]
    min_years_experience = Column(Integer, nullable=True)
    daily_digest_time = Column(String(5), default="08:00", nullable=False)  # HH:MM format
    scrape_interval_hours = Column(Integer, default=6, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyIntel(Base):
    __tablename__ = "company_intel"
    
    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(SQLUUID(as_uuid=True), nullable=False, index=True)
    avg_response_days = Column(Integer, nullable=True)
    interview_stages = Column(Integer, nullable=True)
    applicant_tips = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)  # reddit, glassdoor, linkedin, etc
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EmailType(str, enum.Enum):
    APPROVAL_NEEDED = "approval_needed"  # Type 1: Approval required
    AUTO_APPLIED = "auto_applied"  # Type 2: Auto-applied notification
    APPLICATION_CONFIRMED = "application_confirmed"  # Type 3: After submission
    MANUAL_REQUIRED = "manual_required"  # Type 4: Manual action needed
    DAILY_DIGEST = "daily_digest"  # Type 5: Daily summary


class EmailLog(Base):
    __tablename__ = "email_logs"
    
    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    to_email = Column(String(255), nullable=False, index=True)
    email_type = Column(String(50), nullable=False)  # EmailType enum
    job_id = Column(SQLUUID(as_uuid=True), nullable=True, index=True)
    subject = Column(String(255), nullable=False)
    resend_id = Column(String(255), nullable=True)  # ID from Resend API
    sent_at = Column(DateTime, nullable=True)
    deliver_status = Column(String(50), nullable=True)  # delivered, bounced, complained, etc
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    context = Column(JSONB, nullable=True)  # Any additional context
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
