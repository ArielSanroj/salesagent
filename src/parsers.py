#!/usr/bin/env python3
"""
Parsers for HR Tech Lead Generation System
Data parsing and extraction utilities
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from dateutil.parser import parse as parse_date


class DateParser:
    """Date parsing utilities"""

    @staticmethod
    def parse_article_date(date_str: str) -> Optional[str]:
        """Parse article date string to YYYY-MM-DD format"""
        if not date_str:
            return None

        try:
            parsed_date = parse_date(date_str)
            return parsed_date.strftime("%Y-%m-%d")
        except Exception:
            return None

    @staticmethod
    def is_recent_date(date_str: str, days_threshold: int = 365) -> bool:
        """Check if date is within threshold days"""
        if not date_str:
            return False

        try:
            parsed_date = parse_date(date_str)
            days_diff = (datetime.now() - parsed_date).days
            return days_diff <= days_threshold
        except Exception:
            return False


class TextParser:
    """Text parsing utilities"""

    @staticmethod
    def extract_company_name(text: str) -> Optional[str]:
        """Extract company name from text using simple patterns"""
        if not text or len(text) < 10:
            return None

        # Common company patterns
        patterns = [
            r"([A-Z][a-z]+ [A-Z][a-z]+(?: Inc| Corp| LLC| Ltd| Co)?)",
            r"([A-Z][a-z]+(?: Technologies| Systems| Solutions| Software| Services))",
            r"([A-Z][a-z]+(?: Group| Holdings| Partners| Ventures))",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Return the first match that looks like a company
                for match in matches:
                    if len(match) > 3 and not any(
                        word in match.lower() for word in ["the", "and", "for", "with"]
                    ):
                        return match.strip()

        return None

    @staticmethod
    def extract_person_name(text: str) -> Optional[str]:
        """Extract person name from text using patterns"""
        if not text or len(text) < 10:
            return None

        # Look for titles followed by names
        title_patterns = [
            r"(?:CHRO|Chief Human Resources Officer|HR Director|VP of HR|Head of HR)\s+([A-Z][a-z]+ [A-Z][a-z]+)",
            r"(?:CEO|Chief Executive Officer|President|Founder)\s+([A-Z][a-z]+ [A-Z][a-z]+)",
            r"(?:CTO|Chief Technology Officer|VP of Engineering)\s+([A-Z][a-z]+ [A-Z][a-z]+)",
        ]

        for pattern in title_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].strip()

        return None

    @staticmethod
    def extract_email_from_text(text: str) -> Optional[str]:
        """Extract email address from text"""
        if not text:
            return None

        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        matches = re.findall(email_pattern, text)

        if matches:
            return matches[0]

        return None

    @staticmethod
    def clean_html_content(html_content: str) -> str:
        """Clean HTML content and extract text"""
        if not html_content:
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html_content)

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove common HTML entities
        entities = {
            "&amp;": "&",
            "&lt;": "<",
            "&gt;": ">",
            "&quot;": '"',
            "&#39;": "'",
            "&nbsp;": " ",
        }

        for entity, replacement in entities.items():
            text = text.replace(entity, replacement)

        return text.strip()


class ContentParser:
    """Content parsing utilities"""

    @staticmethod
    def extract_keywords(text: str, keywords: List[str]) -> Dict[str, int]:
        """Extract keyword counts from text"""
        if not text or not keywords:
            return {}

        text_lower = text.lower()
        keyword_counts = {}

        for keyword in keywords:
            count = text_lower.count(keyword.lower())
            if count > 0:
                keyword_counts[keyword] = count

        return keyword_counts

    @staticmethod
    def calculate_relevance_score(content: str, keywords: List[str]) -> float:
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

    @staticmethod
    def extract_metadata(text: str) -> Dict[str, Any]:
        """Extract metadata from text content"""
        if not text:
            return {}

        metadata = {
            "word_count": len(text.split()),
            "char_count": len(text),
            "has_email": bool(TextParser.extract_email_from_text(text)),
            "has_phone": bool(re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", text)),
            "has_url": bool(re.search(r"https?://\S+", text)),
            "sentence_count": len(re.findall(r"[.!?]+", text)),
        }

        return metadata
