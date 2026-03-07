@echo off
setlocal enabledelayedexpansion
title Live Caption - Setup
color 0F

echo.
echo  +=====================================================+
echo  :     Live Caption - Installer                        :
echo  :     Real-time Speech Captioning ^& Translation       :
echo  +=====================================================+
echo.

:: ──────────────────────────────────────────────
:: Check Python
:: ──────────────────────────────────────────────
echo  [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python not found.
    echo     Download from: https://www.python.org/downloads/
    echo     IMPORTANT: Check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo     OK: Python %PYVER% found

:: ──────────────────────────────────────────────
:: Install base Python dependencies
:: ──────────────────────────────────────────────
echo.
echo  [2/5] Installing base dependencies...
pip install fastapi uvicorn[standard] websockets sounddevice numpy requests python-multipart --break-system-packages -q 2>nul
if errorlevel 1 (
    pip install fastapi uvicorn[standard] websockets sounddevice numpy requests python-multipart -q 2>nul
)
echo     OK: Base packages installed

:: ──────────────────────────────────────────────
:: Detect GPU capability
:: ──────────────────────────────────────────────
echo.
echo  [3/5] Detecting GPU capability...

set "GPU_CAPABLE=0"
set "HAS_NVIDIA=0"
set "HAS_CUDA=0"
set "GPU_NAME=None"

:: Check for NVIDIA GPU
nvidia-smi >nul 2>&1
if not errorlevel 1 (
    set "HAS_NVIDIA=1"
    for /f "tokens=*" %%g in ('nvidia-smi --query-gpu^=name --format^=csv^,noheader 2^>nul') do set "GPU_NAME=%%g"
    echo     Found GPU: !GPU_NAME!

    :: Check for CUDA libraries
    where cublas64_12.dll >nul 2>&1
    if not errorlevel 1 (
        set "HAS_CUDA=1"
    )

    :: Also check common paths
    if "!HAS_CUDA!"=="0" (
        if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin\cublas64_12.dll" set "HAS_CUDA=1"
        if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin\cublas64_12.dll" set "HAS_CUDA=1"
        if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin\cublas64_12.dll" set "HAS_CUDA=1"
        if exist "C:\Program Files\Blackmagic Design\DaVinci Resolve\cublas64_12.dll" set "HAS_CUDA=1"
    )

    if "!HAS_CUDA!"=="1" (
        echo     Found CUDA 12 libraries
        set "GPU_CAPABLE=1"
    ) else (
        echo     WARNING: CUDA 12 libraries not found
        echo.
        echo     Your GPU (!GPU_NAME!^) is present but CUDA libraries are missing.
        echo     You can either:
        echo       A^) Install CUDA Toolkit: https://developer.nvidia.com/cuda-downloads
        echo          Then re-run this setup to get Whisper ^(GPU, best quality^).
        echo       B^) Continue now with Vosk ^(CPU, good quality^).
        echo.
    )
) else (
    echo     No NVIDIA GPU detected
    echo.
)

:: ──────────────────────────────────────────────
:: Choose and install speech recognition backend
:: ──────────────────────────────────────────────
echo  [4/5] Installing speech recognition...
echo.

if "!GPU_CAPABLE!"=="1" (
    echo     Your system supports GPU-accelerated Whisper ^(best accuracy: ~95-97%%^).
    echo     Installing faster-whisper...
    echo.
    pip install "faster-whisper>=1.0.0" --break-system-packages -q 2>nul
    if errorlevel 1 (
        pip install "faster-whisper>=1.0.0" -q 2>nul
    )
    echo     OK: Whisper installed ^(GPU mode^)
    set "BACKEND=whisper"
) else (
    echo  +---------------------------------------------------------+
    echo  :  Your system does not have a sufficient GPU to use       :
    echo  :  Whisper voice-to-text.                                  :
    echo  :                                                          :
    echo  :  Would you like to install with a voice-to-text engine   :
    echo  :  that is compatible with your computer but will have     :
    echo  :  lower accuracy?                                         :
    echo  :                                                          :
    echo  :  Whisper ^(GPU^):  ~95-97%% accuracy, needs NVIDIA + CUDA  :
    echo  :  Vosk ^(CPU^):     ~85-90%% accuracy, works on any PC      :
    echo  :                  Real-time streaming, no GPU required     :
    echo  +---------------------------------------------------------+
    echo.
    set /p "INSTALL_VOSK=  Install Vosk CPU voice-to-text? (Y/N): "

    if /i "!INSTALL_VOSK!"=="Y" (
        echo.
        echo     Installing Vosk...
        pip install vosk --break-system-packages -q 2>nul
        if errorlevel 1 (
            pip install vosk -q 2>nul
        )
        echo     OK: Vosk installed ^(CPU mode^)
        echo.
        echo     Note: The voice recognition model ^(~1.8 GB^) will download
        echo     automatically the first time you run the server.
        set "BACKEND=vosk"
    ) else (
        echo.
        echo     Skipping speech recognition install.
        echo     You can install manually later:
        echo       pip install vosk                     ^(for CPU^)
        echo       pip install faster-whisper           ^(for GPU, needs CUDA^)
        echo.
        set "BACKEND=none"
    )
)

:: ──────────────────────────────────────────────
:: First-run configuration
:: ──────────────────────────────────────────────
echo.
echo  [5/5] Configuration
echo.

if exist "%~dp0config.json" (
    echo     Existing config.json found - keeping current settings.
    echo     You can edit settings in the Operator Panel at http://localhost:3001
) else (
    echo     First-time setup:
    echo.

    set /p "DEEPL_KEY=     DeepL API Key (free at deepl.com/pro-api, Enter to skip): "
    set /p "SESSION=     Session title (Enter for 'Live Captioning'): "

    if "!SESSION!"=="" set "SESSION=Live Captioning"

    :: Write config.json
    echo { > "%~dp0config.json"
    echo   "deepl_api_key": "!DEEPL_KEY!", >> "%~dp0config.json"
    echo   "session_title": "!SESSION!", >> "%~dp0config.json"
    echo   "target_lang": "ES", >> "%~dp0config.json"
    echo   "speakers": [], >> "%~dp0config.json"
    echo   "footer_image": null, >> "%~dp0config.json"
    echo   "font_size": 42, >> "%~dp0config.json"
    echo   "max_lines": 3, >> "%~dp0config.json"
    echo   "backend": "!BACKEND!" >> "%~dp0config.json"
    echo } >> "%~dp0config.json"

    echo.
    echo     OK: Config saved. You can change everything in the Operator Panel.
)

:: ──────────────────────────────────────────────
:: Done
:: ──────────────────────────────────────────────
echo.
echo  =====================================================
echo   Setup complete!
echo.
if "!BACKEND!"=="whisper" (
    echo   Backend: Whisper ^(GPU-accelerated, best quality^)
    echo   To start: run.bat
)
if "!BACKEND!"=="vosk" (
    echo   Backend: Vosk ^(CPU, good quality^)
    echo   To start: run.bat
)
if "!BACKEND!"=="none" (
    echo   WARNING: No speech engine installed.
    echo   Install one before running:
    echo     pip install vosk               ^(CPU^)
    echo     pip install faster-whisper     ^(GPU^)
)
echo.
echo   Display ^(projector^):  http://localhost:3000
echo   Operator ^(your PC^):   http://localhost:3001
echo  =====================================================
echo.
pause
