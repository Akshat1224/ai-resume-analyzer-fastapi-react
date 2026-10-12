import pymupdf as fitz
from typing import List, Dict, Any
from nltk.tokenize import sent_tokenize


class PDFParsingError(Exception):
    """Custom exception raised when PDF parsing fails."""
    pass


def sentence_chunking(text: str, max_sentences: int = 3) -> List[str]:
    """Chunk text into small sentence groups while preserving sentence boundaries."""
    if not text or not text.strip():
        return []
    try:
        sentences = sent_tokenize(text)
    except Exception:
        # Fallback to simple line / punctuation split if tokenizer fails
        sentences = [s.strip() for s in text.replace("\n", ". ").split(".") if s.strip()]

    chunks = []
    current_chunk = []
    for sentence in sentences:
        current_chunk.append(sentence)
        if len(current_chunk) >= max_sentences:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks


def parse_pdf_document(file_path: str) -> Dict[str, Any]:
    """
    Synchronous extractor preserving page numbers, raw text, and structured chunks.
    Raises PDFParsingError on corrupt or unreadable files.
    """
    pages_data: List[Dict[str, Any]] = []
    chunked_data: List[Dict[str, Any]] = []
    chunk_id = 1

    try:
        with fitz.open(file_path) as pdf:
            total_pages = len(pdf)
            if total_pages == 0:
                raise PDFParsingError("Uploaded PDF contains no pages.")

            for page_number, page in enumerate(pdf, start=1):
                raw_text = page.get_text() or ""
                cleaned_text = raw_text.strip()
                
                pages_data.append({
                    "page": page_number,
                    "text": cleaned_text,
                    "char_count": len(cleaned_text),
                    "word_count": len(cleaned_text.split()),
                })

                if cleaned_text:
                    chunks = sentence_chunking(cleaned_text, max_sentences=3)
                    for chunk in chunks:
                        chunked_data.append({
                            "page": page_number,
                            "chunk_id": chunk_id,
                            "text": chunk,
                            "char_count": len(chunk),
                            "word_count": len(chunk.split()),
                        })
                        chunk_id += 1

        all_text = "\n\n".join(p["text"] for p in pages_data if p["text"])
        is_scanned = len(all_text.strip()) == 0

        return {
            "pages": pages_data,
            "chunks": chunked_data,
            "full_text": all_text,
            "page_count": total_pages,
            "total_characters": len(all_text),
            "total_words": len(all_text.split()),
            "is_scanned_or_empty": is_scanned,
        }

    except PDFParsingError:
        raise
    except Exception as e:
        raise PDFParsingError(f"PDF parsing failed: {str(e)}") from e


async def extract_text_from_pdf(file_path: str) -> List[Dict[str, Any]]:
    """Backward-compatible async helper returning list of chunks."""
    doc = parse_pdf_document(file_path)
    return doc["chunks"]


async def extract_resume_document(file_path: str) -> Dict[str, Any]:
    """Async wrapper returning complete document structure with pages and metadata."""
    return parse_pdf_document(file_path)
