# ToS Monitor - GCS Upload Script

A Python script to upload your local ToS Monitor data to Google Cloud Storage.

## Quick Start

```bash
# Install dependencies
pip install google-cloud-storage

# Authenticate with Google Cloud
gcloud auth application-default login

# Test what would be uploaded (dry run)
python upload_to_gcs.py --bucket tos-monitor --dry-run

# Actually upload the data
python upload_to_gcs.py --bucket tos-monitor
```

## Usage Options

```bash
python upload_to_gcs.py --bucket BUCKET_NAME [OPTIONS]
```

### Required Arguments
- `--bucket BUCKET_NAME` - Google Cloud Storage bucket name

### Optional Arguments
- `--data-dir PATH` - Local data directory (default: `data`)
- `--dry-run` - Show what would be uploaded without actually uploading

## Examples

```bash
# Upload from default data directory
python upload_to_gcs.py --bucket my-tos-bucket

# Upload from custom directory
python upload_to_gcs.py --bucket my-tos-bucket --data-dir /path/to/data

# Test upload without actually uploading
python upload_to_gcs.py --bucket my-tos-bucket --dry-run

# Upload from different data directory with dry run
python upload_to_gcs.py --bucket my-tos-bucket --data-dir ./custom-data --dry-run
```

## What Gets Uploaded

The script maintains the exact folder structure needed by ToS Monitor:

```
gs://your-bucket/
├── documents.json              ← Configuration file
├── prompt.txt                  ← Prompt templates
└── tos/
    └── anthropic/              ← Document data
        ├── current.txt
        ├── current.json
        ├── last.txt
        ├── prev.txt
        ├── 2024-03-04.txt
        ├── 2024-03-04.json
        └── ... (other versions)
```

## Prerequisites

1. **Google Cloud Authentication**:
   ```bash
   gcloud auth application-default login
   ```

2. **Bucket Permissions**: You need write access to the target bucket

3. **Python Dependencies**:
   ```bash
   pip install google-cloud-storage
   ```

## Features

- ✅ Maintains correct folder structure for ToS Monitor
- ✅ Automatically detects file types (JSON, TXT, etc.)
- ✅ Dry run mode to preview uploads
- ✅ Progress tracking and error handling
- ✅ Bucket access verification
- ✅ Detailed upload summary

## Troubleshooting

### Authentication Issues
```bash
# Re-authenticate
gcloud auth application-default login

# Check current authentication
gcloud auth list
```

### Permission Issues
- Ensure your account has `Storage Object Admin` role on the bucket
- Verify the bucket exists: `gsutil ls gs://your-bucket-name`

### Bucket Not Found
- Create bucket: `gsutil mb gs://your-bucket-name`
- Check spelling and project access