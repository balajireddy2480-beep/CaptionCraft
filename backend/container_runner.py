"""Competition container entry point.

Reads /input/tasks.json, processes each video, writes /output/results.json.
No dependency on PostgreSQL, Redis, or Celery.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from backend.services.fireworks_client import FireworksClient, FireworksConfig
from backend.services.video_processor import process_video

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

INPUT_PATH = os.environ.get("INPUT_PATH", "input/tasks.json")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "output/results.json")
TEMP_BASE = os.environ.get("TEMP_DIR", "tmp/video_captions")


async def process_task(
    task: dict,
    api_key: str,
    model: str,
) -> dict:
    """Process a single video task and return the result.

    Args:
        task: Task dict with task_id, video_url, and styles.
        api_key: Fireworks AI API key.
        model: Fireworks AI model ID.

    Returns:
        Result dict with task_id and captions.
    """
    task_id = task["task_id"]
    video_url = task["video_url"]
    work_dir = Path(TEMP_BASE) / task_id
    start_time = time.time()

    try:
        logger.info("Task %s: starting video processing", task_id)
        frames_b64, transcript = await process_video(
            video_url=video_url,
            work_dir=work_dir,
            num_frames=16,
        )
        logger.info(
            "Task %s: extracted %d frames, transcript=%d chars",
            task_id,
            len(frames_b64),
            len(transcript) if transcript else 0,
        )

        logger.info("Task %s: generating captions via Fireworks AI", task_id)
        config = FireworksConfig(api_key=api_key, model=model)
        async with FireworksClient(config) as client:
            captions = await client.generate_captions(
                frames_b64=frames_b64,
                transcript=transcript,
            )

        elapsed = time.time() - start_time
        logger.info("Task %s: captions generated successfully in %.1fs", task_id, elapsed)
        return {"task_id": task_id, "captions": captions}

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("Task %s failed after %.1fs: %s\n%s", task_id, elapsed, e, traceback.format_exc())
        
        # Ensure all 4 styles are present even on error
        error_caption = f"Unable to generate caption: {str(e)[:100]}"
        return {
            "task_id": task_id,
            "captions": {
                "formal": error_caption,
                "sarcastic": error_caption,
                "humorous_tech": error_caption,
                "humorous_non_tech": error_caption,
            },
        }
    finally:
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)


def validate_result(result: dict) -> dict:
    """Ensure result has all required fields and styles."""
    required_styles = {"formal", "sarcastic", "humorous_tech", "humorous_non_tech"}
    
    if "captions" not in result:
        result["captions"] = {}
    
    missing = required_styles - set(result["captions"].keys())
    for style in missing:
        result["captions"][style] = "Caption generation failed"
    
    return result


async def main() -> None:
    """Main entry point: read tasks, process, write results."""
    api_key = os.environ.get("FIREWORKS_API_KEY", "")
    if not api_key:
        logger.error("FIREWORKS_API_KEY environment variable is required")
        sys.exit(1)

    model = os.environ.get(
        "FIREWORKS_MODEL",
        "accounts/fireworks/models/qwen3p7-plus",
    )

    # Pre-warm Whisper model to save time on first clip
    logger.info("Pre-warming Whisper model...")
    try:
        from backend.services.video_processor import _get_whisper_model
        _get_whisper_model("base")
        logger.info("Whisper model pre-warmed.")
    except ImportError:
        logger.warning("faster_whisper not installed - skipping pre-warm")

    logger.info("Reading tasks from %s", INPUT_PATH)
    with open(INPUT_PATH) as f:
        tasks = json.load(f)

    logger.info("Loaded %d task(s)", len(tasks))

    results = []
    for task in tasks:
        logger.info("Processing task %s", task["task_id"])
        result = await process_task(task, api_key, model)
        result = validate_result(result)
        results.append(result)

    Path(OUTPUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    logger.info("Results written to %s", OUTPUT_PATH)


if __name__ == "__main__":
    asyncio.run(main())
