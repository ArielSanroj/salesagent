#!/usr/bin/env python3
"""
Daily HR Tech Lead Generation Scheduler
Automatically runs the lead generation script every day at 7:45 AM Eastern Time (GMT-5)
Generates opportunities daily for Clio Circle AI
"""

import csv
import fcntl
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

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
    "target_opportunities_per_week": 50,  # Weekly target for full runs
    "signals_per_run": 6,  # All 6 signal types
    "results_per_signal": 2,  # Target 2 results per signal daily
    "run_time": "07:45",  # 7:45 AM daily (GMT-5 / Eastern Time)
    "timezone": "America/New_York",  # Eastern Time (GMT-5)
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

    def _parse_week_key(self, week_key: str) -> Optional[datetime]:
        """Convert stored week identifiers to datetime anchors for retention checks."""
        if not week_key:
            return None

        # Primary format uses "%Y-%W" (e.g. "2025-39"); append weekday to make it parseable
        try:
            return datetime.strptime(f"{week_key}-1", "%Y-%W-%w")
        except Exception:
            pass

        # Legacy ISO strings
        try:
            return datetime.fromisoformat(week_key)
        except Exception:
            logging.warning(f"Unable to parse week key '{week_key}', skipping cleanup")
            return None

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
            # week_key format is "%Y-%W" (e.g., "2025-39"); parse accordingly
            week_date = self._parse_week_key(week_key)
            if not week_date:
                continue
            if week_date < cutoff_date:
                weeks_to_remove.append(week_key)

        for week_key in weeks_to_remove:
            del self.opportunities_tracking["opportunities_by_week"][week_key]
            logging.info(f"Cleaned up old week data: {week_key}")

    def run_lead_generation(self, *, weekly: bool = False) -> bool:
        """Run the lead generation script with appropriate configuration"""
        job_label = "weekly" if weekly else "daily"
        logging.info(f"Starting {job_label} lead generation run")

        try:
            # Run the main script with all signals
            cmd = [sys.executable, str(self.script_path)]

            # Set environment variables for production run
            env = os.environ.copy()
            env["WEEKLY_RUN"] = "true" if weekly else "false"
            env["SKIP_EMAIL"] = "true"  # Scheduler will send email, prevent duplicate
            target = (
                CONFIG.get("target_opportunities_per_week", 50)
                if weekly
                else CONFIG.get("target_opportunities_per_day", 10)
            )
            env["TARGET_OPPORTUNITIES"] = str(target)

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
        """Send daily performance report with same format as outbound.py"""
        try:
            import smtplib
            from email import encoders
            from email.mime.base import MIMEBase
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            # Import signal types for formatting
            sys.path.insert(0, str(Path(__file__).parent))
            try:
                from src.constants import SIGNAL_TYPES
            except ImportError:
                # Fallback if import fails
                SIGNAL_TYPES = {
                    1: "HR tech evaluations",
                    2: "New leadership ≤90 days",
                    3: "High-intent website/content",
                    4: "Tech stack change",
                    5: "Expansion",
                    6: "Hiring/downsizing",
                }

            # Read opportunities from CSV
            opportunities = []
            leads_file = Path("all_signals.csv")
            target = CONFIG["target_opportunities_per_day"]

            if leads_file.exists():
                try:
                    with open(leads_file, "r", newline="") as csvfile:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            opportunities.append(
                                {
                                    "company": row.get("Company", "Unknown"),
                                    "person": row.get("Person", "N/A"),
                                    "email": row.get("Email", "Needs lookup"),
                                    "url": row.get("URL", ""),
                                    "signal_type": int(row.get("Signal Type", 1)),
                                }
                            )
                            if len(opportunities) >= target:
                                break
                except Exception as e:
                    logging.error(f"Failed to read leads file: {e}")

            # Build HTML table format for better readability
            if not opportunities:
                report_content = (
                    "<p>No opportunities were generated during this run.</p>"
                )
            else:
                # Create HTML table
                table_rows = []
                for idx, opp in enumerate(opportunities, start=1):
                    signal_name = SIGNAL_TYPES.get(opp["signal_type"], "Unknown signal")
                    email_value = opp["email"] if opp["email"] else "Needs lookup"
                    person_value = opp["person"] if opp["person"] else "N/A"
                    url_value = opp["url"] if opp["url"] else ""

                    # Truncate long URLs for display
                    url_display = (
                        url_value[:50] + "..." if len(url_value) > 50 else url_value
                    )
                    url_link = (
                        f'<a href="{url_value}">{url_display}</a>'
                        if url_value
                        else "N/A"
                    )

                    table_rows.append(
                        f"""
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{idx}</td>
                        <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{opp['company']}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{signal_name}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{person_value}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;"><a href="mailto:{email_value}">{email_value}</a></td>
                        <td style="border: 1px solid #ddd; padding: 8px; font-size: 11px;">{url_link}</td>
                    </tr>
                    """
                    )

                report_content = f"""
                <p>Generated <strong>{len(opportunities)}</strong> opportunities toward a target of <strong>{target}</strong>.</p>
                <table style="border-collapse: collapse; width: 100%; margin: 20px 0; font-family: Arial, sans-serif; font-size: 13px;">
                    <thead>
                        <tr style="background-color: #4CAF50; color: white;">
                            <th style="border: 1px solid #ddd; padding: 12px; text-align: left;">#</th>
                            <th style="border: 1px solid #ddd; padding: 12px; text-align: left;">Company</th>
                            <th style="border: 1px solid #ddd; padding: 12px; text-align: left;">Signal Type</th>
                            <th style="border: 1px solid #ddd; padding: 12px; text-align: left;">Contact</th>
                            <th style="border: 1px solid #ddd; padding: 12px; text-align: left;">Email</th>
                            <th style="border: 1px solid #ddd; padding: 12px; text-align: left;">URL</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(table_rows)}
                    </tbody>
                </table>
                """

            # Create HTML email body
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 1000px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                    .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2 style="margin: 0; color: #2c3e50;">Daily HR Tech Lead Generation Report</h2>
                        <p style="margin: 5px 0 0 0; color: #7f8c8d;">Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M')}</p>
                    </div>

                    <p>Hello Ariel,</p>
                    <p>Here are the latest HR tech opportunities:</p>

                    {report_content}

                    <div class="footer">
                        <p>This update was automatically generated by your HR Tech Lead Generation System.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Create plain text version for email clients that don't support HTML
            plain_body = f"""
Hello Ariel,

Here are the latest HR tech opportunities generated on {datetime.now().strftime('%Y-%m-%d at %H:%M')}.

Generated {len(opportunities)} opportunities toward a target of {target}.

Opportunities:
"""
            if opportunities:
                plain_body += "\n"
                plain_body += f"{'#':<4} {'Company':<30} {'Signal Type':<30} {'Contact':<25} {'Email':<35}\n"
                plain_body += "-" * 130 + "\n"
                for idx, opp in enumerate(opportunities, start=1):
                    signal_name = SIGNAL_TYPES.get(opp["signal_type"], "Unknown signal")
                    email_value = opp["email"] if opp["email"] else "Needs lookup"
                    person_value = opp["person"] if opp["person"] else "N/A"
                    company_short = (
                        opp["company"][:28]
                        if len(opp["company"]) > 28
                        else opp["company"]
                    )
                    signal_short = (
                        signal_name[:28] if len(signal_name) > 28 else signal_name
                    )
                    person_short = (
                        person_value[:23] if len(person_value) > 23 else person_value
                    )
                    email_short = (
                        email_value[:33] if len(email_value) > 33 else email_value
                    )
                    plain_body += f"{idx:<4} {company_short:<30} {signal_short:<30} {person_short:<25} {email_short:<35}\n"
                    if opp["url"]:
                        plain_body += f"     URL: {opp['url']}\n"
            else:
                plain_body += "No opportunities were generated during this run.\n"

            plain_body += "\n---\nThis update was automatically generated by your HR Tech Lead Generation System."

            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = "ariel@cliocircle.com"
            msg["To"] = CONFIG["email_recipient"]
            msg["Subject"] = "daily leads"

            # Attach both plain text and HTML versions
            msg.attach(MIMEText(plain_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Attach CSV file if it exists
            if leads_file.exists():
                try:
                    with open(leads_file, "rb") as attachment:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename= {leads_file.name}",
                        )
                        msg.attach(part)
                    logging.info(f"CSV file attached: {leads_file.name}")
                except Exception as e:
                    logging.warning(f"Failed to attach CSV file: {e}")

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

            logging.info(
                f"Daily report sent successfully with {len(opportunities)} opportunities"
            )

        except Exception as e:
            logging.error(f"Failed to send daily report: {e}", exc_info=True)

    def run_weekly_job(self):
        """Main weekly job function"""
        logging.info("=" * 50)
        logging.info("STARTING WEEKLY LEAD GENERATION JOB")
        logging.info("=" * 50)

        # Cleanup old data
        self.cleanup_old_data()

        # Run lead generation
        success = self.run_lead_generation(weekly=True)

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
        success = self.run_lead_generation(weekly=False)

        # Always send daily report, even if no opportunities found
        # This ensures you receive daily updates
        try:
            self.send_daily_report()
            logging.info("Daily report sent")
        except Exception as e:
            logging.error(f"Failed to send daily report: {e}")

        if success:
            logging.info("Daily job completed successfully")
        else:
            logging.error("Daily job failed (but report was sent)")

        logging.info("=" * 50)
        logging.info("DAILY JOB COMPLETED")
        logging.info("=" * 50)


def get_next_run_time():
    """Get the next scheduled run time in the specified timezone"""
    tz = pytz.timezone(CONFIG["timezone"])
    now = datetime.now(tz)

    run_hour, run_minute = map(int, CONFIG["run_time"].split(":"))

    # Create next run time for today
    next_run = now.replace(hour=run_hour, minute=run_minute, second=0, microsecond=0)

    # If the time has already passed today, schedule for tomorrow
    if next_run <= now:
        next_run += timedelta(days=1)

    return next_run


def main():
    """Main function to set up and run the scheduler"""
    import signal

    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        release_scheduler_lock()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Acquire lock to prevent multiple scheduler instances
    if not acquire_scheduler_lock():
        sys.exit(1)

    try:
        generator = WeeklyLeadGenerator()

        # Schedule the daily job at 7:45 AM Eastern Time
        schedule.every().day.at(CONFIG["run_time"]).do(generator.run_daily_job)

        # Get next run time in timezone
        next_run = get_next_run_time()

        logging.info("Daily scheduler started - runs at 7:45 AM Eastern Time (GMT-5)")
        logging.info("Schedule: Every day at 7:45 AM Eastern Time (GMT-5)")
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
