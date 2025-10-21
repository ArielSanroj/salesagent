#!/usr/bin/env python3
"""
Test script to verify the weekly scheduler configuration
"""

from datetime import datetime, timedelta

import pytz


def test_schedule_timing():
    """Test the schedule timing configuration"""

    # Configuration
    timezone = "America/New_York"  # GMT-5
    run_time = "20:00"  # 8 PM

    print("🕐 Weekly Scheduler Schedule Test")
    print("=" * 40)

    # Get current time in timezone
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    print(f"Current time ({timezone}): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Target schedule: Every Sunday at {run_time}")

    # Calculate next Sunday at 8 PM
    days_ahead = 6 - now.weekday()  # Sunday is 6
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7

    next_sunday = now + timedelta(days=days_ahead)
    next_run = next_sunday.replace(hour=20, minute=0, second=0, microsecond=0)

    print(f"Next scheduled run: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Calculate time until next run
    time_until = next_run - now
    days = time_until.days
    hours = time_until.seconds // 3600
    minutes = (time_until.seconds % 3600) // 60

    print(f"Time until next run: {days} days, {hours} hours, {minutes} minutes")

    # Show backup schedule
    print("\n📅 Backup Schedule:")
    print("   - Monday at 8:00 PM (if Sunday fails)")
    print("   - Tuesday at 8:00 PM (if Monday fails)")

    # Show timezone info
    print(f"\n🌍 Timezone Information:")
    print(f"   - Timezone: {timezone}")
    print(f"   - UTC Offset: GMT-5 (EST) / GMT-4 (EDT)")
    print(
        f"   - Current UTC time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

    return next_run


if __name__ == "__main__":
    test_schedule_timing()
