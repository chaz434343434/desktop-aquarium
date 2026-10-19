"""Mac smoke test of the BUILT app with a real window (GitHub Mac runner).
Runs the game through its screenshot script and grabs the whole desktop with `screencapture`
a few times, so we can see where the window sits and that panels open.
Usage: python build_assets/mac_smoke.py out/shots"""
import os
import subprocess
import sys
import tempfile
import time

shots = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "out/shots")
os.makedirs(shots, exist_ok=True)
exe = os.path.join("dist", "Desktop Aquarium.app", "Contents", "MacOS", "Desktop Aquarium")
save = os.path.join(tempfile.mkdtemp(), "save.json")
env = dict(os.environ, DA_UPDATE_API="http://127.0.0.1:9/none")     # don't ask the real GitHub
env.pop("SDL_VIDEODRIVER", None)
p = subprocess.Popen([exe, "--fresh", "--demo", "--save", save, "--seconds", "16",
                      "--shots", os.path.join(shots, "game")], env=env)
t0 = time.time()
for at in (3.0, 4.7, 9.7, 13.0):          # tank / shop open / options open / closed again
    time.sleep(max(0, at - (time.time() - t0)))
    subprocess.run(["screencapture", "-x", os.path.join(shots, f"desktop_{at:04.1f}s.png")])
code = p.wait(timeout=60)
ok = code == 0 and os.path.exists(save)
got = sorted(os.listdir(os.path.join(shots, "game"))) if os.path.isdir(os.path.join(shots, "game")) else []
print("exit code", code, "| save written", os.path.exists(save), "| game shots", got)
ok &= len(got) >= 8
print("SMOKE PASS" if ok else "SMOKE FAIL")
sys.exit(0 if ok else 1)
