"""Mac end-to-end check of the self-updater, using the built app and a fake GitHub on localhost.
Runs on GitHub's Mac machines after build_assets/build_mac.sh:  python test_update_mac_e2e.py out/<the>.dmg
Installs the app into a temp 'Applications' folder, serves a newer .dmg whose app carries a
marker file, runs the game and waits for it to download, swap itself and start again."""
import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

dmg = os.path.abspath(sys.argv[1])
APP = "Desktop Aquarium.app"
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


tmp = tempfile.mkdtemp(prefix="da_update_test_")
apps = os.path.join(tmp, "Applications")
os.makedirs(apps)
mnt = os.path.join(tmp, "mnt")
os.makedirs(mnt)
subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", mnt, dmg], check=True)
subprocess.run(["ditto", os.path.join(mnt, APP), os.path.join(apps, APP)], check=True)
subprocess.run(["hdiutil", "detach", mnt], check=True)
install = os.path.join(apps, APP)

# the "new version": same app plus a marker, re-signed, in its own dmg
newsrc = os.path.join(tmp, "newsrc")
os.makedirs(newsrc)
subprocess.run(["ditto", install, os.path.join(newsrc, APP)], check=True)
with open(os.path.join(newsrc, APP, "Contents", "Resources", "UPDATED.txt"), "w") as fh:
    fh.write("updated by test\n")
subprocess.run(["codesign", "--force", "--deep", "--sign", "-", os.path.join(newsrc, APP)], check=True)
arch = "arm64" if os.uname().machine == "arm64" else "intel"
newdmg = os.path.join(tmp, f"Desktop.Aquarium.v9.9.9.Mac.{arch}.dmg")
subprocess.run(["hdiutil", "create", "-volname", "Desktop Aquarium", "-srcfolder", newsrc, "-ov",
                "-format", "UDZO", newdmg], check=True, stdout=subprocess.DEVNULL)
hits = {"api": 0, "dmg": 0}


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        port = self.server.server_address[1]
        if self.path.startswith("/latest"):
            hits["api"] += 1
            tag = "v9.9.9" if hits["api"] == 1 else "v0.0.1"
            other = "intel" if arch == "arm64" else "arm64"
            body = json.dumps({"tag_name": tag, "body": "test", "assets": [
                {"name": "Desktop.Aquarium.v9.9.9.zip", "size": 5,
                 "browser_download_url": f"http://127.0.0.1:{port}/windows.zip"},
                {"name": f"Desktop.Aquarium.v9.9.9.Mac.{other}.dmg", "size": 5,
                 "browser_download_url": f"http://127.0.0.1:{port}/wrong.dmg"},
                {"name": os.path.basename(newdmg), "size": os.path.getsize(newdmg),
                 "browser_download_url": f"http://127.0.0.1:{port}/update.dmg"}]}).encode()
        elif self.path.startswith("/update.dmg"):
            hits["dmg"] += 1
            body = open(newdmg, "rb").read()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
home = os.path.join(tmp, "home")
os.makedirs(home)
env = dict(os.environ, DA_UPDATE_API=f"http://127.0.0.1:{srv.server_address[1]}/latest", DA_AUTO_INSTALL="1",
           HOME=home)
env.pop("SDL_VIDEODRIVER", None)
exe = os.path.join(install, "Contents", "MacOS", "Desktop Aquarium")
p = subprocess.Popen([exe], env=env)
print("started", p.pid)


def app_pids():
    out = subprocess.run(["pgrep", "-f", os.path.join(install, "Contents", "MacOS")],
                         capture_output=True, text=True).stdout
    return [int(x) for x in out.split()]


marker = os.path.join(install, "Contents", "Resources", "UPDATED.txt")
restarted = None
deadline = time.time() + 150
while time.time() < deadline:
    if os.path.exists(marker) and p.poll() is not None:
        others = [x for x in app_pids() if x != p.pid]
        if others:
            restarted = others[0]
            break
    time.sleep(1)

check("the game asked the update server", hits["api"] >= 1)
check("it downloaded the dmg for this Mac's chip", hits["dmg"] == 1)
check("old game closed itself", p.poll() is not None)
check("the new app replaced the old one", os.path.exists(marker))
check("no leftover .old app", not os.path.exists(install + ".old"))
check("the new app is properly signed", subprocess.run(["codesign", "--verify", "--deep", install]).returncode == 0)
check("the game restarted by itself", restarted is not None)
check("save file written", os.path.exists(os.path.join(home, "Library", "Application Support",
                                                       "DesktopAquarium", "save.json")))
for pid in app_pids():
    subprocess.run(["kill", str(pid)])
srv.shutdown()
if not ok:
    log = os.path.join(tempfile.gettempdir(), "DesktopAquariumUpdate.log")
    if os.path.exists(log):
        print(open(log, errors="replace").read()[-2000:])
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
