import asyncio
import pytest
from unittest.mock import patch, MagicMock

from app.services.cache_service import (
    CacheService,
    BoundedMemoryCache,
    cache_service,
)
from evaluation.evaluate_skills import load_dataset, evaluate_benchmark


def test_interview_cache_key_collision_prevention():
    """Verify different question counts, roles, or difficulties produce distinct cache keys."""
    key_5_q = CacheService.build_interview_cache_key("Backend Developer", "Tech", "Senior", "Hard", 5)
    key_10_q = CacheService.build_interview_cache_key("Backend Developer", "Tech", "Senior", "Hard", 10)
    key_diff = CacheService.build_interview_cache_key("Backend Developer", "Tech", "Senior", "Easy", 5)
    key_role = CacheService.build_interview_cache_key("Frontend Developer", "Tech", "Senior", "Hard", 5)

    assert key_5_q != key_10_q, "Different question counts must NOT collide!"
    assert key_5_q != key_diff, "Different difficulties must NOT collide!"
    assert key_5_q != key_role, "Different roles must NOT collide!"


def test_resume_cache_key_deterministic():
    """Identical PDF bytes + JD produce identical keys; different JDs produce distinct keys."""
    pdf_bytes = b"%PDF-1.4 sample content"
    key1 = CacheService.build_resume_cache_key(pdf_bytes, "Python developer needed")
    key2 = CacheService.build_resume_cache_key(pdf_bytes, "Python developer needed")
    key_other_jd = CacheService.build_resume_cache_key(pdf_bytes, "Java developer needed")
    key_no_jd = CacheService.build_resume_cache_key(pdf_bytes, None)

    assert key1 == key2
    assert key1 != key_other_jd
    assert key1 != key_no_jd


def test_bounded_memory_cache_eviction():
    """BoundedMemoryCache evicts oldest items when maxsize is exceeded."""
    async def _run():
        cache = BoundedMemoryCache(maxsize=3, default_ttl=60)
        await cache.set("k1", "v1")
        await cache.set("k2", "v2")
        await cache.set("k3", "v3")

        # All 3 exist
        assert await cache.get("k1") == "v1"

        # Add 4th item -> should evict oldest (k2 was accessed least recently because k1 was just read)
        await cache.set("k4", "v4")
        assert await cache.get("k2") is None
        assert await cache.get("k1") == "v1"
        assert await cache.get("k4") == "v4"

    asyncio.run(_run())


def test_cache_stampede_singleflight():
    """Concurrent requests for the same key only call compute_fn once."""
    async def _run():
        service = CacheService()
        service._redis_online = False
        call_count = 0

        async def expensive_computation():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return {"result": "success"}

        # Fire 5 concurrent requests for the exact same key
        tasks = [
            service.get_or_compute("shared_key_123", expensive_computation, ttl=60)
            for _ in range(5)
        ]
        results = await asyncio.gather(*tasks)

        # All 5 return the same data
        assert all(r == {"result": "success"} for r in results)
        # Compute function was executed ONLY ONCE
        assert call_count == 1

    asyncio.run(_run())


def test_redis_failure_fallback_graceful():
    """When Redis raises connection error, CacheService falls back to memory cache seamlessly."""
    async def _run():
        service = CacheService()
        # Mock Redis client to raise error
        service._redis_client.get = MagicMock(side_effect=Exception("Redis connection refused"))
        service._redis_client.setex = MagicMock(side_effect=Exception("Redis connection refused"))

        # Set and get should not raise exception
        await service.set("test_fallback_key", {"data": "preserved"}, ttl=60)
        val = await service.get("test_fallback_key")

        assert val == {"data": "preserved"}
        assert service.stats["redis_errors"] > 0

    asyncio.run(_run())


def test_evaluation_dataset_scoring_consistency():
    """Evaluation benchmark dataset scores with 0.0 standard deviation across multiple iterations."""
    dataset = load_dataset("../evaluation/evaluation_dataset.json")
    results = evaluate_benchmark(dataset)

    assert results["overall"]["total_samples"] == 5
    assert results["overall"]["precision"] > 0.8
    assert results["overall"]["recall"] > 0.7
    assert results["overall"]["scoring_consistency_variance"] == 0.0
