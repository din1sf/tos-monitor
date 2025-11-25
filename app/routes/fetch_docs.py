"""
Fetch documents endpoint for ToS Monitor.
Handles downloading, normalizing, and storing legal documents.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.storage import get_storage_client
from app.utils.html_parser import get_html_parser
from app.utils.normalizer import get_text_normalizer
from app.utils.hashing import get_content_hasher


logger = logging.getLogger(__name__)
router = APIRouter()


class Document(BaseModel):
    """Document model matching documents.json structure."""
    id: str
    name: str
    url: str
    selector: Optional[str] = None
    description: Optional[str] = None


class FetchRequest(BaseModel):
    """Request model for fetch-docs endpoint."""
    documents: Optional[List[Document]] = None  # Provide documents directly instead of using documents.json
    document_ids: Optional[List[str]] = None  # Filter specific documents (legacy support)
    force_update: bool = False  # Force update even if no changes detected


class DocumentResult(BaseModel):
    """Result model for individual document processing."""
    document_id: str
    document_name: str
    url: str
    success: bool
    changes_detected: bool
    snapshot_created: bool
    timestamp: Optional[str] = None
    error_message: Optional[str] = None
    content_length: Optional[int] = None
    hashes: Optional[Dict[str, str]] = None


class FetchResponse(BaseModel):
    """Response model for fetch-docs endpoint."""
    success: bool
    processed_count: int
    success_count: int
    error_count: int
    documents: List[DocumentResult]
    processing_time: float


@router.post("/fetch-docs", response_model=FetchResponse)
async def fetch_documents(request: FetchRequest = FetchRequest()):
    """
    Fetch and process legal documents.

    This endpoint:
    1. Loads document configuration
    2. Downloads documents from configured URLs
    3. Normalizes content and detects changes
    4. Stores new snapshots if content has changed
    5. Returns processing results
    """
    start_time = datetime.utcnow()

    try:
        # Initialize clients
        storage = get_storage_client()
        html_parser = get_html_parser()
        normalizer = get_text_normalizer()
        hasher = get_content_hasher()

        # Use documents from request if provided, otherwise load from documents.json
        if request.documents:
            # Use documents directly from request body
            documents = [doc.model_dump() for doc in request.documents]
        else:
            # Load document configuration from file
            config = await storage.load_config("documents.json")
            if not config:
                raise HTTPException(
                    status_code=500,
                    detail="Could not load document configuration from storage"
                )

            documents = config.get("documents", [])
            if not documents:
                raise HTTPException(
                    status_code=400,
                    detail="No documents configured in documents.json"
                )

        # Filter documents if specific IDs requested
        if request.document_ids:
            documents = [
                doc for doc in documents
                if doc.get("id") in request.document_ids
            ]
            if not documents:
                raise HTTPException(
                    status_code=400,
                    detail=f"No documents found for IDs: {request.document_ids}"
                )

        logger.info(f"Processing {len(documents)} documents")

        # Process documents
        results = []
        for doc_config in documents:
            result = await process_document(
                doc_config, storage, html_parser, normalizer, hasher, request.force_update
            )
            results.append(result)

        # Calculate summary stats
        success_count = sum(1 for r in results if r.success)
        error_count = len(results) - success_count
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            f"Completed document processing: {success_count}/{len(results)} successful, "
            f"{processing_time:.2f}s"
        )

        return FetchResponse(
            success=True,
            processed_count=len(results),
            success_count=success_count,
            error_count=error_count,
            documents=results,
            processing_time=processing_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in fetch_documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def process_document(
    doc_config: Dict[str, Any],
    storage,
    html_parser,
    normalizer,
    hasher,
    force_update: bool = False
) -> DocumentResult:
    """
    Process a single document.

    Args:
        doc_config: Document configuration
        storage: Storage client
        html_parser: HTML parser
        normalizer: Text normalizer
        hasher: Content hasher
        force_update: Whether to force update regardless of changes

    Returns:
        DocumentResult: Processing result
    """
    doc_id = doc_config.get("id")
    doc_name = doc_config.get("name", doc_id)
    url = doc_config.get("url")
    selector = doc_config.get("selector")

    if not doc_id or not url:
        return DocumentResult(
            document_id=doc_id or "unknown",
            document_name=doc_name,
            url=url or "unknown",
            success=False,
            changes_detected=False,
            snapshot_created=False,
            error_message="Missing document ID or URL in configuration"
        )

    try:
        logger.info(f"Processing document: {doc_id} from {url}")

        # Fetch the document
        page_data = await html_parser.fetch_page(url, selector)
        if not page_data:
            return DocumentResult(
                document_id=doc_id,
                document_name=doc_name,
                url=url,
                success=False,
                changes_detected=False,
                snapshot_created=False,
                error_message="Failed to fetch document content"
            )

        # Normalize content
        raw_content = page_data["content"]
        normalized_content = normalizer.normalize_text(raw_content, preserve_structure=True)

        if not normalized_content.strip():
            return DocumentResult(
                document_id=doc_id,
                document_name=doc_name,
                url=url,
                success=False,
                changes_detected=False,
                snapshot_created=False,
                error_message="Document content is empty after normalization"
            )

        # Generate hashes
        new_hashes = hasher.generate_all_hashes(normalized_content)

        # Create comprehensive metadata
        metadata = hasher.create_metadata(
            normalized_content,
            url,
            {
                "document_id": doc_id,
                "document_name": doc_name,
                "title": page_data.get("title", ""),
                "page_metadata": page_data.get("metadata", {}),
                "normalization_applied": True,
                "selector_used": selector,
                "force_update": force_update
            }
        )

        # Use new ToS storage structure with current/last/prev/dated files
        storage_result = await storage.store_tos_document(doc_id, normalized_content, metadata)

        changes_detected = storage_result.get("changes_detected", False)
        snapshot_created = storage_result.get("snapshot_created", False)
        timestamp = storage_result.get("timestamp", None)

        if changes_detected:
            logger.info(f"Changes detected and snapshot created for {doc_id} at {timestamp}")
        else:
            logger.info(f"No changes detected for {doc_id}, only current.txt updated")

        return DocumentResult(
            document_id=doc_id,
            document_name=doc_name,
            url=url,
            success=True,
            changes_detected=changes_detected,
            snapshot_created=snapshot_created,
            timestamp=timestamp,
            content_length=len(normalized_content),
            hashes=new_hashes
        )

    except Exception as e:
        logger.error(f"Error processing document {doc_id}: {str(e)}")
        return DocumentResult(
            document_id=doc_id,
            document_name=doc_name,
            url=url,
            success=False,
            changes_detected=False,
            snapshot_created=False,
            error_message=str(e)
        )