#!/bin/bash

# Setup Daily HR Tech Lead Generation Scheduler
# This script sets up the daily scheduler to run at 8:00 AM

echo "🚀 Setting up Daily HR Tech Lead Generation Scheduler"
echo "📅 Schedule: Every day at 8:00 AM Eastern Time"
echo "📧 Reports sent to: ariel@cliocircle.com"
echo "=" * 60

# Make scripts executable
chmod +x start_daily_scheduler.py
chmod +x weekly_scheduler.py

# For macOS - Install launchd service
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Setting up macOS launchd service..."

    # Copy plist to LaunchAgents directory
    cp com.cliocircle.daily-leadgen.plist ~/Library/LaunchAgents/

    # Load the service
    launchctl load ~/Library/LaunchAgents/com.cliocircle.daily-leadgen.plist

    echo "✅ macOS service installed and started"
    echo "📋 To manage the service:"
    echo "   - Start: launchctl start com.cliocircle.daily-leadgen"
    echo "   - Stop: launchctl stop com.cliocircle.daily-leadgen"
    echo "   - Unload: launchctl unload ~/Library/LaunchAgents/com.cliocircle.daily-leadgen.plist"

elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Setting up Linux systemd service..."

    # Create systemd service file
    sudo tee /etc/systemd/system/daily-leadgen.service > /dev/null <<EOF
[Unit]
Description=Daily HR Tech Lead Generation Scheduler
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 $(pwd)/start_daily_scheduler.py
Restart=always
Environment=NEWSDATA_API_KEY=pub_3125b0dbc6454c3b892c27756202571a
Environment=EMAIL_PASSWORD=test-password
Environment=TARGET_OPPORTUNITIES=10
Environment=WEEKLY_RUN=false

[Install]
WantedBy=multi-user.target
EOF

    # Enable and start the service
    sudo systemctl daemon-reload
    sudo systemctl enable daily-leadgen.service
    sudo systemctl start daily-leadgen.service

    echo "✅ Linux systemd service installed and started"
    echo "📋 To manage the service:"
    echo "   - Status: sudo systemctl status daily-leadgen"
    echo "   - Start: sudo systemctl start daily-leadgen"
    echo "   - Stop: sudo systemctl stop daily-leadgen"
    echo "   - Logs: sudo journalctl -u daily-leadgen -f"

else
    echo "⚠️  Unsupported operating system: $OSTYPE"
    echo "📋 Manual setup required:"
    echo "   1. Run: python3 start_daily_scheduler.py"
    echo "   2. Set up your system's task scheduler to run this daily at 8:00 AM"
fi

echo ""
echo "🎯 Daily Scheduler Configuration:"
echo "   - Time: 8:00 AM Eastern Time"
echo "   - Target: 10 opportunities per day"
echo "   - Email: ariel@cliocircle.com"
echo "   - Logs: daily_scheduler.log"
echo ""
echo "✅ Setup complete!"
