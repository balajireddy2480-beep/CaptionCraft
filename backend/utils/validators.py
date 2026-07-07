"""File validation utilities for uploaded videos."""

import os
from fastapi import UploadFile, HTTPException


def validate_video_file(
    file: UploadFile,
    allowed_extensions: list[str],
    max_size_bytes: int,
) -> None:
    """
    Validate an uploaded video file for type and size.

    Raises HTTPException with appropriate status codes on failure.
    """
    # Check filename exists
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    # Check file extension
    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed_extensions)}",
        )

    # Check content type
    if file.content_type and not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=415,
            detail=f"Invalid content type '{file.content_type}'. Expected a video file.",
        )


def validate_file_size(file_bytes: bytes, max_size_bytes: int) -> None:
    """Validate that file bytes don't exceed the maximum size."""
    if len(file_bytes) > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        actual_mb = len(file_bytes) / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({actual_mb:.1f} MB). Maximum allowed: {max_mb:.0f} MB.",
        )


VALID_STYLES = {"formal", "sarcastic", "humorous_tech", "humorous_non_tech"}


def validate_styles(styles_str: str) -> list[str]:
    """Parse and validate the requested caption styles."""
    if not styles_str or not styles_str.strip():
        return list(VALID_STYLES)

    styles = [s.strip().lower() for s in styles_str.split(",") if s.strip()]
    invalid = [s for s in styles if s not in VALID_STYLES]

    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid styles: {', '.join(invalid)}. Valid: {', '.join(sorted(VALID_STYLES))}",
        )

    return styles
