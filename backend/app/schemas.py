from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


# Resume Schemas
class ResumeCreate(BaseModel):
    base_resume: Dict[str, Any]


class ResumeResponse(BaseModel):
    id: uuid.UUID
    base_resume: Dict[str, Any]
    resume_pdf_path: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Company Schemas
class CompanyCreate(BaseModel):
    name: str
    careers_url: str
    ats_platform: Optional[str] = None
    ats_url: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    careers_url: Optional[str] = None
    ats_platform: Optional[str] = None
    application_mode: Optional[str] = None


class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    careers_url: str
    ats_platform: Optional[str]
    ats_url: Optional[str]
    application_mode: str
    last_scraped_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Job Schemas
class JobCreate(BaseModel):
    company_id: uuid.UUID
    title: str
    url: str
    raw_jd: Optional[str] = None


class JobResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    url: str
    raw_jd: Optional[str]
    parsed_jd: Optional[Dict[str, Any]]
    fit_score: Optional[int]
    status: str
    found_at: datetime
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Application Schemas
class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    resume_path: Optional[str] = None
    cover_letter: Optional[str] = None
    method: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    resume_path: Optional[str]
    cover_letter: Optional[str]
    submitted_at: Optional[datetime]
    method: Optional[str]
    screenshot_path: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# User Settings Schemas
class UserSettingsCreate(BaseModel):
    notification_email: EmailStr
    global_mode: str = "approval"
    fit_score_threshold: int = 65
    auto_apply_threshold: int = 75
    target_roles: Optional[List[str]] = None
    excluded_keywords: Optional[List[str]] = None
    min_years_experience: Optional[int] = None
    daily_digest_time: str = "08:00"
    scrape_interval_hours: int = 6


class UserSettingsUpdate(BaseModel):
    notification_email: Optional[str] = None
    global_mode: Optional[str] = None
    fit_score_threshold: Optional[int] = None
    auto_apply_threshold: Optional[int] = None
    target_roles: Optional[List[str]] = None
    excluded_keywords: Optional[List[str]] = None
    min_years_experience: Optional[int] = None
    daily_digest_time: Optional[str] = None
    scrape_interval_hours: Optional[int] = None


class UserSettingsResponse(BaseModel):
    id: uuid.UUID
    notification_email: str
    global_mode: str
    fit_score_threshold: int
    auto_apply_threshold: int
    target_roles: Optional[List[str]]
    excluded_keywords: Optional[List[str]]
    min_years_experience: Optional[int]
    daily_digest_time: str
    scrape_interval_hours: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
