# ToS Monitor

A serverless Terms of Service monitoring service that automatically tracks changes in legal documents, stores snapshots in Cloud Storage, and generates human-readable summaries using LLM analysis.

## Features

- 🔍 **Automatic Document Monitoring**: Fetches and monitors legal documents from configured URLs
- 🤖 **AI-Powered Analysis**: Generates human-readable summaries of document changes using multiple LLM providers
- ☁️ **Dual Storage**: Supports both Google Cloud Storage and local file storage modes
- 🎯 **Intelligent Change Detection**: Multiple hashing strategies to distinguish between cosmetic and substantial changes
- 📊 **RESTful API**: Comprehensive API for document management, version tracking, and analysis
- 🏗️ **Serverless Architecture**: Scales to zero when not in use, cost-effective operation
- 🔄 **Version Management**: Maintains current, last, and previous versions with dated snapshots
- 🔧 **Pluggable AI System**: Supports OpenAI, OpenRouter, Bosch LLM Farm, and easily extensible to other providers

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scheduler     │    │   Cloud Run     │    │ Cloud Storage   │
│  (Cloud Tasks)  │───▶│   (FastAPI)     │───▶│   (Buckets)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────────────────┐
                       │      AI Providers           │
                       │ • OpenAI (GPT-4)            │
                       │ • OpenRouter (Multi-model)  │
                       │ • Bosch LLM Farm (Claude)   │
                       └─────────────────────────────┘
```

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [Development](#development)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Quick Start

**For Bosch Users:** Get started in 5 minutes using Bosch LLM Farm (Claude Sonnet 4.5).

```bash
# 1. Clone and install
git clone https://github.com/your-org/tos-monitor.git
cd tos-monitor
pip install -r requirements.txt

# 2. Configure for Bosch LLM Farm
cat > .env << EOF
AI_PROVIDER=bosch-llm-farm
ANTHROPIC_AUTH_TOKEN=your-bosch-token
BOSCH_LLM_MODEL=claude-sonnet-4-5@20250929
STORAGE_MODE=local
EOF

# 3. Start the service
python -m uvicorn app.main:app --reload --port 8080

# 4. In another terminal, sync and analyze
curl -X POST http://localhost:8080/sync?document_ids=anthropic
curl -X POST http://localhost:8080/tos/anthropic
```

**Result:** AI-powered analysis of document changes in seconds! 🚀

For other providers (OpenAI, OpenRouter), see [Configuration](#configuration).

## Installation

### Prerequisites

- Python 3.11+
- Google Cloud SDK (for cloud deployment)
- Docker (optional, for containerized deployment)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/tos-monitor.git
   cd tos-monitor
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Configure documents**
   ```bash
   # Edit config/documents.json with your target documents
   ```

### Docker Setup

```bash
docker build -t tos-monitor .
docker run -p 8080:8080 --env-file .env tos-monitor
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

#### Required Variables

```bash
# Storage Configuration
STORAGE_MODE=local  # or 'cloud' for Google Cloud Storage
# STORAGE_BUCKET=your-bucket-name  # Required only if STORAGE_MODE=cloud

# AI Provider Configuration (choose one of the three options below)

# Option 1: Bosch LLM Farm (Recommended for Bosch internal use)
AI_PROVIDER=bosch-llm-farm
ANTHROPIC_AUTH_TOKEN=your-bosch-auth-token
BOSCH_LLM_MODEL=claude-sonnet-4-5@20250929

# Option 2: OpenRouter (Access to multiple models via unified API)
# AI_PROVIDER=openrouter
# OPENROUTER_API_KEY=sk-or-v1-your-key
# OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Option 3: OpenAI (Direct OpenAI API access)
# AI_PROVIDER=openai
# OPENAI_API_KEY=sk-your-openai-key
# LLM_MODEL=gpt-4-turbo-preview
```

#### Optional Variables

```bash
# Bosch LLM Farm Configuration (optional overrides)
# Base URL for Bosch LLM Farm endpoint
# Default: https://aoai-farm.bosch-temp.com/api/google/v1
# BOSCH_LLM_BASE_URL=https://aoai-farm.bosch-temp.com/api/google/v1

# Available Bosch models:
# - claude-sonnet-4-5@20250929 (Latest, recommended)
# - claude-haiku-4-5@20251001 (Faster, cheaper)
# - gemini-1.5-pro, gemini-1.5-flash (Google models)

# Google Cloud Configuration (only if STORAGE_MODE=cloud)
GOOGLE_CLOUD_PROJECT=your-project-id

# Server Configuration
PORT=8080
HOST=0.0.0.0
DEBUG=false
LOG_LEVEL=INFO
```

### Document Configuration

Edit `config/documents.json` to define the documents you want to monitor:

```json
{
  "documents": [
    {
      "id": "github_terms",
      "name": "GitHub Terms of Service",
      "url": "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service",
      "selector": "article"
    },
    {
      "id": "openai_usage",
      "name": "OpenAI Usage Policies",
      "url": "https://openai.com/policies/usage-policies"
    }
  ]
}
```

**Configuration Fields:**
- `id`: Unique identifier for the document
- `name`: Human-readable name
- `url`: Target URL to monitor
- `selector` (optional): CSS selector for content extraction

### AI Provider Options

The ToS Monitor supports three AI providers for document analysis:

#### 1. Bosch LLM Farm (Recommended for Bosch Users)

**Description:** Bosch internal LLM service providing access to Anthropic Claude models through a secure internal endpoint.

**Advantages:**
- ✅ Pre-approved for Bosch internal use
- ✅ No external API costs
- ✅ Compliance with Bosch security policies
- ✅ Access to latest Claude models (Sonnet 4.5)
- ✅ High-quality legal document analysis

**Configuration:**
```bash
AI_PROVIDER=bosch-llm-farm
ANTHROPIC_AUTH_TOKEN=your-token-from-bosch-portal
BOSCH_LLM_MODEL=claude-sonnet-4-5@20250929
```

**API Format:** Anthropic Messages API via rawPredict endpoint

**Endpoint:** `https://aoai-farm.bosch-temp.com/api/google/v1/publishers/anthropic/models/{model}:rawPredict`

#### 2. OpenRouter

**Description:** Unified API gateway providing access to multiple LLM providers (Anthropic, OpenAI, Google, Meta, etc.).

**Advantages:**
- ✅ Access to 100+ models from different providers
- ✅ Flexible pricing and model selection
- ✅ Single API key for all models
- ✅ Good for experimentation and comparison

**Configuration:**
```bash
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

**Popular Models:**
- `anthropic/claude-3.5-sonnet` - Best for legal analysis
- `openai/gpt-4-turbo` - Strong general purpose
- `meta-llama/llama-3.1-70b-instruct` - Open source option

#### 3. OpenAI

**Description:** Direct access to OpenAI's GPT models.

**Advantages:**
- ✅ Direct API access (no intermediary)
- ✅ Latest GPT models
- ✅ Well-documented and stable

**Configuration:**
```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key
LLM_MODEL=gpt-4-turbo-preview
```

**Popular Models:**
- `gpt-4-turbo-preview` - Most capable
- `gpt-4` - Stable, reliable
- `gpt-3.5-turbo` - Fast and economical

#### Provider Comparison

| Feature | Bosch LLM Farm | OpenRouter | OpenAI |
|---------|----------------|------------|--------|
| **Best For** | Bosch employees | Flexibility | Direct GPT access |
| **Cost** | Internal (free) | Pay-per-use | Pay-per-use |
| **Models** | Claude, Gemini | 100+ models | GPT models only |
| **Compliance** | Bosch-approved | External service | External service |
| **Setup** | Bosch credentials | API key | API key |

### Authentication Setup

#### For Google Cloud Deployment

```bash
# Install Google Cloud SDK
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
```

#### For Local Development

```bash
gcloud auth application-default login
```

## Usage

### Starting the Server

#### Local Development
```bash
python -m uvicorn app.main:app --reload --port 8080
```

#### Production
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Basic Operations

#### 1. Sync Documents
Download and process all configured documents:
```bash
curl -X POST http://localhost:8080/sync
```

Sync specific documents:
```bash
curl -X POST "http://localhost:8080/sync?document_ids=github_terms,openai_usage"
```

Force update (ignore cache):
```bash
curl -X POST "http://localhost:8080/sync?force=true"
```

#### 2. List Documents
```bash
curl http://localhost:8080/tos
```

#### 3. Get Document Details
```bash
curl http://localhost:8080/tos/github_terms
```

#### 4. Analyze Changes
Generate AI-powered change analysis:
```bash
# Basic analysis (compares 'last' vs 'prev' versions)
curl -X POST http://localhost:8080/tos/github_terms \
  -H "Content-Type: application/json" \
  -d '{}'

# Analysis with specific dates
curl -X POST http://localhost:8080/tos/github_terms \
  -H "Content-Type: application/json" \
  -d '{
    "prev": "2024-01-15",
    "last": "2024-02-28"
  }'

# Analysis with specific AI provider
curl -X POST http://localhost:8080/tos/github_terms \
  -H "Content-Type: application/json" \
  -d '{
    "ai_provider": "openrouter"
  }'
```

#### 5. Access Previous Versions
```bash
# Get last version
curl http://localhost:8080/tos/github_terms/last

# Get previous version
curl http://localhost:8080/tos/github_terms/prev

# Get specific date version
curl http://localhost:8080/tos/github_terms/2024-01-15
```

## API Documentation

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service information |
| `GET` | `/health` | Health check with connectivity validation |
| `GET` | `/config` | Current configuration |
| `GET` | `/docs` | Swagger/OpenAPI documentation |

### Document Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sync` | Download and process documents |
| `GET` | `/tos` | List all documents with versions |
| `GET` | `/tos/{id}` | Get document details |
| `GET` | `/tos/{id}/prev` | Get previous version content |
| `GET` | `/tos/{id}/last` | Get last version content |
| `GET` | `/tos/{id}/{date}` | Get specific dated version |
| `POST` | `/tos/{id}` | AI-powered change analysis |

### Query Parameters

#### `/sync` endpoint
- `document_ids`: Comma-separated list of document IDs
- `force`: Boolean to ignore cache and force update

#### AI Analysis (`POST /tos/{id}`)
- **Request Body**: Optional JSON with `ai_provider`, `prev`, and `last` parameters
- **Default Behavior**: Compares `last` version with `prev` version
- **Response**: Plain text analysis (not JSON)
- **Customizable**: Can specify exact dates or different AI provider per request

#### Request Body for AI Analysis
```json
{
  "ai_provider": "openrouter",  // Optional: "openai" or "openrouter"
  "prev": "2024-01-15",        // Optional: specific date or "prev"
  "last": "2024-02-28"         // Optional: specific date or "last"
}
```

### Response Formats

#### Document List Response
```json
{
  "github_terms": {
    "id": "github_terms",
    "name": "GitHub Terms of Service",
    "url": "https://docs.github.com/en/site-policy/...",
    "current": "2024-03-15",
    "last": "2024-02-28",
    "prev": "2024-01-30",
    "changed": true,
    "total": 5,
    "available_dates": ["2024-03-15", "2024-02-28", "2024-01-30", "2024-01-20", "2024-01-10"]
  }
}
```

#### AI Analysis Response
Returns **plain text** analysis (not JSON):
```
Analysis of changes between GitHub Terms of Service versions:

SUMMARY:
The Terms of Service were updated to clarify data processing procedures and user responsibilities...

KEY CHANGES:
1. Data Processing Section:
   - Added new clause about third-party data sharing
   - Modified retention period from 30 to 90 days

2. User Responsibilities:
   - Enhanced content moderation guidelines
   - New restrictions on automated access

IMPACT ASSESSMENT:
These changes primarily affect enterprise users who process user data...

RECOMMENDATIONS:
Users should review the new data processing terms and update their internal policies accordingly.
```

## Deployment

### Google Cloud Run Deployment

#### Automated Deployment

The project includes comprehensive deployment automation:

```bash
# Full deployment with build
./deploy.sh

# Test deployment (dry run)
./deploy.sh --dry-run

# Deploy without rebuilding
./deploy.sh --skip-build

# Deploy with local build
./deploy.sh --local-build
```

#### Manual Deployment

```bash
# Build and submit to Cloud Build
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/tos-monitor

# Deploy to Cloud Run
gcloud run deploy tos-monitor \
    --image gcr.io/$GOOGLE_CLOUD_PROJECT/tos-monitor \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

#### Environment Variables for Cloud Run

Set environment variables in Cloud Run:

```bash
gcloud run services update tos-monitor \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,STORAGE_BUCKET=$BUCKET_NAME,AI_PROVIDER=openrouter" \
    --set-secrets="OPENROUTER_API_KEY=openrouter-key:latest"
```

### Storage Setup

#### Initialize Cloud Storage

Upload existing data to Google Cloud Storage:

```bash
python upload_to_gcs.py --bucket your-bucket-name

# Dry run to test
python upload_to_gcs.py --bucket your-bucket-name --dry-run
```

#### Local Storage Mode

For development or testing, use local storage:

```bash
export STORAGE_MODE=local
# Data will be stored in ./data/ directory
```

## Development

### Project Structure

```
tos-monitor/
├── app/                    # Main application
│   ├── main.py            # FastAPI application entry point
│   ├── storage.py         # Storage abstraction layer
│   ├── tos_client.py      # ToS analysis orchestrator
│   ├── llm_client.py      # LLM client manager
│   ├── routes/            # API endpoint definitions
│   │   ├── fetch_docs.py  # Document fetching endpoints
│   │   └── tos.py         # ToS management endpoints
│   ├── clients/           # AI client implementations
│   │   ├── base.py        # AI client protocol
│   │   ├── openai_client.py
│   │   └── openrouter_client.py
│   └── utils/             # Utility modules
│       ├── html_parser.py # Web scraping
│       ├── normalizer.py  # Text processing
│       └── hashing.py     # Change detection
├── config/                # Configuration files
│   └── documents.json     # Document definitions
├── data/                  # Local storage (when using local mode)
├── .env                   # Environment variables (not in git)
├── .env.example           # Environment template
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
├── deploy.sh             # Deployment wrapper
├── deploy_to_cloudrun.py # Cloud Run deployment automation
└── upload_to_gcs.py      # GCS upload utility
```

### Adding New AI Providers

1. **Create client implementation**
   ```python
   # app/clients/new_provider.py
   from .base import AIClient

   class NewProviderClient(AIClient):
       async def generate_analysis(self, prompt: str) -> str:
           # Implementation
           pass
   ```

2. **Register in LLM client manager**
   ```python
   # app/llm_client.py
   def get_client(provider: str) -> AIClient:
       if provider == "new_provider":
           return NewProviderClient()
   ```

3. **Add configuration**
   ```bash
   # .env
   AI_PROVIDER=new_provider
   NEW_PROVIDER_API_KEY=your-key
   ```

**Example Implementation:**
See `app/clients/bosch_llm_farm_client.py` for a complete Anthropic API-based implementation with Bearer token authentication using the rawPredict endpoint pattern.

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Code Quality

```bash
# Format code
black app/
isort app/

# Lint code
flake8 app/
mypy app/
```

## Examples

### Example 1: Using Bosch LLM Farm (Claude Sonnet 4.5)

```bash
# Set up environment
export AI_PROVIDER=bosch-llm-farm
export ANTHROPIC_AUTH_TOKEN=your-token
export BOSCH_LLM_MODEL=claude-sonnet-4-5@20250929
export STORAGE_MODE=local

# Configure document
cat > config/documents.json << EOF
{
  "documents": [
    {
      "id": "github_tos",
      "name": "GitHub Terms of Service",
      "url": "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service",
      "selector": "article"
    }
  ]
}
EOF

# Start the service
python -m uvicorn app.main:app --reload --port 8080

# In another terminal:
# Sync the document
curl -X POST http://localhost:8080/sync

# Analyze changes with Bosch LLM Farm
curl -X POST http://localhost:8080/tos/github_tos \
  -H "Content-Type: application/json" \
  -d '{"ai_provider": "bosch-llm-farm"}'

# Get HTML formatted output
curl -X POST "http://localhost:8080/tos/github_tos?html=true" \
  -H "Content-Type: application/json" \
  -d '{"ai_provider": "bosch-llm-farm"}'
```

### Example 2: Comparing AI Providers

```bash
# Analyze with different providers to compare results

# Using Bosch LLM Farm (Claude)
curl -X POST http://localhost:8080/tos/github_tos \
  -H "Content-Type: application/json" \
  -d '{"ai_provider": "bosch-llm-farm"}'

# Using OpenRouter (also Claude)
curl -X POST http://localhost:8080/tos/github_tos \
  -H "Content-Type: application/json" \
  -d '{
    "ai_provider": "openrouter"
  }'

# Using OpenAI (GPT-4)
curl -X POST http://localhost:8080/tos/github_tos \
  -H "Content-Type: application/json" \
  -d '{"ai_provider": "openai"}'
```

### Example 3: Batch Processing Multiple Documents

```bash
# Configure multiple documents
cat > config/documents.json << EOF
{
  "documents": [
    {
      "id": "github_tos",
      "name": "GitHub Terms of Service",
      "url": "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service"
    },
    {
      "id": "openai_usage",
      "name": "OpenAI Usage Policies",
      "url": "https://openai.com/policies/usage-policies"
    }
  ]
}
EOF

# Sync all documents
curl -X POST http://localhost:8080/sync

# Get overview of all documents
curl http://localhost:8080/tos
```

### Example 4: Automated Monitoring with Cron

```bash
# Add to crontab for daily monitoring
0 9 * * * curl -X POST http://your-app.run.app/sync
```

### Example 5: Integration with External Systems

```python
import requests

class ToSMonitor:
    def __init__(self, base_url):
        self.base_url = base_url

    def sync_all(self):
        response = requests.post(f"{self.base_url}/sync")
        return response.json()

    def analyze_document(self, doc_id):
        response = requests.post(f"{self.base_url}/tos/{doc_id}")
        return response.json()

    def get_changes(self, doc_id):
        analysis = self.analyze_document(doc_id)
        return analysis.get("changes_detected", False)

# Usage
monitor = ToSMonitor("https://your-app.run.app")
monitor.sync_all()

if monitor.get_changes("github_tos"):
    print("GitHub ToS has changed!")
```

## Troubleshooting

### Common Issues

#### 1. Authentication Errors

```bash
# Check Google Cloud authentication
gcloud auth list
gcloud auth application-default print-access-token

# Re-authenticate if needed
gcloud auth application-default login
```

#### 2. Storage Permission Issues

```bash
# Check bucket permissions
gsutil ls gs://your-bucket-name
gsutil iam get gs://your-bucket-name

# Grant storage access to Cloud Run service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/storage.objectAdmin"
```

#### 3. Document Fetching Failures

Check the logs for specific errors:

```bash
# Local development
tail -f logs/app.log

# Cloud Run
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=tos-monitor"
```

Common causes:
- **Network restrictions**: Target site blocking requests
- **Content selector issues**: CSS selector not matching content
- **Rate limiting**: Too frequent requests to target site

#### 4. AI Provider Issues

```bash
# Test AI provider connectivity
curl -X POST http://localhost:8080/health
```

Check for:
- **API key validity**: Ensure keys are correctly set and not expired
- **Model availability**: Verify the specified model is available
- **Rate limits**: Check if you've hit provider rate limits

#### 5. Bosch LLM Farm Specific Issues

**Authentication Failed (401/403):**
```bash
# Verify your token
echo $ANTHROPIC_AUTH_TOKEN

# Test connection manually
curl -X POST "https://aoai-farm.bosch-temp.com/api/google/v1/publishers/anthropic/models/claude-sonnet-4-5@20250929:rawPredict" \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"anthropic_version":"vertex-2023-10-16","messages":[{"role":"user","content":"Hello!"}],"max_tokens": 10}'
```

**Model Not Found (404):**
- Verify the model name is correct: `claude-sonnet-4-5@20250929`
- Check available models in Bosch LLM Farm portal
- Ensure the model version suffix is included (e.g., `@20250929`)

**Common Bosch LLM Farm Models:**
```bash
# Claude models (recommended for legal analysis)
BOSCH_LLM_MODEL=claude-sonnet-4-5@20250929  # Latest Sonnet
BOSCH_LLM_MODEL=claude-haiku-4-5@20251001   # Faster, cheaper

# Gemini models (also available)
BOSCH_LLM_MODEL=gemini-1.5-pro
BOSCH_LLM_MODEL=gemini-1.5-flash
```

**Endpoint Issues:**
- Default endpoint: `https://aoai-farm.bosch-temp.com/api/google/v1`
- Can be overridden with `BOSCH_LLM_BASE_URL` environment variable
- Ensure you're on Bosch network or VPN

### Debug Mode

Enable debug mode for verbose logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
```

### Health Checks

The `/health` endpoint provides comprehensive health information:

```json
{
  "status": "healthy",
  "timestamp": "2024-03-15T10:30:00Z",
  "checks": {
    "storage": "healthy",
    "ai_provider": "healthy",
    "configuration": "healthy"
  },
  "version": "1.0.0"
}
```

## Contributing

We welcome contributions! Please follow these guidelines:

### Development Setup

1. **Fork the repository**
2. **Clone your fork**
   ```bash
   git clone https://github.com/your-username/tos-monitor.git
   ```
3. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Install development dependencies**
   ```bash
   pip install -r requirements.txt
   pip install black isort flake8 mypy pytest
   ```

### Code Standards

- **Format code** with `black` and `isort`
- **Follow PEP 8** style guidelines
- **Add type hints** for all functions
- **Write tests** for new functionality
- **Update documentation** for API changes

### Submitting Changes

1. **Run tests**
   ```bash
   pytest
   ```
2. **Format code**
   ```bash
   black app/
   isort app/
   ```
3. **Commit changes**
   ```bash
   git commit -m "feat: add new feature description"
   ```
4. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Create a Pull Request**

### Reporting Issues

Please use the GitHub issue tracker to report bugs or request features. Include:

- **Clear description** of the issue
- **Steps to reproduce** (for bugs)
- **Expected vs actual behavior**
- **Environment details** (Python version, OS, etc.)
- **Relevant logs** or error messages

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

For support and questions:

- **Documentation**: Check the `/docs` endpoint when running the service
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for general questions

Built with ❤️ using FastAPI, Google Cloud, and AI technologies.
