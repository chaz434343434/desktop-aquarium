"""Mac smoke test of the BUILT app with a real window (GitHub Mac runner).
1. Plays the game 3 times with the UI script (shop, toys, upgrades, options... open one by one)
   and grabs the whole desktop with `screencapture`, so we can see where the window sits.
   Every run must exit cleanly and write its save: that's the pass/fail.
2. One more run saves the game's own screenshots (bmp, in /tmp) for a closer look. Not pass/fail:
   the test-only --shots writer has crashed on Apple Silicon runners when given a brand-new folder
   inside the build directory, so it's kept apart from the real checks.
Usage: python build_assets/mac_smoke.py out/shots"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

shots = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "out/shots")
os.makedirs(shots, exist_ok=True)
exe = os.path.join("dist", "Desktop Aquarium.app", "Contents", "MacOS", "Desktop Aquarium")
env = dict(os.environ, DA_UPDATE_API="http://127.0.0.1:9/none")     # don't ask the real GitHub
env.pop("SDL_VIDEODRIVER", None)
ok = True
for run in range(3):
    save = os.path.join(tempfile.mkdtemp(), "save.json")
    p = subprocess.Popen([exe, "--fresh", "--demo", "--script", "--save", save, "--seconds", "16"], env=env)
    t0 = time.time()
    if run == 0:
        for at in (3.0, 4.7, 9.7, 13.0):          # tank / shop open / options open / closed again
            time.sleep(max(0, at - (time.time() - t0)))
            subprocess.run(["screencapture", "-x", os.path.join(shots, f"desktop_{at:04.1f}s.png")])
    code = p.wait(timeout=90)
    good = code == 0 and os.path.exists(save)
    print(f"run {run + 1}: exit code {code} | save written {os.path.exists(save)}", flush=True)
    ok &= good

# the game's own screenshots, for a closer look (not pass/fail)
tmp = tempfile.mkdtemp(prefix="da_shots_")
code = subprocess.call([exe, "--fresh", "--demo", "--save", os.path.join(tmp, "s.json"), "--seconds", "13",
                        "--shots", os.path.join(tmp, "game")], env=dict(env, DA_SHOT_EXT="bmp"))
if os.path.isdir(os.path.join(tmp, "game")):
    shutil.copytree(os.path.join(tmp, "game"), os.path.join(shots, "game"), dirs_exist_ok=True)
print("in-game screenshots run: exit", code, sorted(os.listdir(os.path.join(shots, "game")))
      if os.path.isdir(os.path.join(shots, "game")) else [])

if not ok:
    import glob
    import json
    reps = sorted(glob.glob(os.path.expanduser("~/Library/Logs/DiagnosticReports/*.ips")), key=os.path.getmtime)
    for rep in reps[-1:]:
        print("---- crash report", rep)
        txt = open(rep, errors="replace").read()
        try:
            d = json.loads(txt.split(chr(10), 1)[1])
            print("exception:", d.get("exception"))
            th = next(t for t in d["threads"] if t.get("triggered"))
            imgs = d.get("usedImages", [])
            for fr in th["frames"][:25]:
                im = imgs[fr["imageIndex"]].get("name", "?") if fr.get("imageIndex") is not None else "?"
                print("  ", im, fr.get("symbol", hex(fr.get("imageOffset", 0))))
        except Exception as e:
            print("(raw)", txt[:3000], e)
print("SMOKE PASS" if ok else "SMOKE FAIL")
sys.exit(0 if ok else 1)
