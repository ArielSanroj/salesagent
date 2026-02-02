#!/usr/bin/env python3
"""
Results Manager for HR Tech Lead Generation System
Handles saving, filtering, and deduplicating opportunities
"""

import logging
from datetime import datetime
from typing import Any, List

import pandas as pd

from models import Opportunity

logger = logging.getLogger(__name__)


def save_results(opportunities: List[Opportunity], filename: str) -> None:
    """Save opportunities to CSV file"""
    if not opportunities:
        logger.warning("No opportunities to save")
        return

    data = [opp.to_dict() for opp in opportunities]
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


def load_opportunities_from_csv(filename: str) -> List[Opportunity]:
    """Load opportunities from CSV file"""
    try:
        df = pd.read_csv(filename)
        opportunities = []
        for _, row in df.iterrows():
            opp = Opportunity.from_dict(row.to_dict())
            opportunities.append(opp)
        return opportunities
    except Exception as e:
        logger.error(f"Failed to load opportunities from {filename}: {e}")
        return []


def get_timestamped_filename(prefix: str) -> str:
    """Generate timestamped filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{prefix}_{timestamp}.csv"
