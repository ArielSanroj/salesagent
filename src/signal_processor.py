#!/usr/bin/env python3
"""
Signal Processor for HR Tech Lead Generation System
Handles processing of different signal types and opportunity extraction
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from constants import DEFAULT_KEYWORDS, EMAIL_TEMPLATE_MAPPING, SIGNAL_TYPES
from exceptions import ValidationError
from models import Article, Opportunity, SearchQuery

logger = logging.getLogger(__name__)


class SignalProcessor:
    """Processes different signal types and extracts opportunities"""

    def __init__(self, llm_service=None, search_service=None, scraping_service=None):
        self.llm_service = llm_service
        self.search_service = search_service
        self.scraping_service = scraping_service

    def generate_queries(self, signal_id: int) -> List[str]:
        """Generate search queries for a specific signal type"""
        # Predefined queries for each signal type (more efficient than LLM generation)
        signal_queries = {
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

        return signal_queries.get(signal_id, signal_queries[1])

    def calculate_relevance_score(self, content: str, keywords: List[str]) -> float:
        """Calculate relevance score based on keyword presence"""
        if not content or not keywords:
            return 0.0

        content_lower = content.lower()
        keyword_matches = sum(
            1 for keyword in keywords if keyword.lower() in content_lower
        )

        # Base score from keyword matches
        base_score = min(keyword_matches / len(keywords), 1.0)

        # Bonus for multiple occurrences
        total_occurrences = sum(
            content_lower.count(keyword.lower()) for keyword in keywords
        )
        occurrence_bonus = min(total_occurrences * 0.1, 0.3)

        return min(base_score + occurrence_bonus, 1.0)

    def extract_company_name(self, text: str) -> Optional[str]:
        """Extract company name from text using LLM"""
        if not text or len(text) < 10:
            return None

        # Fallback if LLM service is not available
        if not self.llm_service:
            logger.warning(
                "LLM service not available, using fallback for company extraction"
            )
            return None

        prompt = f"""Extract the company name from this text. Return only the company name, nothing else.

Text: {text[:500]}

Company name:"""

        try:
            response = self.llm_service.invoke_sync(prompt, "company_extraction")
            if response and response != "Service temporarily unavailable":
                return response.strip()
        except Exception as e:
            logger.warning(f"Error extracting company name: {e}")

        return None

    def extract_person_name(self, text: str) -> Optional[str]:
        """Extract person name from text using LLM"""
        if not text or len(text) < 10:
            return None

        # Fallback if LLM service is not available
        if not self.llm_service:
            logger.warning(
                "LLM service not available, using fallback for person extraction"
            )
            return None

        prompt = f"""Extract the person's name (CHRO, HR leader, or executive) from this text. Return only the full name, nothing else.

Text: {text[:500]}

Person name:"""

        try:
            response = self.llm_service.invoke_sync(prompt, "person_extraction")
            if response and response != "Service temporarily unavailable":
                return response.strip()
        except Exception as e:
            logger.warning(f"Error extracting person name: {e}")

        return None

    def extract_email(self, company: str, person: str) -> str:
        """Extract email using LLM with fallback"""
        if not company or not person or person.lower() in ["unknown", ""]:
            return "Manual validation needed"

        # Fallback if LLM service is not available
        if not self.llm_service:
            logger.warning("LLM service not available, using fallback for email finder")
            return "Manual validation needed"

        prompt = f"""Given company '{company}' and person '{person}', suggest the most likely email format.

Return ONLY the email address in this format: firstname.lastname@company.com

Examples:
- Company: Google, Person: John Smith → john.smith@google.com
- Company: Microsoft, Person: Jane Doe → jane.doe@microsoft.com

Company: {company}
Person: {person}
Email:"""

        try:
            response = self.llm_service.invoke_sync(prompt, "email_finder")
            if response and response != "Service temporarily unavailable":
                # Clean up the response
                if "@" in response:
                    email = response.split("\n")[-1].strip()
                    if "@" in email and "." in email and self._is_valid_email(email):
                        logger.info(
                            f"LLM suggested email for {person} at {company}: {email}"
                        )
                        return email

            logger.warning(f"LLM returned invalid email format: {response}")
            return "Manual validation needed"
        except Exception as e:
            logger.error(f"LLM email finder failed for {company}, {person}: {e}")
            return "Manual validation needed"

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        if not email or not isinstance(email, str):
            return False

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def parse_article_date(self, date_str: str) -> Optional[str]:
        """Parse article date string to YYYY-MM-DD format"""
        if not date_str:
            return None

        try:
            from dateutil.parser import parse as parse_date

            parsed_date = parse_date(date_str)
            return parsed_date.strftime("%Y-%m-%d")
        except Exception:
            return None

    def process_article(
        self, article: Dict[str, Any], signal_type: int
    ) -> Optional[Opportunity]:
        """Process a single article and extract opportunity"""
        try:
            # Extract basic information
            title = article.get("title", "")
            url = article.get("url", "")
            date = article.get("publishedAt", "")

            if not title or not url:
                return None

            # Scrape content if scraping service is available
            content = ""
            if self.scraping_service:
                try:
                    scraped_content = self.scraping_service.scrape_url_content(url)
                    if scraped_content:
                        content = scraped_content["content"]
                except Exception as e:
                    logger.warning(f"Failed to scrape content from {url}: {e}")
                    content = article.get("content", "")
            else:
                content = article.get("content", "")

            if not content:
                return None

            # Extract company and person using LLM
            company = self.extract_company_name(content)
            person = self.extract_person_name(content)

            if not company:
                return None

            # Calculate relevance score
            keywords = DEFAULT_KEYWORDS
            relevance_score = self.calculate_relevance_score(content, keywords)

            # Apply quality thresholds
            if relevance_score < 0.7:  # Use constant from constants.py
                return None

            # Find email
            email = "Manual validation needed"
            if person and person != "Unknown":
                email = self.extract_email(company, person)

            # Create opportunity
            opportunity = Opportunity(
                title=title,
                company=company,
                person=person or "Unknown",
                email=email,
                url=url,
                date=self.parse_article_date(date)
                or datetime.now().strftime("%Y-%m-%d"),
                content=content[:1000],  # Truncate for storage
                relevance_score=relevance_score,
                signal_type=signal_type,
                source=article.get("source", "Unknown"),
            )

            logger.info(
                f"Processed opportunity: {company} - {person} (Score: {relevance_score:.2f})"
            )
            return opportunity

        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return None

    def process_signal(
        self, signal_id: int, max_results: int = 10
    ) -> List[Opportunity]:
        """Process a specific signal type and return opportunities"""
        logger.info(
            f"Processing signal {signal_id}: {SIGNAL_TYPES.get(signal_id, 'Unknown')}"
        )

        # Generate queries for this signal
        queries = self.generate_queries(signal_id)

        # Search for articles
        all_articles = []
        if self.search_service:
            for query in queries:
                articles = self.search_service.search_articles(
                    query, max_results // len(queries)
                )
                all_articles.extend(articles)

        if not all_articles:
            logger.warning(f"No articles found for signal {signal_id}")
            return []

        # Process articles into opportunities
        opportunities = []
        for article in all_articles:
            opportunity = self.process_article(article, signal_id)
            if opportunity:
                opportunities.append(opportunity)

        logger.info(
            f"Signal {signal_id} completed: {len(opportunities)} opportunities found"
        )
        return opportunities
