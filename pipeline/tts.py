import pyttsx3
from playsound3 import playsound
import asyncio

# THIS FUNCTION IN GENERAL IS A PLACEHOLDER - needs the emotion process stuff


class TTSModule():
    def __init__(self):
        self.engine = pyttsx3.init()
        rate = self.engine.getProperty('rate')
        self.engine.setProperty('rate', 125)
    def process(self, text):
        self.engine.say(text)
        self.engine.runAndWait()
    

