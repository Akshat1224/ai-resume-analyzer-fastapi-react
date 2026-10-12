import httpx
import json
import re
import asyncio
import hashlib
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
import time
from pydantic import BaseModel, Field, ValidationError

from app.core.config import GROQ_MODEL
from app.core.telemetry import logger, redact_sensitive

load_dotenv()

_memory_cache: dict = {}
_cache_ttl: int = 3600

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_http_client: Optional[httpx.AsyncClient] = None
_TIMEOUT = httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0)

# Transient retryable HTTP status codes
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class RawSkillItem(BaseModel):
    skill: str = Field(..., min_length=1)
    category: str = Field(default="required")
    status: str = Field(default="missing")
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning: str = Field(default="")


class RawSkillPayload(BaseModel):
    skills: List[RawSkillItem] = Field(default_factory=list)


class RawATSScorePayload(BaseModel):
    ats_score: int = Field(default=70, ge=0, le=100)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


def get_groq_api_key() -> Optional[str]:
    """Retrieve Groq API key safely without import-time failures."""
    return os.getenv("GROQ_API_KEY")


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
    return _http_client


def get_cache_key(prompt: str) -> str:
    return hashlib.md5(prompt.encode("utf-8")).hexdigest()


def get_from_memory_cache(key: str) -> Optional[dict]:
    if key in _memory_cache:
        data, timestamp = _memory_cache[key]
        if time.time() - timestamp < _cache_ttl:
            return data
        del _memory_cache[key]
    return None


def set_memory_cache(key: str, value: dict) -> None:
    _memory_cache[key] = (value, time.time())


_VALID_JSON_ESCAPES = set('"\\/bfnrtu')


def extract_json_from_markdown(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)```", text)
    return match.group(1).strip() if match else text.strip()


def repair_invalid_escapes(text: str) -> str:
    result = []
    i = 0
    in_string = False
    prev_char = ""
    while i < len(text):
        ch = text[i]
        if ch == '"' and prev_char != "\\":
            in_string = not in_string
            result.append(ch)
            prev_char = ch
            i += 1
            continue
        if in_string and ch == "\\":
            next_ch = text[i + 1] if i + 1 < len(text) else ""
            result.append(ch if next_ch in _VALID_JSON_ESCAPES else "\\\\")
            prev_char = ch
            i += 1
            continue
        result.append(ch)
        prev_char = ch
        i += 1
    return "".join(result)


def try_parse_json_from_text(text: str) -> Optional[dict]:
    stripped = extract_json_from_markdown(text)
    for candidate in (stripped, repair_invalid_escapes(stripped)):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    return None


def sanitize_prompt(prompt: str) -> str:
    prompt = prompt.replace("\x00", "")
    prompt = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", prompt)
    if len(prompt) > 16000:
        prompt = prompt[:16000]
    return prompt.strip()


SYSTEM_PROMPT = (
    "You are a strict, objective resume analysis engine. "
    "Respond with ONLY valid JSON conforming to the requested schema. "
    "Do not extrapolate, assume, or fabricate any candidate experience not explicitly present."
)


async def _call_groq_with_retries(payload: dict, headers: dict, max_retries: int = 3) -> dict:
    """
    Executes Groq API call with bounded exponential backoff retries
    for timeouts, rate limits (429), and transient server errors (5xx).
    """
    client = _get_client()
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            t0 = time.perf_counter()
            resp = await client.post(GROQ_URL, json=payload, headers=headers)
            elapsed = time.perf_counter() - t0

            if resp.status_code == 200:
                logger.info(f"Groq API call succeeded in {elapsed:.2f}s (attempt {attempt})")
                return resp.json()

            # Handle rate limit (429) or transient 5xx errors
            if resp.status_code in _RETRYABLE_STATUS_CODES:
                retry_after = 0.5 * (2 ** (attempt - 1))
                header_retry = resp.headers.get("Retry-After")
                if header_retry and header_retry.isdigit():
                    retry_after = min(float(header_retry), 5.0)

                logger.warning(
                    f"Groq API returned HTTP {resp.status_code} on attempt {attempt}/{max_retries}. "
                    f"Retrying in {retry_after:.2f}s..."
                )
                if attempt < max_retries:
                    await asyncio.sleep(retry_after)
                    continue

            # Non-retryable error
            logger.error(f"Groq API unrecoverable error HTTP {resp.status_code}: {resp.text[:200]}")
            resp.raise_for_status()

        except httpx.TimeoutException as exc:
            last_exception = exc
            logger.warning(f"Groq API request timeout on attempt {attempt}/{max_retries}")
            # Reset connection pool
            global _http_client
            if _http_client and not _http_client.is_closed:
                await _http_client.aclose()
            _http_client = None

            if attempt < max_retries:
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
                continue

        except httpx.HTTPStatusError as exc:
            last_exception = exc
            if exc.response.status_code not in _RETRYABLE_STATUS_CODES or attempt == max_retries:
                raise

        except Exception as exc:
            last_exception = exc
            logger.error(f"Groq API unexpected exception: {redact_sensitive(str(exc))}")
            if attempt == max_retries:
                raise

    raise RuntimeError(f"Groq API failed after {max_retries} attempts: {last_exception}")


async def analyze_resume(prompt: str, max_tokens: int = 1500) -> dict:
    """
    Send prompt to Groq and return parsed JSON with bounded retries and local fallback.
    """
    prompt = sanitize_prompt(prompt)
    cache_key = get_cache_key(prompt)

    cached = get_from_memory_cache(cache_key)
    if cached:
        return cached

    api_key = get_groq_api_key()
    if not api_key:
        logger.info("GROQ_API_KEY not configured. Falling back to local offline heuristic matching.")
        return {"error": "GROQ_API_KEY_MISSING", "detail": "GROQ_API_KEY is not configured in .env"}

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        data = await _call_groq_with_retries(payload, headers, max_retries=3)
        raw_content = data["choices"][0]["message"]["content"]
        parsed = try_parse_json_from_text(raw_content)

        if parsed is not None:
            # Validate structure against Pydantic models
            if "skills" in parsed:
                try:
                    validated = RawSkillPayload.model_validate(parsed)
                    parsed = validated.model_dump()
                except ValidationError as ve:
                    logger.warning(f"AI response partial schema mismatch for skills: {ve}")
            elif "ats_score" in parsed:
                try:
                    validated = RawATSScorePayload.model_validate(parsed)
                    parsed = validated.model_dump()
                except ValidationError as ve:
                    logger.warning(f"AI response partial schema mismatch for ats_score: {ve}")

            set_memory_cache(cache_key, parsed)
            return parsed

        return {"error": "Invalid JSON from LLM", "raw_response": raw_content}

    except Exception as e:
        logger.error(f"AI analysis execution failed: {redact_sensitive(str(e))}")
        return {"error": "AI_ANALYSIS_FAILED", "detail": str(e)}


def offline_heuristic_job_matcher(
    resume_pages: List[Dict[str, Any]],
    job_description: str
) -> Dict[str, Any]:
    """
    Deterministic offline/heuristic extractor used for automated tests and offline mode.
    Extracts requirements from job description and locates verbatim evidence in resume pages.
    """
    known_skills = [
        "python", "fastapi", "react", "typescript", "javascript", "sql", "postgresql",
        "redis", "docker", "kubernetes", "aws", "git", "ci/cd", "rest api", "graphql",
        "tailwind", "html", "css", "pydantic", "node.js", "linux", "c++", "java", "go"
    ]

    jd_lower = job_description.lower()
    found_skills = []

    for s in known_skills:
        pattern = r"\b" + re.escape(s) + r"\b"
        if re.search(pattern, jd_lower):
            is_preferred = bool(re.search(r"(preferred|bonus|nice to have|plus|optional).*?" + re.escape(s), jd_lower))
            found_skills.append((s, "preferred" if is_preferred else "required"))

    if not found_skills:
        lines = [line.strip("- *• \t") for line in job_description.split("\n") if len(line.strip()) > 3]
        for line in lines[:8]:
            found_skills.append((line[:40], "required"))

    skills_result = []
    for skill_name, category in found_skills:
        skill_pat = r"\b" + re.escape(skill_name) + r"\b"
        matched_evidence = []

        for p in resume_pages:
            p_num = p.get("page", 1)
            p_text = p.get("text", "")
            sentences = [s.strip() for s in p_text.replace("\n", ". ").split(".") if s.strip()]
            for sent in sentences:
                if re.search(skill_pat, sent, re.IGNORECASE):
                    matched_evidence.append({
                        "page": p_num,
                        "snippet": sent[:200]
                    })
                    break

        if matched_evidence:
            status = "matched"
            reasoning = f"Verified experience with {skill_name} found in resume on page {matched_evidence[0]['page']}."
        else:
            status = "missing"
            reasoning = f"No mention of {skill_name} found in resume."

        skills_result.append({
            "skill": skill_name.title(),
            "category": category,
            "status": status,
            "evidence": matched_evidence,
            "reasoning": reasoning
        })

    return {"skills": skills_result}
