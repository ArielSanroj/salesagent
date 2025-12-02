#!/usr/bin/env python3
"""
Send historical leads from Nov 5-12, 2025
"""
import csv
import smtplib
import sys
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from constants import SIGNAL_TYPES
from credentials_manager import CredentialsManager

# Configuration
CONFIG = {
    "email_recipient": "ariel@cliocircle.com",
}


def load_opportunities_from_csv_files():
    """Load all opportunities from CSV files dated Nov 5-12"""
    opportunities = []
    csv_files = [
        "all_signals_20251105_0945.csv",
        "all_signals_20251109_0027.csv",
        "all_signals_20251110_0839.csv",
        "all_signals_20251111_0835.csv",
        "all_signals_20251112_0950.csv",
    ]

    for csv_file in csv_files:
        file_path = Path(csv_file)
        if file_path.exists():
            try:
                with open(file_path, "r", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Parse date
                        date_str = row.get("Date", "")
                        try:
                            opp_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                            # Check if date is between Nov 5-12
                            if (
                                datetime(2025, 11, 5).date()
                                <= opp_date
                                <= datetime(2025, 11, 12).date()
                            ):
                                opportunities.append(
                                    {
                                        "company": row.get("Company", "Unknown"),
                                        "person": row.get("Person", "N/A"),
                                        "email": row.get("Email", "Needs lookup"),
                                        "url": row.get("URL", ""),
                                        "signal_type": int(row.get("Signal Type", 1)),
                                        "date": date_str,
                                        "title": row.get("Title", ""),
                                        "relevance_score": row.get(
                                            "Relevance Score", "0"
                                        ),
                                    }
                                )
                        except ValueError:
                            # If date parsing fails, include it anyway
                            opportunities.append(
                                {
                                    "company": row.get("Company", "Unknown"),
                                    "person": row.get("Person", "N/A"),
                                    "email": row.get("Email", "Needs lookup"),
                                    "url": row.get("URL", ""),
                                    "signal_type": int(row.get("Signal Type", 1)),
                                    "date": date_str,
                                    "title": row.get("Title", ""),
                                    "relevance_score": row.get("Relevance Score", "0"),
                                }
                            )
            except Exception as e:
                print(f"Error reading {csv_file}: {e}")

    # Remove duplicates based on company and person
    seen = set()
    unique_opportunities = []
    for opp in opportunities:
        key = (opp["company"].lower(), opp["person"].lower())
        if key not in seen:
            seen.add(key)
            unique_opportunities.append(opp)

    return unique_opportunities


def send_historical_leads_email(opportunities):
    """Send email with historical leads in table format"""
    credentials_manager = CredentialsManager()
    email_config = credentials_manager.get_email_config()

    if not opportunities:
        print("No opportunities found for Nov 5-12")
        return

    # Create HTML table
    table_rows = []
    for idx, opp in enumerate(opportunities, start=1):
        signal_name = SIGNAL_TYPES.get(opp["signal_type"], "Unknown signal")
        email_value = opp["email"] if opp["email"] else "Needs lookup"
        person_value = opp["person"] if opp["person"] else "N/A"
        url_value = opp["url"] if opp["url"] else ""
        date_value = opp["date"] if opp["date"] else "N/A"

        # Truncate long URLs for display
        url_display = url_value[:50] + "..." if len(url_value) > 50 else url_value
        url_link = f'<a href="{url_value}">{url_display}</a>' if url_value else "N/A"

        table_rows.append(
            f"""
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{idx}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{date_value}</td>
            <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{opp['company']}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{signal_name}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{person_value}</td>
            <td style="border: 1px solid #ddd; padding: 8px;"><a href="mailto:{email_value}">{email_value}</a></td>
            <td style="border: 1px solid #ddd; padding: 8px; font-size: 11px;">{url_link}</td>
        </tr>
        """
        )

    html_table = f"""
    <p>Found <strong>{len(opportunities)}</strong> unique opportunities from November 5-12, 2025.</p>
    <table style="border-collapse: collapse; width: 100%; margin: 20px 0; font-family: Arial, sans-serif; font-size: 13px;">
        <thead>
            <tr style="background-color: #4CAF50; color: white;">
                <th style="border: 1px solid #ddd; padding: 12px; text-align: left;">#</th>
                <th style="border: 1px solid #ddd; padding: 12px; text-align: left;">Date</th>
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

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f4f4f4; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .footer {{ margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2 style="margin: 0; color: #2c3e50;">Historical HR Tech Lead Generation Report</h2>
                <p style="margin: 5px 0 0 0; color: #7f8c8d;">November 5-12, 2025</p>
            </div>

            <p>Hello Ariel,</p>
            <p>Here are all the HR tech opportunities generated from November 5-12, 2025:</p>

            {html_table}

            <div class="footer">
                <p>This report was generated on {datetime.now().strftime('%Y-%m-%d at %H:%M')}.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plain text version
    plain_body = f"""
Hello Ariel,

Here are all the HR tech opportunities from November 5-12, 2025.

Found {len(opportunities)} unique opportunities.

Opportunities:
"""
    plain_body += "\n"
    plain_body += f"{'#':<4} {'Date':<12} {'Company':<30} {'Signal Type':<30} {'Contact':<25} {'Email':<35}\n"
    plain_body += "-" * 150 + "\n"
    for idx, opp in enumerate(opportunities, start=1):
        signal_name = SIGNAL_TYPES.get(opp["signal_type"], "Unknown signal")
        email_value = opp["email"] if opp["email"] else "Needs lookup"
        person_value = opp["person"] if opp["person"] else "N/A"
        date_value = opp["date"] if opp["date"] else "N/A"
        company_short = (
            opp["company"][:28] if len(opp["company"]) > 28 else opp["company"]
        )
        signal_short = signal_name[:28] if len(signal_name) > 28 else signal_name
        person_short = person_value[:23] if len(person_value) > 23 else person_value
        email_short = email_value[:33] if len(email_value) > 33 else email_value
        plain_body += f"{idx:<4} {date_value:<12} {company_short:<30} {signal_short:<30} {person_short:<25} {email_short:<35}\n"
        if opp["url"]:
            plain_body += f"     URL: {opp['url']}\n"

    plain_body += f"\n---\nGenerated on {datetime.now().strftime('%Y-%m-%d at %H:%M')}."

    # Create message
    msg = MIMEMultipart("alternative")
    msg["From"] = email_config["sender_email"]
    msg["To"] = CONFIG["email_recipient"]
    msg["Subject"] = "Historical Leads: November 5-12, 2025"

    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # Send email
    try:
        server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
        server.starttls()
        server.login(email_config["sender_email"], email_config["sender_password"])
        server.sendmail(
            email_config["sender_email"], CONFIG["email_recipient"], msg.as_string()
        )
        server.quit()
        print(f"✅ Email sent successfully with {len(opportunities)} opportunities!")
        print(f"📧 Sent to: {CONFIG['email_recipient']}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("📊 Loading opportunities from Nov 5-12, 2025...")
    opportunities = load_opportunities_from_csv_files()
    print(f"✅ Found {len(opportunities)} unique opportunities")

    if opportunities:
        print("📧 Sending email...")
        send_historical_leads_email(opportunities)
    else:
        print("⚠️  No opportunities found for the specified date range")
