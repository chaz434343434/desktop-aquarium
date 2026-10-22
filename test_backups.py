"""Headless checks: autosave every 30s, a backup every 5 minutes (3 kept), and a damaged save
falls back to the newest good backup. Run: python test_backups.py"""
import json
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin import game as G  # noqa: E402

pygame.init()
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


d = tempfile.mkdtemp()
path = os.path.join(d, "save.json")
g = G.Game(save_path=path, fresh=True)
g.apply_window(first=True)
check("autosave every 30 seconds", G.AUTOSAVE_EVERY == 30)
check("backup every 5 minutes", G.BACKUP_EVERY == 300)
g.state["bubbles"] = 111.0
g.update(31)                                   # 30 seconds pass -> autosave
check("autosaved after 30 seconds", json.load(open(path))["bubbles"] >= 111)
check("first save also makes a backup", os.path.exists(g.backup_path(1)))
for i, amount in enumerate((222.0, 333.0, 444.0)):
    g.state["bubbles"] = amount
    g.last_backup -= 301                       # pretend 5 minutes passed
    g.save()
b = [json.load(open(g.backup_path(i)))["bubbles"] for i in (1, 2, 3)]
check(f"3 backups kept, newest first ({b})", b[0] >= 444 and b[1] >= 333 and b[2] >= 222)
check("no 4th backup", not os.path.exists(g.backup_path(4)))
g.state["bubbles"] = 555.0
g.save()
check("saving between backups doesn't touch them", json.load(open(g.backup_path(1)))["bubbles"] < 555)
check("no half-written temp file left over", not os.path.exists(path + ".tmp"))

# damaged save -> newest backup
with open(path, "w") as fh:
    fh.write('{"fish": [{"uid": 1, "sp": "sunfl')       # cut off halfway
g2 = G.Game(save_path=path)
check("a damaged save loads the newest backup instead of starting over", g2.state["bubbles"] >= 444)
check("and says so", any("backup" in t[0] for t in g2.toasts))
os.remove(g.backup_path(1))
with open(path, "w") as fh:
    fh.write("")
g3 = G.Game(save_path=path)
check("if the newest backup is gone too, the next one is used", g3.state["bubbles"] >= 333)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
