import asyncio
import io
import pytest
from starlette.testclient import TestClient
import pymupdf as fitz
from unittest.mock import patch, AsyncMock
import httpx

from app.main import app
from app.core.config import MAX_UPLOAD_BYTES
from app.core.telemetry import redact_sensitive, metrics
from app.utils.stream import stage_broadcaster
from app.services.ai_service import _call_groq_with_retries

client = TestClient(app)


def test_health_check_endpoint():
    """Verify health check returns service status and dependencies."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "resumeiq-api"
    assert "status" in data
    assert "dependencies" in data
    assert "redis" in data["dependencies"]


def test_metrics_endpoint():
    """Verify metrics endpoint tracks requests and calculates latency summary."""
    # Send request to trigger metrics increment
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert data["total_requests"] > 0
    assert "avg_latency_ms" in data
    assert "status_codes" in data


def test_reject_fake_extension_invalid_magic_bytes():
    """Uploading a file named .pdf with text/html content is rejected via magic byte check."""
    fake_pdf = b"<html><body>Not a PDF</body></html>"
    response = client.post(
        "/resume/analyze",
        files={"file": ("fake.pdf", fake_pdf, "application/pdf")},
    )
    assert response.status_code == 400
    assert "header" in response.json()["detail"].lower() or "not a valid pdf" in response.json()["detail"].lower()


def test_reject_oversized_file():
    """Uploading a file exceeding MAX_UPLOAD_BYTES is rejected with HTTP 413."""
    # Generate content slightly larger than MAX_UPLOAD_BYTES
    oversized_bytes = b"%PDF-" + b"0" * (MAX_UPLOAD_BYTES + 1024)
    response = client.post(
        "/resume/analyze",
        files={"file": ("huge.pdf", oversized_bytes, "application/pdf")},
    )
    assert response.status_code == 413
    assert "exceeds maximum limit" in response.json()["detail"]


def test_reject_scanned_image_only_pdf():
    """A PDF with pages but 0 selectable text returns HTTP 422 Unprocessable Entity."""
    doc = fitz.open()
    doc.new_page()  # Blank page without text
    pdf_bytes = doc.tobytes()
    doc.close()

    response = client.post(
        "/resume/analyze",
        files={"file": ("scanned.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 422
    assert "selectable text" in response.json()["detail"]


def test_redact_sensitive_credentials():
    """Verify secret tokens and API keys are redacted from log outputs."""
    raw_text = "Connecting to Groq with key gsk_1234567890abcdef1234567890 and Bearer eyJhbGciOiJIUzI1NiJ9.sample"
    sanitized = redact_sensitive(raw_text)
    assert "gsk_" not in sanitized
    assert "Bearer" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized


def test_stage_broadcaster_emits_actual_stages():
    """Stage broadcaster emits real events and terminates without emitting Completed on error."""
    async def _run():
        test_job_id = "test_job_sse_123"
        await stage_broadcaster.emit_stage(test_job_id, "Validating file...")
        await stage_broadcaster.emit_stage(test_job_id, "Parsing layout...")
        await stage_broadcaster.emit_error(test_job_id, "Corrupt stream")

        events = []
        async for event in stage_broadcaster.stage_generator(test_job_id, timeout=2.0):
            events.append(event["data"])

        assert "Validating file..." in events
        assert "Parsing layout..." in events
        assert "Error: Corrupt stream" in events
        # Completed must NEVER be emitted when an error occurred
        assert "Completed" not in events

    asyncio.run(_run())


def test_ai_bounded_retry_on_rate_limit():
    """Verify _call_groq_with_retries attempts backoff retries on HTTP 429."""
    async def _run():
        mock_resp_429 = httpx.Response(429, headers={"Retry-After": "0.01"}, text="Rate limit exceeded")
        mock_resp_200 = httpx.Response(200, json={"choices": [{"message": {"content": "{\"skills\": []}"}}]})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[mock_resp_429, mock_resp_200])

        with patch("app.services.ai_service._get_client", return_value=mock_client):
            data = await _call_groq_with_retries({"model": "test"}, {"Authorization": "Bearer test"}, max_retries=2)
            assert "choices" in data
            assert mock_client.post.call_count == 2

    asyncio.run(_run())
