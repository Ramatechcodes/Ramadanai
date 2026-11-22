# RAMATECH HOME AI — Full ESP32-only upgrade

This upgrade package is based on your uploaded source archive. It keeps the ESP32 relay pins, I2C LCD pins, local web routes, cloud WebSocket protocol, time/date, voice/TTS companion and time-credit demonstration. The Arduino UNO dependency and its sensor polling/telemetry have been removed.

Start with `documentation/SETUP_GUIDE.md`.

Main files:
- `esp32/RAMATECH_HOME_AI_ESP32_ONLY.ino` — ESP32-only firmware, AP+STA local Wi-Fi and cloud connectivity.
- `render_cloud/` — responsive cloud dashboard and Node WebSocket relay; includes typed commands and TETFund presentation scripts.
- `python_voice/` — Faster-Whisper multilingual companion and optional MMS TTS service.
- `original/` — selected unmodified source files for comparison.

No credentials have been copied from the private `.env` in your archive. Add your own Wi-Fi password, device token and Render access code locally. This source package has not been flashed to your physical ESP32 or deployed to Render.
