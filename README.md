# MarkItLikeItsHot - FastAPI Service for MarkItDown

[![Tests](https://github.com/matthewdeaves/markitlikeitshot/actions/workflows/tests.yml/badge.svg)](https://github.com/matthewdeaves/markitlikeitshot/actions/workflows/tests.yml)

A FastAPI service wrapping Microsoft's [markitdown](https://github.com/microsoft/markitdown) library. This service provides a robust API for converting various file formats and web content to clean, formatted Markdown with enterprise-grade features.

## Features

### Core Functionality
- Convert multiple file formats to Markdown (PDF, DOCX, PPTX, HTML, etc.)
- Process direct text/HTML input
- Convert web pages with special Wikipedia handling
- Clean and standardize Markdown output

### Authentication Features
- API Key Authentication
- Rate Limiting
- Audit Logging
- Health Monitoring
- Comprehensive Error Handling
- CORS Support

### Management Features
- Interactive CLI for user and API key management
- Database initialization and maintenance tools
- System health checks and diagnostics
- Log rotation and cleanup

## Quick Start

### Development Environment
```bash
# Start development environment with hot reload
./run.sh dev
```

### Production Environment
```bash
# Start production environment
./run.sh prod
```

### Test Environment
```bash
# Run test suite
./run.sh test
```

## API Endpoints

### Authentication
All endpoints require an API key (when enabled):
```bash
-H "X-API-Key: your-api-key"
```

### Convert File
```bash
curl -X POST "http://localhost:8000/api/v1/convert/file" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@path/to/document.docx"
```

### Convert HTML Text
```bash
curl -X POST "http://localhost:8000/api/v1/convert/text" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"content": "<h1>Hello World</h1><p>This is a test</p>"}'
```

### Convert URL
```bash
curl -X POST "http://localhost:8000/api/v1/convert/url" \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}'
```

### Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

## Security Configuration

### API Key Authentication

#### Disabling API Key Authentication
API key authentication can be disabled for development or testing purposes:

1. Environment Variable Method:
```bash
export API_KEY_AUTH_ENABLED=false
./run.sh dev
```

2. Docker Compose Method:
Add to your service in docker-compose.yml:
```yaml
environment:
  - API_KEY_AUTH_ENABLED=false
```

3. .env File Method:
Create or modify .env in the project root:
```
API_KEY_AUTH_ENABLED=false
```

### Rate Limiting

Rate limiting remains active even when API key authentication is disabled. To modify:

```yaml
environment:
  - RATE_LIMIT_REQUESTS=100
  - RATE_LIMIT_PERIOD=minute
```

### CORS Configuration

When API key authentication is disabled, you may want to restrict CORS:

```yaml
environment:
  - ALLOWED_ORIGINS=["http://localhost:3000"]
  - ALLOWED_METHODS=["GET", "POST"]
  - ALLOWED_HEADERS=["*"]
```

### Audit Logging

Audit logging tracks all API operations regardless of authentication status:

```yaml
environment:
  - AUDIT_LOG_ENABLED=true
  - AUDIT_LOG_RETENTION_DAYS=90
```

### Example Development Configuration

Complete example for local development:

```yaml
services:
  markitdown-dev:
    environment:
      - ENVIRONMENT=development
      - API_KEY_AUTH_ENABLED=false
      - LOG_LEVEL=DEBUG
      - RATE_LIMIT_REQUESTS=1000
      - RATE_LIMIT_PERIOD=hour
      - ALLOWED_ORIGINS=["*"]
      - AUDIT_LOG_ENABLED=true
      - DATABASE_URL=sqlite:///./data/dev_api_keys.db
```

### Verifying Configuration

Check current security settings:

```bash
# Using the CLI
./run.sh -i dev
# Select "Show Version Info" from the menu

# Or using curl
curl http://localhost:8000/health
```

The health endpoint response includes authentication status:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "auth_enabled": false,
  "database": "connected",
  "rate_limit": {
    "requests": 1000,
    "period": "hour"
  }
}
```

## Management CLI

### Interactive Mode
The easiest way to access the interactive CLI is:
```bash
# Launch interactive CLI for development environment
./run.sh -i dev

# Or for production
./run.sh -i prod
```

### Alternative Method (Direct Docker Access)
If needed, you can still access the CLI directly via Docker:
```bash
sudo docker exec -it markitlikeitshot-markitdown-dev-1 python manage.py interactive
```

### User Management
```bash
# Create new user
python manage.py users create --name "John Doe" --email "john@example.com"

# List users
python manage.py users list

# View user details
python manage.py users info 1
```

### API Key Management
```bash
# Create API key
python manage.py apikeys create --name "Test Key" --user-id 1

# List API keys
python manage.py apikeys list

# Deactivate API key
python manage.py apikeys deactivate 1
```

### System Management
```bash
# Initialize database
python manage.py init

# Check system health
python manage.py check

# Clean old logs
python manage.py clean
```

## Configuration

### Environment Variables
- `ENVIRONMENT`: development/production/test
- `API_KEY_AUTH_ENABLED`: Enable/disable API key authentication
- `LOG_LEVEL`: DEBUG/INFO/WARNING/ERROR/CRITICAL
- `RATE_LIMIT_REQUESTS`: Number of requests allowed per period
- `RATE_LIMIT_PERIOD`: Time period for rate limiting

### Supported File Types
- Documents: .pdf, .docx, .pptx, .xlsx
- Audio: .wav, .mp3
- Images: .jpg, .jpeg, .png
- Web: .html, .htm
- Data: .txt, .csv, .json, .xml

## Project Structure
```
markitlikeitshot
├── ai_dump.sh
├── docker-compose.yml
├── markitdown-service
│   ├── app
│   │   ├── api
│   │   │   └── v1
│   │   │       └── endpoints
│   │   │           └── conversion.py
│   │   ├── cli
│   │   │   ├── commands
│   │   │   │   ├── api_key.py
│   │   │   │   └── user.py
│   │   │   ├── interactive.py
│   │   │   └── manage.py
│   │   ├── core
│   │   │   ├── audit
│   │   │   │   ├── actions.py
│   │   │   │   ├── audit.py
│   │   │   │   └── __init__.py
│   │   │   ├── config
│   │   │   │   ├── __init__.py
│   │   │   │   └── settings.py
│   │   │   ├── errors
│   │   │   │   ├── base.py
│   │   │   │   ├── exceptions.py
│   │   │   │   ├── handlers.py
│   │   │   │   └── __init__.py
│   │   │   ├── __init__.py
│   │   │   ├── logging
│   │   │   │   ├── config.py
│   │   │   │   ├── formatters.py
│   │   │   │   └── __init__.py
│   │   │   ├── rate_limiting
│   │   │   │   ├── __init__.py
│   │   │   │   └── limiter.py
│   │   │   ├── security
│   │   │   │   ├── api_key.py
│   │   │   │   └── user.py
│   │   │   └── validation
│   │   │       ├── __init__.py
│   │   │       └── validators.py
│   │   ├── db
│   │   │   ├── init_db.py
│   │   │   ├── __init__.py
│   │   │   └── session.py
│   │   ├── main.py
│   │   └── models
│   │       ├── auth
│   │       │   ├── api_key.py
│   │       │   └── user.py
│   │       └── __init__.py
│   ├── Dockerfile
│   ├── logs
│   │   ├── app_development.log
│   │   ├── audit_development.log
│   │   ├── audit_test.log
│   │   ├── cli_development.log
│   │   └── sql_development.log
│   ├── manage.py
│   ├── pytest.ini
│   ├── requirements.txt
│   └── tests
│       ├── api
│       ├── conftest.py
│       ├── fixtures
│       ├── test_endpoints.py
│       └── test_files
│           └── TestDoc.docx
├── README.md
└── run.sh
```