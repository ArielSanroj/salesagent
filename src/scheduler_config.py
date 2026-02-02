#!/usr/bin/env python3
"""
Scheduler Configuration for HR Tech Lead Generation System
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pytz

# Scheduler Configuration
SCHEDULER_CONFIG = {
    "target_opportunities_per_day": 10,
    "target_opportunities_per_week": 50,
    "signals_per_run": 6,
    "results_per_signal": 2,
    "run_time": "07:45",
    "timezone": "America/New_York",
    "email_recipient": "ariel@cliocircle.com",
    "data_retention_days": 90,
    "opportunity_tracking_file": "opportunities_tracking.json",
}

SCHEDULER_LOCK_FILE = "weekly_scheduler.lock"


def get_next_run_time() -> datetime:
    """Get the next scheduled run time in the specified timezone"""
    tz = pytz.timezone(SCHEDULER_CONFIG["timezone"])
    now = datetime.now(tz)

    run_hour, run_minute = map(int, SCHEDULER_CONFIG["run_time"].split(":"))

    next_run = now.replace(hour=run_hour, minute=run_minute, second=0, microsecond=0)

    if next_run <= now:
        next_run += timedelta(days=1)

    return next_run


def parse_week_key(week_key: str) -> Optional[datetime]:
    """Convert stored week identifiers to datetime for retention checks"""
    if not week_key:
        return None

    try:
        return datetime.strptime(f"{week_key}-1", "%Y-%W-%w")
    except Exception:
        pass

    try:
        return datetime.fromisoformat(week_key)
    except Exception:
        return None
