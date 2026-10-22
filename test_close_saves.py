"""Real-window test (Windows): the game saves however it's closed.
Starts the game on the top monitor with an old save, closes it a different way each time,
and checks the save file was rewritten by that close (well before the 30-second autosave).
Run: python test_close_saves.py   (or set DA_EXE=path\to\DesktopAquarium.exe to test the built game)"""
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes as wt

ROOT = os.path.dirname(os.path.abspath(__file__))
u = ctypes.windll.user32
k32 = ctypes.windll.kernel32
WM_CLOSE, WM_QUERYENDSESSION, WM_POWERBROADCAST, PBT_APMSUSPEND = 0x10, 0x11, 0x218, 4
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name, flush=True)
    ok &= bool(cond)


def window_of(pid):
    found = []
    proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, lp):
        p = wt.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        buf = ctypes.create_unicode_buffer(64)
        u.GetWindowTextW(hwnd, buf, 64)
        if p.value == pid and buf.value == "Desktop Aquarium":
            found.append(hwnd)
        return True

    u.EnumWindows(proc(cb), 0)
    return found[0] if found else None


def start(env_extra=None):
    d = tempfile.mkdtemp(prefix="da_close_")
    path = os.path.join(d, "save.json")
    with open(path, "w") as fh:
        json.dump({"settings": {"monitor": 2, "sound": False}, "last_time": time.time() - 5, "bubbles": 123.0,
                   "fish": [{"uid": 1, "sp": "sunflower", "name": "Sunny", "lv": 1, "xp": 0, "full": 80, "happy": 70}]},
                  fh)
    env = dict(os.environ, DA_UPDATE_API="http://127.0.0.1:9/none", **(env_extra or {}))
    cmd = [os.environ["DA_EXE"]] if os.environ.get("DA_EXE") else [sys.executable, "-m", "purrfin.main"]
    p = subprocess.Popen(cmd + ["--save", path], cwd=ROOT, env=env,
                         creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    hwnd = None
    for _ in range(100):
        time.sleep(0.1)
        hwnd = window_of(p.pid)
        if hwnd:
            break
    time.sleep(2.5)                       # let it run a little
    t0 = time.time()
    return p, hwnd, path, t0


def saved_after(path, t0):
    try:
        with open(path) as fh:
            return json.load(fh).get("last_time", 0) >= t0
    except (OSError, ValueError):
        return False


def kill(p):
    if p.poll() is None:
        p.kill()
        p.wait()


# 1. Alt+F4 / taskbar "Close window" / Task Manager "End task" all send WM_CLOSE
p, hwnd, path, t0 = start()
check("game window found", hwnd)
u.PostMessageW(hwnd, WM_CLOSE, 0, 0)
p.wait(timeout=15)
check("Alt+F4 / Task Manager 'End task': saved", saved_after(path, t0))

# 2. Windows shutting down: it asks every window first, then ends the programs
p, hwnd, path, t0 = start()
u.SendMessageW(hwnd, WM_QUERYENDSESSION, 0, 0)
time.sleep(0.6)
saved = saved_after(path, t0)
kill(p)                                   # Windows ending the program
check("Windows shutting down / restarting: saved before being ended", saved)

# 3. going to sleep (laptop lid closed)
p, hwnd, path, t0 = start()
u.PostMessageW(hwnd, WM_POWERBROADCAST, PBT_APMSUSPEND, 0)
time.sleep(0.6)
saved = saved_after(path, t0)
kill(p)
check("computer going to sleep: saved", saved)

# 4. Ctrl+C / Ctrl+Break (console, or being told to stop)
import signal  # noqa: E402
if not os.environ.get("DA_EXE"):          # the built game has no console to press Ctrl+Break in
    p, hwnd, path, t0 = start()
    os.kill(p.pid, signal.CTRL_BREAK_EVENT)
    try:
        p.wait(timeout=15)
    except subprocess.TimeoutExpired:
        kill(p)
    check("Ctrl+Break / stop signal: saved", saved_after(path, t0))

# 5. a crash
p, hwnd, path, t0 = start({"DA_CRASH_AFTER": "4"})
p.wait(timeout=20)
check("the game crashing: still saved", saved_after(path, t0))
check("and a crash.log was written", os.path.exists(os.path.join(os.path.dirname(path), "crash.log")))

print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
