"""Checks GitHub for a newer release, downloads it and swaps it in.

Flow: check() asks the GitHub API for the latest release of UPDATE_REPO. If its tag is newer
than VERSION and it has a .zip attached, state becomes "available". install() downloads +
unzips it in the background, writes a tiny batch file that waits for this game to close,
copies the new files over the install folder and starts the game again.
Only the installed .exe can update itself; running from source just says an update exists.

macOS: the release has a .dmg per chip (Apple Silicon / Intel). It's mounted with hdiutil, the new
"Desktop Aquarium.app" is copied out, and a small shell script swaps it in after the game quits.
"""
import json
import os
import platform
import shutil
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from .version import VERSION, UPDATE_REPO

EXE_NAME = "DesktopAquarium.exe"
IS_MAC = sys.platform == "darwin"
APP_NAME = "Desktop Aquarium.app"
# tests can point this at a local server
API = os.environ.get("DA_UPDATE_API") or (
    f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest" if UPDATE_REPO else "")
ALLOWED_HOSTS = ("github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com")


def parse_version(v):
    nums = [int(x) for x in re.findall(r"\d+", v or "")[:3]]
    return tuple(nums + [0] * (3 - len(nums)))


def is_newer(tag, current=VERSION):
    return parse_version(tag) > parse_version(current)


def frozen():
    return getattr(sys, "frozen", False)


def install_dir():
    """the folder (Windows) or the .app bundle (Mac) that gets replaced"""
    if not frozen():
        return None
    if IS_MAC:
        app = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", ".."))
        return app if app.endswith(".app") else None
    return os.path.dirname(sys.executable)


def mac_arch():
    return "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "intel"


def pick_asset(assets, mac=None):
    """the download meant for this computer. Windows: the .zip; Mac: the .dmg for this chip.
    (Old Windows copies take the first .zip, so Mac downloads are never .zip files.)"""
    mac = IS_MAC if mac is None else mac
    for a in assets:
        n = a.get("name", "").lower()
        if mac and n.endswith(".dmg") and mac_arch() in n:
            return a
        if not mac and n.endswith(".zip") and "mac" not in n:
            return a
    return None


def _host_ok(url):
    host = urllib.parse.urlparse(url).hostname or ""
    if os.environ.get("DA_UPDATE_API"):
        return True
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


class Updater:
    def __init__(self):
        self.state = "idle"        # idle | checking | none | offline | available | downloading | ready | error
        self.latest = None         # dict(tag, url, size, notes)
        self.progress = 0.0
        self.error = ""
        self.last_check = 0.0
        self.script = None

    @property
    def enabled(self):
        return bool(API)

    # ------------------------------------------------------------ check
    def check(self, force=False):
        if not self.enabled or self.state in ("checking", "downloading", "ready"):
            return
        if not force and time.time() - self.last_check < 6 * 3600:
            return
        self.last_check = time.time()
        self.state = "checking"
        threading.Thread(target=self._check, daemon=True).start()

    def _check(self):
        try:
            req = urllib.request.Request(API, headers={"User-Agent": "DesktopAquarium",
                                                       "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
            tag = data.get("tag_name", "")
            asset = pick_asset(data.get("assets", []))
            if is_newer(tag) and asset and _host_ok(asset["browser_download_url"]):
                self.latest = dict(tag=tag, url=asset["browser_download_url"], size=asset.get("size", 0),
                                   notes=(data.get("body") or "").strip())
                self.state = "available"
            else:
                self.state = "none"
        except urllib.error.HTTPError as e:
            self.error = str(e)
            self.state = "none" if e.code == 404 else "offline"     # 404 = no release published yet
        except Exception as e:          # offline, rate limited... try again later
            self.error = str(e)
            self.state = "offline"

    # ------------------------------------------------------------ install
    def install(self):
        self.error = ""
        if self.state != "available" or not frozen():
            return False
        if IS_MAC:
            d = install_dir() or ""
            if "AppTranslocation" in d or not os.access(os.path.dirname(d) or "/", os.W_OK):
                self.error = "Move Desktop Aquarium into your Applications folder first, then update."
                return False
        self.state = "downloading"
        self.progress = 0.0
        threading.Thread(target=self._download, daemon=True).start()
        return True

    def _download(self):
        try:
            tmp = tempfile.mkdtemp(prefix="DesktopAquariumUpdate_")
            zpath = os.path.join(tmp, "update.dmg" if IS_MAC else "update.zip")
            req = urllib.request.Request(self.latest["url"], headers={"User-Agent": "DesktopAquarium"})
            with urllib.request.urlopen(req, timeout=60) as r, open(zpath, "wb") as out:
                total = int(r.headers.get("Content-Length") or self.latest.get("size") or 0)
                got = 0
                while True:
                    chunk = r.read(65536)
                    if not chunk:
                        break
                    out.write(chunk)
                    got += len(chunk)
                    if total:
                        self.progress = got / total
            src = os.path.join(tmp, "new")
            if IS_MAC:
                app = extract_dmg(zpath, src)
                self.script = write_mac_swap_script(tmp, app, install_dir(), os.getpid())
            else:
                with zipfile.ZipFile(zpath) as z:
                    z.extractall(src)
                app = find_app_folder(src)
                if not app:
                    raise RuntimeError("the update zip has no " + EXE_NAME)
                self.script = write_swap_script(tmp, app, install_dir(), os.getpid())
            self.state = "ready"
        except Exception as e:
            self.error = str(e)
            self.state = "error"

    def finish(self):
        """start the swap script; the caller must save and quit right after"""
        if self.state == "ready" and self.script and IS_MAC:
            subprocess.Popen(["/bin/sh", self.script], start_new_session=True, close_fds=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=tempfile.gettempdir())
            return True
        if self.state == "ready" and self.script:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            subprocess.Popen(["cmd.exe", "/c", self.script], creationflags=flags, close_fds=True,
                             cwd=tempfile.gettempdir())
            return True
        return False


def find_app_folder(root):
    for dirpath, _, files in os.walk(root):
        if EXE_NAME in files:
            return dirpath
    return None


LOG = os.path.join(tempfile.gettempdir(), "DesktopAquariumUpdate.log")


def write_swap_script(tmp, src, dst, pid):
    """batch file that runs after the game closes. No console, so it waits with ping, not timeout."""
    bat = os.path.join(os.path.dirname(tmp), f"DesktopAquariumSwap_{pid}.bat")
    exe = os.path.join(dst, EXE_NAME)
    with open(bat, "w", encoding="utf-8") as fh:
        fh.write(f"""@echo off
echo [%date% %time%] updating {dst} >> "{LOG}"
set n=0
:wait
tasklist /fi "PID eq {pid}" /nh 2>nul | find " {pid} " >nul || goto copy
set /a n+=1
if %n% gtr 60 goto copy
ping -n 2 127.0.0.1 >nul
goto wait
:copy
robocopy "{src}" "{dst}" /E /R:10 /W:1 /NFL /NDL /NJH /NJS /NP >> "{LOG}" 2>&1
echo robocopy exit %errorlevel% >> "{LOG}"
start "" "{exe}"
rmdir /s /q "{tmp}"
del "%~f0"
""")
    return bat


# ---------------------------------------------------------------- macOS
def extract_dmg(dmg, dest):
    """mount the .dmg, copy the app out of it, unmount. Returns the copied .app path."""
    mnt = os.path.join(os.path.dirname(dmg), "mnt")
    os.makedirs(mnt, exist_ok=True)
    subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-noautoopen", "-mountpoint", mnt, dmg],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    try:
        apps = [n for n in os.listdir(mnt) if n.endswith(".app")]
        if not apps:
            raise RuntimeError("the update has no " + APP_NAME)
        os.makedirs(dest, exist_ok=True)
        out = os.path.join(dest, apps[0])
        subprocess.run(["ditto", os.path.join(mnt, apps[0]), out], check=True, timeout=300)
    finally:
        subprocess.run(["hdiutil", "detach", mnt, "-force"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=60)
    return out


def write_mac_swap_script(tmp, src, dst, pid, relaunch=True):
    """shell script: wait for the game to quit, swap the .app, start it again"""
    sh = os.path.join(os.path.dirname(tmp), f"DesktopAquariumSwap_{pid}.sh")
    q = lambda s: "'" + s.replace("'", "'\''") + "'"
    with open(sh, "w", encoding="utf-8") as fh:
        fh.write(f"""#!/bin/sh
echo "[$(date)] updating {dst}" >> {q(LOG)}
n=0
while kill -0 {pid} 2>/dev/null && [ $n -lt 60 ]; do sleep 1; n=$((n+1)); done
rm -rf {q(dst + ".old")}
mv {q(dst)} {q(dst + ".old")} && ditto {q(src)} {q(dst)} >> {q(LOG)} 2>&1 && rm -rf {q(dst + ".old")} \
  || {{ echo "swap failed, putting the old app back" >> {q(LOG)}; rm -rf {q(dst)}; mv {q(dst + ".old")} {q(dst)}; }}
xattr -dr com.apple.quarantine {q(dst)} 2>/dev/null
{"open " + q(dst) if relaunch else "true"}
rm -rf {q(tmp)}
rm -f "$0"
""")
    os.chmod(sh, 0o755)
    return sh
