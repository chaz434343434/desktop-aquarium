#!/bin/sh
# Builds the Mac app and its .dmg (runs on GitHub's Mac machines, see .github/workflows/mac.yml):
#   out/Desktop.Aquarium.v<version>.Mac.<arm64|intel>.dmg
set -e
cd "$(dirname "$0")/.."
VER=$(python -c "from purrfin.version import VERSION; print(VERSION)")
ARCH=$(python -c "import platform; print('arm64' if platform.machine() == 'arm64' else 'intel')")
APP="dist/Desktop Aquarium.app"

rm -rf build dist out
ICON="--icon build_assets/icon.png"
BID="--osx-bundle-identifier com.chaz434343434.desktopaquarium"
[ -n "$DA_NO_ICON" ] && ICON=""
[ -n "$DA_NO_BID" ] && BID=""
python -m PyInstaller --noconfirm --windowed --onedir --name "Desktop Aquarium" $ICON $BID \
  --exclude-module numpy --exclude-module tkinter --exclude-module matplotlib \
  DesktopAquarium.pyw

PL="$APP/Contents/Info.plist"
if [ -z "$DA_NO_PLIST" ]; then
  plutil -replace CFBundleShortVersionString -string "$VER" "$PL"
  plutil -replace CFBundleVersion -string "$VER" "$PL"
  plutil -replace NSHumanReadableCopyright -string "Desktop Aquarium - made with love for a great teacher" "$PL"
fi
# ad-hoc signature (Apple Silicon won't run unsigned code at all)
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"

mkdir -p out/dmg
ditto "$APP" "out/dmg/Desktop Aquarium.app"
ln -s /Applications out/dmg/Applications
cp "build_assets/How to open on Mac.txt" out/dmg/
cp "build_assets/How to play.txt" out/dmg/
hdiutil create -volname "Desktop Aquarium" -srcfolder out/dmg -ov -format UDZO \
  "out/Desktop.Aquarium.v$VER.Mac.$ARCH.dmg"
rm -rf out/dmg
ls -la out
