#!/usr/bin/env python3
"""
Test script to send a test email with the new table format
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging

from weekly_scheduler import CONFIG, WeeklyLeadGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

print("📧 Sending test email with new table format...")
print(f"📬 Recipient: {CONFIG['email_recipient']}")

# Create generator instance
generator = WeeklyLeadGenerator()

# Send daily report (will use existing CSV if available)
try:
    generator.send_daily_report()
    print("✅ Test email sent successfully!")
    print("📧 Check your inbox at", CONFIG["email_recipient"])
except Exception as e:
    print(f"❌ Error sending email: {e}")
    import traceback

    traceback.print_exc()
