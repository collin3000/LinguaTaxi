@echo off
title Live Caption
cd /d "%~dp0"
python server.py %*
if errorlevel 1 (
    echo.
    echo  If you see errors, try:
    echo    run.bat --device cpu         (skip GPU)
    echo    run.bat --list-mics          (check microphone)
    echo    setup.bat                    (re-run installer)
    echo.
    pause
)
