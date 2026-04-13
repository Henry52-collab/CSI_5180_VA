"""
Train Speaker Verification SVM — V2: Delta-MFCC features (channel-invariant).

Rationale:
    Mean MFCC captures average spectral shape, which is heavily contaminated by
    microphone frequency response and codec artifacts. Dropping mean features
    and using only std + delta-std + delta2-std captures the DYNAMICS of speech
    (articulation rate, transitions), which are much more channel-invariant.

Feature vector: [std MFCC (20), std Δ-MFCC (20), std ΔΔ-MFCC (20)] = 60 dims
(compared to V1's 40 dims: [mean + std]).

Outputs: models/user_verify_svm_v2.pkl
"""

import os
import sys
import pickle
import numpy as np
import librosa
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# ---------------------------------------------------------------------------
TARGET_SR = 16000
DURATION = 3
NUM_SAMPLES = TARGET_SR * DURATION
N_MFCC = 20
WINDOW_SEC = 0.025
HOP_SEC = 0.010

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "voices")
AUTHORIZED_DIR = os.path.join(DATA_DIR, "authorized")
UNAUTHORIZED_DIR = os.path.join(DATA_DIR, "unauthorized")
MODEL_PATH = os.path.join(BASE_DIR, "models", "user_verify_svm_v2.pkl")


def extract_features_v2(audio, sr=TARGET_SR):
    """Extract std + delta-std + delta2-std → 60-dim vector."""
    if len(audio) < NUM_SAMPLES:
        audio = np.pad(audio, (0, NUM_SAMPLES - len(audio)))
    else:
        audio = audio[:NUM_SAMPLES]

    n_fft = int(WINDOW_SEC * sr)
    hop_length = int(HOP_SEC * sr)

    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=N_MFCC,
                                n_fft=n_fft, hop_length=hop_length)
    delta = librosa.feature.delta(mfcc, order=1)
    delta2 = librosa.feature.delta(mfcc, order=2)

    return np.concatenate([
        np.std(mfcc, axis=1),
        np.std(delta, axis=1),
        np.std(delta2, axis=1),
    ])


# ---- Augmentation (same as V1) ----
def augment_noise(y, noise_factor=0.005):
    return y + np.random.randn(len(y)) * noise_factor


def augment_pitch(y, sr=TARGET_SR, n_steps=None):
    if n_steps is None:
        n_steps = np.random.uniform(-2, 2)
    return librosa.effects.pitch_shift(y=y, sr=sr, n_steps=n_steps)


def augment_time_stretch(y, rate=None):
    if rate is None:
        rate = np.random.uniform(0.8, 1.2)
    return librosa.effects.time_stretch(y=y, rate=rate)


def augment_time_shift(y, shift_max=0.2):
    shift = int(np.random.uniform(-shift_max, shift_max) * len(y))
    return np.roll(y, shift)


def augment_volume(y, volume_range=(0.7, 1.3)):
    return y * np.random.uniform(*volume_range)


# ---- Dataset ----
def load_audio_files(directory, label):
    pairs = []
    if not os.path.isdir(directory):
        print(f"WARNING: directory not found: {directory}")
        return pairs
    for fname in os.listdir(directory):
        if fname.lower().endswith((".wav", ".flac", ".mp3")):
            pairs.append((os.path.join(directory, fname), label))
    return pairs


def build_dataset(files, do_augment=True):
    X, y = [], []
    augment_fns = [augment_noise, augment_pitch, augment_time_stretch,
                   augment_time_shift, augment_volume]

    for fpath, label in files:
        try:
            audio, sr = librosa.load(fpath, sr=TARGET_SR, mono=True)
            if len(audio) < NUM_SAMPLES:
                audio = np.pad(audio, (0, NUM_SAMPLES - len(audio)))
            else:
                audio = audio[:NUM_SAMPLES]

            X.append(extract_features_v2(audio, sr))
            y.append(label)

            if do_augment:
                for aug_fn in augment_fns:
                    try:
                        if aug_fn in (augment_pitch, augment_time_stretch):
                            aug_audio = aug_fn(audio, sr)
                        else:
                            aug_audio = aug_fn(audio)
                        if len(aug_audio) < NUM_SAMPLES:
                            aug_audio = np.pad(aug_audio, (0, NUM_SAMPLES - len(aug_audio)))
                        else:
                            aug_audio = aug_audio[:NUM_SAMPLES]
                        X.append(extract_features_v2(aug_audio, sr))
                        y.append(label)
                    except Exception as e:
                        print(f"  aug {aug_fn.__name__} failed for {fpath}: {e}")
        except Exception as e:
            print(f"  skipping {fpath}: {e}")

    return np.array(X), np.array(y)


def train():
    files = []
    files += load_audio_files(AUTHORIZED_DIR, label=1)
    files += load_audio_files(UNAUTHORIZED_DIR, label=0)

    if not files:
        print("ERROR: no audio files")
        sys.exit(1)

    n_auth = sum(1 for _, l in files if l == 1)
    n_unauth = sum(1 for _, l in files if l == 0)
    print(f"V2 (Delta-MFCC, channel-invariant)")
    print(f"Found {n_auth} authorized + {n_unauth} unauthorized files")

    print("Extracting features + augmenting...")
    X, y = build_dataset(files, do_augment=True)
    print(f"Total samples: {len(X)}  (feature dim: {X.shape[1]})")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    print("Training SVM...")
    svm = SVC(kernel="rbf", C=1.0, gamma="scale", probability=True)
    svm.fit(X_train, y_train)

    y_pred = svm.predict(X_test)
    print(f"\nTest Accuracy: {accuracy_score(y_test, y_pred):.3f}")
    print(classification_report(y_test, y_pred,
                                target_names=["unauthorized", "authorized"]))

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"svm": svm, "scaler": scaler, "version": "v2"}, f)
    print(f"Saved → {MODEL_PATH}")


if __name__ == "__main__":
    train()
