#!/usr/bin/env python3
"""
Data Enrichment Service for HR Tech Lead Generation System
Handles company/person extraction and email finding
"""

import logging
import re
from typing import Any, Dict, List, Optional

from pyhunter import PyHunter

from http_utils import is_valid_email

logger = logging.getLogger(__name__)

# Common news sources to filter out
NEWS_SOURCES = [
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


def calculate_relevance_score(content: str, keywords: List[str]) -> float:
    """Calculate relevance score based on keyword presence"""
    if not content or not keywords:
        return 0.0

    content_lower = content.lower()
    keyword_matches = sum(1 for kw in keywords if kw.lower() in content_lower)

    # Base score from keyword matches
    base_score = min(keyword_matches / len(keywords), 1.0)

    # Bonus for multiple occurrences
    total_occurrences = sum(
        content_lower.count(keyword.lower()) for keyword in keywords
    )
    occurrence_bonus = min(total_occurrences * 0.1, 0.3)

    return min(base_score + occurrence_bonus, 1.0)


def extract_company_name(text: str, llm_service=None) -> Optional[str]:
    """Extract company name from text using LLM"""
    if not text or len(text) < 10:
        return None

    if not llm_service:
        logger.warning("LLM service not available for company extraction")
        return None

    prompt = f"""Extract the ACTUAL COMPANY NAME mentioned in this article, NOT the news website or publisher.

CRITICAL: Return ONLY the company name, nothing else. No explanations.

Avoid news sources like: Postregister, Hastingstribune, SHRM, PR Newswire, etc.

Look for:
- Companies that are the SUBJECT of the article
- Companies mentioned in quotes or as the main topic
- Companies that are doing something (receiving awards, making announcements, etc.)

Text: {text[:1000]}

Company name:"""

    try:
        response = llm_service.invoke_sync(prompt, "company_extraction")
        if response and response != "Service temporarily unavailable":
            cleaned = _clean_company_response(response)
            if cleaned and cleaned.lower() not in [ns.lower() for ns in NEWS_SOURCES]:
                logger.info(f"Extracted company: {cleaned}")
                return cleaned
            else:
                logger.warning(f"Extracted company appears to be news source: {cleaned}")
                return _extract_company_fallback(text, llm_service)
    except Exception as e:
        logger.warning(f"Error extracting company name: {e}")

    return None


def _clean_company_response(response: str) -> str:
    """Clean LLM response to extract company name"""
    if not response:
        return ""

    cleaned = response.strip()

    # Remove common prefixes
    prefixes = [
        "the actual company name is:",
        "the company name is:",
        "company name:",
        "company:",
    ]
    for prefix in prefixes:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()

    # Remove quotes and extra whitespace
    cleaned = cleaned.strip("\"'.,;:")

    # Take first line only
    if "\n" in cleaned:
        cleaned = cleaned.split("\n")[0].strip()

    return cleaned if len(cleaned) <= 50 else ""


def _extract_company_fallback(text: str, llm_service) -> Optional[str]:
    """Fallback company extraction with more specific instructions"""
    if not llm_service:
        return None

    prompt = f"""From this text, identify the company that is the MAIN SUBJECT.
NOT a news website, publisher, or media company.

Return ONLY the company name, nothing else. No explanations.

Text: {text[:800]}

Company name:"""

    try:
        response = llm_service.invoke_sync(prompt, "company_extraction")
        if response and response != "Service temporarily unavailable":
            return _clean_company_response(response)
    except Exception:
        pass

    return None


def extract_person_name(text: str, llm_service=None) -> Optional[str]:
    """Extract person name from text using LLM"""
    if not text or len(text) < 10:
        return None

    if not llm_service:
        logger.warning("LLM service not available for person extraction")
        return None

    # Try to extract from quotes first
    prompt_quotes = f"""Extract the person's name from quotes in this text. Look for:
- "said [Name]"
- "according to [Name]"
- "[Name], CHRO/VP HR/Head of HR"

Focus on CHRO, VP of HR, Head of HR, or other HR executives.

Text: {text[:1000]}

Person name (from quotes):"""

    try:
        response = llm_service.invoke_sync(prompt_quotes, "person_extraction")
        if response and response != "Service temporarily unavailable":
            cleaned = _clean_person_response(response)
            if cleaned and len(cleaned.split()) >= 2:
                logger.info(f"Found person name from quotes: {cleaned}")
                return cleaned
    except Exception as e:
        logger.warning(f"Error extracting person name from quotes: {e}")

    # Fallback: General extraction
    prompt_general = f"""Extract the person's name (CHRO, HR leader, or executive).

CRITICAL: Return ONLY the full name (First Last), nothing else.
If no name is found, return "Unknown".

Text: {text[:500]}

Person name:"""

    try:
        response = llm_service.invoke_sync(prompt_general, "person_extraction")
        if response and response != "Service temporarily unavailable":
            cleaned = _clean_person_response(response)
            if cleaned and len(cleaned.split()) >= 2:
                logger.info(f"Found person name (general): {cleaned}")
                return cleaned
    except Exception as e:
        logger.warning(f"Error extracting person name: {e}")

    return None


def _clean_person_response(response: str) -> str:
    """Clean LLM response to extract person name"""
    if not response:
        return ""

    cleaned = response.strip()

    # Remove common prefixes
    prefixes = ["the person's name is:", "person name:", "person:", "name:"]
    for prefix in prefixes:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()

    # Remove quotes
    cleaned = cleaned.strip("\"'.,;:")

    # Take first line only
    if "\n" in cleaned:
        cleaned = cleaned.split("\n")[0].strip()

    # Filter invalid results
    invalid = ["unknown", "none", "n/a", "not found", "unable to find"]
    if cleaned.lower() in invalid:
        return ""

    # Extract name pattern if response is too long
    if len(cleaned) > 40:
        name_match = re.search(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b", cleaned)
        if name_match:
            return name_match.group(1)
        return ""

    return cleaned


def find_email_with_llm(company: str, person: str, llm_service=None) -> str:
    """Find email using LLM"""
    if not company or not person or person.lower() in ["unknown", ""]:
        return "Manual validation needed"

    if not llm_service:
        logger.warning("LLM service not available for email finder")
        return "Manual validation needed"

    prompt = f"""Given company '{company}' and person '{person}', suggest the most likely email.

CRITICAL: Return ONLY the email address, nothing else.
Format: firstname.lastname@companydomain.com

Company: {company}
Person: {person}
Email:"""

    try:
        response = llm_service.invoke_sync(prompt, "email_finder")
        if response and response != "Service temporarily unavailable":
            # Extract email from response
            email_pattern = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
            matches = re.findall(email_pattern, response)

            if matches and is_valid_email(matches[0]):
                logger.info(f"LLM suggested email for {person} at {company}: {matches[0]}")
                return matches[0]

        logger.warning(f"LLM returned invalid email format: {response}")
        return "Manual validation needed"
    except Exception as e:
        logger.error(f"LLM email finder failed for {company}, {person}: {e}")
        return "Manual validation needed"


def verify_email_with_hunter(email: str, hunter_api_key: str = None) -> str:
    """Verify email using Hunter.io"""
    if not hunter_api_key:
        return email

    try:
        hunter = PyHunter(hunter_api_key)
        result = hunter.email_verifier(email)

        if result and result.get("result") == "deliverable":
            logger.info(f"Hunter.io verified email: {email}")
            return email
        else:
            logger.warning(f"Hunter.io could not verify email: {email}")
            return email
    except Exception as e:
        logger.warning(f"Hunter.io verification failed for {email}: {e}")
        return email
