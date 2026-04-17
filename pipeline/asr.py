import numpy as np
import whisper

DOMAIN_PROMPT = (
    "Atlas is a voice assistant. The user asks about movies, cast, director, "
    "plot, rating, genre, similar, trending, upcoming, weather in cities, "
    "timers, and a virtual pet named Doro which can be fed, played with, "
    "petted, washed, put to sleep, woken up, given a treat, or renamed."
)

SILENCE_RMS_THRESHOLD = 0.01


class ASRModule():
    def __init__(self, model_name="small.en"):
        print(f"[ASR] loading Whisper model: {model_name} ...")
        self.asr_model = whisper.load_model(model_name)
        print(f"[ASR] model ready.")

    def process(self, audio):
        if isinstance(audio, np.ndarray):
            rms = float(np.sqrt(np.mean(audio ** 2)))
            if rms < SILENCE_RMS_THRESHOLD:
                print(f"[ASR] Audio too quiet (RMS={rms:.4f}), skipping transcription")
                return None

        try:
            transcribed_text = self.asr_model.transcribe(
                audio,
                language="en",
                fp16=False,
                verbose=False,
                initial_prompt=DOMAIN_PROMPT,
                condition_on_previous_text=False,
            )["text"]
        except Exception as e:
            print(f"ASR error: {e}")
            transcribed_text = None

        return transcribed_text

    def bypass(self, text):
        if text.lower() == "yes":
            return None, False
        return text, True