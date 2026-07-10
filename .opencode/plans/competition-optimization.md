# Competition Optimization Plan

## Overview

Optimize the video captioning agent for the AMD hackathon competition. The agent must process 12 hidden clips (30s-2min each) in under 10 minutes, generating captions in 4 styles for each clip.

## Competition Requirements

| Requirement | Constraint |
|-------------|------------|
| Runtime | Max 10 minutes |
| Clips | 12 hidden (30s-2min) + 3 example |
| Output | `/output/results.json` - valid JSON |
| Styles | All 4 for every clip (missing = zero) |
| Image size | < 10GB compressed |
| Model | `accounts/fireworks/models/qwen3p7-plus` |
| Processing | Sequential (no parallelism) |
| Whisper | Keep `base` model |

## Scoring

Each caption scored on:
1. **Accuracy (0-1):** How faithfully caption reflects video content
2. **Style match (0-1):** How well caption matches requested tone

Final score = weighted average across all clips and styles.

## Current Issues

### Issue 1: Whisper Cold Start (10-30s lost on first clip)
- **Location:** `container_runner.py:53` → `video_processor.py:160`
- **Problem:** Whisper model loads on first clip, wasting 10-30s
- **Fix:** Pre-warm at container startup

### Issue 2: Frame Quality Too Low
- **Location:** `video_processor.py:114` - `scale=640:-1`
- **Location:** `fireworks_client.py:142` - `detail: "low"`
- **Problem:** 4K videos scaled to 640px loses too much detail for accurate captions
- **Fix:** Increase to 1024px, use `detail: "auto"`

### Issue 3: Prompt Too Basic
- **Location:** `prompt_builder.py:6-18`
- **Problem:** 10-line prompt gives minimal guidance for accuracy/style
- **Fix:** Detailed prompt with scene analysis instructions + style examples

### Issue 4: Download Loads Entire File into Memory
- **Location:** `video_processor.py:60-71`
- **Problem:** UHD videos (50-80MB) loaded entirely into RAM
- **Fix:** Use streaming download

### Issue 5: No Per-Clip Timing
- **Location:** `container_runner.py:111-114`
- **Problem:** No visibility into per-clip processing time
- **Fix:** Add timing logs

### Issue 6: Error Handling Gaps
- **Location:** `container_runner.py:76-86`
- **Problem:** Error captions are generic, may not have all 4 styles
- **Fix:** Ensure all 4 styles always present, even on error

## Implementation Plan

### Task 1: Pre-warm Whisper at Container Startup
**File:** `backend/container_runner.py`

**Changes:**
```python
# In main(), before processing loop:
from backend.services.video_processor import _get_whisper_model
logger.info("Pre-warming Whisper model...")
_get_whisper_model("base")
logger.info("Whisper model pre-warmed.")
```

**Impact:** Save 10-30s on first clip.

---

### Task 2: Increase Frame Resolution
**File:** `backend/services/video_processor.py`

**Changes:**
```python
# Line 114: Change scale from 640 to 1024
"-vf", f"fps=1/{interval},scale=1024:-1",
```

**File:** `backend/services/fireworks_client.py`

**Changes:**
```python
# Line 142: Change detail from "low" to "auto"
"detail": "auto",
```

**Impact:** Better accuracy scores (model can see more detail).

---

### Task 3: Rewrite System Prompt for Maximum Scores
**File:** `backend/services/prompt_builder.py`

**New System Prompt:**
```
You are an expert video analyst and caption writer. Your task is to:

1. CAREFULLY ANALYZE the video frames to understand:
   - Setting/location (indoor/outdoor, urban/nature, time of day)
   - Main subjects (people, animals, objects, vehicles)
   - Actions/movements (what is happening, camera movement)
   - Visual details (colors, lighting, textures, clothing)
   - Mood/atmosphere (energetic, calm, dramatic, peaceful)

2. Generate FOUR distinct captions, each in a different style:

   **formal** - Professional documentary narrator tone:
   - Use precise, descriptive language
   - Focus on factual observations
   - Avoid opinions or emotions
   - Example: "A golden retriever puppy explores a sunlit garden, 
     sniffing among lush green foliage while autumn leaves drift 
     in the background."

   **sarcastic** - Dry, ironic, witty observer:
   - Use understatement and deadpan delivery
   - Highlight absurdities with subtle mockery
   - Keep it clever, not mean
   - Example: "Oh look, another dog having the time of its life 
     outdoors. Groundbreaking content."

   **humorous_tech** - Software engineer's perspective:
   - Use programming metaphors and tech jargon
   - Reference coding, debugging, deployment, etc.
   - Make tech jokes that fit the scene
   - Example: "This puppy's exploration algorithm is running 
     at O(n) complexity - sniffing each plant sequentially 
     with no cache hits."

   **humorous_non_tech** - Everyday relatable humor:
   - Use puns, pop culture references, everyday observations
   - Make it accessible to non-technical audiences
   - Keep it light and fun
   - Example: "When you finally get outside but realize 
     you're more interested in the garden than your phone."

3. IMPORTANT RULES:
   - Each caption must accurately describe what's in the video
   - Each caption must be distinctly different in tone
   - Keep captions 1-3 sentences each
   - Return ONLY valid JSON, no markdown or explanations

Output Format:
{
  "formal": "...",
  "sarcastic": "...",
  "humorous_tech": "...",
  "humorous_non_tech": "..."
}
```

**New User Prompt:**
```
Analyze the provided video frames carefully.

First, identify:
- What is the main subject?
- What is the setting?
- What actions are happening?
- What visual details stand out?

Then generate four captions in the specified styles.

{if transcript}Audio Transcript (for context only):
{transcript}{endif}
```

**Impact:** Major improvement in both accuracy and style match scores.

---

### Task 4: Optimize Download with Streaming
**File:** `backend/services/video_processor.py`

**Changes:**
```python
async def download_video(
    video_url: str,
    output_path: Path,
    max_size_bytes: int = 200 * 1024 * 1024,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(
        timeout=300.0,
        follow_redirects=True,
        max_redirects=5,
    ) as client:
        async with client.stream("GET", video_url) as response:
            response.raise_for_status()
            
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > max_size_bytes:
                raise ValueError(
                    f"Video too large: {int(content_length) / (1024*1024):.1f} MB "
                    f"(max {max_size_bytes / (1024*1024):.0f} MB)"
                )
            
            total_size = 0
            with open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    total_size += len(chunk)
                    if total_size > max_size_bytes:
                        raise ValueError(
                            f"Video too large: {total_size / (1024*1024):.1f} MB "
                            f"(max {max_size_bytes / (1024*1024):.0f} MB)"
                        )
                    f.write(chunk)
    
    logger.info("Downloaded %d bytes to %s", total_size, output_path)
    return output_path
```

**Impact:** Lower memory usage, slightly faster for large files.

---

### Task 5: Add Per-Clip Timing
**File:** `backend/container_runner.py`

**Changes:**
```python
import time

async def process_task(task: dict, api_key: str, model: str) -> dict:
    task_id = task["task_id"]
    start_time = time.time()
    
    # ... existing code ...
    
    elapsed = time.time() - start_time
    logger.info("Task %s: completed in %.1fs", task_id, elapsed)
    
    return {"task_id": task_id, "captions": captions}
```

**Impact:** Visibility into performance, helps debug timing issues.

---

### Task 6: Improve Error Handling
**File:** `backend/container_runner.py`

**Changes:**
```python
except Exception as e:
    logger.error("Task %s failed: %s\n%s", task_id, e, traceback.format_exc())
    
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
```

**Impact:** Prevents zero scores from missing styles.

---

### Task 7: Validate Output Format
**File:** `backend/container_runner.py`

**Changes:**
```python
def validate_result(result: dict) -> dict:
    """Ensure result has all required fields."""
    required_styles = {"formal", "sarcastic", "humorous_tech", "humorous_non_tech"}
    
    if "captions" not in result:
        result["captions"] = {}
    
    missing = required_styles - set(result["captions"].keys())
    for style in missing:
        result["captions"][style] = "Caption generation failed"
    
    return result

# In main():
results = []
for task in tasks:
    result = await process_task(task, api_key, model)
    result = validate_result(result)  # Validate before appending
    results.append(result)
```

**Impact:** Guarantees valid output structure.

---

### Task 8: Test with Example Clips
**File:** `tests/competition_test.py` (new)

**Test Plan:**
1. Test clip v1 (urban autumn boulevard)
2. Test clip v2 (orange kitten)
3. Test clip v3 (office worker)
4. Full dry run with all 3 clips

**For each clip:**
- Verify captions describe actual content
- Verify all 4 styles are distinct
- Measure processing time
- Validate JSON output

---

## Execution Order

| Step | Task | File | Impact |
|------|------|------|--------|
| 1 | Pre-warm Whisper | `container_runner.py` | Save 10-30s |
| 2 | Increase frame resolution | `video_processor.py`, `fireworks_client.py` | Better accuracy |
| 3 | Rewrite prompts | `prompt_builder.py` | Major score boost |
| 4 | Optimize download | `video_processor.py` | Lower memory |
| 5 | Add timing | `container_runner.py` | Visibility |
| 6 | Improve error handling | `container_runner.py` | Prevent zeros |
| 7 | Validate output | `container_runner.py` | Guarantee valid JSON |
| 8 | Test clips | `tests/competition_test.py` | Validation |

## Time Budget (After Optimizations)

| Step | Time |
|------|------|
| Pre-warm Whisper | 10s (one-time) |
| Download per clip | 5-10s |
| Extract frames per clip | 3-5s |
| Transcribe per clip | 30-50s |
| Fireworks API per clip | 10-20s |
| **Total per clip** | **48-85s** |
| **12 clips total** | **576-1020s = 9.6-17min** |

**Risk:** Still tight. If clips are 2min each, we may exceed 10 minutes.

**Mitigation (if needed):**
- Reduce frames from 16 to 12
- Reduce frame resolution to 768px
- Use Whisper `tiny` instead of `base`

## Files to Modify

| File | Changes |
|------|---------|
| `backend/container_runner.py` | Pre-warm Whisper, timing, error handling, validation |
| `backend/services/video_processor.py` | Frame resolution, streaming download |
| `backend/services/fireworks_client.py` | Detail level |
| `backend/services/prompt_builder.py` | Complete rewrite |
| `tests/competition_test.py` | New test file |

## Success Criteria

- [ ] All 3 example clips produce accurate captions
- [ ] All 4 styles are distinct for each clip
- [ ] Total time for 3 clips < 5 minutes (extrapolates to < 10min for 12)
- [ ] Output JSON is valid and complete
- [ ] Exit code 0 on success
