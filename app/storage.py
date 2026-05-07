"""
Google Cloud Storage integration for ToS Monitor.
Handles all storage operations including uploading, downloading, and managing file structure.
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, Protocol
from datetime import datetime

# Google Cloud Storage imports (optional for local mode)
try:
    from google.cloud import storage
    from google.api_core import exceptions
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None
    exceptions = None


logger = logging.getLogger(__name__)


class StorageInterface(Protocol):
    """Protocol defining the storage interface for both cloud and local implementations."""

    async def upload_file(self, file_path: str, content: str, content_type: str = "text/plain") -> bool:
        """Upload a file with the given content."""
        ...

    async def download_file(self, file_path: str) -> Optional[str]:
        """Download a file and return its content."""
        ...

    async def list_files(self, prefix: str = "", delimiter: str = None) -> List[str]:
        """List files with optional prefix."""
        ...

    async def file_exists(self, file_path: str) -> bool:
        """Check if a file exists."""
        ...

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file."""
        ...

    async def store_document_snapshot(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> str:
        """Store a document snapshot with timestamp."""
        ...

    async def get_latest_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest version of a document."""
        ...

    async def get_document_snapshots(self, doc_id: str) -> List[str]:
        """Get all snapshot timestamps for a document."""
        ...

    async def store_diff(self, doc_id: str, diff_content: str, metadata: Dict[str, Any]) -> str:
        """Store a diff result for a document."""
        ...

    async def get_latest_diff(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest diff for a document."""
        ...

    async def get_diff_by_timestamp(self, doc_id: str, timestamp: str) -> Optional[Dict[str, Any]]:
        """Get a specific diff by timestamp."""
        ...

    async def load_config(self, config_name: str = "documents.json") -> Optional[Dict[str, Any]]:
        """Load configuration from storage."""
        ...

    async def save_config(self, config_data: Dict[str, Any], config_name: str = "documents.json") -> bool:
        """Save configuration to storage."""
        ...

    async def load_prompt(self, prompt_name: str = "prompt.txt") -> Optional[str]:
        """Load a prompt template from storage."""
        ...

    async def save_prompt(self, prompt_content: str, prompt_name: str = "prompt.txt") -> bool:
        """Save a prompt template to storage."""
        ...

    # ToS-specific storage methods
    async def store_tos_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store ToS document using simplified structure with current/last/prev/dated files.

        Args:
            doc_id: Document identifier
            content: Document content
            metadata: Document metadata

        Returns:
            Dict with processing results (changes_detected, snapshot_created, etc.)
        """
        ...

    async def get_tos_document(self, doc_id: str, version: str = "last") -> Optional[Dict[str, Any]]:
        """
        Get ToS document by version.

        Args:
            doc_id: Document identifier
            version: "current", "last", "prev", or date (e.g., "2025-11-25")

        Returns:
            Dict with content and metadata, or None if not found
        """
        ...


class CloudStorage:
    """
    Cloud Storage client for managing documents, snapshots, diffs, and configuration files.

    Storage Layout:
    - tos/<doc_id>/ (current.txt, last.txt, prev.txt, <date>.txt)
    - documents.json (configuration)
    - prompt.txt (prompt template)
    """

    def __init__(self, bucket_name: str):
        """Initialize Cloud Storage client with bucket name."""
        if not GCS_AVAILABLE:
            raise ImportError(
                "Google Cloud Storage is not available. Install with: pip install google-cloud-storage"
            )

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
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")

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
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")

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
            config_path = config_name
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
            config_path = f"tos/{config_name}"
            return await self.upload_file(
                config_path,
                json.dumps(config_data, indent=2),
                "application/json"
            )
        except Exception as e:
            logger.error(f"Failed to save config {config_name}: {str(e)}")
            return False

    async def load_prompt(self, prompt_name: str = "prompt.txt") -> Optional[str]:
        """
        Load a prompt template from storage.

        Args:
            prompt_name: Name of the prompt file

        Returns:
            Optional[str]: Prompt content or None
        """
        prompt_path = prompt_name
        return await self.download_file(prompt_path)

    async def save_prompt(self, prompt_content: str, prompt_name: str = "prompt.txt") -> bool:
        """
        Save a prompt template to storage.

        Args:
            prompt_content: Prompt content
            prompt_name: Name of the prompt file

        Returns:
            bool: True if successful, False otherwise
        """
        prompt_path = prompt_name
        return await self.upload_file(prompt_path, prompt_content)

    # ToS-specific storage methods
    async def store_tos_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store ToS document using simplified structure with current/last/prev/dated files.
        Flow: current.txt -> compare with last.txt -> if diff: last->prev, current->last, current->date
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")

        # Always store as current first
        current_content_path = f"tos/{doc_id}/current.txt"
        current_metadata_path = f"tos/{doc_id}/current.json"

        await self.upload_file(current_content_path, content)
        await self.upload_file(current_metadata_path, json.dumps(metadata, indent=2), "application/json")

        # Check if last.txt exists and compare with the pointed-to content
        last_date_path = f"tos/{doc_id}/last.txt"

        changes_detected = True
        snapshot_created = False

        try:
            last_date_str = await self.download_file(last_date_path)

            if last_date_str:
                last_date = last_date_str.strip()
                # Load the last content using the date pointer
                last_content_path = f"tos/{doc_id}/{last_date}.txt"
                last_metadata_path = f"tos/{doc_id}/{last_date}.json"

                last_content = await self.download_file(last_content_path)
                last_metadata_str = await self.download_file(last_metadata_path)

                if last_content and last_metadata_str:
                    last_metadata = json.loads(last_metadata_str)
                    old_hashes = last_metadata.get("hashes", {})
                    new_hashes = metadata.get("hashes", {})

                    # Compare structural hashes for change detection
                    if old_hashes.get("structural") == new_hashes.get("structural"):
                        changes_detected = False

        except Exception as e:
            logger.info(f"No previous version found for {doc_id} or error reading: {str(e)}")
            # First time or error reading - treat as changes detected

        # Handle changed file creation/removal
        changed_file_path = f"tos/{doc_id}/changed"

        if changes_detected:
            # Update pointer files and create dated snapshot
            try:
                # Read current last date to move to prev
                last_date_str = await self.download_file(last_date_path)
                if last_date_str:
                    old_last_date = last_date_str.strip()
                    # Move last date -> prev date
                    prev_date_path = f"tos/{doc_id}/prev.txt"
                    await self.upload_file(prev_date_path, old_last_date)
            except Exception:
                pass  # No previous last date to backup

            # Set current timestamp as new last date
            await self.upload_file(last_date_path, timestamp)

            # Create dated snapshot
            dated_content_path = f"tos/{doc_id}/{timestamp}.txt"
            dated_metadata_path = f"tos/{doc_id}/{timestamp}.json"
            await self.upload_file(dated_content_path, content)
            await self.upload_file(dated_metadata_path, json.dumps(metadata, indent=2), "application/json")

            # Create changed file to indicate changes were detected
            await self.upload_file(changed_file_path, timestamp)

            snapshot_created = True
            logger.info(f"Created ToS snapshot for {doc_id} at {timestamp} (pointer system)")
        else:
            # Remove changed file if no changes detected
            await self.delete_file(changed_file_path)
            logger.info(f"No changes detected for {doc_id}, keeping current only")

        return {
            "changes_detected": changes_detected,
            "snapshot_created": snapshot_created,
            "timestamp": timestamp if snapshot_created else None
        }

    async def get_tos_document(self, doc_id: str, version: str = "last") -> Optional[Dict[str, Any]]:
        """Get ToS document by version (current, last, prev, or date)."""
        try:
            if version == "current":
                content_path = f"tos/{doc_id}/current.txt"
                metadata_path = f"tos/{doc_id}/current.json"
            elif version in ["last", "prev"]:
                # Use pointer files to get the actual date
                pointer_path = f"tos/{doc_id}/{version}.txt"
                date_str = await self.download_file(pointer_path)
                if not date_str:
                    return None
                actual_date = date_str.strip()
                content_path = f"tos/{doc_id}/{actual_date}.txt"
                metadata_path = f"tos/{doc_id}/{actual_date}.json"
            else:
                # Assume it's a date
                content_path = f"tos/{doc_id}/{version}.txt"
                metadata_path = f"tos/{doc_id}/{version}.json"

            content = await self.download_file(content_path)
            metadata_str = await self.download_file(metadata_path)

            if content and metadata_str:
                metadata = json.loads(metadata_str)
                return {
                    "content": content,
                    "metadata": metadata
                }
        except Exception as e:
            logger.error(f"Error getting ToS document {doc_id} version {version}: {str(e)}")

        return None


class LocalStorage:
    """
    Local file system storage client for managing documents, snapshots, diffs, and configuration files.

    Storage Layout:
    - data/tos/<doc_id>/ (current.txt, last.txt, prev.txt, <date>.txt)
    - data/documents.json (configuration)
    - data/prompt.txt (LLM prompt for document comparison)
    """

    def __init__(self, base_path: str = "./data"):
        """Initialize Local Storage with base directory path."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Create required subdirectories for new structure
        subdirs = ["tos"]
        for subdir in subdirs:
            (self.base_path / subdir).mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, file_path: str) -> Path:
        """Get the full filesystem path for a given file path."""
        return self.base_path / file_path

    async def upload_file(self, file_path: str, content: str, content_type: str = "text/plain") -> bool:
        """
        Save a file to local filesystem.

        Args:
            file_path: The relative path where to store the file
            content: The content to save
            content_type: MIME type of the content (ignored for local storage)

        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            full_path = self._get_full_path(file_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Use async file I/O
            await asyncio.to_thread(full_path.write_text, content, encoding='utf-8')
            logger.info(f"Successfully saved {file_path} to local storage")
            return True
        except Exception as e:
            logger.error(f"Failed to save {file_path}: {str(e)}")
            return False

    async def download_file(self, file_path: str) -> Optional[str]:
        """
        Read a file from local filesystem.

        Args:
            file_path: The relative path of the file

        Returns:
            Optional[str]: File content if exists, None otherwise
        """
        try:
            full_path = self._get_full_path(file_path)
            if not full_path.exists():
                logger.warning(f"File {file_path} does not exist in local storage")
                return None

            content = await asyncio.to_thread(full_path.read_text, encoding='utf-8')
            logger.debug(f"Successfully read {file_path} from local storage")
            return content
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {str(e)}")
            return None

    async def list_files(self, prefix: str = "", delimiter: str = None) -> List[str]:
        """
        List files in local filesystem with optional prefix.

        Args:
            prefix: Prefix to filter files (relative path)
            delimiter: Delimiter for grouping (e.g., "/" for directories)

        Returns:
            List[str]: List of relative file paths
        """
        try:
            search_path = self.base_path / prefix if prefix else self.base_path

            if not search_path.exists():
                return []

            file_paths = []
            if search_path.is_file():
                # If prefix points to a specific file
                file_paths = [prefix]
            else:
                # Recursively find all files under the prefix path
                for file_path in search_path.rglob("*"):
                    if file_path.is_file():
                        # Get relative path from base_path
                        rel_path = file_path.relative_to(self.base_path)
                        file_paths.append(str(rel_path).replace("\\", "/"))  # Normalize path separators

            # Apply delimiter logic if specified (e.g., group by directories)
            if delimiter:
                filtered_paths = []
                for path in file_paths:
                    if delimiter in path:
                        # Only include direct children, not nested files
                        parts = path.split(delimiter)
                        if len(parts) <= prefix.count(delimiter) + 2:
                            filtered_paths.append(path)
                file_paths = filtered_paths

            logger.debug(f"Listed {len(file_paths)} files with prefix '{prefix}'")
            return sorted(file_paths)
        except Exception as e:
            logger.error(f"Failed to list files with prefix '{prefix}': {str(e)}")
            return []

    async def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in local filesystem.

        Args:
            file_path: The relative path of the file to check

        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            full_path = self._get_full_path(file_path)
            exists = full_path.exists() and full_path.is_file()
            logger.debug(f"File {file_path} exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Failed to check existence of {file_path}: {str(e)}")
            return False

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from local filesystem.

        Args:
            file_path: The relative path of the file to delete

        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            full_path = self._get_full_path(file_path)
            if not full_path.exists():
                logger.warning(f"File {file_path} does not exist, cannot delete")
                return False

            await asyncio.to_thread(full_path.unlink)
            logger.info(f"Successfully deleted {file_path} from local storage")
            return True
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
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")

        # Store the document content
        content_path = f"snapshots/{doc_id}/{timestamp}/content.txt"
        await self.upload_file(content_path, content)

        # Store metadata
        metadata_path = f"snapshots/{doc_id}/{timestamp}/metadata.json"
        await self.upload_file(metadata_path, json.dumps(metadata, indent=2))

        # Update latest pointer
        latest_path = f"latest/{doc_id}/content.txt"
        await self.upload_file(latest_path, content)

        latest_metadata_path = f"latest/{doc_id}/metadata.json"
        await self.upload_file(latest_metadata_path, json.dumps(metadata, indent=2))

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
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")

        # Store the diff content
        diff_path = f"diffs/{doc_id}/{timestamp}/diff.txt"
        await self.upload_file(diff_path, diff_content)

        # Store metadata
        metadata_path = f"diffs/{doc_id}/{timestamp}/metadata.json"
        await self.upload_file(metadata_path, json.dumps(metadata, indent=2))

        # Update latest diff pointer
        latest_diff_path = f"latest/{doc_id}/diff.txt"
        await self.upload_file(latest_diff_path, diff_content)

        latest_diff_metadata_path = f"latest/{doc_id}/diff_metadata.json"
        await self.upload_file(latest_diff_metadata_path, json.dumps(metadata, indent=2))

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
        Load configuration from local storage.

        Args:
            config_name: Name of the configuration file

        Returns:
            Optional[Dict[str, Any]]: Configuration data or None
        """
        try:
            config_path = config_name
            config_str = await self.download_file(config_path)

            if config_str is None:
                return None

            return json.loads(config_str)
        except Exception as e:
            logger.error(f"Failed to load config {config_name}: {str(e)}")
            return None

    async def save_config(self, config_data: Dict[str, Any], config_name: str = "documents.json") -> bool:
        """
        Save configuration to local storage.

        Args:
            config_data: Configuration data to save
            config_name: Name of the configuration file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            config_path = config_name
            return await self.upload_file(
                config_path,
                json.dumps(config_data, indent=2)
            )
        except Exception as e:
            logger.error(f"Failed to save config {config_name}: {str(e)}")
            return False

    async def load_prompt(self, prompt_name: str = "prompt.txt") -> Optional[str]:
        """
        Load a prompt template from local storage.

        Args:
            prompt_name: Name of the prompt file (defaults to 'prompt.txt')

        Returns:
            Optional[str]: Prompt content or None
        """
        # Always use 'prompt.txt' in data root, ignoring the prompt_name parameter for simplicity
        prompt_path = "prompt.txt"
        return await self.download_file(prompt_path)

    async def save_prompt(self, prompt_content: str, prompt_name: str = "prompt.txt") -> bool:
        """
        Save a prompt template to local storage.

        Args:
            prompt_content: Prompt content
            prompt_name: Name of the prompt file (defaults to 'prompt.txt')

        Returns:
            bool: True if successful, False otherwise
        """
        # Always use 'prompt.txt' in data root, ignoring the prompt_name parameter for simplicity
        prompt_path = "prompt.txt"
        return await self.upload_file(prompt_path, prompt_content)

    # ToS-specific storage methods
    async def store_tos_document(self, doc_id: str, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store ToS document using simplified structure with current/last/prev/dated files.
        Flow: current.txt -> compare with last.txt -> if diff: last->prev, current->last, current->date
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")

        # Always store as current first
        current_content_path = f"tos/{doc_id}/current.txt"
        current_metadata_path = f"tos/{doc_id}/current.json"

        await self.upload_file(current_content_path, content)
        await self.upload_file(current_metadata_path, json.dumps(metadata, indent=2))

        # Check if last.txt exists and compare with the pointed-to content
        last_date_path = f"tos/{doc_id}/last.txt"

        changes_detected = True
        snapshot_created = False

        try:
            last_date_str = await self.download_file(last_date_path)

            if last_date_str:
                last_date = last_date_str.strip()
                # Load the last content using the date pointer
                last_content_path = f"tos/{doc_id}/{last_date}.txt"
                last_metadata_path = f"tos/{doc_id}/{last_date}.json"

                last_content = await self.download_file(last_content_path)
                last_metadata_str = await self.download_file(last_metadata_path)

                if last_content and last_metadata_str:
                    last_metadata = json.loads(last_metadata_str)
                    old_hashes = last_metadata.get("hashes", {})
                    new_hashes = metadata.get("hashes", {})

                    # Compare structural hashes for change detection
                    if old_hashes.get("structural") == new_hashes.get("structural"):
                        changes_detected = False

        except Exception as e:
            logger.info(f"No previous version found for {doc_id} or error reading: {str(e)}")
            # First time or error reading - treat as changes detected

        # Handle changed file creation/removal
        changed_file_path = f"tos/{doc_id}/changed"

        if changes_detected:
            # Update pointer files and create dated snapshot
            try:
                # Read current last date to move to prev
                last_date_str = await self.download_file(last_date_path)
                if last_date_str:
                    old_last_date = last_date_str.strip()
                    # Move last date -> prev date
                    prev_date_path = f"tos/{doc_id}/prev.txt"
                    await self.upload_file(prev_date_path, old_last_date)
            except Exception:
                pass  # No previous last date to backup

            # Set current timestamp as new last date
            await self.upload_file(last_date_path, timestamp)

            # Create dated snapshot
            dated_content_path = f"tos/{doc_id}/{timestamp}.txt"
            dated_metadata_path = f"tos/{doc_id}/{timestamp}.json"
            await self.upload_file(dated_content_path, content)
            await self.upload_file(dated_metadata_path, json.dumps(metadata, indent=2))

            # Create changed file to indicate changes were detected
            await self.upload_file(changed_file_path, timestamp)

            snapshot_created = True
            logger.info(f"Created ToS snapshot for {doc_id} at {timestamp} (pointer system)")
        else:
            # Remove changed file if no changes detected
            await self.delete_file(changed_file_path)
            logger.info(f"No changes detected for {doc_id}, keeping current only")

        return {
            "changes_detected": changes_detected,
            "snapshot_created": snapshot_created,
            "timestamp": timestamp if snapshot_created else None
        }

    async def get_tos_document(self, doc_id: str, version: str = "last") -> Optional[Dict[str, Any]]:
        """Get ToS document by version (current, last, prev, or date)."""
        try:
            if version == "current":
                content_path = f"tos/{doc_id}/current.txt"
                metadata_path = f"tos/{doc_id}/current.json"
            elif version in ["last", "prev"]:
                # Use pointer files to get the actual date
                pointer_path = f"tos/{doc_id}/{version}.txt"
                date_str = await self.download_file(pointer_path)
                if not date_str:
                    return None
                actual_date = date_str.strip()
                content_path = f"tos/{doc_id}/{actual_date}.txt"
                metadata_path = f"tos/{doc_id}/{actual_date}.json"
            else:
                # Assume it's a date
                content_path = f"tos/{doc_id}/{version}.txt"
                metadata_path = f"tos/{doc_id}/{version}.json"

            content = await self.download_file(content_path)
            metadata_str = await self.download_file(metadata_path)

            if content and metadata_str:
                metadata = json.loads(metadata_str)
                return {
                    "content": content,
                    "metadata": metadata
                }
        except Exception as e:
            logger.error(f"Error getting ToS document {doc_id} version {version}: {str(e)}")

        return None


def get_storage_client() -> StorageInterface:
    """
    Get a configured storage client instance.

    Supports both local and cloud storage modes:
    - Local mode: Set STORAGE_MODE=local and optionally LOCAL_STORAGE_PATH
    - Cloud mode: Set STORAGE_MODE=cloud (default) and STORAGE_BUCKET

    Returns:
        StorageInterface: Configured storage client (LocalStorage or CloudStorage)
    """
    storage_mode = os.getenv("STORAGE_MODE", "cloud").lower()

    if storage_mode == "local":
        # Local storage mode
        local_path = os.getenv("LOCAL_STORAGE_PATH", "./data")
        logger.info(f"Using local storage mode with path: {local_path}")
        return LocalStorage(local_path)

    elif storage_mode == "cloud":
        # Cloud storage mode (existing behavior)
        if not GCS_AVAILABLE:
            raise ImportError(
                "Google Cloud Storage is not available. Install with: pip install google-cloud-storage "
                "or switch to local mode with STORAGE_MODE=local"
            )

        bucket_name = os.getenv("STORAGE_BUCKET")
        if not bucket_name:
            raise ValueError("STORAGE_BUCKET environment variable is required for cloud mode")

        logger.info(f"Using cloud storage mode with bucket: {bucket_name}")
        return CloudStorage(bucket_name)

    else:
        raise ValueError(
            f"Invalid STORAGE_MODE '{storage_mode}'. Must be 'local' or 'cloud'"
        )