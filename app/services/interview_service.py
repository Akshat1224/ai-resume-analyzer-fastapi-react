import json
import time

from app.services.ai_service import analyze_resume
from app.services.prompt_service import build_interview_questions_prompt
from app.services.redis_service import redis_client


def generate_cache_key(
    role: str,
    industry: str,
    experience_level: str,
    difficulty: str,
) -> str:

    return (
        f"{role}:"
        f"{industry}:"
        f"{experience_level}:"
        f"{difficulty}"
    ).lower()


async def generate_interview_questions(
    role: str,
    industry: str,
    experience_level: str,
    difficulty: str,
    num_questions: int = 5,
) -> dict:

    cache_key = generate_cache_key(
        role,
        industry,
        experience_level,
        difficulty,
    )

    # Redis Cache Check
    try:

        cached_data = redis_client.get(cache_key)

        if cached_data:

            print("[REDIS CACHE HIT]")

            return json.loads(cached_data)

    except Exception as e:

        print(f"[REDIS ERROR] {e}")

    print("[CACHE MISS]")

    prompt = build_interview_questions_prompt(
        role,
        industry,
        experience_level,
        difficulty,
        num_questions,
    )

    start = time.perf_counter()

    result = await analyze_resume(prompt)

    elapsed = time.perf_counter() - start

    print(
        f"[INTERVIEW SERVICE] LLM took {elapsed:.2f}s"
    )

    if "error" not in result:

        try:

            redis_client.setex(
                cache_key,
                3600,
                json.dumps(result)
            )

            print("[REDIS] Cached Successfully")

        except Exception as e:

            print(
                f"[REDIS CACHE ERROR] {e}"
            )

    return result