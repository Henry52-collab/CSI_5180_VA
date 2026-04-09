"""
Wake Word Detection Module (Module 2)

Loads a trained CNN model and detects whether audio contains
the wake word "Hey Atlas".

Pipeline interface:
    process(audio)  → {"detected": bool, "confidence": float}
    bypass(text)    → {"detected": bool}
"""

import os
import numpy as np
import torch
import torch.nn as nn
import librosa
import soundfile

# ---------------------------------------------------------------------------
# Constants (must match training)
# ---------------------------------------------------------------------------
TARGET_SR = 16000
DURATION = 2
NUM_SAMPLES = TARGET_SR * DURATION
N_MFCC = 13
WINDOW_SEC = 0.025
HOP_SEC = 0.025

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "models", "wake_word_cnn.pth")

WAKE_WORD = "hey atlas"
THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# CNN Model (must match training architecture)
# ---------------------------------------------------------------------------
class WakeWordCNN(nn.Module):
    def __init__(self, n_mfcc=N_MFCC, n_time_steps=81):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1)
        self.pool1 = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.pool2 = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(0.3)

        h = n_mfcc // 2 // 2
        w = n_time_steps // 2 // 2
        self.flat_size = 32 * h * w

        self.fc1 = nn.Linear(self.flat_size, 32)
        self.fc2 = nn.Linear(32, 1)

    def forward(self, x):
        x = self.pool1(torch.relu(self.conv1(x)))
        x = self.pool2(torch.relu(self.conv2(x)))
        x = self.dropout(x)
        x = x.reshape(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = torch.sigmoid(self.fc2(x))
        return x


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------
def _extract_mfcc(audio, sr=TARGET_SR):
    """Extract MFCC spectrogram from numpy audio array."""
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
    return mfcc


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------
_model_cache = {}


def _load_model():
    if "model" not in _model_cache:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. "
                "Run training/train_wake_word.py first."
            )
        checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        n_mfcc = checkpoint.get("n_mfcc", N_MFCC)
        n_time_steps = checkpoint.get("n_time_steps", 81)

        model = WakeWordCNN(n_mfcc=n_mfcc, n_time_steps=n_time_steps)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        _model_cache["model"] = model
    return _model_cache["model"]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def process(audio, sr=TARGET_SR):
    """Detect wake word from audio.

    Args:
        audio: numpy array of audio samples, OR a file path (str).
        sr: sample rate (used only when audio is a numpy array).

    Returns:
        dict with "detected" (bool) and "confidence" (float 0-1).
    """
    if isinstance(audio, soundfile.SoundFile):
        audio, sr = librosa.load(audio, sr=TARGET_SR, mono=True)

    model = _load_model()
    mfcc = _extract_mfcc(audio, sr)

    # Shape: (1, 1, N_MFCC, time_steps)
    tensor = torch.FloatTensor(mfcc).unsqueeze(0).unsqueeze(0)

    with torch.no_grad():
        confidence = model(tensor).item()

    return {"detected": confidence >= THRESHOLD, "confidence": round(confidence, 3)}


def bypass(text):
    """Bypass voice wake word by typing it.

    Args:
        text: string typed by the user.

    Returns:
        dict with "detected" (bool).
    """
    return {"detected": text.strip().lower() == WAKE_WORD}
