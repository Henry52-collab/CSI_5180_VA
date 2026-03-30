"""
Train a Speaker Verification SVM model.

Expects voice data organized as:
    data/voices/authorized/   — WAV files from team members
    data/voices/unauthorized/ — WAV files from other students

Outputs:
    models/user_verify_svm.pkl — trained SVM model + scaler

Reuses MFCC extraction and augmentation patterns from Activity 1 (WakeWord notebook).
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
# Constants (adapted from Activity 1 WakeWord notebook)
# ---------------------------------------------------------------------------
TARGET_SR = 16000       # 16 kHz sample rate
DURATION = 3            # seconds per clip (longer than wake word for speaker features)
NUM_SAMPLES = TARGET_SR * DURATION
N_MFCC = 20            # 20 coefficients as specified in Task 7
WINDOW_SEC = 0.025      # 25 ms window
HOP_SEC = 0.010         # 10 ms hop (more overlap = more frames for speaker features)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "voices")
AUTHORIZED_DIR = os.path.join(DATA_DIR, "authorized")
UNAUTHORIZED_DIR = os.path.join(DATA_DIR, "unauthorized")
MODEL_PATH = os.path.join(BASE_DIR, "models", "user_verify_svm.pkl")


# ---------------------------------------------------------------------------
# MFCC extraction (adapted from Activity 1 extract_mfcc)
# ---------------------------------------------------------------------------
def extract_mfcc(file_path, sr=TARGET_SR, n_mfcc=N_MFCC):
    """Load an audio file and return the mean + std of MFCC frames as a
    fixed-length feature vector (2 * n_mfcc dimensions)."""
    y, sr = librosa.load(file_path, sr=sr, mono=True)

    # Pad or trim to fixed length
    if len(y) < NUM_SAMPLES:
        y = np.pad(y, (0, NUM_SAMPLES - len(y)))
    else:
        y = y[:NUM_SAMPLES]

    n_fft = int(WINDOW_SEC * sr)
    hop_length = int(HOP_SEC * sr)

    mfcc = librosa.feature.mfcc(
        y=y, sr=sr,
        n_mfcc=n_mfcc,
        n_fft=n_fft,
        hop_length=hop_length,
    )
    # Aggregate across time: mean + std → fixed-length vector
    mean = np.mean(mfcc, axis=1)
    std = np.std(mfcc, axis=1)
    return np.concatenate([mean, std])


# ---------------------------------------------------------------------------
# Data augmentation (adapted from Activity 1 WakeWord notebook)
# ---------------------------------------------------------------------------
def augment_noise(y, noise_factor=0.005):
    """Add random Gaussian noise."""
    noise = np.random.randn(len(y)) * noise_factor
    return y + noise


def augment_pitch(y, sr=TARGET_SR, n_steps=None):
    """Shift pitch by n_steps semitones (random ±2 if not specified)."""
    if n_steps is None:
        n_steps = np.random.uniform(-2, 2)
    return librosa.effects.pitch_shift(y=y, sr=sr, n_steps=n_steps)


def augment_time_stretch(y, rate=None):
    """Time-stretch the signal (random 0.8–1.2 if not specified)."""
    if rate is None:
        rate = np.random.uniform(0.8, 1.2)
    return librosa.effects.time_stretch(y=y, rate=rate)


def augment_time_shift(y, shift_max=0.2):
    """Shift audio left/right by up to shift_max fraction of length."""
    shift = int(np.random.uniform(-shift_max, shift_max) * len(y))
    return np.roll(y, shift)


def augment_volume(y, volume_range=(0.7, 1.3)):
    """Randomly scale volume."""
    scale = np.random.uniform(*volume_range)
    return y * scale


# ---------------------------------------------------------------------------
# Dataset building
# ---------------------------------------------------------------------------
def load_audio_files(directory, label):
    """Return list of (file_path, label) for all WAVs in a directory."""
    pairs = []
    if not os.path.isdir(directory):
        print(f"WARNING: directory not found: {directory}")
        return pairs
    for fname in os.listdir(directory):
        if fname.lower().endswith((".wav", ".flac", ".mp3")):
            pairs.append((os.path.join(directory, fname), label))
    return pairs


def build_dataset(files, do_augment=True):
    """Extract features from audio files. Optionally augment each sample."""
    X, y = [], []
    augment_fns = [augment_noise, augment_pitch, augment_time_stretch,
                   augment_time_shift, augment_volume]

    for fpath, label in files:
        try:
            # Original sample
            feat = extract_mfcc(fpath)
            X.append(feat)
            y.append(label)

            # Augmented copies
            if do_augment:
                audio, sr = librosa.load(fpath, sr=TARGET_SR, mono=True)
                if len(audio) < NUM_SAMPLES:
                    audio = np.pad(audio, (0, NUM_SAMPLES - len(audio)))
                else:
                    audio = audio[:NUM_SAMPLES]

                for aug_fn in augment_fns:
                    try:
                        if aug_fn in (augment_pitch, augment_time_stretch):
                            aug_audio = aug_fn(audio, sr)
                        else:
                            aug_audio = aug_fn(audio)
                        # Pad/trim augmented audio back to fixed length
                        if len(aug_audio) < NUM_SAMPLES:
                            aug_audio = np.pad(aug_audio, (0, NUM_SAMPLES - len(aug_audio)))
                        else:
                            aug_audio = aug_audio[:NUM_SAMPLES]

                        n_fft = int(WINDOW_SEC * sr)
                        hop_length = int(HOP_SEC * sr)
                        mfcc = librosa.feature.mfcc(
                            y=aug_audio, sr=sr,
                            n_mfcc=N_MFCC,
                            n_fft=n_fft,
                            hop_length=hop_length,
                        )
                        mean = np.mean(mfcc, axis=1)
                        std = np.std(mfcc, axis=1)
                        feat_aug = np.concatenate([mean, std])
                        X.append(feat_aug)
                        y.append(label)
                    except Exception as e:
                        print(f"  augmentation {aug_fn.__name__} failed for {fpath}: {e}")
        except Exception as e:
            print(f"  skipping {fpath}: {e}")

    return np.array(X), np.array(y)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def train():
    # 1 = authorized, 0 = unauthorized
    files = []
    files += load_audio_files(AUTHORIZED_DIR, label=1)
    files += load_audio_files(UNAUTHORIZED_DIR, label=0)

    if len(files) == 0:
        print("ERROR: No audio files found.")
        print(f"  Expected authorized voices in:   {AUTHORIZED_DIR}")
        print(f"  Expected unauthorized voices in:  {UNAUTHORIZED_DIR}")
        sys.exit(1)

    n_auth = sum(1 for _, l in files if l == 1)
    n_unauth = sum(1 for _, l in files if l == 0)
    print(f"Found {n_auth} authorized + {n_unauth} unauthorized audio files")

    print("Extracting features + augmenting...")
    X, y = build_dataset(files, do_augment=True)
    print(f"Total samples after augmentation: {len(X)}  (features shape: {X.shape})")

    # Train / test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Standardize features
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    # Train SVM
    print("Training SVM...")
    svm = SVC(kernel="rbf", C=1.0, gamma="scale", probability=True)
    svm.fit(X_train, y_train)

    # Evaluate
    y_pred = svm.predict(X_test)
    print(f"\nAccuracy: {accuracy_score(y_test, y_pred):.2f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["unauthorized", "authorized"]))

    # Save model + scaler
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"svm": svm, "scaler": scaler}, f)
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    train()
