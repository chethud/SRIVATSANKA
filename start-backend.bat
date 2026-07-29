@echo off
cd /d "%~dp0whatsapp"
echo Starting FastAPI on http://127.0.0.1:8001
venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
