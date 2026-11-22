# RAMATECH HOME AI — ESP32-only full upgrade

## Hardware and retained features

- One ESP32 DevKit is the only controller. No Arduino UNO is used or required.
- One 16x2 I2C LCD (address 0x27 by default; use 0x3F only if your backpack uses it).
- One 4-channel relay module.
- Relay mapping is preserved: GPIO25 light, GPIO26 rope light, GPIO27 fan, GPIO33 TV.
- LCD mapping is preserved: SDA GPIO21, SCL GPIO22.
- Active-LOW relay logic is preserved from the supplied firmware (LOW=ON, HIGH=OFF). Confirm this against your actual board before connecting a load.
- Local HTTP dashboard/routes, four relay controls, all-on/all-off, date/time, LCD command feedback, cloud WebSocket, heartbeat, and time-credit demonstration remain in the ESP32 sketch.

## Connectivity

The ESP32 runs Wi-Fi AP+STA:

1. Local fallback hotspot: SSID `RAMATECH_HOME_AI`, password `RAMATECH2026`, IP normally `192.168.4.1`.
2. Router Wi-Fi: set `WIFI_SSID` and `WIFI_PASSWORD` in the sketch. This gives the ESP32 internet access for the cloud link while its fallback AP remains available.
3. Local dashboard: connect a phone to the ESP32 AP and open `http://192.168.4.1/`. If connected through the router, open `http://ESP32_STATION_IP/`.
4. Remote dashboard: deploy `render_cloud/` to the existing Render Node service and open its HTTPS URL. The ESP32 must have router internet access for remote cloud control.

The ESP32 AP and router Wi-Fi operate together. If your router uses the same 192.168.4.0/24 subnet, change the AP subnet in firmware before use. The AP password is a starter value; change it before public deployment.

## ESP32 upload

1. Disconnect all relay loads before testing.
2. Arduino IDE: select your ESP32 board and COM port.
3. Install ESP32 board support and libraries: `LiquidCrystal_I2C`, `ArduinoJson` (6.x compatible with the supplied code), and `WebSockets` (Links2004 WebSocketsClient).
4. Open `esp32/RAMATECH_HOME_AI_ESP32_ONLY.ino`.
5. Set `WIFI_SSID`, `WIFI_PASSWORD`, `DEVICE_TOKEN`, and `METER_ADMIN_KEY`. The device token must exactly match Render's `DEVICE_TOKEN`. Use long random secrets; do not commit them to GitHub. For the Python companion, set `ESP32_API_TOKEN` to exactly the same value as `METER_ADMIN_KEY` in its `.env` file.
6. Keep `DEVICE_ID` as `RAMATECH_HOME_01` and cloud host as your existing Render hostname unless you have changed it.
7. Upload; open Serial Monitor at 115200 baud. Confirm AP IP, router IP, LCD, and cloud authentication messages.
8. Test each relay with no load first. Test only low-voltage demonstration loads until a qualified electrician has checked mains wiring, enclosure, protection and relay ratings.

## Wiring

| ESP32 | Connect to |
|---|---|
| GPIO25 | Relay IN1 — Light |
| GPIO26 | Relay IN2 — Rope light |
| GPIO27 | Relay IN3 — Fan |
| GPIO33 | Relay IN4 — TV |
| GPIO21 | LCD SDA |
| GPIO22 | LCD SCL |
| 3V3 | LCD backpack VCC only if the LCD/backpack is confirmed to work at 3.3V |
| GND | LCD GND and relay control GND |
| suitable regulated 5V | Relay board VCC / JD-VCC according to its printed labels and board design |

Do not put 5V on ESP32 GPIO pins. Many I2C LCD backpacks pull SDA/SCL up to their VCC; if the backpack requires 5V, use a proper bidirectional I2C level shifter. Do not connect 5V pull-ups directly to ESP32 GPIO21/22. Relay board 3.3V input compatibility varies; verify before relying on it. Keep relay contacts unloaded during initial tests.

## Render cloud deployment

Deploy the contents of `render_cloud/` as the Node service root:

- Build: `npm install`
- Start: `npm start`
- Runtime: Node 20+

Set Render environment variables:

- `DEVICE_TOKEN`: same long random token compiled into ESP32 sketch
- `DEVICE_ID`: `RAMATECH_HOME_01`
- `ACCESS_CODE`: private dashboard login code

Do not use example credentials in production. The Render service remains a small WebSocket relay; AI speech recognition is not hosted on this small Node service.

## Multilingual voice companion (optional local PC)

This is the higher-control speech recognition path. It uses the included Faster-Whisper Python companion and command phrase map for English, Yoruba, Hausa and Igbo. It runs on a PC on the same Wi-Fi as the ESP32.

On Windows, from `python_voice`:

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set `ESP32_URL` to the ESP32's reachable address. For the ESP32 hotspot this is `http://192.168.4.1`; for router mode use the ESP32 station IP. Then run `start_voice_companion.bat`. Open `http://127.0.0.1:8765` on the PC. The server listens on `0.0.0.0`, so a phone on the same LAN can reach `http://PC_LAN_IP:8765` for the companion UI. However, many mobile browsers require HTTPS (or localhost) before granting microphone access; for reliable phone microphone use, open the Render HTTPS dashboard. The PC local companion can use localhost for microphone capture.

The first Whisper model load downloads model files and may take time. `base` is a practical CPU starting point. `small` may improve some recognition but needs more memory/CPU. Yoruba, Hausa and Igbo recognition quality varies by accent, microphone, noise and model coverage. Use short, clear commands and a close microphone. Do not assume the 2-second target is guaranteed for cloud/Whisper speech.

### Optional generated TTS voices

The included `tts_service.py` uses separate MMS TTS models for English, Yoruba, Hausa and Igbo. It is optional and may require substantial disk space, RAM and first-run downloads. Install separately with `pip install -r tts_requirements.txt`, then run `start_tts_service.bat`. The Python companion uses it on port 8766. If it is unavailable, its dashboard falls back to browser speech synthesis. Browser voice availability and pronunciation differ by phone/OS; verify each language on the actual presentation device.

## TETFund exhibition mode

The Render dashboard includes four-language presentation scripts: welcome, project explanation and motivational message. Select the presentation language, then tap the relevant button. Test the spoken output on the exact phone/speaker before the event. The translations are draft exhibition scripts; have a fluent speaker review local wording and pronunciation before public presentation.

Suggested live sequence:

1. Welcome guests in English or the event language.
2. Introduce RAMATECH HOME AI and RAMATECHCODE LAB.
3. Demonstrate light, rope light, fan and TV relay control.
4. Show typed commands and the microphone interface.
5. Switch language and repeat one short command.
6. Explain local Wi-Fi vs internet/cloud operation.
7. Deliver the innovation and youth-motivation messages.

## Performance expectations

- Typed/local appliance commands are short local HTTP/WebSocket messages and should normally respond quickly on a healthy LAN.
- Cloud relay adds internet and server latency.
- Speech recognition must first capture audio and run recognition. Browser-native recognition and Whisper are not guaranteed to finish within two seconds, especially on low-power PCs or for lower-resource languages.
- The fastest demonstration flow is typed command or short local command; keep the Whisper model warmed up before the event.

## Safety and limitations

- No Uno, ultrasonic sensor, soil sensor or IR sensor is used in this build; those telemetry references have been removed from the ESP32-only firmware/cloud status model.
- The retained prepaid counter is a time-based demonstration, not an electrical energy meter and not kWh measurement.
- The demo time-credit function is not proof of payment. Do not use it for real billing.
- Never expose the demo admin key or device token. Do not publish `.env` or firmware containing secrets.
- Mains wiring can cause fire, shock or death. Use an appropriately rated enclosure, fusing, isolation, earthing and a qualified electrician. Exhibition testing should use low-voltage demo loads.


## Local MMS TTS — second CMD window (no domain required)

Keep `TTS_SERVICE_URL=http://127.0.0.1:8766` in `python_voice/.env`. In a second Windows CMD window, change directory to `python_voice`, create/activate `.venv-tts`, install `tts_requirements.txt`, then run `python -m uvicorn tts_service:app --host 127.0.0.1 --port 8766`. Alternatively run `start_tts_local.bat` after creating the environment. This is local to the PC; it is not a public online TTS endpoint. The ESP32 continues to use the Render WebSocket settings in its `.ino` file.
