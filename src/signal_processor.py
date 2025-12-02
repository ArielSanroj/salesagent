#!/usr/bin/env python3
"""
Signal Processor for HR Tech Lead Generation System
Handles processing of different signal types and opportunity extraction
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from constants import DEFAULT_KEYWORDS, EMAIL_TEMPLATE_MAPPING, SIGNAL_TYPES
from exceptions import ValidationError
from models import Article, Opportunity, SearchQuery

logger = logging.getLogger(__name__)


class SignalProcessor:
    """Processes different signal types and extracts opportunities"""

    def __init__(
        self,
        llm_service=None,
        search_service=None,
        scraping_service=None,
        quality_config: Optional[Dict[str, Any]] = None,
    ):
        self.llm_service = llm_service
        self.search_service = search_service
        self.scraping_service = scraping_service
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
        """Extract company name from text using LLM, prioritizing actual companies over news sources"""
        if not text or len(text) < 10:
            return None

        # Fallback if LLM service is not available
        if not self.llm_service:
            logger.warning(
                "LLM service not available, using fallback for company extraction"
            )
            return None

        # Improved prompt to identify actual companies (not news publishers)
        prompt = f"""Extract the ACTUAL COMPANY NAME mentioned in this article, NOT the news website or publisher.

CRITICAL: Return ONLY the company name, nothing else. No explanations, no "the company is" text, just the name.

Avoid news sources like: Postregister, Hastingstribune, SHRM, PR Newswire, Deloitte (if article), Mercer (if article), etc.

Look for:
- Companies that are the SUBJECT of the article (e.g., "Rally House", "McLean & Company", "Smartstream")
- Companies mentioned in quotes or as the main topic
- Companies that are doing something (receiving awards, making announcements, etc.)

Text: {text[:1000]}

Company name:"""

        try:
            response = self.llm_service.invoke_sync(prompt, "company_extraction")
            if response and response != "Service temporarily unavailable":
                cleaned = self._clean_llm_response(response, extract_type="company")
                # Filter out common news sources
                news_sources = [
                    "postregister",
                    "hastingstribune",
                    "shrm",
                    "pr newswire",
                    "prnewswire",
                    "deloitte",
                    "mercer",
                    "fintech finance",
                    "ffnews",
                ]
                if cleaned and cleaned.lower() not in [
                    ns.lower() for ns in news_sources
                ]:
                    logger.info(f"✅ Extracted company: {cleaned}")
                    return cleaned
                else:
                    logger.warning(
                        f"⚠️  Extracted company appears to be news source: {cleaned}"
                    )
                    # Try one more time with more specific instruction
                    return self._extract_company_fallback(text)
        except Exception as e:
            logger.warning(f"Error extracting company name: {e}")

        return None

    def _clean_llm_response(self, response: str, extract_type: str = "company") -> str:
        """Clean verbose LLM responses to extract just the name"""
        if not response:
            return ""

        import re

        cleaned = response.strip()
        cleaned_lower = cleaned.lower()

        # Reject explanation text patterns (common LLM explanation phrases)
        explanation_patterns = [
            "after searching",
            "after reviewing",
            "i found",
            "i did not find",
            "based on the",
            "according to",
            "the text appears",
            "let me know",
            "if you need",
            "there are no",
            "cannot find",
            "unable to",
            "not applicable",
            "not found",
            "the following person",
            "mentioned in quotes",
        ]

        # Check if response contains explanation text
        has_explanation = any(
            pattern in cleaned_lower for pattern in explanation_patterns
        )

        # Remove common prefixes and explanations
        prefixes_to_remove = [
            "the actual company name mentioned in this article is:",
            "the actual company mentioned in this article is:",
            "according to the article, the actual company name mentioned is:",
            "the actual company mentioned is:",
            "based on the text, the actual company mentioned is:",
            "the company name is:",
            "company name:",
            "company:",
            "the extracted person's name is:",
            "the person's name is:",
            "person name:",
            "person:",
            "name:",
            "after searching the text, i found",
            "after reviewing the text, i found",
            "the following person's name mentioned in quotes:",
        ]

        for prefix in prefixes_to_remove:
            if cleaned_lower.startswith(prefix.lower()):
                cleaned = cleaned[len(prefix) :].strip()
                cleaned_lower = cleaned.lower()

        # Remove bullet points and list markers
        cleaned = cleaned.replace("*", "").replace("-", "").strip()

        # Extract just the first line (often the name is on the first line)
        lines = cleaned.split("\n")
        if lines:
            cleaned = lines[0].strip()
            cleaned_lower = cleaned.lower()

        # Remove quotes and extra whitespace
        cleaned = cleaned.strip("\"'.,;:")

        # For person names, extract from common patterns
        if extract_type == "person":
            # Pattern: "FirstName LastName" (2-4 words, capitalized, no explanation words)
            name_pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b"
            matches = re.findall(name_pattern, cleaned)
            if matches:
                # Filter out explanation words
                invalid_words = [
                    "the",
                    "and",
                    "for",
                    "with",
                    "this",
                    "that",
                    "after",
                    "searching",
                    "reviewing",
                    "found",
                    "following",
                    "mentioned",
                    "quotes",
                    "text",
                    "according",
                    "based",
                    "unable",
                    "cannot",
                    "not",
                    "applicable",
                ]
                valid_matches = [
                    m
                    for m in matches
                    if not any(word in m.lower() for word in invalid_words)
                ]
                if valid_matches:
                    # Take the longest match (most likely the full name)
                    cleaned = max(valid_matches, key=len)
                elif matches:
                    # If all matches contain invalid words, try to extract anyway
                    cleaned = max(matches, key=len)
                    # But if it's clearly an explanation, return empty
                    if has_explanation and len(cleaned) > 30:
                        return ""

        # For company names, extract from common patterns
        if extract_type == "company":
            company_pattern = r"\b([A-Z][A-Za-z0-9&]+(?:\s+[A-Z][A-Za-z0-9&]+){0,3})\b"
            matches = re.findall(company_pattern, cleaned)
            if matches:
                # Take a reasonable match
                invalid_words = [
                    "the",
                    "and",
                    "for",
                    "with",
                    "this",
                    "that",
                    "after",
                    "searching",
                ]
                for match in matches:
                    if len(match) > 3 and not any(
                        word in match.lower() for word in invalid_words
                    ):
                        cleaned = match
                        break

        # Final cleanup
        cleaned = cleaned.strip()

        # Remove if it's too long or contains explanation text
        if len(cleaned) > 50 or (has_explanation and len(cleaned) > 20):
            # Try one more extraction attempt using regex
            if extract_type == "person":
                name_match = re.search(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b", cleaned)
                if name_match:
                    return name_match.group(1)
            elif extract_type == "company":
                company_match = re.search(
                    r"\b([A-Z][A-Za-z0-9&]+(?:\s+[A-Z][A-Za-z0-9&]+)?)\b", cleaned
                )
                if company_match:
                    return company_match.group(1)
            return ""

        return cleaned

    def _extract_company_fallback(self, text: str) -> Optional[str]:
        """Fallback company extraction with more specific instructions"""
        if not self.llm_service:
            return None

        prompt = f"""From this text, identify the company that is the MAIN SUBJECT or TOPIC of the article.
This should be a business/organization, NOT a news website, publisher, or media company.

Return ONLY the company name, nothing else. No explanations.

Examples:
- If article says "Rally House wins award" → Rally House
- If article says "McLean & Company releases playbook" → McLean & Company
- If article is ABOUT a company doing something → That company

Text: {text[:800]}

Company name:"""

        try:
            response = self.llm_service.invoke_sync(prompt, "company_extraction")
            if response and response != "Service temporarily unavailable":
                return self._clean_llm_response(response, extract_type="company")
        except Exception:
            pass

        return None

    def extract_person_name(self, text: str) -> Optional[str]:
        """Extract person name from text using LLM, prioritizing quotes"""
        if not text or len(text) < 10:
            return None

        # Fallback if LLM service is not available
        if not self.llm_service:
            logger.warning(
                "LLM service not available, using fallback for person extraction"
            )
            return None

        # First, try to extract from quotes (higher priority)
        prompt_quotes = f"""Extract the person's name from quotes in this text. Look for names mentioned after titles like:
- "said [Name]"
- "according to [Name]"
- "[Name], CHRO/VP HR/Head of HR"
- "[Title] [Name] said"

Focus on CHRO, VP of HR, Head of HR, or other HR executives mentioned in quotes.

Text: {text[:1000]}

Person name (from quotes):"""

        try:
            response = self.llm_service.invoke_sync(prompt_quotes, "person_extraction")
            if response and response != "Service temporarily unavailable":
                cleaned = self._clean_llm_response(response, extract_type="person")
                # Validate it looks like a name (has at least 2 words)
                if (
                    cleaned
                    and len(cleaned.split()) >= 2
                    and cleaned.lower() not in ["unknown", "none", "n/a"]
                ):
                    logger.info(f"✅ Found person name from quotes: {cleaned}")
                    return cleaned
        except Exception as e:
            logger.warning(f"Error extracting person name from quotes: {e}")

        # Fallback: General extraction if quotes didn't work
        prompt_general = f"""Extract the person's name (CHRO, HR leader, or executive) from this text.

CRITICAL: Return ONLY the full name (First Last), nothing else. No explanations, no quotes, no "I found" or "according to" text. Just the name.

If no name is found, return "Unknown".

Text: {text[:500]}

Person name:"""

        try:
            response = self.llm_service.invoke_sync(prompt_general, "person_extraction")
            if response and response != "Service temporarily unavailable":
                cleaned = self._clean_llm_response(response, extract_type="person")
                if (
                    cleaned
                    and len(cleaned.split()) >= 2
                    and cleaned.lower() not in ["unknown", "none", "n/a"]
                ):
                    logger.info(f"✅ Found person name (general extraction): {cleaned}")
                    return cleaned
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

CRITICAL: Return ONLY the email address, nothing else. No explanations, no text, just the email.

Format: firstname.lastname@companydomain.com

Examples:
- Company: Google, Person: John Smith → john.smith@google.com
- Company: Microsoft, Person: Jane Doe → jane.doe@microsoft.com

Company: {company}
Person: {person}
Email:"""

        try:
            response = self.llm_service.invoke_sync(prompt, "email_finder")
            if response and response != "Service temporarily unavailable":
                # Clean up the response - extract email from response
                import re

                # Look for email pattern in response
                email_pattern = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
                email_matches = re.findall(email_pattern, response)

                if email_matches:
                    # Take the first valid email found
                    email = email_matches[0].strip()
                    if self._is_valid_email(email):
                        logger.info(
                            f"LLM suggested email for {person} at {company}: {email}"
                        )
                        return email
                else:
                    # Try to extract from last line
                    lines = response.strip().split("\n")
                    for line in reversed(lines):
                        line = line.strip()
                        if "@" in line:
                            # Extract email from line
                            email_match = re.search(email_pattern, line)
                            if email_match:
                                email = email_match.group(0)
                                if self._is_valid_email(email):
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

    def _fallback_company_from_article(
        self, article: Dict[str, Any], content: str
    ) -> Optional[str]:
        """Derive a best-effort company name when the LLM cannot extract one"""
        candidates: List[Optional[str]] = []

        candidates.extend(
            [
                article.get("company"),
                article.get("source"),
                article.get("source_id"),
            ]
        )

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
            logger.info(f"🏢 Extracting company name from: {url}")
            company = self.extract_company_name(content)
            if company:
                logger.info(f"✅ Company found: {company}")
            else:
                company = self._fallback_company_from_article(article, content)
                if company:
                    logger.info(
                        f"ℹ️ Using fallback company '{company}' derived from article metadata"
                    )
                else:
                    logger.warning(f"❌ No company found in: {url}")
                    return None

            logger.info(f"👤 Extracting person name from: {url}")
            person = self.extract_person_name(content)
            if person and person != "Unknown":
                logger.info(f"✅ Person found: {person}")
            else:
                logger.info(f"ℹ️ No specific person found, using 'Unknown'")

            # Calculate relevance score
            keywords = DEFAULT_KEYWORDS
            relevance_score = self.calculate_relevance_score(content, keywords)
            logger.info(f"📊 Relevance score: {relevance_score:.2f}")

            # Apply quality thresholds
            needs_manual_review = False
            if relevance_score < self.min_relevance_score:
                if relevance_score >= self.low_confidence_score:
                    needs_manual_review = True
                    logger.info(
                        "⚠️ Relevance %.2f below %.2f, keeping for manual review",
                        relevance_score,
                        self.min_relevance_score,
                    )
                else:
                    logger.warning(
                        "❌ Relevance score %.2f below minimum %.2f",
                        relevance_score,
                        self.low_confidence_score,
                    )
                    return None

            # Find email
            email = "Manual validation needed"
            if person and person != "Unknown":
                logger.info(f"📧 Finding email for {person} at {company}")
                email = self.extract_email(company, person)
                if email != "Manual validation needed":
                    logger.info(f"✅ Email found: {email}")
                else:
                    logger.info(f"ℹ️ Email not found, manual validation needed")
            else:
                logger.info(f"ℹ️ No person found, manual validation needed for email")

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
                date=self.parse_article_date(date)
                or datetime.now().strftime("%Y-%m-%d"),
                content=content[:1000],  # Truncate for storage
                relevance_score=relevance_score,
                signal_type=signal_type,
                source=source_label,
            )

            logger.info(
                f"🎯 OPPORTUNITY CREATED: {company} - {person} (Email: {email}, Score: {relevance_score:.2f})"
            )
            return opportunity

        except Exception as e:
            logger.error(f"Error processing article: {e}")
            return None

    def process_signal(
        self, signal_id: int, max_results: int = 10
    ) -> List[Opportunity]:
        """Process a specific signal type and return opportunities"""
        signal_name = SIGNAL_TYPES.get(signal_id, "Unknown")
        logger.info(f"🔍 BUYER SIGNAL ACTIVATED: {signal_id} - {signal_name}")

        # Generate queries for this signal
        queries = self.generate_queries(signal_id)
        logger.info(f"📝 Generated {len(queries)} search queries for {signal_name}")

        # Search for articles
        all_articles = []
        if self.search_service:
            for i, query in enumerate(queries):
                logger.info(f"🔎 Searching query {i+1}/{len(queries)}: '{query}'")
                articles = self.search_service.search_articles(
                    query, max_results // len(queries)
                )
                logger.info(f"📰 Found {len(articles)} articles for query: '{query}'")
                all_articles.extend(articles)

                # Log article URLs
                for article in articles:
                    logger.info(f"📄 Article URL: {article.get('url', 'No URL')}")

        if not all_articles:
            logger.warning(f"❌ No articles found for signal {signal_id}")
            return []

        logger.info(f"📊 Total articles found: {len(all_articles)}")

        # Process articles into opportunities
        opportunities = []
        for i, article in enumerate(all_articles):
            logger.info(
                f"🔍 Processing article {i+1}/{len(all_articles)}: {article.get('title', 'No title')[:50]}..."
            )
            opportunity = self.process_article(article, signal_id)
            if opportunity:
                opportunities.append(opportunity)
                logger.info(
                    f"✅ OPPORTUNITY FOUND: {opportunity.company} - {opportunity.person} (Email: {opportunity.email})"
                )

        logger.info(
            f"🎯 Signal {signal_id} ({signal_name}) completed: {len(opportunities)} opportunities found"
        )
        return opportunities
