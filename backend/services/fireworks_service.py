"""Fireworks AI service — video captioning via Qwen3 Omni."""

import base64
import logging
import mimetypes
from openai import OpenAI

from backend.config import get_settings
from backend.services.prompt_builder import get_style_prompt, get_summary_prompt

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI:
    """Create an OpenAI client pointed at Fireworks AI."""
    settings = get_settings()
    return OpenAI(
        api_key=settings.fireworks_api_key,
        base_url="https://api.fireworks.ai/inference/v1",
    )


def _encode_video(video_bytes: bytes, filename: str) -> tuple[str, str]:
    """Base64-encode video bytes and determine MIME type."""
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type or not mime_type.startswith("video/"):
        mime_type = "video/mp4"

    b64_data = base64.b64encode(video_bytes).decode("utf-8")
    return b64_data, mime_type


def _call_model(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    video_b64: str,
    mime_type: str,
) -> str:
    """Make a single chat completion call with video input."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "input_file",
                        "input_file": {
                            "url": f"data:{mime_type};base64,{video_b64}",
                        },
                    },
                ],
            },
        ],
        max_tokens=150,
        temperature=0.8,
    )
    return response.choices[0].message.content.strip()


def generate_captions(
    video_bytes: bytes,
    filename: str,
    styles: list[str],
) -> dict[str, str]:
    """
    Generate styled captions for a video.

    Args:
        video_bytes: Raw bytes of the video file.
        filename: Original filename (for MIME type detection).
        styles: List of style keys to generate captions for.

    Returns:
        Dictionary mapping style names (and 'video_summary') to caption strings.
    """
    settings = get_settings()
    client = _get_client()
    model = settings.fireworks_model

    # Encode video once, reuse for all calls
    video_b64, mime_type = _encode_video(video_bytes, filename)
    logger.info(
        "Video encoded: %s, MIME: %s, Size: %.1f MB",
        filename,
        mime_type,
        len(video_bytes) / (1024 * 1024),
    )

    results: dict[str, str] = {}

    # Generate video summary first
    summary_prompt = get_summary_prompt()
    try:
        results["video_summary"] = _call_model(
            client, model,
            summary_prompt["system"],
            summary_prompt["user"],
            video_b64, mime_type,
        )
        logger.info("Video summary generated successfully.")
    except Exception as e:
        logger.error("Failed to generate video summary: %s", e)
        results["video_summary"] = "Unable to generate video summary."

    # Generate captions for each requested style
    for style in styles:
        prompt = get_style_prompt(style)
        try:
            caption = _call_model(
                client, model,
                prompt["system"],
                prompt["user"],
                video_b64, mime_type,
            )
            results[style] = caption
            logger.info("Caption generated for style '%s'.", style)
        except Exception as e:
            logger.error("Failed to generate '%s' caption: %s", style, e)
            results[style] = f"Error generating {style} caption. Please try again."

    return results
