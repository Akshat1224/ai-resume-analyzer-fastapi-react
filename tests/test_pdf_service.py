import os
import tempfile
import pytest
import pymupdf as fitz
from app.services.pdf_service import (
    parse_pdf_document,
    sentence_chunking,
    PDFParsingError,
)


@pytest.fixture
def sample_pdf_file():
    """Create a temporary 2-page PDF document."""
    doc = fitz.open()
    
    # Page 1
    p1 = doc.new_page()
    p1.insert_text(
        (50, 72),
        "John Doe\nEmail: john@example.com | Phone: 555-0199\n"
        "Summary: Senior Software Engineer with 5+ years of experience in Python and FastAPI.\n"
        "Experience:\nDeveloped scalable backend APIs using FastAPI and PostgreSQL.\n"
        "Led performance optimization initiatives reducing latency by 40%."
    )
    
    # Page 2
    p2 = doc.new_page()
    p2.insert_text(
        (50, 72),
        "Education: Bachelor of Science in Computer Science.\n"
        "Technical Skills: Python, Docker, Redis, Git, Linux, CI/CD pipelines.\n"
        "Projects: Built distributed caching microservice handling 10k RPS."
    )

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_path = temp.name
    temp.close()
    
    doc.save(temp_path)
    doc.close()

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_parse_valid_pdf_document(sample_pdf_file):
    """Test page-aware PDF extraction preserving pages and structured chunks."""
    result = parse_pdf_document(sample_pdf_file)
    
    assert result["page_count"] == 2
    assert len(result["pages"]) == 2
    assert result["pages"][0]["page"] == 1
    assert "John Doe" in result["pages"][0]["text"]
    assert result["pages"][1]["page"] == 2
    assert "Technical Skills" in result["pages"][1]["text"]
    assert result["is_scanned_or_empty"] is False
    assert len(result["chunks"]) > 0


def test_empty_blank_pdf_detected():
    """A PDF with blank pages (no selectable text) is detected as scanned/empty."""
    doc = fitz.open()
    doc.new_page()  # Blank page without text
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_path = temp.name
    temp.close()
    
    doc.save(temp_path)
    doc.close()

    try:
        result = parse_pdf_document(temp_path)
        assert result["page_count"] == 1
        assert result["is_scanned_or_empty"] is True
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_corrupt_file_error():
    """Corrupt non-PDF bytes raise PDFParsingError."""
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp.write(b"this is corrupt binary junk not a real pdf")
    temp_path = temp.name
    temp.close()

    try:
        with pytest.raises(PDFParsingError):
            parse_pdf_document(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_sentence_chunking():
    """Sentence chunking groups sentences up to max_sentences."""
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."
    chunks = sentence_chunking(text, max_sentences=2)
    assert len(chunks) == 2
    assert "First sentence" in chunks[0]
    assert "Fourth sentence" in chunks[1]
