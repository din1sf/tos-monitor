"""
Google Cloud Storage integration for ToS Monitor.
Handles all storage operations including uploading, downloading, and managing file structure.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from google.cloud import storage
from google.api_core import exceptions


logger = logging.getLogger(__name__)


class CloudStorage:
    """
    Cloud Storage client for managing documents, snapshots, diffs, and configuration files.

    Storage Layout:
    - snapshots/<doc_id>/<timestamp>/
    - latest/<doc_id>/
    - diffs/<doc_id>/
    - config/
    - prompts/
    """

    def __init__(self, bucket_name: str):
        """Initialize Cloud Storage client with bucket name."""
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    async def upload_file(self, file_path: str, content: str, content_type: str = "text/plain") -> bool:
        """
        Upload a file to Cloud Storage.

        Args:
            file_path: The path where to store the file in the bucket
            content: The content to upload
            content_type: MIME type of the content

        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            blob = self.bucket.blob(file_path)
            blob.upload_from_string(content, content_type=content_type)
            logger.info(f"Successfully uploaded {file_path} to {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload {file_path}: {str(e)}")
            return False

    async def download_file(self, file_path: str) -> Optional[str]:
        """
        Download a file from Cloud Storage.

        Args:
            file_path: The path of the file in the bucket

        Returns:
            Optional[str]: File content if exists, None otherwise
        """
        try:
            blob = self.bucket.blob(file_path)
            if not blob.exists():
                logger.warning(f"File {file_path} does not exist in {self.bucket_name}")
                return None

            content = blob.download_as_text()
            logger.debug(f"Successfully downloaded {file_path} from {self.bucket_name}")
            return content
        except Exception as e:
            logger.error(f"Failed to download {file_path}: {str(e)}")
            return None

    async def list_files(self, prefix: str = "", delimiter: str = None) -> List[str]:
        """
        List files in Cloud Storage with optional prefix.

        Args:
            prefix: Prefix to filter files
            delimiter: Delimiter for grouping (e.g., "/" for directories)

        Returns:
            List[str]: List of file paths
        """
        try:
            blobs = self.client.list_blobs(
                self.bucket_name,
                prefix=prefix,
                delimiter=delimiter
            )
            file_paths = [blob.name for blob in blobs]
            logger.debug(f"Listed {len(file_paths)} files with prefix '{prefix}'")
            return file_paths
        except Exception as e:
            logger.error(f"Failed to list files with prefix '{prefix}': {str(e)}")
            return []

    async def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in Cloud Storage.

        Args:
            file_path: The path of the file to check

        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            blob = self.bucket.blob(file_path)
            exists = blob.exists()
            logger.debug(f"File {file_path} exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check existence of {file_path}: {str(e)}")
            return False

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from Cloud Storage.

        Args:
            file_path: The path of the file to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            blob = self.bucket.blob(file_path)
            blob.delete()
            logger.info(f"Successfully deleted {file_path} from {self.bucket_name}")
            return True
        except exceptions.NotFound:
            logger.warning(f"File {file_path} does not exist, cannot delete")
            return False
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {str(e)}")
            return False

    # Document snapshot operations
    async def store_document_snapshot(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> str:
        """
        Store a document snapshot with timestamp.

        Args:
            doc_id: Document identifier
            content: Document content
            metadata: Document metadata (url, timestamp, hash, etc.)

        Returns:
            str: The timestamp used for this snapshot
        """
        timestamp = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")

        # Store the document content
        content_path = f"snapshots/{doc_id}/{timestamp}/content.txt"
        await self.upload_file(content_path, content)

        # Store metadata
        metadata_path = f"snapshots/{doc_id}/{timestamp}/metadata.json"
        await self.upload_file(metadata_path, json.dumps(metadata, indent=2), "application/json")

        # Update latest pointer
        latest_path = f"latest/{doc_id}/content.txt"
        await self.upload_file(latest_path, content)

        latest_metadata_path = f"latest/{doc_id}/metadata.json"
        await self.upload_file(latest_metadata_path, json.dumps(metadata, indent=2), "application/json")

        logger.info(f"Stored snapshot for document {doc_id} at timestamp {timestamp}")
        return timestamp

    async def get_latest_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest version of a document.

        Args:
            doc_id: Document identifier

        Returns:
            Optional[Dict[str, Any]]: Dictionary with 'content' and 'metadata' keys, or None
        """
        try:
            content = await self.download_file(f"latest/{doc_id}/content.txt")
            metadata_str = await self.download_file(f"latest/{doc_id}/metadata.json")

            if content is None or metadata_str is None:
                return None

            metadata = json.loads(metadata_str)
            return {
                "content": content,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"Failed to get latest document for {doc_id}: {str(e)}")
            return None

    async def get_document_snapshots(self, doc_id: str) -> List[str]:
        """
        Get all snapshot timestamps for a document.

        Args:
            doc_id: Document identifier

        Returns:
            List[str]: List of timestamps (sorted newest first)
        """
        prefix = f"snapshots/{doc_id}/"
        files = await self.list_files(prefix)

        # Extract timestamps from file paths
        timestamps = set()
        for file_path in files:
            parts = file_path.split("/")
            if len(parts) >= 3:
                timestamps.add(parts[2])

        # Sort timestamps (newest first)
        sorted_timestamps = sorted(list(timestamps), reverse=True)
        return sorted_timestamps

    # Diff operations
    async def store_diff(self, doc_id: str, diff_content: str, metadata: Dict[str, Any]) -> str:
        """
        Store a diff result for a document.

        Args:
            doc_id: Document identifier
            diff_content: LLM-generated diff summary
            metadata: Diff metadata (timestamps, model used, etc.)

        Returns:
            str: The timestamp used for this diff
        """
        timestamp = datetime.utcnow().isoformat().replace(":", "-").replace(".", "-")

        # Store the diff content
        diff_path = f"diffs/{doc_id}/{timestamp}/diff.txt"
        await self.upload_file(diff_path, diff_content)

        # Store metadata
        metadata_path = f"diffs/{doc_id}/{timestamp}/metadata.json"
        await self.upload_file(metadata_path, json.dumps(metadata, indent=2), "application/json")

        # Update latest diff pointer
        latest_diff_path = f"latest/{doc_id}/diff.txt"
        await self.upload_file(latest_diff_path, diff_content)

        latest_diff_metadata_path = f"latest/{doc_id}/diff_metadata.json"
        await self.upload_file(latest_diff_metadata_path, json.dumps(metadata, indent=2), "application/json")

        logger.info(f"Stored diff for document {doc_id} at timestamp {timestamp}")
        return timestamp

    async def get_latest_diff(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest diff for a document.

        Args:
            doc_id: Document identifier

        Returns:
            Optional[Dict[str, Any]]: Dictionary with 'content' and 'metadata' keys, or None
        """
        try:
            content = await self.download_file(f"latest/{doc_id}/diff.txt")
            metadata_str = await self.download_file(f"latest/{doc_id}/diff_metadata.json")

            if content is None or metadata_str is None:
                return None

            metadata = json.loads(metadata_str)
            return {
                "content": content,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"Failed to get latest diff for {doc_id}: {str(e)}")
            return None

    async def get_diff_by_timestamp(self, doc_id: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific diff by timestamp.

        Args:
            doc_id: Document identifier
            timestamp: Diff timestamp

        Returns:
            Optional[Dict[str, Any]]: Dictionary with 'content' and 'metadata' keys, or None
        """
        try:
            content = await self.download_file(f"diffs/{doc_id}/{timestamp}/diff.txt")
            metadata_str = await self.download_file(f"diffs/{doc_id}/{timestamp}/metadata.json")

            if content is None or metadata_str is None:
                return None

            metadata = json.loads(metadata_str)
            return {
                "content": content,
                "metadata": metadata
            }
        except Exception as e:
            logger.error(f"Failed to get diff {timestamp} for {doc_id}: {str(e)}")
            return None

    # Configuration operations
    async def load_config(self, config_name: str = "documents.json") -> Optional[Dict[str, Any]]:
        """
        Load configuration from storage.

        Args:
            config_name: Name of the configuration file

        Returns:
            Optional[Dict[str, Any]]: Configuration data or None
        """
        try:
            config_path = f"config/{config_name}"
            config_str = await self.download_file(config_path)

            if config_str is None:
                return None

            return json.loads(config_str)
        except Exception as e:
            logger.error(f"Failed to load config {config_name}: {str(e)}")
            return None

    async def save_config(self, config_data: Dict[str, Any], config_name: str = "documents.json") -> bool:
        """
        Save configuration to storage.

        Args:
            config_data: Configuration data to save
            config_name: Name of the configuration file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            config_path = f"config/{config_name}"
            return await self.upload_file(
                config_path,
                json.dumps(config_data, indent=2),
                "application/json"
            )
        except Exception as e:
            logger.error(f"Failed to save config {config_name}: {str(e)}")
            return False

    async def load_prompt(self, prompt_name: str = "default_comparison.txt") -> Optional[str]:
        """
        Load a prompt template from storage.

        Args:
            prompt_name: Name of the prompt file

        Returns:
            Optional[str]: Prompt content or None
        """
        prompt_path = f"prompts/{prompt_name}"
        return await self.download_file(prompt_path)

    async def save_prompt(self, prompt_content: str, prompt_name: str = "default_comparison.txt") -> bool:
        """
        Save a prompt template to storage.

        Args:
            prompt_content: Prompt content
            prompt_name: Name of the prompt file

        Returns:
            bool: True if successful, False otherwise
        """
        prompt_path = f"prompts/{prompt_name}"
        return await self.upload_file(prompt_path, prompt_content)


def get_storage_client() -> CloudStorage:
    """
    Get a configured storage client instance.

    Returns:
        CloudStorage: Configured storage client
    """
    bucket_name = os.getenv("STORAGE_BUCKET")
    if not bucket_name:
        raise ValueError("STORAGE_BUCKET environment variable is required")

    return CloudStorage(bucket_name)