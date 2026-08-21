@echo off
cd /d "%~dp0website"
set VITE_API_PROXY=http://13.232.230.198
echo Starting React dashboard on http://127.0.0.1:5174
echo API proxy: AWS EC2 %VITE_API_PROXY%
npm run dev -- --host 127.0.0.1 --port 5174
