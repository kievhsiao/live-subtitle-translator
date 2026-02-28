@echo off
echo =========================================
echo         Live Subtitle Translator
echo             Model Downloader
echo =========================================
echo.
echo Please select which models to download:
echo [1] GPU Model Only (Recommended, ~2.3GB)
echo [2] CPU Model Only (OpenVINO, ~1.2GB)
echo [3] Download Both Models
echo.

set /p choice="Enter your choice (1-3) [Default: 1]: "

if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    set MODE=gpu
) else if "%choice%"=="2" (
    set MODE=cpu
) else if "%choice%"=="3" (
    set MODE=all
) else (
    echo Invalid choice. Defaulting to GPU mode.
    set MODE=gpu
)

echo.
echo Starting download in %MODE% mode...
call .venv\Scripts\activate.bat
python download_models.py --mode %MODE%

echo.
echo Finished. You can now run start.bat
pause
