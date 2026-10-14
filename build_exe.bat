@echo off
echo ===================================================================
echo   Building Apollo Brand Intelligence & Artemis Dual Executables
echo ===================================================================

cd /d "%~dp0"

echo [1/5] Closing any running Apollo / Artemis instances...
taskkill /F /IM "Apollo Brand Intelligence.exe" 2>nul
taskkill /F /IM ApolloBrandIntelligence.exe 2>nul
taskkill /F /IM Artemis.exe 2>nul
timeout /t 1 /nobreak >nul

echo [2/5] Compiling binaries via PyInstaller Spec...
python -m PyInstaller --noconfirm "Apollo Brand Intelligence.spec"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] PyInstaller build failed with exit code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo [3/5] Bundling application icons and enterprise assets...
if exist "apollo.ico" copy /Y "apollo.ico" "dist\Apollo Brand Intelligence\apollo.ico" >nul
if exist "apollo.png" copy /Y "apollo.png" "dist\Apollo Brand Intelligence\apollo.png" >nul
if exist "artemis.ico" copy /Y "artemis.ico" "dist\Apollo Brand Intelligence\artemis.ico" >nul
if exist "artemis.png" copy /Y "artemis.png" "dist\Apollo Brand Intelligence\artemis.png" >nul
if exist "README.md" copy /Y "README.md" "dist\Apollo Brand Intelligence\README.md" >nul

echo [4/5] Packaging Release Zip Archive...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\Apollo Brand Intelligence' -DestinationPath 'dist\ApolloBrandIntelligence-v3.4.0.zip' -Force"

echo [5/5] Build complete! Verified distribution ready:
dir /b "dist\Apollo Brand Intelligence\*.exe"
echo.
echo Computing SHA-256 Cryptographic Checksums:
powershell -NoProfile -Command "Get-FileHash -Algorithm SHA256 'dist\Apollo Brand Intelligence\*.exe', 'dist\ApolloBrandIntelligence-v3.4.0.zip' | Format-Table -AutoSize"
echo.
echo Done! Output located at: dist\Apollo Brand Intelligence\
pause
