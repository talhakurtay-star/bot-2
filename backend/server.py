"""Jarvis sunucusu - SIFIR HARİCİ PAKET (sadece Python standart kütüphanesi).

Hiçbir 'pip install' gerektirmez. Python'un kendisiyle çalışır:
    python server.py
Tarayıcıda http://127.0.0.1:8000 otomatik açılır.
"""
import os
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import brain
import memory

HOST = "127.0.0.1"
PORT = int(os.environ.get("JARVIS_PORT", "8000"))
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".json": "application/json; charset=utf-8",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # sessiz

    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            return self._send_json(brain.health())
        if path == "/reminders/due":
            return self._send_json({"due": memory.pop_due_reminders()})
        if path in ("/", ""):
            return self._send_file(os.path.join(FRONTEND_DIR, "index.html"))
        # statik dosya (güvenli: yalnızca frontend klasörü)
        safe = os.path.normpath(path).lstrip("/\\")
        full = os.path.normpath(os.path.join(FRONTEND_DIR, safe))
        if full.startswith(os.path.normpath(FRONTEND_DIR)) and os.path.isfile(full):
            return self._send_file(full)
        self.send_error(404)

    def do_POST(self):
        if self.path == "/chat":
            data = self._read_json()
            reply = brain.chat(data.get("message", ""), data.get("session_id", "default"))
            return self._send_json({"reply": reply})
        if self.path == "/reset":
            data = self._read_json()
            memory.clear_session(data.get("session_id", "default"))
            return self._send_json({"status": "ok"})
        self.send_error(404)


def main():
    memory.init_db()
    url = f"http://{HOST}:{PORT}"
    print(f"Jarvis calisiyor -> {url}  (kapatmak icin bu pencereyi kapatin)")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
