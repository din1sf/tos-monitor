#!/usr/bin/env python3
"""
Upload ToS Monitor data to Google Cloud Storage.

This script uploads the local data folder structure to a GCS bucket,
maintaining the correct folder structure for the ToS Monitor application.

Usage:
    python upload_to_gcs.py [--bucket BUCKET_NAME] [--data-dir DATA_DIR] [--dry-run]

Requirements:
    pip install google-cloud-storage
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple
import mimetypes

try:
    from google.cloud import storage
    from google.api_core import exceptions
except ImportError:
    print("Error: google-cloud-storage is not installed.")
    print("Install it with: pip install google-cloud-storage")
    sys.exit(1)


class ToSDataUploader:
    """Uploads ToS Monitor data to Google Cloud Storage."""

    def __init__(self, bucket_name: str, data_dir: str = "data"):
        """
        Initialize the uploader.

        Args:
            bucket_name: Name of the GCS bucket
            data_dir: Local data directory path (default: "data")
        """
        self.bucket_name = bucket_name
        self.data_dir = Path(data_dir)
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def get_content_type(self, file_path: Path) -> str:
        """
        Get the content type for a file.

        Args:
            file_path: Path to the file

        Returns:
            MIME content type string
        """
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            if file_path.suffix.lower() == '.json':
                return 'application/json'
            elif file_path.suffix.lower() == '.txt':
                return 'text/plain'
            else:
                return 'application/octet-stream'
        return content_type

    def get_files_to_upload(self) -> List[Tuple[Path, str]]:
        """
        Get list of files to upload with their GCS destination paths.

        Returns:
            List of tuples (local_file_path, gcs_destination_path)
        """
        files_to_upload = []

        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory {self.data_dir} does not exist")

        # Walk through all files in the data directory
        for root, dirs, files in os.walk(self.data_dir):
            root_path = Path(root)

            for file in files:
                local_file_path = root_path / file

                # Calculate relative path from data directory
                relative_path = local_file_path.relative_to(self.data_dir)

                # Convert to GCS path (use forward slashes)
                gcs_path = str(relative_path).replace(os.sep, '/')

                files_to_upload.append((local_file_path, gcs_path))

        return files_to_upload

    def upload_file(self, local_file_path: Path, gcs_path: str, dry_run: bool = False) -> bool:
        """
        Upload a single file to GCS.

        Args:
            local_file_path: Path to the local file
            gcs_path: Destination path in GCS bucket
            dry_run: If True, only print what would be uploaded

        Returns:
            True if successful (or dry run), False if failed
        """
        try:
            if dry_run:
                content_type = self.get_content_type(local_file_path)
                file_size = local_file_path.stat().st_size
                print(f"[DRY RUN] Would upload: {local_file_path} -> gs://{self.bucket_name}/{gcs_path}")
                print(f"          Content-Type: {content_type}, Size: {file_size} bytes")
                return True

            # Read file content
            with open(local_file_path, 'rb') as f:
                file_content = f.read()

            # Create blob and upload
            blob = self.bucket.blob(gcs_path)
            content_type = self.get_content_type(local_file_path)

            blob.upload_from_string(
                file_content,
                content_type=content_type
            )

            print(f"✓ Uploaded: {local_file_path} -> gs://{self.bucket_name}/{gcs_path}")
            return True

        except Exception as e:
            print(f"✗ Failed to upload {local_file_path}: {str(e)}")
            return False

    def verify_bucket_access(self) -> bool:
        """
        Verify that the bucket exists and is accessible.

        Returns:
            True if bucket is accessible, False otherwise
        """
        try:
            # Try to get bucket metadata
            self.bucket.reload()
            print(f"✓ Bucket gs://{self.bucket_name} is accessible")
            return True
        except exceptions.NotFound:
            print(f"✗ Bucket gs://{self.bucket_name} does not exist")
            return False
        except exceptions.Forbidden:
            print(f"✗ Access denied to bucket gs://{self.bucket_name}")
            return False
        except Exception as e:
            print(f"✗ Error accessing bucket gs://{self.bucket_name}: {str(e)}")
            return False

    def upload_all(self, dry_run: bool = False) -> bool:
        """
        Upload all files from the data directory to GCS.

        Args:
            dry_run: If True, only print what would be uploaded

        Returns:
            True if all uploads successful, False if any failed
        """
        # Verify bucket access
        if not self.verify_bucket_access():
            return False

        # Get files to upload
        try:
            files_to_upload = self.get_files_to_upload()
        except FileNotFoundError as e:
            print(f"✗ {str(e)}")
            return False

        if not files_to_upload:
            print(f"No files found in {self.data_dir}")
            return True

        print(f"\nFound {len(files_to_upload)} files to upload:")
        if dry_run:
            print("Running in DRY RUN mode - no actual uploads will be performed\n")
        else:
            print("")

        # Upload files
        success_count = 0
        total_count = len(files_to_upload)

        for local_file_path, gcs_path in files_to_upload:
            if self.upload_file(local_file_path, gcs_path, dry_run):
                success_count += 1

        print(f"\nUpload summary:")
        print(f"  Total files: {total_count}")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {total_count - success_count}")

        if not dry_run and success_count == total_count:
            print(f"\n✓ All files successfully uploaded to gs://{self.bucket_name}")
            print(f"\nYour ToS Monitor application should now have access to:")
            print(f"  - Configuration: gs://{self.bucket_name}/documents.json")
            print(f"  - Document data: gs://{self.bucket_name}/tos/")

        return success_count == total_count


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Upload ToS Monitor data to Google Cloud Storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python upload_to_gcs.py --bucket my-tos-bucket
  python upload_to_gcs.py --bucket my-tos-bucket --data-dir ./data --dry-run
  python upload_to_gcs.py --bucket my-tos-bucket --data-dir /path/to/data

Note:
  - Make sure you're authenticated with gcloud: gcloud auth application-default login
  - The bucket must already exist and you must have write permissions
        """
    )

    parser.add_argument(
        "--bucket",
        required=True,
        help="Google Cloud Storage bucket name"
    )

    parser.add_argument(
        "--data-dir",
        default="data",
        help="Local data directory to upload (default: data)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without actually uploading"
    )

    args = parser.parse_args()

    print("🚀 ToS Monitor Data Uploader")
    print("=" * 40)
    print(f"Source directory: {args.data_dir}")
    print(f"Target bucket: gs://{args.bucket}")
    print(f"Dry run: {args.dry_run}")
    print()

    try:
        uploader = ToSDataUploader(args.bucket, args.data_dir)
        success = uploader.upload_all(dry_run=args.dry_run)

        if success:
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Upload interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()