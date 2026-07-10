"""FastAPI dependency injection container."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import validate_api_key
from backend.models.database import get_db

# Re-export for convenience
SessionDep = Annotated[AsyncSession, Depends(get_db)]
APIKeyDep = Annotated[str, Depends(validate_api_key)]


# Rate limiter via slowapi — configured in main.py lifespan
async def get_rate_limit_key(request: Request) -> str:
    """Extract the rate limiting key from X-API-Key header."""
    api_key = request.headers.get("X-API-Key", "anonymous")
    return f"api_key:{api_key}"
