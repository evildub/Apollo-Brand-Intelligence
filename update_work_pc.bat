@echo off
title Apollo Brand Intelligence - Auto-Updater
color 0b
echo ========================================================
echo   APOLLO BRAND INTELLIGENCE - 1-CLICK AUTO-UPDATER
echo ========================================================
echo.

set TARGET_DIR=%~dp0

echo [1/3] Checking and downloading latest release from GitHub...
gh release download --repo evildub/Apollo-Brand-Intelligence --pattern "*.zip" --clobber --dir "%TARGET_DIR%"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to download latest release from GitHub.
    echo Make sure you ran 'gh auth login' once on this computer.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Extracting update files...
powershell -NoProfile -Command "Get-ChildItem -Path '%TARGET_DIR%' -Filter '*BrandIntelligence-*.zip' | ForEach-Object { Expand-Archive -Path $_.FullName -DestinationPath '%TARGET_DIR%' -Force; Remove-Item $_.FullName }"

echo.
echo [3/3] Launching latest Apollo Brand Intelligence...
if exist "%TARGET_DIR%Apollo Brand Intelligence\Apollo Brand Intelligence.exe" (
    start "" "%TARGET_DIR%Apollo Brand Intelligence\Apollo Brand Intelligence.exe"
) else (
    start "" "%TARGET_DIR%ApolloBrandIntelligence\ApolloBrandIntelligence.exe"
)
echo.
echo Update complete! Starting application...
timeout /t 2 >nul
