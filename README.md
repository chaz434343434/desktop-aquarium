# Desktop Aquarium

A cozy catfish aquarium that lives at the bottom of your screen. A game for my teacher.

Collect 40 kinds of catfish, buy toys, foods and upgrades, hatch eggs, and grow a tank that
keeps earning scales while you work.

## Download

Get the newest version from **[Releases](../../releases/latest)**:

- **Windows:** `Desktop.Aquarium.vX.Y.Z.zip`. Right-click → Extract All, then run `DesktopAquarium.exe`.
- **Mac (M1/M2/M3/M4…):** `…Mac.arm64.dmg`
- **Mac (older Intel):** `…Mac.intel.dmg`

  Open the .dmg and drag Desktop Aquarium into Applications. The first time you open it, macOS
  blocks it because it isn't from the App Store: go to System Settings → Privacy & Security
  and click **Open Anyway**. (Not sure which Mac you have? Apple menu → About This Mac:
  "Chip: Apple M…" means arm64, "Processor: Intel" means intel.)

The game updates itself after that: Options → Updates → Check for updates.

## Running from source

Python 3.9+ and `pip install pygame==2.6.1`, then `python DesktopAquarium.pyw`.
Tests: `python test_v140.py` (and the other `test_*.py` files).
Mac builds are made by GitHub Actions (`.github/workflows/mac.yml`) every time a release is published.
