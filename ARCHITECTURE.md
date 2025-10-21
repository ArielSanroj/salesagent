# HR Tech Lead Generation System - Architecture Documentation

## Overview

The HR Tech Lead Generation System is a comprehensive B2B lead generation platform that automatically identifies and processes HR technology opportunities. The system uses AI/ML for content analysis, web scraping for data collection, and email automation for outreach.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HR Tech Lead Generation System               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Scheduler │  │   Main      │  │   Email     │            │
│  │   Service   │  │   Engine    │  │   Service   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│         │                │                │                   │
│         └────────────────┼────────────────┘                   │
│                          │                                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                Core Services Layer                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │  │
│  │  │    LLM      │  │   Search    │  │  Scraping   │    │  │
│  │  │   Service   │  │   Service   │  │   Service   │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │  │
│  │  │Credentials  │  │Performance  │  │   Google    │    │  │
│  │  │  Manager    │  │ Optimizer   │  │   Sheets    │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          │                                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                Data & Storage Layer                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │  │
│  │  │    CSV      │  │   Cache     │  │   Logs      │    │  │
│  │  │   Files     │  │   System    │  │   Files     │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Main Engine (`outbound.py`)
- **Purpose**: Central orchestration of the lead generation process
- **Responsibilities**:
  - Initialize all services
  - Coordinate signal processing
  - Manage workflow execution
  - Handle error recovery

### 2. Scheduler Service (`weekly_scheduler.py`)
- **Purpose**: Automated execution of lead generation tasks
- **Responsibilities**:
  - Schedule weekly runs (Sunday 8 PM EST)
  - Backup runs (Monday/Tuesday)
  - Performance tracking
  - Email reporting

### 3. Email Service (`gmail_email_system.py`)
- **Purpose**: Personalized email draft creation
- **Responsibilities**:
  - Template management
  - Personalization logic
  - Gmail API integration
  - Draft creation and management

## Service Layer

### 1. LLM Service (`src/llm_service.py`)
- **Purpose**: AI-powered content analysis and extraction
- **Features**:
  - Resilient connection handling
  - Retry mechanisms with exponential backoff
  - Fallback responses
  - Background processing with queues

### 2. Search Service (`src/search_service.py`)
- **Purpose**: News article search and retrieval
- **Features**:
  - NewsData.io API integration
  - Rate limiting and retry logic
  - Domain filtering
  - Pagination support

### 3. Scraping Service (`src/scraping_service.py`)
- **Purpose**: Web content extraction
- **Features**:
  - Robots.txt compliance
  - Retry mechanisms
  - HTML text extraction
  - Error handling

### 4. Performance Optimizer (`src/performance_optimizer.py`)
- **Purpose**: Performance enhancements and caching
- **Features**:
  - Async scraping with aiohttp
  - Content caching with TTL
  - Batch processing
  - Connection pooling

### 5. Signal Processor (`src/signal_processor.py`)
- **Purpose**: Signal-specific opportunity processing
- **Features**:
  - Signal type classification
  - Query generation
  - Content analysis
  - Opportunity extraction

### 6. Credentials Manager (`src/credentials_manager.py`)
- **Purpose**: Secure credential and configuration management
- **Features**:
  - Environment variable handling
  - YAML configuration loading
  - API key management
  - Validation and error handling

### 7. Google Sheets Service (`src/google_sheets_service.py`)
- **Purpose**: Google Sheets integration
- **Features**:
  - Lead data storage
  - Status tracking
  - Statistics generation
  - API integration

## Data Models

### Core Models (`src/models.py`)

#### Opportunity
```python
@dataclass
class Opportunity:
    title: str
    company: str
    person: str
    email: str
    url: str
    date: str
    content: str
    relevance_score: float
    signal_type: int
    source: str
```

#### Article
```python
@dataclass
class Article:
    url: str
    title: str
    snippet: str
    source: str
    content: str
    published_at: Optional[str]
    keywords: Optional[List[str]]
```

#### EmailDraft
```python
@dataclass
class EmailDraft:
    to_email: str
    subject: str
    body: str
    company: str
    person: str
    signal_type: int
    draft_id: Optional[str]
```

## Signal Types

The system processes 6 different signal types:

1. **HR Tech Evaluations** - Companies evaluating HR technology
2. **New Leadership ≤90 days** - Recent HR leadership appointments
3. **High-Intent Website/Content** - Companies showing HR tech interest
4. **Tech Stack Change** - Companies changing HR systems
5. **Expansion** - Growing companies needing HR solutions
6. **Hiring/Downsizing** - Companies building or restructuring HR teams

## Data Flow

### 1. Signal Processing Flow
```
Signal ID → Query Generation → News Search → Content Scraping → 
LLM Analysis → Opportunity Extraction → Quality Filtering → 
Email Generation → Storage
```

### 2. Weekly Execution Flow
```
Scheduler → Service Initialization → Signal Processing (1-6) → 
Data Aggregation → Filtering & Deduplication → CSV Export → 
Email Report → Gmail Drafts → Performance Tracking
```

## Configuration Management

### Environment Variables
- `OLLAMA_API_KEY` - LLM service API key
- `EMAIL_PASSWORD` - Gmail SMTP password
- `NEWSDATA_API_KEY` - NewsData.io API key
- `HUNTER_KEY` - Hunter.io API key
- `GOOGLE_SHEETS_API_KEY` - Google Sheets API key

### YAML Configuration
- `config/secure_config.yaml` - Non-sensitive configuration
- `config/email_templates.yaml` - Email templates

## Security Features

### 1. Credential Security
- No hardcoded secrets in code
- Environment variable validation
- Secure credential storage
- Automatic credential validation

### 2. Code Security
- Automated security scanning (Bandit)
- Dependency vulnerability checking (Safety)
- Hardcoded secret detection
- Security best practices enforcement

### 3. Runtime Security
- Graceful error handling
- No sensitive data in logs
- Secure API communication
- Input validation and sanitization

## Performance Optimizations

### 1. Async Processing
- Async scraping with aiohttp
- Concurrent URL processing
- Connection pooling
- Rate limiting

### 2. Caching
- Content caching with TTL
- API response caching
- Template caching
- Performance metrics

### 3. Resource Management
- Memory leak prevention
- Connection reuse
- Batch processing
- Garbage collection

## Error Handling

### 1. Service Failures
- LLM service fallbacks
- API retry mechanisms
- Graceful degradation
- Health monitoring

### 2. Data Validation
- Input sanitization
- Type checking
- Range validation
- Format verification

### 3. Recovery Mechanisms
- Automatic retry with backoff
- Circuit breaker patterns
- Fallback responses
- Error logging

## Monitoring and Logging

### 1. Logging Levels
- **INFO**: Normal operation logs
- **WARNING**: Non-critical issues
- **ERROR**: Errors that don't stop execution
- **CRITICAL**: Fatal errors

### 2. Log Files
- `scrape.log` - Main application logs
- `gmail_email_system.log` - Email system logs
- `weekly_scheduler.log` - Scheduler logs

### 3. Performance Metrics
- API call counts
- Processing times
- Success rates
- Error rates

## Testing Strategy

### 1. Unit Tests
- Individual component testing
- Mock external dependencies
- Edge case coverage
- Error condition testing

### 2. Integration Tests
- End-to-end workflow testing
- API integration testing
- Service interaction testing
- Data flow validation

### 3. Performance Tests
- Load testing
- Memory usage monitoring
- Response time measurement
- Scalability testing

## Deployment Architecture

### 1. Local Development
- Python virtual environment
- Local Ollama instance
- Development configuration
- Debug logging

### 2. Production Deployment
- Secure credential management
- Production configuration
- Error monitoring
- Performance monitoring

### 3. Scalability Considerations
- Horizontal scaling potential
- Database migration path
- Message queue integration
- Container deployment

## Future Enhancements

### 1. Architecture Improvements
- Microservices migration
- Event-driven architecture
- Message queue integration
- Container orchestration

### 2. Feature Enhancements
- Real-time processing
- Advanced analytics
- Machine learning integration
- API endpoints

### 3. Operational Improvements
- Automated deployment
- Health checks
- Metrics collection
- Alerting system

## Dependencies

### Core Dependencies
- `pandas` - Data manipulation
- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing
- `python-dotenv` - Environment variables
- `pyyaml` - YAML configuration

### AI/ML Dependencies
- `langchain-ollama` - LLM integration
- `langchain-core` - LLM core functionality

### External Services
- `serpapi` - Search API
- `pyhunter` - Email verification
- `apify-client` - Web scraping
- `google-api-python-client` - Google services

### Development Dependencies
- `pytest` - Testing framework
- `black` - Code formatting
- `flake8` - Linting
- `mypy` - Type checking
- `bandit` - Security scanning

## Conclusion

The HR Tech Lead Generation System is designed with scalability, maintainability, and security in mind. The modular architecture allows for easy extension and modification, while the comprehensive error handling and monitoring ensure reliable operation in production environments.
