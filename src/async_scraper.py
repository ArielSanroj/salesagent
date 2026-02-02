#!/usr/bin/env python3
"""
Async Scraping Service for HR Tech Lead Generation System
Implements async scraping with connection pooling
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from bs4 import BeautifulSoup

from cache_manager import CacheManager
from constants import SCRAPING_MAX_RETRIES, SCRAPING_TIMEOUT

logger = logging.getLogger(__name__)


class AsyncScrapingService:
    """Async scraping service with connection pooling and caching"""

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache_manager = cache_manager or CacheManager()
        self.session: Optional[ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        timeout = ClientTimeout(total=SCRAPING_TIMEOUT)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        self.session = ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def scrape_url_async(self, url: str) -> Optional[Dict[str, str]]:
        """Scrape URL content asynchronously"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        # Check cache first
        cached_content = self.cache_manager.get_cached_content(url)
        if cached_content:
            return cached_content

        for attempt in range(SCRAPING_MAX_RETRIES):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        result = self._extract_content(html_content, url)

                        if result:
                            self.cache_manager.set_cached_content(url, result)
                            return result

                        logger.warning(f"Insufficient content from {url}")
                        return None
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        if attempt < SCRAPING_MAX_RETRIES - 1:
                            await asyncio.sleep(2**attempt)

            except asyncio.TimeoutError:
                logger.warning(f"Timeout scraping {url} (attempt {attempt + 1})")
                if attempt < SCRAPING_MAX_RETRIES - 1:
                    await asyncio.sleep(2**attempt)

            except Exception as e:
                logger.warning(f"Error scraping {url} (attempt {attempt + 1}): {e}")
                if attempt < SCRAPING_MAX_RETRIES - 1:
                    await asyncio.sleep(2**attempt)

        return None

    def _extract_content(self, html_content: str, url: str) -> Optional[Dict[str, str]]:
        """Extract text content from HTML"""
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text and clean it up
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text_content = " ".join(chunk for chunk in chunks if chunk)

        if text_content and len(text_content) > 100:
            title = soup.title.string if soup.title else "No title"
            return {
                "content": text_content,
                "title": title,
                "url": url,
            }

        return None

    async def scrape_urls_batch(
        self, urls: List[str], max_concurrent: int = 10
    ) -> List[Optional[Dict[str, str]]]:
        """Scrape multiple URLs concurrently with rate limiting"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(url: str) -> Optional[Dict[str, str]]:
            async with semaphore:
                return await self.scrape_url_async(url)

        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Scraping task failed: {result}")
                valid_results.append(None)
            else:
                valid_results.append(result)

        return valid_results
