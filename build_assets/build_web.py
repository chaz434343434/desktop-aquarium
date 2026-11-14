"""Builds the web version (for phones and any browser) with pygbag.
Output: build_web/src/build/web/  (index.html + the game packed beside it). Put that folder on any web host.
Run: python build_assets/build_web.py"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "build_web", "src")

MAIN = '''# Desktop Aquarium, web version. pygbag runs this file in the browser.
# pygbag reads the imports here to know what to download, so pygame has to be named.
import asyncio

import pygame  # noqa: F401


async def main():
    from purrfin.main import run_web
    await run_web()


asyncio.run(main())
'''

if os.path.exists(SRC):
    shutil.rmtree(SRC)
os.makedirs(SRC)
shutil.copytree(os.path.join(ROOT, "purrfin"), os.path.join(SRC, "purrfin"),
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
with open(os.path.join(SRC, "main.py"), "w", encoding="utf-8") as fh:
    fh.write(MAIN)
icon = os.path.join(ROOT, "build_assets", "web_icon.png")
if os.path.exists(icon):
    shutil.copy(icon, os.path.join(SRC, "favicon.png"))
cmd = [sys.executable, "-m", "pygbag", "--build", "--app_name", "Desktop Aquarium", "--title", "Desktop Aquarium", SRC]
print(" ".join(cmd))
code = subprocess.call(cmd, cwd=ROOT)
# pygbag's page has two viewport lines and the second cancels "use the phone's real width": keep one good one
page = os.path.join(SRC, "build", "web", "index.html")
if code == 0 and os.path.exists(page):
    html = open(page, encoding="utf-8").read()
    good = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">'
    lines = [ln for ln in html.split("\n") if 'name="viewport"' not in ln]
    head = next(i for i, ln in enumerate(lines) if '<meta charset' in ln)
    lines.insert(head + 1, "    " + good)
    open(page, "w", encoding="utf-8").write("\n".join(lines))
    print("viewport fixed")
sys.exit(code)
