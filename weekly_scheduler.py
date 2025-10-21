#!/usr/bin/env python3
"""
Daily HR Tech Lead Generation Scheduler
Automatically runs the lead generation script every day at 8:00 AM
Generates opportunities daily for Clio Circle AI
"""

import fcntl
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytz
import schedule

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from credentials_manager import CredentialsManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    filename="weekly_scheduler.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)

# Configuration
CONFIG = {
    "target_opportunities_per_day": 10,  # Daily target
    "signals_per_run": 6,  # All 6 signal types
    "results_per_signal": 2,  # Target 2 results per signal daily
    "run_time": "08:00",  # 8:00 AM daily
    "timezone": "America/New_York",  # Eastern Time
    "email_recipient": "ariel@cliocircle.com",
    "data_retention_days": 90,  # Keep data for 90 days
    "opportunity_tracking_file": "opportunities_tracking.json",
}

# Process lock mechanism to prevent multiple scheduler instances
SCHEDULER_LOCK_FILE = "weekly_scheduler.lock"


def acquire_scheduler_lock():
    """Acquire a lock to prevent multiple scheduler instances from running"""
    try:
        lock_fd = os.open(SCHEDULER_LOCK_FILE, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Write PID to lock file
        os.write(lock_fd, str(os.getpid()).encode())
        os.close(lock_fd)
        logging.info(f"Scheduler lock acquired successfully (PID: {os.getpid()})")
        return True
    except (OSError, IOError) as e:
        logging.error(f"Could not acquire scheduler lock: {e}")
        print("❌ Another instance of weekly_scheduler.py is already running!")
        print(
            f"   If you're sure no other instance is running, delete the lock file: rm {SCHEDULER_LOCK_FILE}"
        )
        return False


def release_scheduler_lock():
    """Release the scheduler lock when the process exits"""
    try:
        if os.path.exists(SCHEDULER_LOCK_FILE):
            os.unlink(SCHEDULER_LOCK_FILE)
            logging.info("Scheduler lock released successfully")
    except Exception as e:
        logging.error(f"Error releasing scheduler lock: {e}")


class WeeklyLeadGenerator:
    def __init__(self):
        self.opportunities_tracking = self.load_tracking_data()
        self.script_path = Path(__file__).parent / "outbound.py"
        self.credentials_manager = CredentialsManager()

    def load_tracking_data(self):
        """Load existing opportunity tracking data"""
        tracking_file = CONFIG["opportunity_tracking_file"]
        if os.path.exists(tracking_file):
            try:
                with open(tracking_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load tracking data: {e}")
        return {
            "weekly_runs": {},
            "total_opportunities": 0,
            "opportunities_by_week": {},
            "last_run": None,
        }

    def save_tracking_data(self):
        """Save opportunity tracking data"""
        try:
            with open(CONFIG["opportunity_tracking_file"], "w") as f:
                json.dump(self.opportunities_tracking, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save tracking data: {e}")

    def cleanup_old_data(self):
        """Clean up data older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=CONFIG["data_retention_days"])

        # Clean up old CSV files
        for file_pattern in ["test_signal_*.csv", "all_signals_*.csv"]:
            for file_path in Path(".").glob(file_pattern):
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    file_path.unlink()
                    logging.info(f"Cleaned up old file: {file_path}")

        # Clean up old tracking data
        weeks_to_remove = []
        for week_key in self.opportunities_tracking["opportunities_by_week"]:
            week_date = datetime.fromisoformat(week_key)
            if week_date < cutoff_date:
                weeks_to_remove.append(week_key)

        for week_key in weeks_to_remove:
            del self.opportunities_tracking["opportunities_by_week"][week_key]
            logging.info(f"Cleaned up old week data: {week_key}")

    def run_lead_generation(self):
        """Run the lead generation script with enhanced parameters"""
        logging.info("Starting weekly lead generation run")

        try:
            # Run the main script with all signals
            cmd = [sys.executable, str(self.script_path)]

            # Set environment variables for production run
            env = os.environ.copy()
            env["WEEKLY_RUN"] = "true"
            env["TARGET_OPPORTUNITIES"] = str(CONFIG["target_opportunities_per_week"])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
                env=env,  # 1 hour timeout
            )

            if result.returncode == 0:
                logging.info("Lead generation completed successfully")
                self.process_results()
                return True
            else:
                logging.error(f"Lead generation failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logging.error("Lead generation timed out after 1 hour")
            return False
        except Exception as e:
            logging.error(f"Lead generation failed: {e}")
            return False

    def process_results(self):
        """Process and track the results from the lead generation run"""
        current_week = datetime.now().strftime("%Y-%W")

        # Count opportunities from CSV files
        total_opportunities = 0
        signal_counts = {}

        # Check for all_signals.csv (full run)
        if os.path.exists("all_signals.csv"):
            import pandas as pd

            try:
                df = pd.read_csv("all_signals.csv")
                total_opportunities = len(df)

                # Count by signal type
                signal_counts = df["Signal Type"].value_counts().to_dict()

                logging.info(
                    f"Found {total_opportunities} opportunities in all_signals.csv"
                )

            except Exception as e:
                logging.error(f"Failed to process all_signals.csv: {e}")

        # Check individual signal files
        for signal_id in range(1, 7):
            signal_file = f"test_signal_{signal_id}.csv"
            if os.path.exists(signal_file):
                try:
                    df = pd.read_csv(signal_file)
                    signal_count = len(df)
                    signal_counts[f"Signal {signal_id}"] = signal_count
                    total_opportunities += signal_count
                except Exception as e:
                    logging.error(f"Failed to process {signal_file}: {e}")

        # Update tracking data
        self.opportunities_tracking["weekly_runs"][current_week] = {
            "date": datetime.now().isoformat(),
            "total_opportunities": total_opportunities,
            "signal_counts": signal_counts,
            "target_met": total_opportunities
            >= CONFIG["target_opportunities_per_week"],
        }

        self.opportunities_tracking["total_opportunities"] += total_opportunities
        self.opportunities_tracking["opportunities_by_week"][
            current_week
        ] = total_opportunities
        self.opportunities_tracking["last_run"] = datetime.now().isoformat()

        # Save tracking data
        self.save_tracking_data()

        # Log results
        logging.info(
            f"Weekly run completed: {total_opportunities} opportunities generated"
        )
        logging.info(f"Signal breakdown: {signal_counts}")

        if total_opportunities >= CONFIG["target_opportunities_per_week"]:
            logging.info(
                f"✅ Target met: {total_opportunities}/{CONFIG['target_opportunities_per_week']} opportunities"
            )
        else:
            logging.warning(
                f"⚠️ Target not met: {total_opportunities}/{CONFIG['target_opportunities_per_week']} opportunities"
            )

    def send_weekly_report(self):
        """Send weekly performance report"""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            # Get current week data
            current_week = datetime.now().strftime("%Y-%W")
            week_data = self.opportunities_tracking["weekly_runs"].get(current_week, {})

            # Create report
            report = f"""
Weekly HR Tech Lead Generation Report
=====================================

Week: {current_week}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Performance:
- Opportunities Generated: {week_data.get('total_opportunities', 0)}/{CONFIG['target_opportunities_per_week']}
- Target Met: {'✅ YES' if week_data.get('target_met', False) else '❌ NO'}

Signal Breakdown:
"""

            for signal, count in week_data.get("signal_counts", {}).items():
                report += f"- {signal}: {count} opportunities\n"

            report += f"""
Cumulative Performance:
- Total Opportunities (All Time): {self.opportunities_tracking['total_opportunities']}
- Last Run: {self.opportunities_tracking.get('last_run', 'Never')}

Files Generated:
- all_signals.csv: Complete opportunity list
- synthesized_report.md: Trend analysis
- Individual signal files: test_signal_*.csv
- email_drafts_summary.json: Personalized email drafts created

Email Drafts:
- Personalized drafts created in Gmail for each lead
- Each draft tailored to specific signal type and company context
- Ready for review and sending

Next Run: Next Sunday at 8:00 PM Eastern Time
"""

            # Send email
            msg = MIMEMultipart()
            msg["From"] = "ariel@cliocircle.com"
            msg["To"] = CONFIG["email_recipient"]
            msg["Subject"] = f"Weekly HR Tech Lead Generation Report - {current_week}"

            msg.attach(MIMEText(report, "plain"))

            # Get email configuration from credentials manager
            email_config = self.credentials_manager.get_email_config()

            server = smtplib.SMTP(
                email_config["smtp_server"], email_config["smtp_port"]
            )
            server.starttls()
            server.login(email_config["sender_email"], email_config["sender_password"])
            server.sendmail(
                "ariel@cliocircle.com", CONFIG["email_recipient"], msg.as_string()
            )
            server.quit()

            logging.info("Weekly report sent successfully")

        except Exception as e:
            logging.error(f"Failed to send weekly report: {e}")

    def send_daily_report(self):
        """Send daily performance report"""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            # Get current day data
            current_date = datetime.now().strftime("%Y-%m-%d")

            # Create report
            report = f"""
Daily HR Tech Lead Generation Report
====================================

Date: {current_date}
Time: {datetime.now().strftime('%H:%M')}

Performance:
- Target: {CONFIG['target_opportunities_per_day']} opportunities per day
- Signals Processed: {CONFIG['signals_per_run']} signal types
- Results per Signal: {CONFIG['results_per_signal']} opportunities

Daily Summary:
- All 6 buyer signals activated
- NewsData API searches completed
- Content scraping and LLM analysis performed
- Quality filtering applied (relevance score > 0.7)

Files Generated:
- all_signals.csv: Complete opportunity list
- Individual signal files: test_signal_*.csv
- email_drafts_summary.json: Personalized email drafts created

Email Drafts:
- Personalized drafts created in Gmail for each lead
- Each draft tailored to specific signal type and company context
- Ready for review and sending

Next Run: Tomorrow at 8:00 AM Eastern Time
"""

            # Send email
            msg = MIMEMultipart()
            msg["From"] = "ariel@cliocircle.com"
            msg["To"] = CONFIG["email_recipient"]
            msg["Subject"] = f"Daily HR Tech Lead Generation Report - {current_date}"

            msg.attach(MIMEText(report, "plain"))

            # Get email configuration from credentials manager
            email_config = self.credentials_manager.get_email_config()

            server = smtplib.SMTP(
                email_config["smtp_server"], email_config["smtp_port"]
            )
            server.starttls()
            server.login(email_config["sender_email"], email_config["sender_password"])
            server.sendmail(
                "ariel@cliocircle.com", CONFIG["email_recipient"], msg.as_string()
            )
            server.quit()

            logging.info("Daily report sent successfully")

        except Exception as e:
            logging.error(f"Failed to send daily report: {e}")

    def run_weekly_job(self):
        """Main weekly job function"""
        logging.info("=" * 50)
        logging.info("STARTING WEEKLY LEAD GENERATION JOB")
        logging.info("=" * 50)

        # Cleanup old data
        self.cleanup_old_data()

        # Run lead generation
        success = self.run_lead_generation()

        if success:
            # Send weekly report
            self.send_weekly_report()
            logging.info("Weekly job completed successfully")
        else:
            logging.error("Weekly job failed")

        logging.info("=" * 50)
        logging.info("WEEKLY JOB COMPLETED")
        logging.info("=" * 50)

    def run_daily_job(self):
        """Main daily job function"""
        logging.info("=" * 50)
        logging.info("STARTING DAILY LEAD GENERATION JOB")
        logging.info("=" * 50)

        # Cleanup old data
        self.cleanup_old_data()

        # Run lead generation with daily target
        success = self.run_lead_generation()

        if success:
            # Send daily report
            self.send_daily_report()
            logging.info("Daily job completed successfully")
        else:
            logging.error("Daily job failed")

        logging.info("=" * 50)
        logging.info("DAILY JOB COMPLETED")
        logging.info("=" * 50)


def get_next_run_time():
    """Get the next scheduled run time in the specified timezone"""
    tz = pytz.timezone(CONFIG["timezone"])
    now = datetime.now(tz)

    # Get next Sunday at 8 PM
    days_ahead = 6 - now.weekday()  # Sunday is 6
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7

    next_sunday = now + timedelta(days=days_ahead)
    next_run = next_sunday.replace(hour=20, minute=0, second=0, microsecond=0)

    return next_run


def main():
    """Main function to set up and run the scheduler"""
    # Acquire lock to prevent multiple scheduler instances
    if not acquire_scheduler_lock():
        sys.exit(1)

    try:
        generator = WeeklyLeadGenerator()

        # Schedule the daily job at 8:00 AM
        schedule.every().day.at(CONFIG["run_time"]).do(generator.run_daily_job)

        # Get next run time in timezone
        next_run = get_next_run_time()

        logging.info("Daily scheduler started - runs at 8:00 AM Eastern Time")
        logging.info("Schedule: Every day at 8:00 AM Eastern Time")
        logging.info(f"Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logging.info(
            f"Target: {CONFIG['target_opportunities_per_day']} opportunities per day"
        )
        logging.info(f"Email reports sent to: {CONFIG['email_recipient']}")

        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        logging.info("Scheduler stopped by user")
    except Exception as e:
        logging.error(f"Scheduler error: {e}")
    finally:
        # Always release the lock when exiting
        release_scheduler_lock()


if __name__ == "__main__":
    main()
