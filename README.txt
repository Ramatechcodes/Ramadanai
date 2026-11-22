RAMATECH HOME AI - OFFLINE MULTILINGUAL VOICE INTEGRATION

Files:
- app.py: main assistant, dashboard, Whisper, ESP32 controls, and local TTS proxy.
- tts_service.py: separate offline MMS speech service.
- start_ramadan_home_ai.bat: starts both services.

IMPORTANT:
1. Copy your current app.py to app_backup_before_offline_tts.py before replacing it.
2. Keep your existing .env. Do not overwrite it.
3. This setup expects:
   - Main environment: .venv
   - TTS environment: tts_env
   - ESP32_URL remains in your existing .env (currently http://192.168.3.127).

Start:
Double-click start_ramadan_home_ai.bat.
Open http://127.0.0.1:8765

First use of each language may load its model from the Hugging Face cache and take a while.
Only one TTS language model is kept in memory at a time.
TTS uses CPU and is local to this computer.

If your main environment is not named .venv, edit the BAT file to use its actual folder name.
If your TTS environment is not named tts_env, edit the BAT file accordingly.

To test the voice service by itself:
Activate tts_env, then run:
python -m uvicorn tts_service:app --host 127.0.0.1 --port 8766
Visit http://127.0.0.1:8766/health
