"""
Get diffs endpoint for ToS Monitor.
Handles retrieval of generated document diffs and summaries.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.storage import get_storage_client


logger = logging.getLogger(__name__)
router = APIRouter()


class DocumentDiff(BaseModel):
    """Model for individual document diff information."""
    document_id: str
    document_name: str
    url: Optional[str] = None
    latest_diff_timestamp: Optional[str] = None
    previous_snapshot_timestamp: Optional[str] = None
    current_snapshot_timestamp: Optional[str] = None
    generated_at: Optional[str] = None
    has_diff: bool = False


class DiffContent(BaseModel):
    """Model for diff content and metadata."""
    document_id: str
    document_name: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str


class DiffListResponse(BaseModel):
    """Response model for listing all diffs."""
    success: bool
    document_count: int
    documents: List[DocumentDiff]


@router.get("/diffs", response_model=DiffListResponse)
async def list_diffs(
    has_changes_only: bool = Query(False, description="Only show documents with diffs")
):
    """
    List all documents with their latest diff information.

    Args:
        has_changes_only: If True, only return documents that have diffs

    Returns:
        DiffListResponse: List of documents and their diff status
    """
    try:
        storage = get_storage_client()

        # Load document configuration
        config = await storage.load_config("documents.json")
        if not config:
            raise HTTPException(
                status_code=500,
                detail="Could not load document configuration from storage"
            )

        documents = config.get("documents", [])
        if not documents:
            return DiffListResponse(
                success=True,
                document_count=0,
                documents=[]
            )

        # Process each document
        document_diffs = []
        for doc_config in documents:
            doc_id = doc_config.get("id")
            doc_name = doc_config.get("name", doc_id)
            url = doc_config.get("url")

            if not doc_id:
                continue

            # Get latest diff information
            diff_info = await get_document_diff_info(storage, doc_id, doc_name, url)

            # Filter based on has_changes_only flag
            if has_changes_only and not diff_info.has_diff:
                continue

            document_diffs.append(diff_info)

        logger.info(f"Listed {len(document_diffs)} document diffs")

        return DiffListResponse(
            success=True,
            document_count=len(document_diffs),
            documents=document_diffs
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing diffs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/diffs/{document_id}", response_model=DiffContent)
async def get_latest_diff(document_id: str):
    """
    Get the latest diff for a specific document.

    Args:
        document_id: ID of the document

    Returns:
        DiffContent: Latest diff content and metadata
    """
    try:
        storage = get_storage_client()

        # Get latest diff
        diff_data = await storage.get_latest_diff(document_id)
        if not diff_data:
            raise HTTPException(
                status_code=404,
                detail=f"No diff found for document: {document_id}"
            )

        content = diff_data.get("content", "")
        metadata = diff_data.get("metadata", {})

        # Get document name from config
        doc_name = await get_document_name(storage, document_id)

        logger.info(f"Retrieved latest diff for document: {document_id}")

        return DiffContent(
            document_id=document_id,
            document_name=doc_name,
            content=content,
            metadata=metadata,
            timestamp=metadata.get("generated_at", "")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest diff for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/diffs/{document_id}/{timestamp}", response_model=DiffContent)
async def get_diff_by_timestamp(document_id: str, timestamp: str):
    """
    Get a specific diff by timestamp.

    Args:
        document_id: ID of the document
        timestamp: Timestamp of the specific diff

    Returns:
        DiffContent: Diff content and metadata for the specific timestamp
    """
    try:
        storage = get_storage_client()

        # Get specific diff
        diff_data = await storage.get_diff_by_timestamp(document_id, timestamp)
        if not diff_data:
            raise HTTPException(
                status_code=404,
                detail=f"No diff found for document: {document_id} at timestamp: {timestamp}"
            )

        content = diff_data.get("content", "")
        metadata = diff_data.get("metadata", {})

        # Get document name from config
        doc_name = await get_document_name(storage, document_id)

        logger.info(f"Retrieved diff for document: {document_id} at timestamp: {timestamp}")

        return DiffContent(
            document_id=document_id,
            document_name=doc_name,
            content=content,
            metadata=metadata,
            timestamp=timestamp
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting diff for {document_id} at {timestamp}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/diffs/{document_id}/history")
async def get_diff_history(document_id: str):
    """
    Get diff history for a document.

    Args:
        document_id: ID of the document

    Returns:
        Dict: List of available diff timestamps and metadata
    """
    try:
        storage = get_storage_client()

        # List all diffs for this document
        prefix = f"diffs/{document_id}/"
        files = await storage.list_files(prefix)

        # Extract timestamps from file paths
        timestamps = set()
        for file_path in files:
            parts = file_path.split("/")
            if len(parts) >= 3:
                timestamps.add(parts[2])

        # Sort timestamps (newest first)
        sorted_timestamps = sorted(list(timestamps), reverse=True)

        # Get metadata for each diff
        history = []
        for timestamp in sorted_timestamps:
            try:
                metadata_str = await storage.download_file(f"diffs/{document_id}/{timestamp}/metadata.json")
                if metadata_str:
                    metadata = json.loads(metadata_str)
                    history.append({
                        "timestamp": timestamp,
                        "generated_at": metadata.get("generated_at", ""),
                        "previous_snapshot": metadata.get("previous_snapshot_timestamp", ""),
                        "current_snapshot": metadata.get("current_snapshot_timestamp", ""),
                        "llm_model": metadata.get("llm_model", "")
                    })
            except Exception as e:
                logger.warning(f"Could not load metadata for diff {document_id}/{timestamp}: {str(e)}")

        # Get document name
        doc_name = await get_document_name(storage, document_id)

        logger.info(f"Retrieved diff history for document: {document_id} ({len(history)} entries)")

        return {
            "success": True,
            "document_id": document_id,
            "document_name": doc_name,
            "diff_count": len(history),
            "history": history
        }

    except Exception as e:
        logger.error(f"Error getting diff history for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def get_document_diff_info(storage, doc_id: str, doc_name: str, url: str) -> DocumentDiff:
    """
    Get diff information for a document.

    Args:
        storage: Storage client
        doc_id: Document ID
        doc_name: Document name
        url: Document URL

    Returns:
        DocumentDiff: Document diff information
    """
    try:
        # Get latest diff
        diff_data = await storage.get_latest_diff(doc_id)

        if not diff_data:
            return DocumentDiff(
                document_id=doc_id,
                document_name=doc_name,
                url=url,
                has_diff=False
            )

        metadata = diff_data.get("metadata", {})

        return DocumentDiff(
            document_id=doc_id,
            document_name=doc_name,
            url=url,
            latest_diff_timestamp=metadata.get("generated_at", ""),
            previous_snapshot_timestamp=metadata.get("previous_snapshot_timestamp", ""),
            current_snapshot_timestamp=metadata.get("current_snapshot_timestamp", ""),
            generated_at=metadata.get("generated_at", ""),
            has_diff=True
        )

    except Exception as e:
        logger.warning(f"Error getting diff info for {doc_id}: {str(e)}")
        return DocumentDiff(
            document_id=doc_id,
            document_name=doc_name,
            url=url,
            has_diff=False
        )


async def get_document_name(storage, doc_id: str) -> str:
    """
    Get document name from configuration.

    Args:
        storage: Storage client
        doc_id: Document ID

    Returns:
        str: Document name
    """
    try:
        config = await storage.load_config("documents.json")
        if config:
            documents = config.get("documents", [])
            for doc in documents:
                if doc.get("id") == doc_id:
                    return doc.get("name", doc_id)
    except Exception:
        pass

    return doc_id  # Fallback to ID if name not found