
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LANGA_API_KEY")
URL = "https://langa.julimer.com/v1/audio/speech"

if not API_KEY:
    print("ERROR: LANGA_API_KEY is missing from .env")
    raise SystemExit(1)

text = "Ẹ káàbọ̀! Èmi ni RAMADAN, olùrànlọ́wọ́ ilé ọlọ́gbọ́n yín. Mo lè tan ìmọ́lẹ̀, fọ́ọ̀nù àti tẹlifíṣọ̀n."

payload = {
    "input": text,
    "voice": "yo",
    "response_format": "mp3"
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

print("Connecting to Langa Yoruba voice...")

try:
    response = requests.post(
        URL,
        headers=headers,
        json=payload,
        timeout=120
    )

    if response.status_code != 200:
        print("Langa error:", response.status_code)
        print(response.text[:2000])
        raise SystemExit(1)

    with open("ramatech_yo.mp3", "wb") as audio:
        audio.write(response.content)

    print("SUCCESS! Yoruba audio saved as ramatech_yo.mp3")
    print("Open the MP3 file and listen.")

except requests.RequestException as error:
    print("Connection error:", error)
