"""Serve the TreeSeasons app and catch frames posted by index.html?shot=<name>.

    python render_server.py [port]        (default 3012)

GET  -> static files from the app root (so the page is same-origin)
POST /frame?out=<tag>&n=<i>  body = PNG -> shots/renders/<tag>/frame_<i>.png
POST /done?out=<tag>                     -> prints a line, touches DONE
"""
import base64, http.server, os, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDERS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3012


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        if "POST" in (fmt % args):
            return                      # 800 frame posts would drown the log
        super().log_message(fmt, *args)

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        tag = os.path.basename(q.get("out", ["shot"])[0]) or "shot"
        d = os.path.join(RENDERS, tag)
        os.makedirs(d, exist_ok=True)
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if u.path == "/frame":
            n = int(q.get("n", ["0"])[0])
            if body.startswith(b"data:"):          # toDataURL payload
                body = base64.b64decode(body.split(b",", 1)[1])
            with open(os.path.join(d, f"frame_{n:05d}.png"), "wb") as f:
                f.write(body)
            if n % 60 == 0:
                print(f"[{tag}] frame {n}", flush=True)
        elif u.path == "/log":
            msg = body.decode("utf8", "replace")
            with open(os.path.join(d, "ERROR.txt"), "w", encoding="utf8") as f:
                f.write(msg)
            print(f"[{tag}] ERROR {msg}", flush=True)
        elif u.path == "/done":
            open(os.path.join(d, "DONE"), "w").close()
            print(f"[{tag}] DONE", flush=True)
        self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    print(f"serving {ROOT} on :{PORT}, frames -> {RENDERS}", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
