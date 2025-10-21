#!/usr/bin/env python3
"""
Data Models for HR Tech Lead Generation System
Defines data structures and validation for the system
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Opportunity:
    """Data class for opportunity information"""
    title: str
    company: str
    person: str
    email: str
    url: str
    date: str
    content: str
    relevance_score: float
    signal_type: int
    source: str
    
    def __post_init__(self):
        """Validate data after initialization"""
        if not self.title or not self.company:
            raise ValueError("Title and company are required")
        
        if not 0 <= self.relevance_score <= 1:
            raise ValueError("Relevance score must be between 0 and 1")
        
        if not 1 <= self.signal_type <= 6:
            raise ValueError("Signal type must be between 1 and 6")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV export"""
        return {
            'Title': self.title,
            'Company': self.company,
            'Person': self.person,
            'Email': self.email,
            'URL': self.url,
            'Date': self.date,
            'Relevance Score': self.relevance_score,
            'Signal Type': self.signal_type,
            'Source': self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Opportunity':
        """Create from dictionary"""
        return cls(
            title=data.get('Title', ''),
            company=data.get('Company', ''),
            person=data.get('Person', ''),
            email=data.get('Email', ''),
            url=data.get('URL', ''),
            date=data.get('Date', ''),
            content=data.get('Content', ''),
            relevance_score=float(data.get('Relevance Score', 0)),
            signal_type=int(data.get('Signal Type', 1)),
            source=data.get('Source', '')
        )


@dataclass
class Article:
    """Data class for article information"""
    url: str
    title: str
    snippet: str
    source: str
    content: str
    published_at: Optional[str] = None
    keywords: Optional[List[str]] = None
    creator: Optional[List[str]] = None
    category: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate data after initialization"""
        if not self.url or not self.title:
            raise ValueError("URL and title are required")


@dataclass
class EmailDraft:
    """Data class for email draft information"""
    to_email: str
    subject: str
    body: str
    company: str
    person: str
    signal_type: int
    draft_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate data after initialization"""
        if not self.to_email or not self.subject or not self.body:
            raise ValueError("Email, subject, and body are required")
        
        if not 1 <= self.signal_type <= 6:
            raise ValueError("Signal type must be between 1 and 6")


@dataclass
class SearchQuery:
    """Data class for search query information"""
    query: str
    signal_type: int
    max_results: int = 10
    domains: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate data after initialization"""
        if not self.query:
            raise ValueError("Query is required")
        
        if not 1 <= self.signal_type <= 6:
            raise ValueError("Signal type must be between 1 and 6")


# Signal type constants
SIGNAL_TYPES = {
    1: "HR tech evaluations",
    2: "New leadership ≤90 days", 
    3: "High-intent website/content",
    4: "Tech stack change",
    5: "Expansion",
    6: "Hiring/downsizing"
}

# Quality thresholds
QUALITY_THRESHOLDS = {
    "min_relevance_score": 0.7,
    "min_company_bonus": 0.2,
    "min_person_bonus": 0.3,
    "min_hr_title_bonus": 0.2
}

# Email templates mapping
EMAIL_TEMPLATE_MAPPING = {
    1: "hr_tech_evaluations",
    2: "new_leadership", 
    3: "high_intent_content",
    4: "tech_stack_change",
    5: "expansion",
    6: "hiring_downsizing"
}
