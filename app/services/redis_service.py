import redis

from app.core.config import (
    REDIS_HOST,
    REDIS_PORT
)

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1
)

try:
    redis_client.ping()
    print("[REDIS] Connected Successfully")
except Exception as e:
    print(f"[REDIS] Connection Failed: {e}")