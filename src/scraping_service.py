#!/usr/bin/env python3
"""
Scraping Service for HR Tech Lead Generation System
Handles web scraping with retry logic and error handling
"""

import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from constants import SCRAPING_MAX_RETRIES, SCRAPING_TIMEOUT
from exceptions import NetworkError, ScrapingError

logger = logging.getLogger(__name__)


class ScrapingService:
    """Service for web scraping with retry logic"""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or self._create_session()

    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy"""
        session = requests.Session()

        retry_strategy = Retry(
            total=SCRAPING_MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        if not url or not isinstance(url, str):
            return False

        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in [
                "http",
                "https",
            ]
        except:
            return False

    def can_scrape(self, url: str) -> bool:
        """Check if URL can be scraped according to robots.txt"""
        if not self.is_valid_url(url):
            return False

        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124",
                "Accept-Encoding": "gzip, deflate",
            }

            response = self.session.get(robots_url, headers=headers, timeout=10)
            if response.status_code == 200:
                content = response.content.decode("utf-8", errors="ignore")
                rp = RobotFileParser()
                rp.parse(content.splitlines())
                allowed = rp.can_fetch("*", url)
                logger.info(f"Checked robots.txt for {url}: Allowed={allowed}")
                return allowed

            logger.warning(
                f"Failed to fetch robots.txt for {url}: Status {response.status_code}"
            )
            return True  # Assume allowed if can't check

        except Exception as e:
            logger.warning(
                f"Failed to check robots.txt for {url}: {e}, assuming scrape allowed"
            )
            return True

    def extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML content"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text and clean it up
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            return text
        except Exception as e:
            logger.warning(f"Error extracting text from HTML: {e}")
            return ""

    def scrape_url_content(self, url: str) -> Optional[Dict[str, str]]:
        """Scrape content from URL with retry logic"""
        if not self.is_valid_url(url):
            raise ScrapingError(f"Invalid URL format: {url}")

        if not self.can_scrape(url):
            raise ScrapingError(f"Scraping not allowed for URL: {url}")

        for attempt in range(SCRAPING_MAX_RETRIES):
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }

                response = self.session.get(
                    url, headers=headers, timeout=SCRAPING_TIMEOUT
                )
                response.raise_for_status()

                # Extract text content
                text_content = self.extract_text_from_html(response.text)

                if text_content and len(text_content) > 100:
                    title = BeautifulSoup(response.text, "html.parser").title
                    title_text = title.string if title else "No title"

                    return {"content": text_content, "title": title_text, "url": url}
                else:
                    logger.warning(f"Insufficient content extracted from {url}")
                    return None

            except requests.exceptions.RequestException as e:
                logger.warning(f"Scraping attempt {attempt + 1} failed for {url}: {e}")
                if attempt < SCRAPING_MAX_RETRIES - 1:
                    time.sleep(2**attempt)
                else:
                    raise NetworkError(
                        f"Failed to scrape {url} after {SCRAPING_MAX_RETRIES} attempts: {e}"
                    )
            except Exception as e:
                logger.error(f"Unexpected error scraping {url}: {e}")
                raise ScrapingError(f"Unexpected error scraping {url}: {e}")

        return None
