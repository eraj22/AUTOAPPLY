"""
Application Bot Service
Handles automated job application submissions using form filling
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from playwright.async_api import Page, Browser, async_playwright
import re
import json

logger = logging.getLogger(__name__)


class ATSType(str, Enum):
    """Supported ATS/Application Platforms"""
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"
    ASHBY = "ashby"
    SMARTRECRUITERS = "smartrecruiters"
    BAMBOO_HR = "bamboo_hr"
    TALEO = "taleo"
    ICIMS = "icims"
    GENERIC = "generic"
    DIRECT_EMAIL = "direct_email"


class FormField(BaseModel):
    """Represents a form field to fill"""
    name: str
    field_type: str  # "text", "email", "textarea", "file", "select", "radio", "checkbox"
    selector: Optional[str] = None
    xpath: Optional[str] = None
    value: Optional[str] = None
    options: Optional[List[str]] = None  # For select/radio fields
    required: bool = False


class ApplicationForm(BaseModel):
    """Detected application form structure"""
    ats_type: ATSType
    fields: List[FormField]
    submit_button_selector: Optional[str] = None
    submit_button_xpath: Optional[str] = None
    confidence: float = 0.0  # 0.0-1.0


class ApplicationResult(BaseModel):
    """Result of application submission"""
    success: bool
    ats_type: ATSType
    job_url: str
    submitted_at: Optional[datetime] = None
    message: str
    errors: List[str] = []
    form_data_captured: Dict[str, Any] = {}
    screenshot_path: Optional[str] = None


class ATSDetector:
    """Detect ATS type from job application URL/page"""
    
    ATS_PATTERNS = {
        ATSType.GREENHOUSE: [
            r'boards\.greenhouse\.io',
            r'greenhouse\.io',
            'Powered by Greenhouse',
            'Greenhouse',
        ],
        ATSType.LEVER: [
            r'lever\.co',
            'Lever',
            'lever-jobs',
        ],
        ATSType.WORKDAY: [
            r'workday\.com',
            'Workday',
            'myworkdayjobs',
        ],
        ATSType.ASHBY: [
            r'ashby\.com',
            'Ashby',
            'ashbyhq',
        ],
        ATSType.SMARTRECRUITERS: [
            r'smartrecruiters\.com',
            'SmartRecruiters',
            'smartrecruiters',
        ],
        ATSType.BAMBOO_HR: [
            r'bamboohr\.com',
            'BambooHR',
            'applicant',
        ],
        ATSType.TALEO: [
            r'taleo\.net',
            'Taleo',
            'oracle taleo',
        ],
        ATSType.ICIMS: [
            r'icims\.com',
            'iCIMS',
            'icims',
        ],
    }
    
    @staticmethod
    def detect_ats(url: str, page_content: str = "") -> Tuple[ATSType, float]:
        """
        Detect ATS type from URL and page HTML
        
        Args:
            url: Job application URL
            page_content: HTML content of the page
        
        Returns:
            Tuple of (ATSType, confidence_score)
        """
        combined_content = (url + " " + page_content).lower()
        
        # Check each ATS pattern
        scores = {}
        for ats_type, patterns in ATSDetector.ATS_PATTERNS.items():
            matches = sum(1 for pattern in patterns if pattern.lower() in combined_content)
            scores[ats_type] = matches
        
        if max(scores.values()) > 0:
            best_match = max(scores, key=scores.get)
            confidence = min(scores[best_match] / len(ATSDetector.ATS_PATTERNS[best_match]), 1.0)
            return best_match, confidence
        
        return ATSType.GENERIC, 0.0


class FormExtractor:
    """Extract form fields from application pages"""
    
    @staticmethod
    async def extract_form(page: Page, ats_type: ATSType) -> Optional[ApplicationForm]:
        """
        Extract form fields from page based on ATS type
        
        Args:
            page: Playwright page
            ats_type: Detected ATS type
        
        Returns:
            ApplicationForm with detected fields
        """
        try:
            fields = []
            
            # Different extraction logic per ATS
            if ats_type == ATSType.GREENHOUSE:
                fields = await FormExtractor._extract_greenhouse_form(page)
            elif ats_type == ATSType.LEVER:
                fields = await FormExtractor._extract_lever_form(page)
            elif ats_type == ATSType.WORKDAY:
                fields = await FormExtractor._extract_workday_form(page)
            else:
                # Generic form extraction
                fields = await FormExtractor._extract_generic_form(page)
            
            # Find submit button
            submit_selector = await FormExtractor._find_submit_button(page)
            
            return ApplicationForm(
                ats_type=ats_type,
                fields=fields,
                submit_button_selector=submit_selector,
                confidence=len(fields) / 10 if fields else 0.0  # Rough confidence
            )
        
        except Exception as e:
            logger.error(f"Error extracting form for {ats_type}: {e}")
            return None
    
    @staticmethod
    async def _extract_greenhouse_form(page: Page) -> List[FormField]:
        """Extract Greenhouse form fields"""
        fields = []
        
        # Greenhouse uses standardized selectors
        input_elements = await page.query_selector_all('input[type="text"], input[type="email"], input[type="tel"]')
        
        for elem in input_elements:
            name = await elem.get_attribute('name') or await elem.get_attribute('placeholder') or 'unknown'
            input_type = await elem.get_attribute('type') or 'text'
            required = await elem.get_attribute('required') == ''
            
            fields.append(FormField(
                name=name,
                field_type=input_type,
                selector=f'input[name="{name}"]',
                required=required
            ))
        
        # Textareas
        textarea_elements = await page.query_selector_all('textarea')
        for elem in textarea_elements:
            name = await elem.get_attribute('name') or 'message'
            fields.append(FormField(
                name=name,
                field_type='textarea',
                selector=f'textarea[name="{name}"]',
                required=True
            ))
        
        # Select dropdowns
        select_elements = await page.query_selector_all('select')
        for elem in select_elements:
            name = await elem.get_attribute('name') or 'select'
            options = await elem.query_selector_all('option')
            option_texts = []
            for opt in options:
                text = await opt.text_content()
                if text and text.strip() and text.strip() != 'Select an option':
                    option_texts.append(text.strip())
            
            fields.append(FormField(
                name=name,
                field_type='select',
                selector=f'select[name="{name}"]',
                options=option_texts,
                required=True
            ))
        
        # File uploads
        file_inputs = await page.query_selector_all('input[type="file"]')
        for elem in file_inputs:
            name = await elem.get_attribute('name') or 'resume'
            fields.append(FormField(
                name=name,
                field_type='file',
                selector=f'input[name="{name}"]',
                required=True
            ))
        
        return fields
    
    @staticmethod
    async def _extract_lever_form(page: Page) -> List[FormField]:
        """Extract Lever form fields - similar to generic"""
        return await FormExtractor._extract_generic_form(page)
    
    @staticmethod
    async def _extract_workday_form(page: Page) -> List[FormField]:
        """Extract Workday form fields - complex nested structure"""
        fields = []
        
        # Workday uses data attributes heavily
        sections = await page.query_selector_all('[data-automation-id="decorativeFormSection"]')
        
        for section in sections:
            inputs = await section.query_selector_all('input, textarea, select')
            for elem in inputs:
                field_type = await elem.get_attribute('type') or 'text'
                if field_type == 'hidden':
                    continue
                
                label = await section.query_selector('label')
                name = await label.text_content() if label else 'field'
                
                fields.append(FormField(
                    name=name.strip(),
                    field_type=field_type,
                    selector=None,
                    xpath=f'//input[@type="{field_type}"]',
                    required=False
                ))
        
        return fields
    
    @staticmethod
    async def _extract_generic_form(page: Page) -> List[FormField]:
        """Generic form extraction for unknown ATS"""
        fields = []
        
        # Get all form inputs
        all_inputs = await page.query_selector_all('input, textarea, select')
        
        for elem in all_inputs:
            tag_name = await elem.evaluate('el => el.tagName')
            input_type = await elem.get_attribute('type') or 'text'
            
            if input_type == 'hidden' or input_type == 'submit':
                continue
            
            name = await elem.get_attribute('name') or await elem.get_attribute('id') or 'unknown'
            
            # Skip obvious bot detection/honeypot fields
            if any(x in name.lower() for x in ['honeypot', 'bot', 'spam', 'url']):
                continue
            
            label_text = ""
            label = await elem.evaluate_handle('el => el.labels ? el.labels[0] : null')
            if label:
                label_text = await label.text_content()
            
            fields.append(FormField(
                name=name,
                field_type=input_type,
                selector=f'input[name="{name}"]' if tag_name == 'INPUT' else f'{tag_name.lower()}[name="{name}"]',
                required=await elem.get_attribute('required') == '',
            ))
        
        return fields
    
    @staticmethod
    async def _find_submit_button(page: Page) -> Optional[str]:
        """Find submit button selector"""
        selectors = [
            'button[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            'button:has-text("Send")',
            'input[type="submit"]',
            'button[onclick*="submit"]',
        ]
        
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    return selector
            except:
                continue
        
        return None


class FormFiller:
    """Fill out application forms with candidate data"""
    
    @staticmethod
    async def fill_form(
        page: Page,
        form: ApplicationForm,
        candidate_data: Dict[str, Any],
        resume_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fill form with candidate data
        
        Args:
            page: Playwright page
            form: Form structure
            candidate_data: Candidate information (name, email, etc.)
            resume_path: Path to resume file
        
        Returns:
            Dictionary of fields that were filled
        """
        filled = {}
        
        for field in form.fields:
            try:
                selector = field.selector or field.xpath
                if not selector:
                    logger.warning(f"No selector for field {field.name}")
                    continue
                
                # Get value for this field
                value = FormFiller._map_field_value(field, candidate_data, resume_path)
                
                if not value:
                    if field.required:
                        logger.warning(f"Required field {field.name} has no value")
                    continue
                
                # Fill based on field type
                if field.field_type == 'file':
                    # File upload
                    if resume_path:
                        await page.locator(selector).set_input_files(resume_path)
                        filled[field.name] = resume_path
                
                elif field.field_type == 'select':
                    # Select dropdown
                    await page.locator(selector).select_option(value)
                    filled[field.name] = value
                
                elif field.field_type == 'checkbox':
                    # Checkbox
                    if value.lower() in ['true', 'yes', '1']:
                        await page.locator(selector).check()
                        filled[field.name] = True
                
                elif field.field_type == 'radio':
                    # Radio button
                    await page.locator(selector).check()
                    filled[field.name] = value
                
                else:
                    # Text input / textarea
                    await page.locator(selector).fill(value)
                    filled[field.name] = value
                
                logger.debug(f"Filled field {field.name} with value: {value[:50]}")
            
            except Exception as e:
                logger.warning(f"Error filling field {field.name}: {e}")
                continue
        
        return filled
    
    @staticmethod
    def _map_field_value(field: FormField, candidate_data: Dict[str, Any], resume_path: Optional[str]) -> Optional[str]:
        """Map form field to candidate data"""
        field_name_lower = field.name.lower()
        
        # Direct mappings
        mappings = {
            'name': candidate_data.get('name', ''),
            'fullname': candidate_data.get('name', ''),
            'email': candidate_data.get('email', ''),
            'phone': candidate_data.get('phone', ''),
            'location': candidate_data.get('location', ''),
            'linkedin': candidate_data.get('linkedin_url', ''),
            'github': candidate_data.get('github_url', ''),
            'portfolio': candidate_data.get('portfolio_url', ''),
            'website': candidate_data.get('website_url', ''),
            'resume': resume_path,
            'cover_letter': candidate_data.get('cover_letter', ''),
            'message': candidate_data.get('cover_letter', ''),
            'yes': 'yes',
            'true': 'true',
        }
        
        # Check direct mappings
        for key, value in mappings.items():
            if key in field_name_lower:
                return str(value) if value else None
        
        # Check for common question patterns
        if 'experience' in field_name_lower:
            years = candidate_data.get('years_experience', 5)
            return str(years)
        
        if 'authorization' in field_name_lower or 'work legally' in field_name_lower:
            return 'yes'
        
        if 'relocation' in field_name_lower:
            return candidate_data.get('willing_to_relocate', 'No')
        
        return None


class ApplicationBot:
    """Main application bot orchestrator"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def apply_to_job(
        self,
        job_url: str,
        candidate_data: Dict[str, Any],
        resume_path: Optional[str] = None,
        screenshot_dir: str = "/tmp"
    ) -> ApplicationResult:
        """
        Apply to a job automatically
        
        Args:
            job_url: URL of the job posting
            candidate_data: Candidate information (name, email, phone, etc.)
            resume_path: Path to resume file for upload
            screenshot_dir: Directory to save screenshots
        
        Returns:
            ApplicationResult with success status
        """
        page = None
        
        try:
            page = await self.browser.new_page()
            
            # Navigate to job
            logger.info(f"Navigating to: {job_url}")
            await page.goto(job_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)  # Let page fully load
            
            # Get page content for ATS detection
            page_content = await page.content()
            
            # Detect ATS type
            ats_type, confidence = ATSDetector.detect_ats(job_url, page_content)
            logger.info(f"Detected ATS: {ats_type} (confidence: {confidence:.2f})")
            
            # Extract form
            form = await FormExtractor.extract_form(page, ats_type)
            if not form or not form.fields:
                return ApplicationResult(
                    success=False,
                    ats_type=ats_type,
                    job_url=job_url,
                    message="Could not extract application form",
                    errors=["No form fields detected"]
                )
            
            logger.info(f"Extracted {len(form.fields)} form fields")
            
            # Fill form
            filled_data = await FormFiller.fill_form(page, form, candidate_data, resume_path)
            logger.info(f"Filled {len(filled_data)} fields")
            
            # Take screenshot before submission
            screenshot_path = f"{screenshot_dir}/application_{int(__import__('time').time())}.png"
            try:
                await page.screenshot(path=screenshot_path)
            except:
                screenshot_path = None
            
            # Submit form
            if form.submit_button_selector:
                logger.info("Submitting application...")
                await page.locator(form.submit_button_selector).click()
                
                # Wait for completion (navigate to new page)
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(1000)
            
            # Check for success indicators
            success_indicators = [
                'thank you',
                'application received',
                'submitted successfully',
                'we\'ve received',
                'application confirmed'
            ]
            
            final_content = await page.content()
            success = any(indicator in final_content.lower() for indicator in success_indicators)
            
            return ApplicationResult(
                success=success,
                ats_type=ats_type,
                job_url=job_url,
                submitted_at=datetime.utcnow() if success else None,
                message="Application submitted successfully" if success else "Form submitted (manual verification recommended)",
                form_data_captured=filled_data,
                screenshot_path=screenshot_path
            )
        
        except Exception as e:
            logger.error(f"Error applying to job: {e}", exc_info=True)
            return ApplicationResult(
                success=False,
                ats_type=ATSType.GENERIC,
                job_url=job_url,
                message=f"Application failed: {str(e)}",
                errors=[str(e)]
            )
        
        finally:
            if page:
                await page.close()
