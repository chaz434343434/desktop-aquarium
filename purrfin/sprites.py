"""Procedural pixel art. Everything is drawn at low resolution and scaled up."""
import colorsys
import math
import random

import pygame

from .data import SPECIES_BY_ID


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def dark(c, k=0.55):
    return tuple(int(v * k) for v in c[:3])


def light(c, k=0.35):
    return tuple(int(v + (255 - v) * k) for v in c[:3])


# (t, up, down): half-heights along the body, t=0 tail .. t=1 nose
PROFILES = {
    "cory": [(0, .35, .35), (.3, .8, .8), (.55, 1, 1), (.8, .9, .9), (.95, .6, .7), (1, .3, .45)],
    "pleco": [(0, .3, .3), (.35, .75, .6), (.6, .95, .7), (.85, .9, .7), (1, .45, .6)],
    "long": [(0, .3, .3), (.3, .65, .6), (.6, .95, .9), (.85, .85, .8), (1, .3, .45)],
    "syno": [(0, .3, .3), (.35, .8, .7), (.6, 1, .9), (.85, .8, .8), (1, .35, .45)],
    "banjo": [(0, .18, .18), (.45, .3, .3), (.6, .7, .55), (.82, 1, .8), (1, .5, .5)],
}
# (t start, t end, height as fraction of body height)
DORSAL = {"cory": (.45, .68, 1.0), "pleco": (.3, .72, .7), "long": (.55, .68, .9),
          "syno": (.45, .7, 1.0), "banjo": (.6, .72, .4)}


def _profile(shape, t):
    pts = PROFILES[shape]
    for (t0, u0, d0), (t1, u1, d1) in zip(pts, pts[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return u0 + (u1 - u0) * k, d0 + (d1 - d0) * k
    return pts[-1][1], pts[-1][2]


def build_fish(sp, frame):
    L, H = sp["size"]
    shape = sp["shape"]
    rng = random.Random(sp.get("seed", sp["id"]))
    tw = max(3, L // 3)
    bl = sp.get("barbel", 0)
    dsh = DORSAL[shape]
    dh = int(round(H * dsh[2] * (0.38 if shape == "long" else 0.5))) + 1
    W = tw + L + bl + 3
    SH = H + dh + 6
    ox = tw + 1
    hh = H / 2
    cy = dh + 2 + hh
    body, fins = {}, {}
    vmap, tmap = {}, {}
    pat = sp["pat"]
    pattern = sp["pattern"]
    alpha = 255
    if pattern == "glass":
        alpha = 95

    # ---- body
    for i in range(L):
        t = i / (L - 1)
        up, dn = _profile(shape, t)
        top, bot = cy - up * hh, cy + dn * hh
        for y in range(int(top) - 1, int(bot) + 2):
            yc = y + 0.5
            if top <= yc <= bot:
                v = (yc - top) / max(0.01, bot - top)
                if v < 0.28:
                    c = dark(sp["body"], 0.82)
                elif v < 0.66:
                    c = sp["body"]
                else:
                    c = sp["belly"]
                body[(ox + i, y)] = c
                vmap[(ox + i, y)] = v
                tmap[(ox + i, y)] = t

    # ---- patterns
    keys = list(body)
    if pattern in ("sunflower", "golden"):
        for p in keys:
            if tmap[p] > 0.72:
                body[p] = lerp(body[p], (240, 140, 40), 0.35)
            if vmap[p] < 0.7 and rng.random() < 0.16:
                body[p] = pat
    elif pattern == "sheen":
        for p in keys:
            if 0.3 < vmap[p] < 0.6:
                body[p] = lerp(body[p], pat, 0.45)
    elif pattern == "stripe_h":
        for p in keys:
            if 0.4 < vmap[p] < 0.62 and tmap[p] < 0.92:
                body[p] = pat
    elif pattern in ("spots", "dots", "leopard"):
        dens = {"spots": 0.12, "dots": 0.18, "leopard": 0.2}[pattern]
        for p in keys:
            if vmap[p] < 0.72 and rng.random() < dens:
                body[p] = pat
        if pattern == "leopard":
            for p in keys:
                if 0.45 < vmap[p] < 0.6 and p[0] % 2 == 0:
                    body[p] = pat
    elif pattern == "dots_big":
        for p in keys:
            if (p[0] // 2 + p[1] // 2 * 3 + rng.randint(0, 1)) % 3 == 0 and (p[0] + p[1]) % 2 == 0:
                body[p] = pat
    elif pattern == "blotch":
        blobs = [(ox + rng.uniform(0.15, 0.85) * L, cy + rng.uniform(-0.6, 0.4) * hh) for _ in range(4)]
        for p in keys:
            if any((p[0] - bx) ** 2 + (p[1] - by) ** 2 < 2.6 for bx, by in blobs):
                body[p] = pat
    elif pattern == "bands":
        for p in keys:
            if (p[0] + (p[1] // 2)) % 4 == 0:
                body[p] = pat
    elif pattern == "zebra":
        for p in keys:
            if ((p[0] * 2 + p[1]) // 3) % 2 == 0:
                body[p] = pat
    elif pattern == "raphael":
        for p in keys:
            if 0.28 < vmap[p] < 0.42 or 0.66 < vmap[p] < 0.78:
                body[p] = pat
    elif pattern == "royal":
        for p in keys:
            if p[1] % 2 == 0:
                body[p] = pat
    elif pattern == "redtail":
        for p in keys:
            body[p] = dark(sp["body"], 0.9) if vmap[p] < 0.55 else sp["belly"]
    elif pattern == "panda":
        pass  # handled after eye position is known
    elif pattern in ("moon", "galaxy"):
        for p in keys:
            if rng.random() < (0.07 if pattern == "moon" else 0.1):
                body[p] = pat
        if pattern == "galaxy":         # a faint purple-pink nebula swirl
            for p in keys:
                if body[p] != pat and (p[0] + p[1] * 2) % 7 < 2:
                    body[p] = lerp(body[p], (190, 90, 200), 0.45)
    elif pattern == "pumpkin":
        # pumpkin ribs, and a carved grin that glows from inside
        for p in keys:
            if p[0] % 3 == 0 and vmap[p] < 0.85:
                body[p] = dark(sp["body"], 0.82)
            if 0.55 < tmap[p] < 0.9 and 0.56 < vmap[p] < 0.72 and (p[0] % 2 == 0 or vmap[p] > 0.64):
                body[p] = (255, 214, 70)
    elif pattern == "rainbow":
        for p in keys:
            r, g_, b = colorsys.hsv_to_rgb((tmap[p] * 0.9 + vmap[p] * 0.15) % 1.0, 0.45 + 0.2 * (vmap[p] < 0.6), 1.0)
            body[p] = (int(r * 255), int(g_ * 255), int(b * 255))

    # ---- eye
    ex = ox + int(L * 0.82)
    ey = int(cy - hh * 0.25)
    if pattern == "panda":
        for p in keys:
            if (p[0] - ex) ** 2 + (p[1] - ey) ** 2 < 3.2 or (tmap[p] < 0.12 and vmap[p] < 0.6):
                body[p] = pat

    # ---- tail
    fin_col = pat if pattern == "redtail" else sp["fin"]
    up0, dn0 = _profile(shape, 0)
    stalk = max(1.0, up0 * hh)
    sgn = 1 if frame == 0 else -1
    for j in range(1, tw + 1):
        tt = j / tw
        x = ox - j
        if sp["tail"] == "round":
            spread = stalk + hh * 0.9 * math.sin(min(1, tt) * math.pi * 0.75)
        else:
            spread = stalk + tt * hh * 1.15
        shift = sgn * tt * 1.2
        for y in range(int(cy - spread - 2), int(cy + spread + 3)):
            yc = y + 0.5 - shift
            d = abs(yc - cy)
            if d > spread:
                continue
            if sp["tail"] == "fork" and tt > 0.45 and d < spread * (tt - 0.3) * 0.95:
                continue
            c = fin_col
            if pattern == "raphael" and abs(d - spread * 0.5) < 0.6:
                c = pat
            fins[(x, y)] = c

    # ---- dorsal fin
    t0, t1, _ = dsh
    dcol = pat if pattern == "panda" else sp["fin"]
    for i in range(L):
        t = i / (L - 1)
        if t0 <= t <= t1:
            h = dh * (t - t0) / max(0.01, t1 - t0)
            if shape == "pleco":
                h = dh * (0.6 + 0.4 * (t - t0) / (t1 - t0))
            up, _ = _profile(shape, t)
            top = cy - up * hh
            for y in range(int(top - h), int(top) + 1):
                if (ox + i, y) not in body:
                    fins[(ox + i, y)] = dcol
    # ---- pectoral / pelvic fin
    px = ox + int(L * 0.62)
    _, dn = _profile(shape, 0.62)
    py = int(cy + dn * hh)
    for k in range(2):
        q = (px - k - (frame if k else 0), py + (1 if k else 0))
        if q not in body:
            fins[q] = sp["fin"]

    # ---- assemble
    surf = pygame.Surface((W, SH), pygame.SRCALPHA)
    outline_c = {"moon": (210, 225, 255), "galaxy": (150, 120, 230), "rainbow": (120, 90, 170)}.get(
        pattern, dark(sp["body"], 0.42))
    fin_out = dark(sp["fin"], 0.5)
    allpx = set(body) | set(fins)
    for (x, y) in allpx:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + dx, y + dy)
            if q not in allpx and 0 <= q[0] < W and 0 <= q[1] < SH:
                col = outline_c if (x, y) in body else fin_out
                a = 140 if pattern == "glass" else 255
                if pattern == "glass" or surf.get_at(q).a == 0:
                    surf.set_at(q, (*col, a))
    for p, c in fins.items():
        surf.set_at(p, (*c, int(alpha * 0.85) if pattern == "glass" else 230))
    for p, c in body.items():
        surf.set_at(p, (*c, alpha))
    if pattern == "glass":
        for i in range(int(L * 0.1), int(L * 0.8)):
            surf.set_at((ox + i, int(cy)), (*pat, 200))
        for p, t in tmap.items():
            if t > 0.8:
                surf.set_at(p, (210, 220, 230, 190))

    # eye
    eye = sp.get("eye", (16, 16, 22))
    surf.set_at((ex, ey), (*eye, 255))
    if L >= 15:
        surf.set_at((ex - 1, ey), (*eye, 255))
        surf.set_at((ex, ey - 1), (255, 255, 255, 255))
    elif H >= 6:
        surf.set_at((ex, ey - 1), (*light(body.get((ex, ey - 1), sp["body"]), 0.6), 255))

    # barbels
    bc = (*light(dark(sp["body"], 0.6), 0.25), 255)
    nx, ny = ox + L - 1, int(cy + hh * 0.3)
    wig = 0.5 if frame else 0
    for k in range(1, bl + 1):
        surf.set_at((nx + k, int(ny + k * 0.45 + wig * (k > bl // 2))), bc)
    for k in range(1, max(1, bl // 2) + 1):
        surf.set_at((nx + int(k * 0.5), ny + k), bc)
    if sp.get("bristles"):
        for k in range(3):
            surf.set_at((nx - k, int(cy - hh * 0.55) - (k % 2)), (*light(sp["body"], 0.5), 255))

    if pattern in ("golden", "moon", "galaxy", "rainbow"):
        sp_rng = random.Random(sp["id"] + str(frame))
        for _ in range(3):
            p = sp_rng.choice(keys)
            surf.set_at(p, (255, 255, 240, 255))
    return surf, (ox + L / 2, cy)


_cache = {}


def _rot(c):
    return (c[2], c[0], c[1])


SHINY_TINTS = [(255, 90, 200), (60, 220, 255), (150, 255, 90), (180, 110, 255), (255, 200, 40)]


def shiny_species(sp):
    """same fish, colours rotated round the colour wheel and washed with a bold tint
    (so even white or grey fish look clearly different)"""
    s = dict(sp)
    tint = SHINY_TINTS[sp["tier"] % len(SHINY_TINTS)]
    for k in ("body", "belly", "fin", "pat"):
        if k in s:
            s[k] = lerp(_rot(s[k]), tint, 0.45 if k != "pat" else 0.25)
    return s


def _nudge(col, tone, hue):
    """small per-fish colour shift: tone = lighter/darker steps, hue = tiny turn of the colour wheel"""
    h, s, v = colorsys.rgb_to_hsv(*(x / 255 for x in col))
    h = (h + 0.02 * hue) % 1.0
    v = max(0.0, min(1.0, v * (1 + 0.08 * tone)))
    s = max(0.0, min(1.0, s * (1 + 0.05 * tone)))
    return tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v))


def look_species(sp, look):
    """apply a fish's personal look: (tone -2..2, hue -1..1, pattern seed 0..3, length -1..1, whiskers 0..3)"""
    tone, hue, pseed, dlen, whisk = look
    s = dict(sp)
    for k in ("body", "belly", "fin"):
        s[k] = _nudge(s[k], tone, hue)
    s["seed"] = f"{sp['id']}-{pseed}"
    L, H = s["size"]
    s["size"] = (max(6, L + dlen), H)
    s["barbel"] = s.get("barbel", 0) + whisk
    return s


ART = {}            # species id -> (palette, frames, anchor): hand-drawn pixel art


def _load_art():
    from .art_blue_channel import BLUE_CHANNEL_PALETTE, BLUE_CHANNEL_FRAMES
    # frames as drawn: 0 tail up, 1 tail down, 2 in between -> swim cycle up, middle, down, middle
    order = [BLUE_CHANNEL_FRAMES[i] for i in (0, 2, 1, 2)]
    ART["bluechannel"] = (BLUE_CHANNEL_PALETTE, order, (17, 10))


_load_art()


def _art_colour(sp_id, col, shiny, look):
    """recolour hand-drawn pixels the same way generated fish get their look / shiny colours"""
    if col == (0, 0, 0):
        return col
    if look:
        col = _nudge(col, look[0], look[1])
    if shiny:
        sp = SPECIES_BY_ID[sp_id]
        col = lerp(_rot(col), SHINY_TINTS[sp["tier"] % len(SHINY_TINTS)], 0.45)
    return col


def art_fish(sp_id, shiny, look):
    pal, frames, anchor = ART[sp_id]
    cols = {k: _art_colour(sp_id, c, shiny, look) for k, c in pal.items()}
    out = []
    for rows in frames:
        s = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch != ".":
                    s.set_at((x, y), (*cols[ch], 255))
        out.append(s)
    return out, anchor


def fish_frames(sp_id, shiny=False, look=None):
    """dict: frames[(facing_right, inverted)] -> [surf0, surf1, ...] (2 for generated fish, 4 for drawn ones)"""
    key = (sp_id, bool(shiny), tuple(look) if look else None)
    if key not in _cache:
        if sp_id in ART:
            bs, (ax, ay) = art_fish(sp_id, shiny, look)
        else:
            sp = SPECIES_BY_ID[sp_id]
            if look:
                sp = look_species(sp, look)
            if shiny:
                sp = shiny_species(sp)
            (b0, (ax, ay)), (b1, _) = build_fish(sp, 0), build_fish(sp, 1)
            bs = (b0, b1)
        W, H = bs[0].get_size()
        out = {}
        for right in (True, False):
            for inv in (False, True):
                fr = [b if right else pygame.transform.flip(b, True, False) for b in bs]
                if inv:
                    fr = [pygame.transform.flip(b, False, True) for b in fr]
                out[(right, inv)] = fr
                _anchors[(key, right, inv)] = (ax if right else W - ax, H - ay if inv else ay)
        _cache[key] = out
    return _cache[key]


_anchors = {}


def fish_anchor(sp_id, right, inv, shiny=False, look=None):
    """pixel inside the sprite that sits at the fish's position (body center)"""
    fish_frames(sp_id, shiny, look)
    return _anchors[((sp_id, bool(shiny), tuple(look) if look else None), right, inv)]


def fish_icon(sp_id, scale=3, silhouette=False, shiny=False, look=None):
    key = ("icon", sp_id, scale, silhouette, shiny, tuple(look) if look else None)
    if key not in _cache:
        s = fish_frames(sp_id, shiny, look)[(True, False)][0]
        if silhouette:
            s = s.copy()
            s.fill((20, 22, 34, 255), special_flags=pygame.BLEND_RGBA_MIN)
            s.fill((30, 34, 50, 0), special_flags=pygame.BLEND_RGBA_MAX)
        _cache[key] = pygame.transform.scale(s, (s.get_width() * scale, s.get_height() * scale))
    return _cache[key]


_tag_font = None


def name_tag(text):
    """tiny pixel-font name with a dark outline, at tank resolution"""
    global _tag_font
    key = ("tag", text)
    if key not in _cache:
        if _tag_font is None:
            from .pixfont import PixelFont
            _tag_font = PixelFont(1)
        fg = _tag_font.render(text, False, (255, 250, 230))
        bg = _tag_font.render(text, False, (20, 24, 40))
        w, h = fg.get_width() + 2, fg.get_height() + 2
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
            s.blit(bg, (dx, dy))
        s.blit(fg, (1, 1))
        _cache[key] = s
    return _cache[key]


# ---------------------------------------------------------------- toys
WOOD = (120, 86, 52)
WOOD_D = (70, 48, 30)
STONE = (130, 132, 140)


def draw_toy(surf, tid, cx, by, t=0.0, extra=0.0):
    """draw toy `tid` centered on cx with its base on row `by` (low-res coords)."""
    cx, by = int(cx), int(by)
    D = pygame.draw
    if tid == "ball":
        D.circle(surf, (240, 140, 50), (cx, by - 3), 3)
        D.circle(surf, (255, 200, 140), (cx - 1, by - 4), 1)
    elif tid == "airstone":
        D.rect(surf, (90, 92, 100), (cx - 3, by - 3, 7, 3))
        D.rect(surf, STONE, (cx - 2, by - 3, 5, 1))
    elif tid == "cave":
        old = surf.get_clip()
        surf.set_clip(pygame.Rect(0, 0, surf.get_width(), by + 1).clip(old))
        D.ellipse(surf, WOOD, (cx - 10, by - 12, 20, 26))
        D.ellipse(surf, (34, 26, 22), (cx - 5, by - 7, 10, 16))
        surf.set_clip(old)
        D.line(surf, WOOD_D, (cx - 8, by - 6), (cx - 6, by - 10))
        D.line(surf, light(WOOD, .3), (cx + 6, by - 9), (cx + 8, by - 5))
    elif tid == "sunflower":
        sway = math.sin(t * 1.3) * 1.2
        top = (cx + int(sway), by - 18)
        D.line(surf, (60, 140, 60), (cx, by), top)
        D.ellipse(surf, (70, 160, 70), (cx - 5, by - 9, 5, 3))
        D.ellipse(surf, (70, 160, 70), (cx + 1, by - 12, 5, 3))
        for k in range(8):
            a = k * math.pi / 4 + t * 0.2
            D.circle(surf, (250, 205, 50), (int(top[0] + math.cos(a) * 3.5), int(top[1] + math.sin(a) * 3.5)), 2)
        D.circle(surf, (110, 70, 30), top, 3)
        surf.set_at((top[0] - 1, top[1] - 1), (70, 40, 20))
        surf.set_at((top[0] + 1, top[1]), (70, 40, 20))
    elif tid == "marimo":
        D.circle(surf, (50, 120, 50), (cx, by - 4), 4)
        r = random.Random(int(extra * 3))
        for _ in range(6):
            surf.set_at((cx + r.randint(-3, 3), by - 4 + r.randint(-3, 2)), (90, 170, 80))
    elif tid == "chest":
        D.rect(surf, WOOD, (cx - 6, by - 6, 12, 6))
        D.rect(surf, (220, 180, 60), (cx - 6, by - 6, 12, 1))
        D.rect(surf, (220, 180, 60), (cx - 1, by - 5, 2, 2))
        if extra > 0:  # open
            D.rect(surf, (255, 240, 150), (cx - 5, by - 8, 10, 2))
            D.rect(surf, WOOD_D, (cx - 6, by - 12, 12, 4))
        else:
            D.rect(surf, WOOD_D, (cx - 6, by - 9, 12, 3))
    elif tid == "hammock":
        D.line(surf, WOOD_D, (cx - 7, by), (cx - 7, by - 16))
        D.line(surf, WOOD_D, (cx + 7, by), (cx + 7, by - 16))
        sag = int(math.sin(t * 0.8) * 1)
        D.ellipse(surf, (80, 170, 80), (cx - 7, by - 15 + sag, 14, 4))
        D.line(surf, (50, 120, 50), (cx - 6, by - 13 + sag), (cx + 6, by - 13 + sag))
    elif tid == "castle":
        g, gd = (150, 150, 160), (110, 110, 122)
        D.rect(surf, g, (cx - 7, by - 10, 14, 10))
        D.rect(surf, gd, (cx - 10, by - 16, 5, 16))
        D.rect(surf, gd, (cx + 5, by - 16, 5, 16))
        for k in (-10, -8, 5, 7, 9):
            if k in (-10, -8, 5, 7):
                D.rect(surf, gd, (cx + k, by - 18, 1, 2))
        D.ellipse(surf, (40, 34, 44), (cx - 2, by - 6, 5, 8))
        D.line(surf, (60, 60, 60), (cx + 7, by - 16), (cx + 7, by - 22))
        D.rect(surf, (220, 60, 60), (cx + 8, by - 22, 3 + int(math.sin(t * 3) > 0), 2))
    elif tid == "clam":
        D.ellipse(surf, (225, 190, 200), (cx - 6, by - 4, 12, 5))
        open_ = 3 + int(extra * 2)
        D.ellipse(surf, (240, 205, 215), (cx - 6, by - 4 - open_, 12, 4))
        D.circle(surf, (250, 250, 255), (cx, by - 4), 2)
    elif tid == "ship":
        pts = [(cx - 14, by - 6), (cx + 12, by - 9), (cx + 10, by), (cx - 12, by)]
        D.polygon(surf, WOOD_D, pts)
        D.line(surf, WOOD, (cx - 13, by - 6), (cx + 11, by - 9))
        D.line(surf, WOOD_D, (cx - 2, by - 7), (cx, by - 24))
        D.polygon(surf, (200, 195, 175), [(cx - 1, by - 22), (cx + 7, by - 19), (cx, by - 13)])
        for k in range(3):
            surf.set_at((cx - 8 + k * 6, by - 4), (30, 24, 20))
    elif tid == "coral":
        glow = 0.5 + 0.5 * math.sin(t * 1.5)
        c = lerp((230, 90, 140), (255, 170, 210), glow)
        for dx, h, lean in ((-4, 12, -2), (0, 16, 1), (4, 10, 2), (2, 8, -1)):
            D.line(surf, c, (cx + dx, by), (cx + dx + lean, by - h))
            D.line(surf, c, (cx + dx + lean // 2, by - h // 2), (cx + dx + lean * 2, by - h // 2 - 4))
    elif tid == "diver":
        D.line(surf, (60, 60, 60), (cx - 1, by - 13), (cx - 5, by - 24))
        D.rect(surf, (230, 190, 40), (cx - 3, by - 8, 6, 7))
        D.rect(surf, (200, 160, 30), (cx - 3, by - 2, 2, 2))
        D.rect(surf, (200, 160, 30), (cx + 1, by - 2, 2, 2))
        D.circle(surf, (170, 140, 80), (cx, by - 11), 4)
        D.circle(surf, (120, 200, 230), (cx + 1, by - 11), 2)

    elif tid == "apple":
        D.circle(surf, (200, 30, 40), (cx, by - 4), 4)
        D.circle(surf, (230, 60, 60), (cx - 1, by - 5), 2)
        surf.set_at((cx - 2, by - 6), (255, 200, 200))
        D.line(surf, (90, 60, 30), (cx, by - 8), (cx + 1, by - 10))
        D.ellipse(surf, (70, 160, 60), (cx + 1, by - 11, 4, 2))
    elif tid == "lilypad":
        for k, dx in enumerate((-6, 3)):
            D.ellipse(surf, (60, 150, 60), (cx + dx - 4, by - 2, 9, 3))
            surf.set_at((cx + dx, by - 1), (40, 110, 40))
        D.circle(surf, (255, 190, 220), (cx - 5, by - 3), 1)
        surf.set_at((cx - 5, by - 3), (255, 240, 120))
    elif tid == "waterfall":
        D.polygon(surf, (110, 110, 120), [(cx - 7, by), (cx - 4, by - 9), (cx + 3, by - 11), (cx + 7, by)])
        D.line(surf, (150, 150, 160), (cx - 4, by - 9), (cx + 3, by - 11))
        top = max(4, by - 49)
        for y in range(top, by - 10):
            k = (y - int(t * 20)) % 4
            surf.set_at((cx - 1, y), (200, 235, 250) if k == 0 else (150, 205, 235))
            surf.set_at((cx, y), (230, 248, 255) if k == 2 else (170, 215, 240))
            surf.set_at((cx + 1, y), (150, 205, 235))
        for k in range(3):
            a = t * 6 + k * 2.1
            surf.set_at((cx + int(math.cos(a) * 3), by - 11 - int(abs(math.sin(a)) * 2)), (230, 248, 255))
    elif tid == "volcano":
        D.polygon(surf, (90, 70, 60), [(cx - 9, by), (cx - 2, by - 10), (cx + 2, by - 10), (cx + 9, by)])
        D.line(surf, (130, 100, 80), (cx - 2, by - 10), (cx - 7, by - 1))
        glow = int(120 + 100 * max(0, math.sin(t * 2)))
        D.line(surf, (glow, 80, 40), (cx - 1, by - 10), (cx + 1, by - 10))
    elif tid == "log":
        D.rect(surf, (110, 80, 50), (cx - 12, by - 7, 24, 7))
        D.line(surf, (80, 120, 50), (cx - 12, by - 7), (cx + 11, by - 7))
        D.line(surf, (140, 105, 70), (cx - 10, by - 4), (cx + 8, by - 4))
        D.ellipse(surf, (150, 115, 75), (cx + 9, by - 7, 5, 7))
        D.ellipse(surf, (40, 30, 24), (cx + 10, by - 6, 3, 5))
        for k in range(4):
            surf.set_at((cx - 9 + k * 5, by - 8), (90, 150, 60))
    elif tid == "statue":
        D.rect(surf, (120, 120, 130), (cx - 6, by - 5, 12, 5))
        D.rect(surf, (150, 150, 160), (cx - 6, by - 5, 12, 1))
        gold = (220, 180, 70)
        D.ellipse(surf, gold, (cx - 6, by - 11, 11, 5))
        D.polygon(surf, gold, [(cx - 6, by - 9), (cx - 9, by - 12), (cx - 9, by - 6)])
        D.line(surf, gold, (cx - 1, by - 11), (cx + 1, by - 14))
        surf.set_at((cx + 3, by - 10), (40, 30, 20))
        D.line(surf, gold, (cx + 5, by - 8), (cx + 8, by - 7))
    elif tid == "geyser":
        D.ellipse(surf, (100, 96, 90), (cx - 8, by - 5, 16, 8))
        D.ellipse(surf, (60, 56, 52), (cx - 2, by - 5, 4, 2))
        for k in range(4):
            yy = by - 6 - ((t * 25 + k * 5) % 20)
            surf.set_at((cx + int(math.sin(t * 3 + k) * 1.5), int(yy)), (220, 240, 255))
    elif tid == "duck":
        bob = int(math.sin(t * 2) > 0.3)
        D.ellipse(surf, (250, 210, 40), (cx - 5, by - 4 + bob, 10, 5))
        D.circle(surf, (250, 210, 40), (cx + 3, by - 6 + bob), 3)
        surf.set_at((cx + 4, by - 7 + bob), (20, 20, 20))
        D.line(surf, (240, 120, 30), (cx + 6, by - 6 + bob), (cx + 7, by - 6 + bob))
        D.line(surf, (220, 180, 30), (cx - 3, by - 3 + bob), (cx, by - 3 + bob))
    elif tid == "shells":
        for dx, col in ((-5, (250, 200, 210)), (0, (250, 240, 225)), (5, (240, 170, 140))):
            D.ellipse(surf, col, (cx + dx - 3, by - 4, 6, 4))
            D.line(surf, dark(col, 0.75), (cx + dx, by - 4), (cx + dx, by - 1))
            surf.set_at((cx + dx - 2, by - 2), dark(col, 0.75))
            surf.set_at((cx + dx + 2, by - 2), dark(col, 0.75))
    elif tid == "bamboo":
        for dx, h in ((-3, 20), (1, 26), (4, 16)):
            sway = int(math.sin(t * 0.8 + dx) * (1 if h > 18 else 0))
            D.line(surf, (110, 170, 70), (cx + dx, by), (cx + dx + sway, by - h))
            for yy in range(by - 5, by - h, -5):
                surf.set_at((cx + dx, yy), (70, 120, 50))
            D.line(surf, (90, 160, 60), (cx + dx + sway, by - h + 2), (cx + dx + sway + 3, by - h))
    elif tid == "bottle":
        D.polygon(surf, (150, 210, 180), [(cx - 7, by - 1), (cx + 3, by - 5), (cx + 5, by - 1), (cx - 5, by + 1)])
        D.line(surf, (130, 190, 160), (cx + 3, by - 4), (cx + 7, by - 6))
        surf.set_at((cx + 8, by - 6), (150, 100, 60))
        D.line(surf, (240, 230, 200), (cx - 4, by - 1), (cx + 1, by - 3))
        surf.set_at((cx - 5, by - 2), (220, 240, 235))
    elif tid == "desk":
        wood, dk = (170, 120, 70), (110, 75, 45)
        D.rect(surf, wood, (cx - 7, by - 9, 12, 2))
        D.line(surf, dk, (cx - 6, by - 7), (cx - 6, by))
        D.line(surf, dk, (cx + 3, by - 7), (cx + 3, by))
        D.rect(surf, dk, (cx - 6, by - 7, 10, 2))
        D.circle(surf, (200, 30, 40), (cx + 1, by - 11), 1)
        surf.set_at((cx + 1, by - 13), (70, 160, 60))
        surf.set_at((cx - 4, by - 10), (250, 250, 240))
        surf.set_at((cx - 3, by - 10), (250, 250, 240))
        D.rect(surf, (90, 110, 160), (cx + 6, by - 6, 4, 2))
        D.line(surf, (60, 70, 110), (cx + 9, by - 10), (cx + 9, by))
        D.line(surf, (60, 70, 110), (cx + 6, by - 4), (cx + 6, by))
    elif tid == "snail":
        D.circle(surf, (210, 150, 100), (cx, by - 7), 7)
        D.circle(surf, (180, 120, 80), (cx, by - 7), 4)
        D.circle(surf, (210, 150, 100), (cx + 1, by - 7), 2)
        D.rect(surf, (90, 60, 40), (cx - 6, by - 4, 3, 4))
        surf.set_at((cx + 4, by - 10), (255, 240, 150))
        surf.set_at((cx + 5, by - 10), (255, 240, 150))
    elif tid == "crystal":
        hue = t * 0.6
        for k, (dx, h) in enumerate(((-3, 8), (0, 13), (3, 9), (5, 5))):
            a = hue + k * 0.8
            col = (int(170 + 80 * math.sin(a)), int(170 + 80 * math.sin(a + 2.1)), int(170 + 80 * math.sin(a + 4.2)))
            D.polygon(surf, col, [(cx + dx - 1, by), (cx + dx, by - h), (cx + dx + 2, by - h + 2), (cx + dx + 2, by)])
            surf.set_at((cx + dx, by - h + 2), (255, 255, 255))
    elif tid == "lighthouse":
        for k in range(5):
            D.rect(surf, (220, 50, 50) if k % 2 == 0 else (245, 245, 245), (cx - 3 + k // 3, by - 4 - k * 4, 6 - (k // 3) * 2, 4))
        D.rect(surf, (60, 60, 70), (cx - 2, by - 24, 4, 3))
        on = int(t * 1.5) % 2
        D.rect(surf, (255, 240, 140) if on else (180, 160, 90), (cx - 1, by - 23, 2, 1))
        if on:
            for k in range(2, 8):
                surf.set_at((cx + 1 + k, by - 23 - k // 3), (255, 245, 180))
        D.polygon(surf, (180, 40, 40), [(cx - 3, by - 24), (cx, by - 27), (cx + 3, by - 24)])
    elif tid == "fossil":
        bone = (235, 230, 210)
        D.line(surf, bone, (cx - 9, by - 2), (cx + 6, by - 2))
        for k in range(-7, 6, 3):
            D.line(surf, bone, (cx + k, by - 5), (cx + k, by))
        D.circle(surf, bone, (cx + 8, by - 3), 3)
        surf.set_at((cx + 9, by - 4), (60, 50, 40))
        D.polygon(surf, bone, [(cx - 9, by - 2), (cx - 13, by - 6), (cx - 13, by + 1)])
    elif tid == "conch":
        D.polygon(surf, (250, 190, 170), [(cx - 9, by), (cx + 6, by - 9), (cx + 9, by - 3), (cx + 2, by)])
        D.line(surf, (220, 140, 120), (cx - 6, by - 1), (cx + 6, by - 7))
        D.line(surf, (255, 225, 210), (cx + 3, by - 6), (cx + 8, by - 3))
        surf.set_at((cx + 7, by - 8), (200, 120, 110))
    elif tid == "jackolantern":
        D.ellipse(surf, (226, 116, 24), (cx - 7, by - 10, 14, 10))
        D.line(surf, (196, 96, 20), (cx - 2, by - 9), (cx - 2, by - 2))
        D.line(surf, (196, 96, 20), (cx + 2, by - 9), (cx + 2, by - 2))
        D.rect(surf, (70, 120, 40), (cx - 1, by - 13, 2, 3))
        glow = lerp((255, 180, 40), (255, 245, 150), 0.5 + 0.5 * math.sin(t * 7))
        for p in ((cx - 4, by - 7), (cx - 3, by - 7), (cx + 3, by - 7), (cx + 4, by - 7), (cx - 4, by - 6), (cx + 3, by - 6)):
            surf.set_at(p, glow)
        for x in range(cx - 4, cx + 5):
            surf.set_at((x, by - 4 + (1 if x % 2 else 0)), glow)
    elif tid == "cauldron":
        D.ellipse(surf, (40, 40, 48), (cx - 8, by - 9, 16, 9))
        D.rect(surf, (40, 40, 48), (cx - 7, by - 10, 14, 3))
        D.line(surf, (70, 70, 80), (cx - 8, by - 10), (cx + 7, by - 10))
        brew = lerp((90, 210, 80), (150, 250, 110), 0.5 + 0.5 * math.sin(t * 5))
        D.line(surf, brew, (cx - 6, by - 9), (cx + 5, by - 9))
        surf.set_at((cx - 3 + int(t * 3) % 7, by - 10), (180, 255, 150))
        surf.set_at((cx - 6, by), (30, 30, 36))
        surf.set_at((cx + 5, by), (30, 30, 36))
    elif tid == "skeleton":
        bone, dk = (232, 228, 214), (170, 165, 150)
        D.line(surf, bone, (cx - 8, by - 4), (cx + 4, by - 4))
        for k in range(4):
            x = cx - 6 + k * 3
            D.line(surf, bone, (x, by - 7), (x, by - 1))
        D.polygon(surf, bone, [(cx + 4, by - 7), (cx + 9, by - 5), (cx + 4, by - 3)])
        surf.set_at((cx + 6, by - 5), (40, 30, 30))
        jaw = 1 if extra > 0 else 0
        D.line(surf, dk, (cx + 5, by - 2 + jaw), (cx + 9, by - 3 + jaw))
        D.polygon(surf, dk, [(cx - 8, by - 4), (cx - 11, by - 7), (cx - 11, by - 1)])
    elif tid == "candycorn":
        for i, (dx, h) in enumerate(((-6, 0), (-1, 1), (4, 0), (-3, 3), (2, 3))):
            x, y = cx + dx, by - h
            surf.set_at((x, y - 3), (255, 250, 235))
            D.line(surf, (255, 170, 30), (x - 1, y - 2), (x + 1, y - 2))
            D.line(surf, (255, 215, 60), (x - 1, y - 1), (x + 1, y - 1))
            D.line(surf, (255, 215, 60), (x - 1, y), (x + 1, y))
    elif tid == "anchor":
        iron, dk = (110, 110, 120), (70, 70, 80)
        D.line(surf, iron, (cx, by - 14), (cx, by - 2))
        D.line(surf, iron, (cx - 3, by - 12), (cx + 3, by - 12))
        D.circle(surf, iron, (cx, by - 15), 2, 1)
        D.arc(surf, iron, (cx - 6, by - 7, 12, 8), 3.3, 6.1)
        D.line(surf, dk, (cx - 6, by - 4), (cx - 7, by - 6))
        D.line(surf, dk, (cx + 6, by - 4), (cx + 7, by - 6))
        for k in range(5):
            surf.set_at((cx + 2 + k * 2, by - 16 - k), (90, 80, 70) if k % 2 else (130, 110, 90))
        surf.set_at((cx - 1, by - 9), (160, 90, 60))
    elif tid == "sub":
        y_ = by - 6 + int(math.sin(t * 1.5) > 0.5)
        D.ellipse(surf, (240, 200, 40), (cx - 9, y_ - 3, 18, 7))
        D.rect(surf, (230, 180, 30), (cx - 2, y_ - 6, 5, 4))
        D.line(surf, (90, 90, 100), (cx + 1, y_ - 9), (cx + 1, y_ - 6))
        for k in (-4, 0, 4):
            surf.set_at((cx + k, y_), (120, 200, 240))
        D.line(surf, (200, 150, 30), (cx - 10, y_ - 2), (cx - 10, y_ + 2))
        if int(t * 2) % 2:
            surf.set_at((cx + 9, y_), (255, 250, 200))
    elif tid == "wheel":
        wood, dk = (150, 110, 70), (100, 70, 45)
        D.line(surf, dk, (cx - 7, by), (cx - 4, by - 8))
        D.line(surf, dk, (cx + 7, by), (cx + 4, by - 8))
        D.circle(surf, wood, (cx, by - 9), 7, 1)
        for k in range(6):
            a = t * 0.8 + k * math.pi / 3
            D.line(surf, wood, (cx, by - 9), (cx + int(math.cos(a) * 7), by - 9 + int(math.sin(a) * 7)))
        D.circle(surf, dk, (cx, by - 9), 1)
    elif tid == "mushrooms":
        glow = 0.5 + 0.5 * math.sin(t * 1.8)
        for dx, h, col in ((-5, 6, (120, 220, 255)), (1, 9, (180, 140, 255)), (6, 5, (120, 255, 190))):
            D.line(surf, (230, 230, 220), (cx + dx, by), (cx + dx, by - h))
            D.ellipse(surf, lerp(dark(col, 0.7), col, glow), (cx + dx - 3, by - h - 2, 7, 4))
            surf.set_at((cx + dx - 1, by - h - 1), (255, 255, 255))
    elif tid == "lavalamp":
        D.rect(surf, (150, 150, 160), (cx - 3, by - 3, 7, 3))
        D.polygon(surf, (90, 40, 110), [(cx - 2, by - 3), (cx - 3, by - 15), (cx + 3, by - 15), (cx + 2, by - 3)])
        D.rect(surf, (150, 150, 160), (cx - 2, by - 17, 5, 2))
        for k in range(3):
            yy = by - 5 - int((t * 3 + k * 4) % 10)
            D.circle(surf, (255, 120, 80), (cx + (k % 2) - (k == 2), yy), 1)
    elif tid == "pagoda":
        red, roof = (200, 60, 50), (60, 120, 90)
        D.rect(surf, red, (cx - 4, by - 7, 8, 7))
        D.rect(surf, (40, 30, 30), (cx - 1, by - 5, 3, 5))
        D.polygon(surf, roof, [(cx - 8, by - 7), (cx, by - 11), (cx + 8, by - 7)])
        D.rect(surf, red, (cx - 3, by - 14, 6, 3))
        D.polygon(surf, roof, [(cx - 6, by - 14), (cx, by - 18), (cx + 6, by - 14)])
        D.line(surf, (230, 190, 60), (cx, by - 18), (cx, by - 21))
    elif tid == "organ":
        for i, h in enumerate((8, 12, 16, 12, 8)):
            x = cx - 7 + i * 3
            D.rect(surf, (200, 180, 120), (x, by - h, 2, h))
            surf.set_at((x, by - h), (250, 240, 200))
            if int(t * 3 + i) % 4 == 0:
                surf.set_at((x, by - h - 2 - int(t * 5) % 3), (210, 240, 255))
        D.rect(surf, (120, 80, 50), (cx - 8, by - 3, 16, 3))
    elif tid == "icecave":
        D.polygon(surf, (170, 220, 245), [(cx - 12, by), (cx - 8, by - 11), (cx + 1, by - 14), (cx + 9, by - 10), (cx + 12, by)])
        D.ellipse(surf, (40, 70, 110), (cx - 5, by - 8, 10, 10))
        D.line(surf, (240, 250, 255), (cx - 8, by - 11), (cx + 1, by - 14))
        for k in (-7, -3, 4, 8):
            surf.set_at((cx + k, by - 10 + abs(k) // 3), (255, 255, 255))
    elif tid == "jellies":
        for dx, ph in ((-5, 0), (5, 2)):
            D.line(surf, (110, 90, 70), (cx + dx, by), (cx + dx, by - 14))
            glow = 0.5 + 0.5 * math.sin(t * 2 + ph)
            col = lerp((200, 120, 220), (255, 200, 250), glow)
            D.ellipse(surf, col, (cx + dx - 3, by - 19, 7, 5))
            for k in (-2, 0, 2):
                surf.set_at((cx + dx + k, by - 13 + int(math.sin(t * 3 + k) > 0)), col)
    elif tid == "throne":
        pearl, gold = (240, 235, 245), (230, 190, 70)
        D.rect(surf, gold, (cx - 6, by - 6, 12, 6))
        D.rect(surf, (170, 60, 90), (cx - 5, by - 5, 10, 2))
        D.rect(surf, gold, (cx - 6, by - 16, 12, 10))
        D.rect(surf, (170, 60, 90), (cx - 4, by - 14, 8, 7))
        for k in range(-6, 7, 3):
            D.circle(surf, pearl, (cx + k, by - 17), 1)
        surf.set_at((cx, by - 19), (255, 255, 255))
    elif tid == "crystalcave":
        D.polygon(surf, (90, 80, 110), [(cx - 12, by), (cx - 8, by - 12), (cx + 6, by - 14), (cx + 12, by)])
        D.ellipse(surf, (30, 24, 44), (cx - 5, by - 8, 10, 10))
        glow = 0.5 + 0.5 * math.sin(t * 2)
        for dx, h in ((-9, 6), (-6, 9), (7, 8), (10, 5)):
            col = lerp((170, 110, 240), (230, 190, 255), glow)
            D.polygon(surf, col, [(cx + dx - 1, by), (cx + dx, by - h), (cx + dx + 2, by)])
    elif tid == "hoard":
        gold, dk = (250, 200, 60), (200, 150, 30)
        D.ellipse(surf, dk, (cx - 11, by - 7, 22, 9))
        D.ellipse(surf, gold, (cx - 9, by - 9, 18, 7))
        for k in range(7):
            x = cx - 8 + (k * 5) % 16
            surf.set_at((x, by - 8 + k % 3), (255, 245, 170))
        if int(t * 3) % 2:
            surf.set_at((cx + 3, by - 10), (255, 255, 255))
        D.rect(surf, (230, 60, 80), (cx + 5, by - 6, 2, 2))
    elif tid == "trophy":
        gold, dk = (250, 205, 70), (190, 140, 30)
        D.rect(surf, (90, 70, 50), (cx - 5, by - 3, 10, 3))
        D.rect(surf, dk, (cx - 1, by - 7, 3, 4))
        D.polygon(surf, gold, [(cx - 5, by - 15), (cx + 5, by - 15), (cx + 3, by - 8), (cx - 3, by - 8)])
        D.line(surf, gold, (cx - 7, by - 14), (cx - 5, by - 11))
        D.line(surf, gold, (cx + 7, by - 14), (cx + 5, by - 11))
        D.line(surf, (110, 70, 20), (cx - 2, by - 12), (cx + 2, by - 12))
        surf.set_at((cx - 3, by - 14), (255, 250, 210))
    elif tid == "tower":
        stone, dk = (150, 170, 190), (110, 130, 150)
        D.rect(surf, dk, (cx - 4, by - 24, 8, 24))
        D.rect(surf, stone, (cx - 3, by - 24, 3, 24))
        for k in range(4):
            D.rect(surf, (40, 60, 80), (cx - 1, by - 20 + k * 5, 2, 2))
        D.polygon(surf, (90, 160, 200), [(cx - 6, by - 24), (cx, by - 30), (cx + 6, by - 24)])
    elif tid == "temple":
        stone, dk = (190, 180, 150), (140, 130, 105)
        D.rect(surf, dk, (cx - 12, by - 3, 24, 3))
        for dx in (-9, -4, 1, 6):
            D.rect(surf, stone, (cx + dx, by - 14, 3, 11))
        D.rect(surf, dk, (cx - 12, by - 16, 24, 2))
        D.polygon(surf, stone, [(cx - 12, by - 16), (cx, by - 22), (cx + 12, by - 16)])
        D.line(surf, (80, 140, 70), (cx - 9, by - 14), (cx - 8, by - 8))
    elif tid == "kraken":
        purple, light_ = (170, 80, 160), (220, 140, 210)
        for k in range(14):
            sway = math.sin(t * 1.5 + k * 0.35) * (k * 0.4)
            x = int(cx + sway)
            D.circle(surf, purple, (x, by - k * 2), max(1, 3 - k // 5))
            if k % 3 == 1:
                surf.set_at((x + 2, by - k * 2), light_)
    elif tid == "rainbowfall":
        D.polygon(surf, (120, 120, 130), [(cx - 8, by), (cx - 5, by - 9), (cx + 4, by - 10), (cx + 8, by)])
        top = max(4, by - 49)
        for y in range(top, by - 10):
            k = (y - int(t * 20)) % 6
            for i, dx in enumerate((-2, -1, 0, 1, 2)):
                r, g_, b = colorsys.hsv_to_rgb(((dx + 2) / 6 + k * 0.02) % 1, 0.55, 1.0)
                surf.set_at((cx + dx, y), (int(r * 255), int(g_ * 255), int(b * 255)))
    elif tid == "moonpool":
        glow = 0.5 + 0.5 * math.sin(t * 1.2)
        D.ellipse(surf, (110, 110, 130), (cx - 11, by - 4, 22, 6))
        D.ellipse(surf, lerp((90, 120, 200), (190, 210, 255), glow), (cx - 8, by - 3, 16, 3))
        D.circle(surf, (240, 240, 210), (cx + 2, by - 2), 1)
        for k in range(3):
            a = t * 2 + k * 2.1
            surf.set_at((cx + int(math.cos(a) * 9), by - 6 - int(abs(math.sin(a)) * 5)), (220, 230, 255))
    elif tid == "starcoral":
        for dx, h, lean in ((-4, 12, -2), (0, 17, 1), (4, 11, 2)):
            D.line(surf, (60, 50, 110), (cx + dx, by), (cx + dx + lean, by - h))
            tw = int(t * 4 + dx) % 3
            col = (255, 250, 200) if tw == 0 else (200, 190, 255)
            surf.set_at((cx + dx + lean, by - h), col)
            surf.set_at((cx + dx + lean - 1, by - h), col)
            surf.set_at((cx + dx + lean // 2, by - h // 2), (230, 220, 255))
    elif tid == "galaxyorb":
        D.rect(surf, (120, 100, 80), (cx - 4, by - 2, 8, 2))
        D.circle(surf, (40, 30, 80), (cx, by - 8), 6)
        for k in range(6):
            a = t * 1.5 + k * 1.05
            r = 1 + k % 4
            surf.set_at((cx + int(math.cos(a) * r), by - 8 + int(math.sin(a) * r * 0.7)),
                        (255, 240, 200) if k % 2 else (200, 120, 230))
        D.circle(surf, (180, 200, 255), (cx, by - 8), 6, 1)
        surf.set_at((cx - 3, by - 12), (255, 255, 255))
    elif tid == "fountain":
        stone, dk = (200, 200, 210), (150, 150, 165)
        D.rect(surf, dk, (cx - 9, by - 4, 18, 4))
        D.rect(surf, stone, (cx - 9, by - 4, 18, 1))
        D.rect(surf, dk, (cx - 1, by - 14, 3, 10))
        D.rect(surf, stone, (cx - 5, by - 15, 11, 2))
        D.rect(surf, dk, (cx, by - 19, 1, 4))
        for k in range(6):
            a = (t * 2 + k / 6) % 1
            for side in (-1, 1):
                x = cx + side * int(a * 7)
                y = by - 19 + int(a * a * 14) - int(math.sin(a * 3.14) * 3)
                surf.set_at((x, y), (200, 235, 255))


TOY_SIZE = {"jackolantern": (16, 14), "cauldron": (18, 12), "skeleton": (24, 9), "candycorn": (14, 6),
            "ball": (8, 8), "airstone": (8, 5), "cave": (22, 14), "sunflower": (12, 24),
            "marimo": (10, 10), "chest": (14, 14), "hammock": (16, 18), "castle": (22, 24),
            "clam": (14, 10), "ship": (30, 26), "coral": (16, 20), "diver": (12, 26),
            "apple": (10, 12), "lilypad": (16, 6), "waterfall": (16, 50), "volcano": (20, 12),
            "log": (26, 10), "statue": (18, 16), "geyser": (18, 10), "fountain": (20, 22),
            "duck": (14, 10), "shells": (18, 6), "bamboo": (12, 28), "bottle": (18, 8), "desk": (20, 14),
            "snail": (16, 16), "crystal": (14, 15), "lighthouse": (16, 28), "fossil": (24, 8), "conch": (20, 12),
            "crystalcave": (26, 16), "hoard": (24, 12), "trophy": (16, 18), "tower": (14, 32), "temple": (26, 24),
            "kraken": (12, 30), "rainbowfall": (18, 50), "moonpool": (24, 12), "starcoral": (14, 20),
            "galaxyorb": (16, 16),
            "anchor": (18, 22), "sub": (22, 14), "wheel": (18, 18), "mushrooms": (16, 14), "lavalamp": (10, 20),
            "pagoda": (18, 24), "organ": (18, 20), "icecave": (26, 16), "jellies": (16, 22), "throne": (16, 22)}


def toy_icon(tid, scale=2):
    key = ("toy", tid, scale)
    if key not in _cache:
        w, h = TOY_SIZE[tid]
        s = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        draw_toy(s, tid, (w + 4) // 2, h + 2, 0.5)
        _cache[key] = pygame.transform.scale(s, ((w + 4) * scale, (h + 4) * scale))
    return _cache[key]


def food_icon(color, scale=3):
    key = ("food", color, scale)
    if key not in _cache:
        s = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.rect(s, dark(color, 0.6), (1, 2, 6, 5))
        pygame.draw.rect(s, color, (2, 2, 4, 4))
        s.set_at((3, 3), light(color, 0.6))
        s.set_at((1, 1), color)
        s.set_at((6, 1), color)
        _cache[key] = pygame.transform.scale(s, (8 * scale, 8 * scale))
    return _cache[key]


UPGRADE_GLYPH = {
    "tank": [" XXXXXX ", "X......X", "X..o...X", "X....o.X", "X......X", "X~~~~~~X", " XXXXXX "],
    "filter": [" XXXX ", "XoooX ", "XoooXX", "XoooX.", "XoooX ", " XXXX "],
    "hands": ["  X X ", " XXXXX", "XXXXXX", "XXXXXX", " XXXX ", "  XX  "],
    "magnet": ["XX  XX", "XX  XX", "XX  XX", "XX  XX", " XXXX ", "  XX  "],
    "bubbler": ["  o  o", " o  o ", "  oo  ", " o    ", "XXXXXX", "XXXXXX"],
    "heater": [" XX ", " XX ", " XX ", " XX ", "XXXX", "XooX", " XX "],
    "light": [" XXXX ", "XooooX", "XooooX", " XXXX ", " o  o ", "o    o"],
    "feeder": ["XXXXXX", "X.oo.X", "XXXXXX", "  XX  ", "  o   ", "   o  "],
    "care": [" XXXX ", "X o  X", "X o  X", "X ooox", "X    X", " XXXX "],
    "conditioner": ["  X   ", " XoX  ", " XoX  ", "XoooX ", "XoooX ", " XXX  "],
    "plants": ["  X  X", " XX XX", "X X X ", "  XX  ", "  X   ", " XXX  "],
    "pump": [" XXXX ", "XooooX", "Xo..oX", "Xo..oX", "XooooX", " X  X "],
    "jar": [" XXXX ", "X....X", "X....X", "XooooX", "XooooX", " XXXX "],
    "hatchery": ["      ", " oo o ", "oXXoXX", "oXXoXX", " oo o ", "XXXXXX"],
    "lucky": [" X X  ", "XoXoX ", " XXX  ", "XoXoX ", " X X X", "    X "],
    "autonest": [" o  o ", "oXX oX", "oXX oX", " o  o ", "XXXXXX", " X  X "],
    "abyss": ["XXXXXX", "X....X", "XoooXX", "X....X", "XoooXX", "XXXXXX"],
    "school": ["      ", " XX   ", "XoX XX", " XXXoX", "   XX ", "      "],
    "polish": ["  X   ", " XoX  ", "XoooX ", " XoX  ", "  X  X", "    XX"],
    "current": ["      ", "XX  XX", " XXXX ", "      ", "XX  XX", " XXXX "],
    "timecrystal": [" XXXX ", "  XX  ", " XooX ", " XooX ", "  XX  ", " XXXX "],
    "bait": ["   X  ", "   X  ", "   X  ", "X  X  ", "XooX  ", " XX   "],
    "infinity": ["      ", " X  X ", "XoXXoX", "XoXXoX", " X  X ", "      "],
    "rub": [" X X X", " X X X", "XXXXXX", "XXXXXX", "o XXX ", " o  o "],
    "ghostglow": [" XXXX ", "XXXXXX", "X.XX.X", "XXXXXX", "XXXXXX", "X X X "],
    "spooky": [" XXX  ", "XXXXX ", "X.X.X ", "XXXXX ", " X X o", "    oo"],
    "treats": ["  X   ", " XXX  ", "XoXoX ", "XXXXX ", "XoXoX ", " XXX  "],
}
UPGRADE_COL = {"tank": (120, 200, 255), "filter": (150, 160, 180), "hands": (250, 200, 170),
               "magnet": (230, 80, 80), "bubbler": (130, 210, 240), "heater": (240, 120, 60),
               "light": (250, 230, 120), "feeder": (180, 140, 90), "care": (190, 160, 240),
               "conditioner": (110, 200, 250), "plants": (90, 190, 90), "pump": (140, 170, 200),
               "jar": (255, 210, 80), "hatchery": (250, 230, 200), "lucky": (110, 210, 110),
               "abyss": (60, 90, 170), "school": (120, 200, 230), "polish": (240, 240, 255),
               "current": (90, 170, 230), "timecrystal": (200, 140, 255), "bait": (230, 120, 90),
               "infinity": (255, 180, 230), "autonest": (200, 170, 250),
               "rub": (255, 170, 210), "ghostglow": (170, 250, 190), "spooky": (235, 232, 240),
               "treats": (255, 160, 50)}


def upgrade_icon(uid, scale=4):
    key = ("up", uid, scale)
    if key not in _cache:
        g = UPGRADE_GLYPH[uid]
        w = max(len(r) for r in g)
        s = pygame.Surface((w, len(g)), pygame.SRCALPHA)
        c = UPGRADE_COL[uid]
        for y, row in enumerate(g):
            for x, ch in enumerate(row):
                if ch in "Xx":
                    s.set_at((x, y), (*c, 255))
                elif ch == "o":
                    s.set_at((x, y), (*light(c, 0.6), 255))
                elif ch in ".~":
                    s.set_at((x, y), (*dark(c, 0.5), 255))
        _cache[key] = pygame.transform.scale(s, (w * scale, len(g) * scale))
    return _cache[key]


def pearl_icon(scale=3):
    key = ("pearl", scale)
    if key not in _cache:
        s = pygame.Surface((7, 7), pygame.SRCALPHA)
        pygame.draw.circle(s, (230, 225, 240), (3, 3), 3)
        s.set_at((2, 2), (255, 255, 255))
        s.set_at((4, 5), (190, 180, 210))
        _cache[key] = pygame.transform.scale(s, (7 * scale, 7 * scale))
    return _cache[key]


SCALE_GLYPH = [
    "..XXXXX..",
    ".XooooOX.",
    "XohhoooOX",
    "XohoooooX",
    "XoooooooX",
    "XO.ooo.OX",
    ".XOo.oOX.",
    "..XOoOX..",
    "...XOX...",
    "....X....",
]


def scale_icon(scale=3):
    """the currency: a golden fish scale"""
    key = ("scale", scale)
    if key not in _cache:
        pal = {"X": (150, 90, 20), "o": (250, 200, 60), "O": (215, 150, 35), "h": (255, 248, 200),
               ".": (235, 175, 45)}
        w, h = len(SCALE_GLYPH[0]), len(SCALE_GLYPH)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y, row in enumerate(SCALE_GLYPH):
            inside = [i for i, ch in enumerate(row) if ch == "X"]
            for x, ch in enumerate(row):
                if ch == "." and not (inside and inside[0] < x < inside[-1]):
                    continue
                s.set_at((x, y), (*pal[ch], 255))
        k = max(1, scale * 2 // 3)
        _cache[key] = pygame.transform.scale(s, (w * k, h * k))
    return _cache[key]


def bubble_icon(scale=3):
    key = ("bub", scale)
    if key not in _cache:
        s = pygame.Surface((7, 7), pygame.SRCALPHA)
        pygame.draw.circle(s, (170, 225, 255), (3, 3), 3, 1)
        s.set_at((2, 2), (255, 255, 255))
        _cache[key] = pygame.transform.scale(s, (7 * scale, 7 * scale))
    return _cache[key]


def draw_jar(surf, cx, by, frac, t):
    """glass jar on the sand; frac = how full (0..1)"""
    cx, by = int(cx), int(by)
    glass, rim = (190, 225, 240), (230, 245, 255)
    h = 12
    fill = int(round((h - 3) * frac))
    if fill:
        gold = (255, 205, 60) if frac < 1 or int(t * 4) % 2 else (255, 240, 150)
        pygame.draw.rect(surf, gold, (cx - 3, by - 1 - fill, 7, fill))
        for k in range(0, fill, 3):
            surf.set_at((cx - 2 + k % 5, by - 2 - k), (255, 240, 170))
    pygame.draw.line(surf, glass, (cx - 4, by - h + 2), (cx - 4, by - 1))
    pygame.draw.line(surf, glass, (cx + 4, by - h + 2), (cx + 4, by - 1))
    pygame.draw.line(surf, glass, (cx - 3, by), (cx + 3, by))
    pygame.draw.line(surf, rim, (cx - 3, by - h + 1), (cx + 3, by - h + 1))
    pygame.draw.rect(surf, (150, 100, 60), (cx - 2, by - h - 1, 5, 2))
    surf.set_at((cx - 3, by - h + 4), (255, 255, 255))
    if frac >= 1:
        for k in range(3):
            a = t * 3 + k * 2.1
            surf.set_at((cx + int(math.cos(a) * 6), by - 6 + int(math.sin(a) * 6)), (255, 240, 140))


def draw_nest(surf, cx, by, eggs, t):
    """eggs: list of (rgb colour, ready)"""
    cx, by = int(cx), int(by)
    pygame.draw.ellipse(surf, (150, 120, 80), (cx - 9, by - 3, 18, 5))
    pygame.draw.ellipse(surf, (120, 95, 60), (cx - 7, by - 2, 14, 3))
    for i, (col, ready) in enumerate(eggs):
        x = cx - 5 + i * 4
        wob = int(math.sin(t * 12 + i) * 1) if ready else 0
        pygame.draw.ellipse(surf, col, (x - 1 + wob, by - 6, 4, 5))
        surf.set_at((x + wob, by - 5), (255, 255, 255))
        if ready and int(t * 3 + i) % 2:
            surf.set_at((x + 1 + wob, by - 8), (255, 240, 140))
    if not eggs:
        surf.set_at((cx, by - 2), (170, 140, 100))


def draw_visitor(surf, vid, x, y, right, t):
    """little guests that wander through the tank"""
    x, y = int(x), int(y)
    d = 1 if right else -1
    step = int(t * 8) % 2
    if vid == "crab":
        shell, body = (200, 140, 90), (220, 90, 60)
        pygame.draw.circle(surf, shell, (x - 2 * d, y - 3), 3)
        surf.set_at((x - 2 * d, y - 3), (150, 100, 60))
        pygame.draw.rect(surf, body, (x - 1 if d > 0 else x - 2, y - 2, 4, 2))
        surf.set_at((x + 3 * d, y - 3), (240, 110, 70))
        surf.set_at((x + 3 * d, y - 4), (20, 20, 20))
        for k in range(3):
            surf.set_at((x - 1 + k + step * d, y), body)
    elif vid == "shrimp":
        red = (230, 60, 50)
        for k in range(5):
            surf.set_at((x - k * d, y - 2 + (1 if k in (0, 4) else 0)), red if k % 2 else (250, 110, 90))
        surf.set_at((x + d, y - 2), (20, 20, 20))
        surf.set_at((x + 2 * d, y - 3), (250, 150, 130))
        surf.set_at((x + 3 * d, y - 4), (250, 150, 130))
        surf.set_at((x - 1 * d, y - 1 + step), red)
        surf.set_at((x - 3 * d, y - 1 + 1 - step), red)
    elif vid == "turtle":
        shell, skin = (90, 110, 60), (140, 150, 90)
        pygame.draw.ellipse(surf, shell, (x - 5, y - 3, 10, 5))
        pygame.draw.line(surf, (60, 80, 40), (x - 3, y - 2), (x + 3, y - 2))
        pygame.draw.circle(surf, skin, (x + 6 * d, y - 1), 2)
        surf.set_at((x + 7 * d, y - 2), (20, 20, 20))
        surf.set_at((x - 4, y + 2 + step), skin)
        surf.set_at((x + 3, y + 2 + 1 - step), skin)
        surf.set_at((x - 6 * d, y), skin)
    elif vid == "axolotl":
        pink, gill = (250, 170, 190), (230, 90, 130)
        pygame.draw.ellipse(surf, pink, (x - 5, y - 2, 10, 4))
        pygame.draw.circle(surf, pink, (x + 5 * d, y - 1), 2)
        for k in (-1, 0, 1):
            surf.set_at((x + 4 * d, y - 3 + k * 2 - (1 if k == 0 else 0)), gill)
        surf.set_at((x + 6 * d, y - 2), (30, 20, 30))
        pygame.draw.line(surf, pink, (x - 5 * d, y), (x - 8 * d, y - 1 + step))
        surf.set_at((x - 2, y + 2), pink)
        surf.set_at((x + 2, y + 2), pink)


_scaled = {}


def scaled(img, k):
    """nearest-neighbour shrink for growing babies (cached per frame + size step)"""
    key = (id(img), k)
    if key not in _scaled:
        if len(_scaled) > 400:
            _scaled.clear()
        w, h = img.get_size()
        _scaled[key] = pygame.transform.scale(img, (max(1, int(w * k)), max(1, int(h * k))))
    return _scaled[key]
