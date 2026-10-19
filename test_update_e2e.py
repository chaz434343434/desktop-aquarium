"""End-to-end check of the self-updater using the built exe and a fake GitHub on localhost.
Run after build_release.bat:  python test_update_e2e.py
Copies the release to a temp 'install' folder, serves a fake newer release that contains a
marker file, runs the exe (top monitor, temp AppData) and waits for it to update + restart."""
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from purrfin.version import VERSION  # noqa: E402
REL = os.path.join(ROOT, "release", "v" + VERSION, "Desktop Aquarium")
EXE = "DesktopAquarium.exe"

tmp = tempfile.mkdtemp(prefix="da_update_test_")
install = os.path.join(tmp, "install", "Desktop Aquarium")
shutil.copytree(REL, install)
appdata = os.path.join(tmp, "appdata")
os.makedirs(os.path.join(appdata, "DesktopAquarium"))
with open(os.path.join(appdata, "DesktopAquarium", "save.json"), "w") as fh:   # show on the top monitor
    json.dump({"settings": {"monitor": 2}, "fish": [{"uid": 1, "sp": "sunflower", "name": "Sunny", "lv": 1,
                                                       "xp": 0, "full": 80, "happy": 70}]}, fh)

# the "new version": same files plus a marker
newdir = os.path.join(tmp, "build", "Desktop Aquarium")
shutil.copytree(REL, newdir)
with open(os.path.join(newdir, "UPDATED.txt"), "w") as fh:
    fh.write("updated by test\n")
zpath = shutil.make_archive(os.path.join(tmp, "update"), "zip", os.path.join(tmp, "build"), "Desktop Aquarium")

hits = {"api": 0, "zip": 0}


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        port = self.server.server_address[1]
        if self.path.startswith("/latest"):
            hits["api"] += 1
            tag = "v9.9.9" if hits["api"] == 1 else "v1.1.0"     # only offer the update once
            body = json.dumps({"tag_name": tag, "body": "test", "assets": [
                {"name": "Desktop Aquarium.zip", "size": os.path.getsize(zpath),
                 "browser_download_url": f"http://127.0.0.1:{port}/update.zip"}]}).encode()
            ctype = "application/json"
        elif self.path.startswith("/update.zip"):
            hits["zip"] += 1
            body = open(zpath, "rb").read()
            ctype = "application/zip"
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
env = dict(os.environ, DA_UPDATE_API=f"http://127.0.0.1:{srv.server_address[1]}/latest", DA_AUTO_INSTALL="1",
           APPDATA=appdata)
p = subprocess.Popen([os.path.join(install, EXE), "--monitor", "2"], env=env, cwd=install)
first_pid = p.pid
print("started", first_pid)

ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def exe_pids():
    out = subprocess.run(["tasklist", "/fi", f"imagename eq {EXE}", "/fo", "csv", "/nh"],
                         capture_output=True, text=True).stdout
    return [int(line.split('","')[1]) for line in out.splitlines() if EXE in line]


deadline = time.time() + 120
marker = os.path.join(install, "UPDATED.txt")
restarted = None
while time.time() < deadline:
    if os.path.exists(marker):
        others = [x for x in exe_pids() if x != first_pid]
        if others and p.poll() is not None:
            restarted = others[0]
            break
    time.sleep(1)

check("the game asked the update server", hits["api"] >= 1)
check("it downloaded the new version", hits["zip"] == 1)
check("old game closed itself", p.poll() is not None)
check("new files were copied into the install folder", os.path.exists(marker))
check("the game restarted by itself", restarted is not None)
time.sleep(8)        # let the restarted game check again: it must NOT update a second time
check("no update loop after restart", hits["zip"] == 1)
saved = os.path.exists(os.path.join(appdata, "DesktopAquarium", "save.json"))
check("save file still there", saved)

# close only test copies (they run from our temp install folder), never a real game
ps = ("Get-CimInstance Win32_Process -Filter \"Name='" + EXE + "'\" | "
      "Where-Object { $_.ExecutablePath -like '*" + os.path.basename(tmp) + "*' } | "
      "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
srv.shutdown()
time.sleep(1)
if ok:
    shutil.rmtree(tmp, ignore_errors=True)
else:
    print("kept for inspection:", tmp)
    log = os.path.join(tempfile.gettempdir(), "DesktopAquariumUpdate.log")
    if os.path.exists(log):
        print(open(log, encoding="utf-8", errors="replace").read()[-1500:])
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
