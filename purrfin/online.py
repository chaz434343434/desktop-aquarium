"""Talks to the tank server (server/src/worker.js) on background threads, so a slow connection never
freezes the tank. Nothing is sent until the player presses Share. Results wait in a queue for the game.
In the web version there are no threads: the browser's own fetch does the work, and poll() picks up the
answers on later frames. The game is served from the same site as the server, so addresses are relative."""
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
WEB = sys.platform == "emscripten"

# the web version's helper, added to the page once: fetch() in the background, answers kept until collected
WEB_JS = """
window.daNet = window.daNet || {done: {}};
window.daFetch = function (id, method, url, body, key) {
  const headers = {};
  if (body) headers["content-type"] = "application/json";
  if (key) headers["authorization"] = "Bearer " + key;
  const stop = new AbortController();
  const timer = setTimeout(() => stop.abort(), 10000);
  fetch(url, {method: method, headers: headers, body: body || undefined, signal: stop.signal,
              cache: "no-store", credentials: "omit"})
    .then(r => r.text().then(t => {
      clearTimeout(timer);
      window.daNet.done[id] = JSON.stringify({s: r.status, t: t.length > 64000 ? "" : t});
    }))
    .catch(() => { clearTimeout(timer); window.daNet.done[id] = JSON.stringify({s: 0}); });
};
window.daTake = function (id) {
  const v = window.daNet.done[id];
  if (v === undefined) return null;
  delete window.daNet.done[id];
  return v;
};
"""


def _window():
    import platform
    return platform.window


def base_url():
    if WEB:                                              # same site as the game: relative addresses
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
        self.web_waiting = {}          # web: request number -> (kind, ctx)
        self.web_next = 1
        self.web_ready = False

    @property
    def enabled(self):
        return WEB or bool(base_url())

    def send(self, kind, method, path, body=None, key=None, ctx=None):
        """one request at a time of each kind. False if one is already on its way."""
        if not self.enabled or kind in self.busy:
            return False
        if WEB:
            return self._send_web(kind, method, path, body, key, ctx)
        self.busy.add(kind)
        threading.Thread(target=self._run, args=(kind, method, path, body, key, ctx), daemon=True).start()
        return True

    def _send_web(self, kind, method, path, body, key, ctx):
        try:
            win = _window()
            if not self.web_ready:
                win.eval(WEB_JS)
                self.web_ready = True
            n = self.web_next
            self.web_next += 1
            win.daFetch(n, method, path, json.dumps(body) if body is not None else "", key or "")
        except Exception:
            self.results.put(dict(kind=kind, status="offline", data=None, ctx=ctx))
            self.busy.add(kind)
            return True
        self.busy.add(kind)
        self.web_waiting[n] = (kind, ctx)
        return True

    def _poll_web(self):
        if not self.web_waiting:
            return
        try:
            win = _window()
        except Exception:
            return
        for n in list(self.web_waiting):
            try:
                raw = win.daTake(n)
            except Exception:
                raw = '{"s": 0}'
            if raw is None or str(raw) in ("null", "undefined"):
                continue
            kind, ctx = self.web_waiting.pop(n)
            self.results.put(dict(kind=kind, ctx=ctx, **self._web_answer(str(raw))))

    @staticmethod
    def _web_answer(raw):
        """the browser's answer -> (status, data), the same way the desktop version reads a reply"""
        try:
            r = json.loads(raw)
            code = int(r.get("s", 0))
        except (ValueError, TypeError, AttributeError):
            return dict(status="offline", data=None)
        if code in (403, 404, 429):
            return dict(status={403: "denied", 404: "notfound", 429: "busy"}[code], data=None)
        if not 200 <= code < 300:
            return dict(status="offline", data=None)
        try:
            data = json.loads(r.get("t") or "")
        except (ValueError, TypeError):
            return dict(status="offline", data=None)
        return dict(status="ok", data=data) if isinstance(data, dict) else dict(status="offline", data=None)

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
        if WEB:
            self._poll_web()
        out = []
        while True:
            try:
                r = self.results.get_nowait()
            except queue.Empty:
                return out
            self.busy.discard(r["kind"])
            out.append(r)
