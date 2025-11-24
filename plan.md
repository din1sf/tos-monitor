# ToS Monitor Implementation Plan

## Project Overview
A serverless Terms of Service monitoring service that automatically tracks changes in legal documents, stores snapshots in Cloud Storage, and generates human-readable summaries using LLM analysis.

## 📋 Implementation Checklist

### Phase 1: Project Setup & Dependencies
- [ ] **Setup Python FastAPI project structure**
  - [ ] Create `requirements.txt` with dependencies (FastAPI, uvicorn, google-cloud-storage, etc.)
  - [ ] Create `Dockerfile` for Cloud Run deployment
  - [ ] Setup `.gitignore` for Python project
  - [ ] Create basic project structure as per suggested layout

- [ ] **Create project directory structure:**
  ```
  app/
    main.py
    routes/
      fetch_docs.py
      generate_diffs.py
      get_diffs.py
    storage.py
    llm_client.py
    utils/
      html_parser.py
      normalizer.py
      hashing.py
  config/
    documents.json
  prompts/
    default_comparison.txt
  ```

### Phase 2: Core Infrastructure
- [ ] **Google Cloud Storage Integration (`app/storage.py`)**
  - [ ] Implement storage client initialization
  - [ ] Create functions for bucket operations:
    - [ ] `upload_file()` - Upload files to specific paths
    - [ ] `download_file()` - Download files from storage
    - [ ] `list_files()` - List files in directories
    - [ ] `file_exists()` - Check if file exists
  - [ ] Implement storage layout management:
    - [ ] Snapshots storage (`snapshots/<doc_id>/<timestamp>/`)
    - [ ] Latest files storage (`latest/<doc_id>/`)
    - [ ] Diffs storage (`diffs/<doc_id>/`)
    - [ ] Config storage (`config/`)
    - [ ] Prompts storage (`prompts/`)

- [ ] **LLM Integration (`app/llm_client.py`)**
  - [ ] Choose and configure LLM provider (OpenAI, Anthropic, Vertex AI, etc.)
  - [ ] Implement LLM client with:
    - [ ] `compare_documents()` - Generate diff summaries
    - [ ] Prompt template loading from storage
    - [ ] Error handling and retries
    - [ ] Token usage optimization

### Phase 3: Utility Functions
- [ ] **HTML Parser (`app/utils/html_parser.py`)**
  - [ ] Implement web scraper using requests/httpx
  - [ ] Add user-agent spoofing for different sites
  - [ ] Handle JavaScript-rendered content (if needed)
  - [ ] Implement timeout and retry logic
  - [ ] Add HTML validation and sanitization

- [ ] **Text Normalizer (`app/utils/normalizer.py`)**
  - [ ] Remove HTML tags and extract text content
  - [ ] Normalize whitespace and line breaks
  - [ ] Remove ads, navigation, and boilerplate content
  - [ ] Preserve document structure (headings, lists, etc.)
  - [ ] Handle different document formats (HTML, PDF, etc.)

- [ ] **Content Hashing (`app/utils/hashing.py`)**
  - [ ] Implement content hashing for change detection
  - [ ] Create `generate_hash()` function using SHA-256
  - [ ] Implement `has_content_changed()` comparison function

### Phase 4: API Endpoints

#### POST /fetch-docs (`app/routes/fetch_docs.py`)
- [ ] **Core functionality:**
  - [ ] Load document configuration from `config/documents.json`
  - [ ] Download documents from configured URLs
  - [ ] Normalize document content
  - [ ] Generate content hash for change detection
  - [ ] Compare with previous snapshot
  - [ ] Store new snapshots only when content changes
  - [ ] Update latest snapshot pointers
  - [ ] Create metadata files with timestamps

- [ ] **Optional features:**
  - [ ] Support for filtering specific documents via request body
  - [ ] Parallel document processing
  - [ ] Progress tracking and logging
  - [ ] Error handling per document

#### POST /generate-diffs (`app/routes/generate_diffs.py`)
- [ ] **Core functionality:**
  - [ ] Load all documents with existing snapshots
  - [ ] Find previous and current versions for each document
  - [ ] Load appropriate LLM prompts from storage
  - [ ] Generate diff summaries using LLM
  - [ ] Store diff results in storage
  - [ ] Update latest diff pointers

- [ ] **Features:**
  - [ ] Support for document-specific prompts
  - [ ] Fallback to default prompt if document-specific not found
  - [ ] Batch processing optimization
  - [ ] Error handling and partial failures

#### GET /diffs/* (`app/routes/get_diffs.py`)
- [ ] **Implement endpoints:**
  - [ ] `GET /diffs` - List all documents with latest diff timestamps
  - [ ] `GET /diffs/<doc_id>` - Get latest diff for specific document
  - [ ] `GET /diffs/<doc_id>/<timestamp>` - Get specific historical diff

- [ ] **Features:**
  - [ ] JSON response formatting
  - [ ] Error handling for missing documents/diffs
  - [ ] Optional query parameters for filtering

### Phase 5: Main Application (`app/main.py`)
- [ ] **FastAPI application setup:**
  - [ ] Initialize FastAPI app with proper configuration
  - [ ] Add CORS middleware if needed
  - [ ] Include all route modules
  - [ ] Add health check endpoint
  - [ ] Implement logging configuration
  - [ ] Add authentication middleware (if required)

### Phase 6: Configuration Files
- [ ] **Create `config/documents.json`:**
  ```json
  {
    "documents": [
      {
        "id": "anthropic_commercial_terms",
        "name": "Anthropic Commercial Terms",
        "url": "https://www.anthropic.com/commercial-terms",
        "selector": "main" // optional CSS selector
      }
    ]
  }
  ```

- [ ] **Create `prompts/default_comparison.txt`:**
  - [ ] Write comprehensive prompt for LLM document comparison
  - [ ] Include instructions for formatting output
  - [ ] Add guidelines for identifying substantive vs. cosmetic changes

### Phase 7: Deployment Configuration
- [ ] **Create `Dockerfile`:**
  - [ ] Use appropriate Python base image
  - [ ] Install dependencies efficiently
  - [ ] Configure proper startup command
  - [ ] Set environment variables
  - [ ] Optimize image size

- [ ] **Create deployment scripts:**
  - [ ] Google Cloud Storage bucket creation
  - [ ] Initial config file upload
  - [ ] Cloud Run deployment command
  - [ ] Cloud Scheduler job creation
  - [ ] Service account and IAM setup

### Phase 8: Testing & Validation
- [ ] **Unit Tests:**
  - [ ] Test storage operations
  - [ ] Test HTML parsing and normalization
  - [ ] Test content hashing and comparison
  - [ ] Test API endpoints with mock data

- [ ] **Integration Tests:**
  - [ ] Test end-to-end document fetching flow
  - [ ] Test diff generation with real LLM
  - [ ] Test Cloud Storage integration
  - [ ] Validate storage layout compliance

- [ ] **Manual Testing:**
  - [ ] Test with sample legal documents
  - [ ] Verify diff quality and accuracy
  - [ ] Test error handling scenarios
  - [ ] Validate deployment on Cloud Run

### Phase 9: Production Readiness
- [ ] **Monitoring & Logging:**
  - [ ] Implement structured logging
  - [ ] Add performance metrics
  - [ ] Set up error alerting
  - [ ] Monitor Cloud Storage usage

- [ ] **Security:**
  - [ ] Review and secure API endpoints
  - [ ] Implement proper service account permissions
  - [ ] Validate input sanitization
  - [ ] Review secret management

- [ ] **Documentation:**
  - [ ] API documentation with examples
  - [ ] Deployment guide
  - [ ] Configuration reference
  - [ ] Troubleshooting guide

## 🔧 Technical Considerations

### Dependencies (requirements.txt)
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
google-cloud-storage>=2.10.0
requests>=2.31.0
beautifulsoup4>=4.12.0
openai>=1.0.0  # or anthropic, google-cloud-aiplatform
pydantic>=2.5.0
python-multipart>=0.0.6
```

### Environment Variables
- `GOOGLE_CLOUD_PROJECT` - GCP project ID
- `STORAGE_BUCKET` - Cloud Storage bucket name
- `LLM_API_KEY` - API key for chosen LLM provider
- `LLM_MODEL` - Model name to use

### Storage Permissions
- Service account needs Storage Object Admin role on the bucket
- Cloud Scheduler needs Cloud Run Invoker role

### Performance Optimization
- Use async/await for I/O operations
- Implement connection pooling for storage and LLM clients
- Consider using Cloud Tasks for long-running operations
- Optimize LLM token usage with prompt engineering

## 🚀 Deployment Steps (Post-Implementation)

1. **Create Cloud Storage bucket:**
   ```bash
   gsutil mb -l europe-central2 gs://legal-watcher/
   ```

2. **Upload initial configuration:**
   ```bash
   gsutil cp config/documents.json gs://legal-watcher/config/
   gsutil cp prompts/default_comparison.txt gs://legal-watcher/prompts/
   ```

3. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy tos-monitor \
     --source . \
     --region europe-central2 \
     --allow-unauthenticated=false \
     --set-env-vars STORAGE_BUCKET=legal-watcher
   ```

4. **Setup Cloud Scheduler jobs:**
   ```bash
   # Fetch documents weekly (Mondays at 7 AM)
   gcloud scheduler jobs create http fetch-docs \
     --schedule="0 7 * * 1" \
     --uri="https://[SERVICE-URL]/fetch-docs" \
     --oidc-service-account="[INVOKER-SA]"

   # Generate diffs (Mondays at 7:05 AM)
   gcloud scheduler jobs create http generate-diffs \
     --schedule="5 7 * * 1" \
     --uri="https://[SERVICE-URL]/generate-diffs" \
     --oidc-service-account="[INVOKER-SA]"
   ```

## ✅ Success Criteria

- [ ] System successfully monitors at least one legal document
- [ ] Changes are detected and proper snapshots created
- [ ] LLM generates meaningful diff summaries
- [ ] All API endpoints respond correctly
- [ ] Scheduled jobs execute successfully
- [ ] Storage layout follows specification
- [ ] Cloud Run deployment is stable and scalable

## 📝 Notes

- Consider rate limiting for external document fetching
- Implement document-specific parsing rules if needed
- Plan for handling different document formats beyond HTML
- Consider implementing webhook notifications for changes
- Plan for archiving old snapshots to manage storage costs