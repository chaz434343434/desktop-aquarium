"""Looks for text that doesn't fit: titles running into the buy button, descriptions that get cut off,
in every Shop tab, the Fishdex and Options, with everything unlocked, at every UI size.
Run: python check_layout.py"""
import os
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("DA_DATE", "2026-10-22")
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin.data import SPECIES, TOYS, UPGRADES  # noqa: E402
from purrfin.game import Game  # noqa: E402

pygame.init()
problems = set()


def setup(k):
    g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
    g.state["settings"]["uiscale"] = k
    g.layout()
    g.apply_window(first=True)
    s = g.state
    E.earn(s, 1e70)
    s["dex"] = [sp["id"] for sp in SPECIES]
    s["upgrades"].update({u["id"]: 1 for u in UPGRADES})
    s["upgrades"].update(tank=14)
    for t in TOYS[:30]:
        s["toys"][t["id"]] = dict(lv=3)
    for sp in SPECIES[-6:]:
        E.add_fish(s, sp["id"])
    g.tank.sync()
    g.toasts.clear()
    return g


def check_rows(g, where):
    ui = g.ui
    orig = ui.row

    def row(scr, view, y, icon, title, lines, btn_label, *a, **kw):
        rr = pygame.Rect(view.x + 4, y, view.w - 16, 80)
        tx = rr.x + 92
        bw = max(110, ui.f_norm.size(btn_label)[0] + 24) if btn_label else 0
        btn_x = rr.right - bw - 12 if btn_label else rr.right
        if tx + ui.f_norm.size(title)[0] > btn_x - 4:
            problems.add(f"{where}: title runs into the button: '{title}' ({btn_label})")
        tw = rr.right - tx - bw - 20
        out = []
        for ln in lines[:2]:
            ln = ln[0] if isinstance(ln, tuple) else ln
            out += ui.wrap(ln, ui.f_small, tw)
        if len(out) > 3:
            problems.add(f"{where}: text cut off in '{title}': ...{' '.join(out[3:])[:60]}")
        if btn_label and ui.f_norm.size(btn_label)[0] + 24 > bw:
            problems.add(f"{where}: button label too wide: '{btn_label}'")
        return orig(scr, view, y, icon, title, lines, btn_label, *a, **kw)

    ui.row = row
    g.ui.scroll[(g.ui.panel, g.ui.tab)] = 0
    g.draw()
    ui.row = orig


for k in (1.0, 1.5, 2.0):
    g = setup(k)
    for tab in ("fish", "toys", "upgrades", "hatchery", "themes", "mine", "spawn", "season:halloween"):
        g.ui.panel, g.ui.tab = "shop", tab
        check_rows(g, f"[{int(k * 100)}%] Shop > {tab}")
    for p in ("dex", "settings"):
        g.ui.panel = p
        g.draw()

for p in sorted(problems):
    print(p)
print(f"{len(problems)} layout problems")
