import asyncio
from typing import Dict, Optional, AsyncGenerator
import json
import time

class StageBroadcaster:
    """
    Real-time processing stage broadcaster for SSE event streams.
    Tracks actual pipeline stages per job/session and guarantees that
    'Completed' is never emitted prematurely or on error.
    """

    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._created_at: Dict[str, float] = {}

    def get_or_create_queue(self, job_id: str) -> asyncio.Queue:
        if job_id not in self._queues:
            self._queues[job_id] = asyncio.Queue()
            self._created_at[job_id] = time.time()
        return self._queues[job_id]

    async def emit_stage(self, job_id: str, stage_name: str, payload: Optional[dict] = None):
        """Emit an actual processing stage event to the job's event stream."""
        queue = self.get_or_create_queue(job_id)
        event_data = {
            "stage": stage_name,
            "timestamp": time.time(),
        }
        if payload:
            event_data.update(payload)
            
        await queue.put(event_data)

    async def emit_error(self, job_id: str, error_message: str):
        """Emit a pipeline failure stage. Never emits 'Completed'."""
        await self.emit_stage(job_id, f"Error: {error_message}")

    async def stage_generator(self, job_id: str, timeout: float = 60.0) -> AsyncGenerator[dict, None]:
        """Async generator yielding SSE events for the given job."""
        queue = self.get_or_create_queue(job_id)
        start_time = time.time()

        try:
            while True:
                # Wait for next event or check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    yield {
                        "event": "message",
                        "data": "Error: Stream timeout waiting for processing."
                    }
                    break

                try:
                    event = await asyncio.wait_for(queue.get(), timeout=5.0)
                    stage = event.get("stage", "")

                    yield {
                        "event": "message",
                        "data": stage
                    }

                    if stage == "Completed" or stage.startswith("Error"):
                        break

                except asyncio.TimeoutError:
                    # Keep-alive heartbeat comment
                    yield {
                        "event": "ping",
                        "data": "keep-alive"
                    }

        finally:
            # Clean up queue memory
            self._queues.pop(job_id, None)
            self._created_at.pop(job_id, None)


# Global broadcaster singleton
stage_broadcaster = StageBroadcaster()


async def stream_job_progress(job_id: str) -> AsyncGenerator[dict, None]:
    """Helper for FastAPI EventSourceResponse."""
    async for event in stage_broadcaster.stage_generator(job_id):
        yield event