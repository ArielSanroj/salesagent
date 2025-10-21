#!/usr/bin/env python3
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
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from pyhunter import PyHunter
from ratelimit import limits, sleep_and_retry
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from urllib3.util.retry import Retry

NEWSDATA_LATEST_URL = "https://newsdata.io/api/1/latest"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    filename="scrape.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Load environment variables
load_dotenv()

# Initialize LLM and test connection
llm = ChatOllama(
    model="llama3.1:8b",
    base_url="http://localhost:11434",
)
try:
    test_response = llm.invoke("Test: What is HR tech?")
    logging.info(f"LLM test successful: {test_response.content}")
except Exception as e:
    logging.error(f"LLM test failed: {e}")
    raise

# Hardcoded config
CONFIG = {
    "keywords": [
        "reducing burnout",
        "improve productivity",
        "HR tech",
        "CHRO",
        "employee engagement",
    ],
    "date_range": {
        "start": "2025-01-01",
        "signal2_start": "2025-06-25",
        "end": "2025-09-23",
    },
    "sources": [
        "nytimes.com",
        "wsj.com",
        "forbes.com",
        "hrdive.com",
        "harvardbusinessreview.org",
        "techcrunch.com",
        "reuters.com",
        "ft.com",
        "shrm.org",
        "peoplematters.in",
    ],
    "newsdata_key": os.getenv("NEWSDATA_API_KEY"),
    "hunter_key": os.getenv("HUNTER_KEY"),
    "email_config": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "ariel@cliocircle.com",
        "sender_password": os.getenv("EMAIL_PASSWORD"),
        "recipient_email": "ariel@cliocircle.com",
    },
}


NEWS_API_CALL_COUNT = 0
NEWS_API_CALL_LIMIT = int(os.getenv("NEWSDATA_API_CALL_LIMIT", "10"))


session = requests.Session()
adapter = HTTPAdapter(
    max_retries=Retry(
        total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
    )
)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Global results list
results = []

# Process lock mechanism to prevent multiple instances
LOCK_FILE = "outbound.lock"


def acquire_lock():
    """Acquire a lock to prevent multiple instances from running"""
    try:
        lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Write PID to lock file
        os.write(lock_fd, str(os.getpid()).encode())
        os.close(lock_fd)
        logging.info(f"Lock acquired successfully (PID: {os.getpid()})")
        return True
    except (OSError, IOError) as e:
        logging.error(f"Could not acquire lock: {e}")
        print(f"❌ Another instance of outbound.py is already running!")
        print(
            f"   If you're sure no other instance is running, delete the lock file: rm {LOCK_FILE}"
        )
        return False


def release_lock():
    """Release the lock when the process exits"""
    try:
        if os.path.exists(LOCK_FILE):
            os.unlink(LOCK_FILE)
            logging.info("Lock released successfully")
    except Exception as e:
        logging.error(f"Error releasing lock: {e}")


# Rate limit for API calls (1 call per 10 seconds)
@sleep_and_retry
@limits(calls=5, period=60)
def rate_limited_request(func, *args, **kwargs):
    kwargs.setdefault("timeout", 20)
    return func(*args, **kwargs)


def can_scrape(url):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124",
        "Accept-Encoding": "gzip, deflate",
    }

    try:
        response = rate_limited_request(
            session.get, robots_url, headers=headers, timeout=10
        )
        if response.status_code == 200:
            content = response.content.decode("utf-8", errors="ignore")
            rp = RobotFileParser()
            rp.parse(content.splitlines())
            allowed = rp.can_fetch("*", url)
            logging.info(f"Checked robots.txt for {url}: Allowed={allowed}")
            return allowed
        logging.warning(
            f"Failed to fetch robots.txt for {url}: Status {response.status_code}"
        )
        return True
    except Exception as e:
        logging.warning(
            f"Failed to check robots.txt for {url}: {e}, assuming scrape allowed"
        )
        return True


# Retry decorator without rate_limited_request
def retry_tool(tool_func, max_attempts=3):
    def wrapper(*args, **kwargs):
        last_err = None
        for attempt in range(max_attempts):
            try:
                return tool_func(*args, **kwargs)
            except Exception as e:
                last_err = e
                logging.error(
                    f"Attempt {attempt + 1}/{max_attempts} failed in {tool_func.__name__}: {e}"
                )
                if attempt < max_attempts - 1:
                    time.sleep(2**attempt)
        logging.error(
            f"{tool_func.__name__} failed after {max_attempts} attempts: {last_err}"
        )
        return None

    return wrapper


# Hunter.io email finder
@retry_tool
def hunter_email_finder(company, first_name, last_name):
    if not CONFIG.get("hunter_key"):
        logging.error("Hunter.io key missing")
        return "Manual validation needed"

    # Safely handle company name
    if not company or not isinstance(company, str):
        return "Manual validation needed"

    domain = f"{company.lower().replace(' ', '')}.com"
    hunter = PyHunter(CONFIG["hunter_key"])
    try:
        result = hunter.email_finder(
            domain=domain, first_name=first_name, last_name=last_name
        )
        if isinstance(result, dict):
            email = result.get("email")
            if email:
                logging.info(
                    f"Hunter.io found email for {first_name} {last_name} at {domain}: {email}"
                )
                return f"mailto:{email}"
        return "Manual validation needed"
    except Exception as e:
        logging.error(f"Hunter.io error for {first_name} {last_name}: {e}")
        return "Manual validation needed"


# LLM-based email finder
@retry_tool
def llm_email_finder(company, person):
    if not company or not person or person.lower() in ["unknown", ""]:
        return "Manual validation needed"

    prompt = PromptTemplate(
        input_variables=["company", "person"],
        template="""Given company '{company}' and person '{person}', suggest the most likely email format.

Return ONLY the email address in this format: firstname.lastname@company.com

Examples:
- Company: Google, Person: John Smith → john.smith@google.com
- Company: Microsoft, Person: Jane Doe → jane.doe@microsoft.com

Company: {company}
Person: {person}
Email:""",
    )
    try:
        response = llm.invoke(prompt.format(company=company, person=person))
        email = (
            response.content.strip()
            if hasattr(response, "content")
            else response.strip()
        )

        # Clean up the response to extract just the email
        if "@" in email:
            email = email.split("\n")[-1].strip()  # Get last line
            if "@" in email and "." in email:
                logging.info(f"LLM suggested email for {person} at {company}: {email}")
                return email

        logging.warning(f"LLM returned invalid email format: {email}")
        return "Manual validation needed"
    except Exception as e:
        logging.error(f"LLM email finder failed for {company}, {person}: {e}")
        return "Manual validation needed"


# Hunter.io email verifier
@retry_tool
def hunter_email_verifier(email):
    if not CONFIG.get("hunter_key"):
        return email
    hunter = PyHunter(CONFIG["hunter_key"])
    try:
        result = hunter.email_verifier(email.replace("mailto:", ""))
        if result["result"] == "deliverable" and result["score"] >= 80:
            return email
        return "Invalid email - Manual validation needed"
    except Exception as e:
        logging.error(f"Verification error for {email}: {e}")
        return email


def _fetch_newsdata_page(endpoint, params):
    """Fetch a single page from NewsData.io API with proper error handling"""
    global NEWS_API_CALL_COUNT

    if NEWS_API_CALL_COUNT >= NEWS_API_CALL_LIMIT:
        raise HTTPError("NewsData.io daily call limit reached")

    try:
        response = rate_limited_request(session.get, endpoint, params=params)

        # Handle rate limiting
        if response.status_code == 429:
            raise HTTPError("NewsData.io rate limit exceeded")

        # Handle other HTTP errors
        if response.status_code == 401:
            raise HTTPError("NewsData.io API key invalid or expired")
        elif response.status_code == 403:
            raise HTTPError("NewsData.io API access forbidden")
        elif response.status_code == 422:
            raise HTTPError("NewsData.io invalid request parameters")

        response.raise_for_status()
        payload = response.json()

        # Check API response status
        if payload.get("status") != "success":
            error_msg = payload.get("message", "NewsData.io API error")
            raise HTTPError(f"NewsData.io API error: {error_msg}")

        return payload

    except requests.exceptions.RequestException as e:
        raise HTTPError(f"NewsData.io request failed: {e}")
    except ValueError as e:
        raise HTTPError(f"NewsData.io invalid JSON response: {e}")
    finally:
        NEWS_API_CALL_COUNT += 1


@retry_tool
def fetch_news_articles(query, num_results=10, domains=None):
    """
    Fetch news articles from NewsData.io API with improved implementation

    Args:
        query: Search query string
        num_results: Maximum number of results to return (1-100)

    Returns:
        List of article dictionaries with standardized format
    """
    # Validate and limit num_results
    num_results = min(max(num_results, 1), 100)

    # Check API key
    key = CONFIG.get("newsdata_key")
    if not key:
        logging.warning("NEWSDATA_API_KEY not configured; returning empty results")
        return []

    aggregated = []
    endpoint = NEWSDATA_LATEST_URL

    # Build base parameters
    params = {
        "apikey": key,
        "q": query,
        "language": "en",
    }

    # Domain filtering disabled for now; NewsData.io is strict about syntax.

    # Add date range if configured (NewsData.io expects YYYY-MM-DD format)
    # Temporarily disable date filtering due to future date issues
    date_range = CONFIG.get("date_range", {})
    if False and date_range.get("start"):  # Disabled for now
        # Ensure date is in YYYY-MM-DD format
        start_date = date_range["start"]
        if len(start_date) > 10:  # If it includes time, truncate
            start_date = start_date[:10]
        params["from_date"] = start_date
    if False and date_range.get("end"):  # Disabled for now
        # Ensure date is in YYYY-MM-DD format
        end_date = date_range["end"]
        if len(end_date) > 10:  # If it includes time, truncate
            end_date = end_date[:10]
        params["to_date"] = end_date

    page_token = None
    max_pages = 5  # Prevent infinite loops
    page_count = 0

    try:
        while len(aggregated) < num_results and page_count < max_pages:
            request_params = dict(params)
            if page_token:
                request_params["page"] = page_token

            payload = _fetch_newsdata_page(endpoint, request_params)
            articles = payload.get("results", [])

            if not articles:
                logging.info("No more articles available from NewsData.io")
                break

            for article in articles:
                if len(aggregated) >= num_results:
                    break

                url = article.get("link")
                if not url:
                    continue

                if domains:
                    parsed_domain = urlparse(url).netloc.lower()
                    stripped_domain = (
                        parsed_domain[4:]
                        if parsed_domain.startswith("www.")
                        else parsed_domain
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

                aggregated.append(article_data)

            page_token = payload.get("nextPage")
            page_count += 1

            if not page_token:
                logging.info("Reached last page of NewsData.io results")
                break

    except HTTPError as e:
        logging.error(f"Error fetching news articles: {e}")
    except Exception as e:
        logging.error(f"Unexpected error fetching news articles: {e}")

    logging.info(f"NewsData.io returned {len(aggregated)} articles for query '{query}'")
    return aggregated[:num_results]


# LLM-based dynamic parsing
@retry_tool
def parse_site_dynamic(url, instructions, raw_text=None, metadata=None):
    if not can_scrape(url):
        logging.warning(f"Cannot scrape {url} per robots.txt")
        return None

    # Try direct scraping first
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"
    }
    text = ""
    metadata = metadata or {}

    try:
        if raw_text and isinstance(raw_text, str) and raw_text.strip():
            text = raw_text.strip()
        else:
            response = rate_limited_request(
                session.get, url, headers=headers, timeout=20
            )
            if response.status_code != 200:
                logging.warning(
                    f"Request failed for {url}: status {response.status_code}"
                )
                return None

            if url.lower().endswith(".pdf"):
                logging.warning(f"Skipping PDF content for {url}")
                return None

            soup = BeautifulSoup(response.text, "html.parser")
            text = " ".join(
                tag.get_text(separator=" ", strip=True)
                for tag in soup.find_all(["p", "h1", "h2", "h3", "article"])
                if tag.get_text(strip=True)
            )

    except Exception as e:
        logging.error(f"Scraping error for {url}: {e}")
        return None

    if not text.strip():
        logging.warning(f"No extractable text found for {url}")
        return None

    # Use LLM to extract structured data
    prompt = PromptTemplate(
        input_variables=["text", "keywords"],
        template="""Extract the following information from this text and return ONLY a valid JSON object with no additional text or commentary:

Text: {text}

Extract:
- title: Article or post title
- date: Publication date in YYYY-MM-DD format
- author: Author name if mentioned
- company: Company name if mentioned
- person: CHRO, HR leader, or executive name if mentioned
- content: Main content summary focusing on {keywords}

Return ONLY this JSON format:
{{"title": "string", "date": "YYYY-MM-DD", "author": "string", "company": "string", "person": "string", "content": "string"}}""",
    )

    for attempt in range(3):
        try:
            llm_resp = llm.invoke(
                prompt.format(text=text[:5000], keywords=CONFIG["keywords"])
            )
            break
        except Exception as e:
            logging.warning(f"LLM attempt {attempt + 1}/3 failed: {e}")
            if attempt == 2:
                logging.error(f"LLM failed after 3 attempts for {url}")
                return None
            time.sleep(2**attempt)

    try:
        content = llm_resp.content if hasattr(llm_resp, "content") else str(llm_resp)
        # Clean up the response if it's wrapped in markdown code blocks
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()
        data = json.loads(content)
    except json.JSONDecodeError:
        logging.warning(f"LLM returned non-JSON response for {url}: {llm_resp}")
        return {
            "title": "",
            "date": "",
            "author": "",
            "company": "",
            "person": "",
            "content": "",
            "relevance_score": 0.0,
        }

    if not data.get("title"):
        data["title"] = metadata.get("title", "")
    if not data.get("date"):
        date_pattern = re.search(r"\b(202[4-5]-[0-1][0-9]-[0-3][0-9])\b", text)
        if date_pattern:
            data["date"] = date_pattern.group(1)
        else:
            data["date"] = metadata.get("publishedAt") or datetime.utcnow().strftime(
                "%Y-%m-%d"
            )
    if not data.get("company"):
        data["company"] = metadata.get("source", "")

    # Enhanced relevance scoring
    content = data.get("content", "")
    title = data.get("title", "")
    company = data.get("company", "")
    person = data.get("person", "")

    # Combine title and content for keyword matching
    full_text = f"{title} {content}".lower()

    # Calculate keyword relevance
    keyword_matches = sum(1 for kw in CONFIG["keywords"] if kw.lower() in full_text)
    keyword_score = keyword_matches / len(CONFIG["keywords"])

    # Bonus points for having company and person
    company_bonus = 0.2 if company and company.strip() else 0
    person_bonus = (
        0.3
        if person and person.strip() and person.lower() not in ["unknown", ""]
        else 0
    )

    # Bonus for HR/CHRO titles
    hr_title_bonus = (
        0.2
        if any(
            title in person.lower()
            for title in ["chro", "hr", "human resources", "people", "talent"]
        )
        else 0
    )

    # Base score + bonuses
    relevance_score = (
        0.4 + (keyword_score * 0.4) + company_bonus + person_bonus + hr_title_bonus
    )
    data.update({"relevance_score": min(1.0, relevance_score)})

    # Safely handle person name splitting
    person = data.get("person", "")
    company = data.get("company", "")

    if company and person and person != "Unknown" and isinstance(person, str):
        if " " in person:
            first_name, last_name = person.split(" ", 1)
        else:
            first_name, last_name = person, ""
        data["contact_url"] = hunter_email_finder(company, first_name, last_name)
        if data["contact_url"].startswith("mailto:"):
            data["contact_url"] = hunter_email_verifier(data["contact_url"])
        else:
            data["contact_url"] = llm_email_finder(company, person)
    else:
        data["contact_url"] = llm_email_finder(company or "", person or "Unknown")

    logging.info(
        f"Parsed {url}: company={data.get('company')}, person={data.get('person')}, score={data.get('relevance_score')}"
    )
    return data


# Email sending function
def send_email_report(report_content, csv_file_path=None):
    """Send the synthesized report via email"""
    email_config = CONFIG.get("email_config", {})

    if not email_config:
        logging.error("Email configuration not found")
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

        logging.info(
            f"Email report sent successfully to {email_config['recipient_email']}"
        )
        return True

    except Exception as e:
        logging.error(f"Failed to send email report: {e}")
        return False


# Gmail draft creation function
def create_gmail_drafts(csv_file_path="all_signals.csv"):
    """Create personalized email drafts using Gmail API"""
    try:
        from gmail_email_system import GmailEmailSystem

        email_system = GmailEmailSystem()

        # Initialize Gmail service
        if not email_system.get_gmail_service():
            logging.error("Failed to initialize Gmail service for draft creation")
            return False

        # Create drafts
        drafts = email_system.create_weekly_email_drafts(csv_file_path)

        if drafts:
            logging.info(
                f"Successfully created {len(drafts)} personalized email drafts"
            )
            return True
        else:
            logging.warning("No email drafts were created")
            return False

    except ImportError:
        logging.error("Gmail email system not available - skipping draft creation")
        return False
    except Exception as e:
        logging.error(f"Failed to create Gmail drafts: {e}")
        return False


# Data synthesis
def synthesize_data(data_list):
    prompt = PromptTemplate(
        input_variables=["data"],
        template="Synthesize HR tech trends from: {data}. Output a markdown report with sections: Trends, Competitors, Recommendations.",
    )
    try:
        response = llm.invoke(prompt.format(data=json.dumps(data_list)))
        report = response.content if hasattr(response, "content") else response
        with open("synthesized_report.md", "w") as f:
            f.write(report)
        logging.info("Generated synthesized report: synthesized_report.md")

        # Send email report with CSV attachment for weekly runs
        if os.getenv("WEEKLY_RUN", "false").lower() == "true":
            csv_file = "all_signals.csv"
            if os.path.exists(csv_file):
                # Send report email
                send_email_report(report, csv_file)

                # Create personalized Gmail drafts
                create_gmail_drafts(csv_file)
            else:
                send_email_report(report)
        else:
            send_email_report(report)

        return report
    except Exception as e:
        logging.error(f"Synthesis failed: {e}")
        return ""


# Add result
def add_result(signal_type, data):
    if not data:
        return
    if data.get("relevance_score", 0) < 0.6:
        logging.info(
            f"Skipping low relevance result: score={data.get('relevance_score', 0)}"
        )
        return
    result = {
        "Signal Type": signal_type,
        "Company": data.get("company") or "",
        "Person": data.get("person") or "",
        "Action Details": data.get("action") or f"{signal_type} outreach",
        "Post or News": data.get("title") or "",
        "Contact Information or URL": data.get("contact_url")
        or "Manual validation needed",
        "Personalized Email Draft": data.get("email_draft") or "",
        "relevance_score": float(data.get("relevance_score") or 0.0),
        "date": data.get("date") or datetime.utcnow().strftime("%Y-%m-%d"),
    }
    results.append(result)
    logging.info(
        f"Added result: {signal_type}, company={result['Company']}, person={result['Person']}"
    )


# Personalize email
def personalize_email(template, data):
    # Safely extract first name
    person = data.get("person") or ""
    if person and isinstance(person, str):
        first = person.split()[0] if person.split() else "HR Leader"
    else:
        first = "HR Leader"

    email = template
    email = email.replace("{{first_name}}", first)
    email = email.replace("{{company}}", data.get("company") or "your organization")
    email = email.replace("{{title}}", data.get("title_role") or "CHRO")

    prompt = PromptTemplate(
        input_variables=["email", "content"],
        template="Refine this email for brevity and clarity. Keep subject line. "
        "Return only the final email text. Email:\n{email}\n\nContext:\n{content}",
    )
    try:
        content = data.get("content") or ""
        if content and isinstance(content, str):
            content = content[:1000]
        else:
            content = ""
        resp = llm.invoke(prompt.format(email=email, content=content))
        refined = resp.content if hasattr(resp, "content") else str(resp)
        return refined.rstrip() + "\n\nOpt out: [opt-out link] | GDPR compliant."
    except Exception as e:
        logging.error(f"Email refinement failed: {e}")
        return email.rstrip() + "\n\nOpt out: [opt-out link] | GDPR compliant."


EMAIL_TEMPLATES = {
    1: """Subject: Insights on Your HR Tech Evaluation for Burnout Reduction
Hi {{first_name}},
Saw {{company}} is evaluating HR tech to reduce burnout and boost productivity—smart move amid $300B global costs.
Clio's RAGBLM delivers 70% wellbeing improvements and 30% productivity gains, outperforming tools like Calm.
Let's discuss how we can support your evaluation. Reply or opt out here: [opt-out link] for GDPR compliance.
Best, [Your Name] Sales Director, Clio Circle AI""",
    2: """Subject: Accelerating Your First 90 Days as {{title}} at {{company}}
Hi {{first_name}},
Congrats on stepping into the {{title}} role at {{company}}—exciting times ahead!
As you build foundations for wellbeing, where burnout drains $300B globally, you're likely prioritizing tools that deliver quick wins without disruption.
Clio's AI platform has helped new HR leaders like you achieve 70% wellbeing improvements and 30% productivity gains in pilots, far surpassing competitors like Headspace (20-25% impact).
Veolia's CHRO used Clio to hit targets in under 60 days with our personalized behavioral DNA maps.
What's top of mind for your team's wellbeing strategy? Reply or opt out here: [opt-out link] for GDPR compliance.
Best, [Your Name] Sales Director, Clio Circle AI""",
    3: """Subject: Following Up on Your Interest in HR Tech for Productivity
Hi {{first_name}},
Noticed engagement with burnout solutions content at {{company}}—aligns with 2025 trends for employee wellbeing.
Clio offers AI-driven interventions for 70% wellbeing lifts and 30% productivity gains.
How can we help? Reply or opt out here: [opt-out link] for GDPR compliance.
Best, [Your Name] Sales Director, Clio Circle AI""",
    4: """Subject: Optimizing Your HR Tech Stack Transition
Hi {{first_name}},
Heard {{company}} is switching HR tools to tackle burnout—timely as productivity demands rise.
Clio integrates seamlessly (e.g., with Workday) for 70% wellbeing improvements.
Let's explore. Reply or opt out here: [opt-out link] for GDPR compliance.
Best, [Your Name] Sales Director, Clio Circle AI""",
    5: """Subject: Scaling Wellbeing Amid {{company}}'s Recent Expansion
Hi {{first_name}}, Congrats on {{company}}'s recent funding/region launch—impressive growth! As you scale, maintaining employee wellbeing is key to avoiding the $300B burnout trap. Clio's AI co-pilot has powered expansions for multinationals, achieving 70% wellbeing lifts and 30% productivity boosts, with scalability to 1M+ users on AWS Bedrock. Group Amalia used us during their UAE growth to standardize across 10K+ employees. How are you planning to support wellbeing in this new phase? Reply or opt out here: [opt-out link] for GDPR compliance.
Best, [Your Name] Sales Director, Clio Circle AI""",
    6: """Subject: Supporting Your HR Hiring for Burnout Prevention
Hi {{first_name}},
Saw {{company}} hiring HR roles focused on productivity and wellbeing—great initiative.
Clio's tools provide 70% improvements to complement your team.
Interested? Reply or opt out here: [opt-out link] for GDPR compliance.
Best, [Your Name] Sales Director, Clio Circle AI""",
}


# Generate query
def generate_query(signal_id):
    start_date = CONFIG.get("date_range", {}).get("start", "2025-01-01")
    base_topics = {
        1: [
            "reducing burnout and employee wellbeing",
            "productivity programs for hr technology",
            "burnout prevention investments in hr tech",
        ],
        2: [
            "new chro onboarding priorities",
            "chief people officer strategy update",
            "people leader appointment human resources",
        ],
        3: [
            "employee wellbeing platform case study",
            "workplace wellness success story",
            "hr platform customer results",
        ],
        4: [
            "hr tech implementation project",
            "hcm migration deployment",
            "workday rollout productivity",
        ],
        5: [
            "hr tech funding announcement",
            "employee experience startup raises",
            "talent platform investment",
        ],
        6: [
            "hiring hr director open role",
            "people operations job posting",
            "talent acquisition lead recruitment",
        ],
    }

    fallback_queries = {
        1: ["hr tech", "employee wellbeing", "burnout reduction"],
        2: ["new chro", "chief people officer", "vp people"],
        3: ["workplace wellness", "employee wellbeing platform", "hr software"],
        4: ["hcm migration", "workday implementation", "hr tech upgrade"],
        5: [
            "hr tech funding",
            "employee experience funding",
            "people analytics investment",
        ],
        6: [
            "hiring hr director",
            "people operations hiring",
            "talent acquisition role",
        ],
    }

    topics = base_topics.get(signal_id, base_topics[1])
    queries = []
    total_limit = 6

    prompt = PromptTemplate(
        input_variables=["topic"],
        template=(
            "List up to three concise keyword phrases (one to three words each) that capture news about {topic}. "
            "Use lowercase letters only, no punctuation or numbering. "
            "Return each phrase on its own line."
        ),
    )

    for topic in topics:
        try:
            resp = llm.invoke(prompt.format(topic=topic))
            content = resp.content if hasattr(resp, "content") else str(resp)
            lines = [
                re.sub(r"[^a-z0-9 ]", " ", line.lower()).strip()
                for line in content.splitlines()
            ]
            candidates = [line for line in lines if line]
        except Exception as e:
            logging.warning(f"LLM keyword generation failed for '{topic}': {e}")
            candidates = []

        if not candidates:
            candidates = [topic.lower()]

        for candidate in candidates:
            tokens = [token for token in candidate.split() if token]
            if not (1 <= len(tokens) <= 3):
                tokens = tokens[:3]
            if not tokens:
                continue
            query = " ".join(tokens)
            if query not in queries:
                queries.append(query)

        if len(queries) >= total_limit:
            break

    for fallback in fallback_queries.get(signal_id, []):
        fallback_clean = " ".join(re.sub(r"[^a-z0-9 ]", " ", fallback.lower()).split())
        if fallback_clean and fallback_clean not in queries:
            queries.append(fallback_clean)
        if len(queries) >= total_limit:
            break

    logging.info(
        f"Generated NewsData queries for signal {signal_id}: {queries[:total_limit]}"
    )
    return queries[:total_limit]


# Run signal
def run_signal(signal_id):
    global NEWS_API_CALL_COUNT

    signal_names = {
        1: "HR tech evaluations",
        2: "New leadership ≤90 days",
        3: "High-intent website/content",
        4: "Tech stack change",
        5: "Expansion",
        6: "Hiring/downsizing",
    }
    query_list = generate_query(signal_id)
    if isinstance(query_list, str):
        query_list = [query_list]

    domains = CONFIG.get("sources", [])
    cleaned_domains = []
    for domain in domains:
        domain = domain.lower().strip()
        if domain.startswith("site:"):
            domain = domain.replace("site:", "", 1)
        domain = domain.replace("https://", "").replace("http://", "")
        domain = domain.split("/")[0]
        if domain:
            cleaned_domains.append(domain)

    try:
        num_results = 30 if os.getenv("WEEKLY_RUN", "false").lower() == "true" else 10
        aggregated_search_results = []
        seen_urls = set()

        for query in query_list:
            if len(aggregated_search_results) >= num_results:
                break
            if NEWS_API_CALL_COUNT >= NEWS_API_CALL_LIMIT:
                logging.warning(
                    "NewsData.io daily call limit reached; stopping further queries"
                )
                break

            per_query_limit = min(5, num_results - len(aggregated_search_results))
            logging.info(
                f"Fetching NewsData.io results for signal {signal_id} query '{query}' (limit {per_query_limit})"
            )

            try:
                articles = fetch_news_articles(
                    query,
                    num_results=per_query_limit,
                    domains=cleaned_domains or None,
                )
            except HTTPError as e:
                logging.error(f"NewsData.io query failed for '{query}': {e}")
                continue

            if not articles:
                logging.info(f"No articles returned for query '{query}'")
                continue

            for article in articles:
                url = article.get("url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                aggregated_search_results.append(article)
                if len(aggregated_search_results) >= num_results:
                    break

        if not aggregated_search_results:
            logging.warning(
                f"No search results for signal {signal_id} across {len(query_list)} queries"
            )
            return

        parsed_data = []
        # Increase workers for weekly runs to process more URLs faster
        max_workers = 5 if os.getenv("WEEKLY_RUN", "false").lower() == "true" else 3
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for res in aggregated_search_results:
                if res and "url" in res:
                    future = executor.submit(
                        parse_site_dynamic,
                        res["url"],
                        f"Extract HR details, {CONFIG['keywords']} mentions",
                        raw_text=res.get("content"),
                        metadata={
                            "title": res.get("title"),
                            "publishedAt": res.get("publishedAt"),
                            "source": res.get("source"),
                        },
                    )
                    futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                try:
                    data = future.result()
                    if data:
                        data["action"] = signal_names[signal_id]
                        data["email_draft"] = personalize_email(
                            EMAIL_TEMPLATES[signal_id], data
                        )
                        parsed_data.append(data)
                        add_result(signal_names[signal_id], data)
                except Exception as e:
                    logging.error(f"Error processing future result: {e}")
                    continue

        if parsed_data:
            synthesize_data(parsed_data)

    except Exception as e:
        logging.error(f"Signal {signal_id} failed: {e}")
    finally:
        logging.info(
            f"NewsData.io calls used: {NEWS_API_CALL_COUNT}/{NEWS_API_CALL_LIMIT}"
        )


# Test signal
def test_signal(signal_id):
    logging.info(f"Testing signal {signal_id}")
    run_signal(signal_id)
    df = filter_results()
    save_results(df, filename=f"test_signal_{signal_id}.csv")
    logging.info(
        f"Test for signal {signal_id} complete. Check test_signal_{signal_id}.csv"
    )


# Filter results
def filter_results(min_score=0.7, max_days_signal2=90):
    df = pd.DataFrame(results)
    if df.empty:
        logging.warning("No results to filter")
        return df
    now = datetime.strptime(CONFIG["date_range"]["end"], "%Y-%m-%d")

    def clean_date(s):
        try:
            d = parse_date(s, fuzzy=True)
            return d.replace(tzinfo=None)
        except Exception:
            return pd.NaT

    df["date_obj"] = df["date"].apply(clean_date)
    mask_recent = (now - df["date_obj"]) <= timedelta(days=365)
    df = df[mask_recent | df["date_obj"].isna()]
    m2 = (df["Signal Type"] == "New leadership ≤90 days") & (
        (now - df["date_obj"]) <= timedelta(days=max_days_signal2)
    )
    df = df[m2 | (df["Signal Type"] != "New leadership ≤90 days")]
    df = df[df["relevance_score"] >= min_score].drop_duplicates(
        subset=["Company", "Person"]
    )
    return df.drop(columns=["date_obj"], errors="ignore")


# Save results
def save_results(df, filename="all_signals.csv"):
    if not df.empty:
        df.to_csv(filename, index=False)
        logging.info(f"Saved {len(df)} results to {filename}")

        # Only send email for test runs, not weekly runs (weekly runs send email from synthesize_data)
        if (
            filename.startswith("test_signal_")
            and not os.getenv("WEEKLY_RUN", "false").lower() == "true"
        ):
            send_email_report(
                "", filename
            )  # Send CSV attachment without report content
    else:
        logging.warning(f"No results to save for {filename}")


# Run full workflow
def run_full_workflow(config_file=None):
    if config_file and os.path.exists(config_file):
        with open(config_file, "r") as f:
            CONFIG.update(json.load(f))
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            executor.map(run_signal, range(1, 7))
        df = filter_results()
        save_results(df)
        logging.info(
            "Workflow complete. Check all_signals.csv and synthesized_report.md"
        )
    except Exception as e:
        logging.error(f"Workflow failed: {str(e)}", exc_info=True)


if __name__ == "__main__":
    # Acquire lock to prevent multiple instances
    if not acquire_lock():
        sys.exit(1)

    try:
        # Check if this is a weekly run
        is_weekly_run = os.getenv("WEEKLY_RUN", "false").lower() == "true"
        target_opportunities = int(os.getenv("TARGET_OPPORTUNITIES", "50"))

        if is_weekly_run:
            logging.info(
                f"Starting weekly run - Target: {target_opportunities} opportunities"
            )

            # Run all signals for weekly production
            for signal_id in range(1, 7):
                logging.info(f"Running signal {signal_id}/6")
                run_signal(signal_id)
                time.sleep(5)  # Brief pause between signals

            # Generate final results
            df_all = filter_results()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            save_results(df_all, f"all_signals_{timestamp}.csv")

            # Also save without timestamp for scheduler
            save_results(df_all, "all_signals.csv")

            logging.info(f"Weekly run completed: {len(df_all)} opportunities generated")

        else:
            # Quick single-signal smoke test for development
            test_signal(1)

    except Exception as e:
        logging.error(f"Workflow failed: {e}", exc_info=True)
    finally:
        # Always release the lock when exiting
        release_lock()
