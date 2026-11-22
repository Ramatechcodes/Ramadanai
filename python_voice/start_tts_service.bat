@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (echo Create .venv first. & pause & exit /b 1)
call .venv\Scripts\activate.bat
echo Starting optional multilingual MMS TTS service on port 8766...
python -m uvicorn tts_service:app --host 0.0.0.0 --port 8766
pause
