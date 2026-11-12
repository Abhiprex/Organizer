@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 goto usepy
where python >nul 2>nul
if not errorlevel 1 goto usepython
echo Python was not found. Install it from https://www.python.org and run this again.
goto done
:usepy
py -3 organizer.py --resume
goto done
:usepython
python organizer.py --resume
:done
echo.
pause
