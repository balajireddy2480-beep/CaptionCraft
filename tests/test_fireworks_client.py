"""Regression tests for Fireworks response parsing and validation."""

import pytest

from backend.services.fireworks_client import FireworksClient, FireworksConfig


def test_parse_formatted_partial_response_preserves_recovered_captions():
    """Formatted text with 3 captions should be returned for targeted retry."""
    content = """
    **Formal**: A clear view of a person presenting the video subject in a calm, factual way.
    **Sarcastic**: Because apparently this moment demanded its own cinematic universe.
    **Tech Humor**: The scene is buffering confidence like a frontend waiting on prod logs.
    """

    result = FireworksClient._parse_caption_response(content)

    assert set(result) == {"formal", "sarcastic", "humorous_tech"}
    assert result["humorous_tech"].startswith("The scene is buffering")


def test_parse_json_accepts_tech_humor_alias():
    content = """
    ```json
    {
      "formal": "A person demonstrates the subject of the video with clear visual context.",
      "sarcastic": "A dramatic reminder that everyday events can still receive a spotlight.",
      "tech_humor": "Looks like the main thread finally got around to rendering the scene.",
      "humorous_non_tech": "This is the kind of moment that deserves a snack break and applause."
    }
    ```
    """

    result = FireworksClient._parse_caption_response(content)

    assert "tech_humor" not in result
    assert set(result) == {"formal", "sarcastic", "humorous_tech", "humorous_non_tech"}


@pytest.mark.asyncio
async def test_generate_captions_retries_only_missing_caption(monkeypatch):
    config = FireworksConfig(api_key="test", model="accounts/fireworks/models/qwen3p7-plus")
    client = FireworksClient(config)
    payloads = []

    responses = [
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"formal":"A factual caption about the video subject.",'
                            '"sarcastic":"A dry caption about the same video subject.",'
                            '"humorous_tech":"A tech flavored caption about the video subject."}'
                        )
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"humorous_non_tech":"An everyday joke caption about the video subject."}'
                        )
                    }
                }
            ]
        },
    ]

    async def fake_send(payload, headers):
        payloads.append(payload)
        return responses.pop(0)

    monkeypatch.setattr(client, "_send_with_retry", fake_send)
    client._client = object()

    result = await client.generate_captions(frames_b64=[], transcript="short transcript")

    assert set(result) == {"formal", "sarcastic", "humorous_tech", "humorous_non_tech"}
    targeted_prompt = payloads[1]["messages"][0]["content"]
    assert "humorous_non_tech" in targeted_prompt
    assert "formal" not in targeted_prompt.split("Please generate captions for ONLY these styles:", 1)[1].split(".", 1)[0]
