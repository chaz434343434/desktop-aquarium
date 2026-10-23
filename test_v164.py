"""Headless checks for 1.6.4 bug fixes: typing goes where you expect (search box vs fish name).
Run: python test_v164.py"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame  # noqa: E402

from purrfin.game import Game  # noqa: E402

pygame.init()
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
g.ui.panel, g.ui.tab = "shop", "toys"
g.draw()
g.start_search()
g.text_input("ball")
check("typing in the search box", g.ui.search == "ball")
f = g.state["fish"][0]
g.start_rename(f)
g.text_input("X")
check("right-clicking a fish to rename it: typing goes to the name", g.rename_text.endswith("X"))
check("and not into the search box", g.ui.search == "ball" and not g.searching)
g.finish_rename(False)

g.ui.panel, g.ui.tab = "shop", "toys"
g.draw()
g.start_search()
g.ui.tab = "hatchery"
g.draw()
check("switching to a tab without a search box stops the typing", not g.searching)
g.text_input("zzz")
check("so keys don't vanish into an invisible search box", "zzz" not in g.ui.search)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
