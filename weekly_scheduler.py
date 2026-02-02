#!/usr/bin/env python3
"""
Daily HR Tech Lead Generation Scheduler
Runs lead generation every day at 7:45 AM Eastern Time
"""

import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd
import schedule
from dotenv import load_dotenv

load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from credentials_manager import CredentialsManager
from process_lock import ProcessLock
from scheduler_config import SCHEDULER_CONFIG, SCHEDULER_LOCK_FILE, get_next_run_time
from scheduler_reporter import SchedulerReporter
from tracking_manager import TrackingManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    filename="weekly_scheduler.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)
logger = logging.getLogger(__name__)


class LeadGenerator:
    """Handles lead generation runs and tracking"""

    def __init__(self):
        self.tracking_manager = TrackingManager()
        self.script_path = Path(__file__).parent / "outbound.py"
        self.credentials_manager = CredentialsManager()
        self.reporter = SchedulerReporter(self.credentials_manager)

    def run_lead_generation(self, weekly: bool = False) -> bool:
        """Run the lead generation script"""
        job_label = "weekly" if weekly else "daily"
        logger.info(f"Starting {job_label} lead generation run")

        try:
            cmd = [sys.executable, str(self.script_path)]

            env = os.environ.copy()
            env["WEEKLY_RUN"] = "true" if weekly else "false"
            env["SKIP_EMAIL"] = "true"

            target = (
                SCHEDULER_CONFIG.get("target_opportunities_per_week", 50)
                if weekly
                else SCHEDULER_CONFIG.get("target_opportunities_per_day", 10)
            )
            env["TARGET_OPPORTUNITIES"] = str(target)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
                env=env,
            )

            if result.returncode == 0:
                logger.info("Lead generation completed successfully")
                self._process_results()
                return True
            else:
                logger.error(f"Lead generation failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Lead generation timed out after 1 hour")
            return False
        except Exception as e:
            logger.error(f"Lead generation failed: {e}")
            return False

    def _process_results(self) -> None:
        """Process and track the results"""
        total_opportunities = 0
        signal_counts: Dict[str, int] = {}

        if os.path.exists("all_signals.csv"):
            try:
                df = pd.read_csv("all_signals.csv")
                total_opportunities = len(df)
                signal_counts = df["Signal Type"].value_counts().to_dict()
                logger.info(f"Found {total_opportunities} opportunities")
            except Exception as e:
                logger.error(f"Failed to process all_signals.csv: {e}")

        # Check individual signal files
        for signal_id in range(1, 7):
            signal_file = f"test_signal_{signal_id}.csv"
            if os.path.exists(signal_file):
                try:
                    df = pd.read_csv(signal_file)
                    count = len(df)
                    signal_counts[f"Signal {signal_id}"] = count
                    total_opportunities += count
                except Exception as e:
                    logger.error(f"Failed to process {signal_file}: {e}")

        self.tracking_manager.record_run(total_opportunities, signal_counts)

    def run_weekly_job(self) -> None:
        """Main weekly job function"""
        logger.info("=" * 50)
        logger.info("STARTING WEEKLY LEAD GENERATION JOB")
        logger.info("=" * 50)

        self.tracking_manager.cleanup_old_data()
        success = self.run_lead_generation(weekly=True)

        if success:
            week_data = self.tracking_manager.get_current_week_data()
            self.reporter.send_weekly_report(
                week_data,
                self.tracking_manager.get_total_opportunities(),
                self.tracking_manager.get_last_run()
            )
            logger.info("Weekly job completed successfully")
        else:
            logger.error("Weekly job failed")

        logger.info("=" * 50)
        logger.info("WEEKLY JOB COMPLETED")
        logger.info("=" * 50)

    def run_daily_job(self) -> None:
        """Main daily job function"""
        logger.info("=" * 50)
        logger.info("STARTING DAILY LEAD GENERATION JOB")
        logger.info("=" * 50)

        self.tracking_manager.cleanup_old_data()
        success = self.run_lead_generation(weekly=False)

        # Always send daily report
        try:
            self.reporter.send_daily_report()
            logger.info("Daily report sent")
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")

        if success:
            logger.info("Daily job completed successfully")
        else:
            logger.error("Daily job failed (but report was sent)")

        logger.info("=" * 50)
        logger.info("DAILY JOB COMPLETED")
        logger.info("=" * 50)


def main() -> None:
    """Main function to set up and run the scheduler"""
    lock = ProcessLock(SCHEDULER_LOCK_FILE)

    # Signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        lock.release()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    if not lock.acquire():
        sys.exit(1)

    try:
        generator = LeadGenerator()

        # Schedule daily job
        schedule.every().day.at(SCHEDULER_CONFIG["run_time"]).do(generator.run_daily_job)

        next_run = get_next_run_time()

        logger.info("Daily scheduler started - runs at 7:45 AM Eastern Time")
        logger.info(f"Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"Target: {SCHEDULER_CONFIG['target_opportunities_per_day']} opportunities/day")
        logger.info(f"Email reports sent to: {SCHEDULER_CONFIG['email_recipient']}")

        while True:
            schedule.run_pending()
            time.sleep(60)

    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
    finally:
        lock.release()


if __name__ == "__main__":
    main()
