"""Version + where updates come from.

To ship an update: bump VERSION, run build_release.bat, then on GitHub make a new Release
with the tag  v<VERSION>  (e.g. v1.2.0) and attach  release\\v<VERSION>\\Desktop Aquarium v<VERSION>.zip.
Every copy of the game checks that repo's latest release and offers to install it.
"""
VERSION = "1.6.0"

# "owner/repo" of the public GitHub repository that hosts the releases ("" = don't check)
UPDATE_REPO = "chaz434343434/desktop-aquarium"
