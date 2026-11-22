# RAMADAN HOME AI — existing ZIP additive upgrade

The complete supplied project is preserved under `original/`. The working source is in `esp32/`, `arduino_uno/`, `python_voice/`, and `render_cloud/`.

Read `documentation/EXACT_WIRING_AND_SETUP.md` before wiring. This package does not add any hardware that was not in the user's photograph. The prepaid feature is a time-based demo, not kWh measurement. Flutterwave real payment integration is deliberately not enabled until a persistent payment ledger and server-side transaction verification are configured.

## Windows PC setup

```bat
cd /d path\to\RAMADAN_HOME_AI_UPGRADE\python_voice
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Set `.env` to your real local ESP32 IP:

```env
ASSISTANT_NAME=RAMADAN
ESP32_URL=http://192.168.1.xxx
WHISPER_MODEL=base
```

Run:

```bat
uvicorn app:app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765` on the PC. Use Start recording (Whisper) for the multilingual speech path. Wake-word mode uses the browser SpeechRecognition API and depends on browser/network support.

## Render deployment

Deploy the updated `render_cloud/` folder to the existing Render Node service. Build: `npm install`; start: `npm start`. Keep your actual Render environment variables private: `DEVICE_TOKEN`, `DEVICE_ID=RAMATECH_HOME_01`, `ACCESS_CODE`. The ESP32 firmware must use the same device token and device ID.

## What is preserved / limitations

- `original/` is an unchanged copy of the original extracted package.
- Existing ESP32 relay pins and WebSocket device protocol are retained.
- Arduino Uno reports HC-SR04, soil analog and IR digital readings to ESP32 via I2C address 0x12.
- ESP32 stores time-based prepaid demo seconds and disconnects all relay outputs at zero.
- The phone dashboard supports browser speech recognition where available; browser language coverage varies.
- No current/voltage detector is present, so true kWh measurement is not possible.
- No Flutterwave payment integration is activated in this package. The dashboard's demo top-up is not a payment.
