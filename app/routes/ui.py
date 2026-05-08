import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastapi import HTTPException

import re

from app.storage import get_storage_client
from app.routes.tos import list_tos_documents, get_tos_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ui", tags=["Web UI"])

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent.parent / "templates")
)


@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        documents = await list_tos_documents()
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        documents = {}

    try:
        storage = get_storage_client()
        config = await storage.load_config("documents.json")
        if config:
            config_by_id = {d["id"]: d for d in config.get("documents", []) if "id" in d}
            for doc_id, doc in documents.items():
                cfg = config_by_id.get(doc_id, {})
                doc["selector"] = cfg.get("selector", "")
    except Exception:
        pass

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"documents": documents},
    )


@router.get("/doc/{document_id}", response_class=HTMLResponse)
async def document_detail(request: Request, document_id: str):
    try:
        doc = await get_tos_document(document_id)
    except HTTPException:
        storage = get_storage_client()
        config = await storage.load_config("documents.json")
        doc_config = None
        if config:
            for d in config.get("documents", []):
                if d.get("id") == document_id:
                    doc_config = d
                    break
        if not doc_config:
            raise
        doc = {
            "id": document_id,
            "name": doc_config.get("name", document_id),
            "url": doc_config.get("url", ""),
            "current": None,
            "last": None,
            "prev": None,
            "changed": False,
            "total": 0,
            "available_dates": [],
        }
    return templates.TemplateResponse(
        request=request,
        name="document.html",
        context={"doc": doc},
    )


@router.get("/prompt", response_class=HTMLResponse)
async def prompt_editor(request: Request):
    storage = get_storage_client()
    content = await storage.load_prompt() or ""
    files = await storage.list_files(prefix="")
    versions = sorted(
        [m.group(1) for f in files if (m := re.search(r"prompt-(\d{4}-\d{2}-\d{2})\.txt", f))],
        reverse=True,
    )
    return templates.TemplateResponse(
        request=request,
        name="prompt.html",
        context={"prompt_content": content, "versions": versions},
    )
