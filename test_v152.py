"""Headless checks for 1.5.2: Bought / Not bought sections, Shop search box, draggable scrollbar.
Run: python test_v152.py [screenshot_dir]"""
import os
import sys
import tempfile

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["DA_DATE"] = "2026-10-21"
import pygame  # noqa: E402

from purrfin import economy as E  # noqa: E402
from purrfin.game import Game  # noqa: E402

pygame.init()
shots = sys.argv[1] if len(sys.argv) > 1 else None
ok = True


def check(name, cond):
    global ok
    print(("PASS " if cond else "FAIL ") + name)
    ok &= bool(cond)


def listed(g, tab):
    """(section headers, row titles) a Shop tab draws, in order"""
    out = []
    orig_row, orig_sec = g.ui.row, g.ui.section
    g.ui.row = lambda scr, view, y, icon, title, *a, **k: out.append(("row", title)) or orig_row(scr, view, y, icon, title, *a, **k)
    g.ui.section = lambda scr, view, y, title, n: out.append(("sec", title)) or orig_sec(scr, view, y, title, n)
    g.ui.panel, g.ui.tab = "shop", tab
    g.draw()
    g.ui.row, g.ui.section = orig_row, orig_sec
    return out


def shot(g, name):
    if shots:
        os.makedirs(shots, exist_ok=True)
        g.draw()
        pygame.image.save(g.screen.subsurface(g.ui.panel_rect), os.path.join(shots, name + ".png"))


def key(g, k):
    g.key_down(pygame.event.Event(pygame.KEYDOWN, key=k))


g = Game(save_path=os.path.join(tempfile.mkdtemp(), "s.json"), fresh=True)
g.apply_window(first=True)
s = g.state
g.toasts.clear()
E.earn(s, 1e9)
for tid in ("ball", "cave", "airstone"):
    g.buy_toy(tid)
for uid in ("filter", "hands"):
    g.buy_upgrade(uid)

# ---- sections
out = listed(g, "toys")
secs = [t for k, t in out if k == "sec"]
check("Toys tab: 'Your toys' first, then 'Not bought yet'", secs == ["Your toys", "Not bought yet"])
first_new = out.index(("sec", "Not bought yet"))
owned_rows = [t for k, t in out[:first_new] if k == "row"]
check("all bought toys are in the first group", set(owned_rows) == {"Ping-Pong Ball", "Driftwood Cave", "Air Stone"})
shot(g, "toys_sections")
out = listed(g, "upgrades")
secs = [t for k, t in out if k == "sec"]
check("Upgrades tab: 'Bought' then 'Not bought yet'", secs == ["Bought", "Not bought yet"])
first_new = out.index(("sec", "Not bought yet"))
bought = [t for k, t in out[:first_new] if k == "row"]
check("bought upgrades are together", len(bought) == 2 and all(t.startswith(("Canister", "Gentle")) for t in bought))
shot(g, "upgrades_sections")

# ---- search
r = g.ui.search_rect
check("there's a search box", r is not None)
g.mouse_down(tuple(int(v * g.ui.k) for v in r.center), 1)
check("clicking it starts typing", g.searching)
g.text_input("fil")
out = listed(g, "upgrades")
rows = [t for k, t in out if k == "row"]
check("typing 'fil' shows only the filter upgrades", rows and all("Filter" in t for t in rows))
key(g, pygame.K_BACKSPACE)
key(g, pygame.K_BACKSPACE)
key(g, pygame.K_BACKSPACE)
g.text_input("zzzz")
out = listed(g, "upgrades")
check("no matches -> no rows", not [t for k, t in out if k == "row"])
shot(g, "search_none")
g.ui.search = ""
g.text_input("bronze")
out = listed(g, "fish")
check("search works on the Catfish tab", [t for k, t in out if k == "row"] == ["Bronze Corydoras  NEW!"])
g.ui.search = ""
g.text_input("panda")
out = listed(g, "fish")
check("but doesn't give away catfish you haven't discovered yet", not [t for k, t in out if k == "row"])
g.ui.search = ""
g.text_input("bronze")
key(g, pygame.K_RETURN)
check("Enter stops typing but keeps the search", not g.searching and g.ui.search == "bronze")
shot(g, "search_fish")
g.ui.clear_search()
check("x clears it", g.ui.search == "")
g.start_search()
g.ui.panel = None
g.update(0.05)
check("closing the Shop stops typing", not g.searching)

# ---- draggable scrollbar
g.ui.panel, g.ui.tab = "shop", "fish"
s["dex"] = [sp["id"] for sp in E.SPECIES[:30]]
g.draw()
check("long list has a scrollbar", g.ui.sb is not None)
track, sb_y, sb_h, mx, k = g.ui.sb
grab = (track.centerx, sb_y + sb_h // 2)
scr = lambda p: (int(p[0] * g.ui.k), int(p[1] * g.ui.k))     # noqa: E731
g.mouse_down(scr(grab), 1)
check("grabbing the thumb starts a drag", g.ui.sb_drag is not None)
g.mouse_motion(scr((grab[0], track.bottom)), (0, 200), (1, 0, 0))
check("dragging it to the bottom scrolls to the end", g.ui.scroll[k] == mx)
g.mouse_motion(scr((grab[0], track.y)), (0, -200), (1, 0, 0))
check("and back to the top", g.ui.scroll[k] == 0)
g.mouse_up(scr((grab[0], track.y)), 1)
check("letting go ends the drag", g.ui.sb_drag is None)
g.draw()
track, sb_y, sb_h, mx, k = g.ui.sb
g.mouse_down(scr((track.centerx, track.bottom - 2)), 1)
g.mouse_up(scr((track.centerx, track.bottom - 2)), 1)
check("clicking the track jumps there", g.ui.scroll[k] > mx * 0.8)
g.draw()
shot(g, "scrollbar")
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
