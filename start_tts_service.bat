
@echo off
cd /d "%~dp0"

if not exist ".venv-tts\Scripts\python.exe" (
    echo TTS Python environment not found.
    pause
    exit /b 1
)

echo Starting RAMATECH HOME AI multilingual TTS...
".venv-tts\Scripts\python.exe" -m uvicorn tts_service:app --host 0.0.0.0 --port 8766

pause
