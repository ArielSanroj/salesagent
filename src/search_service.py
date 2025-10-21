#!/usr/bin/env python3
"""
Search Service for HR Tech Lead Generation System
Handles news article search with multiple providers
"""

import logging
import time
from typing import List, Dict, Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from exceptions import APIServiceError, RateLimitError, AuthenticationError, NetworkError
from constants import (
    NEWSDATA_LATEST_URL, NEWS_API_TIMEOUT, NEWS_API_MAX_RETRIES,
    RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD
)

logger = logging.getLogger(__name__)


class SearchService:
    """Service for searching news articles"""
    
    def __init__(self, session: Optional[requests.Session] = None, api_key: Optional[str] = None):
        self.session = session or self._create_session()
        self.api_key = api_key
        self.call_count = 0
        self.call_limit = 50  # Default limit
    
    def _create_session(self) -> requests.Session:
        """Create HTTP session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=NEWS_API_MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def set_api_key(self, api_key: str) -> None:
        """Set API key for the service"""
        self.api_key = api_key
    
    def set_call_limit(self, limit: int) -> None:
        """Set API call limit"""
        self.call_limit = limit
    
    def _check_rate_limit(self) -> bool:
        """Check if we've exceeded the rate limit"""
        if self.call_count >= self.call_limit:
            logger.warning(f"API call limit reached: {self.call_count}/{self.call_limit}")
            return False
        return True
    
    def search_newsdata(self, query: str, num_results: int = 10, domains: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for news articles using NewsData.io API"""
        if not self._check_rate_limit():
            return []
        
        if not self.api_key:
            logger.warning("NewsData API key not configured")
            return []
        
        aggregated = []
        endpoint = NEWSDATA_LATEST_URL
        
        # Build base parameters
        params = {
            "apikey": self.api_key,
            "q": query,
            "language": "en",
        }
        
        page_token = None
        max_pages = 5  # Prevent infinite loops
        page_count = 0
        
        try:
            while len(aggregated) < num_results and page_count < max_pages:
                request_params = dict(params)
                if page_token:
                    request_params["page"] = page_token
                
                response = self.session.get(endpoint, params=request_params, timeout=NEWS_API_TIMEOUT)
                
                # Handle rate limiting
                if response.status_code == 429:
                    logger.warning("NewsData.io rate limit exceeded")
                    break
                
                # Handle other HTTP errors
                if response.status_code == 401:
                    raise AuthenticationError("NewsData.io API key invalid or expired")
                elif response.status_code == 403:
                    raise AuthenticationError("NewsData.io API access forbidden")
                elif response.status_code == 422:
                    raise APIServiceError("NewsData.io invalid request parameters")
                
                response.raise_for_status()
                payload = response.json()
                
                # Check API response status
                if payload.get("status") != "success":
                    error_msg = payload.get("message", "NewsData.io API error")
                    raise APIServiceError(f"NewsData.io API error: {error_msg}")
                
                articles = payload.get("results", [])
                if not articles:
                    logger.info("No more articles available from NewsData.io")
                    break
                
                for article in articles:
                    if len(aggregated) >= num_results:
                        break
                    
                    url = article.get("link")
                    if not url:
                        continue
                    
                    # Filter by domains if specified
                    if domains:
                        from urllib.parse import urlparse
                        parsed_domain = urlparse(url).netloc.lower()
                        stripped_domain = parsed_domain[4:] if parsed_domain.startswith("www.") else parsed_domain
                        if stripped_domain not in domains:
                            continue
                    
                    # Build standardized article object
                    article_data = {
                        "url": url,
                        "title": article.get("title", ""),
                        "snippet": article.get("description", ""),
                        "source": article.get("source_name", article.get("source_id", "")),
                        "source_id": article.get("source_id", ""),
                        "content": article.get("content", ""),
                        "publishedAt": article.get("pubDate"),
                        "keywords": article.get("keywords", []),
                        "creator": article.get("creator", []),
                        "category": article.get("category", []),
                        "country": article.get("country", []),
                        "language": article.get("language", "english"),
                        "image_url": article.get("image_url"),
                        "article_id": article.get("article_id"),
                    }
                    
                    aggregated.append(article_data)
                
                page_token = payload.get("nextPage")
                page_count += 1
                
                if not page_token:
                    logger.info("Reached last page of NewsData.io results")
                    break
                
                # Rate limiting
                time.sleep(1)
        
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"NewsData.io request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in NewsData.io search: {e}")
            raise APIServiceError(f"NewsData.io search failed: {e}")
        finally:
            self.call_count += 1
        
        logger.info(f"NewsData.io returned {len(aggregated)} articles for query '{query}'")
        return aggregated[:num_results]
    
    def search_articles(self, query: str, num_results: int = 10, domains: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for articles using available providers"""
        try:
            return self.search_newsdata(query, num_results, domains)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_call_count(self) -> int:
        """Get current API call count"""
        return self.call_count
    
    def reset_call_count(self) -> None:
        """Reset API call count"""
        self.call_count = 0
