#!/usr/bin/env python3
"""
Signal Processor for HR Tech Lead Generation System
Handles processing of different signal types and opportunity extraction
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from constants import DEFAULT_KEYWORDS, SIGNAL_TYPES
from data_enrichment import (
    calculate_relevance_score,
    extract_company_name,
    extract_person_name,
    find_email_with_llm,
)
from models import Opportunity

logger = logging.getLogger(__name__)


# Predefined queries for each signal type
SIGNAL_QUERIES = {
    1: [
        "HR technology evaluation software solutions",
        "HR tech assessment tools",
        "human resources technology evaluation",
    ],
    2: [
        "new CHRO chief human resources officer appointed",
        "new HR director hired",
        "chief people officer appointment",
    ],
    3: [
        "HR tech content website blog",
        "human resources technology insights",
        "HR software case studies",
    ],
    4: [
        "HR system migration technology change",
        "workday implementation project",
        "HR tech stack transition",
    ],
    5: [
        "company expansion growth hiring HR",
        "startup funding HR technology",
        "HR tech investment announcement",
    ],
    6: [
        "HR team hiring downsizing restructuring",
        "human resources job openings",
        "HR director recruitment",
    ],
}


class SignalProcessor:
    """Processes different signal types and extracts opportunities"""

    def __init__(
        self,
        llm_service=None,
        search_service=None,
        scraping_service=None,
        performance_optimizer=None,
        quality_config: Optional[Dict[str, Any]] = None,
    ):
        self.llm_service = llm_service
        self.search_service = search_service
        self.scraping_service = scraping_service
        self.performance_optimizer = performance_optimizer
        self.quality_config = quality_config or {}
        self.min_relevance_score = float(
            self.quality_config.get("min_relevance_score", 0.7)
        )
        low_conf_default = max(self.min_relevance_score - 0.15, 0.3)
        self.low_confidence_score = float(
            self.quality_config.get("low_confidence_score", low_conf_default)
        )

    def generate_queries(self, signal_id: int) -> List[str]:
        """Generate search queries for a specific signal type"""
        return SIGNAL_QUERIES.get(signal_id, SIGNAL_QUERIES[1])

    def _parse_article_date(self, date_str: str) -> Optional[str]:
        """Parse article date string to YYYY-MM-DD format"""
        if not date_str:
            return None

        try:
            from dateutil.parser import parse as parse_date
            parsed_date = parse_date(date_str)
            return parsed_date.strftime("%Y-%m-%d")
        except Exception:
            return None

    def _fallback_company_from_article(
        self, article: Dict[str, Any], content: str
    ) -> Optional[str]:
        """Derive a best-effort company name when LLM cannot extract one"""
        candidates = [
            article.get("company"),
            article.get("source"),
            article.get("source_id"),
        ]

        url = article.get("url")
        if url:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
                if domain:
                    candidates.append(domain)
            except Exception:
                pass

        import re
        snippet = article.get("snippet") or article.get("title") or content[:200]
        if snippet:
            match = re.search(
                r"([A-Z][A-Za-z0-9&]+(?:\s+[A-Z][A-Za-z0-9&]+)*)", snippet
            )
            if match:
                candidates.append(match.group(1))

        for candidate in candidates:
            if candidate and isinstance(candidate, str):
                cleaned = candidate.strip()
                if cleaned:
                    return cleaned

        return None

    def process_article(
        self, article: Dict[str, Any], signal_type: int
    ) -> Optional[Opportunity]:
        """Process a single article and extract opportunity"""
        try:
            title = article.get("title", "")
            url = article.get("url", "")
            date = article.get("publishedAt", "")

            if not title or not url:
                return None

            # Scrape content
            content = ""
            if self.scraping_service:
                try:
                    scraped = self.scraping_service.scrape_url_content(url)
                    if scraped:
                        content = scraped["content"]
                except Exception as e:
                    logger.warning(f"Failed to scrape {url}: {e}")
                    content = article.get("content", "")
            else:
                content = article.get("content", "")

            if not content:
                return None

            # Extract company and person using shared functions
            logger.info(f"Extracting company name from: {url}")
            company = extract_company_name(content, self.llm_service)

            if not company:
                company = self._fallback_company_from_article(article, content)
                if company:
                    logger.info(f"Using fallback company: {company}")
                else:
                    logger.warning(f"No company found in: {url}")
                    return None

            logger.info(f"Extracting person name from: {url}")
            person = extract_person_name(content, self.llm_service)

            # Calculate relevance score
            relevance_score = calculate_relevance_score(content, DEFAULT_KEYWORDS)
            logger.info(f"Relevance score: {relevance_score:.2f}")

            # Apply quality thresholds
            needs_manual_review = False
            if relevance_score < self.min_relevance_score:
                if relevance_score >= self.low_confidence_score:
                    needs_manual_review = True
                    logger.info(f"Relevance {relevance_score:.2f} below threshold, keeping for review")
                else:
                    logger.warning(f"Relevance {relevance_score:.2f} too low, skipping")
                    return None

            # Find email
            email = "Manual validation needed"
            if person and person != "Unknown":
                logger.info(f"Finding email for {person} at {company}")
                email = find_email_with_llm(company, person, self.llm_service)

            # Create opportunity
            source_label = article.get("source", "Unknown")
            if needs_manual_review:
                source_label = f"{source_label} | Needs Review"

            opportunity = Opportunity(
                title=title,
                company=company,
                person=person or "Unknown",
                email=email,
                url=url,
                date=self._parse_article_date(date) or datetime.now().strftime("%Y-%m-%d"),
                content=content[:1000],
                relevance_score=relevance_score,
                signal_type=signal_type,
                source=source_label,
            )

            logger.info(f"OPPORTUNITY: {company} - {person} (Score: {relevance_score:.2f})")
            return opportunity

        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return None

    def process_signal(
        self, signal_id: int, max_results: int = 10
    ) -> List[Opportunity]:
        """Process a specific signal type and return opportunities"""
        signal_name = SIGNAL_TYPES.get(signal_id, "Unknown")
        logger.info(f"Processing signal {signal_id}: {signal_name}")

        # Generate queries
        base_queries = self.generate_queries(signal_id)

        # Optimize queries if optimizer available
        if self.performance_optimizer:
            queries = self.performance_optimizer.get_optimized_queries_for_signal(
                signal_id, base_queries
            )
            logger.info(f"LLM optimized queries: {queries}")
        else:
            queries = base_queries

        # Search for articles
        all_articles = []
        if self.search_service:
            for i, query in enumerate(queries):
                logger.info(f"Searching query {i+1}/{len(queries)}: '{query}'")
                articles = self.search_service.search_articles(
                    query, max_results // len(queries)
                )
                logger.info(f"Found {len(articles)} articles for query: '{query}'")
                all_articles.extend(articles)

        if not all_articles:
            logger.warning(f"No articles found for signal {signal_id}")
            return []

        logger.info(f"Total articles found: {len(all_articles)}")

        # Process articles into opportunities
        opportunities = []
        for i, article in enumerate(all_articles):
            logger.info(f"Processing article {i+1}/{len(all_articles)}")
            opportunity = self.process_article(article, signal_id)
            if opportunity:
                opportunities.append(opportunity)

        # Analyze results for optimization
        if self.performance_optimizer and opportunities:
            self.performance_optimizer.analyze_and_optimize_from_results(
                opportunities, queries, signal_id
            )

        logger.info(f"Signal {signal_id} completed: {len(opportunities)} opportunities")
        return opportunities
