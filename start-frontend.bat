@echo off
cd /d "%~dp0website"
set VITE_API_PROXY=http://127.0.0.1:8001
echo Starting React dashboard on http://127.0.0.1:5174
npm run dev -- --host 127.0.0.1 --port 5174
