
import torch
import soundfile as sf
from transformers import VitsModel, AutoTokenizer

MODEL = "facebook/mms-tts-hau"

print("Loading Hausa voice...")
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = VitsModel.from_pretrained(MODEL)
model.eval()

text = "Ina kwana. Barka da zuwa gidanmu. Sunana Ramadan."

print("Generating Hausa speech...")

inputs = tokenizer(text, return_tensors="pt")

with torch.no_grad():
    output = model(**inputs).waveform

audio = output.squeeze().cpu().numpy()

sf.write("ramadan_hausa_test.wav", audio, model.config.sampling_rate)

print("SUCCESS! Audio saved as ramadan_hausa_test.wav")
