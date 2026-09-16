@echo off
echo ===================================================
echo   Building Apollo Smart Triage Lab (BETA Standalone)
echo ===================================================

echo [1/5] Closing any running Apollo_Beta instances...
taskkill /F /IM "Apollo_Beta.exe" 2>nul
timeout /t 1 /nobreak >nul

echo [2/5] Running PyInstaller for Apollo_Beta...
python -m PyInstaller --onedir --noconsole --noconfirm --name "Apollo_Beta" --distpath "dist\Apollo_Smart_Triage_Beta" --icon="%~dp0apollo.ico" --add-data "data.json;." --add-data "apollo.ico;." --add-data "apollo.png;." --hidden-import "PIL" --hidden-import "PIL.ImageTk" --hidden-import "openpyxl" --hidden-import "bs4" --hidden-import "requests" --hidden-import "curl_cffi" --hidden-import "curl_cffi.requests" --hidden-import "playwright" --hidden-import "playwright.sync_api" --hidden-import "visual_catalog" --hidden-import "visual_catalog_modal" --hidden-import "visual_harvester" --hidden-import "vinted_scraper" --hidden-import "tiktok_scraper" --hidden-import "intel_pack_manager" main.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller build failed with exit code %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo [3/5] Copying data.json into beta distribution directory...
copy /Y "data.json" "dist\Apollo_Smart_Triage_Beta\Apollo_Beta\data.json" >nul

echo [4/5] Bundling Security Audit and Analyst Documentation...
copy /Y "SECURITY_AUDIT.md" "dist\Apollo_Smart_Triage_Beta\Apollo_Beta\SECURITY_AUDIT.md" >nul

echo [5/5] Build complete! Starting Apollo_Beta...
start "" "dist\Apollo_Smart_Triage_Beta\Apollo_Beta\Apollo_Beta.exe"
echo Done!
