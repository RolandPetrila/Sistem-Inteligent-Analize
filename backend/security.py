"""Security utilities — API key validation."""
from fastapi import Header, HTTPException, status
from backend.config import settings


async def require_api_key(x_ris_key: str = Header(default="")) -> None:
    """Dependency: require X-RIS-Key header if RIS_API_KEY is configured."""
    if not settings.ris_api_key:
        return  # No key configured — open access (local mode)
    if x_ris_key != settings.ris_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-RIS-Key header",
        )
