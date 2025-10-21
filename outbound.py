#!/usr/bin/env python3
"""
HR Tech Lead Generation System - Improved Version
Consolidates functionality from both outbound.py and outbound_secure.py
Implements secure credential management, resilient LLM service, and proper error handling
"""

import asyncio
import concurrent.futures
import fcntl
import io
import json
import logging
import os
import re
import smtplib
import sys
import time
from datetime import datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from pyhunter import PyHunter
from ratelimit import limits, sleep_and_retry
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from urllib3.util.retry import Retry

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from constants import (
    NEWS_API_CALL_LIMIT,
    NEWS_API_TIMEOUT,
    NEWSDATA_LATEST_URL,
    SIGNAL_TYPES,
    TARGET_OPPORTUNITIES_PER_WEEK,
)
from credentials_manager import CredentialsManager
from exceptions import (
    APIServiceError,
    AuthenticationError,
    NetworkError,
    RateLimitError,
    ScrapingError,
    ValidationError,
)
from google_sheets_service import GoogleSheetsService
from llm_service import LLMService
from models import Opportunity
from scraping_service import ScrapingService
from search_service import SearchService
from signal_processor import SignalProcessor

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    filename="scrape.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global variables
credentials_manager = None
llm_service = None
CONFIG = None
session = None

# Process lock mechanism
LOCK_FILE = "outbound.lock"

# Constants
NEWS_API_CALL_COUNT = 0
NEWS_API_CALL_LIMIT = int(os.getenv("NEWSDATA_API_CALL_LIMIT", "50"))


def initialize_services() -> bool:
    """Initialize all services with secure configuration"""
    global credentials_manager, llm_service, CONFIG, session

    try:
        # Initialize credentials manager
        credentials_manager = CredentialsManager()

        # Validate required credentials
        if not credentials_manager.validate_required_credentials():
            logger.error("Missing required credentials. Please check your .env file.")
            return False

        # Get complete configuration
        CONFIG = credentials_manager.get_all_config()

        # Initialize LLM service with resilience (no crash if LLM fails)
        try:
            llm_service = LLMService(credentials_manager)
            logger.info("✅ LLM service initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ LLM service initialization failed: {e}")
            logger.warning("System will continue with fallback responses")
            llm_service = None

        # Create HTTP session with retry strategy
        session = create_session()

        logger.info("✅ All services initialized successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        return False


def create_session() -> requests.Session:
    """Create HTTP session with retry strategy"""
    session = requests.Session()

    # Retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def acquire_lock() -> bool:
    """Acquire a lock to prevent multiple instances from running"""
    try:
        lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.write(lock_fd, str(os.getpid()).encode())
        os.close(lock_fd)
        logger.info(f"Lock acquired successfully (PID: {os.getpid()})")
        return True
    except (OSError, IOError) as e:
        logger.error(f"Could not acquire lock: {e}")
        print("❌ Another instance is already running!")
        print(f"   Delete lock file if needed: rm {LOCK_FILE}")
        return False


def release_lock() -> None:
    """Release the process lock"""
    try:
        if os.path.exists(LOCK_FILE):
            os.unlink(LOCK_FILE)
            logger.info("Lock released successfully")
    except OSError:
        pass


def is_valid_url(url: str) -> bool:
    """Validate URL format"""
    if not url or not isinstance(url, str):
        return False

    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in [
            "http",
            "https",
        ]
    except Exception:
        return False


def extract_text_from_html(html_content: str) -> str:
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


def calculate_relevance_score(content: str, keywords: List[str]) -> float:
    """Calculate relevance score based on keyword presence"""
    if not content or not keywords:
        return 0.0

    content_lower = content.lower()
    keyword_matches = sum(1 for keyword in keywords if keyword.lower() in content_lower)

    # Base score from keyword matches
    base_score = min(keyword_matches / len(keywords), 1.0)

    # Bonus for multiple occurrences
    total_occurrences = sum(
        content_lower.count(keyword.lower()) for keyword in keywords
    )
    occurrence_bonus = min(total_occurrences * 0.1, 0.3)

    return min(base_score + occurrence_bonus, 1.0)


def extract_company_name(text: str) -> Optional[str]:
    """Extract company name from text using LLM"""
    if not text or len(text) < 10:
        return None

    # Fallback if LLM service is not available
    if not llm_service:
        logger.warning(
            "LLM service not available, using fallback for company extraction"
        )
        return None

    prompt = f"""Extract the company name from this text. Return only the company name, nothing else.

Text: {text[:500]}

Company name:"""

    try:
        response = llm_service.invoke_sync(prompt, "company_extraction")
        if response and response != "Service temporarily unavailable":
            return response.strip()
    except Exception as e:
        logger.warning(f"Error extracting company name: {e}")

    return None


def extract_person_name(text: str) -> Optional[str]:
    """Extract person name from text using LLM"""
    if not text or len(text) < 10:
        return None

    # Fallback if LLM service is not available
    if not llm_service:
        logger.warning(
            "LLM service not available, using fallback for person extraction"
        )
        return None

    prompt = f"""Extract the person's name (CHRO, HR leader, or executive) from this text. Return only the full name, nothing else.

Text: {text[:500]}

Person name:"""

    try:
        response = llm_service.invoke_sync(prompt, "person_extraction")
        if response and response != "Service temporarily unavailable":
            return response.strip()
    except Exception as e:
        logger.warning(f"Error extracting person name: {e}")

    return None


def parse_article_date(date_str: str) -> Optional[str]:
    """Parse article date string to YYYY-MM-DD format"""
    if not date_str:
        return None

    try:
        parsed_date = parse_date(date_str)
        return parsed_date.strftime("%Y-%m-%d")
    except Exception:
        return None


def is_valid_email(email: str) -> bool:
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def llm_email_finder(company: str, person: str) -> str:
    """Find email using LLM with fallback"""
    if not company or not person or person.lower() in ["unknown", ""]:
        return "Manual validation needed"

    # Fallback if LLM service is not available
    if not llm_service:
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
        response = llm_service.invoke_sync(prompt, "email_finder")
        if response and response != "Service temporarily unavailable":
            # Clean up the response
            if "@" in response:
                email = response.split("\n")[-1].strip()
                if "@" in email and "." in email and is_valid_email(email):
                    logger.info(
                        f"LLM suggested email for {person} at {company}: {email}"
                    )
                return email

        logger.warning(f"LLM returned invalid email format: {response}")
        return "Manual validation needed"
    except Exception as e:
        logger.error(f"LLM email finder failed for {company}, {person}: {e}")
        return "Manual validation needed"


def hunter_email_verifier(email: str) -> str:
    """Verify email using Hunter.io with fallback"""
    if not CONFIG.get("hunter") or not CONFIG["hunter"].get("api_key"):
        return email

    try:
        hunter = PyHunter(CONFIG["hunter"]["api_key"])
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


def _check_news_api_limits() -> bool:
    """Check if we can make API calls"""
    global NEWS_API_CALL_COUNT

    if NEWS_API_CALL_COUNT >= NEWS_API_CALL_LIMIT:
        logger.warning("NewsData.io daily call limit reached")
        return False

    if not CONFIG.get("newsdata") or not CONFIG["newsdata"].get("api_key"):
        logger.warning("NEWSDATA_API_KEY not configured; returning empty results")
        return False

    return True


def _handle_news_api_response(response) -> bool:
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


def _process_news_articles(
    articles: List[Dict], domains: Optional[List[str]], num_results: int
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
        processed.append(article_data)

    return processed


def fetch_news_articles(
    query: str, num_results: int = 10, domains: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Fetch news articles from NewsData.io API with improved implementation"""
    global NEWS_API_CALL_COUNT

    if not _check_news_api_limits():
        return []

    aggregated = []
    endpoint = NEWSDATA_LATEST_URL

    # Build base parameters
    params = {
        "apikey": CONFIG["newsdata"]["api_key"],
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

            response = session.get(endpoint, params=request_params, timeout=30)

            if not _handle_news_api_response(response):
                break

            response.raise_for_status()
            payload = response.json()

            # Check API response status
            if payload.get("status") != "success":
                error_msg = payload.get("message", "NewsData.io API error")
                logger.error(f"NewsData.io API error: {error_msg}")
                break

            articles = payload.get("results", [])
            if not articles:
                logger.info("No more articles available from NewsData.io")
                break

            processed_articles = _process_news_articles(articles, domains, num_results)
            aggregated.extend(processed_articles)

            page_token = payload.get("nextPage")
            page_count += 1

            if not page_token:
                logger.info("Reached last page of NewsData.io results")
                break

    except Exception as e:
        logger.error(f"Error fetching news articles: {e}")

    finally:
        NEWS_API_CALL_COUNT += 1

    logger.info(f"NewsData.io returned {len(aggregated)} articles for query '{query}'")
    return aggregated[:num_results]


def scrape_url_content(url: str) -> Optional[Dict[str, str]]:
    """Scrape content from URL with retry logic"""
    if not is_valid_url(url):
        return None

    for attempt in range(3):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Extract text content
            text_content = extract_text_from_html(response.text)

            if text_content and len(text_content) > 100:
                return {
                    "content": text_content,
                    "title": BeautifulSoup(response.text, "html.parser").title.string
                    if BeautifulSoup(response.text, "html.parser").title
                    else "No title",
                    "url": url,
                }

        except Exception as e:
            logger.warning(f"Scraping attempt {attempt + 1} failed for {url}: {e}")
            if attempt < 2:
                time.sleep(2**attempt)

        return None


def process_opportunity(
    article: Dict[str, Any], signal_type: int
) -> Optional[Opportunity]:
    """Process a single opportunity with LLM assistance"""
    try:
        # Extract basic information
        title = article.get("title", "")
        url = article.get("url", "")
        date = article.get("publishedAt", "")

        if not title or not url:
            return None

        # Scrape content
        scraped_content = scrape_url_content(url)
        if not scraped_content:
            return None

        content = scraped_content["content"]

        # Extract company and person using LLM
        company = extract_company_name(content)
        person = extract_person_name(content)

        if not company:
            return None

        # Calculate relevance score
        keywords = CONFIG["search"]["keywords"]
        relevance_score = calculate_relevance_score(content, keywords)

        # Apply quality thresholds
        quality_config = CONFIG["quality"]
        if relevance_score < quality_config["min_relevance_score"]:
            return None

        # Find email
        email = "Manual validation needed"
        if person and person != "Unknown":
            email = llm_email_finder(company, person)
            if email != "Manual validation needed":
                email = hunter_email_verifier(email)

        # Create opportunity
        opportunity = Opportunity(
            title=title,
            company=company,
            person=person or "Unknown",
            email=email,
            url=url,
            date=parse_article_date(date) or datetime.now().strftime("%Y-%m-%d"),
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
        logger.error(f"Error processing opportunity: {e}")
        return None


def generate_queries(signal_id: int) -> List[str]:
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


def run_signal(signal_id: int) -> List[Opportunity]:
    """Run a specific signal type using the new SignalProcessor"""
    logger.info(f"Running signal {signal_id}: {SIGNAL_TYPES.get(signal_id, 'Unknown')}")

    # Initialize services
    search_service = SearchService(session, CONFIG.get("newsdata", {}).get("api_key"))
    scraping_service = ScrapingService(session)
    signal_processor = SignalProcessor(llm_service, search_service, scraping_service)

    # Process the signal
    opportunities = signal_processor.process_signal(signal_id, 10)

    logger.info(
        f"Signal {signal_id} completed: {len(opportunities)} opportunities found"
    )
    return opportunities


def save_results(opportunities: List[Opportunity], filename: str) -> None:
    """Save opportunities to CSV file"""
    if not opportunities:
        logger.warning("No opportunities to save")
        return

    # Convert to DataFrame
    data = []
    for opp in opportunities:
        data.append(
            {
                "Title": opp.title,
                "Company": opp.company,
                "Person": opp.person,
                "Email": opp.email,
                "URL": opp.url,
                "Date": opp.date,
                "Relevance Score": opp.relevance_score,
                "Signal Type": opp.signal_type,
                "Source": opp.source,
            }
        )

    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    logger.info(f"Saved {len(opportunities)} opportunities to {filename}")


def filter_results(opportunities: List[Opportunity]) -> List[Opportunity]:
    """Filter and deduplicate opportunities"""
    if not opportunities:
        return []

    # Remove duplicates based on company and person
    seen = set()
    filtered = []

    for opp in opportunities:
        key = (opp.company.lower(), opp.person.lower())
        if key not in seen:
            seen.add(key)
            filtered.append(opp)

    # Sort by relevance score
    filtered.sort(key=lambda x: x.relevance_score, reverse=True)

    logger.info(
        f"Filtered {len(opportunities)} opportunities to {len(filtered)} unique opportunities"
    )
    return filtered


def test_signal(signal_id: int) -> List[Opportunity]:
    """Test a single signal for development"""
    logger.info(f"Testing signal {signal_id}")

    opportunities = run_signal(signal_id)
    if opportunities:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"test_signal_{signal_id}_{timestamp}.csv"
        save_results(opportunities, filename)
        logger.info(
            f"Test completed: {len(opportunities)} opportunities saved to {filename}"
        )
        return opportunities
    else:
        logger.warning(f"No opportunities found for signal {signal_id}")
        return []


def send_email_report(report_content: str, csv_file_path: Optional[str] = None) -> bool:
    """Send the synthesized report via email"""
    email_config = CONFIG.get("email", {})

    if not email_config:
        logger.error("Email configuration not found")
        return False

    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = email_config["sender_email"]
        msg["To"] = email_config["recipient_email"]
        msg[
            "Subject"
        ] = f"HR Tech Lead Generation Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Add report content to email body
        body = f"""
Hello Ariel,

Here's your latest HR Tech Lead Generation Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M')}.

{report_content}

---
This report was automatically generated by your HR Tech Lead Generation System.
        """

        msg.attach(MIMEText(body, "plain"))

        # Attach CSV file if provided
        if csv_file_path and os.path.exists(csv_file_path):
            with open(csv_file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {os.path.basename(csv_file_path)}",
                )
                msg.attach(part)

        # Connect to server and send email
        server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
        server.starttls()
        server.login(email_config["sender_email"], email_config["sender_password"])

        text = msg.as_string()
        server.sendmail(
            email_config["sender_email"], email_config["recipient_email"], text
        )
        server.quit()

        logger.info(
            f"Email report sent successfully to {email_config['recipient_email']}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send email report: {e}")
        return False


def main() -> None:
    """Main execution function"""
    # Acquire lock
    if not acquire_lock():
        sys.exit(1)

    try:
        # Initialize services
        if not initialize_services():
            logger.error("Failed to initialize services")
            sys.exit(1)

        # Check if this is a weekly run
        is_weekly_run = os.getenv("WEEKLY_RUN", "false").lower() == "true"
        target_opportunities = int(os.getenv("TARGET_OPPORTUNITIES", "50"))

        if is_weekly_run:
            logger.info(
                f"Starting weekly run - Target: {target_opportunities} opportunities"
            )

            all_opportunities = []

            # Run all signals
            for signal_id in range(1, 7):
                logger.info(f"Running signal {signal_id}/6")
                opportunities = run_signal(signal_id)
                all_opportunities.extend(opportunities)
                time.sleep(5)  # Brief pause between signals

            # Filter and save results
            filtered_opportunities = filter_results(all_opportunities)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            save_results(filtered_opportunities, f"all_signals_{timestamp}.csv")
            save_results(filtered_opportunities, "all_signals.csv")

            # Send email report
            if filtered_opportunities:
                report_content = f"Generated {len(filtered_opportunities)} opportunities across 6 signal types."
                send_email_report(report_content, "all_signals.csv")

            logger.info(
                f"Weekly run completed: {len(filtered_opportunities)} opportunities generated"
            )

        else:
            # Quick test for development
            opportunities = test_signal(1)
            if opportunities:
                logger.info(f"Test completed: {len(opportunities)} opportunities found")

    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
    finally:
        # Cleanup
        if llm_service:
            llm_service.stop_worker_thread()
        release_lock()


if __name__ == "__main__":
    main()
