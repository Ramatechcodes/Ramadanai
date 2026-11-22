
import torch
import soundfile as sf
from transformers import VitsModel, AutoTokenizer

MODEL = "facebook/mms-tts-eng"

print("Loading English voice...")
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = VitsModel.from_pretrained(MODEL)
model.eval()

text = "Hello! Welcome to Ramadan Home AI. I am your intelligent smart home assistant."

print("Generating English speech...")

inputs = tokenizer(text, return_tensors="pt")

with torch.no_grad():
    output = model(**inputs).waveform

audio = output.squeeze().cpu().numpy()

sf.write("ramadan_english_test.wav", audio, model.config.sampling_rate)

print("SUCCESS! Audio saved as ramadan_english_test.wav")
