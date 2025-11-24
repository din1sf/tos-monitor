"""
Generate diffs endpoint for ToS Monitor.
Handles LLM-powered comparison and diff generation for document changes.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.storage import get_storage_client
from app.llm_client import get_llm_client
from app.utils.hashing import get_content_hasher


logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateDiffsRequest(BaseModel):
    """Request model for generate-diffs endpoint."""
    document_ids: Optional[List[str]] = None  # Filter specific documents
    force_regenerate: bool = False  # Force regeneration even if diff exists


class DiffResult(BaseModel):
    """Result model for individual diff generation."""
    document_id: str
    document_name: str
    success: bool
    diff_generated: bool
    timestamp: Optional[str] = None
    previous_snapshot_timestamp: Optional[str] = None
    current_snapshot_timestamp: Optional[str] = None
    error_message: Optional[str] = None
    diff_length: Optional[int] = None
    token_usage: Optional[Dict[str, Any]] = None


class GenerateDiffsResponse(BaseModel):
    """Response model for generate-diffs endpoint."""
    success: bool
    processed_count: int
    success_count: int
    error_count: int
    diffs_generated: int
    documents: List[DiffResult]
    processing_time: float


@router.post("/generate-diffs", response_model=GenerateDiffsResponse)
async def generate_diffs(request: GenerateDiffsRequest = GenerateDiffsRequest()):
    """
    Generate LLM-powered diffs for document changes.

    This endpoint:
    1. Loads documents with existing snapshots
    2. Finds previous and current versions for comparison
    3. Loads appropriate LLM prompts
    4. Generates diff summaries using LLM
    5. Stores diff results
    6. Returns processing results
    """
    start_time = datetime.utcnow()

    try:
        # Initialize clients
        storage = get_storage_client()
        llm_client = get_llm_client()
        hasher = get_content_hasher()

        # Load document configuration
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

        logger.info(f"Processing diffs for {len(documents)} documents")

        # Process documents
        results = []
        for doc_config in documents:
            result = await process_document_diff(
                doc_config, storage, llm_client, hasher, request.force_regenerate
            )
            results.append(result)

        # Calculate summary stats
        success_count = sum(1 for r in results if r.success)
        error_count = len(results) - success_count
        diffs_generated = sum(1 for r in results if r.diff_generated)
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            f"Completed diff generation: {success_count}/{len(results)} successful, "
            f"{diffs_generated} diffs generated, {processing_time:.2f}s"
        )

        return GenerateDiffsResponse(
            success=True,
            processed_count=len(results),
            success_count=success_count,
            error_count=error_count,
            diffs_generated=diffs_generated,
            documents=results,
            processing_time=processing_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generate_diffs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def process_document_diff(
    doc_config: Dict[str, Any],
    storage,
    llm_client,
    hasher,
    force_regenerate: bool = False
) -> DiffResult:
    """
    Process diff generation for a single document.

    Args:
        doc_config: Document configuration
        storage: Storage client
        llm_client: LLM client
        hasher: Content hasher
        force_regenerate: Whether to force regeneration

    Returns:
        DiffResult: Processing result
    """
    doc_id = doc_config.get("id")
    doc_name = doc_config.get("name", doc_id)

    if not doc_id:
        return DiffResult(
            document_id="unknown",
            document_name=doc_name,
            success=False,
            diff_generated=False,
            error_message="Missing document ID in configuration"
        )

    try:
        logger.info(f"Processing diff for document: {doc_id}")

        # Get all snapshots for this document
        snapshots = await storage.get_document_snapshots(doc_id)

        if len(snapshots) < 2:
            logger.info(f"Document {doc_id} has only {len(snapshots)} snapshot(s), diff not needed")
            return DiffResult(
                document_id=doc_id,
                document_name=doc_name,
                success=True,
                diff_generated=False,
                error_message=f"Need at least 2 snapshots for diff, found {len(snapshots)}"
            )

        # Get the two most recent snapshots
        current_timestamp = snapshots[0]  # Most recent
        previous_timestamp = snapshots[1]  # Second most recent

        # Check if we need to generate a diff
        if not force_regenerate:
            existing_diff = await storage.get_latest_diff(doc_id)
            if existing_diff:
                diff_metadata = existing_diff.get("metadata", {})
                if (diff_metadata.get("current_snapshot_timestamp") == current_timestamp and
                    diff_metadata.get("previous_snapshot_timestamp") == previous_timestamp):
                    logger.info(f"Diff already exists for {doc_id} snapshots {previous_timestamp} -> {current_timestamp}")
                    return DiffResult(
                        document_id=doc_id,
                        document_name=doc_name,
                        success=True,
                        diff_generated=False,
                        previous_snapshot_timestamp=previous_timestamp,
                        current_snapshot_timestamp=current_timestamp,
                        error_message="Diff already exists for these snapshots"
                    )

        # Load snapshots
        previous_content = await storage.download_file(f"snapshots/{doc_id}/{previous_timestamp}/content.txt")
        current_content = await storage.download_file(f"snapshots/{doc_id}/{current_timestamp}/content.txt")

        if not previous_content or not current_content:
            return DiffResult(
                document_id=doc_id,
                document_name=doc_name,
                success=False,
                diff_generated=False,
                error_message="Could not load snapshot content for comparison"
            )

        # Check if content has meaningfully changed using fingerprint hash
        previous_metadata_str = await storage.download_file(f"snapshots/{doc_id}/{previous_timestamp}/metadata.json")
        current_metadata_str = await storage.download_file(f"snapshots/{doc_id}/{current_timestamp}/metadata.json")

        if previous_metadata_str and current_metadata_str:
            import json
            previous_metadata = json.loads(previous_metadata_str)
            current_metadata = json.loads(current_metadata_str)

            previous_hashes = previous_metadata.get("hashes", {})
            current_hashes = current_metadata.get("hashes", {})

            if not hasher.should_generate_diff(previous_hashes, current_hashes):
                logger.info(f"No meaningful content changes detected for {doc_id}, skipping diff")
                return DiffResult(
                    document_id=doc_id,
                    document_name=doc_name,
                    success=True,
                    diff_generated=False,
                    previous_snapshot_timestamp=previous_timestamp,
                    current_snapshot_timestamp=current_timestamp,
                    error_message="No meaningful content changes detected"
                )

        # Load prompt template
        prompt_template = await load_diff_prompt(storage, doc_id)

        # Generate diff using LLM
        logger.info(f"Generating diff for {doc_id} using LLM")
        diff_content = await llm_client.compare_documents(
            previous_content,
            current_content,
            doc_name,
            prompt_template,
            {
                "document_id": doc_id,
                "previous_timestamp": previous_timestamp,
                "current_timestamp": current_timestamp,
                "url": doc_config.get("url", "")
            }
        )

        if not diff_content:
            return DiffResult(
                document_id=doc_id,
                document_name=doc_name,
                success=False,
                diff_generated=False,
                previous_snapshot_timestamp=previous_timestamp,
                current_snapshot_timestamp=current_timestamp,
                error_message="LLM failed to generate diff content"
            )

        # Create diff metadata
        diff_metadata = {
            "document_id": doc_id,
            "document_name": doc_name,
            "previous_snapshot_timestamp": previous_timestamp,
            "current_snapshot_timestamp": current_timestamp,
            "llm_model": llm_client.model,
            "prompt_template_used": "default_comparison.txt" if "default" in prompt_template else "custom",
            "generated_at": datetime.utcnow().isoformat(),
            "url": doc_config.get("url", "")
        }

        # Store the diff
        timestamp = await storage.store_diff(doc_id, diff_content, diff_metadata)

        logger.info(f"Generated and stored diff for {doc_id} at {timestamp}")

        return DiffResult(
            document_id=doc_id,
            document_name=doc_name,
            success=True,
            diff_generated=True,
            timestamp=timestamp,
            previous_snapshot_timestamp=previous_timestamp,
            current_snapshot_timestamp=current_timestamp,
            diff_length=len(diff_content)
        )

    except Exception as e:
        logger.error(f"Error processing diff for document {doc_id}: {str(e)}")
        return DiffResult(
            document_id=doc_id,
            document_name=doc_name,
            success=False,
            diff_generated=False,
            error_message=str(e)
        )


async def load_diff_prompt(storage, doc_id: str) -> str:
    """
    Load appropriate diff prompt for a document.

    Args:
        storage: Storage client
        doc_id: Document ID

    Returns:
        str: Prompt template content
    """
    # Try document-specific prompt first
    doc_specific_prompt = await storage.load_prompt(f"{doc_id}_comparison.txt")
    if doc_specific_prompt:
        logger.debug(f"Using document-specific prompt for {doc_id}")
        return doc_specific_prompt

    # Fall back to default prompt
    default_prompt = await storage.load_prompt("default_comparison.txt")
    if default_prompt:
        logger.debug(f"Using default prompt for {doc_id}")
        return default_prompt

    # Use built-in fallback prompt
    logger.warning(f"No prompt found in storage, using built-in fallback for {doc_id}")
    return get_fallback_prompt()


def get_fallback_prompt() -> str:
    """Get a built-in fallback prompt if none found in storage."""
    return """Compare the two versions of the legal document '{document_name}' below and provide a clear, concise summary of the changes.

Focus on:
1. **Substantial Changes**: New terms, modified policies, changed obligations
2. **User Impact**: How changes affect users' rights, responsibilities, or experience
3. **Legal Implications**: Changes in liability, data handling, dispute resolution
4. **Compliance Requirements**: New requirements users must follow

Ignore:
- Minor formatting or wording changes that don't alter meaning
- Updated dates or version numbers
- Cosmetic changes to layout or presentation

**Previous Version:**
{previous_content}

**Current Version:**
{current_content}

**Additional Context:**
{metadata}

Please provide a structured summary with:
- **Summary**: Brief overview of changes
- **Key Changes**: Bulleted list of important modifications
- **User Impact**: How these changes affect users
- **Recommendations**: Any actions users should consider

Be objective, clear, and focus on meaningful changes that matter to users."""