"""
Atlas VA — Flask Backend

Routes:
    POST /api/verify   — user verification (audio or passcode bypass)
    POST /api/wake     — wake word detection (audio or text bypass)
    POST /api/pipeline — full pipeline: ASR → Intent → Fulfillment → NLG (→ TTS)
    GET  /api/state    — current system state + pet status

Original verify/wake routes by Laura (abo).
Pipeline integration by Fengshou.
"""

import io
import mimetypes
import os

import librosa
import soundfile
from flask import Flask, request, jsonify

mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')

from pipeline.user_verification import process as process_verify
from pipeline.wake_word import process as process_wakeword
from pipeline.asr import ASRModule
from pipeline.intent_detection import IntentDetector
from pipeline.fulfillment import FulfillmentModule, PetState
from pipeline import nlg as nlg_module

app = Flask(__name__)

ALLOWED_EXTENSIONS = {"wav", "webm"}

# ---------------------------------------------------------------------------
# Initialize modules ONCE at startup (not per-request)
# ---------------------------------------------------------------------------
asr = ASRModule()
intent_detector = IntentDetector()
pet_state = PetState()
fulfillment = FulfillmentModule(pet_state)

system_state = {
    "unlocked": False,
    "awake": False,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_valid_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def make_response(module, success, data=None):
    return {"module": module, "success": success, "data": data or {}}


def read_audio(file):
    return soundfile.SoundFile(io.BytesIO(file.read()))


def read_audio_np(file):
    audio, sr = librosa.load(io.BytesIO(file.read()), sr=16000, mono=True)
    return audio


# ---------------------------------------------------------------------------
# POST /api/verify
# ---------------------------------------------------------------------------

@app.route("/api/verify", methods=["POST"])
def verify_voice():
    if "text" in request.form:
        text = request.form.get("text", "")
        if text.lower() == "yes":
            system_state["unlocked"] = True
            return jsonify(make_response("verify", True, {"bypass": True}))
        return jsonify(make_response("verify", False))

    if "file" in request.files:
        file = request.files["file"]
        if file and is_valid_file(file.filename):
            audio = read_audio(file)
            result = process_verify(audio)
            system_state["unlocked"] = result.get("verified", False)
            return jsonify(make_response("verify", result.get("verified", False), result))

    return jsonify(make_response("verify", False))


# ---------------------------------------------------------------------------
# POST /api/wake
# ---------------------------------------------------------------------------

@app.route("/api/wake", methods=["POST"])
def wake_detection():
    if "text" in request.form:
        text = request.form.get("text", "")
        if text.lower() == "hey atlas":
            system_state["awake"] = True
            return jsonify(make_response("wake", True, {"bypass": True}))
        return jsonify(make_response("wake", False))

    if "file" in request.files:
        file = request.files["file"]
        if file and is_valid_file(file.filename):
            audio = read_audio(file)
            result = process_wakeword(audio)
            detected = result.get("detected", False)
            system_state["awake"] = detected
            return jsonify(make_response("wake", detected, result))

    return jsonify(make_response("wake", False))


# ---------------------------------------------------------------------------
# POST /api/pipeline  (ASR → Intent → Fulfillment → NLG)
# ---------------------------------------------------------------------------

@app.route("/api/pipeline", methods=["POST"])
def pipeline():
    nlg_method = request.form.get("nlg_method", "template")

    # --- Get text: either from audio or bypass ---
    if "text" in request.form:
        transcribed_text = request.form.get("text", "")
    elif "file" in request.files:
        file = request.files["file"]
        if not file or not is_valid_file(file.filename):
            return jsonify(make_response("pipeline", False, {"error": "Invalid audio file"}))
        audio = read_audio_np(file)
        transcribed_text = asr.process(audio)
        if not transcribed_text:
            return jsonify(make_response("pipeline", False, {"error": "ASR failed"}))
    else:
        return jsonify(make_response("pipeline", False, {"error": "No input provided"}))

    # --- Intent Detection ---
    intent_data = intent_detector.process(transcribed_text)

    # --- Fulfillment ---
    try:
        fulfillment_result = fulfillment.process(intent_data)
    except Exception as e:
        fulfillment_result = {"type": "error", "error": str(e)}

    # --- NLG ---
    answer = nlg_module.process(intent_data, fulfillment_result, method=nlg_method)

    success = fulfillment_result.get("type") != "error"

    return jsonify(make_response("pipeline", success, {
        "transcript": transcribed_text,
        "intent": intent_data.get("intent"),
        "confidence": intent_data.get("confidence"),
        "slots": intent_data.get("slots", {}),
        "fulfillment": fulfillment_result,
        "answer": answer,
    }))


# ---------------------------------------------------------------------------
# GET /api/state
# ---------------------------------------------------------------------------

@app.route("/api/state")
def get_state():
    return jsonify({
        "system_state": system_state,
        "pet": pet_state.to_dict(),
    })


# ---------------------------------------------------------------------------
# Serve frontend
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return app.send_static_file("index.html") if os.path.exists("static/index.html") \
        else "Atlas VA is running. Frontend not yet built."


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting Atlas VA server...")
    app.run(debug=True, port=5000)
