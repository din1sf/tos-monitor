# ToS Monitor

A serverless Terms of Service monitoring service that automatically tracks changes in legal documents, stores snapshots in Cloud Storage, and generates human-readable summaries using LLM analysis.

## Features

- 🔍 **Automatic Document Monitoring**: Fetches and monitors legal documents from configured URLs
- 🖥️ **Web UI**: Browser-friendly interface for document management and analysis
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
│    Web UI       │    │   FastAPI App   │    │ Cloud Storage   │
│  (Dashboard)    │───▶│  (REST API)     │───▶│  or Local FS    │
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

**Sync Triggering:** Document syncing is triggered manually via the Web UI or API. For automated scheduling, integrate with external cron or Cloud Scheduler to call `POST /sync` on a schedule.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Web UI](#web-ui)
  - [API](#api)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
  - [Cloud Run Deployment](#cloud-run-deployment)
  - [GCS Upload](#gcs-upload)
- [Testing](#testing)
- [Development](#development)
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

# 4. Open the web UI
open http://localhost:8080/ui

# Or use the API
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
   # Or use the web UI to add documents
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

Documents can be configured in two ways:

#### 1. Via Web UI (Recommended)
- Start the application
- Navigate to `http://localhost:8080/ui`
- Click "Add Document" to add new documents
- Use "Edit" and "Remove" from the three-dot menu for each document

#### 2. Via JSON file
Edit `config/documents.json`:

```json
{
  "documents": [
    {
      "id": "github_terms",
      "name": "GitHub Terms of Service",
      "url": "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service",
      "selector": "article"
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

The ToS Monitor supports three AI providers:

#### 1. Bosch LLM Farm (Recommended for Bosch Users)

**Advantages:**
- ✅ Pre-approved for Bosch internal use
- ✅ No external API costs
- ✅ Compliance with Bosch security policies
- ✅ Access to latest Claude models (Sonnet 4.5)

**Configuration:**
```bash
AI_PROVIDER=bosch-llm-farm
ANTHROPIC_AUTH_TOKEN=your-token-from-bosch-portal
BOSCH_LLM_MODEL=claude-sonnet-4-5@20250929
```

#### 2. OpenRouter

**Advantages:**
- ✅ Access to 100+ models from different providers
- ✅ Flexible pricing and model selection

**Configuration:**
```bash
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

#### 3. OpenAI

**Advantages:**
- ✅ Direct API access
- ✅ Latest GPT models

**Configuration:**
```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key
LLM_MODEL=gpt-4-turbo-preview
```

## Usage

### Starting the Server

```bash
# Local Development
python -m uvicorn app.main:app --reload --port 8080

# Production
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Web UI

Open `http://localhost:8080/ui` in your browser to access the web interface:

**Dashboard** (`/ui`)
- View all monitored documents
- See change status and version counts
- Add, edit, or remove documents
- Trigger sync for all or individual documents

**Document Detail** (`/ui/doc/{id}`)
- View version timeline
- Browse document content by version
- Run AI analysis to compare versions
- Download analysis as HTML

### API

#### Basic Operations

**1. Sync Documents**
```bash
# Sync all documents
curl -X POST http://localhost:8080/sync

# Sync specific documents
curl -X POST "http://localhost:8080/sync" \
  -H "Content-Type: application/json" \
  -d '{"document_ids": ["github_terms"]}'
```

**2. List Documents**
```bash
curl http://localhost:8080/tos
```

**3. Analyze Changes**
```bash
# Basic analysis
curl -X POST http://localhost:8080/tos/github_terms \
  -H "Content-Type: application/json" \
  -d '{}'

# With specific versions
curl -X POST http://localhost:8080/tos/github_terms \
  -H "Content-Type: application/json" \
  -d '{"prev": "2024-01-15", "last": "2024-02-28"}'

# Get HTML output
curl -X POST "http://localhost:8080/tos/github_terms?html=true" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**4. Manage Documents**
```bash
# Add a document
curl -X POST http://localhost:8080/config/documents \
  -H "Content-Type: application/json" \
  -d '{
    "id": "new_doc",
    "name": "New Document",
    "url": "https://example.com/terms",
    "selector": "main"
  }'

# Update a document
curl -X PUT http://localhost:8080/config/documents/new_doc \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'

# Delete a document
curl -X DELETE http://localhost:8080/config/documents/new_doc
```

**5. Automated Scheduling (Optional)**

Document syncing is manual by default. To automate it, use cron or Cloud Scheduler:

```bash
# Linux/macOS cron - sync daily at 9am
# Add to crontab (crontab -e)
0 9 * * * curl -X POST http://localhost:8080/sync

# Google Cloud Scheduler
gcloud scheduler jobs create http tos-monitor-sync \
  --schedule="0 9 * * *" \
  --uri="https://your-app.run.app/sync" \
  --http-method=POST \
  --location=us-central1
```

## API Documentation

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service information |
| `GET` | `/health` | Health check |
| `GET` | `/config` | Current configuration |
| `GET` | `/docs` | Swagger/OpenAPI docs |

### Web UI

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/ui` | Dashboard |
| `GET` | `/ui/doc/{id}` | Document detail page |

### Document Management (API)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/sync` | Download and process documents |
| `GET` | `/tos` | List all documents |
| `GET` | `/tos/{id}` | Get document details |
| `GET` | `/tos/{id}/prev` | Previous version content |
| `GET` | `/tos/{id}/last` | Last version content |
| `GET` | `/tos/{id}/{date}` | Specific dated version |
| `POST` | `/tos/{id}` | AI-powered analysis |

### Document Configuration (API)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/config/documents` | Add new document |
| `PUT` | `/config/documents/{id}` | Update document |
| `DELETE` | `/config/documents/{id}` | Remove document |

## Deployment

### Cloud Run Deployment

The project includes an interactive menu-driven deployment script:

**Interactive Deployment:**
```bash
# Make sure you're authenticated
gcloud auth login
gcloud config set project your-project-id

# Run interactive deployment
./deploy.sh
```

This will guide you through:
1. Select environment file (defaults to `.env.cloud`)
2. Choose deployment mode (full/skip-build/dry-run)
3. Select build method (Cloud Build or local Docker)
4. Review and confirm

**Non-Interactive Mode (for CI/automation):**
```bash
# Deploy with specific env file
./deploy.sh --env .env.cloud --skip-menu

# Dry run with custom env
./deploy.sh --env .env.production --skip-menu --dry-run

# Deploy without rebuilding
./deploy.sh --env .env.cloud --skip-menu --skip-build

# Local Docker build
./deploy.sh --env .env.cloud --skip-menu --local-build
```

**Manual Deployment:**
```bash
# Build and push image
gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/tos-monitor

# Deploy to Cloud Run
gcloud run deploy tos-monitor \
    --image gcr.io/$GOOGLE_CLOUD_PROJECT/tos-monitor \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

**Set Environment Variables:**
```bash
gcloud run services update tos-monitor \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,STORAGE_BUCKET=$BUCKET_NAME,AI_PROVIDER=openrouter" \
    --set-secrets="OPENROUTER_API_KEY=openrouter-key:latest"
```

### GCS Upload

Upload local data to Google Cloud Storage:

```bash
# Install dependencies
pip install google-cloud-storage

# Authenticate
gcloud auth application-default login

# Dry run (preview)
python upload_to_gcs.py --bucket tos-monitor --dry-run

# Upload
python upload_to_gcs.py --bucket tos-monitor

# Custom data directory
python upload_to_gcs.py --bucket tos-monitor --data-dir /path/to/data
```

## Testing

### Quick Test (All-in-One)

```bash
#!/bin/bash
# Test Bosch LLM Farm integration

echo "🧪 Testing ToS Monitor with Bosch LLM Farm"

# Test 1: Environment
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
assert os.getenv('AI_PROVIDER') == 'bosch-llm-farm'
print('✅ Environment OK')
"

# Test 2: Client Init
python3 -c "
from app.llm_client import get_llm_client
client = get_llm_client('bosch-llm-farm')
assert client.provider == 'bosch-llm-farm'
print('✅ Client initialization OK')
"

# Test 3: Connection
python3 -c "
from app.llm_client import get_llm_client
import asyncio
async def test():
    client = get_llm_client('bosch-llm-farm')
    result = await client.test_connection()
    assert result, 'Connection failed'
    print('✅ API connection OK')
asyncio.run(test())
"

echo "🎉 All tests passed!"
```

### Step-by-Step Testing

**1. Test Environment:**
```bash
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'AI_PROVIDER: {os.getenv(\"AI_PROVIDER\")}')
print(f'Model: {os.getenv(\"BOSCH_LLM_MODEL\")}')
"
```

**2. Test Client Initialization:**
```bash
python3 -c "
from app.llm_client import get_llm_client
client = get_llm_client('bosch-llm-farm')
print(f'Client: {client.__class__.__name__}')
print(f'Model: {client.model}')
"
```

**3. Test Connection:**
```bash
python3 -c "
from app.llm_client import get_llm_client
import asyncio
async def test():
    client = get_llm_client('bosch-llm-farm')
    result = await client.test_connection()
    print('✅ Connection successful' if result else '❌ Connection failed')
asyncio.run(test())
"
```

**4. Test Full Application:**
```bash
# Start server
python3 -m uvicorn app.main:app --reload --port 8080

# In another terminal:
# Test health
curl http://localhost:8080/health | jq

# Test sync
curl -X POST "http://localhost:8080/sync?document_ids=anthropic"

# Test analysis
curl -X POST http://localhost:8080/tos/anthropic \
  -H "Content-Type: application/json" \
  -d '{"ai_provider": "bosch-llm-farm"}'
```

## Development

### Project Structure

```
tos-monitor/
├── app/
│   ├── main.py              # FastAPI application
│   ├── storage.py           # Storage abstraction
│   ├── tos_client.py        # Analysis orchestrator
│   ├── llm_client.py        # LLM client manager
│   ├── routes/              # API endpoints
│   │   ├── fetch_docs.py    # Document fetching
│   │   ├── tos.py           # ToS management
│   │   ├── config.py        # Document configuration
│   │   └── ui.py            # Web UI routes
│   ├── clients/             # AI implementations
│   │   ├── base.py
│   │   ├── openai_client.py
│   │   ├── openrouter_client.py
│   │   └── bosch_llm_farm_client.py
│   ├── templates/           # Jinja2 templates
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   └── document.html
│   └── utils/               # Utilities
│       ├── html_parser.py
│       ├── normalizer.py
│       ├── hashing.py
│       └── html_formatter.py
├── config/
│   └── documents.json       # Document definitions
├── data/                    # Local storage
├── .env                     # Environment variables
├── .env.cloud               # Cloud deployment config
├── requirements.txt
├── Dockerfile
├── deploy.sh                # Interactive deployment script
└── upload_to_gcs.py
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

## Troubleshooting

### Common Issues

#### Authentication Errors

```bash
# Check Google Cloud authentication
gcloud auth list
gcloud auth application-default login
```

#### Storage Permission Issues

```bash
# Check bucket access
gsutil ls gs://your-bucket-name

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/storage.objectAdmin"
```

#### Bosch LLM Farm Issues

**Authentication Failed (401/403):**
```bash
# Verify token
echo $ANTHROPIC_AUTH_TOKEN

# Test manually
curl -X POST "https://aoai-farm.bosch-temp.com/api/google/v1/publishers/anthropic/models/claude-sonnet-4-5@20250929:rawPredict" \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"anthropic_version":"vertex-2023-10-16","messages":[{"role":"user","content":"Hello"}],"max_tokens":10}'
```

**Model Not Found (404):**
- Verify model name: `claude-sonnet-4-5@20250929`
- Check available models in Bosch LLM Farm portal

#### Document Fetching Failures

Common causes:
- **Network restrictions**: Target site blocking requests
- **Content selector issues**: CSS selector not matching
- **Rate limiting**: Too frequent requests

### Debug Mode

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python -m uvicorn app.main:app --reload
```

### Health Check

```bash
curl http://localhost:8080/health | jq
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature
   ```
3. **Make changes and test**
   ```bash
   pytest
   black app/
   isort app/
   ```
4. **Commit changes**
   ```bash
   git commit -m "feat: add new feature"
   ```
5. **Push and create PR**
   ```bash
   git push origin feature/your-feature
   ```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

- **Documentation**: Check `/docs` endpoint when running the service
- **Issues**: Report bugs via GitHub Issues
- **Web UI**: Access at `/ui` for browser-friendly interface

Built with ❤️ using FastAPI, Google Cloud, and AI technologies.
