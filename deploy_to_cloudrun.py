#!/usr/bin/env python3
"""
Deploy ToS Monitor to Google Cloud Run.

This script builds a Docker image, pushes it to Google Container Registry,
and deploys it to Google Cloud Run with the appropriate configuration.

Usage:
    python deploy_to_cloudrun.py [OPTIONS]

Requirements:
    - gcloud CLI installed and authenticated
    - Docker installed (for local builds)
    - Proper Google Cloud permissions
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class CloudRunDeployer:
    """Deploys ToS Monitor application to Google Cloud Run."""

    def __init__(self, config: Dict):
        """
        Initialize the deployer with configuration.

        Args:
            config: Deployment configuration dictionary
        """
        self.config = config
        self.project_id = config['project_id']
        self.region = config['region']
        self.service_name = config['service_name']
        self.image_name = f"gcr.io/{self.project_id}/{self.service_name}"

    def run_command(self, cmd: List[str], capture_output: bool = True, check: bool = True) -> subprocess.CompletedProcess:
        """
        Run a shell command and return the result.

        Args:
            cmd: Command and arguments as a list
            capture_output: Whether to capture stdout/stderr
            check: Whether to raise exception on non-zero exit code

        Returns:
            CompletedProcess object
        """
        print(f"🔄 Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=check
            )

            if capture_output and result.stdout:
                print(f"✓ Output: {result.stdout.strip()}")

            return result

        except subprocess.CalledProcessError as e:
            print(f"✗ Command failed with exit code {e.returncode}")
            if e.stdout:
                print(f"  stdout: {e.stdout.strip()}")
            if e.stderr:
                print(f"  stderr: {e.stderr.strip()}")
            raise

    def check_prerequisites(self) -> bool:
        """
        Check that all required tools and authentication are available.

        Returns:
            True if all prerequisites are met, False otherwise
        """
        print("📋 Checking prerequisites...")

        # Check gcloud CLI
        try:
            result = self.run_command(['gcloud', 'version'], capture_output=True)
            print("✓ gcloud CLI is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("✗ gcloud CLI is not installed or not in PATH")
            return False

        # Check authentication
        try:
            result = self.run_command(['gcloud', 'auth', 'list', '--format=json'], capture_output=True)
            accounts = json.loads(result.stdout)
            active_accounts = [acc for acc in accounts if acc.get('status') == 'ACTIVE']

            if not active_accounts:
                print("✗ No active gcloud authentication found")
                print("  Run: gcloud auth login")
                return False

            print(f"✓ Authenticated as: {active_accounts[0]['account']}")

        except (subprocess.CalledProcessError, json.JSONDecodeError):
            print("✗ Could not verify gcloud authentication")
            return False

        # Check project access
        try:
            self.run_command(['gcloud', 'config', 'set', 'project', self.project_id])
            print(f"✓ Project {self.project_id} is accessible")
        except subprocess.CalledProcessError:
            print(f"✗ Cannot access project {self.project_id}")
            return False

        # Check Docker (optional for cloud builds)
        if not self.config.get('use_cloud_build', True):
            try:
                self.run_command(['docker', '--version'])
                print("✓ Docker is available")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("✗ Docker is not installed or not in PATH")
                print("  Consider using --cloud-build option")
                return False

        return True

    def build_and_push_image(self, use_cloud_build: bool = True) -> bool:
        """
        Build and push the Docker image.

        Args:
            use_cloud_build: Whether to use Google Cloud Build

        Returns:
            True if successful, False otherwise
        """
        print(f"🏗️  Building and pushing Docker image...")
        print(f"   Image: {self.image_name}")
        print(f"   Method: {'Cloud Build' if use_cloud_build else 'Local Docker'}")

        try:
            if use_cloud_build:
                # Use Google Cloud Build
                cmd = [
                    'gcloud', 'builds', 'submit',
                    '--tag', self.image_name,
                    '--timeout', '10m'
                ]
                self.run_command(cmd, capture_output=False)
            else:
                # Use local Docker
                # Build locally
                build_cmd = ['docker', 'build', '-t', self.image_name, '.']
                self.run_command(build_cmd, capture_output=False)

                # Push to registry
                push_cmd = ['docker', 'push', self.image_name]
                self.run_command(push_cmd, capture_output=False)

            print("✓ Image built and pushed successfully")
            return True

        except subprocess.CalledProcessError:
            print("✗ Failed to build and push image")
            return False

    def prepare_env_vars(self) -> List[str]:
        """
        Prepare environment variables for Cloud Run deployment.

        Returns:
            List of environment variable strings in KEY=VALUE format
        """
        env_vars = []

        # Required environment variables
        required_env = {
            'STORAGE_MODE': 'cloud',
            'STORAGE_BUCKET': self.config['storage_bucket'],
            'GOOGLE_CLOUD_PROJECT': self.project_id,
            'AI_PROVIDER': self.config['ai_provider'],
            'HOST': '0.0.0.0'
        }

        # AI provider specific variables
        if self.config['ai_provider'] == 'openrouter':
            required_env.update({
                'OPENROUTER_MODEL': self.config.get('openrouter_model', 'x-ai/grok-code-fast-1'),
                'OPENROUTER_API_KEY': self.config['openrouter_api_key']
            })
        elif self.config['ai_provider'] == 'openai':
            required_env.update({
                'LLM_MODEL': self.config.get('llm_model', 'gpt-4-turbo-preview'),
                'OPENAI_API_KEY': self.config['openai_api_key']
            })

        # Add optional environment variables
        optional_env = self.config.get('additional_env_vars', {})
        required_env.update(optional_env)

        # Convert to gcloud format
        for key, value in required_env.items():
            env_vars.append(f"{key}={value}")

        return env_vars

    def deploy_to_cloud_run(self, dry_run: bool = False) -> bool:
        """
        Deploy the application to Google Cloud Run.

        Args:
            dry_run: If True, show what would be deployed without actually deploying

        Returns:
            True if successful, False otherwise
        """
        print(f"🚀 Deploying to Cloud Run...")
        print(f"   Service: {self.service_name}")
        print(f"   Region: {self.region}")
        print(f"   Project: {self.project_id}")

        # Prepare deployment command
        cmd = [
            'gcloud', 'run', 'deploy', self.service_name,
            '--image', self.image_name,
            '--platform', 'managed',
            '--region', self.region,
            '--allow-unauthenticated',
            '--service-account', f"{self.config['service_account']}@{self.project_id}.iam.gserviceaccount.com",
            '--memory', self.config.get('memory', '512Mi'),
            '--cpu', self.config.get('cpu', '0.5'),
            '--max-instances', str(self.config.get('max_instances', 2)),
            '--port', '8080'
        ]

        # Add environment variables
        env_vars = self.prepare_env_vars()
        if env_vars:
            cmd.extend(['--set-env-vars', ','.join(env_vars)])

        if dry_run:
            print("🔍 DRY RUN MODE - Command that would be executed:")
            print(f"   {' '.join(cmd)}")
            print(f"\n📋 Environment variables that would be set:")
            for env_var in env_vars:
                key, value = env_var.split('=', 1)
                # Mask sensitive values
                if 'API_KEY' in key or 'SECRET' in key:
                    masked_value = value[:8] + '*' * (len(value) - 8) if len(value) > 8 else '***'
                    print(f"   {key}={masked_value}")
                else:
                    print(f"   {key}={value}")
            return True

        try:
            self.run_command(cmd, capture_output=False)
            print("✓ Deployment successful")
            return True

        except subprocess.CalledProcessError:
            print("✗ Deployment failed")
            return False

    def get_service_info(self) -> Optional[Dict]:
        """
        Get information about the deployed service.

        Returns:
            Service information dictionary or None if failed
        """
        try:
            cmd = [
                'gcloud', 'run', 'services', 'describe', self.service_name,
                '--platform', 'managed',
                '--region', self.region,
                '--format', 'json'
            ]
            result = self.run_command(cmd)
            return json.loads(result.stdout)

        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return None

    def show_deployment_info(self) -> None:
        """Show information about the deployed service."""
        print("📊 Deployment Information")
        print("=" * 50)

        service_info = self.get_service_info()
        if not service_info:
            print("Could not retrieve service information")
            return

        # Extract key information
        status = service_info.get('status', {})
        spec = service_info.get('spec', {})

        # Service URL
        url = status.get('url', 'Unknown')
        print(f"🌐 Service URL: {url}")

        # Latest revision
        latest_revision = status.get('latestRevision', {}).get('name', 'Unknown')
        print(f"📦 Latest Revision: {latest_revision}")

        # Traffic allocation
        traffic = status.get('traffic', [])
        for t in traffic:
            percent = t.get('percent', 0)
            revision = t.get('revisionName', 'Unknown')
            print(f"🚦 Traffic: {percent}% -> {revision}")

        # Resource limits
        template = spec.get('template', {})
        containers = template.get('spec', {}).get('containers', [])
        if containers:
            resources = containers[0].get('resources', {})
            limits = resources.get('limits', {})
            cpu = limits.get('cpu', 'Unknown')
            memory = limits.get('memory', 'Unknown')
            print(f"💾 Resources: CPU={cpu}, Memory={memory}")

        print(f"\n🎯 Quick Test Commands:")
        print(f"   Health check: curl {url}/health")
        print(f"   List ToS docs: curl {url}/tos")
        print(f"   API docs: {url}/docs")

    def deploy(self, dry_run: bool = False, skip_build: bool = False) -> bool:
        """
        Complete deployment process.

        Args:
            dry_run: If True, show what would be done without actually doing it
            skip_build: If True, skip the build step and deploy existing image

        Returns:
            True if successful, False otherwise
        """
        start_time = datetime.now()

        print("🚀 ToS Monitor Cloud Run Deployment")
        print("=" * 50)
        print(f"⏰ Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Check prerequisites
        if not dry_run and not self.check_prerequisites():
            return False

        success = True

        # Build and push image
        if not skip_build and not dry_run:
            print("\n" + "=" * 50)
            success = self.build_and_push_image(self.config.get('use_cloud_build', True))
            if not success:
                return False

        # Deploy to Cloud Run
        print("\n" + "=" * 50)
        success = self.deploy_to_cloud_run(dry_run)
        if not success:
            return False

        # Show deployment info
        if not dry_run:
            print("\n" + "=" * 50)
            self.show_deployment_info()

        # Summary
        end_time = datetime.now()
        duration = end_time - start_time

        print(f"\n✅ Deployment completed successfully!")
        print(f"⏱️  Total time: {duration.total_seconds():.1f} seconds")

        return True


def load_config_from_env() -> Dict:
    """
    Load configuration from .env file and environment variables.

    Returns:
        Configuration dictionary
    """
    config = {}

    # Try to load from .env file
    env_file = Path('.env')
    if env_file.exists():
        print(f"📄 Loading configuration from {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

    # Extract configuration from environment
    config = {
        'project_id': os.getenv('GOOGLE_CLOUD_PROJECT'),
        'region': os.getenv('CLOUD_RUN_REGION', 'europe-west3'),
        'service_name': os.getenv('SERVICE_NAME', 'tos-monitor'),
        'service_account': os.getenv('SERVICE_ACCOUNT', 'tos-monitor-service'),
        'storage_bucket': os.getenv('STORAGE_BUCKET', 'tos-monitor'),
        'ai_provider': os.getenv('AI_PROVIDER', 'openrouter').lower(),
        'memory': os.getenv('MEMORY', '512Mi'),
        'cpu': os.getenv('CPU', '0.5'),
        'max_instances': int(os.getenv('MAX_INSTANCES', '2')),
        'use_cloud_build': os.getenv('USE_CLOUD_BUILD', 'true').lower() == 'true',
    }

    # AI provider specific config
    if config['ai_provider'] == 'openrouter':
        config.update({
            'openrouter_api_key': os.getenv('OPENROUTER_API_KEY'),
            'openrouter_model': os.getenv('OPENROUTER_MODEL', 'x-ai/grok-code-fast-1'),
        })
    elif config['ai_provider'] == 'openai':
        config.update({
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'llm_model': os.getenv('LLM_MODEL', 'gpt-4-turbo-preview'),
        })

    return config


def validate_config(config: Dict) -> List[str]:
    """
    Validate the configuration.

    Args:
        config: Configuration dictionary

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Required fields
    required_fields = ['project_id', 'storage_bucket']
    for field in required_fields:
        if not config.get(field):
            errors.append(f"Missing required configuration: {field.upper()}")

    # AI provider specific validation
    ai_provider = config.get('ai_provider', 'openrouter')
    if ai_provider == 'openrouter':
        if not config.get('openrouter_api_key'):
            errors.append("Missing OPENROUTER_API_KEY for OpenRouter provider")
    elif ai_provider == 'openai':
        if not config.get('openai_api_key'):
            errors.append("Missing OPENAI_API_KEY for OpenAI provider")
    else:
        errors.append(f"Invalid AI_PROVIDER: {ai_provider} (must be 'openai' or 'openrouter')")

    return errors


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Deploy ToS Monitor to Google Cloud Run",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy_to_cloudrun.py                    # Full deployment
  python deploy_to_cloudrun.py --dry-run          # Show what would be deployed
  python deploy_to_cloudrun.py --skip-build       # Deploy without rebuilding image
  python deploy_to_cloudrun.py --local-build      # Use local Docker instead of Cloud Build

Configuration:
  The script reads configuration from .env file and environment variables.
  Required: GOOGLE_CLOUD_PROJECT, STORAGE_BUCKET, OPENROUTER_API_KEY (or OPENAI_API_KEY)
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deployed without actually deploying'
    )

    parser.add_argument(
        '--skip-build',
        action='store_true',
        help='Skip building image and deploy existing image'
    )

    parser.add_argument(
        '--local-build',
        action='store_true',
        help='Use local Docker build instead of Cloud Build'
    )

    parser.add_argument(
        '--config-file',
        help='Path to configuration file (default: .env)'
    )

    args = parser.parse_args()

    try:
        # Load configuration
        config = load_config_from_env()

        # Override cloud build setting if local build requested
        if args.local_build:
            config['use_cloud_build'] = False

        # Validate configuration
        errors = validate_config(config)
        if errors:
            print("❌ Configuration errors:")
            for error in errors:
                print(f"   {error}")
            print("\nPlease check your .env file or environment variables.")
            sys.exit(1)

        # Create deployer and deploy
        deployer = CloudRunDeployer(config)
        success = deployer.deploy(dry_run=args.dry_run, skip_build=args.skip_build)

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()