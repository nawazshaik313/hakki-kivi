"""End-to-end over real HTTP against a fake Ollama server (same API shape as Ollama)."""
import dataclasses
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from hakki_kivi import trip
from hakki_kivi.config import Settings
from hakki_kivi.detect import load_detections_json

ROOT = Path(__file__).resolve().parents[1]


class FakeOllama(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send({"models": [{"name": "gemma4:e2b-it-qat"}]})

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert req["format"] == "json" and req["stream"] is False
        prompt = req["messages"][-1]["content"]
        name = json.loads(prompt[prompt.find("{"): prompt.find("}") + 1])["english_name"]
        cards = {"en": {"name": name, "tip": "tip", "challenge": "listen"},
                 "kn": {"name": f"{name} (ಕನ್ನಡ)", "tip": "ಸುಳಿವು", "challenge": "ಆಲಿಸಿ"}}
        self._send({"message": {"role": "assistant", "content": "```json\n" + json.dumps({"cards": cards}) + "\n```"}})


def test_full_pipeline_with_http_ollama(tmp_path):
    server = HTTPServer(("127.0.0.1", 0), FakeOllama)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        s = dataclasses.replace(Settings(), output_dir=tmp_path,
                                ollama_url=f"http://127.0.0.1:{server.server_port}")
        dets = load_detections_json(ROOT / "samples" / "demo_detections.json")
        result = trip.process_detections(dets, s, ["en", "kn"])
        trip.write_outputs(result, s, ["en", "kn"], "HTTP walk")
        assert result.model_used == "gemma4:e2b-it-qat"
        assert all(c.generated_by == "gemma4:e2b-it-qat" for c in result.cards)
        assert "ಕನ್ನಡ" in result.html_path.read_text(encoding="utf-8")
    finally:
        server.shutdown()
