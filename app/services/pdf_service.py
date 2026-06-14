# 1->Includes error handling while parsing
# 2->Includes page wise processing
#3->Includes sentence aware chunking
import fitz
import nltk

# nltk.download("punkt")
# nltk.download('punkt_tab')
from nltk.tokenize import sent_tokenize


async def extract_text_from_pdf(file_path: str):
    chunked_data = []
    chunk_id = 1
    try:
        with fitz.open(file_path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text()
                if not text:
                    continue
                text = text.strip()
                chunks = sentence_chunking(text, 3)
                for chunk in chunks:
                    chunked_data.append(
                        {
                            "page": page_number,
                            "chunk_id": chunk_id,
                            "text": chunk,
                            "char_count": len(chunk),
                            "word_count": len(chunk.split()),
                        }
                    )
                    chunk_id += 1
        return chunked_data
    except Exception as e:
        raise Exception(f"PDF parsing failed: {str(e)}")


def sentence_chunking(text: str, max_sentences: int = 3):
    sentences = sent_tokenize(text)
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
