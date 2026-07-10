"""Tests for the Video Captioning API v1 endpoints."""

import pytest
from httpx import AsyncClient

from backend.models.task import TaskStatus


# =============================================================================
# POST /v1/tasks — Create Task
# =============================================================================


class TestCreateTask:
    async def test_create_task_success(self, client: AsyncClient):
        """Should return 202 with task_id and PENDING status."""
        payload = {
            "video_url": "https://example.com/videos/demo.mp4",
            "styles": ["formal", "sarcastic"],
        }
        response = await client.post("/v1/tasks", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "PENDING"

    async def test_create_task_all_styles(self, client: AsyncClient):
        """When styles omitted, should default to all 4 styles."""
        payload = {
            "video_url": "https://example.com/videos/demo.mp4",
        }
        response = await client.post("/v1/tasks", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "PENDING"

    async def test_create_task_invalid_style(self, client: AsyncClient):
        """Should return 422 for invalid style names."""
        payload = {
            "video_url": "https://example.com/videos/demo.mp4",
            "styles": ["invalid_style"],
        }
        response = await client.post("/v1/tasks", json=payload)
        assert response.status_code == 422

    async def test_create_task_empty_styles(self, client: AsyncClient):
        """Empty styles list should default to all styles."""
        payload = {
            "video_url": "https://example.com/videos/demo.mp4",
            "styles": [],
        }
        response = await client.post("/v1/tasks", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "PENDING"

    async def test_create_task_missing_auth(self, client: AsyncClient):
        """Should return 401 when X-API-Key header is missing."""
        payload = {
            "video_url": "https://example.com/videos/demo.mp4",
        }
        response = await client.post(
            "/v1/tasks", json=payload, headers={}
        )
        assert response.status_code == 401

    async def test_create_task_invalid_auth(self, client: AsyncClient):
        """Should return 403 for invalid X-API-Key."""
        payload = {
            "video_url": "https://example.com/videos/demo.mp4",
        }
        response = await client.post(
            "/v1/tasks",
            json=payload,
            headers={"X-API-Key": "invalid-key"},
        )
        assert response.status_code == 403

    # --- SSRF Tests ---

    @pytest.mark.parametrize(
        "bad_url",
        [
            "http://localhost:8080/video.mp4",
            "http://127.0.0.1:5432/video.mp4",
            "http://10.0.0.1/video.mp4",
            "http://192.168.1.1/video.mp4",
            "http://[::1]:8000/video.mp4",
        ],
    )
    async def test_ssrf_blocked(self, client: AsyncClient, bad_url: str):
        """Internal IP URLs should be rejected with 400."""
        payload = {"video_url": bad_url}
        response = await client.post("/v1/tasks", json=payload)
        assert response.status_code == 400
        assert "SSRF" in response.text or "not allowed" in response.text

    async def test_ssrf_file_scheme(self, client: AsyncClient):
        """file:// URLs should be rejected."""
        payload = {"video_url": "file:///etc/passwd"}
        response = await client.post("/v1/tasks", json=payload)
        assert response.status_code == 400  # Pydantic rejects non-http schemes

    async def test_ssrf_internal_hostname(self, client: AsyncClient):
        """Hostnames ending in .local or .internal should be rejected."""
        payload = {"video_url": "http://db.internal/video.mp4"}
        response = await client.post("/v1/tasks", json=payload)
        assert response.status_code == 400

    # --- URL Validation Tests ---

    async def test_invalid_url_format(self, client: AsyncClient):
        """Malformed URLs should be rejected by Pydantic."""
        payload = {"video_url": "not-a-url"}
        response = await client.post("/v1/tasks", json=payload)
        assert response.status_code == 422


# =============================================================================
# GET /v1/tasks/{task_id} — Get Task Status
# =============================================================================


class TestGetTask:
    async def test_get_task_completed(self, client: AsyncClient, sample_task):
        """Should return COMPLETED status with result."""
        response = await client.get(f"/v1/tasks/{sample_task.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == str(sample_task.id)
        assert data["status"] == "COMPLETED"
        assert data["result"] is not None
        assert "formal" in data["result"]
        assert "sarcastic" in data["result"]
        assert data["error_message"] is None

    async def test_get_task_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent task."""
        response = await client.get(
            "/v1/tasks/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_get_task_invalid_uuid(self, client: AsyncClient):
        """Should return 422 for invalid UUID format."""
        response = await client.get("/v1/tasks/not-a-uuid")
        assert response.status_code == 422

    async def test_get_task_missing_auth(self, client: AsyncClient, sample_task):
        """Should return 401 without API key."""
        response = await client.get(
            f"/v1/tasks/{sample_task.id}", headers={}
        )
        assert response.status_code == 401


# =============================================================================
# GET /health — Health Check
# =============================================================================


class TestHealthCheck:
    async def test_health_endpoint(self, client: AsyncClient):
        """Health endpoint should return service status."""
        response = await client.get("/health", headers={"X-API-Key": "test-api-key-123"})
        # Health may be degraded without Redis, but should return
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "redis" in data
