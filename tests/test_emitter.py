import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from services.detection.emitter import Emitter


class _RecordingHandler(BaseHTTPRequestHandler):
    received = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        _RecordingHandler.received.append(json.loads(body))
        self.send_response(201)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # silence default request logging to stderr


def test_emit_queues_on_unreachable_host_then_retry_drains(tmp_path):
    queue_path = tmp_path / "queue" / "pending_incidents.jsonl"
    emitter = Emitter(base_url="http://localhost:1", queue_path=queue_path, start_retry_thread=False)

    payload = {"id": "inc_test_001", "camera_id": "cam1"}
    emitter.emit(payload)

    assert queue_path.exists()
    with open(queue_path) as f:
        queued = [json.loads(line) for line in f if line.strip()]
    assert queued == [payload]

    _RecordingHandler.received = []
    server = HTTPServer(("localhost", 0), _RecordingHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        emitter.base_url = f"http://localhost:{port}"
        emitter.flush_queue()

        assert not queue_path.exists()
        assert _RecordingHandler.received == [payload]
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_flush_queue_is_noop_when_no_queue_file(tmp_path):
    queue_path = tmp_path / "queue" / "pending_incidents.jsonl"
    emitter = Emitter(base_url="http://localhost:1", queue_path=queue_path, start_retry_thread=False)
    emitter.flush_queue()  # must not raise
    assert not queue_path.exists()
