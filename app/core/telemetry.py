import time
import logging
import re
from typing import Dict, Any, List
from app.core.config import LOG_LEVEL

# Setup root structured logger
logger = logging.getLogger("resumeiq")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [resumeiq] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Redaction patterns for sensitive data
_API_KEY_PATTERN = re.compile(r"gsk_[a-zA-Z0-9_-]{20,}|Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE)


def redact_sensitive(text: str) -> str:
    """Mask API keys or authorization tokens from logs."""
    if not isinstance(text, str):
        return text
    return _API_KEY_PATTERN.sub("[REDACTED_SECRET]", text)


class MetricsCollector:
    """Lightweight in-memory latency and error metrics collector."""

    def __init__(self):
        self.start_time = time.time()
        self.total_requests = 0
        self.total_errors = 0
        self.total_latency_ms = 0.0
        self.status_codes: Dict[int, int] = {}
        self._latencies: List[float] = []

    def record(self, method: str, path: str, status_code: int, duration_ms: float):
        self.total_requests += 1
        self.total_latency_ms += duration_ms
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        
        if status_code >= 400:
            self.total_errors += 1

        if len(self._latencies) < 1000:
            self._latencies.append(duration_ms)
        else:
            self._latencies.pop(0)
            self._latencies.append(duration_ms)

    def summary(self) -> Dict[str, Any]:
        uptime_seconds = int(time.time() - self.start_time)
        avg_latency = (
            round(self.total_latency_ms / self.total_requests, 2)
            if self.total_requests > 0
            else 0.0
        )
        p95_latency = (
            round(sorted(self._latencies)[int(len(self._latencies) * 0.95)], 2)
            if self._latencies
            else 0.0
        )

        return {
            "uptime_seconds": uptime_seconds,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": (
                round((self.total_errors / self.total_requests) * 100, 2)
                if self.total_requests > 0
                else 0.0
            ),
            "avg_latency_ms": avg_latency,
            "p95_latency_ms": p95_latency,
            "status_codes": self.status_codes,
        }


metrics = MetricsCollector()
