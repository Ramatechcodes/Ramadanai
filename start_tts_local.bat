@echo off
cd /d "%~dp0"
if not exist .venv-tts\Scripts\activate.bat (
  echo TTS virtual environment not found.
  echo First run: py -3.13 -m venv .venv-tts
  echo Then install: .venv-tts\Scripts\python.exe -m pip install -r tts_requirements.txt
  pause
  exit /b 1
)
call .venv-tts\Scripts\activate.bat
echo Starting RAMATECH MMS TTS locally at http://127.0.0.1:8766
python -m uvicorn tts_service:app --host 127.0.0.1 --port 8766
pause
