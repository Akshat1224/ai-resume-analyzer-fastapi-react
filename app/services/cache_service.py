import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from typing import Optional, Any, Dict
import redis

from app.core.config import REDIS_HOST, REDIS_PORT, GROQ_MODEL
from app.core.telemetry import logger

SCHEMA_VERSION = "v1.2"
DEFAULT_CACHE_TTL = 3600  # 1 hour
MAX_MEMORY_CACHE_ITEMS = 500
REDIS_RETRY_INTERVAL = 30.0  # seconds before checking offline Redis again


class BoundedMemoryCache:
    """Thread-safe bounded in-memory LRU cache with TTL expiration."""

    def __init__(self, maxsize: int = MAX_MEMORY_CACHE_ITEMS, default_ttl: int = DEFAULT_CACHE_TTL):
        self._maxsize = maxsize
        self._default_ttl = default_ttl
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key not in self._cache:
                return None
            val, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return val

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        async with self._lock:
            expiry = time.time() + (ttl or self._default_ttl)
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, expiry)
            if len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()


class CacheService:
    """
    Tiered caching system:
      1. Primary: Redis (with circuit breaker to prevent blocking when offline)
      2. Fallback: Bounded in-memory LRU cache
      3. Concurrency: Stampede locking per key
    """

    def __init__(self):
        self._redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
        )
        self._redis_online: Optional[bool] = None
        self._last_redis_check: float = time.time()

        self._memory_cache = BoundedMemoryCache()
        self._key_locks: Dict[str, asyncio.Lock] = {}
        self._locks_mutex = asyncio.Lock()
        self.stats = {"hits": 0, "misses": 0, "redis_errors": 0}

    def _can_try_redis(self) -> bool:
        now = time.time()
        if self._redis_online is False:
            if now - self._last_redis_check < REDIS_RETRY_INTERVAL:
                return False
        return True

    def _mark_redis_failure(self):
        self._redis_online = False
        self._last_redis_check = time.time()
        self.stats["redis_errors"] += 1

    def _mark_redis_success(self):
        self._redis_online = True
        self._last_redis_check = time.time()

    async def _get_key_lock(self, key: str) -> asyncio.Lock:
        async with self._locks_mutex:
            if key not in self._key_locks:
                self._key_locks[key] = asyncio.Lock()
            return self._key_locks[key]

    # Deterministic Cache Key Builders
    @staticmethod
    def build_resume_cache_key(pdf_bytes: bytes, job_description: Optional[str] = None) -> str:
        pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()[:16]
        jd_norm = (job_description or "").strip().lower()
        jd_hash = hashlib.sha256(jd_norm.encode("utf-8")).hexdigest()[:16] if jd_norm else "none"
        return f"resumeiq:analysis:{SCHEMA_VERSION}:{GROQ_MODEL}:{pdf_hash}:{jd_hash}"

    @staticmethod
    def build_interview_cache_key(
        role: str,
        industry: str,
        experience_level: str,
        difficulty: str,
        num_questions: int = 5,
    ) -> str:
        r_norm = role.strip().lower()
        i_norm = industry.strip().lower()
        e_norm = experience_level.strip().lower()
        d_norm = difficulty.strip().lower()
        return (
            f"resumeiq:interview:{SCHEMA_VERSION}:{GROQ_MODEL}:"
            f"{r_norm}:{i_norm}:{e_norm}:{d_norm}:{num_questions}"
        )

    async def get(self, key: str) -> Optional[Any]:
        """Fetch item from Redis with fast fallback to bounded in-memory cache."""
        if self._can_try_redis():
            try:
                val = self._redis_client.get(key)
                self._mark_redis_success()
                if val is not None:
                    self.stats["hits"] += 1
                    try:
                        return json.loads(val)
                    except Exception:
                        return val
            except Exception as e:
                self._mark_redis_failure()
                logger.debug(f"Redis get failed for {key}: {e}")

        mem_val = await self._memory_cache.get(key)
        if mem_val is not None:
            self.stats["hits"] += 1
            return mem_val

        self.stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> None:
        """Store item in Redis and bounded in-memory fallback."""
        serialized = json.dumps(value) if not isinstance(value, str) else value

        if self._can_try_redis():
            try:
                self._redis_client.setex(key, ttl, serialized)
                self._mark_redis_success()
            except Exception as e:
                self._mark_redis_failure()
                logger.debug(f"Redis set failed for {key}: {e}")

        await self._memory_cache.set(key, value, ttl=ttl)

    async def delete(self, key: str) -> None:
        """Invalidate key in Redis and in-memory cache."""
        if self._can_try_redis():
            try:
                self._redis_client.delete(key)
            except Exception:
                self._mark_redis_failure()
        await self._memory_cache.delete(key)

    async def get_or_compute(self, key: str, compute_fn, ttl: int = DEFAULT_CACHE_TTL) -> Any:
        """Stampede-protected cache fetch-or-compute with singleflight lock per key."""
        cached = await self.get(key)
        if cached is not None:
            return cached

        lock = await self._get_key_lock(key)
        async with lock:
            cached = await self.get(key)
            if cached is not None:
                return cached

            computed = await compute_fn()
            if computed is not None and (not isinstance(computed, dict) or "error" not in computed):
                await self.set(key, computed, ttl=ttl)

            return computed


cache_service = CacheService()
