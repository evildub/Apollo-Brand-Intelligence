@echo off
echo ===================================================================
echo   Building Apollo Brand Intelligence & Artemis Dual Executables
echo ===================================================================

echo [1/5] Closing any running Apollo / Artemis instances...
taskkill /F /IM "Apollo Brand Intelligence.exe" 2>nul
taskkill /F /IM ApolloBrandIntelligence.exe 2>nul
taskkill /F /IM Artemis.exe 2>nul
timeout /t 1 /nobreak >nul

echo [2/5] Compiling binaries via PyInstaller Spec...
python -m PyInstaller --noconfirm "Apollo Brand Intelligence.spec"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller build failed with exit code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo [3/5] Copying data.json into distribution directory...
copy /Y "data.json" "dist\Apollo Brand Intelligence\data.json" >nul

echo [4/5] Bundling Security Audit and Analyst Documentation...
copy /Y "SECURITY_AUDIT.md" "dist\Apollo Brand Intelligence\SECURITY_AUDIT.md" >nul
copy /Y "EXE_README.md" "dist\Apollo Brand Intelligence\README.md" >nul

echo [5/5] Build complete! Verified distribution ready:
dir /b "dist\Apollo Brand Intelligence\*.exe"
echo.
echo Computing SHA-256 Cryptographic Checksums:
powershell -NoProfile -Command "Get-FileHash -Algorithm SHA256 'dist\Apollo Brand Intelligence\*.exe' | Format-Table -AutoSize"
echo Done!
