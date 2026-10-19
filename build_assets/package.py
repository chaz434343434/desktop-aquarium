"""Copies the PyInstaller build into a folder named after the version and zips it:

    release\\v1.2.0\\Desktop Aquarium v1.2.0.zip   <- upload this to the GitHub release
    release\\v1.2.0\\Desktop Aquarium\\             <- the same game unzipped, for testing
    release\\v1.2.0\\GITHUB TAG - v1.2.0.txt       <- the exact tag to use on GitHub

Older version folders are left alone. Checks that nothing went missing on the way."""
import os
import re
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist", "DesktopAquarium")


def read_version():
    with open(os.path.join(ROOT, "purrfin", "version.py"), encoding="utf-8") as fh:
        return re.search(r'VERSION\s*=\s*"([^"]+)"', fh.read()).group(1)


VERSION = read_version()
TAG = "v" + VERSION
REL = os.path.join(ROOT, "release", TAG)
OUT = os.path.join(REL, "Desktop Aquarium")
ZIP_BASE = os.path.join(REL, f"Desktop Aquarium {TAG}")


def count(path):
    return sum(len(files) for _, _, files in os.walk(path))


if os.path.exists(REL):
    shutil.rmtree(REL)          # raises if a file is locked (game still running) instead of half-copying
shutil.copytree(DIST, OUT)
shutil.copy(os.path.join(ROOT, "build_assets", "How to play.txt"), OUT)

want = count(DIST) + 1
got = count(OUT)
if got != want:
    sys.exit(f"Copy incomplete: {got} of {want} files")
# the folder inside the zip stays "Desktop Aquarium" so installs don't carry an old version in their name
zpath = shutil.make_archive(ZIP_BASE, "zip", REL, "Desktop Aquarium")
with zipfile.ZipFile(zpath) as z:
    n = len([i for i in z.infolist() if not i.is_dir()])
if n != want:
    sys.exit(f"Zip incomplete: {n} of {want} files")
with open(os.path.join(REL, f"GITHUB TAG - {TAG}.txt"), "w", encoding="utf-8") as fh:
    fh.write(f"""Desktop Aquarium {TAG}

On GitHub (github.com/chaz434343434/desktop-aquarium):
  Releases -> Draft a new release
  Tag:   {TAG}      (type it exactly, with the v)
  Title: Desktop Aquarium {VERSION}
  Attach: Desktop Aquarium {TAG}.zip   (from this folder)
  -> Publish release
""")
print(f"Done: {zpath}  ({want} files, {os.path.getsize(zpath) / 1e6:.1f} MB)")
print(f"GitHub tag to use: {TAG}")
