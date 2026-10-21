"""Hi-res UI: HUD strip, panels (shop / fishdex / options), tooltips, toasts."""
import pygame

from . import economy as E
from . import sprites
from .pixfont import PixelFont
from .version import VERSION
from .data import SEASONAL_SPECIES, SEASONS, RUB_COOLDOWN
from .data import (SPECIES, SPECIES_BY_ID, FOODS, TOYS, UPGRADES, TOY_MAX_LEVEL, TANK_NAMES, CLUTCHES, THEMES,
                   CLUTCHES_BY_ID,
                   TANK_CAPACITY, SPAWN_MIN, PEARL_BONUS, PEARL_TREE, PEARL_TREE_BY_ID)

BG = (30, 36, 56)
BG2 = (44, 54, 80)
BG3 = (58, 72, 106)
BORDER = (12, 14, 24)
TEXT = (240, 240, 232)
DIM = (150, 160, 186)
ACC = (255, 204, 68)
GOOD = (72, 168, 70)          # the chunky green button
GOLD = (210, 150, 36)
TAB = (40, 104, 72)
NAV = (54, 70, 104)
BAD = (186, 68, 60)
PINK = (255, 150, 190)
SCALE_COL = (255, 214, 90)
SHADOW = (10, 12, 22)

STRIP_H = 30
KEY = (255, 0, 255)           # transparent colour (same as the game window)
UI_SCALES = (1.0, 1.5, 2.0)   # keep to steps of 0.5 so the 2px pixel font stays crisp
ROW_H = 84
PX = 2                        # size of one UI "pixel"


def s_pending(g):
    s = g.state
    return bool(s.get("pending")) and len(s["fish"]) >= E.capacity(s)


def _lighten(c, k=0.15):
    return tuple(min(255, int(v + (255 - v) * k)) for v in c)


def _darken(c, k=0.7):
    return tuple(int(v * k) for v in c)


class UI:
    def __init__(self, game):
        self.g = game
        self.f_small = PixelFont(2)
        self.f_norm = PixelFont(2, SHADOW)
        self.f_big = PixelFont(3, SHADOW)
        self.f_huge = PixelFont(4, SHADOW)
        self.panel = None
        self.tab = "fish"
        self.scroll = {}
        self.hits = []
        self.tips = []
        self.mouse = None
        self.confirm = None
        self.dex_sel = None
        self.grip_rect = None
        self.drag = None              # (dx, dy) grab offset while moving a panel
        self.update_prompt = False
        self.k = 1.0
        self.W = self.H = 0
        self.tank = pygame.Rect(0, 0, 0, 0)
        self.surf = None
        self.panel_rect = None
        self.content_h = 0
        self.view_h = 0

    # ------------------------------------------------------------ helpers
    def box(self, scr, rect, col=BG, radius=7, border=BORDER, bevel=True):
        """chunky pixel box: notched corners, dark outline, light top-left / dark bottom-right bevel"""
        r = pygame.Rect(rect)
        P = PX
        scr.fill(border, (r.x + P, r.y, r.w - 2 * P, r.h))
        scr.fill(border, (r.x, r.y + P, r.w, r.h - 2 * P))
        inner = r.inflate(-2 * P, -2 * P)
        scr.fill(col, inner)
        if bevel and inner.w > 2 * P and inner.h > 2 * P:
            hi, lo = _lighten(col, 0.22), _darken(col, 0.68)
            scr.fill(hi, (inner.x, inner.y, inner.w - P, P))
            scr.fill(hi, (inner.x, inner.y, P, inner.h - P))
            scr.fill(lo, (inner.x + P, inner.bottom - P, inner.w - P, P))
            scr.fill(lo, (inner.right - P, inner.y + P, P, inner.h - P))

    def text(self, scr, s, font, col, pos, anchor="topleft"):
        img = font.render(str(s), True, col)
        r = img.get_rect(**{anchor: pos})
        scr.blit(img, r)
        return r

    def hovered(self, rect):
        return self.mouse is not None and rect.collidepoint(self.mouse)

    def button(self, scr, rect, label, cb, enabled=True, col=GOOD, font=None, tip=None):
        rect = pygame.Rect(rect)
        c = col if enabled else (66, 70, 84)
        if enabled and self.hovered(rect):
            c = _lighten(c, 0.18)
        self.box(scr, rect, c, 6)
        self.text(scr, label, font or self.f_norm, TEXT if enabled else DIM,
                  (rect.centerx, rect.centery + 1), "center")
        if enabled:
            self.hits.append((rect, cb))
        if tip:
            self.tips.append((rect, tip))
        return rect

    def bar(self, scr, rect, k, col):
        r = pygame.Rect(rect)
        scr.fill(BORDER, r)
        w = int((r.w - 4) // PX * max(0.0, min(1.0, k))) * PX
        if w > 0:
            scr.fill(col, (r.x + 2, r.y + 2, w, r.h - 4))
            scr.fill(_lighten(col, 0.35), (r.x + 2, r.y + 2, w, PX))

    def wrap(self, s, font, width):
        words, lines, cur = s.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if font.size(t)[0] > width and cur:
                lines.append(cur)
                cur = w
            else:
                cur = t
        if cur:
            lines.append(cur)
        return lines

    # ------------------------------------------------------------ input
    # ------------------------------------------------------------ scale
    def ui_pos(self, pos):
        return (int(pos[0] / self.k), int(pos[1] / self.k))

    def set_mouse(self, pos):
        self.mouse = None if pos is None else self.ui_pos(pos)

    def over_panel(self, pos):
        return bool(self.panel_rect and self.panel_rect.collidepoint(self.ui_pos(pos)))

    def to_ui(self, x, y):
        sx, sy = self.g.to_screen(x, y)
        return sx / self.k, sy / self.k

    def begin(self):
        g = self.g
        k = float(g.state["settings"].get("uiscale", 1.0))
        self.k = k if k in UI_SCALES else 1.0
        self.W, self.H = int(g.win_w / self.k), int(g.win_h / self.k)
        r = g.tank_rect
        self.tank = pygame.Rect(int(r.x / self.k), int(r.y / self.k), int(r.w / self.k), int(r.h / self.k))

    def click(self, pos, button):
        if button == 4 or button == 5:
            return False
        pos = self.ui_pos(pos)
        for rect, cb in reversed(self.hits):
            if rect.collidepoint(pos):
                cb()
                return True
        if self.grip_rect and self.grip_rect.collidepoint(pos) and self.panel_rect:
            self.drag = (pos[0] - self.panel_rect.x, pos[1] - self.panel_rect.y)
            return True
        if self.panel_rect and self.panel_rect.collidepoint(pos):
            return True
        return False

    def drag_to(self, pos):
        pos = self.ui_pos(pos)
        self.g.state["settings"]["panel_pos"] = [pos[0] - self.drag[0], pos[1] - self.drag[1]]

    def reset_panel_pos(self):
        self.g.state["settings"]["panel_pos"] = None

    def wheel(self, pos, dy):
        pos = self.ui_pos(pos)
        if self.panel_rect and self.panel_rect.collidepoint(pos):
            key = (self.panel, self.tab)
            mx = max(0, self.content_h - self.view_h)
            self.scroll[key] = max(0, min(mx, self.scroll.get(key, 0) - dy * 40))
            return True
        return False

    def open(self, name):
        self.panel = None if self.panel == name else name
        self.confirm = None

    def open_tab(self, t):
        """HUD shortcut straight to a shop tab; clicking the button that's already lit closes the panel.
        t == "fish" is the Shop button: it reopens whichever normal shop tab you last used."""
        own = ("mine", "hatchery")
        showing = self.panel == "shop" and (self.tab == t if t in own else self.tab not in own)
        if showing:
            self.panel = None
        else:
            self.panel = "shop"
            if t in own or self.tab in own:
                self.tab = t
        self.confirm = None

    def set_tab(self, t):
        self.tab = t
        self.confirm = None

    # ------------------------------------------------------------ main draw
    def draw(self, screen):
        self.begin()
        if self.k == 1.0:
            return self._draw(screen)
        if self.surf is None or self.surf.get_size() != (self.W, self.H):
            self.surf = pygame.Surface((self.W, self.H))
        self.surf.fill(KEY)
        self._draw(self.surf)
        big = pygame.transform.scale(self.surf, screen.get_size())
        big.set_colorkey(KEY)
        screen.blit(big, (0, 0))

    def _draw(self, scr):
        self.hits = []
        self.tips = []
        g = self.g
        if g.minimized:
            self.panel_rect = None
            r = self.tank
            lab = "Aquarium " + E.fmt(g.state["bubbles"])
            w = self.f_norm.size(lab)[0] + 46
            b = pygame.Rect(r.right - w - 6, self.H - 40, w, 34)
            self.button(scr, b, "", self.restore, col=GOOD)
            scr.blit(sprites.scale_icon(3), (b.x + 10, b.y + 6))
            self.text(scr, lab, self.f_norm, TEXT, (b.x + 36, b.centery + 1), "midleft")
            return
        self.draw_strip(scr)
        if s_pending(g):              # a hatchling has no room: this choice can't be skipped
            self.panel = "baby"
        elif self.panel == "baby":
            self.panel = None
        self.panel_rect = None
        self.grip_rect = None
        if self.panel:
            self.draw_panel(scr)
        self.draw_toasts(scr)
        if g.renaming:
            self.draw_rename(scr)
        elif self.update_prompt:
            self.draw_update(scr)
        elif g.welcome:
            self.draw_welcome(scr)
        self.draw_floaters(scr)
        self.draw_fish_tip(scr)
        self.draw_tips(scr)

    def restore(self):
        self.g.minimized = False

    def minimize(self):
        self.g.minimized = True
        self.panel = None

    # ------------------------------------------------------------ strip (two rows)
    def hud_top(self):
        return self.tank.y - 2 * STRIP_H - 12

    def draw_strip(self, scr):
        g, s = self.g, self.g.state
        r = self.tank
        y1 = r.y - STRIP_H - 4                 # row 1: scales + foods
        y2 = y1 - STRIP_H - 4                  # row 2: buffs + menu buttons
        # ---- row 1 widths first so the row can slide left if the tank is narrow
        amt = self.f_big.render(E.fmt(s["bubbles"]), True, SCALE_COL)
        rate = self.f_small.render(f"+{E.fmt(g.real_rate())}/s", True, (170, 220, 250))
        # fixed widths (widest possible number) so the food buttons never shift
        amt_w = max(self.f_big.size("888" + u)[0] for u in E.UNITS)
        rate_w = max(self.f_small.size("+888" + u + "/s")[0] for u in E.UNITS)
        pill_w = 34 + amt_w + 8 + rate_w + 12
        foods = []
        nxt = None
        for fd in FOODS:
            if s["earned_total"] >= fd["unlock"]:
                foods.append(fd)
            elif nxt is None:
                nxt = fd
        row_w = pill_w + 8 + (len(foods) + (1 if nxt else 0)) * (STRIP_H + 4)
        x = min(r.x + 4, r.right - 4 - row_w)
        x = max(4, x)
        pill = pygame.Rect(x, y1, pill_w, STRIP_H)
        self.box(scr, pill, BG)
        scr.blit(sprites.scale_icon(3), (x + 8, y1 + 4))
        scr.blit(amt, (x + 34, y1 + (STRIP_H - amt.get_height()) // 2 + 1))
        scr.blit(rate, (x + 34 + amt_w + 8, y1 + (STRIP_H - rate.get_height()) // 2 + 1))
        tip = [f"Scales: {E.fmt(s['bubbles'])}", f"Earning: {E.fmt(g.real_rate())} scales/s", f"(fish {E.fmt(E.income(s))}/s + toys, bubbles, pets)",
               f"All bonuses: x{E.global_mult(s):.2f}", f"Lifetime: {E.fmt(s['earned_total'])}"]
        if s["pearls"]:
            tip.append(f"Pearls: {s['pearls']} to spend (Shop > Pearls)")
        self.tips.append((pill, tip))
        x = pill.right + 8
        for fd in foods:
            b = pygame.Rect(x, y1, STRIP_H, STRIP_H)
            c = E.food_cost(s, fd["id"])
            ok = g.can_afford(c)
            col = NAV if ok else (70, 50, 58)
            if self.hovered(b):
                col = _lighten(col, 0.18)
            self.box(scr, b, col)
            ic = sprites.food_icon(fd["color"], 2)
            scr.blit(ic, ic.get_rect(center=b.center))
            cd = g.food_cd.get(fd["id"], 0) - g.now
            if cd > 0:
                k = cd / fd["cooldown"]
                sh = pygame.Surface((b.w - 4, int((b.h - 4) * k)), pygame.SRCALPHA)
                sh.fill((0, 0, 0, 120))
                scr.blit(sh, (b.x + 2, b.y + 2))
            self.hits.append((b, lambda i=fd["id"]: g.use_food(i)))
            self.tips.append((b, [fd["name"], "Free!" if c == 0 else f"Cost: {E.fmt(c)} scales", fd["desc"],
                                  f"+{fd['full']} full  +{fd['happy']} happy  +{fd['xp']} xp"]))
            x += STRIP_H + 4
        if nxt:
            b = pygame.Rect(x, y1, STRIP_H, STRIP_H)
            self.box(scr, b, (50, 52, 64))
            self.text(scr, "?", self.f_norm, DIM, (b.centerx, b.centery + 1), "center")
            self.tips.append((b, ["New food", f"Unlocks at {E.fmt(nxt['unlock'])} lifetime scales"]))
        # ---- row 2: menu buttons on the right
        bx = r.right - 4
        specs = [("x", g.quit, 30, BAD, "Save & quit"), ("_", self.minimize, 30, NAV, "Hide tank"),
                 ("Options", lambda: self.open("settings"), None, NAV, None),
                 ("Chill", g.toggle_chill, None, (60, 120, 190) if s["chill"] else NAV,
                  ["Chill mode", "Hunger & happiness stop draining", "No pop-bubbles (no pressure)"]),
                 ("Fishdex", lambda: self.open("dex"), None, NAV, None),
                 ("Shop", lambda: self.open_tab("fish"), None, GOOD, None),
                 ("My Tank", lambda: self.open_tab("mine"), None, NAV, ["My Tank", "Your fish: levels, names, selling"])]
        if E.ulv(s, "hatchery"):
            specs.append(("Hatchery", lambda: self.open_tab("hatchery"), None, NAV, ["Hatchery", "Lay and hatch eggs"]))
        if g.updater.state in ("available", "downloading", "ready"):
            pulse = GOLD if int(g.now * 2) % 2 else _lighten(GOLD, 0.3)
            specs.append(("Update!", lambda: setattr(self, "update_prompt", True), None, pulse,
                          ["New version", f"{g.updater.latest['tag']} is ready to install"]))
        if E.ulv(s, "jar") or E.ulv(s, "hatchery"):
            ready = sum(1 for e in s["eggs"] if e["left"] <= 0)
            cap = E.jar_cap(s)
            jar_k = s["jar"] / cap if cap > 0 else 0
            hot = ready > 0 or jar_k >= 0.5
            tip = ["Collect"]
            if E.ulv(s, "jar"):
                tip.append(f"Scale Jar: {E.fmt(s['jar'])}  ({int(jar_k * 100)}% full)")
            if E.ulv(s, "hatchery"):
                tip.append(f"Eggs ready: {ready}   in nest: {len(s['eggs'])}/{E.egg_slots(s)}")
            pulse = GOLD if int(g.now * 2) % 2 else _lighten(GOLD, 0.25)
            specs.append(("Collect" + (" !" if hot else ""), g.collect_all, None, pulse if hot else NAV, tip))
        if E.ulv(s, "rub"):
            st, left = g.rub, g.rub_t
            pink = (196, 84, 140)
            if st == "ready":
                rub = ("Scratch!", _lighten(pink, 0.2) if int(g.now * 2) % 2 else pink, ["Fin Scratches", "Click, then hold the mouse",
                       f"on your fish and wiggle for {E.rub_secs(s)}s!"])
            elif st == "armed":
                rub = ("Scratch a fish!", _lighten(pink, 0.35), ["Hold the mouse on a fish and wiggle", "Click again to cancel"])
            elif st == "active":
                rub = (f"Scratch! {left:.1f}s", _lighten(pink, 0.45), ["Keep scratching!"])
            else:
                rub = (f"Scratch {int(left) + 1}s", (70, 50, 64), ["Fin Scratches", "Recharging"])
            specs.append((rub[0], g.rub_button, self.f_norm.size("Scratch a fish!")[0] + 20, rub[1], rub[2]))
        for lab, cb, w, col, tip in specs:
            w = w or self.f_norm.size(lab)[0] + 20
            bx -= w
            shop_tab = self.tab if self.panel == "shop" else None
            active = (lab == "Shop" and shop_tab not in (None, "mine", "hatchery")) \
                or (lab == "My Tank" and shop_tab == "mine") or (lab == "Hatchery" and shop_tab == "hatchery") \
                or (lab == "Fishdex" and self.panel == "dex")                 or (lab == "Options" and self.panel == "settings")
            self.button(scr, (bx, y2, w, STRIP_H), lab, cb, col=_lighten(col, 0.25) if active else col, tip=tip)
            bx -= 4
        # ---- buffs to the left of the buttons
        names = {"double": ("2x", ACC), "frenzy": ("Frenzy", (255, 160, 120)), "bliss": ("Bliss", (140, 220, 140))}
        for b, t in s["buffs"].items():
            lab, col = names.get(b, (b, TEXT))
            img = self.f_small.render(f"{lab} {E.fmt_time(t)}", True, col)
            w = img.get_width() + 16
            bx -= w
            rr = pygame.Rect(bx, y2 + 3, w, STRIP_H - 6)
            self.box(scr, rr, BG)
            scr.blit(img, img.get_rect(center=(rr.centerx, rr.centery + 1)))
            bx -= 4

    def draw_toasts(self, scr):
        g = self.g
        inside = g.compact and not g.compact_tall      # Mac's short window: no room above, so over the water
        y = self.tank.y + 8 if inside else self.hud_top() - 4
        for text, col, t in reversed(g.toasts):
            img = self.f_norm.render(text, True, col)
            w = img.get_width() + 20
            x = max(4, min(self.tank.x + 4, self.tank.right - 4 - w))
            h = img.get_height() + 10
            rr = pygame.Rect(x, y if inside else y - h, w, h)
            self.box(scr, rr, BG)
            scr.blit(img, (rr.x + 10, rr.y + 5))
            y = rr.bottom + 4 if inside else rr.y - 4

    def draw_floaters(self, scr):
        g = self.g
        top = self.tank.y + 14
        for x, y, text, col, life in g.tank.texts:
            sx, sy = self.to_ui(x, y)
            img = self.f_norm.render(text, True, col)
            rr = img.get_rect(center=(sx, max(top, sy)))
            rr.clamp_ip(self.tank)
            scr.blit(img, rr)

    def draw_fish_tip(self, scr):
        g = self.g
        if g.mouse_low is None or (self.panel_rect and self.mouse and self.panel_rect.collidepoint(self.mouse)):
            return
        a = g.tank.fish_at(*g.mouse_low)
        if not a:
            return
        f, sp = a.f, a.sp
        w, h = 300, 150
        sx, sy = self.to_ui(a.x, a.y)
        rr = pygame.Rect(int(sx - w / 2), int(self.hud_top() - h - 4), w, h)
        rr.clamp_ip(scr.get_rect())
        pr = self.panel_rect
        if pr and rr.colliderect(pr):
            left = rr.copy()
            left.right = pr.x - 8
            right = rr.copy()
            right.x = pr.right + 8
            if left.x >= 0 and (abs(left.centerx - sx) <= abs(right.centerx - sx) or right.right > scr.get_width()):
                rr = left
            elif right.right <= scr.get_width():
                rr = right
            else:
                rr.bottom = pr.y - 6
            rr.clamp_ip(scr.get_rect())
        self.box(scr, rr, BG)
        self.text(scr, f["name"], self.f_norm, ACC, (rr.x + 12, rr.y + 8))
        self.text(scr, f"Lv {f['lv']}", self.f_norm, TEXT, (rr.right - 12, rr.y + 8), "topright")
        if f.get("shiny"):
            self.text(scr, "SHINY x2", self.f_small, (255, 150, 230), (rr.right - 12, rr.y + 30), "topright")
        self.text(scr, sp["name"], self.f_small, DIM, (rr.x + 12, rr.y + 30))
        rows = [("XP", f["xp"] / E.xp_needed(f["lv"]), (150, 130, 250)),
                ("Full", f["full"] / 100, (240, 170, 80)), ("Happy", f["happy"] / 100, PINK)]
        if f.get("grow"):
            rows = [("Grow", E.growth(f), (150, 230, 160))] + rows[1:]
        yy = rr.y + 52
        for lab, k, col in rows:
            self.text(scr, lab, self.f_small, DIM, (rr.x + 12, yy))
            self.bar(scr, (rr.x + 74, yy + 2, w - 88, 12), k, col)
            yy += 18
        self.text(scr, f"+{E.fmt(E.fish_rate(g.state, f) * E.global_mult(g.state))}/s  click to pet!",
                  self.f_small, (170, 220, 250), (rr.x + 12, yy + 2))
        if f.get("grow"):
            self.text(scr, f"Baby! Grows up in {E.fmt_time(f['grow'])}", self.f_small, (150, 230, 160),
                      (rr.x + 12, yy + 20))
        else:
            self.text(scr, "Right-click to rename", self.f_small, DIM, (rr.x + 12, yy + 20))

    def draw_tips(self, scr):
        if self.mouse is None:
            return
        for rect, lines in reversed(self.tips):
            if rect.collidepoint(self.mouse):
                if isinstance(lines, str):
                    lines = [lines]
                imgs = [(self.f_norm if i == 0 else self.f_small).render(l, True, ACC if i == 0 else TEXT)
                        for i, l in enumerate(lines)]
                w = max(i.get_width() for i in imgs) + 20
                h = sum(i.get_height() + 2 for i in imgs) + 14
                rr = pygame.Rect(self.mouse[0] - w // 2, rect.y - h - 6, w, h)
                if rr.y < 0:                       # no room above (Mac's short window): show it below
                    rr.y = rect.bottom + 6
                rr.clamp_ip(scr.get_rect())
                self.box(scr, rr, BG)
                y = rr.y + 8
                for i in imgs:
                    scr.blit(i, (rr.x + 10, y))
                    y += i.get_height() + 2
                return

    def draw_rename(self, scr):
        g = self.g
        f = g.renaming
        w = 480
        hint = self.wrap("Enter saves, Esc cancels", self.f_small, w - 30)
        h = 150 + 16 * (len(hint) - 1)
        r = self.tank
        rr = pygame.Rect(r.centerx - w // 2, self.hud_top() - 8 - h, w, h)
        rr.clamp_ip(scr.get_rect())
        self.box(scr, rr, BG)
        self.text(scr, f"Name your {SPECIES_BY_ID[f['sp']]['name']}", self.f_norm, ACC, (rr.centerx, rr.y + 12), "midtop")
        box = pygame.Rect(rr.x + 30, rr.y + 42, rr.w - 60, 36)
        self.box(scr, box, (18, 22, 36), bevel=False)
        caret = "_" if int(g.now * 2) % 2 else " "
        self.text(scr, g.rename_text + caret, self.f_big, TEXT, (box.x + 10, box.centery + 1), "midleft")
        for i, ln in enumerate(hint):                 # wrapped so it always fits the box
            self.text(scr, ln, self.f_small, DIM, (rr.centerx, rr.y + 84 + 16 * i), "midtop")
        self.button(scr, (rr.centerx - 220, rr.bottom - 44, 120, 32), "Save", lambda: g.finish_rename(True), col=GOOD)
        self.button(scr, (rr.centerx - 90, rr.bottom - 44, 180, 32), "Remove name", g.remove_name,
                    enabled=bool(f.get("named")), col=BAD,
                    tip=["Remove name", "Takes the name tag off this fish"])
        self.button(scr, (rr.centerx + 100, rr.bottom - 44, 120, 32), "Cancel", lambda: g.finish_rename(False), col=NAV)
        self.panel_rect = self.panel_rect or rr

    def draw_update(self, scr):
        g = self.g
        u = g.updater
        w, h = 480, 160
        r = self.tank
        rr = pygame.Rect(r.centerx - w // 2, self.hud_top() - 8 - h, w, h)
        rr.clamp_ip(scr.get_rect())
        self.box(scr, rr, BG)
        tag = u.latest["tag"] if u.latest else "?"
        self.text(scr, f"Update {tag} is available!", self.f_big, ACC, (rr.centerx, rr.y + 12), "midtop")
        if u.state == "downloading":
            self.text(scr, "Downloading...", self.f_small, DIM, (rr.centerx, rr.y + 50), "midtop")
            self.bar(scr, (rr.x + 40, rr.y + 74, rr.w - 80, 16), u.progress, (255, 214, 90))
            return
        if u.state == "ready":
            self.text(scr, "Installing - the game will reopen in a moment.", self.f_small, DIM,
                      (rr.centerx, rr.y + 50), "midtop")
            return
        self.text(scr, f"You have v{VERSION}. Your fish and progress are kept.", self.f_small, TEXT,
                  (rr.centerx, rr.y + 48), "midtop")
        self.text(scr, "It saves, closes for a moment, then reopens.", self.f_small, DIM,
                  (rr.centerx, rr.y + 68), "midtop")

        def later():
            self.update_prompt = False
        self.button(scr, (rr.centerx - 150, rr.bottom - 44, 170, 32), "Update now", g.start_update, col=GOOD)
        self.button(scr, (rr.centerx + 30, rr.bottom - 44, 120, 32), "Later", later, col=NAV)
        self.panel_rect = self.panel_rect or rr

    def draw_welcome(self, scr):
        g = self.g
        away, amt = g.welcome
        w, h = 500, 160
        r = self.tank
        rr = pygame.Rect(r.centerx - w // 2, self.hud_top() - 8 - h, w, h)
        rr.clamp_ip(scr.get_rect())
        self.box(scr, rr, BG)
        self.text(scr, "Welcome back!", self.f_big, ACC, (rr.centerx, rr.y + 12), "midtop")
        self.text(scr, f"You were away {E.fmt_time(away)}.", self.f_small, DIM, (rr.centerx, rr.y + 46), "midtop")
        self.text(scr, f"Your catfish shed {E.fmt(amt)} scales", self.f_norm, SCALE_COL,
                  (rr.centerx, rr.y + 68), "midtop")
        s = g.state
        extra = []
        if E.ulv(s, "jar") and s["jar"] >= 1:
            extra.append(f"Jar: {E.fmt(s['jar'])}")
        ready = sum(1 for e in s["eggs"] if e["left"] <= 0)
        if ready:
            extra.append(f"{ready} egg{'s' if ready > 1 else ''} ready")
        if extra:
            self.text(scr, "  -  ".join(extra), self.f_small, TEXT, (rr.centerx, rr.y + 90), "midtop")

        def close():
            g.welcome = None

        def collect():
            g.welcome = None
            g.collect_all()
        if extra:
            self.button(scr, (rr.centerx - 125, rr.bottom - 44, 140, 32), "Collect!", collect, col=GOLD)
            self.button(scr, (rr.centerx + 25, rr.bottom - 44, 100, 32), "Later", close, col=NAV)
        else:
            self.button(scr, (rr.centerx - 55, rr.bottom - 44, 110, 32), "Yay!", close, col=GOOD)
        self.panel_rect = self.panel_rect or rr

    # ------------------------------------------------------------ panels
    def draw_panel(self, scr):
        g = self.g
        r = self.tank
        w = min(800, self.W - 8)
        bottom = self.hud_top() - 4
        h = min(450, bottom - 6)
        rr = pygame.Rect(max(4, r.right - w), bottom - h, w, h)
        pp = g.state["settings"].get("panel_pos")
        if pp:
            rr.topleft = pp
        rr.clamp_ip(scr.get_rect())
        self.panel_rect = rr
        self.box(scr, rr, BG)
        # grip bar: drag here to move the panel
        grip = pygame.Rect(rr.x + 6, rr.y + 5, rr.w - 54, 10)
        self.grip_rect = grip.inflate(0, 6)
        gcol = (120, 130, 160) if (self.drag or self.hovered(self.grip_rect)) else (70, 80, 108)
        for gx in range(grip.x + 4, grip.right - 4, 6):
            scr.fill(gcol, (gx, grip.y + 2, 2, 2))
            scr.fill(gcol, (gx + 3, grip.y + 6, 2, 2))
        self.tips.append((self.grip_rect, ["Drag to move", "Reset it in Options"]))
        if self.panel != "baby":
            self.button(scr, (rr.right - 40, rr.y + 8, 30, 30), "x", lambda: self.open(self.panel), col=BAD)
        if self.panel == "shop":
            tabs = [("fish", "Catfish"), ("toys", "Toys"), ("upgrades", "Upgrades"), ("hatchery", "Hatchery"),
                    ("themes", "Themes"),
                    ("mine", "My Tank"), ("spawn", "Pearls")]
            x = rr.x + 10
            for key, lab in tabs:
                tw = self.f_norm.size(lab)[0] + 22
                self.button(scr, (x, rr.y + 20, tw, 30), lab, lambda k=key: self.set_tab(k),
                            col=GOOD if self.tab == key else TAB)
                x += tw + 6
            draw = {"fish": self.tab_fish, "toys": self.tab_toys, "upgrades": self.tab_upgrades,
                    "mine": self.tab_mine, "spawn": self.tab_spawn, "hatchery": self.tab_hatchery,
                    "themes": self.tab_themes}[self.tab]
            title = None
        elif self.panel == "dex":
            draw, title = self.tab_dex, "Fishdex"
        else:
            draw, title = self.tab_settings, "Options"
        if self.panel == "baby":
            draw, title = self.tab_baby, "A baby catfish hatched!"
        if title:
            self.text(scr, title, self.f_big, ACC, (rr.x + 14, rr.y + 22))
        view = pygame.Rect(rr.x + 6, rr.y + 58, rr.w - 12, rr.h - 64)
        self.view_h = view.h
        key = (self.panel, self.tab)
        off = self.scroll.get(key, 0)
        n_hits = len(self.hits)
        n_tips = len(self.tips)
        scr.set_clip(view)
        self.content_h = draw(scr, view, view.y - off)
        scr.set_clip(None)
        # drop hits that are scrolled out of view, clip the rest
        kept = self.hits[:n_hits]
        for hr, cb in self.hits[n_hits:]:
            c = hr.clip(view)
            if c.w > 0 and c.h > 0:
                kept.append((c, cb))
        self.hits = kept
        self.tips = self.tips[:n_tips] + [(t[0].clip(view), t[1]) for t in self.tips[n_tips:]]
        mx = max(0, self.content_h - view.h)
        if off > mx:
            self.scroll[key] = mx
        if mx > 0:
            k = view.h / self.content_h
            sb_h = max(20, int(view.h * k))
            sb_y = view.y + int((view.h - sb_h) * (off / mx))
            scr.fill(BORDER, (view.right - 6, view.y, 6, view.h))
            scr.fill(GOOD, (view.right - 6, sb_y, 6, sb_h))

    def row(self, scr, view, y, icon, title, lines, btn_label, btn_cb, enabled, tcol=TEXT, btn_col=GOOD,
            tip=None):
        rr = pygame.Rect(view.x + 4, y, view.w - 16, ROW_H - 4)
        self.box(scr, rr, BG2)
        if icon is not None:
            ir = icon.get_rect(center=(rr.x + 44, rr.centery))
            if ir.w > 80:
                icon = pygame.transform.scale(icon, (80, int(icon.get_height() * 80 / icon.get_width())))
                ir = icon.get_rect(center=(rr.x + 44, rr.centery))
            scr.blit(icon, ir)
        tx = rr.x + 92
        bw = max(110, self.f_norm.size(btn_label)[0] + 24) if btn_label else 0
        tw = rr.right - tx - bw - 20
        self.text(scr, title, self.f_norm, tcol, (tx, rr.y + 8))
        yy = rr.y + 30
        out = []
        for ln in lines[:2]:
            col = DIM
            if isinstance(ln, tuple):
                ln, col = ln
            out += [(w, col) for w in self.wrap(ln, self.f_small, tw)]
        for ln, col in out[:3]:
            self.text(scr, ln, self.f_small, col, (tx, yy))
            yy += 16
        if btn_label:
            self.button(scr, (rr.right - bw - 10, rr.centery - 17, bw, 34), btn_label, btn_cb, enabled,
                        col=btn_col, tip=tip)
        return rr

    def tab_fish(self, scr, view, y):
        g, s = self.g, self.g.state
        cap = E.capacity(s)
        n = len(s["fish"])
        self.text(scr, f"Tank: {n}/{cap} fish  ({TANK_NAMES[E.ulv(s, 'tank')]})", self.f_norm,
                  ACC if n >= cap else TEXT, (view.x + 8, y + 2))
        self.text(scr, "New species give +3% scales forever.", self.f_small, DIM, (view.x + 8, y + 22))
        y0 = y
        y += 42
        full = n >= cap
        for sp in SEASONAL_SPECIES:
            why = E.seasonal_fish_buyable(s, sp["id"])
            if why == "season":
                continue                      # out of season and never owned: hidden
            c = E.species_cost(s, sp["id"])
            season = SEASONS[sp["season"]]["name"]
            ever = sp["id"] in s.get("seasonal_owned", [])
            note = f"{season} special! One per tank." if E.in_season(sp["season"]) else "One per tank."
            fish = next((f for f in s["fish"] if f["sp"] == sp["id"]), None)
            each = E.fish_rate(s, fish or dict(sp=sp["id"], lv=1, happy=70, full=80)) * E.global_mult(s)
            lines = [(f"{E.fmt(each)}/s  -  2x your best catfish. {note}", (255, 170, 80)), sp["blurb"]]
            if why == "owned":
                lab, ok = "In tank", False
            else:
                lab, ok = ("Tank full" if full else E.fmt(c)), (not full) and g.can_afford(c)
            self.row(scr, view, y, sprites.fish_icon(sp["id"], 3), sp["name"] + ("" if ever else "  NEW!"), lines,
                     lab, lambda i=sp["id"]: g.buy_species(i), ok, tcol=(255, 170, 80))
            y += ROW_H
        for sp in SPECIES:
            i = sp["tier"]
            if not E.species_visible(s, i):
                break
            known = E.species_known(s, i) or sp["id"] in s["dex"]
            c = E.species_cost(s, sp["id"])
            own = E.owned_count(s, sp["id"])
            if known:
                icon = sprites.fish_icon(sp["id"], 3)
                lines = [(f"{E.fmt(sp['rate'] * E.global_mult(s))}/s each  -  you have {own}", (170, 220, 250)),
                         sp["blurb"]]
                lab = "Tank full" if full else E.fmt(c)
                self.row(scr, view, y, icon, sp["name"] + ("" if sp["id"] in s["dex"] else "  NEW!"), lines,
                         lab, lambda i=sp["id"]: g.buy_species(i), (not full) and g.can_afford(c))
            else:
                icon = sprites.fish_icon(sp["id"], 3, silhouette=True)
                self.row(scr, view, y, icon, "???", ["Buy the species above to discover this one."],
                         None, None, False, DIM)
            y += ROW_H
        return y - y0

    def tab_toys(self, scr, view, y):
        g, s = self.g, self.g.state
        y0 = y
        self.text(scr, f"Fish play with toys and shed scales. Total bonus +{int(E.toy_bonus(s) * 100)}%",
                  self.f_small, DIM, (view.x + 8, y + 2))
        y += 24
        unowned = 0
        seasonal = [t for t in TOYS if t.get("season") and (E.toy_lv(s, t["id"]) or E.seasonal_ok(s, t))]
        for t in seasonal + [t for t in TOYS if not t.get("season")]:
            lv = E.toy_lv(s, t["id"])
            if lv == 0 and not t.get("season"):
                unowned += 1
                if unowned > 2:
                    break
            c = E.toy_cost(s, t["id"])
            maxed = lv >= TOY_MAX_LEVEL
            best = max(s["fish"], key=lambda f: E.fish_rate(s, f))
            pay = E.toy_play_value(s, best, t["id"]) if lv else 0
            nxt = f"  (next: +{t['bonus']}%)" if 0 < lv < TOY_MAX_LEVEL else ""
            lines = [(f"Lv {lv}/{TOY_MAX_LEVEL}  +{t['bonus'] * lv}% scales{nxt}", (170, 220, 250)),
                     (f"Pays up to {E.fmt(pay)} scales every time a fish plays with it" if lv else
                      f"{t['desc']} Fish that play with it shed scales!", (255, 214, 90) if lv else DIM)]
            lab = "MAX" if maxed else (("Buy " if lv == 0 else "Up ") + E.fmt(c))
            if t.get("season") and not lv:
                lines[0] = (f"{SEASONS[t['season']]['name']} special!  +{t['bonus']}% scales per level", (255, 170, 80))
            self.row(scr, view, y, sprites.toy_icon(t["id"], 2), t["name"], lines, lab,
                     lambda i=t["id"]: g.buy_toy(i), (not maxed) and g.can_afford(c),
                     tcol=(255, 170, 80) if t.get("season") else TEXT)
            y += ROW_H
        return y - y0

    def upgrade_effect(self, uid):
        s = self.g.state
        l = E.ulv(s, uid)
        if uid == "tank":
            nxt = TANK_CAPACITY[min(l + 1, len(TANK_CAPACITY) - 1)]
            return f"{TANK_NAMES[l]}: {E.capacity(s)} fish  ->  {TANK_NAMES[min(l + 1, len(TANK_NAMES) - 1)]}: {nxt}"
        if uid == "filter":
            return f"Now +{20 * l}% scales"
        if uid == "hands":
            return f"Pet power x{E.hands_mult(s):.1f}"
        if uid == "magnet":
            return f"Pop-bubbles worth {E.fmt(E.pop_value(s))}"
        if uid == "bubbler":
            return f"A pop-bubble every ~{E.pop_interval(s):.1f}s"
        if uid == "heater":
            return f"Needs drain x{E.drain_mult(s):.2f}"
        if uid == "light":
            return f"+{E.passive_xp(s):.2f} XP/s per fish"
        if uid == "feeder":
            return "Off" if l == 0 else f"Checks every {max(8, 40 - 7 * l)}s, feeds below {25 + 6 * l}% full"
        if uid == "conditioner":
            return f"Now +{15 * l}% scales  -  water clarity {int(l / 25 * 100)}%"
        if uid == "plants":
            return f"Now +{8 * l}% scales"
        if uid == "pump":
            return f"Toys pay +{int(E.PUMP_EFF * 100 * l)}%"
        if uid == "jar":
            if not l:
                return "Not built yet"
            return f"Fills at {int((0.4 + 0.05 * l) * 100)}% of income, holds {E.jar_minutes(s)} min worth"
        if uid == "hatchery":
            if not l:
                return "Not built yet"
            return f"{E.egg_slots(s)} nest slot(s), hatch time x{E.hatch_speed(s):.2f}, rewards +{10 * (l - 1)}%"
        if uid == "ghostglow":
            return f"Now +{10 * l}% scales"
        if uid == "spooky":
            return f"Bubbles worth +{40 * l}%"
        if uid == "treats":
            return f"Visitors x{1 + 0.2 * l:.1f} as often, gifts +{60 * l}%"
        if uid == "rub":
            if not l:
                return "Not learned yet"
            return f"Rub for {E.rub_secs(s)}s, then rest {RUB_COOLDOWN}s"
        if uid == "autonest":
            return "On - eggs are re-laid for you" if l else "Off"
        if uid == "lucky":
            return f"Golden bubble chance {E.golden_chance(s) * 100:.1f}%"
        if uid == "abyss":
            return f"Now +{50 * l}% scales"
        if uid == "school":
            return f"Now +{2 * l * len(s['fish'])}% scales ({len(s['fish'])} fish)"
        if uid == "polish":
            return f"Pop-bubbles x{1 + l} value"
        if uid == "current":
            return f"Toys pay +{50 * l}%"
        if uid == "timecrystal":
            return f"Eggs x{0.9 ** l:.2f} time, jar +{25 * l}%"
        if uid == "bait":
            return f"Shiny chance {E.shiny_chance(s) * 100:.1f}%, visitor gifts x{1 + l}"
        if uid == "infinity":
            return f"Tank holds {E.capacity(s)} catfish"
        if uid == "care":
            pct, hrs = E.offline_terms(s)
            return f"Offline: {int(pct * 100)}% income for up to {hrs:g}h"
        return ""

    def tab_upgrades(self, scr, view, y):
        g, s = self.g, self.g.state
        y0 = y
        hidden = 0
        for u in sorted(UPGRADES, key=lambda u: not u.get("season")):
            if not E.upgrade_visible(s, u["id"]):
                hidden += 1
                continue
            l = E.ulv(s, u["id"])
            maxed = l >= u["max"]
            c = E.upgrade_cost(s, u["id"])
            lab = "MAX" if maxed else E.fmt(c)
            self.row(scr, view, y, sprites.upgrade_icon(u["id"], 4), f"{u['name']}  (Lv {l})",
                     [(self.upgrade_effect(u["id"]), (170, 220, 250)), u["desc"]], lab,
                     lambda i=u["id"]: g.buy_upgrade(i), (not maxed) and g.can_afford(c))
            y += ROW_H
        if hidden:
            self.text(scr, f"+{hidden} more upgrade{'s' if hidden > 1 else ''} unlock{'' if hidden > 1 else 's'} "
                      "as your tank gets richer...", self.f_small, DIM, (view.x + 12, y + 4))
            y += 26
        return y - y0

    def tab_mine(self, scr, view, y):
        g, s = self.g, self.g.state
        y0 = y
        gm = E.global_mult(s)
        for f in sorted(s["fish"], key=lambda f: -E.fish_rate(s, f)):
            sp = SPECIES_BY_ID[f["sp"]]
            rr = pygame.Rect(view.x + 4, y, view.w - 14, ROW_H - 4)
            self.box(scr, rr, BG2)
            ic = sprites.fish_icon(f["sp"], 3, shiny=f.get("shiny", False), look=E.fish_look(f))
            if ic.get_width() > 76:
                ic = pygame.transform.scale(ic, (76, int(ic.get_height() * 76 / ic.get_width())))
            scr.blit(ic, ic.get_rect(center=(rr.x + 40, rr.centery)))
            self.text(scr, f"{f['name']}  Lv {f['lv']}" + ("  *SHINY*" if f.get("shiny") else ""), self.f_norm,
                      (255, 170, 230) if f.get("shiny") else TEXT, (rr.x + 84, rr.y + 4))
            self.button(scr, (rr.right - 230, rr.centery - 13, 92, 26), "Rename",
                        lambda fish=f: g.start_rename(fish), col=TAB, font=self.f_small)
            self.text(scr, f"{sp['name']}  -  +{E.fmt(E.fish_rate(s, f) * gm)}/s", self.f_small, DIM,
                      (rr.x + 84, rr.y + 23))
            bx = rr.x + 84
            for lab, k, col in (("xp", f["xp"] / E.xp_needed(f["lv"]), (150, 130, 250)),
                                ("full", f["full"] / 100, (240, 170, 80)), ("happy", f["happy"] / 100, PINK)):
                self.bar(scr, (bx, rr.y + 41, 70, 8), k, col)
                bx += 78
            if len(s["fish"]) > 1:
                conf = self.confirm == ("rehome", f["uid"])
                lab = "Sure?" if conf else f"Sell +{E.fmt(E.sell_value(s, f))}"

                def cb(u=f["uid"], conf=conf):
                    if conf:
                        self.confirm = None
                        g.rehome(u)
                    else:
                        self.confirm = ("rehome", u)
                bw = max(110, self.f_small.size(lab)[0] + 20)
                self.button(scr, (rr.right - bw - 8, rr.centery - 13, bw, 26), lab, cb,
                            col=BAD if conf else NAV, font=self.f_small)
            y += ROW_H
        return y - y0

    def tab_themes(self, scr, view, y):
        g, s = self.g, self.g.state
        y0 = y
        self.text(scr, "Change the whole look of the tank. Every theme you own: +5% scales.", self.f_small, DIM,
                  (view.x + 8, y + 2))
        y += 24
        for th in sorted(THEMES, key=lambda t: not t.get("season")):     # seasonal ones on top
            if not E.theme_visible(s, th["id"]):
                continue
            icon = pygame.Surface((56, 36))
            for yy in range(28):
                k = yy / 27
                icon.fill(tuple(int(th["water"][0][i] + (th["water"][1][i] - th["water"][0][i]) * k) for i in range(3)),
                          (0, yy, 56, 1))
            icon.fill(th["sand"][0], (0, 28, 56, 8))
            for i, pc in enumerate(th["plants"][:3]):
                icon.fill(pc, (8 + i * 16, 12 - i * 3, 3, 16 + i * 3))
            own = th["id"] in s["themes"]
            using = s.get("theme") == th["id"]
            if using:
                lab, ok, col = "In use", False, GOOD
            elif own:
                lab, ok, col = "Use", True, TAB
            else:
                c = E.theme_cost(s, th["id"])
                lab, ok, col = E.fmt(c), g.can_afford(c), GOOD
            extra = f"+{th['bonus']}% scales forever" if th["bonus"] else "Free"
            lines = [(extra, (255, 214, 90)), th["desc"]]
            if th.get("season"):
                if th["id"] == "haunted":
                    for i, pc in enumerate(((240, 238, 245), (230, 116, 24))):
                        icon.fill(pc, (40 + i * 7, 18 - i * 6, 4, 4))
                if not own:
                    lines[0] = (f"{extra}  -  {SEASONS[th['season']]['name']} only!", (255, 170, 80))
            self.row(scr, view, y, icon, th["name"], lines, lab,
                     lambda i=th["id"]: g.theme_action(i), ok, btn_col=col,
                     tcol=(255, 170, 80) if th.get("season") else TEXT)
            y += ROW_H
        return y - y0

    def tab_hatchery(self, scr, view, y):
        g, s = self.g, self.g.state
        y0 = y
        lv = E.ulv(s, "hatchery")
        if not lv:
            for ln in self.wrap("Build the Hatchery (Shop > Upgrades) to lay eggs for free. "
                                "When they hatch, baby fry swim around, every fish grows, and you get a gift of scales.",
                                self.f_small, view.w - 30):
                self.text(scr, ln, self.f_small, TEXT, (view.x + 10, y))
                y += 18
            return y - y0 + 10
        slots = E.egg_slots(s)
        nxt = next((l for l in range(lv + 1, 11) if 1 + (l - 1) // 3 > 1 + (lv - 1) // 3), None)
        more = f"  (next slot at Hatchery Lv {nxt})" if nxt else ""
        self.text(scr, f"Nest: {len(s['eggs'])}/{slots} eggs{more}", self.f_norm, TEXT, (view.x + 8, y + 2))
        ready = [e for e in s["eggs"] if e["left"] <= 0]
        if ready:
            self.button(scr, (view.right - 200, y - 2, 180, 30), f"Hatch {len(ready)} ready!", g.hatch_ready,
                        col=GOLD)
        y += 26
        st = s["stats"]
        self.text(scr, f"Nursery: {st.get('eggs_hatched', 0)} eggs hatched  -  {st.get('babies', 0)} babies  -  "
                       f"{st.get('shiny_babies', 0)} shiny  -  {st.get('empty_eggs', 0)} empty",
                  self.f_small, (200, 180, 255), (view.x + 8, y))
        y += 22
        if E.ulv(s, "autonest"):
            on = not s.get("autonest_off")
            self.button(scr, (view.x + 8, y, 190, 28), "Auto-Nest: ON" if on else "Auto-Nest: OFF",
                        g.toggle_autonest, col=GOOD if on else NAV,
                        tip=["Auto-Nest", "Turn it off to change which eggs you lay"])
            self.text(scr, "Re-lays the same eggs after they hatch." if on else
                      "Paused: lay whichever eggs you want.", self.f_small, DIM, (view.x + 210, y + 7))
            y += 36
        for e in s["eggs"]:
            cl = CLUTCHES_BY_ID[e["c"]]
            rr = pygame.Rect(view.x + 4, y, view.w - 16, 44)
            self.box(scr, rr, BG2)
            pygame.draw.ellipse(scr, cl["color"], (rr.x + 14, rr.y + 8, 20, 26))
            done = e["left"] <= 0
            self.text(scr, cl["name"], self.f_norm, ACC if done else TEXT, (rr.x + 48, rr.y + 6))
            txt = "Ready to hatch!" if done else f"{E.fmt_time(e['left'])} left"
            reward = ("could be anything!" if e["c"] == "mystery" else
                      f"+{E.fmt(E.clutch_reward(s, e))} & +{E.clutch_levels(s, e['c']):.1f} lv each")
            self.text(scr, f"{txt}   {reward}",
                      self.f_small,
                      (255, 214, 90) if done else DIM, (rr.x + 48, rr.y + 25))
            self.bar(scr, (rr.right - 230, rr.y + 16, 170, 12), 1 - e["left"] / max(1, e["total"]),
                     (255, 214, 90) if done else (150, 200, 240))
            conf = self.confirm == ("egg", id(e))

            def rm(e=e, conf=conf):
                if conf:
                    self.confirm = None
                    g.remove_egg(e)
                else:
                    self.confirm = ("egg", id(e))
            self.button(scr, (rr.right - 50, rr.y + 8, 40, 28), "?" if conf else "x", rm, col=BAD if conf else NAV,
                        tip=["Click again to remove" if conf else "Remove this egg",
                             "Mystery Eggs go back to your stash" if e["c"] == "mystery" else "Its timer is lost"])
            y += 48
        y += 6
        full = len(s["eggs"]) >= slots
        if s.get("mystery", 0) > 0:
            from .data import MYSTERY_EGG as M
            icon = pygame.Surface((24, 30), pygame.SRCALPHA)
            pygame.draw.ellipse(icon, M["color"], (2, 2, 20, 26))
            self.text(icon, "?", self.f_small, (255, 255, 255), (12, 16), "center")
            lines = [(f"You have {s['mystery']}  -  hatches in {E.fmt_time(E.clutch_time(s, 'mystery'))}",
                      (210, 180, 255)), M["desc"]]
            self.row(scr, view, y, icon, "Mystery Egg", lines, "Nest full" if full else "Lay (free)",
                     lambda: g.lay_clutch("mystery"), not full)
            y += ROW_H
        for cl in CLUTCHES:
            fake = dict(c=cl["id"], inc=E.income(s))
            lines = [(f"{E.fmt_time(E.clutch_time(s, cl['id']))}  -  +{E.fmt(E.clutch_reward(s, fake))} scales, "
                      f"+{E.clutch_levels(s, cl['id']):.1f} levels to every fish", (255, 214, 90)), cl["desc"]]
            icon = pygame.Surface((24, 30), pygame.SRCALPHA)
            pygame.draw.ellipse(icon, cl["color"], (2, 2, 20, 26))
            pygame.draw.ellipse(icon, (255, 255, 255), (6, 6, 5, 7))
            self.row(scr, view, y, icon, cl["name"], lines, "Nest full" if full else "Lay (free)",
                     lambda i=cl["id"]: g.lay_clutch(i), not full)
            y += ROW_H
        return y - y0

    def tab_baby(self, scr, view, y):
        """mandatory choice: a hatchling arrived but the tank is full"""
        g, s = self.g, self.g.state
        y0 = y
        if not s.get("pending"):
            return 0
        b = s["pending"][0]
        sp = SPECIES_BY_ID[b["sp"]]
        rr = pygame.Rect(view.x + 4, y, view.w - 16, 92)
        self.box(scr, rr, (60, 54, 40))
        ic = sprites.fish_icon(b["sp"], 4, shiny=b.get("shiny", False), look=E.fish_look(b))
        scr.blit(ic, ic.get_rect(center=(rr.x + 70, rr.centery)))
        self.text(scr, f"{b['name']} the baby {sp['name']}" + ("  *SHINY*" if b.get("shiny") else ""),
                  self.f_norm, ACC, (rr.x + 150, rr.y + 10))
        self.text(scr, "Your tank is full! Sell this baby, or sell a fish below to make room.", self.f_small,
                  TEXT, (rr.x + 150, rr.y + 34))
        grown = E.fish_rate(s, dict(b, grow=0)) * E.global_mult(s)
        self.text(scr, f"Earns +{E.fmt(grown)}/s grown  (+{E.fmt(grown * 0.25)}/s as a fry)", self.f_small,
                  (170, 220, 250), (rr.x + 150, rr.y + 52))
        more = len(s["pending"]) - 1
        if more:
            self.text(scr, f"(+{more} more hatchling{'s' if more > 1 else ''} waiting)", self.f_small, DIM,
                      (rr.x + 150, rr.y + 70))
        self.button(scr, (rr.right - 200, rr.bottom - 40, 186, 32), f"Sell baby +{E.fmt(E.sell_value(s, b))}",
                    g.sell_pending, col=BAD)
        y += 100
        self.text(scr, "Or sell one of these to keep the baby:", self.f_norm, TEXT, (view.x + 8, y + 2))
        y += 26
        gm = E.global_mult(s)
        for f in sorted(s["fish"], key=lambda f: E.fish_rate(s, f)):
            fsp = SPECIES_BY_ID[f["sp"]]
            row = pygame.Rect(view.x + 4, y, view.w - 16, 48)
            self.box(scr, row, BG2)
            fic = sprites.fish_icon(f["sp"], 2, shiny=f.get("shiny", False), look=E.fish_look(f))
            scr.blit(fic, fic.get_rect(center=(row.x + 44, row.centery)))
            self.text(scr, f"{f['name']}  Lv {f['lv']}" + ("  *SHINY*" if f.get("shiny") else ""), self.f_norm,
                      TEXT, (row.x + 92, row.y + 6))
            self.text(scr, f"{fsp['name']}  -  +{E.fmt(E.fish_rate(s, f) * gm)}/s", self.f_small, DIM,
                      (row.x + 92, row.y + 26))
            self.button(scr, (row.right - 150, row.centery - 14, 140, 28), f"Sell +{E.fmt(E.sell_value(s, f))}",
                        lambda u=f["uid"]: g.rehome(u), col=NAV, font=self.f_small)
            y += 52
        return y - y0

    def tab_spawn(self, scr, view, y):
        g, s = self.g, self.g.state
        y0 = y
        lines = ("Spawning Season: release your tank into the river and start fresh. Your catfish leave "
                 "you Pearls to spend in the Pearl Tree below - those bonuses last forever. You keep pearls, "
                 "the tree, Fishdex, themes and shinies. Scales, fish, toys and upgrades reset.")
        for ln in self.wrap(lines, self.f_small, view.w - 30):
            self.text(scr, ln, self.f_small, TEXT, (view.x + 10, y))
            y += 17
        y += 10
        p = E.pearls_for(s)
        scr.blit(sprites.pearl_icon(4), (view.x + 10, y))
        self.text(scr, f"Pearls to spend: {s['pearls']}   (seasons: {s['spawns']})", self.f_big, TEXT,
                  (view.x + 44, y))
        y += 34
        self.text(scr, f"Scales this season: {E.fmt(s['earned_run'])}", self.f_norm, DIM, (view.x + 10, y))
        y += 22
        if s["earned_run"] < SPAWN_MIN:
            self.text(scr, f"Need {E.fmt(SPAWN_MIN)} scales this season to spawn.", self.f_norm, (255, 160, 160),
                      (view.x + 10, y))
            self.bar(scr, (view.x + 10, y + 24, view.w - 40, 12), s["earned_run"] / SPAWN_MIN, (200, 190, 240))
            y += 50
        else:
            self.text(scr, f"Spawning now gives +{p} pearls", self.f_norm, (200, 255, 200), (view.x + 10, y))
            y += 30
            conf = self.confirm == ("spawn",)

            def cb():
                if conf:
                    self.confirm = None
                    g.spawn()
                else:
                    self.confirm = ("spawn",)
            self.button(scr, (view.x + 10, y, 260, 34), "Are you sure? Click again" if conf else "Begin Spawning Season",
                        cb, col=BAD if conf else (120, 100, 190))
            y += 44
        y += 6
        self.text(scr, "PEARL TREE", self.f_big, ACC, (view.x + 10, y))
        y += 34
        return y - y0 + self.draw_tree(scr, view, y)

    def draw_tree(self, scr, view, y):
        g, s = self.g, self.g.state
        cols = 4
        cw = (view.w - 20) // cols
        bw, bh, rh = cw - 14, 112, 136
        boxes = {}
        for n in PEARL_TREE:
            boxes[n["id"]] = pygame.Rect(view.x + 6 + n["col"] * cw, y + n["row"] * rh, bw, bh)
        # branches first so boxes sit on top
        for n in PEARL_TREE:
            if n["req"]:
                a, b = boxes[n["req"]], boxes[n["id"]]
                col = (200, 180, 255) if E.tlv(s, n["req"]) else (70, 70, 96)
                scr.fill(col, (a.centerx - 2, a.bottom, 4, b.y - a.bottom))
        for n in PEARL_TREE:
            r = boxes[n["id"]]
            st = E.tree_state(s, n["id"])
            lv = E.tlv(s, n["id"])
            fill = {"max": (70, 60, 110), "locked": (40, 42, 56)}.get(st, (56, 52, 92) if lv else BG2)
            self.box(scr, r, fill)
            tcol = DIM if st == "locked" else (ACC if lv else TEXT)
            self.text(scr, n["name"], self.f_norm, tcol, (r.x + 8, r.y + 6))
            self.text(scr, f"Lv {lv}/{n['max']}", self.f_small, (200, 180, 255), (r.x + 8, r.y + 26))
            yy = r.y + 44
            for ln in self.wrap(n["desc"], self.f_small, r.w - 16)[:2]:
                self.text(scr, ln, self.f_small, DIM if st == "locked" else TEXT, (r.x + 8, yy))
                yy += 15
            if st == "max":
                lab, ok = "MAX", False
            elif st == "locked":
                lab, ok = "Locked", False
            else:
                lab, ok = f"Buy ({E.tree_cost(s, n['id'])})", st == "ok"
            self.button(scr, (r.x + 8, r.bottom - 32, r.w - 16, 26), lab, lambda i=n["id"]: g.buy_tree(i),
                        enabled=ok, col=(120, 100, 190), font=self.f_small,
                        tip=None if st != "locked" else ["Locked", f"Needs {PEARL_TREE_BY_ID[n['req']]['name']} first"])
        rows = 1 + max(n["row"] for n in PEARL_TREE)
        return rows * rh

    def tab_dex(self, scr, view, y):
        g, s = self.g, self.g.state
        y0 = y
        n = len(s["dex"])
        self.text(scr, f"Discovered {n}/{len(SPECIES)}  -  +{3 * n}% scales   Shinies {len(s.get('shinies', []))}",
                  self.f_norm, TEXT, (view.x + 8, y))
        y += 26
        if self.dex_sel and self.dex_sel in s["dex"]:
            sp = SPECIES_BY_ID[self.dex_sel]
            rr = pygame.Rect(view.x + 4, y, view.w - 16, 100)
            self.box(scr, rr, BG2)
            ic = sprites.fish_icon(sp["id"], 4)
            scr.blit(ic, ic.get_rect(center=(rr.x + 60, rr.centery)))
            tx = rr.x + 130
            self.text(scr, sp["name"], self.f_big, ACC, (tx, rr.y + 6))
            hab = {"bottom": "Bottom dweller", "mid": "Mid-water cruiser", "glass": "Glass & rock grazer",
                   "inverted": "Swims upside down"}[sp["habitat"]]
            self.text(scr, f"{hab}  -  base {E.fmt(sp['rate'])}/s  -  owned {E.owned_count(s, sp['id'])}",
                      self.f_small, (170, 220, 250), (tx, rr.y + 38))
            yy = rr.y + 58
            for ln in self.wrap(sp["blurb"], self.f_small, rr.right - tx - 10)[:2]:
                self.text(scr, ln, self.f_small, TEXT, (tx, yy))
                yy += 17
            y += 108
        cols = max(1, (view.w - 10) // 185)
        cw = (view.w - 16) // cols
        for i, sp in enumerate(SPECIES):
            cx = view.x + 4 + (i % cols) * cw
            cy = y + (i // cols) * 106
            rr = pygame.Rect(cx, cy, cw - 6, 100)
            have = sp["id"] in s["dex"]
            sel = self.dex_sel == sp["id"]
            col = BG3 if sel else BG2
            if have and self.hovered(rr):
                col = _lighten(col, 0.1)
            self.box(scr, rr, col)
            ic = sprites.fish_icon(sp["id"], 3, silhouette=not have)
            if ic.get_width() > rr.w - 10:
                ic = pygame.transform.scale(ic, (rr.w - 10, int(ic.get_height() * (rr.w - 10) / ic.get_width())))
            scr.blit(ic, ic.get_rect(center=(rr.centerx, rr.y + 32)))
            nm = self.wrap(sp["name"], self.f_small, rr.w - 12) if have else [f"#{i + 1}  ???"]
            ny = rr.bottom - 8 - 17 * len(nm[:2])
            for ln in nm[:2]:
                self.text(scr, ln, self.f_small, TEXT if have else DIM, (rr.centerx, ny), "midtop")
                ny += 17
            if sp["id"] in s.get("shinies", []):
                self.text(scr, "*", self.f_big, (255, 150, 230), (rr.right - 8, rr.y + 2), "topright")
            if have:
                self.hits.append((rr, lambda i=sp["id"]: setattr(self, "dex_sel", i)))
        rows = (len(SPECIES) + cols - 1) // cols
        return y - y0 + rows * 106

    def tab_settings(self, scr, view, y):
        g = self.g
        st = g.state["settings"]
        y0 = y
        import pygame as _pg

        def label(t):
            self.text(scr, t, self.f_norm, TEXT, (view.x + 12, y + 6))

        def sb(x, w, lab, cb, on=False):
            self.button(scr, (x, y, w, 28), lab, cb, col=GOOD if on else NAV)

        X = view.x + 170
        label("Tank width")
        sb(X, 34, "-", lambda: g.change_setting("width", max(0.2, round(st["width"] - 0.05, 2))))
        self.text(scr, f"{int(st['width'] * 100)}%", self.f_norm, ACC, (X + 70, y + 14), "center")
        sb(X + 106, 34, "+", lambda: g.change_setting("width", min(1.0, round(st["width"] + 0.05, 2))))
        y += 36
        label("Position")
        for i, a in enumerate(("left", "center", "right")):
            sb(X + i * 86, 80, a.title(), lambda a=a: g.change_setting("align", a), st["align"] == a)
        y += 36
        label("Pixel size")
        for i, (lab, v) in enumerate((("Small", 2), ("Medium", 3), ("Large", 4))):
            sb(X + i * 86, 80, lab, lambda v=v: g.change_setting("scale", v), st["scale"] == v)
        y += 36
        label("Opacity")
        sb(X, 34, "-", lambda: g.change_setting("opacity", max(120, st["opacity"] - 15)))
        self.text(scr, f"{int(st['opacity'] / 2.55)}%", self.f_norm, ACC, (X + 70, y + 14), "center")
        sb(X + 106, 34, "+", lambda: g.change_setting("opacity", min(255, st["opacity"] + 15)))
        y += 36
        from . import winutil
        mons = winutil.monitors()
        cur = st.get("monitor", -1)
        cur = 0 if cur < 0 or cur >= len(mons) else cur
        label("Monitor")
        sb(X, 34, "<", lambda: g.change_setting("monitor", (cur - 1) % len(mons)))
        self.text(scr, f"{cur + 1} / {len(mons)}" + ("  (main)" if mons[cur]["primary"] else ""), self.f_norm, ACC,
                  (X + 100, y + 14), "center")
        sb(X + 166, 34, ">", lambda: g.change_setting("monitor", (cur + 1) % len(mons)))
        y += 36
        label("Always on top")
        sb(X, 80, "On", lambda: g.change_setting("topmost", True), st["topmost"])
        sb(X + 86, 80, "Off", lambda: g.change_setting("topmost", False), not st["topmost"])
        y += 36
        label("Sound")
        sb(X, 80, "On", lambda: g.change_setting("sound", True), st["sound"])
        sb(X + 86, 80, "Off", lambda: g.change_setting("sound", False), not st["sound"])
        sb(X + 182, 34, "-", lambda: g.change_setting("volume", max(0.0, round(st["volume"] - 0.1, 1))))
        self.text(scr, f"{int(st['volume'] * 100)}%", self.f_norm, ACC, (X + 250, y + 14), "center")
        sb(X + 282, 34, "+", lambda: g.change_setting("volume", min(1.0, round(st["volume"] + 0.1, 1))))
        y += 36
        label("Updates")
        sb(X, 80, "On", lambda: g.change_setting("autoupdate", True), st.get("autoupdate", True))
        sb(X + 86, 80, "Off", lambda: g.change_setting("autoupdate", False), not st.get("autoupdate", True))
        self.button(scr, (X + 172, y, 210, 28), "Check for updates", g.check_updates, col=GOOD,
                    tip=["Check for updates", "Looks on GitHub for a newer version right now"])
        ustate = {"checking": "checking...", "none": "up to date", "available": "update ready!",
                  "downloading": "downloading...", "error": "failed",
                  "offline": "offline"}.get(g.updater.state, "")
        if not g.updater.enabled:
            ustate = "no update source set"
        self.text(scr, f"v{VERSION}  {ustate}", self.f_small, DIM, (X + 392, y + 6))
        y += 36
        label("UI size")
        cur_k = float(st.get("uiscale", 1.0))
        for i, kk in enumerate(UI_SCALES):
            sb(X + i * 86, 80, f"{int(kk * 100)}%", lambda kk=kk: g.change_setting("uiscale", kk), cur_k == kk)
        self.text(scr, "(bigger text and buttons)", self.f_small, DIM, (X + 268, y + 6))
        y += 36
        label("Brightness")
        bnow = int(st.get("brightness", 0))
        sb(X, 34, "-", lambda: g.change_setting("brightness", max(-5, bnow - 1)))
        self.text(scr, ("+" if bnow > 0 else "") + str(bnow), self.f_norm, ACC, (X + 70, y + 14), "center")
        sb(X + 106, 34, "+", lambda: g.change_setting("brightness", min(5, bnow + 1)))
        sb(X + 150, 80, "Reset", lambda: g.change_setting("brightness", 0), False)
        self.text(scr, "(darker / brighter tank)", self.f_small, DIM, (X + 240, y + 6))
        y += 36
        label("Name tags")
        sb(X, 80, "On", lambda: g.change_setting("nametags", True), st.get("nametags", True))
        sb(X + 86, 80, "Off", lambda: g.change_setting("nametags", False), not st.get("nametags", True))
        self.text(scr, "(names you give show above your fish)", self.f_small, DIM, (X + 182, y + 6))
        y += 36
        label("Bugs & Support")
        self.button(scr, (X, y, 150, 28), "Report a bug", lambda: g.report("bug"), col=BAD,
                    tip=["Report a bug", "Opens GitHub in your browser with", "your game version filled in"])
        self.button(scr, (X + 156, y, 130, 28), "Get help", lambda: g.report("help"), col=NAV,
                    tip=["Get help", "Ask a question on GitHub"])
        self.text(scr, "(needs a free GitHub account)", self.f_small, DIM, (X + 296, y + 6))
        y += 36
        label("Performance")
        pw = st.get("power", "normal")
        sb(X, 80, "Normal", lambda: g.change_setting("power", "normal"), pw != "saver")
        sb(X + 86, 130, "Battery saver", lambda: g.change_setting("power", "saver"), pw == "saver")
        self.text(scr, "(try this if your computer is lagging)", self.f_small, DIM, (X + 226, y + 6))
        y += 36
        label("Day & night")
        sb(X, 80, "Clock", lambda: g.change_setting("daynight", True), st.get("daynight", True))
        sb(X + 86, 110, "Always day", lambda: g.change_setting("daynight", False), not st.get("daynight", True))
        self.text(scr, "(follows your computer's clock)", self.f_small, DIM, (X + 206, y + 6))
        y += 44
        conf = self.confirm == ("reset",)

        def reset():
            if conf:
                self.confirm = None
                g.reset_save()
            else:
                self.confirm = ("reset",)
        self.button(scr, (view.x + 12, y, 140, 30), "Save & Quit", g.quit, col=GOOD)
        self.button(scr, (view.x + 370, y, 200, 30), "Reset panel spot", self.reset_panel_pos, col=NAV)
        self.button(scr, (view.x + 160, y, 200, 30), "Really erase everything?" if conf else "Reset save", reset,
                    col=BAD)
        y += 44
        st_ = g.state["stats"]
        help_ = ["HOW TO PLAY",
                 "Click a catfish to pet it: scales, happiness & XP.",
                 "Pop the floating bubbles for scales. Golden ones are worth 10x!",
                 "Feed with the food buttons. Hungry fish show a thought bubble and slow down.",
                 "Happy, well-fed, high-level fish shed more scales. Toys keep them happy.",
                 "Drag toys to rearrange the tank. Hover a fish to see its needs.",
                 f"Stats: {st_['pets']} pets, {st_['pops']} pops, {st_['fed']} snacks, "
                 f"played {E.fmt_time(st_['playtime'])}."]
        for i, ln in enumerate(help_):
            self.text(scr, ln, self.f_norm if i == 0 else self.f_small, ACC if i == 0 else DIM, (view.x + 12, y))
            y += 18
        return y - y0 + 8
