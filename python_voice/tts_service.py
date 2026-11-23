import gc
import io
import logging
import threading
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import torch
import soundfile as sf
from transformers import VitsModel, AutoTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MODELS = {
    "en": "facebook/mms-tts-eng",
    "yo": "facebook/mms-tts-yor",
    "ha": "facebook/mms-tts-hau",
    "ig": "rnjema-unima/mms-tts-ibo-baseline",
}
LANGUAGE_NAMES = {"en":"English","yo":"Yoruba","ha":"Hausa","ig":"Igbo"}

app = FastAPI(title="RAMADAN HOME AI Offline TTS")
loaded_language = None
tokenizer = None
model = None
model_lock = threading.Lock()
@app.on_event("startup")
def startup_load_voice():
    logging.info("Starting RAMADAN HOME AI TTS engine...")
    try:
        with model_lock:
            load_language("en")
        logging.info("English default voice loaded successfully.")
    except Exception:
        logging.exception("TTS startup voice loading failed.")

class SpeechRequest(BaseModel):
    text: str
    language: str = "en"

def load_language(language):
    global loaded_language, tokenizer, model
    if language not in MODELS:
        language = "en"
    if loaded_language == language and model is not None and tokenizer is not None:
        return
    logging.info("Loading %s offline voice model...", LANGUAGE_NAMES[language])
    # Release the previous language model before loading the next one.
    model = None
    tokenizer = None
    loaded_language = None
    gc.collect()
    tokenizer = AutoTokenizer.from_pretrained(MODELS[language])
    model = VitsModel.from_pretrained(MODELS[language])
    model.eval()
    loaded_language = language
    logging.info("%s voice model is ready.", LANGUAGE_NAMES[language])

@app.get("/health")
def health():
    return {"ok":True,"engine":"local MMS VITS","loaded_language":loaded_language,
            "supported_languages":list(MODELS.keys()),"device":"cpu"}

@app.post("/speak")
def speak(request: SpeechRequest):
    text = request.text.strip()
    language = request.language.lower()
    if not text:
        raise HTTPException(400,"Text cannot be empty.")
    if language not in MODELS:
        raise HTTPException(400,"Unsupported language. Use en, yo, ha or ig.")
    if len(text) > 1200:
        raise HTTPException(413,"Text is too long. Maximum is 1200 characters.")
    try:
        with model_lock:
            load_language(language)
            inputs = tokenizer(text, return_tensors="pt")
            with torch.inference_mode():
                waveform = model(**inputs).waveform.squeeze().cpu().numpy()
            audio_buffer = io.BytesIO()
            sf.write(audio_buffer, waveform, model.config.sampling_rate, format="WAV")
            audio_buffer.seek(0)
            audio_bytes = audio_buffer.read()
        return Response(content=audio_bytes, media_type="audio/wav",
            headers={"Cache-Control":"no-store"})
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Offline speech generation failed")
        raise HTTPException(500,f"Could not generate {LANGUAGE_NAMES[language]} speech: {e}")
