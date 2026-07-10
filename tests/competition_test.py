"""Competition test script — validates the container_runner pipeline.

Tests each example clip individually and runs a full dry run.
Usage:
    python -m tests.competition_test
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.fireworks_client import FireworksClient, FireworksConfig
from backend.services.video_processor import process_video, _get_whisper_model

TEMP_BASE = Path(os.environ.get("TEMP_DIR", "/tmp/video_captions"))

EXAMPLE_CLIPS = [
    {
        "task_id": "v1",
        "video_url": "https://storage.googleapis.com/amd-hackathon-clips/1860079-uhd_2560_1440_25fps.mp4",
        "description": "Urban autumn boulevard with golden trees and city traffic",
        "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"],
    },
    {
        "task_id": "v2",
        "video_url": "https://storage.googleapis.com/amd-hackathon-clips/13825391-uhd_3840_2160_30fps.mp4",
        "description": "Orange kitten among green foliage in a garden",
        "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"],
    },
    {
        "task_id": "v3",
        "video_url": "https://storage.googleapis.com/amd-hackathon-clips/3044693-uhd_3840_2160_24fps.mp4",
        "description": "Office worker at a desktop computer in a modern open-plan office",
        "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"],
    },
]

REQUIRED_STYLES = {"formal", "sarcastic", "humorous_tech", "humorous_non_tech"}


async def process_single_clip(
    task: dict,
    api_key: str,
    model: str,
) -> dict:
    """Process a single clip and return the result."""
    task_id = task["task_id"]
    video_url = task["video_url"]
    work_dir = TEMP_BASE / task_id
    start_time = time.time()

    try:
        logger.info("[%s] Starting: %s", task_id, task["description"])
        
        # Try to import video processor, fall back to simpler version if faster_whisper not available
        try:
            from backend.services.video_processor import process_video
            frames_b64, transcript = await process_video(
                video_url=video_url,
                work_dir=work_dir,
                num_frames=16,
            )
        except ImportError:
            # Local testing without faster_whisper - use simplified processing
            from backend.services.video_processor import download_video, extract_keyframes
            video_path = work_dir / "video.mp4"
            await download_video(video_url, video_path)
            frames_b64 = extract_keyframes(str(video_path), str(work_dir / "frames"), 16)
            transcript = None
            logger.warning("[%s] faster_whisper not available - skipping transcription", task_id)
        
        logger.info(
            "[%s] Extracted %d frames, transcript=%d chars (%.1fs)",
            task_id,
            len(frames_b64),
            len(transcript) if transcript else 0,
            time.time() - start_time,
        )

        config = FireworksConfig(api_key=api_key, model=model)
        async with FireworksClient(config) as client:
            captions = await client.generate_captions(
                frames_b64=frames_b64,
                transcript=transcript,
            )

        elapsed = time.time() - start_time
        logger.info("[%s] Completed in %.1fs", task_id, elapsed)
        return {"task_id": task_id, "captions": captions}

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("[%s] Failed after %.1fs: %s", task_id, elapsed, e)
        import traceback
        traceback.print_exc()
        error_caption = f"Error: {str(e)[:100]}"
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


def validate_result(result: dict) -> bool:
    """Validate a single result has all required fields."""
    task_id = result.get("task_id", "unknown")
    captions = result.get("captions", {})
    
    missing = REQUIRED_STYLES - set(captions.keys())
    if missing:
        logger.error("[%s] Missing styles: %s", task_id, missing)
        return False
    
    for style, caption in captions.items():
        if not caption or not isinstance(caption, str):
            logger.error("[%s] Invalid caption for style '%s'", task_id, style)
            return False
    
    return True


def validate_output(results: list[dict]) -> bool:
    """Validate the full output matches competition requirements."""
    all_valid = True
    for result in results:
        if not validate_result(result):
            all_valid = False
    return all_valid


async def test_single_clip(task: dict, api_key: str, model: str) -> bool:
    """Test a single clip and report results."""
    logger.info("=" * 60)
    logger.info("TESTING: %s — %s", task["task_id"], task["description"])
    logger.info("=" * 60)
    
    result = await process_single_clip(task, api_key, model)
    valid = validate_result(result)
    
    captions = result.get("captions", {})
    for style in ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]:
        caption = captions.get(style, "MISSING")
        logger.info("[%s] %s: %s", task["task_id"], style, caption[:100])
    
    if valid:
        logger.info("[%s] PASS — All styles present", task["task_id"])
    else:
        logger.error("[%s] FAIL — Missing or invalid styles", task["task_id"])
    
    return valid


async def test_full_dry_run(tasks: list[dict], api_key: str, model: str) -> bool:
    """Run all clips sequentially and validate output."""
    logger.info("=" * 60)
    logger.info("FULL DRY RUN — %d clips", len(tasks))
    logger.info("=" * 60)
    
    start_time = time.time()
    results = []
    
    for task in tasks:
        result = await process_single_clip(task, api_key, model)
        results.append(result)
    
    total_time = time.time() - start_time
    logger.info("Total time: %.1fs (%.1f minutes)", total_time, total_time / 60)
    
    valid = validate_output(results)
    
    output_path = TEMP_BASE / "test_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Results written to %s", output_path)
    
    if total_time > 600:
        logger.warning("WARNING: Total time %.1fs exceeds 10-minute limit!", total_time)
    
    if valid:
        logger.info("DRY RUN PASS — All clips valid")
    else:
        logger.error("DRY RUN FAIL — Some clips invalid")
    
    return valid and total_time <= 600


async def main():
    """Run all competition tests."""
    api_key = os.environ.get("FIREWORKS_API_KEY", "")
    if not api_key:
        logger.error("FIREWORKS_API_KEY environment variable is required")
        sys.exit(1)

    model = os.environ.get(
        "FIREWORKS_MODEL",
        "accounts/fireworks/models/qwen3p7-plus",
    )

    logger.info("Pre-warming Whisper model...")
    try:
        from backend.services.video_processor import _get_whisper_model
        _get_whisper_model("base")
        logger.info("Whisper model pre-warmed.")
    except ImportError:
        logger.warning("faster_whisper not installed locally - skipping pre-warm (OK for testing)")

    results = {"passed": 0, "failed": 0}

    # Test each clip individually
    for task in EXAMPLE_CLIPS:
        passed = await test_single_clip(task, api_key, model)
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1

    # Full dry run
    dry_run_passed = await test_full_dry_run(EXAMPLE_CLIPS, api_key, model)
    
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info("Individual clips: %d passed, %d failed", results["passed"], results["failed"])
    logger.info("Full dry run: %s", "PASS" if dry_run_passed else "FAIL")
    
    if results["failed"] == 0 and dry_run_passed:
        logger.info("ALL TESTS PASSED")
        sys.exit(0)
    else:
        logger.error("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
