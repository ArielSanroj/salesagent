# HR Tech Lead Generation System

## 🎯 Overview

An advanced B2B lead generation system that automatically identifies and processes HR technology opportunities. The system uses AI/ML for content analysis, web scraping for data collection, and email automation for personalized outreach.

## ✨ Key Features

- **🤖 AI-Powered Analysis**: Uses Ollama LLM for intelligent content extraction and opportunity identification
- **📊 6 Signal Types**: Comprehensive coverage of HR tech opportunities
- **🔄 Automated Workflow**: Weekly scheduling with backup runs
- **📧 Personalized Emails**: Gmail API integration for professional email drafts
- **🛡️ Secure Architecture**: Externalized credentials and secure configuration management
- **⚡ High Performance**: Async scraping, caching, and optimized processing
- **🧪 Comprehensive Testing**: 80%+ test coverage with full mocking
- **📈 Scalable Design**: Modular architecture for easy extension

## 🏗️ Architecture

### Core Components
- **Main Engine** (`outbound.py`) - Central orchestration
- **Scheduler Service** (`weekly_scheduler.py`) - Automated execution
- **Email Service** (`gmail_email_system.py`) - Personalized outreach
- **LLM Service** (`src/llm_service.py`) - AI-powered analysis
- **Search Service** (`src/search_service.py`) - News article retrieval
- **Scraping Service** (`src/scraping_service.py`) - Web content extraction
- **Performance Optimizer** (`src/performance_optimizer.py`) - Async processing and caching

### Signal Types
1. **HR Tech Evaluations** - Companies evaluating HR technology
2. **New Leadership ≤90 days** - Recent HR leadership appointments  
3. **High-Intent Website/Content** - Companies showing HR tech interest
4. **Tech Stack Change** - Companies changing HR systems
5. **Expansion** - Growing companies needing HR solutions
6. **Hiring/Downsizing** - Companies building or restructuring HR teams

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Ollama with llama3.1:8b model
- Gmail API credentials
- Required API keys (see Configuration section)

### Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy environment template: `cp env.example .env`
4. Configure environment variables in `.env` file
5. Set up Gmail API credentials
6. Run the system: `python outbound.py`

### New Architecture Features
- **Modular Design**: Separated into focused service modules
- **Secure Configuration**: All credentials externalized to environment variables
- **Resilient LLM Service**: Graceful fallbacks when LLM is unavailable
- **Async Scraping**: High-performance concurrent web scraping
- **Comprehensive Testing**: 80%+ test coverage with mocking
- **Type Safety**: Full type hints throughout the codebase

## ⚙️ Configuration

### Environment Variables
Create a `.env` file with the following variables:

```bash
# Required Credentials
OLLAMA_API_KEY=your_ollama_api_key_here
EMAIL_PASSWORD=your_gmail_app_password_here
EMAIL_SENDER=ariel@cliocircle.com
EMAIL_RECIPIENT=ariel@cliocircle.com

# Optional API Keys
NEWSDATA_API_KEY=your_newsdata_api_key_here
HUNTER_KEY=your_hunter_api_key_here
SERPAPI_KEY=your_serpapi_key_here
GOOGLE_SHEETS_API_KEY=your_google_sheets_api_key_here

# System Configuration
WEEKLY_RUN=false
TARGET_OPPORTUNITIES=50
DEBUG=false
LOG_LEVEL=INFO
```

### Gmail API Setup
1. Create a Google Cloud Project
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Download `gmail_credentials.json`
5. Place in project root directory

## 🔧 Usage

### Manual Execution
```bash
# Test single signal
python outbound.py

# Weekly run (all signals)
WEEKLY_RUN=true python outbound.py
```

### Automated Scheduling
```bash
# Start weekly scheduler
python weekly_scheduler.py

# Stop scheduler
pkill -f weekly_scheduler.py
```

### Email System
```bash
# Test email system
python gmail_email_system.py
```

## 🧪 Testing

### Run All Tests
```bash
pytest tests/ -v --cov=src --cov-report=html
```

### Run Specific Test Suites
```bash
# Main system tests
pytest tests/test_outbound.py -v

# Scheduler tests
pytest tests/test_weekly_scheduler.py -v

# Service tests
pytest tests/test_llm_service.py -v
pytest tests/test_credentials_manager.py -v
```

### Test Coverage
- **Target**: 80%+ coverage
- **Current**: Comprehensive test suite with mocking
- **Reports**: HTML coverage reports in `htmlcov/`

## 📊 Performance

### Optimizations
- **Async Scraping**: Concurrent URL processing with aiohttp
- **Caching**: Content caching with TTL for improved performance
- **Connection Pooling**: Reuse HTTP connections
- **Batch Processing**: Efficient data processing
- **Rate Limiting**: Respectful API usage

### Metrics
- **Processing Time**: ~15 minutes for 50 opportunities
- **Memory Usage**: Optimized with proper cleanup
- **API Efficiency**: Intelligent rate limiting
- **Error Recovery**: Graceful handling of failures

## 🛡️ Security

### Security Features
- **No Hardcoded Secrets**: All credentials in environment variables
- **Secure Configuration**: YAML-based configuration management
- **Input Validation**: Comprehensive data validation
- **Error Handling**: Secure error messages without sensitive data
- **Dependency Scanning**: Automated vulnerability detection

### Best Practices
- Environment variable validation
- Secure credential storage
- Input sanitization
- Error logging without sensitive data
- Regular dependency updates

## 📈 Monitoring

### Logging
- **Main Logs**: `scrape.log`
- **Email Logs**: `gmail_email_system.log`
- **Scheduler Logs**: `weekly_scheduler.log`

### Performance Tracking
- API call counts
- Processing times
- Success rates
- Error rates
- Memory usage

## 🔄 Workflow

### Weekly Execution Flow
1. **Scheduler Activation** - Sunday 8 PM EST
2. **Service Initialization** - Load configurations and validate credentials
3. **Signal Processing** - Process all 6 signal types
4. **Data Aggregation** - Collect and filter opportunities
5. **Email Generation** - Create personalized email drafts
6. **Performance Tracking** - Update metrics and statistics
7. **Report Generation** - Send weekly performance report

### Data Flow
```
Signal ID → Query Generation → News Search → Content Scraping → 
LLM Analysis → Opportunity Extraction → Quality Filtering → 
Email Generation → Storage → Reporting
```

## 🚀 Deployment

### Local Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit .env with your credentials

# Run system
python outbound.py
```

### Production Considerations
- Secure credential management
- Production configuration
- Error monitoring
- Performance monitoring
- Backup strategies

## 📚 Documentation

### Architecture Documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed system architecture
- [SYSTEM_SUMMARY.md](SYSTEM_SUMMARY.md) - System overview
- [README_SECURE_DEPLOYMENT.md](README_SECURE_DEPLOYMENT.md) - Security guide

### API Documentation
- Gmail API integration
- NewsData.io API usage
- Hunter.io email verification
- Google Sheets integration

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Install development dependencies: `pip install -r requirements.txt[dev]`
4. Run tests: `pytest tests/`
5. Run linters: `black src/ tests/ && flake8 src/ tests/`
6. Submit a pull request

### Code Quality
- **Formatting**: Black code formatting
- **Linting**: Flake8 linting
- **Type Checking**: MyPy type checking
- **Security**: Bandit security scanning
- **Testing**: Comprehensive test coverage

## 📄 License

This project is proprietary software. All rights reserved.

## 🆘 Support

### Troubleshooting
1. Check logs for error messages
2. Verify environment variables
3. Test API connections
4. Validate Gmail API setup

### Common Issues
- **LLM Connection**: Ensure Ollama is running
- **API Limits**: Check API usage and limits
- **Gmail API**: Verify OAuth credentials
- **Environment**: Validate all required variables

## 🔮 Future Enhancements

### Planned Features
- Real-time processing
- Advanced analytics dashboard
- Machine learning integration
- API endpoints for external access
- Microservices architecture
- Container deployment

### Performance Improvements
- Database integration
- Message queue processing
- Horizontal scaling
- Advanced caching strategies
- Machine learning optimization

---

**Built with ❤️ for HR Tech Lead Generation**
