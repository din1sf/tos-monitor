import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.storage import get_storage_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config/documents", tags=["Document Configuration"])


class DocumentInput(BaseModel):
    id: str = Field(..., min_length=1, max_length=100, description="Unique document identifier (alphanumeric, underscores, hyphens)")
    name: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., min_length=1)
    selector: Optional[str] = None
    description: Optional[str] = None


class DocumentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    url: Optional[str] = Field(None, min_length=1)
    selector: Optional[str] = None
    description: Optional[str] = None


_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')


async def _load_config():
    storage = get_storage_client()
    config = await storage.load_config("documents.json")
    if not config:
        config = {"documents": [], "metadata": {}}
    return storage, config


async def _save_config(storage, config):
    config.setdefault("metadata", {})
    config["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
    saved = await storage.save_config(config, "documents.json")
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to save configuration")


@router.post("", status_code=201)
async def add_document(doc: DocumentInput):
    if not _ID_PATTERN.match(doc.id):
        raise HTTPException(status_code=400, detail="ID must contain only alphanumeric characters, underscores, and hyphens")

    storage, config = await _load_config()
    documents = config.get("documents", [])

    for existing in documents:
        if existing.get("id") == doc.id:
            raise HTTPException(status_code=409, detail=f"Document '{doc.id}' already exists")

    new_doc = {"id": doc.id, "name": doc.name, "url": doc.url}
    if doc.selector:
        new_doc["selector"] = doc.selector
    if doc.description:
        new_doc["description"] = doc.description

    documents.append(new_doc)
    config["documents"] = documents
    await _save_config(storage, config)

    return {"success": True, "document": new_doc}


@router.put("/{document_id}")
async def update_document(document_id: str, update: DocumentUpdate):
    storage, config = await _load_config()
    documents = config.get("documents", [])

    for i, existing in enumerate(documents):
        if existing.get("id") == document_id:
            if update.name is not None:
                existing["name"] = update.name
            if update.url is not None:
                existing["url"] = update.url
            if update.selector is not None:
                existing["selector"] = update.selector if update.selector else None
                if not update.selector and "selector" in existing:
                    del existing["selector"]
            if update.description is not None:
                existing["description"] = update.description if update.description else None
                if not update.description and "description" in existing:
                    del existing["description"]

            documents[i] = existing
            config["documents"] = documents
            await _save_config(storage, config)
            return {"success": True, "document": existing}

    raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    storage, config = await _load_config()
    documents = config.get("documents", [])

    for i, existing in enumerate(documents):
        if existing.get("id") == document_id:
            documents.pop(i)
            config["documents"] = documents
            await _save_config(storage, config)
            return {"success": True, "deleted": document_id}

    raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")
