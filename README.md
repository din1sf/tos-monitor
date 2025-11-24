# ToS Monitor

A serverless Terms of Service monitoring service that automatically tracks changes in legal documents, stores snapshots in Cloud Storage, and generates human-readable summaries using LLM analysis.

## Features

- 🔍 **Automatic Document Monitoring**: Fetches and monitors legal documents from configured URLs
- 📸 **Smart Snapshots**: Creates snapshots only when meaningful content changes are detected
- 🤖 **LLM-Powered Analysis**: Generates human-readable summaries of document changes using OpenAI GPT models
- ☁️ **Cloud-Native**: Designed for Google Cloud Run with Cloud Storage for persistence
- 🎯 **Intelligent Change Detection**: Multiple hashing strategies to distinguish between cosmetic and substantial changes
- 📊 **RESTful API**: Clean API for fetching documents, generating diffs, and retrieving results
- 🏗️ **Serverless Architecture**: Scales to zero when not in use, cost-effective operation

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scheduler     │    │   Cloud Run     │    │ Cloud Storage   │
│  (Cloud Tasks)  │───▶│   (FastAPI)     │───▶│   (Snapshots)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   OpenAI API    │
                       │ (Diff Analysis) │
                       └─────────────────┘
```

## Storage Layout

```
storage-bucket/
├── config/
│   └── documents.json          # Document configuration
├── prompts/
│   ├── default_comparison.txt  # Default LLM prompt
│   └── {doc_id}_comparison.txt # Document-specific prompts
├── snapshots/
│   └── {doc_id}/
│       └── {timestamp}/
│           ├── content.txt     # Normalized document content
│           └── metadata.json   # Snapshot metadata
├── latest/
│   └── {doc_id}/
│       ├── content.txt         # Latest document version
│       ├── metadata.json       # Latest metadata
│       ├── diff.txt           # Latest diff content
│       └── diff_metadata.json # Latest diff metadata
└── diffs/
    └── {doc_id}/
        └── {timestamp}/
            ├── diff.txt        # LLM-generated comparison
            └── metadata.json   # Diff metadata
```

## Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud Project with Cloud Storage and Cloud Run enabled
- OpenAI API key

### Local Development

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd tos-monitor

   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run locally**:
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Cloud Deployment

1. **Create Cloud Storage bucket**:
   ```bash
   gsutil mb -l us-central1 gs://your-bucket-name
   ```

2. **Upload initial configuration**:
   ```bash
   gsutil cp config/documents.json gs://your-bucket-name/config/
   gsutil cp prompts/default_comparison.txt gs://your-bucket-name/prompts/
   ```

3. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy tos-monitor \
     --source . \
     --region us-central1 \
     --allow-unauthenticated=false \
     --set-env-vars STORAGE_BUCKET=your-bucket-name,OPENAI_API_KEY=your-api-key
   ```

4. **Setup Cloud Scheduler** (optional):
   ```bash
   # Fetch documents weekly (Mondays at 7 AM)
   gcloud scheduler jobs create http fetch-docs \
     --schedule="0 7 * * 1" \
     --uri="https://your-service-url/fetch-docs" \
     --oidc-service-account="your-invoker-sa"

   # Generate diffs (Mondays at 7:05 AM)
   gcloud scheduler jobs create http generate-diffs \
     --schedule="5 7 * * 1" \
     --uri="https://your-service-url/generate-diffs" \
     --oidc-service-account="your-invoker-sa"
   ```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `STORAGE_BUCKET` | Google Cloud Storage bucket name | Yes |
| `OPENAI_API_KEY` | OpenAI API key for LLM analysis | Yes |
| `LLM_MODEL` | OpenAI model to use (default: gpt-4-turbo-preview) | No |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | No* |
| `PORT` | Port to run the application (default: 8080) | No |

*Required for Cloud Run deployment

## API Endpoints

### Document Management

- **POST /fetch-docs**: Download and store legal documents
  ```json
  {
    "document_ids": ["anthropic_commercial_terms"],  // Optional filter
    "force_update": false  // Force update even if no changes
  }
  ```

- **POST /generate-diffs**: Generate LLM-powered document comparisons
  ```json
  {
    "document_ids": ["anthropic_commercial_terms"],  // Optional filter
    "force_regenerate": false  // Force regeneration
  }
  ```

### Diff Retrieval

- **GET /diffs**: List all documents with diff status
- **GET /diffs/{document_id}**: Get latest diff for a document
- **GET /diffs/{document_id}/{timestamp}**: Get specific diff by timestamp
- **GET /diffs/{document_id}/history**: Get diff history for a document

### Utility

- **GET /**: Service information
- **GET /health**: Health check with dependency validation
- **GET /config**: Current configuration information

## Configuration

### Document Configuration (`config/documents.json`)

```json
{
  "documents": [
    {
      "id": "unique_document_id",
      "name": "Human Readable Name",
      "url": "https://example.com/terms",
      "selector": "main"  // Optional CSS selector
    }
  ]
}
```

### Custom Prompts

Create document-specific prompts by adding `{document_id}_comparison.txt` files to the `prompts/` directory in your storage bucket.

## Change Detection

The system uses three levels of content hashing:

1. **Content Hash**: Detects any change in the document
2. **Structural Hash**: Ignores minor formatting changes
3. **Fingerprint Hash**: Ignores dates, versions, and minor content changes

This allows the system to:
- Create snapshots only when content meaningfully changes
- Generate diffs only for substantial modifications
- Avoid noise from cosmetic updates

## Development

### Project Structure

```
app/
├── main.py                 # FastAPI application
├── storage.py              # Cloud Storage integration
├── llm_client.py           # OpenAI LLM client
├── routes/
│   ├── fetch_docs.py       # Document fetching endpoint
│   ├── generate_diffs.py   # Diff generation endpoint
│   └── get_diffs.py        # Diff retrieval endpoints
└── utils/
    ├── html_parser.py      # Web scraping and HTML parsing
    ├── normalizer.py       # Text normalization
    └── hashing.py          # Content hashing and comparison
```

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

# Sort imports
isort app/

# Type checking
mypy app/
```

## Monitoring

The service includes comprehensive logging and health checks:

- **Health Endpoint**: `/health` validates all dependencies
- **Structured Logging**: JSON-formatted logs for Cloud Logging
- **Error Handling**: Graceful error handling with detailed error responses
- **Metrics**: Built-in request/response metrics

## Security

- **Authentication**: Configure authentication for production deployments
- **CORS**: Configure CORS policies for your domain
- **Service Accounts**: Use least-privilege service accounts
- **Secrets**: Store API keys in Google Secret Manager
- **Network Security**: Use VPC connectors for private resources

## Cost Optimization

- **Serverless**: Scales to zero when not in use
- **Efficient Storage**: Only stores snapshots when content changes
- **LLM Optimization**: Smart prompts and content truncation to minimize token usage
- **Caching**: Built-in caching to avoid redundant operations

## Troubleshooting

### Common Issues

1. **Storage Permission Errors**:
   - Ensure service account has Storage Object Admin role
   - Verify bucket name and project configuration

2. **LLM API Errors**:
   - Check OpenAI API key validity and quota
   - Monitor token usage and rate limits

3. **Document Fetching Failures**:
   - Verify URLs are accessible
   - Check if sites require specific user agents
   - Consider rate limiting and retry logic

4. **Memory Issues**:
   - Large documents may require increased Cloud Run memory
   - Consider implementing content truncation for very long documents

### Debugging

Enable debug logging by setting log level:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check Cloud Logging for detailed execution traces and error messages.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure code passes linting and tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Check the [documentation](docs/)
- Search existing [issues](issues/)
- Create a new issue with detailed reproduction steps
