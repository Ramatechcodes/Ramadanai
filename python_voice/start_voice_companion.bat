@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
  echo Create the environment first: py -3.11 -m venv .venv
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
if exist .env (echo Loaded .env) else (copy .env.example .env)
echo Starting RAMATECH multilingual voice companion on port 8765...
python -m uvicorn app:app --host 0.0.0.0 --port 8765
pause
