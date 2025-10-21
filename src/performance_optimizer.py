#!/usr/bin/env python3
"""
Performance Optimizer for HR Tech Lead Generation System
Implements async scraping, caching, and performance optimizations
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path

import aiohttp
from aiohttp import ClientTimeout, ClientSession

from exceptions import NetworkError, ScrapingError
from constants import SCRAPING_TIMEOUT, SCRAPING_MAX_RETRIES

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching for scraped content and API responses"""
    
    def __init__(self, cache_dir: str = "cache", ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_hours = ttl_hours
    
    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path"""
        return self.cache_dir / f"{cache_key}.json"
    
    def get_cached_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached content for URL"""
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Check TTL
            cached_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cached_time > timedelta(hours=self.ttl_hours):
                cache_path.unlink()  # Remove expired cache
                return None
            
            logger.info(f"Cache hit for {url}")
            return data['content']
        
        except Exception as e:
            logger.warning(f"Error reading cache for {url}: {e}")
            return None
    
    def set_cached_content(self, url: str, content: Dict[str, Any]) -> None:
        """Cache content for URL"""
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'content': content
            }
            
            with open(cache_path, 'w') as f:
                json.dump(data, f)
            
            logger.info(f"Cached content for {url}")
        
        except Exception as e:
            logger.warning(f"Error caching content for {url}: {e}")


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
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
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
                        
                        # Extract text content
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.decompose()
                        
                        # Get text and clean it up
                        text = soup.get_text()
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text_content = ' '.join(chunk for chunk in chunks if chunk)
                        
                        if text_content and len(text_content) > 100:
                            title = soup.title.string if soup.title else "No title"
                            
                            result = {
                                'content': text_content,
                                'title': title,
                                'url': url
                            }
                            
                            # Cache the result
                            self.cache_manager.set_cached_content(url, result)
                            
                            return result
                        else:
                            logger.warning(f"Insufficient content extracted from {url}")
                            return None
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        if attempt < SCRAPING_MAX_RETRIES - 1:
                            await asyncio.sleep(2 ** attempt)
                        else:
                            return None
            
            except asyncio.TimeoutError:
                logger.warning(f"Timeout scraping {url} (attempt {attempt + 1})")
                if attempt < SCRAPING_MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return None
            
            except Exception as e:
                logger.warning(f"Error scraping {url} (attempt {attempt + 1}): {e}")
                if attempt < SCRAPING_MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return None
        
        return None
    
    async def scrape_urls_batch(self, urls: List[str], max_concurrent: int = 10) -> List[Optional[Dict[str, str]]]:
        """Scrape multiple URLs concurrently with rate limiting"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url: str) -> Optional[Dict[str, str]]:
            async with semaphore:
                return await self.scrape_url_async(url)
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return only successful results
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Scraping task failed: {result}")
                valid_results.append(None)
            else:
                valid_results.append(result)
        
        return valid_results


class PerformanceOptimizer:
    """Main performance optimizer that coordinates async operations"""
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.scraping_service = AsyncScrapingService(self.cache_manager)
    
    async def process_opportunities_async(self, articles: List[Dict[str, Any]], signal_processor) -> List[Any]:
        """Process opportunities asynchronously"""
        # Extract URLs for batch scraping
        urls = [article.get('url') for article in articles if article.get('url')]
        
        if not urls:
            return []
        
        # Scrape all URLs concurrently
        async with self.scraping_service:
            scraped_contents = await self.scraping_service.scrape_urls_batch(urls)
        
        # Process scraped content
        opportunities = []
        for i, article in enumerate(articles):
            if i < len(scraped_contents) and scraped_contents[i]:
                # Update article with scraped content
                article['scraped_content'] = scraped_contents[i]['content']
                article['scraped_title'] = scraped_contents[i]['title']
                
                # Process opportunity
                opportunity = signal_processor.process_article(article, article.get('signal_type', 1))
                if opportunity:
                    opportunities.append(opportunity)
        
        return opportunities
    
    def optimize_llm_calls(self, queries: List[str]) -> List[str]:
        """Optimize LLM calls by using predefined queries instead of generating them"""
        # Use predefined queries instead of LLM generation for better performance
        optimized_queries = []
        
        for query in queries:
            # Simple keyword extraction without LLM
            keywords = query.lower().split()
            if len(keywords) > 3:
                # Take first 3 keywords for efficiency
                optimized_query = ' '.join(keywords[:3])
                optimized_queries.append(optimized_query)
            else:
                optimized_queries.append(query)
        
        return optimized_queries
    
    def batch_process_opportunities(self, opportunities: List[Any], batch_size: int = 10) -> List[List[Any]]:
        """Process opportunities in batches for better memory management"""
        batches = []
        for i in range(0, len(opportunities), batch_size):
            batch = opportunities[i:i + batch_size]
            batches.append(batch)
        
        return batches
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        cache_dir = self.cache_manager.cache_dir
        cache_files = list(cache_dir.glob("*.json"))
        
        return {
            "cache_size": len(cache_files),
            "cache_dir": str(cache_dir),
            "timestamp": datetime.now().isoformat()
        }
