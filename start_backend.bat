@echo off
echo Starting AI Director's Cut Backend...
echo.
set PYTHONUTF8=1
cd /d "%~dp0backend"
"C:\Users\Ujjwal Gupta\anaconda3\python.exe" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
