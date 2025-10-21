# Gmail API Setup Instructions

## 🚀 Quick Setup for Gmail API Integration

### 1. Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

### 2. Create Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Desktop application"
4. Download the JSON file
5. Rename it to `gmail_credentials.json` and place in project root

### 3. File Structure
```
outboundai/
├── gmail_credentials.json    # Downloaded from Google Cloud
├── gmail_token.json         # Auto-generated after first run
├── gmail_email_system.py    # Email system
└── outbound.py              # Main script
```

### 4. First Run Authentication
When you first run the system, it will:
1. Open a browser window
2. Ask you to sign in to Gmail
3. Grant permissions for draft creation
4. Save authentication token for future runs

### 5. Permissions Required
- **Gmail Compose**: Create email drafts
- **Gmail Read**: Access draft information

### 6. Security Notes
- `gmail_credentials.json`: Keep secure (contains client secrets)
- `gmail_token.json`: Auto-generated, contains access tokens
- Never commit these files to version control

## 📧 How It Works

### Weekly Automation Flow
1. **Sunday 8 PM**: System runs lead generation
2. **Generates**: 50+ opportunities across 6 signal types
3. **Creates**: Personalized email drafts in Gmail
4. **Sends**: Weekly report to ariel@cliocircle.com

### Email Draft Features
- **Personalized Subject**: Based on signal type and company
- **Customized Opening**: References specific company context
- **Professional Body**: Clio's proven solution details
- **Tailored Closing**: Relevant to signal type
- **Professional Signature**: Ariel, CEO & Founder

### Signal-Specific Templates
1. **HR Tech Evaluations**: Focus on evaluation process
2. **New Leadership**: Emphasize first 90 days
3. **High-Intent Content**: Reference their engagement
4. **Tech Stack Change**: Highlight integration benefits
5. **Expansion**: Focus on scaling challenges
6. **Hiring/Downsizing**: Support team building

## 🔧 Troubleshooting

### Common Issues
1. **"Credentials not found"**: Check `gmail_credentials.json` exists
2. **"Permission denied"**: Re-run authentication process
3. **"No drafts created"**: Check CSV file has valid email addresses
4. **"Rate limit exceeded"**: System includes 1-second delays

### Manual Testing
```bash
# Test Gmail system only
python3 gmail_email_system.py

# Test with specific CSV
python3 -c "
from gmail_email_system import GmailEmailSystem
system = GmailEmailSystem()
system.get_gmail_service()
system.create_weekly_email_drafts('all_signals.csv')
"
```

## 📊 Expected Results

### Weekly Output
- **50+ Opportunities**: High-quality leads
- **Personalized Drafts**: One per valid email
- **Professional Templates**: Signal-specific content
- **Gmail Integration**: Drafts ready for review
- **Weekly Report**: Performance summary

### Draft Quality
- **Subject Lines**: Compelling and relevant
- **Personalization**: Company and person-specific
- **Professional Tone**: CEO-level communication
- **Clear CTA**: 15-30 minute call request
- **Compliance**: GDPR opt-out included

---

**Status**: ✅ Ready for Production
**Next Step**: Set up Gmail credentials and test
**Schedule**: Every Sunday at 8:00 PM Eastern Time