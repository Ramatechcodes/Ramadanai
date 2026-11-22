
import torch
import soundfile as sf
from transformers import VitsModel, AutoTokenizer

MODEL = "facebook/mms-tts-yor"

print("Loading Yoruba voice...")
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = VitsModel.from_pretrained(MODEL)

model.eval()

text = "E kaaro. Kaabo si ile wa. Oruko mi ni Ramadan."

print("Generating Yoruba speech...")

inputs = tokenizer(text, return_tensors="pt")

with torch.no_grad():
    output = model(**inputs).waveform

audio = output.squeeze().cpu().numpy()

sf.write("ramadan_yoruba_test.wav", audio, model.config.sampling_rate)

print("SUCCESS! Audio saved as ramadan_yoruba_test.wav")
