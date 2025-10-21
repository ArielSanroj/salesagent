#!/usr/bin/env python3
"""
Test script for the daily scheduler
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from weekly_scheduler import WeeklyLeadGenerator, CONFIG
import schedule

def test_scheduler():
    """Test the scheduler setup"""
    print("🧪 Testing Daily Scheduler Setup")
    print("=" * 50)
    
    # Test configuration
    print(f"📅 Run time: {CONFIG['run_time']}")
    print(f"🌍 Timezone: {CONFIG['timezone']}")
    print(f"📧 Email: {CONFIG['email_recipient']}")
    print(f"🎯 Target: {CONFIG['target_opportunities_per_day']} opportunities per day")
    
    # Test scheduler setup
    generator = WeeklyLeadGenerator()
    
    # Clear any existing schedules
    schedule.clear()
    
    # Schedule the daily job
    schedule.every().day.at(CONFIG["run_time"]).do(generator.run_daily_job)
    
    print(f"✅ Scheduler configured successfully")
    print(f"📋 Next run: {schedule.next_run()}")
    
    # Test for 5 seconds
    print("⏱️  Testing scheduler for 5 seconds...")
    start_time = time.time()
    
    while time.time() - start_time < 5:
        schedule.run_pending()
        time.sleep(1)
        print(f"⏰ {time.time() - start_time:.1f}s - Scheduler running...")
    
    print("✅ Scheduler test completed successfully!")

if __name__ == "__main__":
    test_scheduler()