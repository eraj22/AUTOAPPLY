"""
Resume Parser using Ollama LLM
Converts resume/CV text into standardized, machine-readable user profile data
"""

import logging
import json
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class UserPreferences(BaseModel):
    """User job preferences"""
    
    min_salary: Optional[int] = Field(None, description="Minimum acceptable salary")
    max_salary: Optional[int] = Field(None, description="Maximum acceptable salary")
    preferred_remote_type: str = Field("hybrid", description="fully_remote|hybrid|onsite")
    desired_industries: List[str] = Field(default_factory=list, description="Preferred industries")
    desired_company_sizes: List[str] = Field(
        default_factory=lambda: ["51-200", "201-1000"], 
        description="Preferred company sizes"
    )
    willing_to_travel: int = Field(0, description="% travel willing to do")
    open_to_contract: bool = Field(False, description="Open to contract roles?")
    visa_sponsorship_needed: bool = Field(False, description="Need visa sponsorship?")
    relocation_willing: bool = Field(False, description="Willing to relocate?")
    desired_locations: List[str] = Field(default_factory=list, description="Preferred locations")


class ParsedResumeData(BaseModel):
    """Standardized resume data extracted from resume text"""
    
    full_name: Optional[str] = Field(None, description="Candidate full name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="Current location")
    
    all_skills: List[str] = Field(default_factory=list, description="All skills mentioned")
    technical_skills: List[str] = Field(default_factory=list, description="Technical skills")
    soft_skills: List[str] = Field(default_factory=list, description="Soft skills")
    
    seniority_level: str = Field("mid", description="junior|mid|senior|lead|executive")
    years_of_experience: int = Field(0, description="Total years of professional experience")
    years_in_current_role: Optional[int] = Field(None, description="Years in current position")
    
    current_title: Optional[str] = Field(None, description="Current job title")
    current_company: Optional[str] = Field(None, description="Current company")
    
    past_companies: List[str] = Field(default_factory=list, description="Previous employers")
    past_titles: List[str] = Field(default_factory=list, description="Previous titles")
    
    education_level: Optional[str] = Field(None, description="Bachelor's|Master's|PhD|Bootcamp|etc")
    university: Optional[str] = Field(None, description="University name")
    degree_field: Optional[str] = Field(None, description="Field of study")
    
    certifications: List[str] = Field(default_factory=list, description="Certifications held")
    
    primary_focus_area: Optional[str] = Field(None, description="Backend|Frontend|Full-Stack|DevOps|etc")
    secondary_focus_areas: List[str] = Field(default_factory=list, description="Secondary specialties")
    
    tech_stack: List[str] = Field(default_factory=list, description="Technologies used professionally")
    
    key_achievements: List[str] = Field(default_factory=list, description="Notable achievements")
    
    github_url: Optional[str] = Field(None, description="GitHub profile URL")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    portfolio_url: Optional[str] = Field(None, description="Portfolio/website URL")
    
    open_to_opportunities: bool = Field(True, description="Open to job opportunities?")
    
    preferences: UserPreferences = Field(default_factory=UserPreferences, description="Job preferences")
    
    confidence_score: float = Field(0.7, description="Parser confidence 0-1.0")
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Developer",
                "email": "john@example.com",
                "phone": "+1-555-0123",
                "location": "San Francisco, CA",
                "all_skills": ["Python", "FastAPI", "PostgreSQL", "React", "Docker"],
                "technical_skills": ["Python", "FastAPI", "PostgreSQL"],
                "soft_skills": ["Leadership", "Communication"],
                "seniority_level": "mid",
                "years_of_experience": 5,
                "current_title": "Senior Backend Engineer",
                "current_company": "TechCorp",
                "primary_focus_area": "Backend",
                "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
                "key_achievements": ["Led migration to microservices", "Improved API performance 40%"],
                "education_level": "Bachelor's",
                "university": "State University",
                "preferences": {
                    "min_salary": 150000,
                    "preferred_remote_type": "hybrid",
                    "desired_industries": ["SaaS", "FinTech"]
                }
            }
        }


class ResumeParser:
    """Parse resume text using Ollama LLM"""
    
    def __init__(self, ollama_url: Optional[str] = None, model: str = "tinyllama"):
        if ollama_url is None:
            ollama_url = settings.ollama_api_url
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = 60.0
    
    async def parse_resume(self, resume_text: str) -> ParsedResumeData:
        """
        Parse resume text and extract structured data
        
        Args:
            resume_text: Full resume content as text
        
        Returns:
            ParsedResumeData with extracted information
        
        Raises:
            Exception: If Ollama is unavailable or parsing fails
        """
        try:
            if not resume_text or len(resume_text.strip()) < 10:
                logger.warning("Resume text too short or empty")
                return ParsedResumeData(confidence_score=0.0)
            
            # Prepare prompt
            prompt = self._build_parsing_prompt(resume_text)
            
            logger.debug("Parsing resume")
            
            # Call Ollama
            response = await self._call_ollama(prompt)
            
            # Extract JSON
            parsed_data = self._extract_json_response(response)
            
            # Create ParsedResumeData object
            result = ParsedResumeData(**parsed_data)
            result.confidence_score = min(result.confidence_score, 0.95)
            
            logger.info(f"Parsed resume for {result.full_name or 'Unknown'} with confidence {result.confidence_score:.2%}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Ollama: {e}")
            return ParsedResumeData(confidence_score=0.0)
        except Exception as e:
            logger.error(f"Error parsing resume: {e}", exc_info=True)
            return ParsedResumeData(confidence_score=0.0)
    
    def _build_parsing_prompt(self, resume_text: str) -> str:
        """Build prompt for Ollama LLM"""
        
        return f"""Analyze this resume and extract structured data. Return ONLY valid JSON, no other text.

Resume:
{resume_text}

Return this exact JSON structure with extracted values (use null for unknown fields):
{{
  "full_name": "full name from resume",
  "email": "email if present",
  "phone": "phone if present",
  "location": "current location",
  "all_skills": ["skill1", "skill2"],
  "technical_skills": ["Python", "FastAPI"],
  "soft_skills": ["Leadership", "Communication"],
  "seniority_level": "junior|mid|senior|lead|executive",
  "years_of_experience": number,
  "years_in_current_role": number_or_null,
  "current_title": "current job title",
  "current_company": "current company name",
  "past_companies": ["company1", "company2"],
  "past_titles": ["title1", "title2"],
  "education_level": "Bachelor's|Master's|PhD|Bootcamp",
  "university": "university name",
  "degree_field": "field of study",
  "certifications": ["certification1"],
  "primary_focus_area": "Backend|Frontend|Full-Stack|DevOps|Data Engineer|etc",
  "secondary_focus_areas": ["focus2"],
  "tech_stack": ["technology1", "technology2"],
  "key_achievements": ["achievement1", "achievement2"],
  "github_url": "github url if present",
  "linkedin_url": "linkedin url if present",
  "portfolio_url": "portfolio url if present",
  "open_to_opportunities": true|false,
  "preferences": {{
    "min_salary": number_or_null,
    "max_salary": number_or_null,
    "preferred_remote_type": "fully_remote|hybrid|onsite",
    "desired_industries": ["industry1"],
    "desired_company_sizes": ["51-200", "201-1000"],
    "willing_to_travel": 0-100,
    "open_to_contract": true|false,
    "visa_sponsorship_needed": true|false,
    "relocation_willing": true|false,
    "desired_locations": ["location1"]
  }},
  "confidence_score": 0.0-1.0
}}

IMPORTANT:
- Return ONLY the JSON object, no markdown, no explanation
- Extract ALL technical skills mentioned
- Infer seniority level from years of experience and titles
- List skills in tech_stack if mentioned in professional context
- Set lower confidence if resume is vague or incomplete
- Extract preferences from any "open to", "seeking", or "looking for" statements"""
    
    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API with prompt"""
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "temperature": 0.3
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                    raise Exception(f"Ollama API returned {response.status_code}")
                
                result = response.json()
                return result.get("response", "")
        
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Ollama at {self.ollama_url}")
            raise Exception("Ollama service unavailable")
        except httpx.TimeoutException:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            raise Exception("Ollama request timeout")
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            raise
    
    def _extract_json_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from Ollama response"""
        
        response = response.strip()
        
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()
        
        response = response.replace("```", "").strip()
        
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in response: {response[:200]}")
            raise


# Singleton instance
_resume_parser_instance: Optional[ResumeParser] = None


def get_resume_parser() -> ResumeParser:
    """Get or create ResumeParser singleton"""
    global _resume_parser_instance
    if _resume_parser_instance is None:
        _resume_parser_instance = ResumeParser()
    return _resume_parser_instance
