#!/usr/bin/env python3
"""
Start Daily HR Tech Lead Generation Scheduler
Runs the lead generation script every day at 8:00 AM
Sends daily reports to ariel@cliocircle.com
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Start the daily scheduler"""
    print("🚀 Starting Daily HR Tech Lead Generation Scheduler")
    print("📅 Schedule: Every day at 8:00 AM Eastern Time")
    print("📧 Reports sent to: ariel@cliocircle.com")
    print("🎯 Target: 10 opportunities per day")
    print("=" * 60)

    try:
        # Run the scheduler
        subprocess.run([sys.executable, "weekly_scheduler.py"], check=True)
    except KeyboardInterrupt:
        print("\n⏹️  Scheduler stopped by user")
    except Exception as e:
        print(f"❌ Error running scheduler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
