@echo off
echo ===================================================
echo   Building Apollo Brand Intelligence Standalone EXE
echo ===================================================

echo [1/5] Closing any running Apollo / Valknut instances...
taskkill /F /IM "Apollo Brand Intelligence.exe" 2>nul
taskkill /F /IM ApolloBrandIntelligence.exe 2>nul
taskkill /F /IM "Valknut Brand Intelligence.exe" 2>nul
taskkill /F /IM ValknutBrandIntelligence.exe 2>nul
timeout /t 1 /nobreak >nul

echo [2/5] Running PyInstaller...
python -m PyInstaller --onedir --noconsole --noconfirm --name "Apollo Brand Intelligence" --icon="%~dp0apollo.ico" --add-data "data.json;." --add-data "apollo.ico;." --add-data "apollo.png;." --hidden-import "PIL" --hidden-import "PIL.ImageTk" --hidden-import "openpyxl" --hidden-import "bs4" --hidden-import "requests" --hidden-import "curl_cffi" --hidden-import "curl_cffi.requests" --hidden-import "playwright" --hidden-import "playwright.sync_api" --hidden-import "visual_catalog" --hidden-import "visual_catalog_modal" --hidden-import "visual_harvester" --hidden-import "vinted_scraper" --hidden-import "tiktok_scraper" --hidden-import "manomano_scraper" --hidden-import "printerval_scraper" --hidden-import "redbubble_scraper" --hidden-import "mercadolibre_scraper" --hidden-import "temu_scraper" --hidden-import "scribd_scraper" --hidden-import "vero_pdf_parser" --hidden-import "vero_disclosure_modal" --hidden-import "pypdf" --hidden-import "intel_pack_manager" --hidden-import "field_guide_modal" --hidden-import "tooltip" --hidden-import "batch_importer" --hidden-import "exporter" --hidden-import "aliexpress_scraper" --hidden-import "wish_scraper" main.py

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

echo [5/5] Build complete! Starting application...
start "" "dist\Apollo Brand Intelligence\Apollo Brand Intelligence.exe"
echo Done!
