"""Hand-made 5x7 pixel font (with descenders). Drop-in for pygame.font.Font.render/size."""
import pygame

_G = {
    "A": ".XXX. X...X X...X XXXXX X...X X...X X...X",
    "B": "XXXX. X...X X...X XXXX. X...X X...X XXXX.",
    "C": ".XXX. X...X X.... X.... X.... X...X .XXX.",
    "D": "XXXX. X...X X...X X...X X...X X...X XXXX.",
    "E": "XXXXX X.... X.... XXXX. X.... X.... XXXXX",
    "F": "XXXXX X.... X.... XXXX. X.... X.... X....",
    "G": ".XXX. X...X X.... X.XXX X...X X...X .XXXX",
    "H": "X...X X...X X...X XXXXX X...X X...X X...X",
    "I": "XXX .X. .X. .X. .X. .X. XXX",
    "J": "..XXX ...X. ...X. ...X. X..X. X..X. .XX..",
    "K": "X...X X..X. X.X.. XX... X.X.. X..X. X...X",
    "L": "X.... X.... X.... X.... X.... X.... XXXXX",
    "M": "X...X XX.XX X.X.X X.X.X X...X X...X X...X",
    "N": "X...X XX..X X.X.X X..XX X...X X...X X...X",
    "O": ".XXX. X...X X...X X...X X...X X...X .XXX.",
    "P": "XXXX. X...X X...X XXXX. X.... X.... X....",
    "Q": ".XXX. X...X X...X X...X X.X.X X..X. .XX.X",
    "R": "XXXX. X...X X...X XXXX. X.X.. X..X. X...X",
    "S": ".XXXX X.... X.... .XXX. ....X ....X XXXX.",
    "T": "XXXXX ..X.. ..X.. ..X.. ..X.. ..X.. ..X..",
    "U": "X...X X...X X...X X...X X...X X...X .XXX.",
    "V": "X...X X...X X...X X...X X...X .X.X. ..X..",
    "W": "X...X X...X X...X X.X.X X.X.X X.X.X .X.X.",
    "X": "X...X X...X .X.X. ..X.. .X.X. X...X X...X",
    "Y": "X...X X...X .X.X. ..X.. ..X.. ..X.. ..X..",
    "Z": "XXXXX ....X ...X. ..X.. .X... X.... XXXXX",
    "a": ".... .... .XX. ...X .XXX X..X .XXX",
    "b": "X... X... XXX. X..X X..X X..X XXX.",
    "c": "... ... .XX X.. X.. X.. .XX",
    "d": "...X ...X .XXX X..X X..X X..X .XXX",
    "e": ".... .... .XX. X..X XXXX X... .XX.",
    "f": "..X .X. XXX .X. .X. .X. .X.",
    "g": ".... .... .XXX X..X X..X .XXX ...X ...X .XX.",
    "h": "X... X... XXX. X..X X..X X..X X..X",
    "i": "X . X X X X X",
    "j": "..X ... ..X ..X ..X ..X ..X X.X .X.",
    "k": "X... X... X..X X.X. XX.. X.X. X..X",
    "l": "X. X. X. X. X. X. .X",
    "m": "..... ..... XX.X. X.X.X X.X.X X.X.X X.X.X",
    "n": ".... .... XXX. X..X X..X X..X X..X",
    "o": ".... .... .XX. X..X X..X X..X .XX.",
    "p": ".... .... XXX. X..X X..X X..X XXX. X... X...",
    "q": ".... .... .XXX X..X X..X X..X .XXX ...X ...X",
    "r": "... ... X.X XX. X.. X.. X..",
    "s": ".... .... .XXX X... .XX. ...X XXX.",
    "t": ".X. .X. XXX .X. .X. .X. ..X",
    "u": ".... .... X..X X..X X..X X..X .XXX",
    "v": "..... ..... X...X X...X X...X .X.X. ..X..",
    "w": "..... ..... X...X X...X X.X.X X.X.X .X.X.",
    "x": ".... .... X..X X..X .XX. X..X X..X",
    "y": ".... .... X..X X..X X..X X..X .XXX ...X .XX.",
    "z": ".... .... XXXX ...X .XX. X... XXXX",
    "0": ".XXX. X...X X..XX X.X.X XX..X X...X .XXX.",
    "1": ".X. XX. .X. .X. .X. .X. XXX",
    "2": ".XXX. X...X ....X ...X. ..X.. .X... XXXXX",
    "3": "XXXX. ....X ....X .XXX. ....X ....X XXXX.",
    "4": "...X. ..XX. .X.X. X..X. XXXXX ...X. ...X.",
    "5": "XXXXX X.... XXXX. ....X ....X X...X .XXX.",
    "6": ".XXX. X.... X.... XXXX. X...X X...X .XXX.",
    "7": "XXXXX ....X ...X. ..X.. .X... .X... .X...",
    "8": ".XXX. X...X X...X .XXX. X...X X...X .XXX.",
    "9": ".XXX. X...X X...X .XXXX ....X ....X .XXX.",
    " ": "... ... ... ... ... ... ...",
    ".": ". . . . . . X",
    ",": ". . . . . . X X",
    "!": "X X X X X . X",
    "?": ".XXX. X...X ....X ...X. ..X.. ..... ..X..",
    ":": ". . X . . X .",
    ";": ". . X . . X X",
    "'": "X X . . . . .",
    '"': "X.X X.X ... ... ... ... ...",
    "-": "... ... ... XXX ... ... ...",
    "+": "..... ..X.. ..X.. XXXXX ..X.. ..X.. .....",
    "/": "....X ...X. ...X. ..X.. .X... .X... X....",
    "(": ".X X. X. X. X. X. .X",
    ")": "X. .X .X .X .X .X X.",
    "%": "XX..X XX..X ...X. ..X.. .X... X..XX X..XX",
    "#": ".X.X. XXXXX .X.X. .X.X. .X.X. XXXXX .X.X.",
    "=": "..... ..... XXXXX ..... XXXXX ..... .....",
    "<": "...X ..X. .X.. X... .X.. ..X. ...X",
    ">": "X... .X.. ..X. ...X ..X. .X.. X...",
    "_": "..... ..... ..... ..... ..... ..... XXXXX",
    "*": "..... X.X.X .XXX. XXXXX .XXX. X.X.X .....",
    "~": "..... ..... .X..X X.XX. ..... ..... .....",
    "&": ".XX.. X..X. .XX.. .X... X.X.X X..X. .XX.X",
    "[": "XX X. X. X. X. X. XX",
    "]": "XX .X .X .X .X .X XX",
    "$": "..X.. .XXXX X.X.. .XXX. ..X.X XXXX. ..X..",
}
_GLYPHS = {}
for _ch, _rows in _G.items():
    rows = _rows.split(" ") if _ch != " " else ["..."] * 7
    _GLYPHS[_ch] = [r for r in rows]

CELL_H = 9
SPACING = 1


class PixelFont:
    """render(text, antialias_ignored, color) -> Surface, like pygame fonts."""

    def __init__(self, scale=2, shadow=None):
        self.scale = scale
        self.shadow = shadow       # shadow colour or None
        self._cache = {}

    def _glyph(self, ch):
        return _GLYPHS.get(ch) or _GLYPHS["?"]

    def size(self, text):
        w = 0
        for ch in str(text):
            w += len(self._glyph(ch)[0]) + SPACING
        w = max(0, w - SPACING)
        extra = 1 if self.shadow else 0
        return (w + extra) * self.scale, (CELL_H - 1 + extra) * self.scale

    def get_height(self):
        return self.size("A")[1]

    def render(self, text, aa=False, color=(255, 255, 255), bg=None):
        text = str(text)
        key = (text, tuple(color))
        if key in self._cache:
            return self._cache[key]
        s = self.scale
        w, h = self.size(text)
        surf = pygame.Surface((max(1, w), h), pygame.SRCALPHA)
        layers = [(1, self.shadow), (0, color)] if self.shadow else [(0, color)]
        for off, col in layers:
            x = 0
            for ch in text:
                g = self._glyph(ch)
                for ry, row in enumerate(g):
                    for rx, c in enumerate(row):
                        if c == "X":
                            surf.fill(col, ((x + rx + off) * s, (ry + off) * s, s, s))
                x += len(g[0]) + SPACING
        if len(self._cache) > 3000:
            self._cache.clear()
        self._cache[key] = surf
        return surf
