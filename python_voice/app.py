import os, re, json, time, uuid, sqlite3, logging, tempfile, hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, RedirectResponse, JSONResponse
from pydantic import BaseModel

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ramadan-home-ai")

APP_NAME = os.getenv("ASSISTANT_NAME", "RAMADAN")
ESP32_URL = os.getenv("ESP32_URL", "http://192.168.4.1").rstrip("/")
ESP32_API_TOKEN = os.getenv("ESP32_API_TOKEN", "")
TTS_SERVICE_URL = os.getenv("TTS_SERVICE_URL", "http://127.0.0.1:8766").rstrip("/")
FLW_SECRET_KEY = os.getenv("FLW_SECRET_KEY", "")
FLW_PUBLIC_KEY = os.getenv("FLW_PUBLIC_KEY", "")
FLW_WEBHOOK_HASH = os.getenv("FLW_WEBHOOK_HASH", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
DATABASE_PATH = os.getenv("DATABASE_PATH", "ramadan_home_ai_payments.db")
UNIT_PRICE_NGN = 100
MINUTES_PER_UNIT = 10
TZ = ZoneInfo("Africa/Lagos")
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")

app = FastAPI(title="RAMADAN HOME AI", version="2.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"]
)

# Optional ASR dependency. The app still starts if faster-whisper is not installed.
whisper_model = None
try:
    from faster_whisper import WhisperModel
    whisper_model = WhisperModel(WHISPER_MODEL_NAME, device="cpu", compute_type="int8")
    log.info("Whisper model loaded: %s", WHISPER_MODEL_NAME)
except Exception as exc:
    log.warning("Whisper is unavailable; typed commands still work: %s", exc)

def db():
    conn = sqlite3.connect(DATABASE_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS payments (
            tx_ref TEXT PRIMARY KEY, email TEXT NOT NULL, units INTEGER NOT NULL,
            amount INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            flw_id TEXT, created_at TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS credited_transactions (
            transaction_id TEXT PRIMARY KEY, tx_ref TEXT NOT NULL, credited_at TEXT NOT NULL
        )""")
init_db()

def now_lagos():
    return datetime.now(TZ)

def normalize(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def esp_get(path, params=None, timeout=5):
    try:
        r = requests.get(f"{ESP32_URL}{path}", params=params, timeout=timeout)
        r.raise_for_status()
        try: return r.json()
        except Exception: return {"ok": True, "text": r.text}
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"ESP32 connection failed: {exc}")

def esp_secure_get(path, params=None):
    if not ESP32_API_TOKEN:
        raise HTTPException(status_code=503, detail="Set ESP32_API_TOKEN in .env and the matching token in the ESP32 sketch.")
    params = dict(params or {})
    params["key"] = ESP32_API_TOKEN
    return esp_get(path, params=params, timeout=8)

class CommandBody(BaseModel):
    text: str
    language: str = "auto"

class PaymentBody(BaseModel):
    email: str
    units: int = 1
    name: str = "RAMATECH HOME AI Demo"

LANGS = {
    "en": "English", "yo": "Yoruba", "ha": "Hausa", "ig": "Igbo"
}

# Phrase matching is deliberately broad and forgiving for a live demonstration.
COMMANDS = {
    "light_on": ["turn on light", "switch on light", "light on", "tan ina", "tan ina naa", "tan ina si", "kunna haske", "kunna fitila", "gbana ina", "muo oku", "gbanwuo oku"],
    "light_off": ["turn off light", "switch off light", "light off", "pa ina", "pa ina naa", "kashe haske", "kashe fitila", "pa oku", "gbanyuo oku"],
    "rope_on": ["turn on rope light", "rope light on", "tan ina okun", "kunna igiya", "gbana ori"],
    "rope_off": ["turn off rope light", "rope light off", "pa ina okun", "kashe igiya", "gbanyuo ori"],
    "fan_on": ["turn on fan", "switch on fan", "fan on", "tan fan", "tan fanka", "kunna fanka", "gbana fan", "gbanye fan"],
    "fan_off": ["turn off fan", "switch off fan", "fan off", "pa fan", "pa fanka", "kashe fanka", "gbanyuo fan"],
    "tv_on": ["turn on tv", "switch on tv", "tv on", "tan tv", "kunna talabijin", "gbana tv", "gbanye igwe onyonyo"],
    "tv_off": ["turn off tv", "switch off tv", "tv off", "pa tv", "kashe talabijin", "gbanyuo tv", "gbanyụọ tv"],
    "all_on": ["turn on everything", "turn on all", "all on", "tan gbogbo nkan", "tan gbogbo", "kunna komai", "kunna dukkan na'urori", "gbanye ihe niile"],
    "all_off": ["turn off everything", "turn off all", "all off", "pa gbogbo nkan", "kashe komai", "kashe dukkan na'urori", "gbanyuo ihe niile"],
    "status": ["status", "check status", "device status", "what is on", "halin na'urori", "duba halin", "ipo awon ẹrọ", "ọnọdụ ngwaọrụ", "kedu ihe di na"],
    "time": ["what time is it", "tell me the time", "time now", "ago melo ni", "menene lokaci", "kedu oge"],
    "date": ["what is the date", "today date", "what day is today", "ojo wo ni", "wace rana ce", "kedu ubochi"],
    "weather": ["weather", "how is the weather", "weather today", "oju ojo", "yanayi", "ihu igwe"],
    "where": ["where are you", "where are u", "where are you now", "nibo lo wa", "ina kake", "ina kike", "ebee ka i no", "ebee ka ịnọ"],
    "greet": ["greet the audience", "greet our audience", "greet tetfund", "greet the high table", "welcome the audience", "ki gbogbo eniyan", "gaishe jama a", "kele ndi obia", "kele ndi niile"],
    "who": ["who are you", "what is your name", "introduce yourself", "ta ni e", "waye kai", "onye ka i bu"],
    "creator": ["who created you", "who made you", "your creator", "ta ni o da e", "waye ya halicce ka", "onye kere gi"],
    "help": ["help", "show commands", "list commands", "what can you do", "commands", "iranlowo", "taimako", "enyemaka"]
}

REPLIES = {
    "en": {
        "where": "I am right here with you at the exhibition, ready to help and demonstrate the RAMATECH HOME AI system.",
        "who": "I am RAMADAN, your multilingual smart home assistant. I can understand and respond in English, Yoruba, Hausa and Igbo.",
        "creator": "I was designed and developed by RAMATECHCODE LAB in Nigeria.",
        "greet": "Good day, distinguished guests. With great respect, I acknowledge the founder and representatives of TETFund, our chairman, the respected members of the high table, our royal fathers, invited guests, school leaders, exhibitors and everyone present. You are all warmly welcome. Thank you for supporting innovation, education, technology and young Nigerian inventors. I am RAMADAN, the RAMATECH HOME AI assistant, proudly developed in Nigeria by RAMATECHCODE LAB. It is an honour to welcome you.",
        "help": "You can ask me to turn the light, rope light, fan or television on or off; control all appliances; check device status; tell you the time, date or weather; ask where I am; ask who created me; or ask me to greet the audience."
    },
    "yo": {
        "where": "Mo wa nibi pelu yin ni ibi ifihan yii. Mo setan lati ran yin lowo ati lati se afihan eto RAMATECH HOME AI.",
        "who": "Emi ni RAMADAN, oluranlọwọ ile oloye. Mo le gbo ati dahun ni ede Geesi, Yoruba, Hausa ati Igbo.",
        "creator": "Ile-iṣẹ RAMATECHCODE LAB ni Naijiria lo se mi.",
        "greet": "E kaaro tabi e kaasan si gbogbo awon alejo pataki. Mo fi ibowo nla ki oludasile ati awon asoju TETFund, alaga wa, gbogbo awon omo egbe ori tabili giga, awon oba ati awon baba wa ti a bọwọ fun, awon alejo pataki, awon olori ile-iwe, awon olufihan ati gbogbo eniyan ti o wa nibi. E ku abo. E se fun atilẹyin yin fun imo tuntun, eko, imo ero ati awon odo oludasile Naijiria. Emi ni RAMADAN, oluranlọwọ RAMATECH HOME AI, ti RAMATECHCODE LAB se ni Naijiria. Inu mi dun lati ki gbogbo yin.",
        "help": "E le pase fun mi lati tan tabi pa ina, ina okun, fan ati telifisonu; dari gbogbo ohun elo; ṣayẹwo ipo wọn; sọ akoko, ọjọ ati oju ojo; beere ibi ti mo wa; beere ẹni to da mi; tabi ki n ki gbogbo alejo."
    },
    "ha": {
        "where": "Ina nan tare da ku a wannan baje kolin. A shirye nake in taimaka muku in kuma nuna yadda RAMATECH HOME AI ke aiki.",
        "who": "Ni ce RAMADAN, mataimakiyar gida mai basira. Ina iya fahimta da amsawa da Turanci, Yarbanci, Hausa da Igbo.",
        "creator": "RAMATECHCODE LAB ce ta kirkire ni a Najeriya.",
        "greet": "Barkan ku da zuwa, manyan baki. Ina gaishe da wanda ya kafa wannan shiri da wakilan TETFund, shugaban taro, dukkan manyan baki da ke zaune a babban tebur, sarakunan gargajiya da iyayen kasa, baki na musamman, shugabannin makarantu, masu baje kolin da dukkan mahalarta. Muna maraba da ku baki daya. Mun gode da goyon bayanku ga kirkire-kirkire, ilimi, fasaha da matasan masu kirkira a Najeriya. Ni ce RAMADAN, mataimakiyar RAMATECH HOME AI, wadda RAMATECHCODE LAB ta kirkira a Najeriya. Abin alfahari ne in yi muku maraba.",
        "help": "Za ku iya umartar ni in kunna ko kashe fitila, hasken igiya, fan ko talabijin; in sarrafa dukkan na'urori; in duba halinsu; in fada muku lokaci, rana ko yanayi; in fada muku inda nake; wanda ya kirkiro ni; ko in gaishe da mahalarta."
    },
    "ig": {
        "where": "Anọ m ebe a unu nọ n'ihe ngosi a ugbu a. Adị m njikere inyere unu aka ma gosi unu ka RAMATECH HOME AI si arụ ọrụ.",
        "who": "Abụ m RAMADAN, onye enyemaka ụlọ nwere ọgụgụ isi. Ana m aghọta ma na-aza n'asụsụ Bekee, Yoruba, Hausa na Igbo.",
        "creator": "RAMATECHCODE LAB dị na Naịjirịa mepụtara m.",
        "greet": "Ụtụtụ ọma ma ọ bụ ehihie ọma, ndị ọbịa niile a na-asọpụrụ. Ana m ekele onye guzobere mmemme a na ndị nnọchi anya TETFund, onye isi oche, ndị niile nọ n'oche ndị isi, ndị eze na ndị nna anyị a na-asọpụrụ, ndị ọbịa pụrụ iche, ndị isi ụlọ akwụkwọ, ndị ngosi na onye ọ bụla bịara ebe a. Nnọọ unu niile. Daalụ maka nkwado unu n'ihe ọhụrụ, agụmakwụkwọ, teknụzụ na ndị ntorobịa na-emepụta ihe ọhụrụ na Naịjirịa. Abụ m RAMADAN, onye enyemaka RAMATECH HOME AI nke RAMATECHCODE LAB mepụtara na Naịjirịa. Ọ bụ nnukwu nsọpụrụ ịnabata unu.",
        "help": "Unu nwere ike ịgwa m ka m gbanye ma ọ bụ menyụọ ọkụ, ọkụ eriri, fan ma ọ bụ tiivi; jikwaa ngwa niile; lelee ọnọdụ ha; gwa unu oge, ụbọchị ma ọ bụ ihu igwe; jụọ ebe m nọ; onye kere m; ma ọ bụ ka m kelee ndị bịara."
    }
}

def detect_language(text, requested="auto"):
    if requested in LANGS:
        return requested
    n = normalize(text)
    if any(x in n for x in ["nibo", "e ka", "tan ina", "pa ina", "ojo wo", "mo wa"]): return "yo"
    if any(x in n for x in ["ina kake", "ina kike", "kunna", "kashe", "barkan", "menene"]): return "ha"
    if any(x in n for x in ["ebee", "gbanye", "gbanyuo", "ekele", "nnọọ", "abum"]): return "ig"
    return "en"

def match_command(text):
    n = normalize(text)
    for command, phrases in COMMANDS.items():
        for phrase in phrases:
            p = normalize(phrase)
            if p and (p in n or n in p):
                return command
    # Simple English appliance fallbacks
    if "light" in n and ("on" in n or "off" in n): return "light_on" if "on" in n else "light_off"
    if "fan" in n and ("on" in n or "off" in n): return "fan_on" if "on" in n else "fan_off"
    if "tv" in n and ("on" in n or "off" in n): return "tv_on" if "on" in n else "tv_off"
    return None

def spoken_reply(text, lang):
    return REPLIES.get(lang, REPLIES["en"]).get(text, text)

def execute_command(text, language="auto"):
    lang = detect_language(text, language)
    cmd = match_command(text)
    if not cmd:
        return {"ok": False, "language": lang, "reply": {
            "en": "Sorry, I did not understand that command. Say help or show commands.",
            "yo": "E jowo, mi ko ye aṣẹ naa. E le so iranlowo tabi akojọ aṣẹ.",
            "ha": "Yi hakuri, ban fahimci umarnin ba. Ku ce taimako ko jerin umarni.",
            "ig": "Ndo, aghọtaghị m iwu ahụ. Kwuo enyemaka ma ọ bụ iwu niile."
        }[lang]}
    if cmd in ("where", "who", "creator", "greet", "help"):
        return {"ok": True, "language": lang, "command": cmd, "reply": spoken_reply(cmd, lang)}
    if cmd == "time":
        t = now_lagos().strftime("%I:%M %p")
        return {"ok": True, "language": lang, "command": cmd, "reply": f"The time in Nigeria is {t}." if lang=="en" else (f"Aago Naijiria ni {t}." if lang=="yo" else (f"Lokacin Najeriya yanzu {t} ne." if lang=="ha" else f"Oge dị na Naịjirịa bụ {t}."))}
    if cmd == "date":
        d = now_lagos().strftime("%A, %d %B %Y")
        return {"ok": True, "language": lang, "command": cmd, "reply": (f"Today is {d}." if lang=="en" else (f"Yau ita ce {d}." if lang=="ha" else f"Ọjọ oni ni {d}."))}
    if cmd == "weather":
        try:
            # Sango Ota / Ogun demonstration coordinates; change WEATHER_LAT/LON in .env if needed.
            lat = float(os.getenv("WEATHER_LAT", "6.70")); lon = float(os.getenv("WEATHER_LON", "3.23"))
            w = requests.get("https://api.open-meteo.com/v1/forecast", params={"latitude":lat,"longitude":lon,"current":"temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m","timezone":"Africa/Lagos"}, timeout=8).json()["current"]
            reply = f"Current weather is {w['temperature_2m']} degrees Celsius, humidity {w['relative_humidity_2m']} percent, wind speed {w['wind_speed_10m']} kilometres per hour."
        except Exception: reply = "I could not retrieve the weather right now."
        return {"ok": True, "language": lang, "command": cmd, "reply": reply}
    devices = {"light_on":("light","on"),"light_off":("light","off"),
               "rope_on":("rope","on"),"rope_off":("rope","off"),
               "fan_on":("fan","on"),"fan_off":("fan","off"),
               "tv_on":("tv","on"),"tv_off":("tv","off")}
    try:
        if cmd in devices:
            device, state = devices[cmd]
            result = esp_get("/control", {"device":device,"state":state})
            reply = f"{device.replace('_',' ').title()} switched {state}."
        elif cmd in ("all_on","all_off"):
            state = "on" if cmd == "all_on" else "off"
            result = esp_get("/all", {"state":state})
            reply = f"All appliances switched {state}."
        elif cmd == "status":
            result = esp_get("/status")
            reply = "Here is the current appliance status."
        else:
            result = {}
            reply = "Command completed."
        return {"ok": True, "language": lang, "command": cmd, "reply": reply, "device_data": result}
    except HTTPException as exc:
        return {"ok": False, "language": lang, "command": cmd, "reply": str(exc.detail)}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD)

@app.get("/health")
def health():
    tts_ok = False
    try: tts_ok = requests.get(f"{TTS_SERVICE_URL}/health", timeout=2).ok
    except Exception: pass
    return {"ok":True,"assistant":APP_NAME,"timezone":"Africa/Lagos","whisper_loaded":whisper_model is not None,
            "offline_tts":tts_ok,"esp32_url_configured":bool(ESP32_URL),"flutterwave_test_mode":bool(FLW_SECRET_KEY),
            "unit_price_ngn":UNIT_PRICE_NGN,"minutes_per_unit":MINUTES_PER_UNIT}

@app.post("/command")
def command(body: CommandBody):
    return execute_command(body.text, body.language)

@app.post("/speak")
def speak(request: Request, payload: dict):
    text = str(payload.get("text","")).strip()
    language = str(payload.get("language","en")).lower()
    if language not in LANGS: language = "en"
    if not text: raise HTTPException(400, "Text is required")
    try:
        r = requests.post(f"{TTS_SERVICE_URL}/speak", json={"text":text,"language":language}, timeout=90)
        if not r.ok: raise HTTPException(502, f"Offline TTS service returned {r.status_code}: {r.text[:200]}")
        return Response(content=r.content, media_type=r.headers.get("content-type","audio/wav"))
    except requests.RequestException as exc:
        raise HTTPException(503, f"Offline TTS service is not available: {exc}")

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = Form("auto")):
    if whisper_model is None: raise HTTPException(503, "Whisper is not installed or failed to load.")
    suffix = os.path.splitext(file.filename or "audio.webm")[1] or ".webm"
    content = await file.read()
    if not content: raise HTTPException(400, "Empty audio")
    if len(content) > 20 * 1024 * 1024: raise HTTPException(413, "Audio is larger than 20 MB")
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(content); tmp = f.name
        lang = None if language in ("auto","") else language
        segments, info = whisper_model.transcribe(
    tmp,
    language=lang,
    vad_filter=False,
    beam_size=5,
    condition_on_previous_text=False
)
        
        transcript = " ".join(seg.text.strip() for seg in segments).strip()
        detected = info.language or "en"
        mapped = detected if detected in LANGS else detect_language(transcript, language)
        result = execute_command(transcript, mapped)
        return {"ok":True,"transcript":transcript,"language":mapped,"command":result}
    except HTTPException: raise
    except Exception as exc:
        log.exception("Transcription failed")
        raise HTTPException(500, f"Transcription failed: {exc}")
    finally:
        if tmp and os.path.exists(tmp): os.unlink(tmp)

@app.get("/proxy/{route}")
def proxy(route: str, device: str = "", state: str = ""):
    allowed = {"control","all","status","display","time"}
    if route not in allowed: raise HTTPException(404, "Unknown ESP32 route")
    params = {"device":device,"state":state} if route=="control" else ({"state":state} if route=="all" else None)
    return esp_get("/"+route, params)

@app.get("/proxy/meter/status")
def meter_status():
    return esp_get("/meter/status")

@app.post("/mode/{mode}")
def set_mode(mode: str):
    mode = mode.upper()
    if mode not in ("HOME_AI","PREPAID"): raise HTTPException(400, "Mode must be HOME_AI or PREPAID")
    return esp_secure_get("/meter/mode", {"mode":mode})

@app.post("/payment/initialize")
def payment_initialize(body: PaymentBody):
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", str(body.email)):
        raise HTTPException(400, "Enter a valid email address.")
    if not FLW_SECRET_KEY: raise HTTPException(503, "Flutterwave test secret key is not configured in .env")
    if not PUBLIC_BASE_URL.startswith("https://"):
        raise HTTPException(503, "Set PUBLIC_BASE_URL to your public HTTPS Python app URL or secure HTTPS tunnel before accepting test payments.")
    if body.units < 1 or body.units > 100: raise HTTPException(400, "Choose between 1 and 100 units per payment.")
    amount = body.units * UNIT_PRICE_NGN
    tx_ref = "RAMATECH-" + uuid.uuid4().hex.upper()
    with db() as conn:
        conn.execute("INSERT INTO payments(tx_ref,email,units,amount,status,created_at) VALUES(?,?,?,?,?,?)",
                     (tx_ref, str(body.email), body.units, amount, "pending", now_lagos().isoformat()))
    payload = {
        "tx_ref":tx_ref, "amount":amount, "currency":"NGN",
        "redirect_url":f"{PUBLIC_BASE_URL}/payment/callback",
        "customer":{"email":str(body.email),"name":body.name},
        "customizations":{"title":"RAMATECH HOME AI","description":f"{body.units} prepaid demonstration unit(s)"},
        "meta":{"product":"RAMATECH_HOME_AI_DEMO_UNITS","units":body.units}
    }
    try:
        r = requests.post("https://api.flutterwave.com/v3/payments", json=payload,
                          headers={"Authorization":f"Bearer {FLW_SECRET_KEY}","Content-Type":"application/json"}, timeout=20)
        data = r.json()
        if not r.ok or data.get("status") != "success":
            raise HTTPException(502, f"Flutterwave checkout initialization failed: {data.get('message','Unknown error')}")
        return {"ok":True,"tx_ref":tx_ref,"amount":amount,"units":body.units,"checkout_url":data["data"]["link"]}
    except requests.RequestException as exc:
        raise HTTPException(502, f"Could not contact Flutterwave: {exc}")

def verify_and_credit(transaction_id: str):
    if not FLW_SECRET_KEY: raise HTTPException(503, "Flutterwave secret key is not configured.")
    try:
        r = requests.get(f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify",
                         headers={"Authorization":f"Bearer {FLW_SECRET_KEY}"}, timeout=20)
        data = r.json()
        if not r.ok or data.get("status") != "success": raise HTTPException(400, "Flutterwave could not verify this transaction.")
        tx = data.get("data", {})
        tx_ref = str(tx.get("tx_ref",""))
        with db() as conn:
            order = conn.execute("SELECT * FROM payments WHERE tx_ref=?", (tx_ref,)).fetchone()
            if not order: raise HTTPException(404, "Payment reference was not found.")
            if tx.get("status") != "successful" or tx.get("currency") != "NGN" or int(float(tx.get("amount",0))) != int(order["amount"]):
                raise HTTPException(400, "Payment verification failed: status, currency or exact amount did not match.")
            already = conn.execute("SELECT transaction_id FROM credited_transactions WHERE transaction_id=?", (str(transaction_id),)).fetchone()
            if already:
                return {"ok":True,"already_credited":True,"units":int(order["units"]),"amount":int(order["amount"])}
            # ESP32 is credited only after server-side Flutterwave verification.
            esp_secure_get("/meter/topup", {"minutes":int(order["units"])*MINUTES_PER_UNIT})
            conn.execute("INSERT INTO credited_transactions(transaction_id,tx_ref,credited_at) VALUES(?,?,?)",
                         (str(transaction_id),tx_ref,now_lagos().isoformat()))
            conn.execute("UPDATE payments SET status='successful',flw_id=? WHERE tx_ref=?",
                         (str(transaction_id),tx_ref))
            return {"ok":True,"already_credited":False,"units":int(order["units"]),"minutes":int(order["units"])*MINUTES_PER_UNIT,
                    "amount":int(order["amount"])}
    except requests.RequestException as exc:
        raise HTTPException(502, f"Payment verification or meter top-up failed: {exc}")

@app.get("/payment/callback", response_class=HTMLResponse)
def payment_callback(status: str = "", tx_ref: str = "", transaction_id: str = ""):
    if status != "successful" or not transaction_id:
        return HTMLResponse("<h2>Payment not completed</h2><p>No prepaid units were added. You can return to RAMATECH HOME AI and try again.</p>")
    result = verify_and_credit(transaction_id)
    return HTMLResponse(f"""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>Payment result</title></head>
    <body style='font-family:Arial;padding:30px;background:#101827;color:white'><h2>Payment verified</h2>
    <p>{result['units']} unit(s) added successfully.</p><p>{result['minutes']} minutes of demonstration time added.</p>
    <p>You may close this page and return to RAMATECH HOME AI.</p></body></html>""")

@app.post("/payment/verify")
def payment_verify(payload: dict):
    transaction_id = str(payload.get("transaction_id","")).strip()
    if not transaction_id: raise HTTPException(400, "transaction_id is required")
    return verify_and_credit(transaction_id)

@app.post("/flutterwave/webhook")
async def flutterwave_webhook(request: Request):
    if not FLW_WEBHOOK_HASH: raise HTTPException(503, "Webhook hash is not configured.")
    supplied = request.headers.get("verif-hash","")
    if not supplied or supplied != FLW_WEBHOOK_HASH: raise HTTPException(401, "Invalid webhook signature")
    payload = await request.json()
    data = payload.get("data",{})
    if data.get("id") and data.get("status") == "successful":
        try: verify_and_credit(str(data["id"]))
        except Exception: log.exception("Webhook payment verification failed")
    return {"received":True}

DASHBOARD = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RAMATECH HOME AI</title><style>
:root{--bg:#08111f;--panel:#111f33;--line:#263a55;--txt:#edf4ff;--muted:#a7b8ce;--cyan:#31d6d0;--gold:#f4bd54;--red:#ff7272}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(135deg,#07101d,#10243b);color:var(--txt);font-family:Arial,sans-serif}
header{padding:22px 5%;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}h1{margin:0;font-size:25px}small,.muted{color:var(--muted)}main{max-width:1100px;margin:auto;padding:22px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;margin:14px 0;box-shadow:0 10px 30px #0003}
.switches{display:flex;gap:10px;flex-wrap:wrap}.mode{padding:13px 20px;border-radius:12px;border:1px solid var(--line);background:#182b43;color:white;font-weight:bold;cursor:pointer}.mode.active{background:var(--cyan);color:#07101d}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}.device{background:#172a42;border:1px solid var(--line);border-radius:13px;padding:16px}
button{border:0;border-radius:10px;padding:11px 15px;background:var(--cyan);color:#07101d;font-weight:bold;cursor:pointer;margin:4px}button.secondary{background:#314761;color:white}button.off{background:#43566e;color:white}
input,select{padding:12px;border-radius:9px;border:1px solid var(--line);background:#091626;color:white;max-width:100%}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.big{font-size:32px;font-weight:bold;color:var(--gold)}.hidden{display:none!important}
#log{white-space:pre-wrap;background:#081522;padding:12px;border-radius:10px;min-height:55px;color:#b9d3ed}
.meter{height:12px;background:#263a55;border-radius:20px;overflow:hidden}.meter>div{height:100%;background:var(--cyan);width:0%}
.commandlist{columns:2;line-height:1.8}@media(max-width:600px){.commandlist{columns:1}header{padding:18px}main{padding:12px}}
</style></head><body>
<header><div><h1>🤖 RAMATECH HOME AI</h1><small>Indigenous multilingual smart-home automation prototype</small></div><div id="health">Connecting…</div></header>
<main>
<section class="panel"><h2>Choose operating mode</h2><div class="switches">
<button id="homeMode" class="mode active" onclick="changeMode('HOME_AI')">🏠 HOME AI CONTROL — FREE</button>
<button id="prepaidMode" class="mode" onclick="changeMode('PREPAID')">⚡ PREPAID METER</button></div>
<p class="muted">HOME AI mode has no token restriction. PREPAID mode uses demonstration time units.</p></section>
<section id="homePanel" class="panel"><h2>Home AI control</h2><p>Voice, typed commands and manual controls work without prepaid units in this mode.</p>
<div class="grid" id="devices"></div>
<h3>Select your speaking language</h3>

<div class="row" id="languageButtons">
    <button onclick="selectLanguage('en')" class="lang-btn">🇬🇧 English</button>
    <button onclick="selectLanguage('yo')" class="lang-btn secondary">🇳🇬 Yoruba</button>
    <button onclick="selectLanguage('ha')" class="lang-btn secondary">🇳🇬 Hausa</button>
    <button onclick="selectLanguage('ig')" class="lang-btn secondary">🇳🇬 Igbo</button>
</div>

<select id="language" onchange="refreshDeviceLabels()" style="display:none">
    <option value="en">English</option>
    <option value="yo">Yoruba</option>
    <option value="ha">Hausa</option>
    <option value="ig">Igbo</option>
</select>

<div class="row" style="margin-top:15px">
    <input id="typed" style="flex:1;min-width:220px"
    placeholder="Type your command here">

    <button onclick="sendTyped()">Send command</button>
</div><div class="row"><button id="listenBtn" onclick="toggleListening()">🎙 Start hands-free listening</button><label>Voice speed <b id="speedLabel">1.0×</b></label><input id="speed" type="range" min="0.65" max="1.5" value="1" step="0.05" oninput="speedLabel.textContent=Number(this.value).toFixed(2)+'×'"></div>
<p class="muted">After you start listening, the microphone records in short automatic sections and sends them for recognition. You do not need to press Stop after every sentence. Press Stop Listening only when you want to end the session.</p>
<div id="log">Ready.</div><audio id="player" controls class="hidden"></audio></section>
<section id="prepaidPanel" class="panel hidden"><h2>⚡ RAMATECH prepaid demonstration meter</h2>
<p class="muted">Prototype time-credit meter — no ampere, voltage or kWh sensor is used. One unit represents 10 minutes while any appliance is ON.</p>
<div class="grid"><div class="device"><small>AVAILABLE UNITS</small><div class="big" id="units">—</div></div><div class="device"><small>REMAINING TIME</small><div class="big" id="remaining">—</div></div><div class="device"><small>METER MODE</small><div class="big" id="meterMode" style="font-size:22px">—</div></div></div>
<div class="meter" style="margin:16px 0"><div id="bar"></div></div><p id="loadState" class="muted">Checking meter…</p>
<h3>Buy demonstration units</h3><div class="row"><label>Units</label><input id="buyUnits" type="number" min="1" max="100" value="1" style="width:90px" oninput="amountLabel()"><b id="amount">₦100</b></div>
<div class="row"><input id="email" type="email" placeholder="Your email address for Flutterwave receipt" style="min-width:240px;flex:1"><button onclick="buyUnits()">Buy units with Flutterwave (TEST)</button></div>
<p class="muted">₦100 per unit · 10 minutes per unit · Flutterwave test mode. No real money is charged while using test keys.</p>
<div class="grid" id="prepaidDevices"></div><div id="meterLog">Meter status will appear here.</div></section>
<section class="panel"><h2>Commands you can try</h2><p class="muted">Select a language above or leave Auto detect on. Use natural wording; these are examples, not the only accepted phrases.</p>
<div class="commandlist">
<b>English:</b><br>Turn on/off the light<br>Turn on/off the rope light<br>Turn on/off the fan<br>Turn on/off the TV<br>Turn on/off everything<br>Check status<br>What time/date is it?<br>How is the weather?<br>Where are you now?<br>Who created you?<br>Greet the audience<br>Show commands<br><br>
<b>Yoruba:</b><br>Tan ina / Pa ina<br>Tan fan / Pa fan<br>Tan TV / Pa TV<br>Tan gbogbo nkan / Pa gbogbo nkan<br>Ojo wo ni oni?<br>Nibo lo wa?<br>Ta ni o da e?<br>Ki gbogbo eniyan<br><br>
<b>Hausa:</b><br>Kunna haske / Kashe haske<br>Kunna fanka / Kashe fanka<br>Kunna talabijin / Kashe talabijin<br>Kunna komai / Kashe komai<br>Menene lokaci?<br>Ina kake?<br>Waye ya halicce ka?<br>Gaishe da jama'a<br><br>
<b>Igbo:</b><br>Gbanye oku / Gbanyuo oku<br>Gbanye fan / Gbanyuo fan<br>Gbanye TV / Gbanyuo TV<br>Gbanye ihe niile<br>Kedu oge?<br>Ebee ka i no?<br>Onye kere gi?<br>Kelee ndi obia
</div></section>
</main>
<script>
let currentMode='HOME_AI', recorder=null, stream=null, listenTimer=null, busy=false, lastText='', lastAt=0;

const names=['light','rope','fan','tv'];

const translations = {
    en: {
        light:'LIGHT',
        rope:'ROPE LIGHT',
        fan:'FAN',
        tv:'TELEVISION',
        on:'ON',
        off:'OFF',
        all:'ALL APPLIANCES',
        ready:'Ready.'
    },
    yo: {
        light:'INA',
        rope:'INA OKUN',
        fan:'FAN',
        tv:'TELIFISONU',
        on:'TAN',
        off:'PA',
        all:'GBOGBO OHUN ELO',
        ready:'Mo setan.'
    },
    ha: {
        light:'HASKE',
        rope:'HASKE IGIYA',
        fan:'FANKA',
        tv:'TALABIJIN',
        on:'KUNNA',
        off:'KASHE',
        all:'DUKKAN NA\'URORI',
        ready:'Ina shirye.'
    },
    ig: {
        light:'Ọkụ',
        rope:'Ọkụ ERIRI',
        fan:'FAN',
        tv:'IGWE ONYONYỌ',
        on:'GBANYE',
        off:'GBANYỤỌ',
        all:'NGWA NIỊLE',
        ready:'Adị m njikere.'
    }
};

function selectedLanguage(){
    const lang=document.getElementById('language').value;
    return lang==='auto'?'en':lang;
}
function selectLanguage(lang){
    document.getElementById('language').value=lang;

    document.querySelectorAll('.lang-btn').forEach(button=>{
        button.classList.add('secondary');
    });

    const buttons={
        en:0,
        yo:1,
        ha:2,
        ig:3
    };

    document.querySelectorAll('.lang-btn')[buttons[lang]]
        .classList.remove('secondary');

    refreshDeviceLabels();

    const greetings={
        en:'English selected. I am ready.',
        yo:'A ti yan ede Yoruba. Mo setan.',
        ha:'An zaɓi harshen Hausa. Ina shirye.',
        ig:'Ahọrọla asụsụ Igbo. Adị m njikere.'
    };

    log(greetings[lang]);
    speak(greetings[lang],lang);
}

function translateDevice(device){
    return translations[selectedLanguage()][device] || device.toUpperCase();
}

function translateButton(state){
    return translations[selectedLanguage()][state] || state.toUpperCase();
}
function log(t){document.getElementById('log').textContent=t}
function meterLog(t){document.getElementById('meterLog').textContent=t}
function buildDevices(target){
    document.getElementById(target).innerHTML=names.map(n=>`
        <div class="device">
            <h3>${translateDevice(n)}</h3>
            <button onclick="control('${n}','on')">
                ${translateButton('on')}
            </button>
            <button class="off" onclick="control('${n}','off')">
                ${translateButton('off')}
            </button>
        </div>
    `).join('');
}

function refreshDeviceLabels(){
    buildDevices('devices');
    buildDevices('prepaidDevices');
}

refreshDeviceLabels();
async function api(url,opts={}){let r=await fetch(url,{headers:{'Content-Type':'application/json'},...opts});let d=await r.json().catch(()=>({detail:r.statusText}));if(!r.ok)throw Error(d.detail||'Request failed');return d}
async function changeMode(mode){try{let d=await api('/mode/'+mode,{method:'POST'});currentMode=mode;document.getElementById('homePanel').classList.toggle('hidden',mode!=='HOME_AI');document.getElementById('prepaidPanel').classList.toggle('hidden',mode!=='PREPAID');document.getElementById('homeMode').classList.toggle('active',mode==='HOME_AI');document.getElementById('prepaidMode').classList.toggle('active',mode==='PREPAID');log('Mode changed to '+mode);await refreshMeter()}catch(e){log('Could not change mode: '+e.message)}}
async function control(device,state){
    const lang=selectedLanguage();

    const replies={
        en:{
            light:{on:'The light is now on.',off:'The light is now off.'},
            rope:{on:'The rope light is now on.',off:'The rope light is now off.'},
            fan:{on:'The fan is now on.',off:'The fan is now off.'},
            tv:{on:'The television is now on.',off:'The television is now off.'}
        },
        yo:{
            light:{on:'Ina ti tan.',off:'Ina ti pa.'},
            rope:{on:'Ina okun ti tan.',off:'Ina okun ti pa.'},
            fan:{on:'Fan ti tan.',off:'Fan ti pa.'},
            tv:{on:'Telifisonu ti tan.',off:'Telifisonu ti pa.'}
        },
        ha:{
            light:{on:'An kunna hasken.',off:'An kashe hasken.'},
            rope:{on:'An kunna hasken igiya.',off:'An kashe hasken igiya.'},
            fan:{on:'An kunna fanka.',off:'An kashe fanka.'},
            tv:{on:'An kunna talabijin.',off:'An kashe talabijin.'}
        },
        ig:{
            light:{on:'Agbanyela ọkụ.',off:'Anyụla ọkụ.'},
            rope:{on:'Agbanyela ọkụ eriri.',off:'Anyụla ọkụ eriri.'},
            fan:{on:'Agbanyela fan.',off:'Anyụla fan.'},
            tv:{on:'Agbanyela igwe onyonyo.',off:'Anyụla igwe onyonyo.'}
        }
    };

    try{
        let d=await api(
            '/proxy/control?device='+encodeURIComponent(device)+
            '&state='+encodeURIComponent(state)
        );

        const reply=replies[lang][device][state];

        log(reply);
        await speak(reply,lang);
        await refreshMeter();

    }catch(e){
        const errors={
            en:'I could not control the appliance. Please check the ESP32 connection.',
            yo:'Mi o le dari ohun elo naa. E jowo, e ṣayẹwo asopọ ESP32.',
            ha:'Ban iya sarrafa naurar ba. Da fatan za a duba haɗin ESP32.',
            ig:'Enweghị m ike ijikwa ngwa ahụ. Biko lelee njikọ ESP32.'
        };

        log(e.message);
        await speak(errors[lang],lang);
    }
}
async function sendTyped(){
    let t=document.getElementById('typed').value.trim();

    if(!t)return;

    const lang=selectedLanguage();

    try{
        let d=await api('/command',{
            method:'POST',
            body:JSON.stringify({
                text:t,
                language:lang
            })
        });

        log(d.reply+(d.device_data?
            '\n'+JSON.stringify(d.device_data):''));

        await speak(d.reply,d.language || lang);

    }catch(e){
        log(e.message);
    }
}
async function speak(text,language){try{let r=await fetch('/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,language})});if(!r.ok)throw Error('TTS service unavailable');let blob=await r.blob(),url=URL.createObjectURL(blob),a=document.getElementById('player');a.src=url;a.playbackRate=Number(document.getElementById('speed').value);a.classList.remove('hidden');await a.play()}catch(e){console.warn(e);if('speechSynthesis' in window){speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.lang=({en:'en-NG',yo:'yo-NG',ha:'ha-NG',ig:'ig-NG'}[language]||'en-NG');u.rate=Number(document.getElementById('speed').value);speechSynthesis.speak(u)}else{log('TTS unavailable: '+e.message)}}}
async function startListening(){try{stream=await navigator.mediaDevices.getUserMedia({audio:true});recorder=new MediaRecorder(stream);let chunks=[];recorder.ondataavailable=e=>{if(e.data&&e.data.size)chunks.push(e.data)};recorder.onstop=async()=>{if(chunks.length){let blob=new Blob(chunks,{type:recorder.mimeType||'audio/webm'});chunks=[];await sendAudio(blob)}if(stream&&recorder&&recorder.state==='inactive'&&document.getElementById('listenBtn').dataset.stop!=='1'){recorder.start();listenTimer=setTimeout(()=>{if(recorder&&recorder.state==='recording')recorder.stop()},5500)}};document.getElementById('listenBtn').dataset.stop='0';document.getElementById('listenBtn').textContent='⏹ Stop listening';recorder.start();listenTimer=setTimeout(()=>{if(recorder&&recorder.state==='recording')recorder.stop()},5500);log('Listening continuously. Speak a command.');}catch(e){log('Microphone error: '+e.message)}}
async function sendAudio(blob){if(busy||blob.size<1500)return;busy=true;try{let fd=new FormData();fd.append('file',blob,'voice.webm');fd.append('language',selectedLanguage());let r=await fetch('/transcribe',{method:'POST',body:fd}),d=await r.json();if(!r.ok)throw Error(d.detail||'Transcription failed');let t=(d.transcript||'').trim();if(t){let key=t.toLowerCase(),now=Date.now();if(key!==lastText||now-lastAt>7000){lastText=key;lastAt=now;let c=d.command;log('Heard: '+t+'\\n'+(c.reply||''));if(c.ok){
    speak(c.reply,c.language || selectedLanguage());
}}}}catch(e){console.warn(e)}finally{busy=false}}
function toggleListening(){let b=document.getElementById('listenBtn');if(!recorder||recorder.state==='inactive'&&!stream){startListening();return}if(b.dataset.stop==='1'){b.dataset.stop='0';b.textContent='🎙 Start hands-free listening';if(listenTimer)clearTimeout(listenTimer);try{if(recorder.state!=='inactive')recorder.stop()}catch(e){}if(stream)stream.getTracks().forEach(t=>t.stop());stream=null;recorder=null;log('Listening stopped.')}else{b.dataset.stop='1';b.textContent='🎙 Stopping…';if(listenTimer)clearTimeout(listenTimer);if(recorder&&recorder.state==='recording')recorder.stop();if(stream)stream.getTracks().forEach(t=>t.stop());stream=null;recorder=null;b.dataset.stop='1';b.textContent='🎙 Start hands-free listening';log('Listening stopped.')}} 
async function refreshMeter(){try{let d=await api('/proxy/meter/status');let secs=Number(d.prepaidSeconds||0),mins=Math.floor(secs/60),units=(secs/600).toFixed(2);document.getElementById('units').textContent=units;document.getElementById('remaining').textContent=mins+' min';document.getElementById('meterMode').textContent=d.mode||'—';document.getElementById('loadState').textContent=d.loadActive?'Appliance load is ON — time credit is counting down.':'No appliance load is active — time credit is not being deducted.';document.getElementById('bar').style.width=Math.min(100,(secs/3600)*100)+'%';meterLog(JSON.stringify(d,null,2))}catch(e){meterLog('Could not read meter: '+e.message)}}
function amountLabel(){let n=Math.max(1,Math.min(100,Number(document.getElementById('buyUnits').value)||1));document.getElementById('amount').textContent='₦'+(n*100).toLocaleString('en-NG')}
async function buyUnits(){let email=document.getElementById('email').value.trim(),units=Number(document.getElementById('buyUnits').value)||1;if(!email){meterLog('Enter your email address first.');return}try{let d=await api('/payment/initialize',{method:'POST',body:JSON.stringify({email,units})});location.href=d.checkout_url}catch(e){meterLog('Payment setup: '+e.message)}}
async function health(){try{let d=await api('/health');document.getElementById('health').textContent='API online · TTS '+(d.offline_tts?'ready':'offline')+' · Whisper '+(d.whisper_loaded?'ready':'offline')}catch(e){document.getElementById('health').textContent='API connection issue'}}
health();refreshMeter();setInterval(refreshMeter,5000);
</script></body></html>"""
