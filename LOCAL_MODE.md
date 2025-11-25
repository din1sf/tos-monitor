# ToS Monitor - Local Mode Setup

This document explains how to run ToS Monitor in local mode using local file storage instead of Google Cloud Storage.

## Overview

ToS Monitor now supports two storage modes:
- **Cloud Mode** (default): Uses Google Cloud Storage for all data storage
- **Local Mode**: Uses local file system for data storage

## Local Mode Configuration

### Environment Variables

Set these environment variables to enable local mode:

```bash
# Required: Set storage mode to local
export STORAGE_MODE=local

# Optional: Set custom local storage path (defaults to "./data")
export LOCAL_STORAGE_PATH=./data
```

### Directory Structure

In local mode, ToS Monitor creates the following directory structure:

```
data/                          # Base storage directory
├── config/                    # Configuration files
│   └── documents.json         # Document list configuration
├── prompts/                   # Prompt templates
│   └── default_comparison.txt # Default diff comparison prompt
├── snapshots/                 # Document snapshots
│   └── <doc_id>/             # Per-document snapshots
│       └── <timestamp>/       # Timestamped versions
│           ├── content.txt    # Document content
│           └── metadata.json  # Document metadata
├── latest/                    # Latest document versions
│   └── <doc_id>/             # Per-document latest files
│       ├── content.txt        # Latest content
│       ├── metadata.json      # Latest metadata
│       ├── diff.txt          # Latest diff (if any)
│       └── diff_metadata.json # Latest diff metadata
└── diffs/                     # Historical diffs
    └── <doc_id>/             # Per-document diffs
        └── <timestamp>/       # Timestamped diffs
            ├── diff.txt       # Diff content
            └── metadata.json  # Diff metadata
```

## Setup Instructions

### 1. Create Configuration

Create the configuration file at `data/config/documents.json`:

```json
{
  "documents": [
    {
      "id": "my-service-terms",
      "name": "My Service Terms",
      "url": "https://example.com/terms",
      "description": "Terms of service for my service"
    },
    {
      "id": "my-service-privacy",
      "name": "My Service Privacy Policy",
      "url": "https://example.com/privacy",
      "description": "Privacy policy for my service"
    }
  ]
}
```

### 2. Create Default Prompt (Optional)

Create a prompt template at `data/prompts/default_comparison.txt`:

```text
Compare the two versions of the document and identify any changes.

Document Name: {document_name}
Previous Version Timestamp: {prev_timestamp}
Current Version Timestamp: {curr_timestamp}

Previous Content:
{prev_content}

Current Content:
{curr_content}

Please provide a detailed summary of the changes, including:
1. New sections or clauses added
2. Sections or clauses removed
3. Modified text with specific differences
4. Overall significance of the changes

Keep the analysis focused on legal and policy implications.
```

### 3. Configure Environment Variables

The easiest way is to use the provided `.env` file which is automatically loaded:

```bash
# Edit the .env file (already configured for local mode)
# Set STORAGE_MODE=local (already set)
# Optionally change LOCAL_STORAGE_PATH (defaults to ./data)
```

Alternatively, you can set environment variables manually:

```bash
# Enable local mode
export STORAGE_MODE=local

# Optional: Set custom storage path
export LOCAL_STORAGE_PATH=./my-custom-data-dir
```

### 4. Install Dependencies (Local Mode Only)

In local mode, Google Cloud Storage dependencies are optional:

```bash
# Install core dependencies (without google-cloud-storage)
pip install fastapi uvicorn requests beautifulsoup4 openai pydantic python-multipart
```

Or use the full requirements if you want to support both modes:

```bash
pip install -r requirements.txt
```

### 5. Start the Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The application will start in local mode and create the necessary directories automatically.

## Testing Local Mode

Run the included test script to verify local storage functionality:

```bash
python3 test_local_storage.py
```

This will test:
- Configuration loading
- Prompt loading
- Document snapshot storage
- Latest document retrieval
- Snapshot listing
- Diff storage
- Basic file operations

## API Usage

Once running in local mode, use the same API endpoints:

```bash
# Fetch documents and store locally
curl -X POST http://localhost:8000/fetch-docs

# Get latest documents from local storage
curl http://localhost:8000/documents

# Get document history from local storage
curl http://localhost:8000/documents/my-service-terms/history
```

## Migration from Cloud to Local

To migrate existing data from cloud storage to local storage:

1. Export your documents using the cloud mode
2. Switch to local mode by setting `STORAGE_MODE=local`
3. Import the documents using the fetch-docs endpoint

## Advantages of Local Mode

- **No Cloud Dependencies**: Works without Google Cloud Storage setup
- **Complete Data Control**: All data stored locally
- **Offline Capability**: No internet required for storage operations
- **Cost-Effective**: No cloud storage costs
- **Privacy**: Data never leaves your machine
- **Development Friendly**: Easy to inspect and debug stored data

## Limitations

- **No Built-in Backup**: You need to handle backups manually
- **Single Machine**: Data is tied to the local machine
- **Scalability**: Less suitable for distributed deployments

## Backup Recommendations

Since local mode stores all data locally, consider these backup strategies:

1. **Regular Directory Backup**: Backup the entire data directory
2. **Version Control**: Use git to track configuration changes
3. **Automated Sync**: Use rsync or similar tools for regular sync
4. **Cloud Backup**: Backup the data directory to cloud storage services