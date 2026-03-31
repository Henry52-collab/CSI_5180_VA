import whisper


def process(audio_path):

    asr_model = whisper.load_model("base")
    try:
        transcribed_text = asr_model.transcribe(
            audio_path,
            langauge="en",
            fp16=False,
            verbose=False
        )["text"]
    except:
        print("Something went wrong")

    return transcribed_text

def bypass(text):
    return text # TEMPORARY