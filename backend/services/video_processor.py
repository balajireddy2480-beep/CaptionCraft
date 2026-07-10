"""Shared video processing: download, frame extraction, and audio transcription."""

from __future__ import annotations

import base64
import logging
import os
import subprocess
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_whisper_model = None
_whisper_model_name = None


def _get_whisper_model(model_name: str):
    """Get or create a cached Whisper model instance.

    The model is loaded once and reused across tasks to avoid 10-30s load time.
    If the model name changes, the old model is replaced.
    """
    global _whisper_model, _whisper_model_name
    if _whisper_model is None or _whisper_model_name != model_name:
        from faster_whisper import WhisperModel
        logger.info("Loading Whisper model '%s' (first time or model changed)...", model_name)
        _whisper_model = WhisperModel(model_name, device="cpu", compute_type="int8")
        _whisper_model_name = model_name
        logger.info("Whisper model '%s' loaded and cached.", model_name)
    return _whisper_model


async def download_video(
    video_url: str,
    output_path: Path,
    max_size_bytes: int = 200 * 1024 * 1024,
) -> Path:
    """Download a video from a URL to a local path using streaming.

    Args:
        video_url: Public URL of the video.
        output_path: Local path to save the video.
        max_size_bytes: Maximum allowed file size in bytes.

    Returns:
        Path to the downloaded video file.

    Raises:
        ValueError: If the video exceeds the maximum size.
        httpx.HTTPStatusError: If the download fails.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(
        timeout=300.0,
        follow_redirects=True,
        max_redirects=5,
    ) as client:
        async with client.stream("GET", video_url, headers={"User-Agent": "VideoCaptioningAgent/1.0"}) as response:
            response.raise_for_status()
            
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > max_size_bytes:
                raise ValueError(
                    f"Video too large: {int(content_length) / (1024 * 1024):.1f} MB "
                    f"(max {max_size_bytes / (1024 * 1024):.0f} MB)"
                )
            
            total_size = 0
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    total_size += len(chunk)
                    if total_size > max_size_bytes:
                        raise ValueError(
                            f"Video too large: {total_size / (1024 * 1024):.1f} MB "
                            f"(max {max_size_bytes / (1024 * 1024):.0f} MB)"
                        )
                    f.write(chunk)
    
    logger.info("Downloaded %d bytes to %s", total_size, output_path)
    return output_path


def extract_keyframes(
    video_path: str,
    output_dir: str,
    num_frames: int = 16,
) -> list[str]:
    """Extract uniformly spaced keyframes from a video and return as base64 strings.

    Args:
        video_path: Path to the video file.
        output_dir: Directory to write frame JPEGs.
        num_frames: Number of frames to extract.

    Returns:
        List of base64-encoded JPEG frame strings.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    duration_cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        video_path,
    ]
    try:
        result = subprocess.run(
            duration_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        duration_str = result.stdout.strip()
    except FileNotFoundError:
        logger.warning("ffprobe not found. Falling back to ffmpeg for duration extraction.")
        duration_str = ""
    if not duration_str:
        # Fall back to ffmpeg to get duration
        fallback_cmd = [
            "ffmpeg",
            "-i", video_path,
            "-f", "null",
            "-",
        ]
        fallback = subprocess.run(
            fallback_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        import re
        match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", fallback.stderr)
        if match:
            h, m, s = match.groups()
            duration = float(h) * 3600 + float(m) * 60 + float(s)
        else:
            logger.warning("Could not determine video duration for %s, using default 30s", video_path)
            duration = 30.0
    else:
        duration = float(duration_str)

    interval = max(duration / num_frames, 0.5)

    output_pattern = os.path.join(output_dir, "frame_%03d.jpg")
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vf", f"fps=1/{interval},scale=1024:-1",
        "-frames:v", str(num_frames),
        "-q:v", "5",
        output_pattern,
    ]
    subprocess.run(ffmpeg_cmd, capture_output=True, timeout=120, check=True)

    frame_files = sorted(Path(output_dir).glob("frame_*.jpg"))
    frames_b64 = []
    for f in frame_files:
        frames_b64.append(base64.b64encode(f.read_bytes()).decode("utf-8"))

    logger.info("Extracted %d keyframes from %s", len(frames_b64), video_path)
    return frames_b64


def transcribe_audio(
    video_path: str,
    temp_dir: str,
    whisper_model: str = "base",
) -> str | None:
    """Extract audio from video and transcribe using faster-whisper.

    Args:
        video_path: Path to the video file.
        temp_dir: Directory for temporary audio file.
        whisper_model: Whisper model size (tiny, base, small, medium, large).

    Returns:
        Transcript text, or None if transcription fails.
    """
    temp_audio = os.path.join(temp_dir, "audio.wav")

    try:
        extract_cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            temp_audio,
        ]
        subprocess.run(extract_cmd, capture_output=True, timeout=120, check=True)

        model = _get_whisper_model(whisper_model)
        segments, _info = model.transcribe(temp_audio, beam_size=5)
        transcript_parts = []
        for seg in segments:
            transcript_parts.append(seg.text)
        transcript = " ".join(transcript_parts).strip()
        logger.info("Transcribed %d chars from %s", len(transcript), video_path)
        return transcript if transcript else None

    except Exception as e:
        logger.warning(
            "Audio transcription failed for %s: %s. Proceeding without transcript.",
            video_path,
            e,
        )
        return None


async def process_video(
    video_url: str,
    work_dir: Path,
    num_frames: int = 16,
    max_size_bytes: int = 200 * 1024 * 1024,
    whisper_model: str = "base",
) -> tuple[list[str], str | None]:
    """Full video processing pipeline: download, extract frames, transcribe.

    Args:
        video_url: Public URL of the video.
        work_dir: Working directory for temporary files.
        num_frames: Number of keyframes to extract.
        max_size_bytes: Maximum video file size.
        whisper_model: Whisper model size.

    Returns:
        Tuple of (frames_b64, transcript).
    """
    work_dir.mkdir(parents=True, exist_ok=True)

    video_path = work_dir / "video.mp4"
    await download_video(video_url, video_path, max_size_bytes)
    logger.info("Video downloaded to %s", video_path)

    frames_dir = work_dir / "frames"
    frames_b64 = extract_keyframes(str(video_path), str(frames_dir), num_frames)

    transcript = transcribe_audio(str(video_path), str(work_dir), whisper_model)

    return frames_b64, transcript
