"""Writes a pygame Surface as a PNG file with plain Python (zlib), without pygame's own image saver
(which crashed the packaged game on Apple-chip Macs)."""
import struct
import zlib

import pygame


def save_png(surf, path):
    w, h = surf.get_size()
    raw = pygame.image.tobytes(surf, "RGB")
    stride = w * 3
    rows = b"".join(b"\x00" + raw[y * stride:(y + 1) * stride] for y in range(h))   # filter type 0 per row

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))     # 8-bit RGB
           + chunk(b"IDAT", zlib.compress(rows, 6))
           + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)
    return path
