"""Tank codes: turn your tank into a short piece of text a friend can paste in to look at it.
Only what you can see is in it (fish, toys, theme, name). Codes from other people are checked
strictly before use: unknown fish/toys are dropped and everything is size-limited."""
import base64
import json
import re
import zlib

from . import economy as E
from .data import SPECIES_BY_ID, TOYS_BY_ID, THEMES_BY_ID, TOY_MAX_LEVEL, MORPHS_BY_ID

PREFIX = "DA1:"
MAX_FISH = 80
MAX_NAME = 22
MAX_FRIENDS = 30
MAX_CODE = 20000
ONLINE_ID = re.compile(r"^[1-9][0-9]{5}$")


def encode(s):
    fish = []
    for f in s["fish"][:MAX_FISH]:
        fish.append([f["sp"], 1 if f.get("shiny") else 0, list(E.fish_look(f))[:4],
                     f["name"] if f.get("named") else "", int(f.get("lv", 1)), f.get("morph", "")])
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


def _body(text):
    """just the code part of some pasted text"""
    i = (text or "").find(PREFIX)
    if i < 0:
        raise ValueError("no tank code")
    body = ""
    for ch in text[i + len(PREFIX):i + len(PREFIX) + MAX_CODE]:
        if ch.isalnum() or ch in "-_":
            body += ch
        elif ch in " \r\n\t":
            continue
        else:
            break
    return body


def _unpack(text):
    """(the tank's data, just the bytes that held it). Words pasted after the code get ignored."""
    body = _body(text)
    if len(body) % 4 == 1:                 # a stray extra letter can never be part of a real code
        body = body[:-1]
    try:
        packed = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
        dec = zlib.decompressobj()
        raw = dec.decompress(packed, 200000)          # never unpack something huge
        d = json.loads(raw.decode("utf-8"))
    except Exception:
        raise ValueError("damaged tank code")
    return d, packed[:len(packed) - len(dec.unused_data)]


BACKUP = "DAS1:"              # the first backup codes (still read)
BACKUP2 = "DAS2-"             # since then: DAS2-<length>-<data>-<check>, so a cut-off code can be spotted


def _check(data):
    return format(zlib.crc32(data.encode("ascii")) & 0xFFFFF, "05x")


def backup_code(state):
    """the whole save as one piece of text, to keep somewhere safe (the web version's save lives in the browser)"""
    raw = json.dumps(state, separators=(",", ":")).encode("utf-8")
    data = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii").rstrip("=")
    return f"{BACKUP2}{len(data)}-{data}-{_check(data)}"


def backup_problem(text):
    """why a pasted backup code can't be used: '' (it's fine), 'none' (no code in there) or 'cut' (cut short
    or changed, usually because only part of it was copied)"""
    if read_backup(text) is not None:
        return ""
    return "cut" if text and (BACKUP in text or BACKUP2 in text) else "none"


def _read_backup2(text):
    i = text.find(BACKUP2)
    rest = "".join(ch for ch in text[i + len(BACKUP2):] if not ch.isspace())
    parts = rest.split("-")
    if len(parts) < 3 or not parts[0].isdigit():
        return None
    n = int(parts[0])
    joined = "-".join(parts[1:])               # the data itself can contain - (it's URL-safe base64)
    data, check = joined[:n], joined[n + 1:n + 6]
    if len(data) != n or check != _check(data):
        return None
    try:
        raw = zlib.decompressobj().decompress(base64.urlsafe_b64decode(data + "=" * (-n % 4)), 5_000_000)
        s = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    return s if isinstance(s, dict) and isinstance(s.get("fish"), list) and s["fish"] else None


def read_backup(text):
    """a save from a backup code, or None if it isn't one"""
    text = text or ""
    if BACKUP2 in text:
        return _read_backup2(text)
    i = text.find(BACKUP)
    if i < 0:
        return None
    body = ""
    for ch in text[i + len(BACKUP):]:
        if ch.isalnum() or ch in "-_":
            body += ch
        elif not ch.isspace():                 # line breaks inside the code are fine; anything else ends it
            break
    for trim in range(4):                      # words typed after the code: the packed data ignores extra
        part = body[:len(body) - trim]         # bytes, but the letters can misalign the text decoding
        try:
            dec = zlib.decompressobj()
            raw = dec.decompress(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)), 5_000_000)
            s = json.loads(raw.decode("utf-8"))
        except Exception:
            continue
        if isinstance(s, dict) and isinstance(s.get("fish"), list) and s["fish"]:
            return s
    return None


def clean_code(text):
    """the code on its own, exactly as encode() wrote it, so the same tank always matches itself"""
    _, used = _unpack(text)
    return PREFIX + base64.urlsafe_b64encode(used).decode("ascii").rstrip("=")


def clean_friends(s):
    """the saved friends list as it comes out of a save file: keep only what looks right"""
    good = []
    raw = s.get("friends")
    for f in raw if isinstance(raw, list) else []:
        if not (isinstance(f, dict) and isinstance(f.get("code"), str) and f["code"].startswith(PREFIX)
                and len(f["code"]) <= MAX_CODE + len(PREFIX)):
            continue
        one = dict(name=_clean_name(f.get("name", "")) or "Friend", tank=_clean_name(f.get("tank", "")),
                   code=f["code"], fish=_int(f.get("fish"), 0, MAX_FISH, 0), saved=_int(f.get("saved"), 0, 2 ** 40, 0))
        if isinstance(f.get("id"), str) and ONLINE_ID.match(f["id"]):
            one["id"] = f["id"]
        good.append(one)
    s["friends"] = good[:MAX_FRIENDS]
    me = s.get("online")
    if not (isinstance(me, dict) and isinstance(me.get("id"), str) and ONLINE_ID.match(me["id"])
            and isinstance(me.get("key"), str) and re.fullmatch("[0-9a-f]{64}", me["key"])):
        s["online"] = None


def decode(text, settings):
    """a code (anywhere in the text) -> a tank you can look at. Raises ValueError if there isn't a good one."""
    d, _ = _unpack(text)
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
        if len(f) > 5 and f[5] in MORPHS_BY_ID:
            vs["fish"][-1]["morph"] = f[5]
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
