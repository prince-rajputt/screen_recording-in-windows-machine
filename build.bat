@echo off
REM Builds ScreenCapturePro.exe into dist\
python -m PyInstaller --noconfirm --onefile --windowed ^
  --name "ScreenCapturePro" ^
  --icon "assets\icon.ico" ^
  app\main.py
echo.
echo Build complete. Find your exe in dist\ScreenCapturePro.exe
