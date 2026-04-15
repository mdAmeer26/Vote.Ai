@echo off
echo ============================================================
echo Starting Voter Fraud Detection System
echo ============================================================
call venv\Scripts\activate.bat
set DEBUG=False
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
