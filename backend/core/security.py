"""API key authentication and SSRF protection."""

import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException, Request
from fastapi.security import APIKeyHeader

from backend.core.config import get_settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def validate_api_key(request: Request) -> str:
    """Validate the X-API-Key header against the configured allowed keys."""
    api_key: str | None = request.headers.get("X-API-Key")
    settings = get_settings()

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Provide it in the X-API-Key header.",
        )

    if api_key not in settings.allowed_api_keys_list:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )

    return api_key


_PRIVATE_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _is_private_ip(host: str) -> bool:
    """Check if a hostname resolves to a private/internal IP address."""
    try:
        addr = ipaddress.ip_address(host)
        return any(addr in net for net in _PRIVATE_RANGES)
    except ValueError:
        pass
    try:
        results = socket.getaddrinfo(host, None)
        for family, _type, _proto, _canonname, sockaddr in results:
            try:
                addr = ipaddress.ip_address(sockaddr[0])
                if any(addr in net for net in _PRIVATE_RANGES):
                    return True
            except ValueError:
                continue
    except socket.gaierror:
        pass
    return False


def check_ssrf(video_url: str) -> str:
    """Validate a video URL to prevent SSRF attacks.

    Checks that the URL:
    - Uses http or https scheme
    - Does not resolve to a private/internal IP address

    Returns the validated URL string. Raises HTTPException on failure.
    """
    parsed = urlparse(video_url)

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed.",
        )

    host = parsed.hostname or ""
    if host.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise HTTPException(
            status_code=400,
            detail="URL points to localhost, which is not allowed for SSRF protection.",
        )

    if host.endswith(".local") or host.endswith(".internal"):
        raise HTTPException(
            status_code=400,
            detail=f"URL points to internal hostname '{host}', which is not allowed.",
        )

    if _is_private_ip(host):
        raise HTTPException(
            status_code=400,
            detail=f"URL resolves to a private IP address ({host}), which is not allowed for SSRF protection.",
        )

    return video_url
