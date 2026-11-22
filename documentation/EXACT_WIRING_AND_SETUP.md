# RAMADAN HOME AI — wiring and bring-up guide (existing parts only)

## What this package does and does not do

- Keeps the supplied `original/` files unchanged.
- Uses the ESP32 as the main relay, LCD, Wi-Fi and cloud controller.
- Uses the Uno as an I2C sensor slave for the HC-SR04, soil probe module and one digital IR module.
- Uses the PC browser microphone + existing local Faster-Whisper recording page. A browser speech-recognition wake-word mode is included as an optional convenience; it depends on Chrome/Edge speech-recognition support and an internet connection.
- Uses the Render HTTPS dashboard microphone on iPhone and Android where the browser exposes Web Speech Recognition. Browser language coverage differs; if unavailable, use the PC Whisper page or type a command.
- Includes a time-credit prepaid *demonstration*, not kWh metering. No current/voltage sensor exists in the supplied hardware.
- Does not claim a Flutterwave payment is implemented. The dashboard's demo top-up button adds test minutes only. Real payment-to-credit needs a persistent transaction database and server-side Flutterwave verification before enabling it.

## Board and sensor identification

From the supplied photo, the clearly identifiable items are ESP32 DevKit, Arduino Uno, 4-channel relay board, 16x2 LCD with I2C backpack, HC-SR04 ultrasonic module, soil-moisture probe and comparator board, and small sensor modules with blue trimmers. Connect only one IR module after confirming its `VCC`, `GND`, `OUT` labels. The blue component covered by glue is not confidently identifiable from the photo; leave it disconnected until its label/model is confirmed. Do not guess its pinout.

## Important power and logic rules

1. Use USB 5V power for the ESP32 and Uno, preferably separate USB ports/cables. Join grounds between ESP32, Uno and relay control supply.
2. Do not join two separate +5V rails together. Do not feed 5V into ESP32 3V3 or GPIO pins.
3. Power the Uno and its HC-SR04/soil/IR sensors at 5V from the Uno USB supply.
4. Power the LCD backpack from ESP32 3V3 for this direct shared I2C arrangement. This keeps its I2C pull-ups at 3.3V. The LCD may have reduced contrast or fail at 3.3V on some modules. If it does not work, stop: do not simply move it to 5V and leave SDA/SCL directly connected to the ESP32. A level shifter would then be required, but is not part of the currently available parts.
5. The Uno's A4/A5 I2C bus must not have pull-ups to 5V. Do not use `INPUT_PULLUP` on A4/A5. The ESP32/LCD bus must be pulled up to 3.3V only.
6. Relay module coil supply is 5V. The ESP32 GPIOs must be able to trigger the relay input at 3.3V. Test the module with no load first. Some 5V relay boards do not reliably accept 3.3V logic.
7. Start with relay contacts unloaded. For exhibition, switch only low-voltage DC demonstration loads. Do not connect mains wiring or household appliances to this prototype.

## ESP32 wiring

| ESP32 DevKit | Component | Pin |
|---|---|---|
| GPIO25 | Relay IN1 | Light |
| GPIO26 | Relay IN2 | Rope light |
| GPIO27 | Relay IN3 | Fan |
| GPIO33 | Relay IN4 | TV / spare output |
| GND | Relay GND | Common control ground |
| 5V/VIN | Relay VCC | Only if the relay board is powered from the same suitable regulated 5V source; otherwise use its separate 5V supply and common GND |
| GPIO21 | LCD SDA + Uno A4/SDA | Shared I2C SDA, 3.3V pull-up only |
| GPIO22 | LCD SCL + Uno A5/SCL | Shared I2C SCL, 3.3V pull-up only |
| 3V3 | LCD backpack VCC | Try only if the backpack/LCD operates correctly at 3.3V |
| GND | LCD GND | Common ground |

The original firmware uses active-LOW relay logic (`LOW = ON`, `HIGH = OFF`). Keep that only if your actual relay board behaves that way. The firmware starts all relays OFF.

## Arduino Uno wiring

| Uno | Component |
|---|---|
| 5V | HC-SR04 VCC, soil-module VCC, IR-module VCC |
| GND | All sensor grounds and common ESP32 ground |
| D9 | HC-SR04 TRIG |
| D10 | HC-SR04 ECHO |
| A0 | Soil module AO |
| D2 | Soil module DO (optional; firmware currently reports analog A0) |
| D3 | IR module OUT |
| A4/SDA | ESP32 GPIO21 shared I2C SDA |
| A5/SCL | ESP32 GPIO22 shared I2C SCL |

Uno sketch I2C address: `0x12`. LCD address in the supplied ESP32 sketch: `0x27` (some backpacks use `0x3F`; if blank, scan/confirm address before changing it).

## Upload order

1. Disconnect relay loads. Upload `arduino_uno/ramadan_uno_sensor_slave.ino` to the Uno. Open Serial Monitor at 9600 and check distance, soil raw and IR readings.
2. Connect I2C SDA/SCL and common ground as described. Do not connect Uno 5V to ESP32 3V3 or 5V.
3. Open `esp32/RAMATECH_HOME_AI_Multilingual_Compatible.ino`. Install the existing project libraries: ESP32 board support, LiquidCrystal_I2C, ArduinoJson and WebSocketsClient. Preferences is included with the ESP32 Arduino core.
4. Set Wi-Fi SSID/password, Render host, device ID and the same `DEVICE_TOKEN` as the Render service. Change `METER_ADMIN_KEY` from the placeholder.
5. Confirm LCD backpack works at 3.3V before connecting it to ESP32 I2C. Upload the ESP32 sketch and open Serial Monitor at 115200.
6. Verify `/status` and `/meter/status` from a browser on the same Airtel router using the ESP32's printed IP address.
7. Test each relay with no load. Then test one low-voltage DC load at a time through COM and NO.
8. Test time credit: `http://ESP32_IP/meter/topup?minutes=5&key=YOUR_DEMO_KEY`. Never publish this key or expose this endpoint to the public internet.
9. Start the PC Python companion. Use `Start recording (Whisper)` for multilingual recognition. The optional browser wake-word mode detects the word RAMADAN using browser speech recognition; it is not an offline always-on wake-word engine.
10. Deploy the updated `render_cloud/` files to the existing Render service. Set `DEVICE_TOKEN`, `DEVICE_ID=RAMATECH_HOME_01`, and `ACCESS_CODE` in Render. Do not use example secrets.
11. Open the Render HTTPS dashboard on iPhone/Android, connect using the access code, allow microphone access, select language and tap Speak to RAMADAN. Add to Home Screen if desired.

## PC and phone microphone arrangement

- PC: open `http://127.0.0.1:8765` in Chrome/Edge on the PC. The Whisper recording button records through the PC microphone and sends audio to the local Python service. This is the more capable multilingual path.
- PC optional wake mode: the browser listens for the word RAMADAN using its Web Speech API. It depends on browser and internet support; leave the tab open and keep the PC awake.
- iPhone/Android: open the Render HTTPS dashboard. The browser microphone feature uses Web Speech API. Language support is browser-dependent; not every browser provides Yoruba, Hausa or Igbo recognition. Use typed commands if recognition is unavailable.
- Both devices control the same ESP32 via the Render WebSocket cloud path. The PC Python companion also has local direct-ESP32 controls through `ESP32_URL` when the PC and ESP32 share the Airtel router.

## Prepaid demonstration limitation

The ESP32 stores prepaid demo seconds in Preferences and deducts seconds while any of the four relays is ON. At zero, all relays turn OFF. This is a time-based demonstration, not actual energy measurement, not a utility meter, and not kWh accounting. The cloud dashboard button adds demonstration minutes through the authenticated Render WebSocket. It is not Flutterwave and must not be described as a verified cash recharge. Do not use it for real electricity billing.

## Troubleshooting

- LCD blank: verify I2C address (0x27/0x3F), 3.3V operation, contrast trimmer, SDA/SCL and ground. Do not apply 5V I2C pull-ups to ESP32.
- Relay does not click: verify active-LOW input, 5V coil supply, common ground and 3.3V trigger compatibility. Never test with mains.
- Uno sensor data missing: verify I2C address 0x12, A4/A5, common ground and that the I2C bus pull-ups are 3.3V only.
- ESP32 offline on Render: check Wi-Fi, device token, device ID, Render service logs and WSS URL.
- Phone mic missing: use the HTTPS Render URL, allow microphone permission, try current Safari/Chrome, or type the command. Web Speech API is not guaranteed on every device/browser.
- PC Whisper errors: use the existing venv and `pip install -r requirements.txt`; ensure the model downloads once while online.
