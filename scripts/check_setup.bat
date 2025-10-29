@echo off
REM Document Translator - Windows Setup Checker
REM Run this file to verify your installation

echo ============================================================
echo Document Translator - Setup Checker
echo ============================================================
echo.

echo Checking for required folders...
echo.

if exist "ooxml\" (
    echo [OK] ooxml\ folder found
) else (
    echo [ERROR] ooxml\ folder is MISSING!
    set MISSING=1
)

if exist "scripts\" (
    echo [OK] scripts\ folder found
) else (
    echo [ERROR] scripts\ folder is MISSING!
    set MISSING=1
)

if exist "document_translator.py" (
    echo [OK] document_translator.py found
) else (
    echo [ERROR] document_translator.py is MISSING!
    set MISSING=1
)

echo.
echo ============================================================

if defined MISSING (
    echo.
    echo ERROR: Some required files/folders are missing!
    echo.
    echo You need to have these folders:
    echo   - ooxml\
    echo   - scripts\
    echo.
    echo SOLUTION:
    echo 1. Re-download ALL files from the source
    echo 2. Extract the COMPLETE archive
    echo 3. Make sure folders are included
    echo.
    echo For detailed help, see: WINDOWS_TROUBLESHOOTING.md
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo SUCCESS: All required files and folders found!
    echo.
    echo Next steps:
    echo 1. Install dependencies:
    echo    pip install googletrans==4.0.0rc1 defusedxml
    echo.
    echo 2. Run the translator:
    echo    python document_translator.py input.docx output.docx es
    echo.
    echo 3. Or use the GUI:
    echo    python document_translator_gui.py
    echo.
    pause
    exit /b 0
)
