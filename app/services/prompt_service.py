from typing import Union


def build_resume_prompt(resume_data: Union[list[dict], str]) -> str:
    """
    Build a tightly scoped ATS analysis prompt.

    Accepts either:
      - list[dict]  from pdf_service (structured chunked extraction)
      - str         for direct text input or testing

    The PDF service returns rich structured chunks — that's the correct
    pattern for a reusable service. This function's job is to extract
    only what the LLM needs (the text), discarding the metadata that is
    useful for other consumers (RAG, indexing, etc.) but is pure noise
    for a language model.
    """
    if isinstance(resume_data, list):
        # Sort by page then chunk_id to preserve reading order,
        # then join only the text content.
        sorted_chunks = sorted(
            resume_data, key=lambda c: (c.get("page", 0), c.get("chunk_id", 0))
        )
        resume_text = "\n\n".join(
            chunk["text"] for chunk in sorted_chunks if chunk.get("text")
        )
    else:
        resume_text = resume_data.strip()

    return f"""You are an ATS resume scoring engine. Output ONLY a single JSON object. \
No prose, no markdown fences, no explanation before or after.

JSON schema (fill every field):
{{
  "ats_score": <integer 0-100>,
  "strengths": [<string>, ...],
  "weaknesses": [<string>, ...],
  "missing_skills": [<string>, ...],
  "suggestions": [<string>, ...]
}}

Resume:
{resume_text}"""


def build_interview_questions_prompt(
    role: str,
    industry: str,
    experience_level: str,
    difficulty: str,
    num_questions: int = 5,
) -> str:
    return f"""Generate {num_questions} technical interview questions for a {experience_level} {role} in {industry}.
Difficulty: {difficulty}.
 
Reply with ONLY a JSON object in this exact format, no other text:
{{
  "questions": [
    {{
      "question": "...",
      "hints": "...",
      "sample_answer": "...",
      "difficulty": "{difficulty}"
    }}
  ]
}}
 
Rules:
- sample_answer must be plain text, no regex or special characters
- hints must be one concise sentence
- question must be specific and practical"""