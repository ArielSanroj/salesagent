#!/bin/bash

# HR Tech Lead Generation - Weekly Scheduler Startup Script
# This script sets up and starts the weekly automation system

echo "🚀 Starting HR Tech Lead Generation Weekly Scheduler"
echo "=================================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << EOF
# HR Tech Lead Generation Configuration
# Add your API keys here

# NVIDIA API Key (required for LLM)
NVIDIA_API_KEY=your_nvidia_api_key_here

# SerpAPI Key (optional, for Google search)
SERPAPI_KEY=your_serpapi_key_here

# Hunter.io Key (optional, for email finding)
HUNTER_KEY=your_hunter_key_here

# BrightData Proxy Password (optional, for proxy access)
BRIGHTDATA_PASSWORD=your_brightdata_password_here

# Email Configuration (already configured)
EMAIL_SENDER=ariel@cliocircle.com
EMAIL_RECIPIENT=ariel@cliocircle.com
EOF
    echo "📝 Please edit .env file with your API keys before running the scheduler."
    echo "   Required: NVIDIA_API_KEY"
    echo "   Optional: SERPAPI_KEY, HUNTER_KEY, BRIGHTDATA_PASSWORD"
    exit 1
fi

# Test the main script first
echo "🧪 Testing main script..."
python3 outbound.py
if [ $? -ne 0 ]; then
    echo "❌ Main script test failed. Please check your configuration."
    exit 1
fi

echo "✅ Main script test passed!"

# Start the weekly scheduler
echo "📅 Starting weekly scheduler..."
echo "   - Runs every Sunday at 8:00 PM GMT-5 (Eastern Time)"
echo "   - Target: 50+ opportunities per week"
echo "   - Reports sent to: ariel@cliocircle.com"
echo "   - Logs saved to: weekly_scheduler.log"
echo "   - Backup runs: Monday & Tuesday at 8:00 PM"
echo ""
echo "Press Ctrl+C to stop the scheduler"
echo "=================================================="

# Run the scheduler
python3 weekly_scheduler.py
