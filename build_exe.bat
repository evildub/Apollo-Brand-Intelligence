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

echo [3/6] Copying data.json and application icons into distribution directory...
copy /Y "data.json" "dist\Apollo Brand Intelligence\data.json" >nul
copy /Y "apollo.ico" "dist\Apollo Brand Intelligence\apollo.ico" >nul
copy /Y "apollo.png" "dist\Apollo Brand Intelligence\apollo.png" >nul
copy /Y "artemis.ico" "dist\Apollo Brand Intelligence\artemis.ico" >nul
copy /Y "artemis.png" "dist\Apollo Brand Intelligence\artemis.png" >nul

echo [4/6] Bundling Security Audit, Executive Brief, and Analyst Documentation...
copy /Y "SECURITY_AUDIT.md" "dist\Apollo Brand Intelligence\SECURITY_AUDIT.md" >nul
copy /Y "ENTERPRISE_EXECUTIVE_BRIEF.md" "dist\Apollo Brand Intelligence\ENTERPRISE_EXECUTIVE_BRIEF.md" >nul
copy /Y "EVALUATION.md" "dist\Apollo Brand Intelligence\EVALUATION.md" >nul
copy /Y "EXE_README.md" "dist\Apollo Brand Intelligence\README.md" >nul

echo [5/6] Packaging Release Zip Archive...
powershell -NoProfile -Command "Compress-Archive -Path 'dist\Apollo Brand Intelligence' -DestinationPath 'dist\ApolloBrandIntelligence-v3.4.0.zip' -Force"

echo [6/6] Build complete! Verified distribution ready:
dir /b "dist\Apollo Brand Intelligence\*.exe"
echo.
echo Computing SHA-256 Cryptographic Checksums:
powershell -NoProfile -Command "Get-FileHash -Algorithm SHA256 'dist\Apollo Brand Intelligence\*.exe', 'dist\ApolloBrandIntelligence-v3.4.0.zip' | Format-Table -AutoSize"
echo Done!
