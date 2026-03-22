"""
Job Matching Engine
Calculates match scores between jobs and user resumes
"""

import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from difflib import SequenceMatcher
from app.services.job_parser import ParsedJobData
from app.services.resume_parser import ParsedResumeData

logger = logging.getLogger(__name__)


class MatchReason(BaseModel):
    """Why a job is/isn't a match"""
    
    category: str  # "skill", "salary", "remote", "seniority", "industry"
    match_type: str  # "positive" or "negative"
    message: str
    weight: float = 1.0  # Importance factor


class JobMatchResult(BaseModel):
    """Result of matching a job to a user's resume"""
    
    job_id: Optional[str] = None
    job_title: str
    company_name: Optional[str] = None
    match_score: int = Field(..., ge=0, le=100, description="Overall match 0-100")
    
    skill_match_score: int = Field(0, description="Skill match 0-100")
    seniority_match_score: int = Field(0, description="Seniority match 0-100")
    salary_match_score: int = Field(0, description="Salary match 0-100")
    remote_match_score: int = Field(0, description="Remote match 0-100")
    
    positive_matches: List[str] = Field(default_factory=list, description="Why it's a good match")
    concerns: List[str] = Field(default_factory=list, description="Why it might not match")
    missing_skills: List[str] = Field(default_factory=list, description="Skills user doesn't have")
    skill_gaps: List[str] = Field(default_factory=list, description="Nice-to-have skills missing")
    
    salary_gap: int = Field(0, description="Amount below user's minimum (if any)")
    reason_breakdown: List[MatchReason] = Field(default_factory=list, description="Detailed scoring breakdown")
    
    recommendation: str = Field("Review before applying", description="Brief recommendation")


class JobMatcher:
    """Match jobs to user profiles"""
    
    # Weights for score calculation
    SKILL_WEIGHT = 0.35
    SENIORITY_WEIGHT = 0.20
    SALARY_WEIGHT = 0.20
    REMOTE_WEIGHT = 0.10
    INDUSTRY_WEIGHT = 0.10
    COMPANY_SIZE_WEIGHT = 0.05
    
    def calculate_match(self,
                       parsed_job: ParsedJobData,
                       parsed_resume: ParsedResumeData,
                       job_title: str = "Unknown",
                       company_name: Optional[str] = None,
                       job_id: Optional[str] = None) -> JobMatchResult:
        """
        Calculate overall match score and reasoning
        
        Args:
            parsed_job: Structured job data from AI parser
            parsed_resume: Structured resume data from AI parser
            job_title: Job posting title
            company_name: Company name
            job_id: Unique job ID for reference
        
        Returns:
            JobMatchResult with score and detailed breakdown
        """
        
        result = JobMatchResult(
            job_id=job_id,
            job_title=job_title,
            company_name=company_name
        )
        
        # Calculate component scores
        skill_score = self._calculate_skill_match(parsed_job, parsed_resume, result)
        seniority_score = self._calculate_seniority_match(parsed_job, parsed_resume, result)
        salary_score = self._calculate_salary_match(parsed_job, parsed_resume, result)
        remote_score = self._calculate_remote_match(parsed_job, parsed_resume, result)
        industry_score = self._calculate_industry_match(parsed_job, parsed_resume, result)
        company_size_score = self._calculate_company_size_match(parsed_job, parsed_resume, result)
        
        # Store component scores
        result.skill_match_score = skill_score
        result.seniority_match_score = seniority_score
        result.salary_match_score = salary_score
        result.remote_match_score = remote_score
        
        # Calculate weighted overall score
        overall_score = (
            skill_score * self.SKILL_WEIGHT +
            seniority_score * self.SENIORITY_WEIGHT +
            salary_score * self.SALARY_WEIGHT +
            remote_score * self.REMOTE_WEIGHT +
            industry_score * self.INDUSTRY_WEIGHT +
            company_size_score * self.COMPANY_SIZE_WEIGHT
        )
        
        result.match_score = int(round(overall_score))
        
        # Generate recommendation
        result.recommendation = self._generate_recommendation(result)
        
        logger.info(f"Matched '{job_title}' with score {result.match_score}")
        
        return result
    
    def _calculate_skill_match(self, parsed_job: ParsedJobData, parsed_resume: ParsedResumeData, 
                               result: JobMatchResult) -> int:
        """Calculate skill match percentage (0-100)"""
        
        user_skills = set(s.lower() for s in parsed_resume.all_skills)
        required_skills = set(s.lower() for s in parsed_job.required_skills)
        nice_skills = set(s.lower() for s in parsed_job.nice_to_have_skills)
        
        if not required_skills:
            return 100  # No specific skills required
        
        # Match required skills
        matched_required = user_skills & required_skills
        missing_required = required_skills - user_skills
        
        result.missing_skills = list(missing_required)
        
        # Match nice-to-have
        matched_nice = user_skills & nice_skills
        missing_nice = nice_skills - user_skills
        
        result.skill_gaps = list(missing_nice)
        
        # Calculate percentage
        required_match_pct = len(matched_required) / len(required_skills) * 100
        
        # Bonus for nice-to-have skills
        nice_bonus = min(len(matched_nice) / max(len(nice_skills), 1) * 10, 10)
        
        skill_score = min(required_match_pct + nice_bonus, 100)
        
        # Add positive/negative reasons
        if len(matched_required) == len(required_skills):
            result.positive_matches.append(f"✓ Has all {len(required_skills)} required skills")
        elif len(matched_required) > 0:
            result.positive_matches.append(f"✓ Has {len(matched_required)}/{len(required_skills)} required skills")
        
        if missing_required:
            result.concerns.append(f"⚠ Missing {len(missing_required)} required skills: {', '.join(list(missing_required)[:3])}")
        
        if matched_nice:
            result.positive_matches.append(f"✓ Has {len(matched_nice)} nice-to-have skills")
        
        result.reason_breakdown.append(MatchReason(
            category="skill",
            match_type="positive" if len(matched_required) == len(required_skills) else "neutral",
            message=f"Matched {len(matched_required)}/{len(required_skills)} required skills",
            weight=self.SKILL_WEIGHT
        ))
        
        return int(skill_score)
    
    def _calculate_seniority_match(self, parsed_job: ParsedJobData, parsed_resume: ParsedResumeData,
                                   result: JobMatchResult) -> int:
        """Calculate seniority level match (0-100)"""
        
        seniority_hierarchy = {
            "junior": 1,
            "mid": 2,
            "senior": 3,
            "lead": 4,
            "executive": 5
        }
        
        job_level = seniority_hierarchy.get(parsed_job.seniority_level.lower(), 2)
        user_level = seniority_hierarchy.get(parsed_resume.seniority_level.lower(), 2)
        
        # Perfect match
        if job_level == user_level:
            result.positive_matches.append(f"✓ Seniority level matches ({parsed_resume.seniority_level})")
            result.reason_breakdown.append(MatchReason(
                category="seniority",
                match_type="positive",
                message=f"Perfect seniority match: {parsed_resume.seniority_level}",
                weight=self.SENIORITY_WEIGHT
            ))
            return 100
        
        # One level off (still good)
        if abs(job_level - user_level) == 1:
            result.positive_matches.append(f"~ Seniority close match")
            return 80
        
        # Two or more levels off
        if user_level > job_level:
            result.concerns.append(f"⚠ Overqualified for {parsed_job.seniority_level} role")
            result.reason_breakdown.append(MatchReason(
                category="seniority",
                match_type="negative",
                message=f"Candidate is {parsed_resume.seniority_level}, role is {parsed_job.seniority_level}",
                weight=self.SENIORITY_WEIGHT
            ))
            return 60
        else:
            result.concerns.append(f"⚠ May be underqualified for {parsed_job.seniority_level} role")
            return 50
    
    def _calculate_salary_match(self, parsed_job: ParsedJobData, parsed_resume: ParsedResumeData,
                                result: JobMatchResult) -> int:
        """Calculate salary match (0-100)"""
        
        user_min = parsed_resume.preferences.min_salary
        job_max = parsed_job.salary_max
        
        # No salary info on either side
        if not user_min or not job_max:
            return 75  # Neutral
        
        # Job meets or exceeds user minimum
        if job_max >= user_min:
            result.positive_matches.append(f"✓ Salary ${job_max:,} meets expectation (min: ${user_min:,})")
            result.reason_breakdown.append(MatchReason(
                category="salary",
                match_type="positive",
                message=f"Salary ${job_max:,} >= user minimum ${user_min:,}",
                weight=self.SALARY_WEIGHT
            ))
            return 100
        
        # Job below user minimum
        gap = user_min - job_max
        result.salary_gap = gap
        
        gap_pct = (gap / user_min) * 100
        match_score = max(0, 100 - gap_pct)
        
        result.concerns.append(f"✗ Salary ${job_max:,} below minimum ${user_min:,} (gap: ${gap:,})")
        
        result.reason_breakdown.append(MatchReason(
            category="salary",
            match_type="negative",
            message=f"Salary ${job_max:,} is ${gap:,} below user expectation",
            weight=self.SALARY_WEIGHT
        ))
        
        return int(match_score)
    
    def _calculate_remote_match(self, parsed_job: ParsedJobData, parsed_resume: ParsedResumeData,
                                result: JobMatchResult) -> int:
        """Calculate remote work preference match (0-100)"""
        
        remote_hierarchy = {
            "fully_remote": 100,
            "remote": 100,
            "hybrid": 75,
            "onsite": 50,
            "on-site": 50
        }
        
        user_pref = parsed_resume.preferences.preferred_remote_type.lower()
        job_type = parsed_job.remote_type.lower()
        
        # Map to hierarchy
        user_score = remote_hierarchy.get(user_pref, 50)
        job_score = remote_hierarchy.get(job_type, 50)
        
        # Calculate match
        if user_score == job_score:
            result.positive_matches.append(f"✓ Remote work setup matches ({job_type})")
            result.reason_breakdown.append(MatchReason(
                category="remote",
                match_type="positive",
                message=f"Job is {job_type} - matches preference",
                weight=self.REMOTE_WEIGHT
            ))
            return 100
        
        # Partial match (hybrid vs remote)
        if (user_pref in ["hybrid", "remote", "fully_remote"] and 
            job_type in ["hybrid", "remote", "fully_remote"]):
            return 85
        
        # Not a good match
        result.concerns.append(f"⚠ Job is {job_type}, prefer {user_pref}")
        return 50
    
    def _calculate_industry_match(self, parsed_job: ParsedJobData, parsed_resume: ParsedResumeData,
                                  result: JobMatchResult) -> int:
        """Calculate industry preference match (0-100)"""
        
        desired = [i.lower() for i in parsed_resume.preferences.desired_industries]
        job_industry = parsed_job.industry.lower() if parsed_job.industry else None
        
        if not desired or not job_industry:
            return 75  # Neutral if no preference or no industry specified
        
        if job_industry in desired:
            result.positive_matches.append(f"✓ {parsed_job.industry} industry matches your focus")
            return 100
        
        # Check for partial matches
        for ind in desired:
            if ind in job_industry or job_industry in ind:
                return 70
        
        return 50
    
    def _calculate_company_size_match(self, parsed_job: ParsedJobData, parsed_resume: ParsedResumeData,
                                      result: JobMatchResult) -> int:
        """Calculate company size preference match (0-100)"""
        
        preferred = parsed_resume.preferences.desired_company_sizes
        job_size = parsed_job.company_size
        
        if not job_size:
            return 75
        
        if job_size in preferred:
            return 100
        
        return 60
    
    def _generate_recommendation(self, result: JobMatchResult) -> str:
        """Generate brief recommendation based on score"""
        
        if result.match_score >= 85:
            return "🎯 Excellent match! Highly recommended to apply"
        elif result.match_score >= 70:
            return "✓ Good match, worth considering"
        elif result.match_score >= 50:
            return "~ Moderate match, apply if interested"
        else:
            return "⚠ Weak match, review carefully before applying"


# Matcher singleton
_matcher_instance: Optional[JobMatcher] = None


def get_job_matcher() -> JobMatcher:
    """Get or create JobMatcher singleton"""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = JobMatcher()
    return _matcher_instance
