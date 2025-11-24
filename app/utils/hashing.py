"""
Content hashing utility for ToS Monitor.
Handles content hashing for change detection and comparison.
"""

import hashlib
import logging
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class ContentHasher:
    """
    Content hasher for generating and comparing document hashes.
    Provides multiple hashing strategies for different comparison needs.
    """

    def __init__(self):
        """Initialize content hasher."""
        self.hash_algorithm = hashlib.sha256

    def generate_hash(self, content: str, hash_type: str = "content") -> str:
        """
        Generate a hash for content.

        Args:
            content: Content to hash
            hash_type: Type of hash ("content", "structural", "fingerprint")

        Returns:
            str: Hexadecimal hash string
        """
        if not content:
            return ""

        try:
            if hash_type == "content":
                # Raw content hash - detects any change
                processed_content = content.strip()
            elif hash_type == "structural":
                # Structural hash - ignores minor formatting changes
                processed_content = self._normalize_for_structural_hash(content)
            elif hash_type == "fingerprint":
                # Fingerprint hash - ignores dates, minor changes
                processed_content = self._normalize_for_fingerprint_hash(content)
            else:
                raise ValueError(f"Unknown hash type: {hash_type}")

            # Generate hash
            hash_object = self.hash_algorithm(processed_content.encode('utf-8'))
            hash_hex = hash_object.hexdigest()

            logger.debug(f"Generated {hash_type} hash: {hash_hex[:16]}... for {len(content)} chars")
            return hash_hex

        except Exception as e:
            logger.error(f"Failed to generate {hash_type} hash: {str(e)}")
            return ""

    def _normalize_for_structural_hash(self, content: str) -> str:
        """
        Normalize content for structural hashing.
        Removes minor formatting differences while preserving structure.

        Args:
            content: Original content

        Returns:
            str: Normalized content for structural hashing
        """
        import re

        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content)

        # Normalize line breaks
        content = re.sub(r'\n\s*\n', '\n\n', content)

        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in content.split('\n')]
        content = '\n'.join(lines)

        # Normalize punctuation spacing
        content = re.sub(r' +([,.;:!?])', r'\1', content)
        content = re.sub(r'([,.;:!?])([A-Za-z])', r'\1 \2', content)

        return content.strip()

    def _normalize_for_fingerprint_hash(self, content: str) -> str:
        """
        Normalize content for fingerprint hashing.
        Removes dates, version numbers, and other dynamic content.

        Args:
            content: Original content

        Returns:
            str: Normalized content for fingerprint hashing
        """
        import re

        # Start with structural normalization
        content = self._normalize_for_structural_hash(content)

        # Remove date patterns
        date_patterns = [
            r'\b(?:updated|modified|revised)\s*:?\s*(?:on\s+)?'
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december)'
            r'\s+\d{1,2},?\s+\d{4}',

            r'\b(?:updated|modified|revised)\s*:?\s*(?:on\s+)?'
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
            r'\.?\s+\d{1,2},?\s+\d{4}',

            r'\b(?:updated|modified|revised)\s*:?\s*(?:on\s+)?'
            r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}',

            r'\b(?:updated|modified|revised)\s*:?\s*(?:on\s+)?'
            r'\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}',

            # Standalone dates
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)'
            r'\s+\d{1,2},?\s+\d{4}',

            r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b',
            r'\b\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}\b',
        ]

        for pattern in date_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)

        # Remove version numbers
        content = re.sub(r'\bversion\s+\d+(?:\.\d+)*', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\bv\d+(?:\.\d+)*', '', content, flags=re.IGNORECASE)

        # Remove copyright years
        content = re.sub(r'copyright\s+©?\s*\d{4}(?:-\d{4})?', 'copyright', content, flags=re.IGNORECASE)

        # Normalize excessive whitespace created by removals
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n+', '\n\n', content)

        return content.strip()

    def has_content_changed(self, old_hash: str, new_hash: str, hash_type: str = "content") -> bool:
        """
        Check if content has changed based on hash comparison.

        Args:
            old_hash: Previous hash
            new_hash: Current hash
            hash_type: Type of hash comparison

        Returns:
            bool: True if content has changed, False otherwise
        """
        if not old_hash or not new_hash:
            return True  # If we don't have hashes, assume changed

        changed = old_hash != new_hash

        if changed:
            logger.info(f"Content change detected ({hash_type} hash): {old_hash[:16]}... → {new_hash[:16]}...")
        else:
            logger.debug(f"No content change ({hash_type} hash): {old_hash[:16]}...")

        return changed

    def compare_hashes(self, old_hashes: Dict[str, str], new_hashes: Dict[str, str]) -> Dict[str, bool]:
        """
        Compare multiple hash types and determine what has changed.

        Args:
            old_hashes: Dictionary of previous hashes by type
            new_hashes: Dictionary of current hashes by type

        Returns:
            Dict[str, bool]: Dictionary indicating changes for each hash type
        """
        changes = {}

        # Check all hash types
        hash_types = set(old_hashes.keys()) | set(new_hashes.keys())

        for hash_type in hash_types:
            old_hash = old_hashes.get(hash_type, "")
            new_hash = new_hashes.get(hash_type, "")
            changes[hash_type] = self.has_content_changed(old_hash, new_hash, hash_type)

        return changes

    def generate_all_hashes(self, content: str) -> Dict[str, str]:
        """
        Generate all types of hashes for content.

        Args:
            content: Content to hash

        Returns:
            Dict[str, str]: Dictionary of hash type to hash value
        """
        return {
            "content": self.generate_hash(content, "content"),
            "structural": self.generate_hash(content, "structural"),
            "fingerprint": self.generate_hash(content, "fingerprint")
        }

    def should_create_snapshot(self, old_hashes: Dict[str, str], new_hashes: Dict[str, str]) -> bool:
        """
        Determine if a new snapshot should be created based on hash comparison.

        Args:
            old_hashes: Previous hashes
            new_hashes: Current hashes

        Returns:
            bool: True if snapshot should be created
        """
        changes = self.compare_hashes(old_hashes, new_hashes)

        # Create snapshot if structural content has changed
        # (ignore minor formatting changes but catch meaningful updates)
        return changes.get("structural", True)

    def should_generate_diff(self, old_hashes: Dict[str, str], new_hashes: Dict[str, str]) -> bool:
        """
        Determine if a diff should be generated based on hash comparison.

        Args:
            old_hashes: Previous hashes
            new_hashes: Current hashes

        Returns:
            bool: True if diff should be generated
        """
        changes = self.compare_hashes(old_hashes, new_hashes)

        # Generate diff if fingerprint has changed
        # (only for substantial content changes, ignore dates/versions)
        return changes.get("fingerprint", True)

    def create_metadata(self, content: str, url: str = "", additional_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create comprehensive metadata including all hash types.

        Args:
            content: Document content
            url: Document URL
            additional_metadata: Additional metadata to include

        Returns:
            Dict[str, Any]: Complete metadata dictionary
        """
        from datetime import datetime

        # Generate all hashes
        hashes = self.generate_all_hashes(content)

        # Create base metadata
        metadata = {
            "timestamp": datetime.utcnow().isoformat(),
            "url": url,
            "content_length": len(content),
            "content_hash": hashes["content"],
            "structural_hash": hashes["structural"],
            "fingerprint_hash": hashes["fingerprint"],
            "hashes": hashes
        }

        # Add additional metadata if provided
        if additional_metadata:
            metadata.update(additional_metadata)

        return metadata


def get_content_hasher() -> ContentHasher:
    """
    Get a configured content hasher instance.

    Returns:
        ContentHasher: Configured content hasher
    """
    return ContentHasher()