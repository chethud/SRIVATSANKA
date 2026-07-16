@echo off
cd /d "%~dp0whatsapp"
call venv\Scripts\activate.bat
echo Starting FastAPI on http://127.0.0.1:8001
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
