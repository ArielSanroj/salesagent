#!/usr/bin/env python3
"""
Constants for HR Tech Lead Generation System
Centralizes all magic numbers and strings
"""

# API Configuration
NEWSDATA_LATEST_URL = "https://newsdata.io/api/1/latest"
NEWS_API_CALL_LIMIT = 50
NEWS_API_TIMEOUT = 30
NEWS_API_MAX_RETRIES = 3

# Rate Limiting
RATE_LIMIT_CALLS = 5
RATE_LIMIT_PERIOD = 60  # seconds
SCRAPING_TIMEOUT = 30
SCRAPING_MAX_RETRIES = 3

# Quality Thresholds
MIN_RELEVANCE_SCORE = 0.7
MIN_COMPANY_BONUS = 0.2
MIN_PERSON_BONUS = 0.3
MIN_HR_TITLE_BONUS = 0.2

# Signal Types
SIGNAL_TYPES = {
    1: "HR tech evaluations",
    2: "New leadership ≤90 days", 
    3: "High-intent website/content",
    4: "Tech stack change",
    5: "Expansion",
    6: "Hiring/downsizing"
}

# Email Template Mapping
EMAIL_TEMPLATE_MAPPING = {
    1: "hr_tech_evaluations",
    2: "new_leadership", 
    3: "high_intent_content",
    4: "tech_stack_change",
    5: "expansion",
    6: "hiring_downsizing"
}

# Search Keywords
DEFAULT_KEYWORDS = [
    "reducing burnout",
    "improve productivity",
    "HR tech",
    "CHRO",
    "employee engagement"
]

# News Sources
DEFAULT_SOURCES = [
    "nytimes.com",
    "wsj.com",
    "forbes.com",
    "hrdive.com",
    "harvardbusinessreview.org",
    "techcrunch.com",
    "reuters.com",
    "ft.com",
    "shrm.org",
    "peoplematters.in"
]

# File Paths
LOCK_FILE = "outbound.lock"
LOG_FILE = "scrape.log"
EMAIL_LOG_FILE = "gmail_email_system.log"
SCHEDULER_LOG_FILE = "weekly_scheduler.log"
TRACKING_FILE = "opportunities_tracking.json"

# Date Formats
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIMESTAMP_FORMAT = "%Y%m%d_%H%M"

# Email Configuration
DEFAULT_SMTP_SERVER = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_SENDER_EMAIL = "ariel@cliocircle.com"
DEFAULT_RECIPIENT_EMAIL = "ariel@cliocircle.com"

# Gmail API Configuration
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
GMAIL_CREDENTIALS_FILE = "gmail_credentials.json"
GMAIL_TOKEN_FILE = "gmail_token.json"

# Weekly Scheduler Configuration
TARGET_OPPORTUNITIES_PER_WEEK = 50
SIGNALS_PER_RUN = 6
RESULTS_PER_SIGNAL = 10
RUN_DAY = "sunday"
RUN_TIME = "20:00"
TIMEZONE = "America/New_York"
BACKUP_DAYS = ["monday", "tuesday"]
DATA_RETENTION_DAYS = 90

# Processing Configuration
MAX_WORKERS = 5
BATCH_SIZE = 10
PROCESSING_TIMEOUT = 3600  # 1 hour

# Error Messages
ERROR_MESSAGES = {
    "MISSING_CREDENTIALS": "Missing required credentials. Please check your .env file.",
    "LLM_SERVICE_UNAVAILABLE": "LLM service not available, using fallback responses",
    "INVALID_EMAIL": "Invalid email address format",
    "SCRAPING_FAILED": "Failed to scrape content from URL",
    "API_LIMIT_REACHED": "API call limit reached",
    "NETWORK_ERROR": "Network error occurred",
    "VALIDATION_ERROR": "Data validation failed"
}

# Success Messages
SUCCESS_MESSAGES = {
    "SERVICES_INITIALIZED": "All services initialized successfully",
    "OPPORTUNITY_PROCESSED": "Opportunity processed successfully",
    "EMAIL_SENT": "Email sent successfully",
    "DRAFT_CREATED": "Email draft created successfully",
    "DATA_SAVED": "Data saved successfully"
}
