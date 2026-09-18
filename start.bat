@echo off
echo ===================================================
echo           Starting AI Director's Cut
echo ===================================================
echo.
echo Starting Backend (FastAPI on port 8000)...
start "AI Director's Cut - Backend" cmd /k "call start_backend.bat"

echo Starting Frontend (Next.js on port 3000)...
start "AI Director's Cut - Frontend" cmd /k "call start_frontend.bat"

echo.
echo Both servers are starting!
echo Once ready, open your browser at:
echo   http://localhost:3000
echo.
