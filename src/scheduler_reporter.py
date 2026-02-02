#!/usr/bin/env python3
"""
Scheduler Reporter for HR Tech Lead Generation System
Handles sending daily and weekly reports
"""

import csv
import logging
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

from constants import SIGNAL_TYPES
from scheduler_config import SCHEDULER_CONFIG

logger = logging.getLogger(__name__)


class SchedulerReporter:
    """Handles sending scheduled reports"""

    def __init__(self, credentials_manager):
        self.credentials_manager = credentials_manager

    def send_weekly_report(
        self,
        week_data: Dict[str, Any],
        total_opportunities: int,
        last_run: Optional[str]
    ) -> None:
        """Send weekly performance report"""
        try:
            current_week = datetime.now().strftime("%Y-%W")

            report = self._build_weekly_report(
                current_week, week_data, total_opportunities, last_run
            )

            msg = MIMEMultipart()
            msg["From"] = "ariel@cliocircle.com"
            msg["To"] = SCHEDULER_CONFIG["email_recipient"]
            msg["Subject"] = f"Weekly HR Tech Lead Generation Report - {current_week}"
            msg.attach(MIMEText(report, "plain"))

            self._send_email(msg)
            logger.info("Weekly report sent successfully")

        except Exception as e:
            logger.error(f"Failed to send weekly report: {e}")

    def _build_weekly_report(
        self,
        current_week: str,
        week_data: Dict[str, Any],
        total_opportunities: int,
        last_run: Optional[str]
    ) -> str:
        """Build weekly report content"""
        report = f"""
Weekly HR Tech Lead Generation Report
=====================================

Week: {current_week}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Performance:
- Opportunities Generated: {week_data.get('total_opportunities', 0)}/{SCHEDULER_CONFIG['target_opportunities_per_week']}
- Target Met: {'YES' if week_data.get('target_met', False) else 'NO'}

Signal Breakdown:
"""
        for signal, count in week_data.get("signal_counts", {}).items():
            report += f"- {signal}: {count} opportunities\n"

        report += f"""
Cumulative Performance:
- Total Opportunities (All Time): {total_opportunities}
- Last Run: {last_run or 'Never'}

Files Generated:
- all_signals.csv: Complete opportunity list
- synthesized_report.md: Trend analysis
- Individual signal files: test_signal_*.csv
- email_drafts_summary.json: Personalized email drafts

Next Run: Tomorrow at {SCHEDULER_CONFIG['run_time']} {SCHEDULER_CONFIG['timezone']}
"""
        return report

    def send_daily_report(self, target: int = None) -> None:
        """Send daily performance report"""
        try:
            target = target or SCHEDULER_CONFIG["target_opportunities_per_day"]
            opportunities = self._load_opportunities_from_csv()

            html_body = self._build_daily_html_report(opportunities, target)
            plain_body = self._build_daily_plain_report(opportunities, target)

            msg = MIMEMultipart("alternative")
            msg["From"] = "ariel@cliocircle.com"
            msg["To"] = SCHEDULER_CONFIG["email_recipient"]
            msg["Subject"] = "daily leads"

            msg.attach(MIMEText(plain_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Attach CSV
            leads_file = Path("all_signals.csv")
            if leads_file.exists():
                self._attach_csv(msg, leads_file)

            self._send_email(msg)
            logger.info(f"Daily report sent with {len(opportunities)} opportunities")

        except Exception as e:
            logger.error(f"Failed to send daily report: {e}", exc_info=True)

    def _load_opportunities_from_csv(self) -> List[Dict[str, Any]]:
        """Load opportunities from CSV file"""
        opportunities = []
        leads_file = Path("all_signals.csv")
        target = SCHEDULER_CONFIG["target_opportunities_per_day"]

        if leads_file.exists():
            try:
                with open(leads_file, "r", newline="") as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        opportunities.append({
                            "company": row.get("Company", "Unknown"),
                            "person": row.get("Person", "N/A"),
                            "email": row.get("Email", "Needs lookup"),
                            "url": row.get("URL", ""),
                            "signal_type": int(row.get("Signal Type", 1)),
                        })
                        if len(opportunities) >= target:
                            break
            except Exception as e:
                logger.error(f"Failed to read leads file: {e}")

        return opportunities

    def _build_daily_html_report(
        self, opportunities: List[Dict[str, Any]], target: int
    ) -> str:
        """Build HTML report content"""
        report_date = datetime.now().strftime('%Y-%m-%d at %H:%M')

        if not opportunities:
            content = "<p>No opportunities were generated during this run.</p>"
        else:
            content = self._build_html_table(opportunities, target)

        return f"""
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
            <p style="margin: 5px 0 0 0; color: #7f8c8d;">Generated on {report_date}</p>
        </div>
        <p>Hello Ariel,</p>
        <p>Here are the latest HR tech opportunities:</p>
        {content}
        <div class="footer">
            <p>This update was automatically generated by your HR Tech Lead Generation System.</p>
        </div>
    </div>
</body>
</html>
"""

    def _build_html_table(self, opportunities: List[Dict[str, Any]], target: int) -> str:
        """Build HTML table for opportunities"""
        rows = []
        for idx, opp in enumerate(opportunities, start=1):
            signal_name = SIGNAL_TYPES.get(opp["signal_type"], "Unknown signal")
            email_val = opp["email"] if opp["email"] else "Needs lookup"
            person_val = opp["person"] if opp["person"] else "N/A"
            url_val = opp["url"] if opp["url"] else ""
            url_display = url_val[:50] + "..." if len(url_val) > 50 else url_val
            url_link = f'<a href="{url_val}">{url_display}</a>' if url_val else "N/A"

            rows.append(f"""
<tr>
    <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{idx}</td>
    <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{opp['company']}</td>
    <td style="border: 1px solid #ddd; padding: 8px;">{signal_name}</td>
    <td style="border: 1px solid #ddd; padding: 8px;">{person_val}</td>
    <td style="border: 1px solid #ddd; padding: 8px;"><a href="mailto:{email_val}">{email_val}</a></td>
    <td style="border: 1px solid #ddd; padding: 8px; font-size: 11px;">{url_link}</td>
</tr>
""")

        return f"""
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
        {''.join(rows)}
    </tbody>
</table>
"""

    def _build_daily_plain_report(
        self, opportunities: List[Dict[str, Any]], target: int
    ) -> str:
        """Build plain text report content"""
        report_date = datetime.now().strftime('%Y-%m-%d at %H:%M')

        body = f"""
Hello Ariel,

Here are the latest HR tech opportunities generated on {report_date}.

Generated {len(opportunities)} opportunities toward a target of {target}.

Opportunities:
"""
        if opportunities:
            body += "\n"
            body += f"{'#':<4} {'Company':<30} {'Signal Type':<30} {'Contact':<25} {'Email':<35}\n"
            body += "-" * 130 + "\n"

            for idx, opp in enumerate(opportunities, start=1):
                signal_name = SIGNAL_TYPES.get(opp["signal_type"], "Unknown signal")
                email_val = opp["email"] if opp["email"] else "Needs lookup"
                person_val = opp["person"] if opp["person"] else "N/A"
                company_short = opp["company"][:28] if len(opp["company"]) > 28 else opp["company"]
                signal_short = signal_name[:28] if len(signal_name) > 28 else signal_name
                person_short = person_val[:23] if len(person_val) > 23 else person_val
                email_short = email_val[:33] if len(email_val) > 33 else email_val

                body += f"{idx:<4} {company_short:<30} {signal_short:<30} {person_short:<25} {email_short:<35}\n"
                if opp["url"]:
                    body += f"     URL: {opp['url']}\n"
        else:
            body += "No opportunities were generated during this run.\n"

        body += "\n---\nThis update was automatically generated by your HR Tech Lead Generation System."
        return body

    def _attach_csv(self, msg: MIMEMultipart, file_path: Path) -> None:
        """Attach CSV file to email"""
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {file_path.name}",
                )
                msg.attach(part)
            logger.info(f"CSV file attached: {file_path.name}")
        except Exception as e:
            logger.warning(f"Failed to attach CSV file: {e}")

    def _send_email(self, msg: MIMEMultipart) -> None:
        """Send email via SMTP"""
        email_config = self.credentials_manager.get_email_config()

        server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
        server.starttls()
        server.login(email_config["sender_email"], email_config["sender_password"])
        server.sendmail(
            "ariel@cliocircle.com",
            SCHEDULER_CONFIG["email_recipient"],
            msg.as_string()
        )
        server.quit()
