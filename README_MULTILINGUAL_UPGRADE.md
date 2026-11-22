# RAMATECH HOME AI — Multilingual Upgrade Pack

This is an additive upgrade. The original project is preserved in `original/`. The compatible ESP32 sketch is in `esp32/`, and the new Python voice companion is in `python_voice/`.

## Architecture (keeps Python off Render)

- **Render:** keep running the existing lightweight Node.js WebSocket cloud server (`render_cloud/server.js`). It continues to relay authenticated device status/commands. Do not deploy the Python Whisper service to Render's free instance.
- **ESP32:** keep the same four active-LOW relay outputs, LCD wiring, local HTTP routes and cloud WebSocket protocol from the supplied Phase 6B sketch.
- **Python companion:** run on your Windows PC or another always-on computer on the same Wi-Fi as the ESP32. It performs multilingual speech-to-text locally with `faster-whisper` (CPU/int8), and gets weather from the free Open-Meteo API. This workload uses your computer's RAM, not Render's.
- **Browser speech output:** uses voices installed on the computer. Yoruba/Hausa/Igbo TTS voices are not guaranteed to exist on every Windows/iPhone/browser. The UI falls back to an installed English voice if the requested language voice is unavailable.

## Supported interaction

The Python companion accepts English, Yoruba (`yo`), Hausa (`ha`) and Igbo (`ig`) speech/typed text. Whisper automatically detects spoken language; choose **Auto detect from voice**. Select Olamide, Rasheed, Ifeanyi or Usman as the assistant name. It includes date, time, weather, appliance control and status commands.

Language recognition is best-effort. Yoruba, Hausa and Igbo are lower-resource speech-recognition languages than English; accuracy varies with accent, recording quality and model. The included `base` model is a practical starting point. On a more powerful PC, set `WHISPER_MODEL=small` for potentially better recognition at higher RAM/CPU cost. The first run downloads the model to the PC.

## 1. Install Python companion on Windows

Install Python 3.10–3.12 (64-bit), then open Command Prompt:

```bat
cd path\to\Ramatech_HOME_AI_Multilingual_Upgrade\python_voice
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set the ESP32's actual local IP address:

```env
ASSISTANT_NAME=Olamide
ESP32_URL=http://192.168.1.100
WHISPER_MODEL=base
```

Find the ESP32 IP in your router's connected-device list, or check the ESP32 Serial Monitor at 115200 baud. The ESP32 and PC must be on the same Wi-Fi. Do not put the ESP32's local IP into Render environment variables.

Start the companion:

```bat
uvicorn app:app --host 127.0.0.1 --port 8765
```

Open **http://127.0.0.1:8765** in Chrome or Edge on that same PC. Allow microphone access. On the first voice request, Whisper downloads the model; wait for that download to finish. You can use typed commands immediately.

For Windows convenience, `start_voice_companion.bat` activates the virtual environment and starts the service.

## 2. ESP32 firmware

Open `esp32/RAMATECH_HOME_AI_Multilingual_Compatible.ino` in Arduino IDE. It retains the supplied Phase 6B pin assignments and existing routes/protocol. Before uploading:

1. Select your ESP32 board and COM port.
2. Install the same libraries already used by your working project: **ArduinoJson**, **WebSockets**, and **LiquidCrystal_I2C** (plus ESP32 board support).
3. Set `WIFI_SSID` and `WIFI_PASSWORD`.
4. Set `CLOUD_HOST` to your actual Render hostname.
5. Set `DEVICE_TOKEN` to the exact same long random token configured as `DEVICE_TOKEN` on Render.
6. Confirm relay board is active-LOW as in your original wiring.
7. Upload and open Serial Monitor at 115200 baud.

**Hardware safety:** disconnect mains power while wiring. Do not change relay pins or relay polarity unless your physical module is different. Use a properly rated, enclosed relay/contactor and qualified electrician for mains loads.

## 3. Render free deployment

Keep your current Node service and existing Render service. Deploy `render_cloud/` as the Node service root (or retain your existing root if it already points to these files). Runtime: Node 20+. Build command: `npm install`; Start command: `npm start`.

Set environment variables in Render:
- `DEVICE_TOKEN` = long random secret, identical to the ESP32 sketch
- `DEVICE_ID` = `RAMATECH_HOME_01`
- `ACCESS_CODE` = a private dashboard access code

Do not commit real Wi-Fi passwords, device tokens or access codes to GitHub. The original uploaded project contained a Wi-Fi password and fixed device token; the new sketch replaces those with placeholders. Change your Wi-Fi password if the original credential is still active and was shared beyond your private device.

**RAM note:** Python and Whisper are not part of the Render deployment. Render continues to run the existing small Node.js relay. Weather is fetched from Open-Meteo; no weather API key or database is required.

## 4. Commands to try

English:
- `What is today's date?`
- `What time is it?`
- `What's the weather today in Lagos?`
- `Turn on the fan`
- `Turn off the light`
- `Turn everything off`
- `What is the appliance status?`

Yoruba examples:
- `Tan ina`
- `Pa ina`
- `Oju ojo` (weather)

Hausa examples:
- `Kunna fitila`
- `Kashe fitila`
- `Yanayi` (weather)

Igbo examples:
- `Gbanye ọkụ`
- `Gbanyụọ ọkụ`
- `Ihu igwe` (weather)

The phrase matcher includes starter phrases, not a full natural-language grammar. Add variants to `devices`, `on_words` and `off_words` in `python_voice/app.py` to improve regional phrasing.

## 5. Existing features and limitations

The supplied original folder remains intact for comparison, including the original web dashboard, Android APK, icons, and both ESP32 sketches. The compatible sketch is copied from the existing Phase 6B firmware rather than replacing its relay hardware design. The Python voice companion is an additional local interface; it does not silently replace the deployed dashboard.

The original browser speech recognition is still available in the original dashboard, but browser-native speech recognition often has limited language coverage. Use the Python companion for the multilingual recognition path.

This package is a source upgrade, not a claim that it has been flashed to your ESP32 or deployed to your Render account. Test on the bench before connecting mains appliances.
