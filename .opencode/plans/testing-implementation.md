# Comprehensive Testing & Caption Generation Plan

## Overview

This plan ensures captions are generated correctly through comprehensive testing at all levels: end-to-end, integration, unit, and frontend.

---

## Phase 1: Test Infrastructure Setup

### 1.1 Test Video Organization

**Location:** `tests/fixtures/videos/`

Create a structured test video library:

```
tests/fixtures/videos/
├── small/
│   ├── test_5s.mp4          # 5 seconds, 2MB
│   └── test_10s.mp4         # 10 seconds, 4MB
├── medium/
│   ├── test_30s.mp4         # 30 seconds, 10MB
│   └── test_60s.mp4         # 60 seconds, 15MB
├── edge_cases/
│   ├── no_audio.mp4         # Video without audio track
│   ├── silent.mp4           # Video with silent audio
│   ├── fast_motion.mp4      # High frame rate video
│   └── low_resolution.mp4   # 240p video
├── formats/
│   ├── test.mov             # QuickTime format
│   ├── test.webm            # WebM format
│   └── test.avi             # AVI format
└── invalid/
    ├── too_large.mp4        # 30MB (exceeds limit)
    ├── corrupted.mp4        # Broken file
    └── not_video.txt        # Non-video file
```

**Action:** Create a script to generate or download test videos if needed.

### 1.2 Test Configuration

**File:** `tests/config.py`

```python
# Test configuration constants
TEST_VIDEOS_DIR = Path(__file__).parent / "fixtures" / "videos"
MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25MB
SUPPORTED_FORMATS = [".mp4", ".mov", ".webm", ".avi"]
POLL_INTERVAL = 3  # seconds
MAX_POLL_TIME = 300  # 5 minutes
```

---

## Phase 2: End-to-End Tests

### 2.1 Manual E2E Test Script

**File:** `tests/e2e_manual.py`

**Purpose:** Quick validation that the full pipeline works.

**Test Flow:**
1. Upload a small test video via API
2. Poll for task completion (every 3 seconds)
3. Verify task reaches COMPLETED status
4. Validate caption structure
5. Check all 4 caption styles are present
6. Measure total processing time
7. Verify metadata fields (processing_time_seconds, model_used, video_summary)

**Implementation:**
```python
async def test_e2e_small_video():
    """Test complete workflow with a 5-second video."""
    # 1. Upload video
    video_path = TEST_VIDEOS_DIR / "small" / "test_5s.mp4"
    task_id = await upload_video(video_path)
    
    # 2. Poll for completion
    result = await poll_until_complete(task_id, timeout=120)
    
    # 3. Validate response
    assert result["status"] == "COMPLETED"
    assert "formal" in result["result"]
    assert "sarcastic" in result["result"]
    assert "humorous_tech" in result["result"]
    assert "humorous_non_tech" in result["result"]
    assert result["result"]["processing_time_seconds"] > 0
    assert result["result"]["model_used"] is not None
```

**Run Command:**
```bash
python tests/e2e_manual.py
```

### 2.2 Automated E2E Tests

**File:** `tests/test_e2e.py`

**Purpose:** Automated end-to-end tests for CI/CD.

**Test Cases:**

#### 2.2.1 Happy Path Tests
- `test_e2e_small_video` - 5 second video
- `test_e2e_medium_video` - 30 second video
- `test_e2e_all_styles` - Verify all 4 styles generated
- `test_e2e_single_style` - Request only 1 style

#### 2.2.2 Error Handling Tests
- `test_e2e_invalid_file_type` - Upload .txt file
- `test_e2e_file_too_large` - Upload 30MB file
- `test_e2e_corrupted_file` - Upload broken video
- `test_e2e_no_audio` - Video without audio (should still work)

#### 2.2.3 Performance Tests
- `test_e2e_processing_time_under_60s` - Small video completes in <60s
- `test_e2e_concurrent_uploads` - 3 simultaneous uploads

**Implementation Structure:**
```python
class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_e2e_small_video(self):
        """Complete workflow with small video."""
        pass
    
    @pytest.mark.asyncio
    async def test_e2e_medium_video(self):
        """Complete workflow with medium video."""
        pass
    
    @pytest.mark.asyncio
    async def test_e2e_error_handling(self):
        """Test error scenarios."""
        pass
```

---

## Phase 3: Backend Unit Tests

### 3.1 Video Processor Tests

**File:** `tests/test_video_processor.py`

**Test Coverage:**

#### Download Tests
- `test_download_video_success` - Successful HTTP download
- `test_download_video_too_large` - File exceeds size limit
- `test_download_video_404` - URL not found
- `test_download_video_timeout` - Connection timeout
- `test_download_video_invalid_url` - Malformed URL

#### Keyframe Extraction Tests
- `test_extract_keyframes_count` - Verify 16 frames extracted
- `test_extract_keyframes_quality` - Check JPEG quality
- `test_extract_keyframes_base64` - Verify base64 encoding
- `test_extract_keyframes_short_video` - Video shorter than 16 frames
- `test_extract_keyframes_long_video` - 10-minute video

#### Audio Transcription Tests
- `test_transcribe_audio_with_speech` - Clear speech detected
- `test_transcribe_audio_no_audio` - Video without audio track
- `test_transcribe_audio_silent` - Silent audio track
- `test_transcribe_audio_background_noise` - Noisy audio
- `test_transcribe_audio_multiple_languages` - Non-English speech

#### Integration Tests
- `test_process_video_full_pipeline` - Download + extract + transcribe
- `test_process_video_cleanup` - Temp files deleted

**Implementation:**
```python
class TestVideoProcessor:
    def test_download_video_success(self, tmp_path):
        """Test successful video download."""
        pass
    
    def test_extract_keyframes_count(self):
        """Test that exactly 16 frames are extracted."""
        pass
    
    def test_transcribe_audio_with_speech(self):
        """Test transcription with clear speech."""
        pass
```

### 3.2 Fireworks Client Tests

**File:** `tests/test_fireworks_client.py`

**Test Coverage:**

#### Success Cases
- `test_generate_captions_success` - Valid response
- `test_generate_captions_all_styles` - All 4 styles returned
- `test_generate_captions_with_transcript` - With audio transcript
- `test_generate_captions_without_transcript` - No transcript

#### Retry Logic Tests
- `test_retry_on_429_rate_limit` - Rate limit retry
- `test_retry_on_500_server_error` - Server error retry
- `test_retry_on_timeout` - Timeout retry
- `test_retry_exponential_backoff` - Backoff timing
- `test_retry_max_attempts` - Stop after max retries

#### Error Handling Tests
- `test_auth_error_401` - Invalid API key
- `test_auth_error_403` - Forbidden
- `test_invalid_json_response` - Malformed JSON
- `test_missing_caption_keys` - Incomplete response
- `test_empty_response` - No content

#### Response Parsing Tests
- `test_parse_valid_json` - Correct JSON parsing
- `test_parse_markdown_code_block` - Strip markdown fences
- `test_parse_missing_keys` - Fill missing keys with defaults
- `test_parse_invalid_caption_type` - Non-string values

**Implementation:**
```python
class TestFireworksClient:
    @pytest.mark.asyncio
    async def test_generate_captions_success(self, mock_httpx):
        """Test successful caption generation."""
        pass
    
    @pytest.mark.asyncio
    async def test_retry_on_429(self, mock_httpx):
        """Test retry on rate limit."""
        pass
    
    def test_parse_response_valid_json(self):
        """Test JSON parsing."""
        pass
```

### 3.3 Upload Endpoint Tests

**File:** `tests/test_upload_endpoint.py`

**Test Coverage:**

#### Validation Tests
- `test_upload_valid_mp4` - Valid MP4 file
- `test_upload_valid_mov` - Valid MOV file
- `test_upload_valid_webm` - Valid WebM file
- `test_upload_invalid_extension` - .txt file rejected
- `test_upload_too_large` - 30MB file rejected
- `test_upload_missing_file` - No file in request
- `test_upload_invalid_styles` - Invalid style names

#### Task Creation Tests
- `test_upload_creates_task` - Task created in DB
- `test_upload_task_status_pending` - Initial status is PENDING
- `test_upload_task_styles_saved` - Styles stored correctly
- `test_upload_task_video_path_saved` - File path stored

#### Worker Dispatch Tests
- `test_upload_dispatches_to_celery` - Celery task queued
- `test_upload_celery_task_id_matches` - Task ID matches

#### Error Handling Tests
- `test_upload_file_save_error` - Disk full scenario
- `test_upload_db_error` - Database connection error
- `test_upload_celery_error` - Celery unavailable

**Implementation:**
```python
class TestUploadEndpoint:
    @pytest.mark.asyncio
    async def test_upload_valid_mp4(self, client, test_video):
        """Test successful MP4 upload."""
        response = await client.post(
            "/v1/tasks/upload",
            files={"video": test_video},
            data={"styles": "formal,sarcastic"}
        )
        assert response.status_code == 202
        assert "task_id" in response.json()
    
    @pytest.mark.asyncio
    async def test_upload_too_large(self, client, large_video):
        """Test upload size limit."""
        response = await client.post(
            "/v1/tasks/upload",
            files={"video": large_video}
        )
        assert response.status_code == 400
```

### 3.4 Worker Task Tests

**File:** `tests/test_worker_tasks.py`

**Test Coverage:**

#### Task Processing Tests
- `test_worker_picks_up_task` - Task status changes to PROCESSING
- `test_worker_processes_video` - Video is processed
- `test_worker_generates_captions` - Captions generated
- `test_worker_saves_result` - Result saved to DB
- `test_worker_marks_completed` - Status changes to COMPLETED

#### Error Handling Tests
- `test_worker_handles_video_error` - Video processing fails
- `test_worker_handles_api_error` - Fireworks API fails
- `test_worker_marks_failed` - Status changes to FAILED
- `test_worker_saves_error_message` - Error message stored
- `test_worker_retry_on_failure` - Retry mechanism works

#### Cleanup Tests
- `test_worker_cleans_temp_files` - Temp directory deleted
- `test_worker_cleans_on_error` - Cleanup on failure

#### Metadata Tests
- `test_worker_adds_processing_time` - processing_time_seconds set
- `test_worker_adds_model_used` - model_used set
- `test_worker_adds_video_summary` - video_summary set

**Implementation:**
```python
class TestWorkerTasks:
    @pytest.mark.asyncio
    async def test_worker_processes_task(self, test_session, mock_services):
        """Test complete task processing."""
        # Create task
        task = Task(id=uuid.uuid4(), status=TaskStatus.PENDING, ...)
        test_session.add(task)
        await test_session.commit()
        
        # Run worker
        await process_video_task(str(task.id))
        
        # Verify
        await test_session.refresh(task)
        assert task.status == TaskStatus.COMPLETED
        assert task.result_json is not None
```

---

## Phase 4: Integration Tests

### 4.1 Database Integration Tests

**File:** `tests/test_database.py`

**Test Coverage:**
- `test_create_task` - Task creation
- `test_update_task_status` - Status updates
- `test_save_result_json` - JSON field storage
- `test_query_by_status` - Status filtering
- `test_timestamps` - created_at, updated_at
- `test_concurrent_updates` - Race condition handling

### 4.2 Celery Integration Tests

**File:** `tests/test_celery_integration.py`

**Test Coverage:**
- `test_task_registration` - Task is registered
- `test_task_serialization` - Task can be serialized
- `test_task_queue` - Task added to queue
- `test_task_execution` - Task executes correctly
- `test_task_retry` - Retry mechanism works

---

## Phase 5: Frontend Tests

### 5.1 API Service Tests

**File:** `frontend/src/services/__tests__/api.test.js`

**Test Coverage:**

#### Upload Tests
- `test_upload_video_success` - Successful upload
- `test_upload_video_progress` - Progress callback called
- `test_upload_video_error` - Network error
- `test_upload_video_abort` - Upload cancelled

#### Poll Tests
- `test_poll_task_success` - Successful poll
- `test_poll_task_not_found` - 404 error
- `test_poll_task_network_error` - Network failure

#### Health Tests
- `test_health_check_success` - Backend healthy
- `test_health_check_failure` - Backend down

**Implementation:**
```javascript
describe('uploadVideo', () => {
  it('should upload video successfully', async () => {
    const mockXHR = createMockXHR(200, { task_id: '123' });
    // ... test implementation
  });
  
  it('should track upload progress', async () => {
    // ... test progress callback
  });
});
```

### 5.2 Hook Tests

**File:** `frontend/src/hooks/__tests__/useCaptions.test.js`

**Test Coverage:**

#### State Management Tests
- `test_initial_state` - Correct initial state
- `test_generate_sets_loading` - Loading state set
- `test_generate_sets_phase` - Phase transitions
- `test_generate_success` - Captions set on success
- `test_generate_error` - Error set on failure

#### Polling Tests
- `test_polling_starts_after_upload` - Polling initiated
- `test_polling_stops_on_complete` - Polling stops
- `test_polling_stops_on_error` - Polling stops on error
- `test_polling_interval` - Correct interval (3s)

#### Cleanup Tests
- `test_cleanup_on_unmount` - Interval cleared
- `test_cleanup_on_reset` - Interval cleared on reset

**Implementation:**
```javascript
describe('useCaptions', () => {
  it('should transition through phases correctly', async () => {
    const { result } = renderHook(() => useCaptions());
    
    // Initially idle
    expect(result.current.phase).toBe('idle');
    
    // Start generation
    act(() => {
      result.current.generate(mockFile, ['formal']);
    });
    
    expect(result.current.phase).toBe('uploading');
    // ... more assertions
  });
});
```

### 5.3 Component Tests

**File:** `frontend/src/components/__tests__/`

#### UploadZone Tests
- `test_file_selection` - File input works
- `test_drag_and_drop` - Drag-drop works
- `test_disabled_state` - Disabled when loading
- `test_file_validation` - Invalid files rejected

#### CaptionGrid Tests
- `test_renders_captions` - Captions displayed
- `test_renders_selected_styles` - Only selected styles
- `test_renders_video_summary` - Summary shown
- `test_renders_processing_time` - Time shown

#### CaptionCard Tests
- `test_renders_caption` - Caption text shown
- `test_copy_button` - Copy works
- `test_word_count` - Word count shown

---

## Phase 6: Performance & Load Tests

### 6.1 Performance Tests

**File:** `tests/test_performance.py`

**Test Coverage:**
- `test_small_video_processing_time` - <60 seconds
- `test_medium_video_processing_time` - <120 seconds
- `test_whisper_model_caching` - Second task faster
- `test_memory_usage` - No memory leaks

### 6.2 Load Tests

**File:** `tests/test_load.py`

**Test Coverage:**
- `test_concurrent_uploads_3` - 3 simultaneous uploads
- `test_concurrent_uploads_5` - 5 simultaneous uploads
- `test_sequential_uploads_10` - 10 uploads in sequence
- `test_worker_scaling` - Multiple workers

---

## Phase 7: Test Execution Plan

### 7.1 Test Execution Order

```bash
# 1. Run all backend tests
pytest tests/ -v

# 2. Run specific test suites
pytest tests/test_e2e.py -v
pytest tests/test_video_processor.py -v
pytest tests/test_fireworks_client.py -v
pytest tests/test_upload_endpoint.py -v
pytest tests/test_worker_tasks.py -v

# 3. Run with coverage
pytest tests/ --cov=backend --cov-report=html

# 4. Run frontend tests
cd frontend && npm test

# 5. Run manual E2E test
python tests/e2e_manual.py
```

### 7.2 CI/CD Integration

**File:** `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v --cov=backend
      
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'
      - name: Install dependencies
        run: cd frontend && npm install
      - name: Run tests
        run: cd frontend && npm test
```

---

## Phase 8: Test Data Management

### 8.1 Test Video Generation Script

**File:** `tests/fixtures/generate_test_videos.py`

```python
#!/usr/bin/env python3
"""Generate test videos for testing."""

import subprocess
from pathlib import Path

def create_test_video(output_path, duration=5, resolution="640x480"):
    """Create a test video using ffmpeg."""
    cmd = [
        "ffmpeg",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size={resolution}:rate=30",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-y",
        str(output_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)

if __name__ == "__main__":
    # Generate test videos
    videos_dir = Path(__file__).parent / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    
    # Small videos
    create_test_video(videos_dir / "small" / "test_5s.mp4", duration=5)
    create_test_video(videos_dir / "small" / "test_10s.mp4", duration=10)
    
    # Medium videos
    create_test_video(videos_dir / "medium" / "test_30s.mp4", duration=30)
    
    print("Test videos generated successfully!")
```

### 8.2 Test Fixtures

**File:** `tests/fixtures/__init__.py`

```python
"""Test fixtures for video captioning tests."""

from pathlib import Path

FIXTURES_DIR = Path(__file__).parent
VIDEOS_DIR = FIXTURES_DIR / "videos"

def get_test_video(name: str) -> Path:
    """Get path to a test video."""
    return VIDEOS_DIR / name
```

---

## Phase 9: Validation Checklist

### 9.1 Caption Generation Validation

- [ ] Captions are generated for all 4 styles
- [ ] Captions are relevant to video content
- [ ] Captions are in correct language
- [ ] Captions are properly formatted
- [ ] Processing time is recorded
- [ ] Model name is recorded
- [ ] Video summary is generated

### 9.2 Error Handling Validation

- [ ] Invalid file types are rejected
- [ ] Oversized files are rejected
- [ ] Network errors are handled
- [ ] API errors are handled
- [ ] Worker errors are reported
- [ ] Task status is updated correctly

### 9.3 Performance Validation

- [ ] Small videos process in <60s
- [ ] Medium videos process in <120s
- [ ] Whisper model is cached
- [ ] Memory usage is stable
- [ ] Concurrent uploads work
- [ ] No memory leaks

---

## Phase 10: Documentation

### 10.1 Test Documentation

**File:** `tests/README.md`

```markdown
# Video Captioning Tests

## Running Tests

### Backend Tests
```bash
# All tests
pytest tests/ -v

# Specific suite
pytest tests/test_e2e.py -v

# With coverage
pytest tests/ --cov=backend --cov-report=html
```

### Frontend Tests
```bash
cd frontend
npm test
```

## Test Structure

- `test_e2e.py` - End-to-end workflow tests
- `test_video_processor.py` - Video processing tests
- `test_fireworks_client.py` - AI client tests
- `test_upload_endpoint.py` - Upload endpoint tests
- `test_worker_tasks.py` - Worker task tests
- `test_performance.py` - Performance tests

## Test Videos

Test videos are located in `tests/fixtures/videos/`.

To generate test videos:
```bash
python tests/fixtures/generate_test_videos.py
```
```

---

## Implementation Priority

### Immediate (This Week)
1. **Phase 1** - Set up test infrastructure
2. **Phase 2** - Write and run E2E tests
3. **Phase 3.1** - Video processor tests
4. **Phase 3.2** - Fireworks client tests

### Short-term (Next Week)
5. **Phase 3.3** - Upload endpoint tests
6. **Phase 3.4** - Worker task tests
7. **Phase 4** - Integration tests

### Medium-term (Week 3)
8. **Phase 5** - Frontend tests
9. **Phase 6** - Performance tests

### Long-term (Week 4)
10. **Phase 7** - CI/CD integration
11. **Phase 8** - Test data management
12. **Phase 9** - Validation
13. **Phase 10** - Documentation

---

## Success Criteria

- [ ] All E2E tests pass
- [ ] All unit tests pass
- [ ] Code coverage > 80%
- [ ] Performance tests meet targets
- [ ] Frontend tests pass
- [ ] CI/CD pipeline works
- [ ] Documentation complete

---

## Questions for You

1. **Where are your sample videos located?** Should I copy them to `tests/fixtures/videos/`?
2. **What video sizes/durations do you have?** This helps determine test categories.
3. **Should I start with Phase 1 and 2** to validate captions work first?
4. **Do you want me to generate additional test videos** or use only yours?
5. **Are there specific edge cases** you want tested (e.g., non-English videos, very long videos)?

---

## Next Steps

Once you confirm, I'll:
1. Set up test infrastructure (Phase 1)
2. Create E2E test script (Phase 2.1)
3. Run manual E2E test with your videos
4. Fix any issues found
5. Continue with automated tests

**Ready to proceed?**
