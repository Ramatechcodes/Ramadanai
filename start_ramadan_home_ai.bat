@echo off
title RAMATECH HOME AI - Offline Voice
cd /d "%~dp0"

echo Starting RAMADAN HOME AI offline voice engine...
start "RAMADAN Offline TTS - Port 8766" cmd /k "cd /d "%~dp0" && call tts_env\Scripts\activate && python -m uvicorn tts_service:app --host 127.0.0.1 --port 8766"

timeout /t 3 /nobreak >nul

echo Starting RAMADAN main assistant...
call .venv\Scripts\activate
python -m uvicorn app:app --host 127.0.0.1 --port 8765 --log-level info

pause
