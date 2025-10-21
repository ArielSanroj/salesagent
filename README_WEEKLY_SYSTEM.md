# HR Tech Lead Generation - Weekly Automation System

## 🎯 Overview

This system automatically generates **50+ HR tech opportunities per week** and sends comprehensive reports to `ariel@cliocircle.com` every **Sunday at 8:00 PM GMT-5** (Eastern Time).

## 📅 Schedule

- **Primary Run**: Every Sunday at 8:00 PM Eastern Time
- **Backup Runs**: Monday & Tuesday at 8:00 PM (if Sunday fails)
- **Target**: 50+ opportunities per week
- **Reports**: Automated email delivery with CSV attachments

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Clone and navigate to project
cd /path/to/outboundai

# Run the startup script
./start_weekly_scheduler.sh
```

### 2. Configure API Keys
Edit `.env` file with your API keys:
```env
# Required
NVIDIA_API_KEY=your_nvidia_api_key_here

# Optional (for enhanced functionality)
SERPAPI_KEY=your_serpapi_key_here
HUNTER_KEY=your_hunter_key_here
BRIGHTDATA_PASSWORD=your_brightdata_password_here
```

### 3. Start Weekly Automation
```bash
# Activate virtual environment
source venv/bin/activate

# Start the scheduler
python3 weekly_scheduler.py
```

## 📊 System Components

### Core Files
- `outbound.py` - Main lead generation script
- `weekly_scheduler.py` - Automated scheduling system
- `start_weekly_scheduler.sh` - Easy startup script
- `production_config.json` - Production configuration
- `requirements.txt` - Python dependencies

### Generated Files
- `all_signals.csv` - Complete opportunity list
- `synthesized_report.md` - Trend analysis report
- `test_signal_*.csv` - Individual signal results
- `weekly_scheduler.log` - System logs
- `opportunities_tracking.json` - Performance tracking

## 🎯 Signal Types (6 Total)

1. **HR Tech Evaluations** - Companies evaluating HR tech solutions
2. **New Leadership ≤90 Days** - Recent CHRO/HR leader appointments
3. **High-Intent Website/Content** - Companies with HR tech content
4. **Tech Stack Change** - Companies switching HR systems
5. **Expansion** - Companies with recent funding/growth
6. **Hiring/Downsizing** - HR team changes

## 📈 Performance Tracking

The system tracks:
- **Weekly opportunity counts**
- **Signal type breakdown**
- **Target achievement (50+ per week)**
- **Email delivery status**
- **Historical performance data**

## 🔧 Configuration Options

### Weekly Scheduler (`production_config.json`)
```json
{
  "weekly_scheduler": {
    "target_opportunities_per_week": 50,
    "run_day": "sunday",
    "run_time": "20:00",
    "timezone": "America/New_York",
    "backup_days": ["monday", "tuesday"],
    "email_recipient": "ariel@cliocircle.com"
  }
}
```

### Search Optimization
- **Weekly Results**: 30 per signal (vs 20 for testing)
- **Concurrent Workers**: 5 (vs 3 for testing)
- **Timeout**: 1 hour per run
- **Rate Limiting**: 1 call per 8 seconds

## 📧 Email System

### Weekly Report Includes:
- **Performance Summary**: Opportunities generated vs target
- **Signal Breakdown**: Count by signal type
- **Cumulative Stats**: Total opportunities over time
- **File Attachments**: CSV files with all opportunities
- **Email Drafts**: Personalized Gmail drafts created
- **Next Run Info**: When the next report will be sent

### Gmail Draft Creation:
- **Personalized Emails**: One draft per lead with valid email
- **Signal-Specific Templates**: Customized for each signal type
- **Professional Content**: CEO-level communication
- **Ready for Review**: Drafts saved in Gmail for manual sending
- **Compliance**: GDPR opt-out included

### Email Configuration:
- **Sender**: ariel@cliocircle.com
- **Recipient**: ariel@cliocircle.com
- **SMTP**: Gmail (smtp.gmail.com:587)
- **Gmail API**: For professional draft creation
- **Security**: TLS encryption + OAuth2

## 🛠️ Manual Operations

### Run Single Test
```bash
source venv/bin/activate
python3 outbound.py
```

### Run Weekly Production
```bash
source venv/bin/activate
WEEKLY_RUN=true TARGET_OPPORTUNITIES=50 python3 outbound.py
```

### Test Schedule Timing
```bash
source venv/bin/activate
python3 test_scheduler.py
```

## 📋 Monitoring & Logs

### Log Files
- `weekly_scheduler.log` - Scheduler operations
- `scrape.log` - Lead generation details
- `opportunities_tracking.json` - Performance metrics

### Key Metrics
- **Success Rate**: % of weekly runs completed
- **Target Achievement**: % of weeks hitting 50+ opportunities
- **Email Delivery**: % of reports successfully sent
- **Data Quality**: Average relevance scores

## 🔄 Data Management

### Retention Policy
- **CSV Files**: 90 days
- **Log Files**: 90 days
- **Tracking Data**: 90 days
- **Reports**: Permanent (in email)

### Cleanup Process
- Automatic cleanup of old files
- Weekly data archiving
- Performance data retention

## 🚨 Troubleshooting

### Common Issues

1. **No Opportunities Generated**
   - Check API keys in `.env`
   - Verify internet connection
   - Check proxy configuration

2. **Email Delivery Failed**
   - Verify Gmail app password
   - Check SMTP settings
   - Review email logs

3. **Schedule Not Running**
   - Check timezone configuration
   - Verify scheduler is running
   - Review scheduler logs

### Debug Commands
```bash
# Check scheduler status
tail -f weekly_scheduler.log

# Test individual components
python3 test_scheduler.py

# Manual run with debugging
WEEKLY_RUN=true python3 outbound.py
```

## 📞 Support

For issues or questions:
- Check logs: `weekly_scheduler.log`
- Review configuration: `production_config.json`
- Test components: `test_scheduler.py`

## 🎯 Expected Results

### Weekly Output
- **50+ opportunities** across all signal types
- **High-quality leads** (relevance score ≥0.7)
- **Actionable contacts** with email addresses
- **Personalized email drafts** for outreach
- **Comprehensive trend analysis**

### Business Impact
- **Automated lead generation** for Clio Circle AI
- **Consistent weekly pipeline** of 50+ opportunities
- **Reduced manual effort** in lead research
- **Improved targeting** with AI-powered analysis
- **Scalable system** supporting $36M ARR goal

---

**System Status**: ✅ Ready for Production
**Next Run**: Every Sunday at 8:00 PM Eastern Time
**Target**: 50+ opportunities per week
**Reports**: Automated delivery to ariel@cliocircle.com
