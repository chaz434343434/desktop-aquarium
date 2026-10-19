@echo off
rem Rebuilds release\v<version>\ : the game folder, "Desktop Aquarium v<version>.zip" and a tag reminder
cd /d "%~dp0"
tasklist /fi "imagename eq DesktopAquarium.exe" | find /i "DesktopAquarium.exe" >nul && (
  echo Close Desktop Aquarium first - its files can't be replaced while it's running.
  exit /b 1
)
python build_assets\make_icon.py || goto :fail
python -m PyInstaller --noconfirm --windowed --onedir --name DesktopAquarium ^
  --icon "%~dp0build_assets\purrfin.ico" --version-file "%~dp0build_assets\version_info.txt" ^
  --distpath "%~dp0dist" --workpath "%~dp0build" --specpath "%~dp0build" ^
  --exclude-module numpy --exclude-module tkinter --exclude-module PIL --exclude-module matplotlib ^
  DesktopAquarium.pyw || goto :fail
python build_assets\package.py || goto :fail
exit /b 0
:fail
echo Build failed.
exit /b 1
