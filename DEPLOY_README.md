# ToS Monitor - Cloud Run Deployment Script

A comprehensive Python script to build, deploy, and update your ToS Monitor application on Google Cloud Run.

## Quick Start

```bash
# Make sure you're authenticated
gcloud auth login
gcloud config set project your-project-id

# Test what would be deployed (dry run)
python deploy_to_cloudrun.py --dry-run

# Deploy the application
python deploy_to_cloudrun.py
```

## Usage Options

```bash
python deploy_to_cloudrun.py [OPTIONS]
```

### Available Options
- `--dry-run` - Show what would be deployed without actually deploying
- `--skip-build` - Skip building image and deploy existing image
- `--local-build` - Use local Docker instead of Google Cloud Build
- `--config-file PATH` - Path to configuration file (default: .env)

## Configuration

The script reads configuration from your `.env` file. Required variables:

```bash
# Required
GOOGLE_CLOUD_PROJECT=your-project-id
STORAGE_BUCKET=your-bucket-name

# AI Provider (choose one)
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# OR for OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here
```

See `deploy-config.env.example` for all available options.

## Examples

### Full Deployment (Recommended)
```bash
# Build new image and deploy
python deploy_to_cloudrun.py
```

### Quick Update (Code Changes)
```bash
# Build and deploy with updated code
python deploy_to_cloudrun.py
```

### Deploy Existing Image
```bash
# Deploy without rebuilding (faster for config-only changes)
python deploy_to_cloudrun.py --skip-build
```

### Test Deployment
```bash
# See what would be deployed without actually deploying
python deploy_to_cloudrun.py --dry-run
```

### Use Local Docker
```bash
# Build locally instead of using Cloud Build
python deploy_to_cloudrun.py --local-build
```

## What the Script Does

1. **✅ Prerequisites Check**
   - Verifies gcloud CLI is installed
   - Checks authentication status
   - Validates project access
   - Confirms Docker availability (if needed)

2. **🏗️ Image Build & Push**
   - Uses Google Cloud Build (default) or local Docker
   - Builds from current directory's Dockerfile
   - Pushes to Google Container Registry
   - Handles build timeouts and errors

3. **🚀 Cloud Run Deployment**
   - Deploys with optimal configuration
   - Sets up environment variables
   - Configures resource limits
   - Assigns proper service account

4. **📊 Post-Deployment Info**
   - Shows service URL
   - Displays resource allocation
   - Provides test commands
   - Shows revision information

## Deployment Configuration

### Automatic Configuration
The script automatically configures:
- **Port 8080** (Cloud Run standard)
- **Service account** with storage permissions
- **Environment variables** from your .env file
- **Resource limits** (customizable)
- **Auto-scaling** settings

### Resource Settings
Default resource limits (customizable in .env):
```bash
MEMORY=512Mi      # Memory allocation
CPU=0.5           # CPU allocation
MAX_INSTANCES=2   # Maximum instances
```

### Environment Variables
The script automatically sets these in Cloud Run:
- `STORAGE_MODE=cloud`
- `STORAGE_BUCKET=your-bucket`
- `GOOGLE_CLOUD_PROJECT=your-project`
- `AI_PROVIDER=openrouter` (or openai)
- `OPENROUTER_API_KEY=***` (from .env)
- Plus any additional variables from .env

## Prerequisites

1. **Google Cloud SDK**:
   ```bash
   # Install gcloud CLI
   curl https://sdk.cloud.google.com | bash

   # Authenticate
   gcloud auth login
   gcloud config set project your-project-id
   ```

2. **Required APIs**:
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

3. **Service Account** (if not exists):
   ```bash
   # The script expects this service account to exist
   gcloud iam service-accounts create tos-monitor-service \
     --display-name="ToS Monitor Service Account"
   ```

4. **Permissions**:
   - Cloud Run Admin
   - Storage Admin (for bucket access)
   - Cloud Build Editor (for image building)

## Troubleshooting

### Authentication Issues
```bash
# Re-authenticate
gcloud auth login

# Check current auth
gcloud auth list

# Set project
gcloud config set project your-project-id
```

### Permission Issues
```bash
# Check current project
gcloud config get-value project

# List available projects
gcloud projects list

# Check IAM permissions
gcloud projects get-iam-policy your-project-id
```

### Build Issues
```bash
# Use local build instead of Cloud Build
python deploy_to_cloudrun.py --local-build

# Check Cloud Build status
gcloud builds list --limit=5
```

### Service Issues
```bash
# Check service status
gcloud run services list

# View service logs
gcloud run services logs read tos-monitor

# Describe service
gcloud run services describe tos-monitor --region=europe-west3
```

## Output Example

```
🚀 ToS Monitor Cloud Run Deployment
==================================================
⏰ Started at: 2025-11-26 17:15:30

📋 Checking prerequisites...
✓ gcloud CLI is available
✓ Authenticated as: your-email@gmail.com
✓ Project your-project-id is accessible

==================================================
🏗️ Building and pushing Docker image...
   Image: gcr.io/your-project-id/tos-monitor
   Method: Cloud Build
✓ Image built and pushed successfully

==================================================
🚀 Deploying to Cloud Run...
   Service: tos-monitor
   Region: europe-west3
   Project: your-project-id
✓ Deployment successful

==================================================
📊 Deployment Information
🌐 Service URL: https://tos-monitor-123456789.europe-west3.run.app
📦 Latest Revision: tos-monitor-00004-abc
🚦 Traffic: 100% -> tos-monitor-00004-abc
💾 Resources: CPU=0.5, Memory=512Mi

🎯 Quick Test Commands:
   Health check: curl https://tos-monitor-123456789.europe-west3.run.app/health
   List ToS docs: curl https://tos-monitor-123456789.europe-west3.run.app/tos
   API docs: https://tos-monitor-123456789.europe-west3.run.app/docs

✅ Deployment completed successfully!
⏱️ Total time: 45.2 seconds
```

## Security Notes

- API keys are automatically masked in dry-run output
- Uses service accounts instead of user credentials in production
- Environment variables are encrypted at rest in Cloud Run
- All traffic uses HTTPS automatically