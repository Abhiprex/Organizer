@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 goto usepy
where python >nul 2>nul
if not errorlevel 1 goto usepython
echo Python was not found. Install it from https://www.python.org and run this again.
goto done
:usepy
py -3 manage_folders.py %*
goto done
:usepython
python manage_folders.py %*
:done
echo.
pause
