"""
ToS endpoint routes for the ToS Monitor application.
Provides endpoints to list all documents and get details of specific documents.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.storage import get_storage_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tos", tags=["ToS Documents"])


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
            "available_dates": available_dates,
            "details": {
                "current": {
                    "date": current_date,
                    "timestamp": current_metadata.get("timestamp"),
                    "content_length": current_metadata.get("content_length"),
                    "content_hash": current_metadata.get("content_hash"),
                    "structural_hash": current_metadata.get("structural_hash"),
                    "title": current_metadata.get("title")
                },
                "last": None,
                "prev": None
            }
        }

        # Add last document details if available
        if last_doc and last_date:
            last_metadata = last_doc.get("metadata", {})
            document_info["details"]["last"] = {
                "date": last_date,
                "timestamp": last_metadata.get("timestamp"),
                "content_length": last_metadata.get("content_length"),
                "content_hash": last_metadata.get("content_hash"),
                "structural_hash": last_metadata.get("structural_hash"),
                "title": last_metadata.get("title")
            }

        # Add prev document details if available
        if prev_doc and prev_date:
            prev_metadata = prev_doc.get("metadata", {})
            document_info["details"]["prev"] = {
                "date": prev_date,
                "timestamp": prev_metadata.get("timestamp"),
                "content_length": prev_metadata.get("content_length"),
                "content_hash": prev_metadata.get("content_hash"),
                "structural_hash": prev_metadata.get("structural_hash"),
                "title": prev_metadata.get("title")
            }

        return document_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ToS document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")