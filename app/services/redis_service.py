import redis
from typing import Optional
from app.core.config import REDIS_HOST, REDIS_PORT

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=0.5,
    socket_timeout=0.5,
)

_redis_available: Optional[bool] = None


def is_redis_available() -> bool:
    global _redis_available
    if _redis_available is None:
        try:
            redis_client.ping()
            _redis_available = True
        except Exception:
            _redis_available = False
    return _redis_available