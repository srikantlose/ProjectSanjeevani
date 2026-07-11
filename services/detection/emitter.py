"""Posts IncidentCandidate payloads to the API, queuing to disk on failure (plan.md §7.7)."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import httpx


class Emitter:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        queue_path: str | Path = "data/queue/pending_incidents.jsonl",
        retry_interval_s: float = 5.0,
        start_retry_thread: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.queue_path = Path(queue_path)
        self.retry_interval_s = retry_interval_s
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        if start_retry_thread:
            self._thread = threading.Thread(target=self._retry_loop, daemon=True)
            self._thread.start()

    def emit(self, payload: dict) -> None:
        if not self._post(payload):
            self._queue(payload)

    def _post(self, payload: dict) -> bool:
        try:
            response = httpx.post(f"{self.base_url}/api/incidents/candidate", json=payload, timeout=3.0)
            return 200 <= response.status_code < 300
        except httpx.HTTPError:
            return False

    def _queue(self, payload: dict) -> None:
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.queue_path, "a") as f:
            f.write(json.dumps(payload) + "\n")

    def flush_queue(self) -> None:
        """Re-POSTs every queued payload; rewrites the queue file with only the ones that still fail."""
        if not self.queue_path.exists():
            return
        with open(self.queue_path) as f:
            lines = [line for line in f if line.strip()]

        still_failing = []
        for line in lines:
            payload = json.loads(line)
            if not self._post(payload):
                still_failing.append(line)

        if still_failing:
            with open(self.queue_path, "w") as f:
                f.writelines(still_failing)
        else:
            self.queue_path.unlink(missing_ok=True)

    def _retry_loop(self) -> None:
        while not self._stop_event.wait(self.retry_interval_s):
            self.flush_queue()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.retry_interval_s + 1)
