RAMATECH HOME AI - MULTILINGUAL COMMAND UPGRADE

This patch updates python_voice/app.py only. It preserves the existing FastAPI routes, ESP32 control endpoints, payment handlers, Whisper model selection and local TTS proxy.

Includes:
- 18 command actions in each of English, Yoruba, Hausa and Igbo (72 buttons total).
- Each button calls the existing /command endpoint. Appliance actions use the existing ESP32 /control and /all endpoints.
- Localized command replies are sent to the existing /speak endpoint, which proxies to TTS_SERVICE_URL (default http://127.0.0.1:8766).
- Improved Unicode normalization, longest-phrase matching and language-specific Whisper prompts.
- Explicitly selected ASR language is retained for the reply/TTS language.

Apply only after backing up your current app.py. Do not overwrite .env, databases, virtual environments, tts_service.py or ESP32 firmware. Test locally before any GitHub push or Render deployment.
