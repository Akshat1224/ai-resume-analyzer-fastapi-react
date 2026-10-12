import io
import pytest
from starlette.testclient import TestClient
import pymupdf as fitz
from app.main import app

client = TestClient(app)


def create_mock_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_analyze_with_job_description():
    """Test full job matching with PDF resume and job description."""
    resume_text = (
        "Jane Smith\nEmail: jane@example.com | Phone: 555-0100\n"
        "Summary: Senior Backend Engineer specializing in Python, FastAPI, and PostgreSQL.\n"
        "Experience: Developed microservices in Python using FastAPI. Managed PostgreSQL database clusters.\n"
        "Skills: Python, FastAPI, PostgreSQL, Docker, Git"
    )
    pdf_bytes = create_mock_pdf_bytes(resume_text)

    job_description = (
        "We are looking for a Senior Python Developer.\n"
        "Requirements:\n"
        "- 4+ years of Python\n"
        "- FastAPI experience\n"
        "- PostgreSQL experience\n"
        "Preferred:\n"
        "- Kubernetes experience"
    )

    response = client.post(
        "/resume/analyze",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        data={"job_description": job_description},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify top-level structure
    assert "ats_score" in data
    assert "strengths" in data
    assert "missing_skills" in data
    assert "job_match" in data

    # Verify job match details
    job_match = data["job_match"]
    assert job_match is not None
    assert "score_breakdown" in job_match
    breakdown = job_match["score_breakdown"]
    assert 0 <= breakdown["total_match_score"] <= 100
    assert breakdown["required_score"] > 0

    # Verify verified skills and evidence
    skills_analysis = job_match["skills_analysis"]
    assert len(skills_analysis) > 0
    python_skill = next((s for s in skills_analysis if s["skill"].lower() == "python"), None)
    assert python_skill is not None
    assert python_skill["status"] == "matched"
    assert len(python_skill["evidence"]) > 0
    assert python_skill["evidence"][0]["verified"] is True


def test_analyze_without_job_description_backward_compatible():
    """Test fallback structural ATS analysis when no Job Description is provided."""
    resume_text = (
        "Alice Developer\nEmail: alice@example.com | Phone: 555-1234\n"
        "Experience:\nDeveloped web applications using React and Python.\n"
        "Education:\nB.S. in Software Engineering.\n"
        "Skills:\nReact, Python, SQL, Git, Linux.\n"
        "Projects:\nOptimized database queries reducing latency by 35%."
    )
    pdf_bytes = create_mock_pdf_bytes(resume_text)

    response = client.post(
        "/resume/analyze",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    data = response.json()

    assert "ats_score" in data
    assert data["ats_score"] > 50  # Well structured resume receives good structural score
    assert "strengths" in data
    assert "suggestions" in data
    assert data["metadata"]["mode"] == "structural_ats_only"


def test_reject_non_pdf_file():
    """Uploading a non-PDF file returns HTTP 400."""
    response = client.post(
        "/resume/analyze",
        files={"file": ("resume.txt", b"plain text resume", "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF documents are supported" in response.json()["detail"]


def test_reject_empty_pdf_file():
    """Uploading an empty 0-byte file returns HTTP 400."""
    response = client.post(
        "/resume/analyze",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
