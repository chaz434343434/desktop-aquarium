"""Talks to the tank server (server/src/worker.js) on background threads, so a slow connection never
freezes the tank. Nothing is sent until the player presses Share. Results wait in a queue for the game."""
import json
import os
import queue
import re
import sys
try:
    import ssl
except ImportError:
    ssl = None
import threading
import urllib.error
import urllib.request

from .version import ONLINE_URL, VERSION

try:
    import certifi                   # the Mac build has no certificate list of its own
except ImportError:
    certifi = None

MAX_REPLY = 64000
ID = re.compile(r"^[1-9][0-9]{5}$")


def base_url():
    if sys.platform == "emscripten":                     # the web version talks to it another way (not yet)
        return ""
    url = os.environ.get("DA_ONLINE_URL")
    if url:
        return url.rstrip("/")
    if os.environ.get("SDL_VIDEODRIVER") == "dummy":     # automated tests never touch the real server by accident
        return ""
    return ONLINE_URL.rstrip("/")


def ssl_context():
    if ssl is None:
        return None
    if certifi:
        try:
            return ssl.create_default_context(cafile=certifi.where())
        except (OSError, ssl.SSLError):
            pass
    return ssl.create_default_context()


class Online:
    def __init__(self):
        self.results = queue.Queue()
        self.busy = set()

    @property
    def enabled(self):
        return bool(base_url())

    def send(self, kind, method, path, body=None, key=None, ctx=None):
        """one request at a time of each kind. False if one is already on its way."""
        if not self.enabled or kind in self.busy:
            return False
        self.busy.add(kind)
        threading.Thread(target=self._run, args=(kind, method, path, body, key, ctx), daemon=True).start()
        return True

    def _run(self, kind, method, path, body, key, ctx):
        status, data = "offline", None
        try:
            status, data = self._request(method, path, body, key)
        except Exception:                    # no internet, server down, nonsense reply: all just "not now"
            pass
        self.results.put(dict(kind=kind, status=status, data=data, ctx=ctx))

    def _request(self, method, path, body, key):
        raw = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(base_url() + path, data=raw, method=method,
                                     headers={"User-Agent": f"DesktopAquarium/{VERSION}"})
        if raw is not None:
            req.add_header("Content-Type", "application/json")
        if key:
            req.add_header("Authorization", "Bearer " + key)
        try:
            with urllib.request.urlopen(req, timeout=10, context=ssl_context()) as r:
                text = r.read(MAX_REPLY + 1)
        except urllib.error.HTTPError as e:
            return {403: "denied", 404: "notfound", 429: "busy"}.get(e.code, "offline"), None
        if len(text) > MAX_REPLY:
            return "offline", None
        data = json.loads(text.decode("utf-8"))
        return ("ok", data) if isinstance(data, dict) else ("offline", None)

    def poll(self):
        out = []
        while True:
            try:
                r = self.results.get_nowait()
            except queue.Empty:
                return out
            self.busy.discard(r["kind"])
            out.append(r)
