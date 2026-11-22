
import torch
import soundfile as sf
from transformers import VitsModel, AutoTokenizer

MODEL = "rnjema-unima/mms-tts-ibo-baseline"

print("Loading Igbo voice...")
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = VitsModel.from_pretrained(MODEL)
model.eval()

text = "Ndewo. Nnọọ n'ụlọ anyị. Aha m bụ Ramadan."

print("Generating Igbo speech...")

inputs = tokenizer(text, return_tensors="pt")

with torch.no_grad():
    output = model(**inputs).waveform

audio = output.squeeze().cpu().numpy()

sf.write("ramadan_igbo_test.wav", audio, model.config.sampling_rate)

print("SUCCESS! Audio saved as ramadan_igbo_test.wav")
