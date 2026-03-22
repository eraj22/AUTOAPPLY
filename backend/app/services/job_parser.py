"""
Job Description Parser using Ollama LLM
Converts unstructured job descriptions into standardized, machine-readable data
"""

import logging
import json
import httpx
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.config import settings

logger = logging.getLogger(__name__)


class ParsedJobData(BaseModel):
    """Standardized job data extracted from any job description"""
    
    required_skills: List[str] = Field(default_factory=list, description="Must-have skills")
    nice_to_have_skills: List[str] = Field(default_factory=list, description="Nice-to-have skills")
    
    seniority_level: str = Field("mid", description="junior|mid|senior|lead|executive")
    
    salary_min: Optional[int] = Field(None, description="Minimum salary in USD")
    salary_max: Optional[int] = Field(None, description="Maximum salary in USD")
    salary_currency: str = Field("USD", description="Currency code")
    
    remote_type: str = Field("onsite", description="fully_remote|hybrid|onsite")
    
    company_size: Optional[str] = Field(None, description="1-50|51-200|201-1000|1001-5000|5000+")
    
    location: Optional[str] = Field(None, description="City, Country or Remote")
    
    industry: Optional[str] = Field(None, description="Industry vertical (e.g., SaaS, FinTech)")
    
    role_type: Optional[str] = Field(None, description="Full-time|Part-time|Contract|Freelance")
    
    tech_stack: List[str] = Field(default_factory=list, description="Technologies/frameworks used")
    
    benefits: List[str] = Field(default_factory=list, description="Notable benefits")
    
    estimated_interview_rounds: Optional[int] = Field(None, description="Number of interview stages")
    
    travel_required: Optional[int] = Field(0, description="% travel required")
    
    visa_sponsorship: Optional[bool] = Field(None, description="Does company sponsor visas?")
    
    experience_required_years: Optional[int] = Field(None, description="Years of experience needed")
    
    education_required: Optional[str] = Field(None, description="Required education level")
    
    title_aliases: List[str] = Field(default_factory=list, description="Similar role titles")
    
    responsibilities: List[str] = Field(default_factory=list, description="Key responsibilities")
    
    growth_opportunities: List[str] = Field(default_factory=list, description="Growth potential areas")
    
    company_stage: Optional[str] = Field(None, description="Pre-seed|Seed|Series A/B/C|Growth|Public")
    
    confidence_score: float = Field(0.7, description="Parser confidence 0-1.0")
    
    class Config:
        json_schema_extra = {
            "example": {
                "required_skills": ["Python", "FastAPI", "PostgreSQL"],
                "nice_to_have_skills": ["Docker", "Kubernetes"],
                "seniority_level": "mid",
                "salary_min": 140000,
                "salary_max": 180000,
                "remote_type": "hybrid",
                "company_size": "201-1000",
                "location": "San Francisco, CA",
                "industry": "SaaS",
                "role_type": "Full-time",
                "tech_stack": ["Python", "FastAPI", "PostgreSQL", "React"],
                "benefits": ["Health insurance", "401k", "Remote flexibility"],
                "estimated_interview_rounds": 4,
                "visa_sponsorship": True
            }
        }


class JobParser:
    """Parse job descriptions using Ollama LLM"""
    
    def __init__(self, ollama_url: str = settings.OLLAMA_API_URL, model: str = "llama2"):
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = 60.0
    
    async def parse_job_description(self, job_title: str, job_description: str, 
                                   company_name: Optional[str] = None) -> ParsedJobData:
        """
        Parse a job description and extract structured data
        
        Args:
            job_title: Job posting title
            job_description: Full job description text
            company_name: Company name for context
        
        Returns:
            ParsedJobData with extracted information
        
        Raises:
            Exception: If Ollama is unavailable or parsing fails
        """
        try:
            if not job_description or len(job_description.strip()) == 0:
                logger.warning("Empty job description provided")
                return ParsedJobData(confidence_score=0.0)
            
            # Prepare prompt with explicit JSON instructions
            prompt = self._build_parsing_prompt(job_title, job_description, company_name)
            
            logger.debug(f"Parsing job: {job_title}")
            
            # Call Ollama
            response = await self._call_ollama(prompt)
            
            # Extract and validate JSON
            parsed_data = self._extract_json_response(response)
            
            # Create ParsedJobData object with validation
            result = ParsedJobData(**parsed_data)
            result.confidence_score = min(result.confidence_score, 0.95)  # Cap at 0.95
            
            logger.info(f"Parsed job '{job_title}' with confidence {result.confidence_score:.2%}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Ollama: {e}")
            return ParsedJobData(confidence_score=0.0)
        except Exception as e:
            logger.error(f"Error parsing job description: {e}", exc_info=True)
            return ParsedJobData(confidence_score=0.0)
    
    def _build_parsing_prompt(self, job_title: str, job_description: str, 
                             company_name: Optional[str] = None) -> str:
        """Build prompt for Ollama LLM"""
        
        company_context = f"Company: {company_name}\n" if company_name else ""
        
        return f"""Analyze this job posting and extract structured data. Return ONLY valid JSON, no other text.

{company_context}Job Title: {job_title}

Job Description:
{job_description}

Return this exact JSON structure with extracted values (use null for unknown fields):
{{
  "required_skills": ["skill1", "skill2"],
  "nice_to_have_skills": ["skill3"],
  "seniority_level": "junior|mid|senior|lead|executive",
  "salary_min": number_or_null,
  "salary_max": number_or_null,
  "salary_currency": "USD",
  "remote_type": "fully_remote|hybrid|onsite",
  "company_size": "1-50|51-200|201-1000|1001-5000|5000+",
  "location": "city, country or 'Remote'",
  "industry": "SaaS|FinTech|Healthcare|etc",
  "role_type": "Full-time|Part-time|Contract|Freelance",
  "tech_stack": ["tech1", "tech2"],
  "benefits": ["benefit1", "benefit2"],
  "estimated_interview_rounds": number_or_null,
  "travel_required": 0-100,
  "visa_sponsorship": true|false|null,
  "experience_required_years": number_or_null,
  "education_required": "Bachelor's degree|Master's|etc",
  "title_aliases": ["similar_title_1", "similar_title_2"],
  "responsibilities": ["resp1", "resp2"],
  "growth_opportunities": ["area1", "area2"],
  "company_stage": "Pre-seed|Seed|Series A|Series B|Series C|Growth|Public",
  "confidence_score": 0.0-1.0
}}

IMPORTANT: 
- Return ONLY the JSON object, no markdown, no explanation
- For skills, extract specific technologies and frameworks
- Estimate values if not explicitly stated, but set lower confidence_score
- Match seniority level based on required experience and language
- Include company_stage if mentioned or can be inferred"""
    
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
                        "temperature": 0.3  # Lower temp for consistency
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
        """Extract JSON from Ollama response, handling various formats"""
        
        response = response.strip()
        
        # Try to find JSON block
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()
        
        # Remove any markdown code fence
        response = response.replace("```", "").strip()
        
        # Parse JSON
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in response: {response[:200]}")
            raise
    
    async def parse_batch(self, jobs: List[Dict[str, str]]) -> List[ParsedJobData]:
        """
        Parse multiple job descriptions
        
        Args:
            jobs: List of dicts with 'title', 'description', and optional 'company'
        
        Returns:
            List of ParsedJobData objects
        """
        results = []
        
        for i, job in enumerate(jobs, 1):
            logger.info(f"Parsing job {i}/{len(jobs)}: {job.get('title', 'Unknown')}")
            
            parsed = await self.parse_job_description(
                job_title=job.get("title", "Unknown"),
                job_description=job.get("description", ""),
                company_name=job.get("company")
            )
            results.append(parsed)
        
        return results


# Singleton instance
_parser_instance: Optional[JobParser] = None


def get_job_parser() -> JobParser:
    """Get or create JobParser singleton"""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = JobParser()
    return _parser_instance
