@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
  start "" pythonw organizer_app.py %*
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python is not installed. Install it from python.org, then run this again.
    pause
  ) else (
    python organizer_app.py %*
  )
)
