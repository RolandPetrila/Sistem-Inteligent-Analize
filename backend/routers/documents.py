"""E3: Mistral OCR — Upload documente scanate si extragere text structurat."""

import base64

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger

from backend.config import settings

router = APIRouter()

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_MB = 20


@router.post("/ocr")
async def extract_text_from_document(file: UploadFile = File(...)) -> dict:
    """E3: Extrage text din document scanat (PDF/imagine) folosind Mistral OCR.

    Returneaza textul extras si datele structurate detectate.
    """
    if not settings.mistral_api_key:
        raise HTTPException(
            status_code=503,
            detail="Mistral API key neconfigurat. Adauga MISTRAL_API_KEY in .env",
        )

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tip fisier nesuptat: {file.content_type}. Acceptat: PDF, JPEG, PNG, WEBP",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Fisierul depaseste limita de {MAX_FILE_SIZE_MB}MB",
        )

    filename = file.filename or "document"
    is_pdf = file.content_type == "application/pdf"

    try:
        if is_pdf:
            result = await _ocr_pdf(content, filename)
        else:
            result = await _ocr_image(content, file.content_type or "image/jpeg", filename)
        return result
    except httpx.HTTPStatusError as e:
        logger.warning(f"[OCR] Mistral API error: {e.response.status_code}")
        raise HTTPException(
            status_code=502,
            detail=f"Eroare Mistral API: {e.response.status_code}",
        )
    except Exception as e:
        logger.error(f"[OCR] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Eroare la procesarea documentului")


async def _ocr_pdf(content: bytes, filename: str) -> dict:
    """Process PDF document using Mistral OCR API."""
    b64 = base64.b64encode(content).decode()

    payload = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{b64}",
        },
        "include_image_base64": False,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.mistral.ai/v1/ocr",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.mistral_api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    pages = data.get("pages", [])
    full_text = "\n\n".join(
        p.get("markdown", "") for p in pages if p.get("markdown")
    )

    return {
        "filename": filename,
        "type": "pdf",
        "pages": len(pages),
        "text": full_text,
        "char_count": len(full_text),
        "model": "mistral-ocr-latest",
    }


async def _ocr_image(content: bytes, mime_type: str, filename: str) -> dict:
    """Process image document using Mistral vision model."""
    b64 = base64.b64encode(content).decode()

    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extrage tot textul din aceasta imagine. "
                            "Pastreaza structura originala (tabele, liste, paragrafe). "
                            "Raspunde DOAR cu textul extras, fara comentarii suplimentare."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:{mime_type};base64,{b64}",
                    },
                ],
            }
        ],
        "max_tokens": 4096,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.mistral.ai/v1/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.mistral_api_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    return {
        "filename": filename,
        "type": "image",
        "pages": 1,
        "text": text,
        "char_count": len(text),
        "model": "mistral-small-latest",
    }
