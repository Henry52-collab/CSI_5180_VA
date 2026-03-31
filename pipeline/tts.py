import edge_tts
from playsound3 import playsound
import asyncio

# THIS FUNCTION IN GENERAL IS A PLACEHOLDER - needs the emotion process stuff
async def generate_tts(text, voice="en-US-JennyNeural"):
    output_file = "output.mp3" # PLACEHOLDER

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

    return output_file

def process(text):
    audio_file = asyncio.run(generate_tts(text))
    playsound("output.mp3") # PLACEHOLDER