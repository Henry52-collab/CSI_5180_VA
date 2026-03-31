"""
User Verification Module (Module 1)

Loads a trained SVM model and verifies whether an audio sample
belongs to an authorized user.

Pipeline interface:
    process(audio_path) → {"verified": bool, "confidence": float}
    bypass(code)        → {"verified": bool}
"""

import os
import pickle
import numpy as np
import librosa

# ---------------------------------------------------------------------------
# Constants (must match training)
# ---------------------------------------------------------------------------
TARGET_SR = 16000
DURATION = 3
NUM_SAMPLES = TARGET_SR * DURATION
N_MFCC = 20
WINDOW_SEC = 0.025
HOP_SEC = 0.010

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "user_verify_svm.pkl")

# Bypass passcode — change this to your team's chosen code
PASSCODE = "atlas123"

# Confidence threshold for verification
THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Feature extraction (same as training)
# ---------------------------------------------------------------------------
def _extract_features(audio, sr=TARGET_SR):
    """Extract mean+std MFCC feature vector from a numpy audio array."""
    if len(audio) < NUM_SAMPLES:
        audio = np.pad(audio, (0, NUM_SAMPLES - len(audio)))
    else:
        audio = audio[:NUM_SAMPLES]

    n_fft = int(WINDOW_SEC * sr)
    hop_length = int(HOP_SEC * sr)

    mfcc = librosa.feature.mfcc(
        y=audio, sr=sr,
        n_mfcc=N_MFCC,
        n_fft=n_fft,
        hop_length=hop_length,
    )
    mean = np.mean(mfcc, axis=1)
    std = np.std(mfcc, axis=1)
    return np.concatenate([mean, std])


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------
_model_cache = {}


def _load_model():
    if "svm" not in _model_cache:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. "
                "Run training/train_verification.py first."
            )
        with open(MODEL_PATH, "rb") as f:
            data = pickle.load(f)
        _model_cache["svm"] = data["svm"]
        _model_cache["scaler"] = data["scaler"]
    return _model_cache["svm"], _model_cache["scaler"]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def process(audio, sr=TARGET_SR):
    """Verify a speaker from audio.

    Args:
        audio: numpy array of audio samples, OR a file path (str).
        sr: sample rate (used only when audio is a numpy array).

    Returns:
        dict with "verified" (bool) and "confidence" (float 0-1).
    """
    # Accept file path or numpy array
    if isinstance(audio, str):
        audio, sr = librosa.load(audio, sr=TARGET_SR, mono=True)

    svm, scaler = _load_model()
    features = _extract_features(audio, sr)
    features_scaled = scaler.transform(features.reshape(1, -1))

    confidence = svm.predict_proba(features_scaled)[0, 1]  # P(authorized)
    verified = confidence >= THRESHOLD

    return {"verified": bool(verified), "confidence": round(float(confidence), 3)}


def bypass(code):
    """Bypass voice verification with a passcode.

    Args:
        code: string passcode entered by the user.

    Returns:
        dict with "verified" (bool).
    """
    return {"verified": code == PASSCODE}
