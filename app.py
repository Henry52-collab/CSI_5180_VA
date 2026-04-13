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
import re
from datetime import datetime

import librosa
import soundfile
from flask import Flask, request, jsonify

mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')

from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# Startup banner — warn about first-run model downloads
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("  ATLAS VA — Starting Up")
print("=" * 60)
print("  First run will download ~500MB of ML models (Whisper, BERT).")
print("  This can take 1-5 minutes depending on your connection.")
print("  Models are cached locally; subsequent starts take seconds.")
print("  Tip: run  `python bootstrap.py`  first to preload everything.")
print("=" * 60 + "\n")

if not os.getenv("OPENWEATHER_API_KEY"):
    print("*** WARNING: OPENWEATHER_API_KEY not set. Weather queries will fail.")
    print("    Copy .env.example to .env and fill in your keys.")
if not os.getenv("TMDB_API_KEY"):
    print("*** WARNING: TMDB_API_KEY not set. Movie queries will fail.")
    print("    Copy .env.example to .env and fill in your keys.")
if not os.getenv("OPENAI_API_KEY"):
    print("*** WARNING: OPENAI_API_KEY not set. OpenAI TTS backend unavailable;")
    print("    pyttsx3 still works, and frontend falls back to browser TTS.")
print()

import base64

from pipeline.user_verification import process as process_verify
from pipeline.wake_word import process as process_wakeword
from pipeline.asr import ASRModule
from pipeline.intent_detection import IntentDetector
from pipeline.fulfillment import FulfillmentModule, PetState
from pipeline import nlg as nlg_module
from pipeline import tts as tts_module

app = Flask(__name__)

ALLOWED_EXTENSIONS = {"wav", "webm"}

# ---------------------------------------------------------------------------
# Initialize modules ONCE at startup (not per-request)
# ---------------------------------------------------------------------------
print("[1/3] Loading ASR module (Whisper small.en, ~460MB if not cached)...")
asr = ASRModule()
print("[2/3] Loading Intent Detection module (DistilBERT)...")
intent_detector = IntentDetector()
print("[3/3] Loading Fulfillment module (Pet state, movie/weather APIs)...")
pet_state = PetState()
fulfillment = FulfillmentModule(pet_state)
print("\n[READY] All modules loaded. Open http://localhost:5000 in Chrome.\n")

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
            audio = read_audio_np(file)
            result = process_verify(audio)
            print(f"[Verify] Veriefied={result.get('verified')} confidence={result.get('confidence')}")
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
            audio = read_audio_np(file)
            result = process_wakeword(audio)
            detected = result.get("detected", False)
            system_state["awake"] = detected
            return jsonify(make_response("wake", detected, result))

    return jsonify(make_response("wake", False))


# ---------------------------------------------------------------------------
# POST /api/pipeline  (ASR → Intent → Fulfillment → NLG)
# ---------------------------------------------------------------------------

def _synthesize_tts(text, emotion, backend):
    """Run TTS with error handling. Returns (audio_b64, mime, error_str)."""
    try:
        audio_bytes = tts_module.process(text, emotion, backend=backend)
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        mime = tts_module.mime_for_backend(backend)
        return audio_b64, mime, None
    except Exception as e:
        print(f"[TTS] {backend} failed: {e}  (frontend will fallback to browser TTS)")
        return None, None, str(e)


@app.route("/api/pipeline", methods=["POST"])
def pipeline():
    import json as _json
    nlg_method   = request.form.get("nlg_method",   "template")
    tts_backend  = request.form.get("tts_backend",  "pyttsx3")

    # --- Intent bypass: user provided intent + slots directly ---
    if "intent" in request.form:
        intent_name = request.form.get("intent")
        slots_raw = request.form.get("slots", "{}")
        try:
            slots = _json.loads(slots_raw)
        except Exception:
            slots = {}
        intent_data = {"intent": intent_name, "confidence": 1.0, "slots": slots}
        transcribed_text = f"[bypass: {intent_name}]"

        try:
            fulfillment_result = fulfillment.process(intent_data)
        except Exception as e:
            print(f"[Pipeline] Fulfillment ERROR: {e}")
            fulfillment_result = {"type": "error", "error": str(e)}

        nlg_result = nlg_module.process(intent_data, fulfillment_result, method=nlg_method)
        answer  = nlg_result["text"]
        emotion = nlg_result["emotion"]
        print(f"[Pipeline] Bypass: intent={intent_name} slots={slots}")
        print(f"[Pipeline] NLG: '{answer[:80]}' emotion={emotion}")

        audio_b64, mime, tts_err = _synthesize_tts(answer, emotion, tts_backend)

        return jsonify(make_response("pipeline", True, {
            "transcript": transcribed_text,
            "intent": intent_name,
            "confidence": 1.0,
            "slots": slots,
            "fulfillment": fulfillment_result,
            "answer": answer,
            "emotion": emotion,
            "audio_b64": audio_b64,
            "audio_mime": mime,
            "tts_backend": tts_backend,
            "tts_error": tts_err,
        }))

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
    print(f"[Pipeline] ASR: '{transcribed_text}'")
    print(f"[Pipeline] Intent: {intent_data.get('intent')} ({intent_data.get('confidence', 0):.2f}) slots={intent_data.get('slots')}")

    # --- Fulfillment ---
    try:
        fulfillment_result = fulfillment.process(intent_data)
    except Exception as e:
        print(f"[Pipeline] Fulfillment ERROR: {e}")
        fulfillment_result = {"type": "error", "error": str(e)}

    # --- NLG ---
    nlg_result = nlg_module.process(intent_data, fulfillment_result, method=nlg_method)
    answer  = nlg_result["text"]
    emotion = nlg_result["emotion"]
    snippet = answer[:80] + ("..." if len(answer) > 80 else "")
    print(f"[Pipeline] NLG: '{snippet}' emotion={emotion}")

    # --- TTS ---
    audio_b64, mime, tts_err = _synthesize_tts(answer, emotion, tts_backend)

    return jsonify(make_response("pipeline", True, {
        "transcript": transcribed_text,
        "intent": intent_data.get("intent"),
        "confidence": intent_data.get("confidence"),
        "slots": intent_data.get("slots", {}),
        "fulfillment": fulfillment_result,
        "answer": answer,
        "emotion": emotion,
        "audio_b64": audio_b64,
        "audio_mime": mime,
        "tts_backend": tts_backend,
        "tts_error": tts_err,
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
# POST /api/collect_sample — save browser-recorded WAV as training data
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@app.route("/api/collect_sample", methods=["POST"])
def collect_sample():
    name = request.form.get("name", "").strip()
    target = request.form.get("target", "authorized")  # "authorized" or "unauthorized"

    name = re.sub(r"[^a-zA-Z0-9_-]", "", name)
    if not name:
        return jsonify({"success": False, "error": "invalid or missing name"})
    if target not in ("authorized", "unauthorized"):
        return jsonify({"success": False, "error": "invalid target"})

    if "file" not in request.files:
        return jsonify({"success": False, "error": "no file uploaded"})
    file = request.files["file"]
    if not file or not is_valid_file(file.filename):
        return jsonify({"success": False, "error": "invalid file"})

    save_dir = os.path.join(BASE_DIR, "data", "voices", target)
    os.makedirs(save_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    filename = f"{name}-browser-{ts}.wav"
    full_path = os.path.join(save_dir, filename)
    file.save(full_path)
    print(f"[CollectSample] saved {filename} to {target}/")
    return jsonify({"success": True, "filename": filename})


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
