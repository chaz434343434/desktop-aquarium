"""Headless check of Options > Check for updates: newer version / up to date / GitHub unreachable.
Run: python test_check_updates.py [shot.png]"""
import http.server
import json
import os
import sys
import tempfile
import threading
import time

state = {"tag": "v9.9.9"}


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({"tag_name": state["tag"], "assets": [
            {"name": "Desktop Aquarium.zip", "size": 1,
             "browser_download_url": "http://127.0.0.1/none.zip"},
            {"name": "Desktop.Aquarium.Mac.arm64.dmg", "size": 1,
             "browser_download_url": "http://127.0.0.1/none.dmg"},
            {"name": "Desktop.Aquarium.Mac.intel.dmg", "size": 1,
             "browser_download_url": "http://127.0.0.1/none.dmg"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["DA_UPDATE_API"] = f"http://127.0.0.1:{srv.server_address[1]}/latest"
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame  # noqa: E402
from purrfin import updater  # noqa: E402
from purrfin.game import Game  # noqa: E402
from purrfin.version import VERSION  # noqa: E402

pygame.init()
g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
g.state["settings"]["autoupdate"] = False      # only manual checks in this test
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def press_and_wait():
    g.toasts.clear()
    g.check_updates()
    for _ in range(100):
        g.update(0.05)
        if not g.manual_check:
            break
        time.sleep(0.05)
    return [t[0] for t in g.toasts]


msgs = press_and_wait()
check("newer version -> update popup opens", g.ui.update_prompt and g.updater.state == "available")
g.ui.update_prompt = False

state["tag"] = "v" + VERSION
msgs = press_and_wait()
check(f"same version -> 'up to date' message {msgs}", any("up to date" in m for m in msgs))

updater.API = "http://127.0.0.1:1/latest"           # nothing listens there
msgs = press_and_wait()
check(f"offline -> 'couldn't reach GitHub' message {msgs}", any("Couldn't reach" in m for m in msgs))

g.ui.panel = "settings"
g.draw()
g.draw()
if len(sys.argv) > 1:
    pygame.image.save(g.screen.subsurface(g.ui.panel_rect), sys.argv[1])
srv.shutdown()
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
