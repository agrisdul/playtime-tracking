import json
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

STATE_FILE = "state.json"

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"sessions": []}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def now_ms():
    return int(time.time() * 1000)

class Handler(SimpleHTTPRequestHandler):
    def _send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/state":
            state = load_state()
            # Clean expired sessions only if you want auto-removal; here we keep them and mark expired on client.
            self._send_json(state)
            return

        # serve files normally (admin.html, screen.html, etc.)
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/add":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            body = json.loads(raw) if raw else {}

            nick = (body.get("nick") or "").strip()
            minutes = int(body.get("minutes") or 0)
            players = int(body.get("players") or 1)

            if not nick or minutes <= 0:
                self._send_json({"ok": False, "error": "nick and minutes required"}, status=400)
                return

            state = load_state()
            session_id = f"{int(time.time())}-{len(state['sessions'])+1}"
            start = now_ms()
            end = start + minutes * 60 * 1000

            state["sessions"].append({
                "id": session_id,
                "nick": nick,
                "players": players,
                "minutes": minutes,
                "start_ms": start,
                "end_ms": end
            })
            save_state(state)
            self._send_json({"ok": True, "id": session_id})
            return

        if parsed.path == "/api/remove":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            body = json.loads(raw) if raw else {}
            sid = body.get("id")

            state = load_state()
            state["sessions"] = [s for s in state["sessions"] if s["id"] != sid]
            save_state(state)
            self._send_json({"ok": True})
            return

        if parsed.path == "/api/clear":
            save_state({"sessions": []})
            self._send_json({"ok": True})
            return

        self._send_json({"ok": False, "error": "unknown endpoint"}, status=404)

def main():
    host = "0.0.0.0"
    port = 8080
    print(f"Server running at http://{host}:{port}")
    print("Open /admin.html on iPad, /screen.html on TV")
    ThreadingHTTPServer((host, port), Handler).serve_forever()

if __name__ == "__main__":
    main()
