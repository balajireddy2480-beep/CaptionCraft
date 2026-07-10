"""Async Fireworks AI client with retry logic for video captioning."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from backend.services.prompt_builder import build_user_prompt, get_system_prompt
from backend.core.logging import get_logger

logger = get_logger(__name__)

FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"
FIREWORKS_CHAT_ENDPOINT = f"{FIREWORKS_BASE_URL}/chat/completions"

# Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
RETRY_BACKOFF = [1, 2, 4, 8, 16, 30]
MAX_RETRIES = len(RETRY_BACKOFF)
EXPECTED_CAPTION_KEYS = ("formal", "sarcastic", "humorous_tech", "humorous_non_tech")
EXPECTED_CAPTION_KEY_SET = set(EXPECTED_CAPTION_KEYS)


class FireworksAIError(Exception):
    """Base exception for Fireworks AI API errors."""


class FireworksAuthError(FireworksAIError):
    """Raised on 401/403 authentication errors."""


class FireworksRateLimitError(FireworksAIError):
    """Raised on 429 rate limit errors."""


class FireworksServerError(FireworksAIError):
    """Raised on 5xx server errors."""


@dataclass
class FireworksConfig:
    """Configuration for the Fireworks AI client.

    Attributes:
        api_key: Fireworks API key.
        model: Model ID for caption generation.
        base_url: Base URL for the Fireworks API.
        max_tokens: Maximum tokens in the response.
        temperature: Sampling temperature.
        timeout: HTTP client timeout in seconds.
    """
    api_key: str
    model: str = "accounts/fireworks/models/qwen3p7-plus"
    base_url: str = FIREWORKS_BASE_URL
    max_tokens: int = 1024
    temperature: float = 0.3
    timeout: float = 120.0


class FireworksClient:
    """Reusable async HTTP client for the Fireworks AI API.

    Usage as a context manager::

        async with FireworksClient(config) as client:
            result = await client.generate_captions(frames_b64=frames)

    The underlying :class:`httpx.AsyncClient` is reused across calls within the
    context, providing connection pooling.
    """

    def __init__(self, config: FireworksConfig) -> None:
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> FireworksClient:
        self._client = httpx.AsyncClient(timeout=self.config.timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def generate_captions(
        self,
        frames_b64: list[str],
        transcript: str | None = None,
        style_hints: dict[str, str] | None = None,
        requested_styles: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, str]:
        """Call Fireworks AI to generate captions from video frames and transcript.

        Retries the request if the response cannot be parsed as valid captions,
        up to 3 times with targeted prompts for any missing styles.

        Args:
            frames_b64: Base64-encoded JPEG frames from the video.
            transcript: Optional audio transcript.
            style_hints: Optional style-specific instructions.

        Returns:
            Dict with keys ``formal``, ``sarcastic``, ``humorous_tech``,
            ``humorous_non_tech``.

        Raises:
            FireworksAuthError: If the API key is invalid.
            FireworksAIError: For non-recoverable API errors.
        """
        headers = self._build_headers()
        last_error: str | None = None
        expected_keys = self._normalize_requested_keys(requested_styles)
        accumulated_captions: dict[str, str] = {}

        for attempt in range(3):
            missing_keys = expected_keys - accumulated_captions.keys()
            if not missing_keys:
                break
                
            if attempt == 0:
                messages = self._build_messages(
                    frames_b64, transcript, style_hints, sorted(expected_keys)
                )
            else:
                logger.info(
                    "Retrying with targeted prompt for missing keys",
                    attempt=attempt + 1,
                    missing_keys=list(missing_keys),
                    accumulated_keys=list(accumulated_captions.keys()),
                )
                messages = self._build_targeted_messages(
                    frames_b64, transcript, accumulated_captions, missing_keys
                )

            payload = self._build_payload(messages)
            
            # Log the request details without base64 images to keep logs clean
            logger.info(
                "FIREWORKS_REQUEST",
                attempt=attempt + 1,
                model=payload.get("model"),
                max_tokens=payload.get("max_tokens"),
                temperature=payload.get("temperature"),
                num_frames=len(frames_b64),
                missing_keys_requested=list(missing_keys),
            )
            
            start_time = time.perf_counter()
            try:
                data = await self._send_with_retry(payload, headers)
            except Exception as e:
                logger.error(
                    "FIREWORKS_RESPONSE_FAILED",
                    attempt=attempt + 1,
                    error=str(e),
                    elapsed_ms=round((time.perf_counter() - start_time) * 1000, 2),
                )
                raise
                
            content = data["choices"][0]["message"]["content"]
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            logger.info(
                "FIREWORKS_RESPONSE",
                attempt=attempt + 1,
                content_length=len(content),
                elapsed_ms=elapsed_ms,
            )

            try:
                result = self._parse_caption_response(content, expected_keys)
                logger.info(
                    "JSON_PARSE",
                    status="SUCCESS",
                    parsed_keys=list(result.keys()),
                )
                
                # Filter out fallback text or short invalid strings
                valid_new_captions = {}
                for key, val in result.items():
                    if val and not any(f in val.lower() for f in ["could not generate", "caption generation failed"]) and len(val) >= 10:
                        valid_new_captions[key] = val
                        
                accumulated_captions.update(valid_new_captions)
                
                logger.info(
                    "VALIDATION",
                    status="PARTIAL_OR_COMPLETE",
                    valid_keys_found=list(valid_new_captions.keys()),
                    total_accumulated_keys=list(accumulated_captions.keys()),
                )
                
                # Check if we now have all 4
                if expected_keys.issubset(accumulated_captions.keys()):
                    return {key: accumulated_captions[key] for key in EXPECTED_CAPTION_KEYS if key in expected_keys}
                    
                # Otherwise, raise FireworksAIError to trigger retry for remaining keys
                remaining = expected_keys - accumulated_captions.keys()
                raise FireworksAIError(f"Missing keys: {remaining}")
                
            except FireworksAIError as e:
                last_error = str(e)
                logger.warning(
                    "Caption validation failed",
                    attempt=attempt + 1,
                    error=last_error,
                )
                continue

        missing_keys = expected_keys - accumulated_captions.keys()

        raise FireworksAIError(
            f"Failed to generate valid captions after 3 attempts. "
            f"Missing: {', '.join(sorted(missing_keys))}. "
            f"Recovered: {', '.join(sorted(accumulated_captions)) or 'none'}. "
            f"Last error: {last_error}"
        )

    def _build_targeted_messages(
        self,
        frames_b64: list[str],
        transcript: str | None,
        accumulated_captions: dict[str, str],
        missing_keys: set[str],
    ) -> list[dict[str, Any]]:
        """Build messages asking the model to generate ONLY the missing captions."""
        system_prompt = (
            "You are an expert video analyst and caption writer.\n\n"
            "CRITICAL: You MUST return ONLY a valid JSON object. "
            "Do NOT include any analysis, explanations, markdown, or text outside the JSON.\n\n"
            "Your task is to generate the MISSING captions for the video in the specified style(s).\n\n"
            f"Please generate captions for ONLY these styles: {', '.join(sorted(missing_keys))}.\n\n"
            "All requested keys are mandatory. Spell each key exactly as requested. "
            "Use humorous_tech, never tech_humor.\n\n"
            "Output format (return a JSON object with only the missing keys):\n"
            "{" + ", ".join(f'"{key}": "..."' for key in sorted(missing_keys)) + "}"
        )
        
        user_prompt_parts = [
            "We have already successfully generated captions for these styles:\n"
            + json.dumps(accumulated_captions, indent=2)
            + f"\n\nPlease analyze the video frames and generate captions ONLY for the missing style(s): {', '.join(sorted(missing_keys))}."
        ]
        if transcript:
            user_prompt_parts.append(f"\n\nAudio context: {transcript}")
            
        content_parts: list[dict[str, Any]] = [
            {"type": "text", "text": "\n\n".join(user_prompt_parts)},
        ]
        for frame_b64 in frames_b64:
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame_b64}",
                    "detail": "auto",
                },
            })
            
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_parts},
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        frames_b64: list[str],
        transcript: str | None = None,
        style_hints: dict[str, str] | None = None,
        requested_styles: list[str] | tuple[str, ...] | None = None,
    ) -> list[dict[str, Any]]:
        """Build the messages array for the chat completion API."""
        system_prompt = get_system_prompt()
        user_prompt = build_user_prompt(transcript, style_hints, requested_styles)

        content_parts: list[dict[str, Any]] = [
            {"type": "text", "text": user_prompt},
        ]

        for frame_b64 in frames_b64:
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame_b64}",
                    "detail": "auto",
                },
            })

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_parts},
        ]

    def _build_payload(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Build the request payload."""
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        # Only add response_format if the model supports it
        # Some models don't support this parameter
        if "qwen" in self.config.model.lower() or "llama" in self.config.model.lower():
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _build_headers(self) -> dict[str, str]:
        """Build the request headers."""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _send_with_retry(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Send the request with exponential-backoff retry.

        Retries on 429 (rate limit), 5xx (server error), and network/timeout
        errors.  Raises immediately on 401/403 (auth errors).  Respects the
        ``Retry-After`` header when present on rate-limit responses.
        """
        client = self._client
        if client is None:
            raise RuntimeError("FireworksClient must be used as an async context manager")

        last_exception: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await client.post(
                    FIREWORKS_CHAT_ENDPOINT,
                    json=payload,
                    headers=headers,
                )

                if response.status_code == 200:
                    return response.json()

                if response.status_code in (401, 403):
                    raise FireworksAuthError(
                        f"Fireworks AI authentication failed: {response.text}"
                    )

                if response.status_code == 429 or response.status_code >= 500:
                    wait = self._retry_after(response, attempt)

                    error_cls = (
                        FireworksRateLimitError if response.status_code == 429
                        else FireworksServerError
                    )
                    last_exception = error_cls(
                        f"{'Rate limited' if response.status_code == 429 else f'Server error {response.status_code}'}: {response.text}"
                    )

                    logger.warning(
                        "FIREWORKS_RETRY",
                        attempt=attempt + 1,
                        max_attempts=MAX_RETRIES + 1,
                        status_code=response.status_code,
                        wait_seconds=wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                raise FireworksAIError(
                    f"Unexpected status {response.status_code}: {response.text}"
                )

            except (httpx.TimeoutException, httpx.RequestError) as e:
                wait = RETRY_BACKOFF[attempt] if attempt < MAX_RETRIES else 30
                last_exception = e
                logger.warning(
                    "FIREWORKS_REQUEST_ERROR",
                    attempt=attempt + 1,
                    max_attempts=MAX_RETRIES + 1,
                    error=str(e),
                    wait_seconds=wait,
                )
                await asyncio.sleep(wait)

        raise FireworksAIError(
            f"Fireworks AI request failed after {MAX_RETRIES + 1} attempts. "
            f"Last error: {last_exception}"
        ) from last_exception

    @staticmethod
    def _retry_after(response: httpx.Response, attempt: int) -> float:
        """Return the wait time respecting the ``Retry-After`` header when present."""
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return float(retry_after)
            except ValueError:
                pass
        return float(RETRY_BACKOFF[attempt] if attempt < MAX_RETRIES else 30)

    @staticmethod
    def _parse_caption_response(
        content: str,
        expected_keys: set[str] | None = None,
    ) -> dict[str, str]:
        """Parse the JSON response from Fireworks AI.

        Args:
            content: The raw text response from the model.

        Returns:
            Dict with caption keys.

        Raises:
            FireworksAIError: If the response cannot be parsed as valid JSON.
        """
        cleaned = content.strip()
        
        # Try to extract JSON from the response if it's embedded in text
        # Look for JSON object pattern
        json_start = cleaned.find('{')
        json_end = cleaned.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            # Extract the JSON portion
            json_str = cleaned[json_start:json_end + 1]
            try:
                result = json.loads(json_str)
                result = FireworksClient._normalize_caption_keys(result)
                
                # Check if we got the expected keys
                if any(key in result for key in EXPECTED_CAPTION_KEYS):
                    cleaned = json.dumps(result)
            except json.JSONDecodeError:
                # If extraction fails, continue with original content
                pass
        
        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("\n", 1)[0] if "\n" in cleaned else cleaned
            cleaned = cleaned.strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        try:
            result = json.loads(cleaned)
            result = FireworksClient._normalize_caption_keys(result)
        except json.JSONDecodeError:
            # Try to repair partial JSON (truncated response from model)
            result = FireworksClient._try_repair_partial_json(cleaned, expected_keys)
            if result:
                logger.info("JSON_PARSE", status="REPAIRED_PARTIAL_JSON", parsed_keys=list(result.keys()))
                return result

            # Try to extract captions from formatted text as fallback
            result = FireworksClient._extract_captions_from_text(content, expected_keys)
            if result:
                logger.info("JSON_PARSE", status="EXTRACTED_FROM_TEXT", parsed_keys=list(result.keys()))
                return result
            
            # Check if the response contains analysis text instead of JSON
            if "formal" not in cleaned.lower() and "sarcastic" not in cleaned.lower():
                raise FireworksAIError(
                    f"Model returned analysis text instead of JSON. "
                    f"Raw content: {content[:300]}..."
                )
            raise FireworksAIError(
                f"Failed to parse AI response as JSON. "
                f"Raw content: {content[:500]}"
            )

        return result

    @staticmethod
    def _normalize_caption_keys(result: Any) -> dict[str, str]:
        """Normalize accepted model key aliases to the app's canonical keys."""
        if not isinstance(result, dict):
            raise FireworksAIError(f"Expected JSON object, got {type(result).__name__}.")

        normalized: dict[str, str] = {}
        for key, value in result.items():
            canonical_key = "humorous_tech" if key == "tech_humor" else key
            if canonical_key not in EXPECTED_CAPTION_KEY_SET:
                continue
            if isinstance(value, str):
                caption = value.strip()
            elif value is None:
                caption = ""
            else:
                caption = str(value).strip()
            normalized[canonical_key] = caption
        return normalized

    @staticmethod
    def _normalize_requested_keys(
        requested_styles: list[str] | tuple[str, ...] | None,
    ) -> set[str]:
        if not requested_styles:
            return set(EXPECTED_CAPTION_KEYS)

        normalized: set[str] = set()
        for style in requested_styles:
            canonical = "humorous_tech" if style == "tech_humor" else style
            if canonical in EXPECTED_CAPTION_KEY_SET:
                normalized.add(canonical)
        return normalized or set(EXPECTED_CAPTION_KEYS)
    
    @staticmethod
    def _try_repair_partial_json(
        content: str,
        expected_keys: set[str] | None = None,
    ) -> dict[str, str] | None:
        """Try to extract completed key-value pairs from truncated JSON."""
        import re
        
        result = {}
        styles = [key for key in EXPECTED_CAPTION_KEYS if expected_keys is None or key in expected_keys]
        
        # Match completed "key": "value" pairs in JSON format
        # Handle escaped quotes within values
        for style in styles:
            # Check for either the standard key name or the alternative 'tech_humor' key
            style_pattern = style
            if style == "humorous_tech":
                style_pattern = "(?:humorous_tech|tech_humor)"
            pattern = rf'"{style_pattern}"\s*:\s*"((?:[^"\\]|\\.)*)"'
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                value = match.group(1)
                # Unescape JSON escape sequences
                value = value.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
                if len(value) >= 10:
                    result[style] = value
        
        min_required = 1 if expected_keys and len(expected_keys) == 1 else 2
        if len(result) >= min_required:
            return result
        
        return None
    
    @staticmethod
    def _extract_captions_from_text(
        content: str,
        expected_keys: set[str] | None = None,
    ) -> dict[str, str] | None:
        """Try to extract captions from formatted text if JSON parsing fails.
        
        Looks for patterns like:
        - **Formal**: caption text
        - 1. **Formal**: caption text
        - Formal: caption text
        """
        import re
        
        result = {}
        styles = [key for key in EXPECTED_CAPTION_KEYS if expected_keys is None or key in expected_keys]
        
        # Split content into lines for easier processing
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            for style in styles:
                # Check if this line contains a style label
                style_patterns = [
                    rf'\*\*{style}\*\*:',
                    rf'\*\*{style}\s+caption\*\*:',
                    rf'\*\*{style.replace("_", " ").title()}\*\*:',
                    rf'\*\*{style.replace("_", " ").title()}\s+Caption\*\*:',
                    rf'{style}:',
                    rf'{style}\s+caption:',
                    rf'{style.replace("_", " ").title()}:',
                    rf'{style.replace("_", " ").title()}\s+Caption:',
                ]
                if style == "humorous_non_tech":
                    style_patterns.extend([
                        r'\*\*Humorous Non-Tech\*\*:',
                        r'Humorous Non-Tech:',
                        r'\*\*Non-Tech\*\*:',
                        r'Non-Tech:',
                        r'\*\*humorous-non-tech\*\*:',
                        r'humorous-non-tech:',
                    ])
                elif style == "humorous_tech":
                    style_patterns.extend([
                        r'\*\*Tech Humor\*\*:',
                        r'Tech Humor:',
                        r'\*\*Tech\*\*:',
                        r'Tech:',
                        r'\*\*tech_humor\*\*:',
                        r'tech_humor:',
                    ])
                
                for pattern in style_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        # Extract caption text after the label
                        match = re.search(rf'{pattern}\s*(.+)', line, re.IGNORECASE)
                        if match:
                            caption = match.group(1).strip()
                            # Skip if it's a meta-comment or too short
                            if (caption and len(caption) > 20 and 
                                not any(meta in caption.lower() for meta in ['needs to', '(good)', '(bad)', 'drafting', 'refining'])):
                                # Clean up the caption - remove quotes if present
                                caption = caption.strip('"\'')
                                result[style] = caption
                            elif not caption or len(caption) <= 20:
                                # Caption might be on next lines
                                caption_lines = []
                                for j in range(i + 1, min(i + 5, len(lines))):
                                    next_line = lines[j].strip()
                                    # Stop if we hit another style label or empty line
                                    if not next_line or any(re.search(rf'\*\*{s}\*\*:', next_line, re.IGNORECASE) for s in styles):
                                        break
                                    # Skip meta-comments
                                    if any(meta in next_line.lower() for meta in ['needs to', '(good)', '(bad)', 'drafting', 'refining']):
                                        continue
                                    caption_lines.append(next_line)
                                if caption_lines:
                                    caption = ' '.join(caption_lines).strip('"\'')
                                    if len(caption) > 20:
                                        result[style] = caption

        if expected_keys and len(expected_keys) == 1 and not result:
            only_style = next(iter(expected_keys))
            result.update(FireworksClient._extract_single_caption_from_analysis(content, only_style))
        
        # Only return if we found at least 2 styles
        min_required = 1 if expected_keys and len(expected_keys) == 1 else 2
        if len(result) >= min_required:
            logger.info("JSON_PARSE", status="EXTRACTED_FROM_FORMATTED_TEXT", parsed_keys=list(result.keys()))
            return result
        
        return None

    @staticmethod
    def _extract_single_caption_from_analysis(content: str, style: str) -> dict[str, str]:
        """Extract a single requested caption from chatty model analysis text."""
        import re

        label = style.replace("_", " ")
        patterns = [
            rf'(?:final\s+)?{re.escape(label)}\s+caption\s*[:\-]\s*["“]?(.+?)["”]?(?:\n|$)',
            rf'(?:final\s+)?caption\s*[:\-]\s*["“]?(.+?)["”]?(?:\n|$)',
            rf'return(?:ing)?\s*[:\-]\s*["“]?(.+?)["”]?(?:\n|$)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, content, flags=re.IGNORECASE)
            for candidate in reversed(matches):
                caption = candidate.strip().strip('"\'` ')
                if len(caption) < 20:
                    continue
                lowered = caption.lower()
                if any(meta in lowered for meta in ["the user wants", "analyze", "json", "caption should"]):
                    continue
                return {style: caption}
        return {}


async def generate_captions(
    frames_b64: list[str],
    transcript: str | None = None,
    style_hints: dict[str, str] | None = None,
    requested_styles: list[str] | tuple[str, ...] | None = None,
) -> dict[str, str]:
    """Convenience wrapper that creates a :class:`FireworksClient` and generates
    captions.

    Builds configuration from the application :class:`Settings`.  For advanced
    usage (e.g., custom config, or connection pooling across many calls), use
    :class:`FireworksClient` directly.

    Args:
        frames_b64: Base64-encoded JPEG frames from the video.
        transcript: Optional audio transcript.
        style_hints: Optional style-specific instructions.

    Returns:
        Dict with caption keys.
    """
    from backend.core.config import get_settings

    settings = get_settings()
    config = FireworksConfig(
        api_key=settings.fireworks_api_key,
        model=settings.fireworks_model,
        max_tokens=settings.fireworks_max_tokens,
    )
    async with FireworksClient(config) as client:
        return await client.generate_captions(
            frames_b64=frames_b64,
            transcript=transcript,
            style_hints=style_hints,
            requested_styles=requested_styles,
        )
