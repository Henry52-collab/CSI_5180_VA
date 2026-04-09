import os
from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename

from pipeline.wake_word import process as process_wakeword
from pipeline.user_verification import process as process_verify
from pipeline.asr import ASRModule
import soundfile

import librosa 

ALLOWED_EXTENSIONS = {'wav', 'webm'} # TODO: Convert from webm to wav (is this needed?)

app = Flask(__name__)

import io

system_state = {
    "unlocked": False,
    "wake": False
}

def is_valid_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/api/verify", methods=["POST"])
def verify_voice():

    return_json = {}
    return_json["module"] = "verify"
    return_json["success"] = False
    return_json["data"] = {}

    if "text" in request.form:
        text = request.form.get("text")

        if text == "yes": # TEMPORARY BYPASS - CHANGE THIS
            system_state["unlocked"] = True
            return_json["success"] = True
            return_json["data"] = {"bypass": True}

    elif "file" in request.files:
        file = request.files['file']

        if file and is_valid_file(file.filename):

            audio = soundfile.SoundFile(io.BytesIO(file.read()))

            result = process_verify(audio)

            return_json["success"] = result["verified"]
            system_state["unlocked"] = result["verified"]
            return_json["module"] = "verify"
            return_json["data"] = result

    return return_json

        
@app.route("/api/wake", methods=["POST"])
def wake_detection():


    return_json = {}
    return_json["module"] = "wake"
    return_json["success"] = False
    return_json["data"] = {}

    if "text" in request.form:
        text = request.form.get("text")

        if text.lower() == "hey atlas": # TEMPORARY BYPASS - CHANGE THIS
            system_state["unlocked"] = True
            return_json["success"] = True
            return_json["data"] = {"bypass": True}

    elif "file" in request.files:
        file = request.files['file']

        return_json = {}
        return_json["module"] = "wake"

        if file and is_valid_file(file.filename):

            audio = soundfile.SoundFile(io.BytesIO(file.read()))

            result = process_wakeword(audio)

            system_state["wake"] = result["detected"]

            return_json["success"] = result["detected"]
            return_json["data"] = result
    return return_json

# NOT COMPLETE
@app.route("/api/pipeline")
def pipeline():
    asr_module = ASRModule()
    file = request.files['file']

    if file.filename == '':
        return
    if file and is_valid_file(file.filename):
        audio, sr = librosa.load(io.BytesIO(file.read()), sr=16000, mono=True)

        transcribed_text = asr_module.process(audio)

        if not transcribed_text:
            return None

@app.route("/api/state")
def get_state():
    return system_state # temporary
