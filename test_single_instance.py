"""Real-window test (Windows): only one copy of the game runs per save file.
Opens the game, hides it with the _ button, then launches it 5 more times at once:
the extra copies must close by themselves and the first one must come back on screen.
Run: python test_single_instance.py   (DA_EXE=...\DesktopAquarium.exe to test the built game)"""
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name, flush=True)
    ok &= bool(cond)


d = tempfile.mkdtemp(prefix="da_single_")
save = os.path.join(d, "save.json")
with open(save, "w") as fh:
    json.dump({"settings": {"monitor": 2, "sound": False}, "last_time": time.time(),
               "fish": [{"uid": 1, "sp": "sunflower", "name": "Sunny", "lv": 1, "xp": 0, "full": 80, "happy": 70}]}, fh)
env = dict(os.environ, DA_UPDATE_API="http://127.0.0.1:9/none", DA_STATUS_FILE=os.path.join(d, "status.txt"))
cmd = [os.environ["DA_EXE"]] if os.environ.get("DA_EXE") else [sys.executable, "-m", "purrfin.main"]
first = subprocess.Popen(cmd + ["--save", save], cwd=ROOT, env=env)
time.sleep(5)
check("first copy is running", first.poll() is None)
# hide the tank (the _ button) via the test hook, then spam launches
open(os.path.join(d, "hide.txt"), "w").close()
time.sleep(1.5)
t0 = time.time()
extra = [subprocess.Popen(cmd + ["--save", save], cwd=ROOT, env=env) for _ in range(5)]
codes = []
for p in extra:
    try:
        codes.append(p.wait(timeout=20))
    except subprocess.TimeoutExpired:
        p.kill()
        codes.append("still running")
check(f"all 5 extra copies closed by themselves ({codes})", all(c == 0 for c in codes))
check("they closed quickly", time.time() - t0 < 20)
check("the first copy is still running", first.poll() is None)
time.sleep(1.5)
status = open(os.path.join(d, "status.txt")).read() if os.path.exists(os.path.join(d, "status.txt")) else ""
check(f"the first copy came back on screen ({status.strip()})", "minimized=False" in status and "woken" in status)
# a different save file is a different game: that one may run alongside
other = os.path.join(d, "other.json")
second = subprocess.Popen(cmd + ["--save", other, "--fresh", "--monitor", "2"], cwd=ROOT, env=env)
time.sleep(5)
check("a copy on a different save file is allowed", second.poll() is None)
second.kill()
first.kill()
first.wait()
second.wait()
after = subprocess.Popen(cmd + ["--save", save, "--seconds", "3"], cwd=ROOT, env=env)
check("once the game is closed it can be opened again", after.wait(timeout=30) == 0)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
