import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.storage import get_storage_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prompt", tags=["Prompt Management"])


@router.get("", response_class=PlainTextResponse)
async def get_prompt():
    storage = get_storage_client()
    content = await storage.load_prompt()
    return PlainTextResponse(content or "")


@router.put("")
async def save_prompt(request: Request):
    storage = get_storage_client()
    body = await request.body()
    new_content = body.decode("utf-8")

    current = await storage.load_prompt()
    if current:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await storage.upload_file(f"prompt-{date_str}.txt", current)

    saved = await storage.save_prompt(new_content)
    if not saved:
        return {"error": "Failed to save prompt"}, 500
    return {"status": "saved"}


@router.get("/versions")
async def list_prompt_versions():
    storage = get_storage_client()
    files = await storage.list_files(prefix="")
    dates = []
    for f in files:
        m = re.match(r"prompt-(\d{4}-\d{2}-\d{2})\.txt$", f)
        if m:
            dates.append(m.group(1))
    dates.sort(reverse=True)
    return {"versions": dates}


@router.get("/{date}", response_class=PlainTextResponse)
async def get_prompt_version(date: str):
    storage = get_storage_client()
    content = await storage.download_file(f"prompt-{date}.txt")
    if content is None:
        return PlainTextResponse("Version not found", status_code=404)
    return PlainTextResponse(content)
