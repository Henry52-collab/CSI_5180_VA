import whisper

class ASRModule():
    def __init__(self):
        self.asr_model = whisper.load_model("base")


    def process(self, audio):

        try:
            transcribed_text = self.asr_model.transcribe(
                audio,
                langauge="en",
                fp16=False,
                verbose=False
            )["text"]
        except:
            print("Something went wrong")
            transcribed_text = None

        return transcribed_text

    def bypass(self, text):
        if text.lower() == "yes":
            return None, False
        return text, True