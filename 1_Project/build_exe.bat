@echo off
cd /d "%~dp0"
echo Building Organizer.exe - this needs internet once and takes a few minutes.
python -m pip install --upgrade pyinstaller pystray pillow
if errorlevel 1 goto fail
python -m PyInstaller --noconfirm --clean --onedir --windowed --name Organizer --add-data "presets;presets" --hidden-import pystray._win32 --hidden-import app_window --hidden-import app_backend --hidden-import organizer organizer_app.py
if errorlevel 1 goto fail
copy /y organizer_config.json dist\Organizer\ >nul
echo.
echo Done. Your program is in:  dist\Organizer\Organizer.exe
echo Copy the whole dist\Organizer folder wherever you like. Some antivirus tools warn about new .exe files; that is normal for self-built programs.
pause
exit /b 0
:fail
echo Something went wrong. Make sure Python is installed and you are online, then try again.
pause
exit /b 1
