import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.core.config import CORS_ORIGINS
from app.core.telemetry import logger, metrics
from app.routes.resume import router as resume_router
from app.routes.interview import router as interview_router
from app.routes.health import router as health_router

app = FastAPI(
    title="ResumeIQ API",
    description="Production-grade evidence-based job-matching and interview preparation platform",
    version="1.0.0",
)

# Configure explicit CORS origins from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def telemetry_and_logging_middleware(request: Request, call_next):
    """Measures request execution time, records metrics, and provides structured logging."""
    start_time = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as exc:
        logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
        raise
    finally:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        metrics.record(
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_ms=duration_ms,
        )
        # Avoid logging noisy health or metrics endpoints repeatedly
        if request.url.path not in ("/health", "/metrics", "/resume/stream"):
            logger.info(
                f"{request.method} {request.url.path} -> {status_code} in {duration_ms}ms"
            )


# Mount feature routers
app.include_router(health_router)
app.include_router(resume_router)
app.include_router(interview_router)