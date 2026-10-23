"""Tank codes: turn your tank into a short piece of text a friend can paste in to look at it.
Only what you can see is in it (fish, toys, theme, name). Codes from other people are checked
strictly before use: unknown fish/toys are dropped and everything is size-limited."""
import base64
import json
import zlib

from . import economy as E
from .data import SPECIES_BY_ID, TOYS_BY_ID, THEMES_BY_ID, TOY_MAX_LEVEL

PREFIX = "DA1:"
MAX_FISH = 80
MAX_NAME = 22


def encode(s):
    fish = []
    for f in s["fish"][:MAX_FISH]:
        fish.append([f["sp"], 1 if f.get("shiny") else 0, list(E.fish_look(f))[:4],
                     f["name"] if f.get("named") else "", int(f.get("lv", 1))])
    d = {"v": 1, "n": s.get("tank_name", ""), "th": s.get("theme", "classic"),
         "pl": E.ulv(s, "plants"), "cd": E.ulv(s, "conditioner"), "f": fish,
         "t": {tid: [v["lv"], round(v.get("x", 0.5), 3)] for tid, v in s["toys"].items()}}
    raw = json.dumps(d, separators=(",", ":")).encode("utf-8")
    return PREFIX + base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii").rstrip("=")


def _clean_name(name):
    from .pixfont import _GLYPHS
    return "".join(ch for ch in str(name)[:MAX_NAME] if ch in _GLYPHS).strip()


def _int(v, lo, hi, default):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


def decode(text, settings):
    """a code (anywhere in the text) -> a tank you can look at. Raises ValueError if there isn't a good one."""
    i = (text or "").find(PREFIX)
    if i < 0:
        raise ValueError("no tank code")
    body = ""
    for ch in text[i + len(PREFIX):i + len(PREFIX) + 20000]:
        if ch.isalnum() or ch in "-_":
            body += ch
        elif ch in " \r\n\t":
            continue
        else:
            break
    try:
        packed = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        dec = zlib.decompressobj()
        raw = dec.decompress(packed, 200000)          # never unpack something huge
        d = json.loads(raw.decode("utf-8"))
    except Exception:
        raise ValueError("damaged tank code")
    if not isinstance(d, dict) or not isinstance(d.get("f"), list):
        raise ValueError("not a tank code")
    vs = E.new_state()
    vs["fish"] = []
    vs["settings"] = dict(settings)
    vs["chill"] = True                                  # no bubbles to pop: just looking
    vs["tank_name"] = _clean_name(d.get("n", ""))
    th = d.get("th")
    vs["theme"] = th if th in THEMES_BY_ID else "classic"
    vs["upgrades"] = {"plants": _int(d.get("pl"), 0, 12, 0), "conditioner": _int(d.get("cd"), 0, 25, 0)}
    for n, f in enumerate(d["f"][:MAX_FISH]):
        if not isinstance(f, list) or len(f) < 5 or f[0] not in SPECIES_BY_ID:
            continue
        look = f[2] if isinstance(f[2], list) and len(f[2]) == 4 else [0, 0, 0, 0]
        look = [_int(look[0], -2, 2, 0), _int(look[1], -1, 1, 0), _int(look[2], 0, 3, 0), _int(look[3], -1, 1, 0)]
        name = _clean_name(f[3])
        vs["fish"].append(dict(uid=n + 1, sp=f[0], name=name or SPECIES_BY_ID[f[0]]["name"], named=bool(name),
                               lv=_int(f[4], 1, 9999, 1), xp=0.0, full=90.0, happy=90.0, shiny=bool(f[1]),
                               look=look))
    toys = d.get("t") if isinstance(d.get("t"), dict) else {}
    for tid, v in list(toys.items())[:len(TOYS_BY_ID)]:
        if tid in TOYS_BY_ID and isinstance(v, list) and len(v) == 2:
            try:
                x = max(0.02, min(0.98, float(v[1])))
            except (TypeError, ValueError):
                x = 0.5
            vs["toys"][tid] = dict(lv=_int(v[0], 1, TOY_MAX_LEVEL, 1), x=x)
    if not vs["fish"]:
        raise ValueError("no fish in that tank code")
    vs["next_uid"] = len(vs["fish"]) + 1
    return vs
