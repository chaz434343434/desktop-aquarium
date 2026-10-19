"""Draws the app icon (Sunny the Sunflower Catfish on a water tile) -> purrfin.ico + icon.png"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame  # noqa: E402
from PIL import Image  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))
from purrfin import sprites  # noqa: E402

N = 32
tile = pygame.Surface((N, N), pygame.SRCALPHA)
for y in range(3, N - 3):
    k = (y - 3) / (N - 7)
    col = tuple(int(a + (b - a) * k) for a, b in zip((90, 185, 215), (25, 85, 130)))
    pygame.draw.line(tile, col, (3, y), (N - 4, y))
pygame.draw.rect(tile, (230, 205, 150), (3, N - 7, N - 6, 4))
pygame.draw.rect(tile, (20, 24, 36), (2, 2, N - 4, N - 4), 1)
fish = sprites.fish_frames("sunflower")[(True, False)][0]
tile.blit(fish, ((N - fish.get_width()) // 2, (N - fish.get_height()) // 2 + 1))
for x, y in ((8, 8), (11, 5), (24, 9)):
    pygame.draw.circle(tile, (210, 240, 255), (x, y), 1)

big = pygame.transform.scale(tile, (256, 256))
png = os.path.join(HERE, "icon.png")
pygame.image.save(big, png)
img = Image.open(png).convert("RGBA")
img.save(os.path.join(HERE, "purrfin.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128),
                                                    (256, 256)])
print("icon ok")
