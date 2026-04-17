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
TARGET_SR = 16000          # 16 kHz mono — standard for speech tasks
DURATION = 3               # clip length in seconds
NUM_SAMPLES = TARGET_SR * DURATION  # = 48000 samples per clip
N_MFCC = 20                # number of Mel-frequency cepstral coefficients
WINDOW_SEC = 0.025         # 25 ms FFT window (speech-standard)
HOP_SEC = 0.010            # 10 ms hop → high time resolution for speaker traits

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Select which trained model to use:
#   user_verify_svm.pkl     — v1: mean + std MFCC (original)
#   user_verify_svm_v2.pkl  — v2: std + Δ-std + ΔΔ-std (channel-invariant features)
#   user_verify_svm_v3.pkl  — v3: v1 features + channel augmentations
#   user_verify_svm_v4.pkl  — v4: v2 features + channel augmentations
MODEL_PATH = os.path.join(BASE_DIR, "models",
                          os.getenv("VERIFY_MODEL", "user_verify_svm_v2.pkl"))

# by pass code
PASSCODE = "Doro"

# Confidence threshold for verification
THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Feature extraction — dispatch by model version
# ---------------------------------------------------------------------------
def _pad_or_trim(audio):
    if len(audio) < NUM_SAMPLES:
        return np.pad(audio, (0, NUM_SAMPLES - len(audio)))
    return audio[:NUM_SAMPLES]


def _extract_features_v1(audio, sr):
    """V1: mean + std of 20 MFCCs → 40-dim feature vector.
    Simple but sensitive to recording channel (mic type, room)."""
    audio = _pad_or_trim(audio)
    n_fft = int(WINDOW_SEC * sr)     # FFT window = 400 samples at 16 kHz
    hop_length = int(HOP_SEC * sr)   # hop = 160 samples → 100 frames/sec
    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=N_MFCC,
                                n_fft=n_fft, hop_length=hop_length)
    # mean captures "average voice timbre", std captures "variability"
    return np.concatenate([np.mean(mfcc, axis=1), np.std(mfcc, axis=1)])


def _extract_features_v2(audio, sr):
    """V2/V4: std of MFCC + delta + delta-delta → 60-dim feature vector.
    Drops mean (channel-dependent), keeps only std (more robust).
    Delta/delta-delta capture how voice dynamics change over time."""
    audio = _pad_or_trim(audio)
    n_fft = int(WINDOW_SEC * sr)
    hop_length = int(HOP_SEC * sr)
    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=N_MFCC,
                                n_fft=n_fft, hop_length=hop_length)
    delta = librosa.feature.delta(mfcc, order=1)   # 1st derivative (velocity)
    delta2 = librosa.feature.delta(mfcc, order=2)  # 2nd derivative (acceleration)
    return np.concatenate([np.std(mfcc, axis=1),
                           np.std(delta, axis=1),
                           np.std(delta2, axis=1)])


def _extract_features_v5(audio, sr):
    """V5: mean + std + delta-std + delta2-std = 80 dims."""
    audio = _pad_or_trim(audio)
    n_fft = int(WINDOW_SEC * sr)
    hop_length = int(HOP_SEC * sr)
    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=N_MFCC,
                                n_fft=n_fft, hop_length=hop_length)
    delta = librosa.feature.delta(mfcc, order=1)
    delta2 = librosa.feature.delta(mfcc, order=2)
    return np.concatenate([np.mean(mfcc, axis=1),
                           np.std(mfcc, axis=1),
                           np.std(delta, axis=1),
                           np.std(delta2, axis=1)])


_FEATURE_EXTRACTORS = {
    "v1": _extract_features_v1,
    "v2": _extract_features_v2,
    "v3": _extract_features_v1,  # v3 uses v1 features, just more augmentation
    "v4": _extract_features_v2,
    "v5": _extract_features_v5,
    "v6": _extract_features_v5,  # v6/v7 use v5 features, just more aggressive aug
    "v7": _extract_features_v5,
}


def _extract_features(audio, sr=TARGET_SR):
    """Dispatch to correct feature extractor based on loaded model version."""
    version = _model_cache.get("version", "v1")
    return _FEATURE_EXTRACTORS[version](audio, sr)


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
        _model_cache["version"] = data.get("version", "v1")
        print(f"[Verify] Loaded model: {os.path.basename(MODEL_PATH)} "
              f"(version={_model_cache['version']})")
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
    # StandardScaler normalizes features to zero-mean unit-variance (fit on training data)
    features_scaled = scaler.transform(features.reshape(1, -1))
    # predict_proba returns [P(unauthorized), P(authorized)] — we want column 1
    confidence = svm.predict_proba(features_scaled)[0, 1]
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
