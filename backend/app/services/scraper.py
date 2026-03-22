from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import asyncio
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class JobScraper:
    """Base scraper for job listings"""
    
    def __init__(self):
        self.browser = None
        self.playwright = None
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def scrape_linkedin_jobs(self, search_query: str, location: str = "United States") -> List[Dict[str, Any]]:
        """
        Scrape LinkedIn jobs (simplified - LinkedIn has CAPTCHA)
        In production, use official API or data provider
        """
        logger.info(f"Scraping LinkedIn jobs: {search_query} in {location}")
        # TODO: Implement LinkedIn scraping with proper handling
        # For now, return empty (real implementation would need proxy/API)
        return []
    
    async def scrape_github_jobs(self) -> List[Dict[str, Any]]:
        """Scrape GitHub Jobs board"""
        jobs = []
        page = None
        try:
            page = await self.browser.new_page()
            await page.goto("https://jobs.github.com/")
            
            # Wait for jobs to load
            await page.wait_for_selector('[data-test-selector="job-result"]', timeout=5000)
            
            # Get HTML
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Parse jobs
            job_elements = soup.select('[data-test-selector="job-result"]')
            for job_elem in job_elements[:20]:  # Limit to 20 jobs
                title = job_elem.select_one('[data-test-selector="job-result-item"]')
                link = job_elem.select_one('a')
                
                if title and link:
                    jobs.append({
                        "title": title.text.strip(),
                        "url": link.get('href', ''),
                        "source": "github_jobs"
                    })
            
            logger.info(f"Found {len(jobs)} jobs on GitHub Jobs")
            
        except Exception as e:
            logger.error(f"Error scraping GitHub Jobs: {e}")
        finally:
            if page:
                await page.close()
        
        return jobs
    
    async def scrape_greenhouse_jobs(self, company_name: str, careers_url: str) -> List[Dict[str, Any]]:
        """
        Scrape Greenhouse careers page for jobs
        Greenhouse uses consistent HTML structure
        """
        jobs = []
        page = None
        
        try:
            page = await self.browser.new_page()
            await page.goto(careers_url, wait_until="networkidle")
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Greenhouse typically uses this structure
            job_elements = soup.select('div[class*="opening"]')
            
            for job_elem in job_elements:
                title_elem = job_elem.select_one('a')
                if title_elem:
                    job_url = title_elem.get('href', '')
                    job_title = title_elem.text.strip()
                    
                    jobs.append({
                        "title": job_title,
                        "url": job_url if job_url.startswith('http') else f"https://greenhouse.io{job_url}",
                        "company": company_name,
                        "source": "greenhouse"
                    })
            
            logger.info(f"Found {len(jobs)} jobs on Greenhouse for {company_name}")
            
        except Exception as e:
            logger.error(f"Error scraping Greenhouse ({company_name}): {e}")
        finally:
            if page:
                await page.close()
        
        return jobs
    
    async def scrape_all_sources(self, companies: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Scrape all job sources"""
        all_jobs = []
        
        for company in companies:
            if company.get('ats_platform') == 'greenhouse' or 'greenhouse' in company.get('careers_url', '').lower():
                jobs = await self.scrape_greenhouse_jobs(company['name'], company['careers_url'])
                all_jobs.extend(jobs)
        
        # Add GitHub Jobs
        github_jobs = await self.scrape_github_jobs()
        all_jobs.extend(github_jobs)
        
        return all_jobs


# Async helper
async def scrape_jobs_async(companies: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Helper to scrape all jobs from companies"""
    async with JobScraper() as scraper:
        return await scraper.scrape_all_sources(companies)
