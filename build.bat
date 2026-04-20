@echo off
REM Build Semantic File Aggregator as a standalone Windows desktop app.
REM Usage: build.bat

setlocal

where python >nul 2>nul
if errorlevel 1 (
    echo Python not found in PATH. Install Python 3.10+ and try again.
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

python -m PyInstaller --noconfirm SemanticFileAggregator.spec
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo.
echo ============================================================
echo Build complete.
echo   Folder bundle: dist\SemanticFileAggregator\
echo   Launcher:      dist\SemanticFileAggregator\SemanticFileAggregator.exe
echo ============================================================
endlocal
