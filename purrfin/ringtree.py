"""The Ring Tree: the big prestige screen. Rings grow outward from the Spring in six branches, and you
only find out what's further along a branch by buying the ring before it."""
import math
import random

import pygame

from . import economy as E
from . import sprites
from .data import PEARL_TREE, PEARL_TREE_BY_ID

R = 24                 # ring radius on screen
STEP = 170             # distance between one ring and the next one out
XS, YS = 1.25, 1.0     # the panel is wider than it is tall, so the tree is too
ZOOMS = (1.0, 0.75, 0.55, 0.4)
CARD_W = 262
HEAD_H = 46

SPRING = "spring"      # the middle of the tree: free, always there, not a ring you buy
SPRING_NAME = "The Spring"

# branch (its first ring): name, colour, icon
BRANCHES = {
    "gills": ("Riches", (255, 205, 90), ("..###..", ".#...#.", "#..#..#", "#.###.#", "#..#..#", ".#...#.", "..###..")),
    "hatch": ("Nursery", (150, 230, 140), ("...#...", "..###..", ".#####.", ".#####.", "#######", "#######", ".#####.")),
    "headstart": ("Seasons", (110, 190, 255), ("#......", "##.....", "###..#.", "#######", "###..#.", "##.....", "#......")),
    "shiny": ("Shine", (255, 150, 220), ("...#...", "...#...", "..###..", "#######", "..###..", "...#...", "...#...")),
    "tender": ("Care", (255, 140, 130), (".##.##.", "#######", "#######", "#######", ".#####.", "..###..", "...#...")),
    "curious": ("Wonder", (190, 150, 255), (".#####.", "##...##", "....##.", "...##..", "...#...", ".......", "...#...")),
}
SPRING_ICON = ("...#...", "..###..", ".#####.", "#######", "#######", ".#####.", "..###..")

KIDS = {}
for _n in PEARL_TREE:
    KIDS.setdefault(_n["req"], []).append(_n["id"])


def branch_of(nid):
    while PEARL_TREE_BY_ID[nid]["req"]:
        nid = PEARL_TREE_BY_ID[nid]["req"]
    return nid


def _lighten(c, k):
    return tuple(min(255, int(v + (255 - v) * k)) for v in c)


def _darken(c, k):
    return tuple(int(v * (1 - k)) for v in c)


def ring_layout():
    """{ring id: (x, y)} with the Spring at (0, 0). Each ring gets a slice of the circle sized to how
    many rings hang off it, so branches never cross."""
    def leaves(nid):
        kids = KIDS.get(nid, [])
        return max(1, sum(leaves(k) for k in kids))

    pos = {}

    def place(nid, a0, a1, depth):
        a = (a0 + a1) / 2
        pos[nid] = (math.cos(a) * STEP * depth * XS, math.sin(a) * STEP * depth * YS)
        kids = KIDS.get(nid, [])
        total = sum(leaves(k) for k in kids)
        at = a0
        for k in kids:
            span = (a1 - a0) * leaves(k) / total
            place(k, at, at + span, depth + 1)
            at += span

    roots = KIDS[None]
    total = sum(leaves(k) for k in roots)
    at = -math.pi / 2 - math.pi * leaves(roots[0]) / total
    for k in roots:
        span = 2 * math.pi * leaves(k) / total
        place(k, at, at + span, 1)
        at += span
    return pos


LAYOUT = ring_layout()


class RingTree:
    def __init__(self, ui):
        self.ui = ui
        self.g = ui.g
        self.pan = [0.0, 0.0]
        self.goal = None           # where the view is gliding to
        self.zoom = 1.0
        self.sel = None
        self.hold = None           # [mouse x, mouse y, pan x, pan y] while dragging the view
        self.canvas = pygame.Rect(0, 0, 1, 1)
        self.born = {}             # ring id -> when it was discovered (it grows in)
        self.sparks = []           # [x, y, vx, vy, life, colour]
        self.last = None
        self.bg = None
        self.need_fit = True
        rnd = random.Random(7)
        self.stars = [(rnd.random(), rnd.random(), rnd.choice((1, 1, 1, 2)), rnd.randint(70, 170)) for _ in range(120)]
        self.bubbles = [[rnd.random(), rnd.random(), rnd.randint(1, 3), rnd.uniform(0.01, 0.03)] for _ in range(24)]

    # ------------------------------------------------------------ opening and moving around
    def opened(self):
        self.hold = None
        self.goal = None
        self.sel = None
        self.need_fit = True       # sized on the next draw, once the window has its new size

    def visible(self):
        s = self.g.state
        return [n["id"] for n in PEARL_TREE if E.tree_visible(s, n["id"])]

    def fit(self):
        """zoom and centre so everything you've found fits on screen"""
        ids = self.visible()
        c = self.canvas
        xs = [LAYOUT[i][0] for i in ids] + [0]
        ys = [LAYOUT[i][1] for i in ids] + [0]
        w, h = max(xs) - min(xs) + 180, max(ys) - min(ys) + 180
        self.zoom = next((z for z in ZOOMS if w * z <= max(c.w, 400) and h * z <= max(c.h, 300)), ZOOMS[-1])
        self.goal = [-(max(xs) + min(xs)) / 2 * self.zoom, -(max(ys) + min(ys)) / 2 * self.zoom]

    def zoom_by(self, d):
        i = ZOOMS.index(self.zoom) + d
        if 0 <= i < len(ZOOMS):
            k = ZOOMS[i] / self.zoom
            self.zoom = ZOOMS[i]
            self.pan = [self.pan[0] * k, self.pan[1] * k]
            self.goal = None

    def wheel(self, dy):
        if dy:
            self.zoom_by(-1 if dy > 0 else 1)
        return True

    def press(self, pos):
        """a press on the open water of the tree: start looking around"""
        if self.canvas.collidepoint(pos):
            self.hold = [pos[0], pos[1], self.pan[0], self.pan[1]]
            self.goal = None
            return True
        return False

    def drag_to(self, pos):
        if self.hold:
            self.pan = [self.hold[2] + pos[0] - self.hold[0], self.hold[3] + pos[1] - self.hold[1]]

    def release(self):
        self.hold = None

    def clamp_pan(self):
        """you can look around what you've found, but not wander off into what you haven't"""
        ids = self.visible()
        xs = [LAYOUT[i][0] * self.zoom for i in ids] + [0]
        ys = [LAYOUT[i][1] * self.zoom for i in ids] + [0]
        self.pan[0] = max(-max(xs), min(-min(xs), self.pan[0]))
        self.pan[1] = max(-max(ys), min(-min(ys), self.pan[1]))

    def bought(self, nid, new_ids):
        """a ring was just bought: sparkle, and let anything it uncovered grow in"""
        now = self.g.now
        x, y = self.at(nid)
        col = BRANCHES[branch_of(nid)][1]
        for _ in range(26):
            a = random.uniform(0, math.tau)
            v = random.uniform(40, 170)
            self.sparks.append([x, y, math.cos(a) * v, math.sin(a) * v, random.uniform(0.4, 0.9), col])
        for k in new_ids:
            self.born[k] = now
        spots = [self.at(k) for k in new_ids]
        if any(not self.canvas.inflate(-140, -140).collidepoint(p) for p in spots):
            # only glide over if what you just found is off screen
            cx = sum(LAYOUT[k][0] for k in new_ids) / len(new_ids)
            cy = sum(LAYOUT[k][1] for k in new_ids) / len(new_ids)
            self.goal = [-cx * self.zoom, -cy * self.zoom]

    def at(self, nid):
        p = (0, 0) if nid == SPRING else LAYOUT[nid]
        return (self.canvas.centerx + p[0] * self.zoom + self.pan[0],
                self.canvas.centery + p[1] * self.zoom + self.pan[1])

    def grown(self, nid):
        """0 -> 1 as a newly found ring grows in"""
        t = self.born.get(nid)
        if t is None:
            return 1.0
        k = (self.g.now - t) / 0.7
        if k >= 1:
            del self.born[nid]
            return 1.0
        return max(0.0, k)

    # ------------------------------------------------------------ drawing
    def draw(self, scr, rr):
        ui, g = self.ui, self.g
        s = g.state
        ui.box(scr, rr, (20, 24, 44))
        self.canvas = pygame.Rect(rr.x + 6, rr.y + HEAD_H + 6, rr.w - CARD_W - 18, rr.h - HEAD_H - 12)
        if self.need_fit:
            self.need_fit = False
            self.fit()
            self.pan, self.goal = list(self.goal), None
        dt = 0.0 if self.last is None else max(0.0, min(0.2, g.now - self.last))
        self.last = g.now
        if self.goal:
            k = min(1.0, dt * 6)
            self.pan[0] += (self.goal[0] - self.pan[0]) * k
            self.pan[1] += (self.goal[1] - self.pan[1]) * k
            if abs(self.goal[0] - self.pan[0]) + abs(self.goal[1] - self.pan[1]) < 1:
                self.goal = None
        elif not self.hold:
            self.clamp_pan()
        self.draw_header(scr, rr, s)
        scr.set_clip(self.canvas)
        self.draw_water(scr, dt)
        hover = self.draw_rings(scr, s)
        self.draw_sparks(scr, dt)
        tip = ui.f_small.render("Drag to look around  -  scroll to zoom", True, (150, 160, 200))
        back = pygame.Surface((tip.get_width() + 16, tip.get_height() + 8), pygame.SRCALPHA)
        back.fill((8, 12, 28, 200))
        scr.blit(back, (self.canvas.x + 4, self.canvas.y + 4))
        scr.blit(tip, (self.canvas.x + 12, self.canvas.y + 8))
        scr.set_clip(None)
        pygame.draw.rect(scr, (70, 78, 120), self.canvas, 2)
        self.draw_card(scr, pygame.Rect(self.canvas.right + 6, self.canvas.y, CARD_W, self.canvas.h), s, hover)

    def draw_header(self, scr, rr, s):
        ui, g = self.ui, self.g
        ui.text(scr, "RING TREE", ui.f_big, (235, 215, 255), (rr.x + 14, rr.y + 12))
        x = rr.x + 14 + ui.f_big.size("RING TREE")[0] + 22
        scr.blit(sprites.pearl_icon(3), (x, rr.y + 15))
        lab = f"{s['pearls']} pearl{'s' if s['pearls'] != 1 else ''}"
        ui.text(scr, lab, ui.f_norm, (255, 240, 200), (x + 28, rr.y + 14))
        x += 28 + ui.f_norm.size(lab)[0] + 22
        found, total = len(self.visible()), len(PEARL_TREE)
        ui.text(scr, f"Found {found} of {total} rings", ui.f_small, (180, 170, 230), (x, rr.y + 17))
        bx = rr.right - 40
        ui.button(scr, (bx, rr.y + 8, 30, 30), "x", lambda: ui.open("rings"), col=(170, 60, 70))
        for lab, cb, w in (("Spawning", ui.rings_to_spawn, 100), ("Fit", self.fit, 54),
                           ("+", lambda: self.zoom_by(-1), 30), ("-", lambda: self.zoom_by(1), 30)):
            bx -= w + 4
            ui.button(scr, (bx, rr.y + 8, w, 30), lab, cb, col=(70, 66, 120))

    def draw_water(self, scr, dt):
        c = self.canvas
        if self.bg is None or self.bg.get_size() != c.size:
            self.bg = pygame.Surface(c.size)
            for y in range(c.h):
                k = y / max(1, c.h - 1)
                pygame.draw.line(self.bg, (int(10 + 8 * k), int(16 + 26 * k), int(38 + 34 * k)), (0, y), (c.w, y))
            for fx, fy, sz, a in self.stars:
                self.bg.fill((a, a, min(255, a + 40)), (int(fx * c.w), int(fy * c.h), sz, sz))
        scr.blit(self.bg, c.topleft)
        for b in self.bubbles:
            b[1] -= b[3] * dt
            if b[1] < 0:
                b[1] = 1.0
            pygame.draw.circle(scr, (60, 90, 130), (c.x + int(b[0] * c.w), c.y + int(b[1] * c.h)), b[2], 1)

    def draw_rings(self, scr, s):
        ui, g = self.ui, self.g
        c = self.canvas
        mouse = ui.mouse
        over = bool(mouse and c.collidepoint(mouse))
        ids = self.visible()
        # lines first, so the rings sit on top of them
        for nid in ids:
            n = PEARL_TREE_BY_ID[nid]
            a = self.at(n["req"] or SPRING)
            b = self.at(nid)
            col = BRANCHES[branch_of(nid)][1]
            k = self.grown(nid)
            b = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
            if E.tlv(s, nid):
                pygame.draw.line(scr, col, a, b, 4)
            else:
                self.dashed(scr, a, b, _darken(col, 0.45))
            # more out there? a few fading dots, and no more than that
            if not E.tlv(s, nid) and KIDS.get(nid) and k >= 1:
                self.hint(scr, self.at(nid), a, col)
        self.draw_spring(scr)
        hover = None
        for nid in ids:
            if self.draw_ring(scr, s, nid, over, mouse):
                hover = nid
        return hover

    def dashed(self, scr, a, b, col):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        if d < 1:
            return
        for i in range(0, int(d), 14):
            t0, t1 = i / d, min(1.0, (i + 8) / d)
            pygame.draw.line(scr, col, (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                             (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1), 2)

    def hint(self, scr, p, parent, col):
        dx, dy = p[0] - parent[0], p[1] - parent[1]
        d = math.hypot(dx, dy) or 1
        dx, dy = dx / d, dy / d
        for i, shade in ((0, 0.55), (1, 0.7), (2, 0.82)):
            at = self.ring_r() + 12 + i * 11
            pygame.draw.circle(scr, _darken(col, shade), (int(p[0] + dx * at), int(p[1] + dy * at)), 2)

    def draw_spring(self, scr):
        ui, g = self.ui, self.g
        x, y = self.at(SPRING)
        p = 2 * math.sin(g.now * 2)
        for rad, col in ((R + 12 + p, (60, 110, 170)), (R + 6 + p, (90, 150, 210))):
            pygame.draw.circle(scr, col, (int(x), int(y)), int(rad), 2)
        pygame.draw.circle(scr, (26, 60, 100), (int(x), int(y)), R)
        pygame.draw.circle(scr, (150, 210, 255), (int(x), int(y)), R, 3)
        self.icon(scr, SPRING_ICON, x, y, (190, 230, 255), 3)
        if self.canvas.collidepoint(x, y):
            rect = pygame.Rect(int(x) - R, int(y) - R, 2 * R, 2 * R).clip(self.canvas)
            ui.hits.append((rect, lambda: setattr(self, "sel", None)))
        if self.zoom >= 0.75:
            ui.text(scr, SPRING_NAME, ui.f_small, (190, 230, 255), (int(x), int(y) + R + 6), "midtop")

    def icon(self, scr, rows, x, y, col, k):
        x0, y0 = int(x) - 7 * k // 2, int(y) - 7 * k // 2
        for ry, row in enumerate(rows):
            for rx, ch in enumerate(row):
                if ch == "#":
                    scr.fill(col, (x0 + rx * k, y0 + ry * k, k, k))

    def draw_ring(self, scr, s, nid, over, mouse):
        ui, g = self.ui, self.g
        n = PEARL_TREE_BY_ID[nid]
        k = self.grown(nid)
        x, y = self.at(nid)
        px, py = self.at(n["req"] or SPRING)
        x, y = px + (x - px) * k, py + (y - py) * k
        full_r = self.ring_r()
        rad = max(3, int(full_r * k))
        ix, iy = int(x), int(y)
        lv = E.tlv(s, nid)
        st = E.tree_state(s, nid)
        branch = branch_of(nid)
        col = BRANCHES[branch][1]
        hit = pygame.Rect(ix - full_r - 2, iy - full_r - 2, 2 * full_r + 4, 2 * full_r + 4)
        hov = over and hit.collidepoint(mouse)
        if st == "ok":                    # you can afford it: it calls to you
            pygame.draw.circle(scr, _lighten(col, 0.3), (ix, iy), rad + 5 + int(2 * math.sin(g.now * 4)), 2)
        if self.sel == nid:
            pygame.draw.circle(scr, (255, 255, 255), (ix, iy), rad + 9, 2)
        ring_col = (255, 225, 120) if st == "max" else (col if lv else _darken(col, 0.4))
        if hov:
            ring_col = _lighten(ring_col, 0.3)
        pygame.draw.circle(scr, (34, 38, 62) if lv else (24, 27, 46), (ix, iy), rad)
        pygame.draw.circle(scr, ring_col, (ix, iy), rad, 4 if full_r >= R else 3)
        if k >= 1:
            self.icon(scr, BRANCHES[branch][2], x, y, col if lv else _darken(col, 0.35), 3 if full_r >= 19 else 2)
            self.pips(scr, ix, iy, lv, n["max"], full_r)
        if (self.zoom >= 0.75 or hov or self.sel == nid) and k >= 1:
            name = n["name"].replace(" Ring", "")
            img = ui.f_small.render(name, True, (255, 255, 255) if hov or self.sel == nid else (205, 210, 235))
            lr = img.get_rect(midtop=(ix, iy + full_r + 7))
            sh = pygame.Surface((lr.w + 6, lr.h + 2), pygame.SRCALPHA)
            sh.fill((8, 12, 28, 170))
            scr.blit(sh, (lr.x - 3, lr.y - 1))
            scr.blit(img, lr)
        rect = hit.clip(self.canvas)
        if rect.w > 0 and rect.h > 0:
            ui.hits.append((rect, lambda i=nid: self.select(i)))
            cost = "Maxed out" if st == "max" else f"Next level: {E.tree_cost(s, nid)} pearls"
            ui.tips.append((rect, [n["name"], f"Lv {lv}/{n['max']}", n["desc"], cost]))
        return hov

    def pips(self, scr, x, y, lv, mx, r):
        """little dots round the ring: one per level"""
        if mx <= 1:
            return
        for i in range(mx):
            a = -math.pi / 2 + 2 * math.pi * i / mx
            p = (int(x + math.cos(a) * (r + 1)), int(y + math.sin(a) * (r + 1)))
            pygame.draw.circle(scr, (255, 240, 170) if i < lv else (16, 18, 34), p, 2)

    def ring_r(self):
        """rings shrink a little when you zoom right out, so they don't bump into each other"""
        return R if self.zoom >= 0.75 else 19 if self.zoom >= 0.55 else 15

    def select(self, nid):
        self.sel = nid

    def draw_sparks(self, scr, dt):
        for p in list(self.sparks):
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
            if p[4] <= 0:
                self.sparks.remove(p)
                continue
            scr.fill(_lighten(p[5], 0.3), (int(p[0]), int(p[1]), 3, 3))

    def draw_card(self, scr, rr, s, hover):
        ui, g = self.ui, self.g
        ui.box(scr, rr, (32, 36, 64))
        x, y = rr.x + 14, rr.y + 12
        w = rr.w - 28
        nid = self.sel
        if nid is None or not E.tree_visible(s, nid):
            ui.text(scr, SPRING_NAME, ui.f_big, (190, 230, 255), (x, y))
            y += 38
            lines = ["Every ring grows out from here. Rings last forever, through every Spawning Season.",
                     "", "Click a ring to see what it does.", "",
                     "You can't see where a branch goes until you buy the ring before it."]
            for para in lines:
                for ln in ui.wrap(para, ui.f_small, w) or [""]:
                    ui.text(scr, ln, ui.f_small, (210, 214, 235), (x, y))
                    y += 18
            y += 12
            if not s["pearls"]:
                for ln in ui.wrap("Pearls come from starting a Spawning Season, once you've earned enough scales.", ui.f_small, w):
                    ui.text(scr, ln, ui.f_small, (255, 220, 150), (x, y))
                    y += 18
                ui.button(scr, (x, rr.bottom - 48, w, 36), "Go to Spawning", ui.rings_to_spawn, col=(120, 100, 190))
            return
        n = PEARL_TREE_BY_ID[nid]
        branch = branch_of(nid)
        bname, col, icon = BRANCHES[branch]
        lv = E.tlv(s, nid)
        st = E.tree_state(s, nid)
        pygame.draw.circle(scr, (24, 27, 46), (x + 30, y + 30), 30)
        pygame.draw.circle(scr, (255, 225, 120) if st == "max" else col, (x + 30, y + 30), 30, 4)
        self.icon(scr, icon, x + 30, y + 30, col, 4)
        ui.text(scr, f"{bname} branch", ui.f_small, col, (x + 72, y + 8))
        ui.text(scr, f"Level {lv} of {n['max']}", ui.f_small, (255, 240, 170), (x + 72, y + 30))
        y += 72
        for ln in ui.wrap(n["name"], ui.f_big, w):
            ui.text(scr, ln, ui.f_big, (235, 225, 255), (x, y))
            y += 30
        y += 4
        for ln in ui.wrap(n["desc"], ui.f_norm, w):
            ui.text(scr, ln, ui.f_norm, (220, 224, 240), (x, y))
            y += 22
        y += 8
        hidden = [k for k in KIDS.get(nid, []) if not E.tree_visible(s, k)]
        if hidden:
            for ln in ui.wrap("Something lies beyond this ring...", ui.f_small, w):
                ui.text(scr, ln, ui.f_small, (190, 170, 240), (x, y))
                y += 18
        by = rr.bottom - 48
        if st == "max":
            ui.button(scr, (x, by, w, 36), "Maxed out!", lambda: None, enabled=False, col=(120, 100, 40))
            return
        cost = E.tree_cost(s, nid)
        ui.text(scr, f"Costs {cost} pearl{'s' if cost != 1 else ''}", ui.f_norm,
                (255, 240, 200) if st == "ok" else (255, 170, 170), (x, by - 28))
        ui.button(scr, (x, by, w, 36), "Buy" if lv == 0 else "Level up", lambda i=nid: g.buy_tree(i),
                  enabled=st == "ok", col=(120, 100, 190))
