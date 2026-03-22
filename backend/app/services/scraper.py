from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class JobScraper:
    """Multi-platform job scraper using Playwright for browser automation"""
    
    def __init__(self):
        self.browser = None
        self.playwright = None
    
    async def __aenter__(self):
        """Async context manager entry - initialize browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def scrape_github_jobs(self, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Scrape GitHub Jobs board (https://jobs.github.com/)
        
        Args:
            search_query: Optional search query (e.g., "python", "remote")
        
        Returns:
            List of job dictionaries with title, company, location, url, source, scraped_at
        """
        jobs = []
        page = None
        try:
            page = await self.browser.new_page()
            url = "https://jobs.github.com/"
            if search_query:
                url += f"?search={search_query}"
            
            logger.info(f"Scraping GitHub Jobs: {url}")
            await page.goto(url, wait_until="networkidle")
            
            # Wait for job listings to appear
            try:
                await page.wait_for_selector("div.job-listing-result", timeout=10000)
            except:
                logger.warning("Timeout waiting for job listings on GitHub Jobs")
                return jobs
            
            # Get all job elements
            job_elements = await page.query_selector_all("div.job-listing-result")
            logger.info(f"Found {len(job_elements)} job elements on GitHub Jobs")
            
            for job_elem in job_elements:
                try:
                    # Extract title
                    title_elem = await job_elem.query_selector("a.result-title")
                    title_text = await title_elem.text_content() if title_elem else "N/A"
                    
                    # Extract company
                    company_elem = await job_elem.query_selector("a.result-company")
                    company_text = await company_elem.text_content() if company_elem else "N/A"
                    
                    # Extract location
                    location_elem = await job_elem.query_selector(".result-location")
                    location_text = await location_elem.text_content() if location_elem else "Remote"
                    
                    # Extract job URL
                    job_url = await title_elem.get_attribute("href") if title_elem else ""
                    full_url = urljoin("https://jobs.github.com/", job_url)
                    
                    job = {
                        "title": title_text.strip(),
                        "company": company_text.strip(),
                        "location": location_text.strip(),
                        "url": full_url,
                        "source": "github_jobs",
                        "scraped_at": datetime.now().isoformat()
                    }
                    jobs.append(job)
                    logger.debug(f"Scraped job: {job['title']} at {job['company']}")
                
                except Exception as e:
                    logger.warning(f"Error parsing job element: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(jobs)} jobs from GitHub Jobs")
            
        except Exception as e:
            logger.error(f"Error scraping GitHub Jobs: {e}", exc_info=True)
        finally:
            if page:
                await page.close()
        
        return jobs
    
    async def scrape_greenhouse_jobs(self, careers_url: str) -> List[Dict[str, Any]]:
        """
        Scrape Greenhouse careers board
        
        Args:
            careers_url: Company's Greenhouse URL (e.g., https://company.greenhouse.io/jobs)
        
        Returns:
            List of job dictionaries
        """
        jobs = []
        page = None
        
        try:
            page = await self.browser.new_page()
            logger.info(f"Scraping Greenhouse: {careers_url}")
            
            await page.goto(careers_url, wait_until="networkidle")
            
            # Greenhouse uses various selectors - try main ones
            selectors = [
                "div[class*='job-opening']",
                "div[class*='opening']",
                "section[class*='opening']",
                ".job-title",
                "[data-test-selector='job-title']"
            ]
            
            job_elements = []
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        job_elements = elements
                        logger.debug(f"Found {len(job_elements)} elements using selector: {selector}")
                        break
                except:
                    continue
            
            if not job_elements:
                logger.warning(f"No job elements found with any selector at {careers_url}")
                return jobs
            
            for job_elem in job_elements[:50]:  # Limit to 50 jobs per page
                try:
                    # Try to extract title
                    title_elem = await job_elem.query_selector("a")
                    if not title_elem:
                        title_elem = await job_elem.query_selector("[class*='title']")
                    
                    title = await title_elem.text_content() if title_elem else "N/A"
                    job_url = await title_elem.get_attribute("href") if title_elem else ""
                    
                    # Make URL absolute
                    if job_url and not job_url.startswith("http"):
                        job_url = urljoin(careers_url, job_url)
                    
                    # Try to extract department/category
                    dept_elem = await job_elem.query_selector("[class*='department']")
                    department = await dept_elem.text_content() if dept_elem else ""
                    
                    # Try to extract location
                    loc_elem = await job_elem.query_selector("[class*='location']")
                    location = await loc_elem.text_content() if loc_elem else ""
                    
                    if title and title.strip() != "N/A":
                        job = {
                            "title": title.strip(),
                            "department": department.strip() if department else "",
                            "location": location.strip() if location else "",
                            "url": job_url,
                            "source": "greenhouse",
                            "scraped_at": datetime.now().isoformat()
                        }
                        jobs.append(job)
                        logger.debug(f"Scraped Greenhouse job: {job['title']}")
                
                except Exception as e:
                    logger.debug(f"Error parsing Greenhouse job element: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(jobs)} jobs from Greenhouse at {careers_url}")
            
        except Exception as e:
            logger.error(f"Error scraping Greenhouse ({careers_url}): {e}", exc_info=True)
        finally:
            if page:
                await page.close()
        
        return jobs
    
    async def scrape_linkedin_jobs(self, search_query: str, location: str = "") -> List[Dict[str, Any]]:
        """
        Placeholder for LinkedIn scraping
        
        Note: LinkedIn actively blocks web scrapers. They have:
        - CAPTCHA challenges for automated detection
        - Bot detection via browser fingerprinting
        - Terms of Service that prohibit scraping
        - Rate limiting and IP blocking
        
        Recommended alternatives:
        1. Use LinkedIn API (requires approval)
        2. Use LinkedIn recruiter platform
        3. Use job aggregator APIs (Adzuna, GitHub Jobs API, etc.)
        4. Use data providers that have legal agreements
        
        Args:
            search_query: Job search query
            location: Location filter
        
        Returns:
            Empty list (not implemented)
        """
        logger.warning("LinkedIn scraping is blocked due to anti-bot measures. Use LinkedIn API instead.")
        return []
    
    async def scrape_all_sources(self, 
                                github_query: Optional[str] = None,
                                greenhouse_urls: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape all available job sources
        
        Args:
            github_query: Optional search query for GitHub Jobs
            greenhouse_urls: List of Greenhouse company URLs to scrape
        
        Returns:
            Dictionary with results from each source
        """
        results = {
            "github": [],
            "greenhouse": [],
            "linkedin": []
        }
        
        # GitHub Jobs
        if github_query:
            try:
                logger.info(f"Scraping GitHub Jobs for: {github_query}")
                results["github"] = await self.scrape_github_jobs(github_query)
            except Exception as e:
                logger.error(f"GitHub scraping failed: {e}")
                results["github"] = []
        
        # Greenhouse
        if greenhouse_urls:
            for url in greenhouse_urls:
                try:
                    logger.info(f"Scraping Greenhouse: {url}")
                    gh_jobs = await self.scrape_greenhouse_jobs(url)
                    results["greenhouse"].extend(gh_jobs)
                except Exception as e:
                    logger.error(f"Greenhouse scraping failed for {url}: {e}")
        
        # LinkedIn (not implemented)
        results["linkedin"] = []
        
        return results
