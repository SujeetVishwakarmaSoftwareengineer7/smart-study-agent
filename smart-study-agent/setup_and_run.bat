@echo off
title Smart Study Generator — AI Study Assistant Setup ^& Launch (qwen/qwen3.8-27b via Groq)
color 0B
cls

echo ============================================================
echo   Smart Study Generator — Agentic AI Application
echo   Powered by Qwen via Groq API
echo ============================================================
echo.

:: ─── Check Python ───────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.9 or higher from:
    echo   https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% found.

:: ─── Set working directory ───────────────────────────────────────
cd /d "%~dp0"

:: ─── Create .env if missing ──────────────────────────────────────
if not exist ".env" (
    echo.
    echo [SETUP] .env file not found. Creating from template...
    copy ".env.example" ".env" >nul 2>&1
    echo.
    echo ============================================================
    echo   ACTION REQUIRED: Configure your API key
    echo ============================================================
    echo.
    echo A .env file has been created in:
    echo   %~dp0.env
    echo.
    echo Please open .env in a text editor and:
    echo   1. Replace "your_groq_api_key_here" with your actual Groq API key
    echo   2. Get your API key from: https://console.groq.com/keys
    echo   3. Save the file
    echo   4. Run this script again
    echo.
    echo Opening .env for editing...
    start notepad ".env"
    echo.
    pause
    exit /b 0
)

:: ─── Check if API key is configured ────────────────────────────
findstr /C:"your_groq_api_key_here" ".env" >nul 2>&1
if not errorlevel 1 (
    echo.
    echo [WARNING] GROQ_API_KEY appears to still be the placeholder value.
    echo Please edit .env and add your actual Groq API key.
    echo Get your key at: https://console.groq.com/keys
    echo.
    choice /C YN /M "Open .env for editing now"
    if errorlevel 2 goto skip_edit
    start notepad ".env"
    echo Please save your API key, then run this script again.
    pause
    exit /b 0
    :skip_edit
)

:: ─── Create virtual environment if missing ───────────────────────
if not exist "venv" (
    echo.
    echo [SETUP] Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

:: ─── Activate virtual environment ───────────────────────────────
echo.
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

:: ─── Install/upgrade dependencies ───────────────────────────────
echo.
echo [SETUP] Installing dependencies from requirements.txt...
echo (This may take a few minutes on first run)
echo.
pip install -r requirements.txt --quiet --upgrade
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    echo Try running: pip install -r requirements.txt
    pause
    exit /b 1
)
echo [OK] Dependencies installed.

:: ─── Create required directories ────────────────────────────────
if not exist "uploads" mkdir uploads
if not exist "data" mkdir data

:: ─── Check Tesseract (optional, for image OCR) ──────────────────
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [INFO] Tesseract OCR not found. Image OCR will be unavailable.
    echo   To enable image text extraction, install from:
    echo   https://github.com/UB-Mannheim/tesseract/wiki
    echo   (Optional — PDF and TXT upload will still work)
)

:: ─── Start the backend server ───────────────────────────────────
echo.
echo ============================================================
echo   Starting Smart Study Generator...
echo ============================================================
echo.
echo [INFO] Backend starting at: http://localhost:5000
echo [INFO] Press Ctrl+C to stop the server
echo.

:: Open browser after a short delay
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5000"

:: Start Flask app
cd backend
python app.py

echo.
echo [INFO] Server stopped.
pause
