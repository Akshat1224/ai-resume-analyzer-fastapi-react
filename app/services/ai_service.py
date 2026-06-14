import httpx
import json
import re
import asyncio
import hashlib
from typing import Optional
import os
from dotenv import load_dotenv
import time

load_dotenv()

_memory_cache: dict = {}
_cache_ttl: int = 3600

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_http_client: Optional[httpx.AsyncClient] = None

# FIX 1: Tighter timeouts. Connect should be fast (Groq is CDN-backed).
# Read timeout is where you wait for the LLM to finish generating.
_TIMEOUT = httpx.Timeout(connect=4.0, read=12.0, write=5.0, pool=5.0)


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=_TIMEOUT,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    return _http_client


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def get_cache_key(prompt: str) -> str:
    # FIX 2: Use a deterministic hash. Python's built-in hash() changes across
    # process restarts (PYTHONHASHSEED), causing 100% cache misses after restart.
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


# ---------------------------------------------------------------------------
# JSON repair helpers (kept as fallback but rarely needed with json mode)
# ---------------------------------------------------------------------------

_VALID_JSON_ESCAPES = set('"\\\/bfnrtu')


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
    if len(prompt) > 6000:
        prompt = prompt[:6000]
    return prompt.strip()


# ---------------------------------------------------------------------------
# System prompt — the single biggest latency win
# ---------------------------------------------------------------------------

# FIX 3: A concise system prompt that:
#   a) Tells the LLM to output ONLY JSON (no prose, no markdown fences)
#   b) Specifies the exact schema so the LLM doesn't guess / pad extra fields
#   c) Keeps the system prompt itself short to minimize prefill time
SYSTEM_PROMPT = (
    "You are a resume analysis assistant. "
    "Respond with ONLY valid JSON — no markdown, no explanation, no extra text. "
    "Be concise: keep each value short (1-2 sentences max)."
)


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------


async def _call_groq(payload: dict, headers: dict) -> dict:
    """Single Groq API call. Raises on non-200."""
    client = _get_client()
    resp = await client.post(GROQ_URL, json=payload, headers=headers)
    if resp.status_code != 200:
        print(f"[GROQ ERROR] {resp.status_code}: {resp.text[:200]}")
    resp.raise_for_status()
    return resp.json()


async def analyze_resume(prompt: str) -> dict:
    """
    Send prompt to Groq and return parsed JSON.

    Performance fixes applied:
    1. Persistent HTTP client (reuses TCP+TLS connections)
    2. System prompt forces concise JSON — less generation = less latency
    3. response_format=json_object — Groq constrains decoding to valid JSON,
       eliminating markdown wrapper tokens and JSON repair retries
    4. max_tokens capped at 500 (5 questions × ~80 tokens each ≈ 400)
    5. Tighter connect timeout (4s vs 8s), read timeout stays at 12s
    6. Retry loop actually retries (range(2), not range(1))
    7. Deterministic cache key via MD5 (survives process restarts)
    """
    prompt = sanitize_prompt(prompt)
    cache_key = get_cache_key(prompt)

    cached = get_from_memory_cache(cache_key)
    if cached:
        return cached

    # FIX 4: Three critical payload changes:
    #   a) Added system message — guides the LLM to be concise and JSON-only
    #   b) response_format: json_object — Groq's constrained decoding ensures
    #      the output is always valid JSON. This eliminates:
    #        - Markdown wrapping (```json ... ```) — saves ~10 tokens
    #        - Invalid JSON retries — saves an entire round-trip
    #        - JSON repair overhead on the server
    #   c) max_tokens stays at 500 — plenty for 5 interview questions
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 500,
        "response_format": {"type": "json_object"},  # <-- KEY FIX
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    # FIX 5: range(2) — actually retry once on timeout.
    # The original code used range(1) which means only ONE attempt, no retry.
    last_error: Optional[Exception] = None
    for attempt in range(2):
        try:
            t0 = time.perf_counter()
            data = await _call_groq(payload, headers)
            elapsed = time.perf_counter() - t0
            print(f"[GROQ] {elapsed:.2f}s (attempt {attempt + 1})")

            raw = data["choices"][0]["message"]["content"]

            # With response_format=json_object, this should always succeed
            # on the first try. Fallback to repair just in case.
            parsed = try_parse_json_from_text(raw)
            if parsed is not None:
                set_memory_cache(cache_key, parsed)
                return parsed

            return {"error": "Invalid JSON from LLM", "raw_response": raw}

        except httpx.TimeoutException as e:
            last_error = e
            print(f"[GROQ] attempt {attempt + 1} timed out")
            # Reset client so retry gets a fresh connection
            global _http_client
            if _http_client and not _http_client.is_closed:
                await _http_client.aclose()
            _http_client = None
            if attempt == 0:
                await asyncio.sleep(0.3)

        except httpx.HTTPStatusError as e:
            return {
                "error": f"Groq API error {e.response.status_code}",
                "detail": str(e),
            }

        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    return {"error": f"Request timed out after 2 attempts: {last_error}"}
