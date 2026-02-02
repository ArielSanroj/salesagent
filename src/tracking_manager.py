#!/usr/bin/env python3
"""
Tracking Manager for HR Tech Lead Generation System
Handles opportunity tracking data persistence and cleanup
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from scheduler_config import SCHEDULER_CONFIG, parse_week_key

logger = logging.getLogger(__name__)


class TrackingManager:
    """Manages opportunity tracking data"""

    def __init__(self):
        self.tracking_file = SCHEDULER_CONFIG["opportunity_tracking_file"]
        self.data = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """Load existing tracking data"""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load tracking data: {e}")

        return {
            "weekly_runs": {},
            "total_opportunities": 0,
            "opportunities_by_week": {},
            "last_run": None,
        }

    def save(self) -> None:
        """Save tracking data"""
        try:
            with open(self.tracking_file, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tracking data: {e}")

    def cleanup_old_data(self) -> None:
        """Clean up data older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=SCHEDULER_CONFIG["data_retention_days"])

        # Clean up old CSV files
        for pattern in ["test_signal_*.csv", "all_signals_*.csv"]:
            for file_path in Path(".").glob(pattern):
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    file_path.unlink()
                    logger.info(f"Cleaned up old file: {file_path}")

        # Clean up old tracking data
        weeks_to_remove = []
        for week_key in self.data["opportunities_by_week"]:
            week_date = parse_week_key(week_key)
            if not week_date:
                continue
            if week_date < cutoff_date:
                weeks_to_remove.append(week_key)

        for week_key in weeks_to_remove:
            del self.data["opportunities_by_week"][week_key]
            logger.info(f"Cleaned up old week data: {week_key}")

    def record_run(self, total_opportunities: int, signal_counts: Dict[str, int]) -> None:
        """Record a run's results"""
        current_week = datetime.now().strftime("%Y-%W")

        self.data["weekly_runs"][current_week] = {
            "date": datetime.now().isoformat(),
            "total_opportunities": total_opportunities,
            "signal_counts": signal_counts,
            "target_met": total_opportunities >= SCHEDULER_CONFIG["target_opportunities_per_week"],
        }

        self.data["total_opportunities"] += total_opportunities
        self.data["opportunities_by_week"][current_week] = total_opportunities
        self.data["last_run"] = datetime.now().isoformat()

        self.save()

        logger.info(f"Recorded run: {total_opportunities} opportunities")

        if total_opportunities >= SCHEDULER_CONFIG["target_opportunities_per_week"]:
            logger.info(f"Target met: {total_opportunities}/{SCHEDULER_CONFIG['target_opportunities_per_week']}")
        else:
            logger.warning(f"Target not met: {total_opportunities}/{SCHEDULER_CONFIG['target_opportunities_per_week']}")

    def get_current_week_data(self) -> Dict[str, Any]:
        """Get current week's data"""
        current_week = datetime.now().strftime("%Y-%W")
        return self.data["weekly_runs"].get(current_week, {})

    def get_total_opportunities(self) -> int:
        """Get total opportunities all time"""
        return self.data["total_opportunities"]

    def get_last_run(self) -> Optional[str]:
        """Get last run timestamp"""
        return self.data.get("last_run")
