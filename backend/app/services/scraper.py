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
    
    async def scrape_indeed_jobs(self, search_query: str, location: str = "USA") -> List[Dict[str, Any]]:
        """
        Scrape Indeed job listings
        
        Args:
            search_query: Job search query (e.g., "python developer", "backend engineer")
            location: Location filter (default: USA)
        
        Returns:
            List of job dictionaries from Indeed
        """
        jobs = []
        page = None
        
        try:
            page = await self.browser.new_page()
            url = f"https://www.indeed.com/jobs?q={search_query}&l={location}"
            
            logger.info(f"Scraping Indeed: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            
            # Wait a bit for JS to render
            await page.wait_for_timeout(2000)
            
            # Get all job cards
            job_elements = await page.query_selector_all("div.job_seen_beacon")
            logger.info(f"Found {len(job_elements)} job elements on Indeed")
            
            for job_elem in job_elements[:100]:  # Limit to 100 jobs per page
                try:
                    # Extract job title
                    title_elem = await job_elem.query_selector("h2.jobTitle span")
                    title = await title_elem.text_content() if title_elem else "N/A"
                    
                    # Extract company name
                    company_elem = await job_elem.query_selector("span.companyName")
                    company = await company_elem.text_content() if company_elem else "N/A"
                    
                    # Extract location
                    loc_elem = await job_elem.query_selector("div.companyLocation")
                    location_text = await loc_elem.text_content() if loc_elem else "Unknown"
                    
                    # Extract job URL
                    link_elem = await job_elem.query_selector("h2.jobTitle a")
                    job_url = await link_elem.get_attribute("href") if link_elem else ""
                    
                    if job_url and not job_url.startswith("http"):
                        job_url = f"https://www.indeed.com{job_url}"
                    
                    # Extract job ID from URL
                    job_id = job_url.split("jk=")[-1].split("&")[0] if "jk=" in job_url else ""
                    
                    # Extract snippet/summary
                    snippet_elem = await job_elem.query_selector("div.job-snippet")
                    snippet = await snippet_elem.text_content() if snippet_elem else ""
                    
                    if title and title.strip() != "N/A":
                        job = {
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": location_text.strip(),
                            "url": job_url,
                            "external_id": job_id,
                            "source": "indeed",
                            "description_snippet": snippet.strip() if snippet else "",
                            "scraped_at": datetime.now().isoformat()
                        }
                        jobs.append(job)
                        logger.debug(f"Scraped Indeed job: {job['title']} at {job['company']}")
                
                except Exception as e:
                    logger.debug(f"Error parsing Indeed job element: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(jobs)} jobs from Indeed")
            
        except Exception as e:
            logger.error(f"Error scraping Indeed: {e}", exc_info=True)
        finally:
            if page:
                await page.close()
        
        return jobs
    
    async def scrape_glassdoor_jobs(self, search_query: str, location: str = "United States") -> List[Dict[str, Any]]:
        """
        Scrape Glassdoor job listings
        
        Args:
            search_query: Job search query
            location: Location filter
        
        Returns:
            List of job dictionaries from Glassdoor
        """
        jobs = []
        page = None
        
        try:
            page = await self.browser.new_page()
            # Glassdoor requires query params for search
            url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={search_query}&locT=C&locId=1"
            
            logger.info(f"Scraping Glassdoor: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            
            # Wait for content to load
            await page.wait_for_timeout(2000)
            
            # Get all job cards - Glassdoor uses CSS module naming
            job_elements = await page.query_selector_all("[data-test='jobs-search-results-item']")
            logger.info(f"Found {len(job_elements)} job elements on Glassdoor")
            
            for job_elem in job_elements[:100]:  # Limit to 100 jobs
                try:
                    # Extract job title
                    title_elem = await job_elem.query_selector("jobTitle")
                    if not title_elem:
                        title_elem = await job_elem.query_selector("[data-test='job-link']")
                    title = await title_elem.text_content() if title_elem else "N/A"
                    
                    # Extract job URL and ID
                    link_elem = await job_elem.query_selector("a")
                    job_url = await link_elem.get_attribute("href") if link_elem else ""
                    if job_url and not job_url.startswith("http"):
                        job_url = f"https://www.glassdoor.com{job_url}"
                    
                    # Extract company name
                    company_elem = await job_elem.query_selector("[data-test='employer-name']")
                    company = await company_elem.text_content() if company_elem else "N/A"
                    
                    # Extract location
                    loc_elem = await job_elem.query_selector("[data-test='job-location']")
                    location_text = await loc_elem.text_content() if loc_elem else "Unknown"
                    
                    # Extract salary if available
                    salary_elem = await job_elem.query_selector("[data-test='job-salary']")
                    salary = await salary_elem.text_content() if salary_elem else ""
                    
                    if title and title.strip() != "N/A":
                        # Extract job ID from URL if available
                        job_id = job_url.split("jobListingId=")[-1].split("&")[0] if "jobListingId=" in job_url else ""
                        
                        job = {
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": location_text.strip(),
                            "url": job_url,
                            "external_id": job_id,
                            "source": "glassdoor",
                            "salary": salary.strip() if salary else "",
                            "scraped_at": datetime.now().isoformat()
                        }
                        jobs.append(job)
                        logger.debug(f"Scraped Glassdoor job: {job['title']} at {job['company']}")
                
                except Exception as e:
                    logger.debug(f"Error parsing Glassdoor job element: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(jobs)} jobs from Glassdoor")
            
        except Exception as e:
            logger.error(f"Error scraping Glassdoor: {e}", exc_info=True)
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
                                search_query: str = "software engineer",
                                location: str = "USA",
                                github_query: Optional[str] = None,
                                greenhouse_urls: Optional[List[str]] = None,
                                scrape_indeed: bool = True,
                                scrape_glassdoor: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape all available job sources
        
        Args:
            search_query: Default search query for job boards
            location: Default location filter
            github_query: Optional search query for GitHub Jobs
            greenhouse_urls: List of Greenhouse company URLs to scrape
            scrape_indeed: Whether to scrape Indeed
            scrape_glassdoor: Whether to scrape Glassdoor
        
        Returns:
            Dictionary with results from each source
        """
        results = {
            "github": [],
            "greenhouse": [],
            "indeed": [],
            "glassdoor": [],
            "linkedin": [],
            "stats": {
                "total_scraped": 0,
                "scrape_timestamp": datetime.now().isoformat()
            }
        }
        
        # GitHub Jobs
        if github_query:
            try:
                logger.info(f"Scraping GitHub Jobs for: {github_query}")
                results["github"] = await self.scrape_github_jobs(github_query)
                results["stats"]["total_scraped"] += len(results["github"])
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
                    results["stats"]["total_scraped"] += len(gh_jobs)
                except Exception as e:
                    logger.error(f"Greenhouse scraping failed for {url}: {e}")
        
        # Indeed
        if scrape_indeed:
            try:
                logger.info(f"Scraping Indeed for: {search_query} in {location}")
                results["indeed"] = await self.scrape_indeed_jobs(search_query, location)
                results["stats"]["total_scraped"] += len(results["indeed"])
            except Exception as e:
                logger.error(f"Indeed scraping failed: {e}")
                results["indeed"] = []
        
        # Glassdoor
        if scrape_glassdoor:
            try:
                logger.info(f"Scraping Glassdoor for: {search_query}")
                results["glassdoor"] = await self.scrape_glassdoor_jobs(search_query, location)
                results["stats"]["total_scraped"] += len(results["glassdoor"])
            except Exception as e:
                logger.error(f"Glassdoor scraping failed: {e}")
                results["glassdoor"] = []
        
        # LinkedIn (not supported due to anti-bot measures)
        results["linkedin"] = []
        
        return results
    
    @staticmethod
    def normalize_job_data(job_dict: Dict[str, Any], company_id: str) -> Dict[str, Any]:
        """
        Normalize job data from different sources into consistent format
        
        Args:
            job_dict: Raw job data from scraper
            company_id: Company UUID to associate with job
        
        Returns:
            Normalized job dictionary for database insertion
        """
        return {
            "company_id": company_id,
            "title": job_dict.get("title", "Unknown Position").strip(),
            "url": job_dict.get("url", ""),
            "source": job_dict.get("source", "unknown"),
            "external_job_id": job_dict.get("external_id", ""),
            "location": job_dict.get("location", "Remote"),
            "scraped_at": job_dict.get("scraped_at"),
            "raw_jd": job_dict.get("description_snippet", ""),
            "parsed_jd": {
                "company_name": job_dict.get("company", ""),
                "position": job_dict.get("title", ""),
                "location": job_dict.get("location", ""),
                "salary": job_dict.get("salary", ""),
                "department": job_dict.get("department", ""),
                "source": job_dict.get("source", ""),
            }
        }
    
    @staticmethod
    def is_duplicate_job(job_url: str, existing_urls: List[str], existing_external_ids: Dict[str, str]) -> bool:
        """
        Check if a job is a duplicate based on URL and external IDs
        
        Args:
            job_url: Job URL to check
            existing_urls: List of URLs already in database
            existing_external_ids: Dict mapping source to external_id of existing jobs
        
        Returns:
            True if job appears to be a duplicate
        """
        # Check exact URL match
        if job_url in existing_urls:
            logger.debug(f"Duplicate found: URL match {job_url}")
            return True
        
        # Check for similar URLs (same job, different tracking params)
        base_url = job_url.split("?")[0].split("#")[0]
        for existing_url in existing_urls:
            existing_base = existing_url.split("?")[0].split("#")[0]
            if base_url == existing_base and len(base_url) > 20:  # Avoid false positives on short URLs
                logger.debug(f"Duplicate found: Base URL match {base_url}")
                return True
        
        return False
