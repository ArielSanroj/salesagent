#!/usr/bin/env python3
"""
News Fetcher Service for HR Tech Lead Generation System
Handles fetching articles from NewsData.io API
"""

import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from constants import NEWS_API_CALL_LIMIT, NEWS_API_TIMEOUT, NEWSDATA_LATEST_URL

logger = logging.getLogger(__name__)


class NewsFetcher:
    """Fetches news articles from NewsData.io API"""

    def __init__(self, session, api_key: str):
        self.session = session
        self.api_key = api_key
        self.call_count = 0
        self.call_limit = NEWS_API_CALL_LIMIT

    def can_fetch(self) -> bool:
        """Check if we can make API calls"""
        if self.call_count >= self.call_limit:
            logger.warning("NewsData.io daily call limit reached")
            return False

        if not self.api_key:
            logger.warning("NEWSDATA_API_KEY not configured")
            return False

        return True

    def fetch_articles(
        self,
        query: str,
        num_results: int = 10,
        domains: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch news articles from NewsData.io API"""
        if not self.can_fetch():
            return []

        aggregated = []
        params = {
            "apikey": self.api_key,
            "q": query,
            "language": "en",
        }

        page_token = None
        max_pages = 5
        page_count = 0

        try:
            while len(aggregated) < num_results and page_count < max_pages:
                request_params = dict(params)
                if page_token:
                    request_params["page"] = page_token

                response = self.session.get(
                    NEWSDATA_LATEST_URL,
                    params=request_params,
                    timeout=NEWS_API_TIMEOUT
                )

                if not self._handle_response(response):
                    break

                response.raise_for_status()
                payload = response.json()

                if payload.get("status") != "success":
                    error_msg = payload.get("message", "NewsData.io API error")
                    logger.error(f"NewsData.io API error: {error_msg}")
                    break

                articles = payload.get("results", [])
                if not articles:
                    logger.info("No more articles available from NewsData.io")
                    break

                processed = self._process_articles(articles, domains, num_results)
                aggregated.extend(processed)

                page_token = payload.get("nextPage")
                page_count += 1

                if not page_token:
                    logger.info("Reached last page of NewsData.io results")
                    break

        except Exception as e:
            logger.error(f"Error fetching news articles: {e}")

        finally:
            self.call_count += 1

        logger.info(f"NewsData.io returned {len(aggregated)} articles for query '{query}'")
        return aggregated[:num_results]

    def _handle_response(self, response) -> bool:
        """Handle NewsData.io API response and return success status"""
        if response.status_code == 429:
            logger.warning("NewsData.io rate limit exceeded")
            return False
        elif response.status_code == 401:
            logger.error("NewsData.io API key invalid or expired")
            return False
        elif response.status_code == 403:
            logger.error("NewsData.io API access forbidden")
            return False
        elif response.status_code == 422:
            logger.error("NewsData.io invalid request parameters")
            return False

        return True

    def _process_articles(
        self,
        articles: List[Dict],
        domains: Optional[List[str]],
        num_results: int
    ) -> List[Dict]:
        """Process articles and filter by domains"""
        processed = []

        for article in articles:
            if len(processed) >= num_results:
                break

            url = article.get("link")
            if not url:
                continue

            if domains:
                parsed_domain = urlparse(url).netloc.lower()
                stripped_domain = (
                    parsed_domain[4:] if parsed_domain.startswith("www.") else parsed_domain
                )
                if stripped_domain not in domains:
                    continue

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
            processed.append(article_data)

        return processed


def create_news_fetcher(session, api_key: str) -> NewsFetcher:
    """Factory function to create NewsFetcher instance"""
    return NewsFetcher(session, api_key)
