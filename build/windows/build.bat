@echo off
setlocal EnableDelayedExpansion
:: ════════════════════════════════════════════════════════
:: LinguaTaxi — Windows Installer Build Script
::
:: This script does the heavy lifting so the end-user installer
:: is a simple file copy with no downloads or scripts.
::
:: Prerequisites on BUILD machine:
::   - Inno Setup 6+  (https://jrsoftware.org/isinfo.php)
::   - Internet connection
::
:: What it does:
::   1. Downloads Python 3.11.9 full installer
::   2. Installs Python locally to build\windows\python_dist\
::   3. Creates a venv with all packages pre-installed
::   4. Compiles the Inno Setup installer
::
:: Output: dist\LinguaTaxi-Setup-1.0.0.exe
:: ════════════════════════════════════════════════════════

title LinguaTaxi - Build Installer

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%..\.."
set "DIST_DIR=%PROJECT_DIR%\dist"
set "PYTHON_DIR=%SCRIPT_DIR%python_dist"
set "VENV_DIR=%SCRIPT_DIR%venv_dist"
set "PYTHON_VER=3.11.9"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VER%/python-%PYTHON_VER%-amd64.exe"

echo.
echo   ========================================
echo     LinguaTaxi - Build Installer
echo   ========================================
echo.

:: ── Step 1: Find Inno Setup ──
set "ISCC="
for %%p in (
    "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    "%ProgramFiles%\Inno Setup 6\ISCC.exe"
) do (
    if exist "%%~p" set "ISCC=%%~p"
)

if not defined ISCC (
    echo   ERROR: Inno Setup 6 not found.
    echo   Download from: https://jrsoftware.org/isinfo.php
    pause
    exit /b 1
)
echo   [OK] Inno Setup: %ISCC%

:: ── Step 2: Download and install Python locally ──
if exist "%PYTHON_DIR%\python.exe" (
    echo   [OK] Python already built at python_dist\
    goto :python_ready
)

echo.
echo   Downloading Python %PYTHON_VER% installer...
set "INSTALLER=%SCRIPT_DIR%python_installer.exe"
powershell -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%INSTALLER%'" 2>nul

if not exist "%INSTALLER%" (
    echo   ERROR: Download failed. Check internet connection.
    pause
    exit /b 1
)

echo   Installing Python to python_dist\ ...
echo   (This takes 1-2 minutes)
"%INSTALLER%" /quiet InstallAllUsers=0 PrependPath=0 Include_launcher=0 Include_test=0 Include_tcltk=1 TargetDir="%PYTHON_DIR%" >> "%SCRIPT_DIR%build_log.txt" 2>&1

:: Wait for installer to complete
:wait_python
timeout /t 2 /nobreak >nul
if not exist "%PYTHON_DIR%\python.exe" goto :wait_python

del "%INSTALLER%" 2>nul

:: Verify tkinter works
"%PYTHON_DIR%\python.exe" -c "import tkinter; print('tkinter OK')" >> "%SCRIPT_DIR%build_log.txt" 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo   ERROR: Python installed but tkinter missing.
    pause
    exit /b 1
)
echo   [OK] Python %PYTHON_VER% installed with tkinter

:python_ready

:: ── Step 3: Create venv with all packages ──
if exist "%VENV_DIR%\Scripts\pythonw.exe" (
    echo   [OK] Venv already built at venv_dist\
    echo        (Delete venv_dist\ to force rebuild)
    goto :venv_ready
)

echo.
echo   Creating virtual environment...
"%PYTHON_DIR%\python.exe" -m venv "%VENV_DIR%" >> "%SCRIPT_DIR%build_log.txt" 2>&1

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo   ERROR: venv creation failed.
    pause
    exit /b 1
)

echo   Upgrading pip...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip >> "%SCRIPT_DIR%build_log.txt" 2>&1

echo   Installing core packages...
"%VENV_DIR%\Scripts\pip.exe" install fastapi uvicorn websockets sounddevice numpy requests python-multipart >> "%SCRIPT_DIR%build_log.txt" 2>&1

echo   Installing faster-whisper (GPU/CPU backend)...
"%VENV_DIR%\Scripts\pip.exe" install faster-whisper >> "%SCRIPT_DIR%build_log.txt" 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo   faster-whisper failed, installing Vosk fallback...
    "%VENV_DIR%\Scripts\pip.exe" install vosk >> "%SCRIPT_DIR%build_log.txt" 2>&1
)

:: Also install vosk as backup
echo   Installing Vosk (CPU fallback)...
"%VENV_DIR%\Scripts\pip.exe" install vosk >> "%SCRIPT_DIR%build_log.txt" 2>&1

echo   [OK] All packages installed

:venv_ready

:: ── Step 4: Check icon ──
if exist "%PROJECT_DIR%\assets\linguataxi.ico" (
    echo   [OK] Icon found
) else (
    echo   [--] No icon — run: python assets\generate_icons.py
)

:: ── Step 5: Compile installer ──
mkdir "%DIST_DIR%" 2>nul

echo.
echo   Compiling installer...
echo.

"%ISCC%" "%SCRIPT_DIR%installer.iss"

if !ERRORLEVEL! EQU 0 (
    echo.
    echo   ========================================
    echo     BUILD SUCCESSFUL
    echo     Output: dist\LinguaTaxi-Setup-1.0.0.exe
    echo   ========================================
    echo.
    echo   Note: To rebuild from scratch, delete:
    echo     build\windows\python_dist\
    echo     build\windows\venv_dist\
    echo.
) else (
    echo.
    echo   BUILD FAILED - check errors above.
    echo   See build\windows\build_log.txt for details.
    echo.
)

pause
