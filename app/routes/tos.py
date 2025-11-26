"""
ToS endpoint routes for the ToS Monitor application.
Provides endpoints to list all documents and get details of specific documents.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from app.storage import get_storage_client
from app.tos_client import ToSClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tos", tags=["ToS Documents"])


class AnalyzeRequest(BaseModel):
    """Request model for document analysis."""
    ai_provider: Optional[str] = Field(
        None,
        description="AI provider to use ('openai' or 'openrouter'). If not provided, uses AI_PROVIDER env var.",
        example="openrouter"
    )
    prev: Optional[str] = Field(
        None,
        description="Previous version to compare (YYYY-MM-DD format or 'prev'). If not provided, uses 'prev' pointer.",
        example="2025-11-25"
    )
    last: Optional[str] = Field(
        None,
        description="Latest version to compare (YYYY-MM-DD format or 'last'). If not provided, uses 'last' pointer.",
        example="2025-11-26"
    )


@router.get("", response_model=Dict[str, Any])
async def list_tos_documents():
    """
    List all ToS documents with their current, last, and previous dates.

    Returns:
        JSON response with document IDs as keys containing their basic information
    """
    try:
        storage = get_storage_client()

        # Load document configuration
        config = await storage.load_config("documents.json")
        if not config:
            raise HTTPException(
                status_code=404,
                detail="Document configuration not found"
            )

        documents = config.get("documents", [])
        result = {}

        for doc in documents:
            doc_id = doc.get("id")
            if not doc_id:
                continue

            try:
                # Get current document info
                current_doc = await storage.get_tos_document(doc_id, "current")

                # Get last and prev dates from pointer files
                last_date = None
                prev_date = None

                try:
                    last_date_content = await storage.download_file(f"tos/{doc_id}/last.txt")
                    if last_date_content:
                        last_date = last_date_content.strip()
                except Exception:
                    pass

                try:
                    prev_date_content = await storage.download_file(f"tos/{doc_id}/prev.txt")
                    if prev_date_content:
                        prev_date = prev_date_content.strip()
                except Exception:
                    pass

                # Check if there are changes (changed file exists)
                has_changes = await storage.file_exists(f"tos/{doc_id}/changed")

                # Get all available dated versions
                prefix = f"tos/{doc_id}/"
                all_files = await storage.list_files(prefix)

                # Extract dates from dated files (YYYY-MM-DD.txt format)
                available_dates = []
                for file_path in all_files:
                    filename = file_path.split("/")[-1]
                    if filename.endswith(".txt") and len(filename) == 14:  # YYYY-MM-DD.txt
                        date_part = filename[:-4]  # Remove .txt
                        if date_part not in ["current", "last", "prev"]:
                            available_dates.append(date_part)

                # Sort dates in descending order (newest first)
                available_dates.sort(reverse=True)

                current_date = None
                if current_doc and current_doc.get("metadata"):
                    timestamp = current_doc["metadata"].get("timestamp")
                    if timestamp:
                        try:
                            # Parse ISO timestamp and convert to date
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            current_date = dt.strftime("%Y-%m-%d")
                        except Exception:
                            current_date = datetime.now().strftime("%Y-%m-%d")

                result[doc_id] = {
                    "id": doc_id,
                    "name": doc.get("name", ""),
                    "url": doc.get("url", ""),
                    "current": current_date,
                    "last": last_date,
                    "prev": prev_date,
                    "changed": has_changes,
                    "total": len(available_dates),
                    "available_dates": available_dates
                }

            except Exception as e:
                logger.warning(f"Error processing document {doc_id}: {str(e)}")
                # Still include the document with basic info
                result[doc_id] = {
                    "id": doc_id,
                    "name": doc.get("name", ""),
                    "url": doc.get("url", ""),
                    "current": None,
                    "last": None,
                    "prev": None,
                    "changed": False,
                    "total": 0,
                    "available_dates": []
                }

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing ToS documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{document_id}", response_model=Dict[str, Any])
async def get_tos_document(document_id: str):
    """
    Get detailed information for a specific ToS document.

    Args:
        document_id: The ID of the document to retrieve

    Returns:
        JSON response with detailed document information including current, last, and prev versions
    """
    try:
        storage = get_storage_client()

        # Load document configuration to verify document exists
        config = await storage.load_config("documents.json")
        if not config:
            raise HTTPException(
                status_code=404,
                detail="Document configuration not found"
            )

        documents = config.get("documents", [])
        doc_config = None
        for doc in documents:
            if doc.get("id") == document_id:
                doc_config = doc
                break

        if not doc_config:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{document_id}' not found in configuration"
            )

        # Get current document
        current_doc = await storage.get_tos_document(document_id, "current")
        if not current_doc:
            raise HTTPException(
                status_code=404,
                detail=f"Current version of document '{document_id}' not found"
            )

        # Get last and prev documents
        last_doc = await storage.get_tos_document(document_id, "last")
        prev_doc = await storage.get_tos_document(document_id, "prev")

        # Get pointer dates
        last_date = None
        prev_date = None

        try:
            last_date_content = await storage.download_file(f"tos/{document_id}/last.txt")
            if last_date_content:
                last_date = last_date_content.strip()
        except Exception:
            pass

        try:
            prev_date_content = await storage.download_file(f"tos/{document_id}/prev.txt")
            if prev_date_content:
                prev_date = prev_date_content.strip()
        except Exception:
            pass

        # Check if there are changes
        has_changes = await storage.file_exists(f"tos/{document_id}/changed")

        # Get all available dated versions
        prefix = f"tos/{document_id}/"
        all_files = await storage.list_files(prefix)

        # Extract dates from dated files
        available_dates = []
        for file_path in all_files:
            filename = file_path.split("/")[-1]
            if filename.endswith(".txt") and len(filename) == 14:  # YYYY-MM-DD.txt
                date_part = filename[:-4]  # Remove .txt
                if date_part not in ["current", "last", "prev"]:
                    available_dates.append(date_part)

        # Sort dates in descending order (newest first)
        available_dates.sort(reverse=True)

        # Build response
        current_metadata = current_doc.get("metadata", {})
        current_date = None
        if current_metadata.get("timestamp"):
            try:
                dt = datetime.fromisoformat(current_metadata["timestamp"].replace('Z', '+00:00'))
                current_date = dt.strftime("%Y-%m-%d")
            except Exception:
                current_date = datetime.now().strftime("%Y-%m-%d")

        document_info = {
            "id": document_id,
            "name": doc_config.get("name", ""),
            "url": doc_config.get("url", ""),
            "current": current_date,
            "last": last_date,
            "prev": prev_date,
            "changed": has_changes,
            "total": len(available_dates),
            "available_dates": available_dates
        }

        return document_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ToS document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{document_id}/prev", response_class=PlainTextResponse)
async def get_tos_document_prev_content(document_id: str):
    """
    Get the content of the previous version of a ToS document as plain text.

    Args:
        document_id: The ID of the document to retrieve

    Returns:
        Plain text content of the document
    """
    try:
        storage = get_storage_client()

        # Verify document exists in configuration
        config = await storage.load_config("documents.json")
        if not config:
            raise HTTPException(
                status_code=404,
                detail="Document configuration not found"
            )

        documents = config.get("documents", [])
        doc_config = None
        for doc in documents:
            if doc.get("id") == document_id:
                doc_config = doc
                break

        if not doc_config:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{document_id}' not found in configuration"
            )

        # Get previous document content
        prev_doc = await storage.get_tos_document(document_id, "prev")
        if not prev_doc:
            raise HTTPException(
                status_code=404,
                detail=f"Previous version of document '{document_id}' not found"
            )

        return PlainTextResponse(content=prev_doc.get("content", ""), media_type="text/plain")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting previous content for document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{document_id}/last", response_class=PlainTextResponse)
async def get_tos_document_last_content(document_id: str):
    """
    Get the content of the last version of a ToS document as plain text.

    Args:
        document_id: The ID of the document to retrieve

    Returns:
        Plain text content of the document
    """
    try:
        storage = get_storage_client()

        # Verify document exists in configuration
        config = await storage.load_config("documents.json")
        if not config:
            raise HTTPException(
                status_code=404,
                detail="Document configuration not found"
            )

        documents = config.get("documents", [])
        doc_config = None
        for doc in documents:
            if doc.get("id") == document_id:
                doc_config = doc
                break

        if not doc_config:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{document_id}' not found in configuration"
            )

        # Get last document content
        last_doc = await storage.get_tos_document(document_id, "last")
        if not last_doc:
            raise HTTPException(
                status_code=404,
                detail=f"Last version of document '{document_id}' not found"
            )

        return PlainTextResponse(content=last_doc.get("content", ""), media_type="text/plain")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting last content for document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{document_id}/{date}", response_class=PlainTextResponse)
async def get_tos_document_date_content(document_id: str, date: str):
    """
    Get the content of a specific dated version of a ToS document as plain text.

    Args:
        document_id: The ID of the document to retrieve
        date: The date of the version to retrieve (YYYY-MM-DD format)

    Returns:
        Plain text content of the document
    """
    try:
        storage = get_storage_client()

        # Verify document exists in configuration
        config = await storage.load_config("documents.json")
        if not config:
            raise HTTPException(
                status_code=404,
                detail="Document configuration not found"
            )

        documents = config.get("documents", [])
        doc_config = None
        for doc in documents:
            if doc.get("id") == document_id:
                doc_config = doc
                break

        if not doc_config:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{document_id}' not found in configuration"
            )

        # Validate date format (basic check)
        if len(date) != 10 or date.count('-') != 2:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format '{date}'. Expected YYYY-MM-DD format"
            )

        # Get specific dated document content
        dated_doc = await storage.get_tos_document(document_id, date)
        if not dated_doc:
            raise HTTPException(
                status_code=404,
                detail=f"Version '{date}' of document '{document_id}' not found"
            )

        return PlainTextResponse(content=dated_doc.get("content", ""), media_type="text/plain")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dated content for document {document_id}, date {date}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{document_id}", response_class=PlainTextResponse)
async def analyze_tos_document(
    document_id: str,
    request: AnalyzeRequest = Body(...)
):
    """
    Generate AI-powered difference analysis between two versions of a ToS document.

    By default compares the latest and previous versions as defined by the pointer system.
    Optionally accepts specific dates and AI provider for custom comparison.

    Args:
        document_id: The ID of the document to analyze
        request: Analysis configuration with optional ai_provider, prev_date, latest_date

    Returns:
        Plain text response with AI analysis content only
    """
    try:
        storage = get_storage_client()
        tos_client = ToSClient(ai_provider=request.ai_provider)

        logger.info(f"Starting analysis for document: {document_id}")

        # Verify document exists in configuration
        config = await storage.load_config("documents.json")
        if not config:
            raise HTTPException(
                status_code=404,
                detail="Document configuration not found"
            )

        documents = config.get("documents", [])
        doc_config = None
        for doc in documents:
            if doc.get("id") == document_id:
                doc_config = doc
                break

        if not doc_config:
            raise HTTPException(
                status_code=404,
                detail=f"Document '{document_id}' not found in configuration"
            )

        # Determine which versions to compare
        prev_version = request.prev if request.prev else "prev"
        latest_version = request.last if request.last else "last"

        logger.info(f"Comparing versions: {prev_version} vs {latest_version}")

        # Get document versions
        try:
            prev_doc = await storage.get_tos_document(document_id, prev_version)
            if not prev_doc:
                available_versions = await _get_available_versions(storage, document_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Previous version '{prev_version}' not found for document '{document_id}'. "
                           f"Available versions: {available_versions}"
                )

            latest_doc = await storage.get_tos_document(document_id, latest_version)
            if not latest_doc:
                available_versions = await _get_available_versions(storage, document_id)
                raise HTTPException(
                    status_code=404,
                    detail=f"Latest version '{latest_version}' not found for document '{document_id}'. "
                           f"Available versions: {available_versions}"
                )

        except Exception as e:
            if "HTTPException" in str(type(e)):
                raise
            logger.error(f"Error fetching document versions: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch document versions: {str(e)}"
            )

        # Extract content
        prev_content = prev_doc.get("content", "")
        latest_content = latest_doc.get("content", "")

        if not prev_content:
            raise HTTPException(
                status_code=422,
                detail=f"Previous version '{prev_version}' has no content"
            )

        if not latest_content:
            raise HTTPException(
                status_code=422,
                detail=f"Latest version '{latest_version}' has no content"
            )

        # Check if documents are identical
        if prev_content.strip() == latest_content.strip():
            return PlainTextResponse(
                content=f"No differences found between versions {prev_version} and {latest_version} of {doc_config.get('name', document_id)}.",
                media_type="text/plain"
            )

        # Perform analysis using ToS client (no approval required)
        analysis_result = await tos_client.analyze_documents(
            previous_content=prev_content,
            current_content=latest_content,
            document_name=doc_config.get("name", document_id),
            metadata=None,
            request_approval=False
        )

        logger.info(f"Analysis completed for document {document_id} with status: {analysis_result.get('status')}")

        # Return only the AI analysis content as plain text
        if analysis_result.get("status") == "success":
            analysis_content = analysis_result.get("analysis", "")
            return PlainTextResponse(content=analysis_content, media_type="text/plain")
        else:
            # Return error message as plain text
            error_message = analysis_result.get("message", "Analysis failed")
            return PlainTextResponse(content=f"Error: {error_message}", media_type="text/plain")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing ToS document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


async def _get_available_versions(storage, document_id: str) -> List[str]:
    """Helper function to get available versions for error messages."""
    try:
        prefix = f"tos/{document_id}/"
        all_files = await storage.list_files(prefix)

        versions = []
        for file_path in all_files:
            filename = file_path.split("/")[-1]
            if filename.endswith(".txt"):
                version = filename[:-4]  # Remove .txt
                versions.append(version)

        return sorted(versions)
    except Exception:
        return ["Unable to list available versions"]