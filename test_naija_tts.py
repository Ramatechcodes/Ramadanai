
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NAIJA_ASR_KEY")
URL = "https://asr.naijallm.com/v1/audio/speech"

if not API_KEY:
    print("ERROR: NAIJA_ASR_KEY missing from .env")
    raise SystemExit(1)

text = (
    "Ẹ káàbọ̀! Èmi ni RAMADAN. "
    "Mo lè ṣàkóso àwọn ohun èlò inú ilé yín. "
    "Ṣé ẹ fẹ́ kí n tan ìmọ́lẹ̀?"
)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "input": text,
    "language": "yo",
    "voice": "yoruba_female2",
    "response_format": "mp3"
}

print("Testing NaijaLLM Yoruba speech...")

try:
    response = requests.post(
        URL,
        headers=headers,
        json=payload,
        timeout=300
    )

    if response.status_code != 200:
        print("ERROR:", response.status_code)
        print(response.text[:2000])
        raise SystemExit(1)

    with open("ramadan_yoruba.mp3", "wb") as f:
        f.write(response.content)

    print("SUCCESS!")
    print("Audio saved as ramadan_yoruba.mp3")
    print("Voice:", response.headers.get("X-Voice"))
    print("Language:", response.headers.get("X-Language"))

except requests.RequestException as e:
    print("Connection error:", e)
