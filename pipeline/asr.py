import whisper

# Domain prompt — biases the Whisper decoder toward vocabulary Atlas expects
# to hear. Dramatically reduces hallucination on numbers and proper nouns
# (movie titles, years like "2012"), and stops the model from wandering into
# non-English tokens when audio is slightly noisy.
DOMAIN_PROMPT = (
    "Atlas is a voice assistant. The user asks about movies (cast, director, "
    "plot, rating, genre, similar movies, trending, upcoming), weather in "
    "cities, timers, and a virtual pet named Doro (feed, play with, pet, "
    "wash, put to sleep, wake up, give a treat, check status, rename). "
    "Movie titles may contain years like 2012 or 1999."
)


class ASRModule():
    def __init__(self, model_name="small.en"):
        # small.en: English-only, 244M params, markedly more accurate than base
        # and still fast enough on CPU (~1s per short utterance). medium.en is
        # better still but ~3x slower — use it if GPU is available and you want
        # near-perfect transcription.
        print(f"[ASR] loading Whisper model: {model_name} ...")
        self.asr_model = whisper.load_model(model_name)
        print(f"[ASR] model ready.")

    def process(self, audio_path):
        try:
            transcribed_text = self.asr_model.transcribe(
                audio_path,
                language="en",
                fp16=False,
                verbose=False,
                initial_prompt=DOMAIN_PROMPT,
                # Suppress runaway hallucination on silence/noise
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