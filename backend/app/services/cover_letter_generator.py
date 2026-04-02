"""
Cover Letter Generator using Ollama LLM
Generates personalized cover letters based on resume and job data
"""

import logging
import httpx
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CoverLetterGenerator:
    """Generate personalized cover letters using AI"""
    
    def __init__(self, ollama_url: Optional[str] = None, model: str = "tinyllama"):
        if ollama_url is None:
            ollama_url = settings.ollama_api_url
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = 60.0
    
    async def generate_cover_letter(
        self,
        resume_data: dict,
        job_data: dict,
        job_title: str,
        company_name: str
    ) -> str:
        """
        Generate a personalized cover letter using AI
        
        Args:
            resume_data: Parsed resume data (from ParsedResumeData)
            job_data: Parsed job data (from ParsedJobData)
            job_title: Job title/position name
            company_name: Company name
        
        Returns:
            Generated cover letter text
        
        Raises:
            Exception: If Ollama is unavailable or generation fails
        """
        try:
            if not resume_data or not job_data:
                logger.warning("Missing resume or job data")
                return ""
            
            # Prepare prompt
            prompt = self._build_generation_prompt(
                resume_data, job_data, job_title, company_name
            )
            
            logger.debug(f"Generating cover letter for {job_title} at {company_name}")
            
            # Call Ollama
            response = await self._call_ollama(prompt)
            
            logger.info(f"Generated cover letter for {job_title}")
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {e}", exc_info=True)
            raise
    
    def _build_generation_prompt(
        self,
        resume_data: dict,
        job_data: dict,
        job_title: str,
        company_name: str
    ) -> str:
        """Build prompt for Ollama to generate cover letter"""
        
        # Extract key information from resume
        candidate_name = resume_data.get("full_name", "Candidate")
        candidate_skills = ", ".join(resume_data.get("technical_skills", [])[:5])
        candidate_experience = resume_data.get("years_of_experience", 0)
        candidate_current_title = resume_data.get("current_title", "Professional")
        candidate_achievements = resume_data.get("key_achievements", [])[:2]
        
        # Extract key information from job
        required_skills = ", ".join(job_data.get("required_skills", [])[:5])
        job_responsibilities = ", ".join(job_data.get("responsibilities", [])[:3])
        company_stage = job_data.get("company_stage", "innovative")
        
        # Build achievements section
        achievements_text = ""
        if candidate_achievements:
            achievements_text = "I am particularly proud of " + ", and ".join(
                [f"having {a.lower()}" for a in candidate_achievements[:2]]
            ) + "."
        
        prompt = f"""Write a professional and compelling cover letter for the following job application. 
Make it personalized, specific, and enthusiastic. Keep it to 3-4 paragraphs, around 250 words.
Return ONLY the cover letter text, no additional commentary.

CANDIDATE INFORMATION:
- Name: {candidate_name}
- Current Title: {candidate_current_title}
- Years of Experience: {candidate_experience}
- Key Skills: {candidate_skills}
- Notable Achievements: {achievements_text}

JOB INFORMATION:
- Position: {job_title}
- Company: {company_name}
- Company Stage: {company_stage}
- Required Skills: {required_skills}
- Key Responsibilities: {job_responsibilities}

Write a cover letter that:
1. Opens with enthusiasm for the specific role and company
2. Demonstrates how the candidate's skills match the job requirements
3. Highlights relevant achievements and experience
4. Closes with a strong call to action

Make it written in first person as if from the candidate."""

        return prompt
    
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
                        "temperature": 0.7  # Slightly higher temperature for more creative writing
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


# Singleton instance
_cover_letter_generator_instance: Optional[CoverLetterGenerator] = None


def get_cover_letter_generator() -> CoverLetterGenerator:
    """Get or create CoverLetterGenerator singleton"""
    global _cover_letter_generator_instance
    if _cover_letter_generator_instance is None:
        _cover_letter_generator_instance = CoverLetterGenerator()
    return _cover_letter_generator_instance
