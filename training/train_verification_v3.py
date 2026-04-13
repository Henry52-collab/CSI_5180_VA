"""
Train Speaker Verification SVM — V3: Channel-augmented training.

Rationale:
    V1 augmentations (pitch/stretch/volume/noise) don't simulate the CHANNEL
    distortions that cause browser recordings to fail. Here we add:
      - Downsample→upsample (simulates lossy codec bandwidth reduction)
      - Band-pass filter 300–4000 Hz (simulates narrow-band mic frequency response)
      - High-pass filter 100 Hz (simulates removal of low-frequency room rumble)
      - Random EQ tilt (simulates different mic frequency response)

Keeps V1's feature extractor (mean + std MFCC).

Outputs: models/user_verify_svm_v3.pkl
"""

import os
import sys
import pickle
import numpy as np
import librosa
import scipy.signal
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
MODEL_PATH = os.path.join(BASE_DIR, "models", "user_verify_svm_v3.pkl")


def extract_features_v1(audio, sr=TARGET_SR):
    """V1 feature: mean + std MFCC = 40 dims."""
    if len(audio) < NUM_SAMPLES:
        audio = np.pad(audio, (0, NUM_SAMPLES - len(audio)))
    else:
        audio = audio[:NUM_SAMPLES]

    n_fft = int(WINDOW_SEC * sr)
    hop_length = int(HOP_SEC * sr)
    mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=N_MFCC,
                                n_fft=n_fft, hop_length=hop_length)
    return np.concatenate([np.mean(mfcc, axis=1), np.std(mfcc, axis=1)])


# ---- Standard augmentations ----
def aug_noise(y, _sr):       return y + np.random.randn(len(y)) * 0.005
def aug_pitch(y, sr):        return librosa.effects.pitch_shift(y=y, sr=sr, n_steps=np.random.uniform(-2, 2))
def aug_time_stretch(y, _sr):return librosa.effects.time_stretch(y=y, rate=np.random.uniform(0.8, 1.2))
def aug_time_shift(y, _sr):  return np.roll(y, int(np.random.uniform(-0.2, 0.2) * len(y)))
def aug_volume(y, _sr):      return y * np.random.uniform(0.7, 1.3)


# ---- NEW: Channel augmentations ----
def aug_downsample_upsample(y, sr):
    """Downsample to 8kHz then back to 16kHz — simulates codec bandwidth loss."""
    low = librosa.resample(y, orig_sr=sr, target_sr=8000)
    return librosa.resample(low, orig_sr=8000, target_sr=sr)


def aug_bandpass(y, sr):
    """Band-pass filter 300-4000 Hz — simulates narrow-band mic."""
    low = 300 / (sr / 2)
    high = 4000 / (sr / 2)
    b, a = scipy.signal.butter(4, [low, high], btype="band")
    return scipy.signal.filtfilt(b, a, y).astype(np.float32)


def aug_highpass(y, sr):
    """High-pass filter 100 Hz — removes low-frequency rumble."""
    cutoff = 100 / (sr / 2)
    b, a = scipy.signal.butter(4, cutoff, btype="high")
    return scipy.signal.filtfilt(b, a, y).astype(np.float32)


def aug_eq_tilt(y, sr):
    """Random EQ tilt — boost/cut high frequencies to simulate different mic."""
    cutoff = 2000 / (sr / 2)
    b, a = scipy.signal.butter(2, cutoff, btype="high")
    high_part = scipy.signal.filtfilt(b, a, y).astype(np.float32)
    # Randomly boost or cut high frequencies by ±6 dB
    gain = np.random.uniform(0.5, 1.5)
    return (y + (gain - 1) * high_part).astype(np.float32)


def load_audio_files(directory, label):
    pairs = []
    if not os.path.isdir(directory):
        return pairs
    for fname in os.listdir(directory):
        if fname.lower().endswith((".wav", ".flac", ".mp3")):
            pairs.append((os.path.join(directory, fname), label))
    return pairs


def pad_or_trim(audio):
    if len(audio) < NUM_SAMPLES:
        return np.pad(audio, (0, NUM_SAMPLES - len(audio)))
    return audio[:NUM_SAMPLES]


def build_dataset(files, do_augment=True):
    X, y = [], []
    standard_augs = [aug_noise, aug_pitch, aug_time_stretch, aug_time_shift, aug_volume]
    channel_augs  = [aug_downsample_upsample, aug_bandpass, aug_highpass, aug_eq_tilt]

    for fpath, label in files:
        try:
            audio, sr = librosa.load(fpath, sr=TARGET_SR, mono=True)
            audio = pad_or_trim(audio)

            X.append(extract_features_v1(audio, sr))
            y.append(label)

            if do_augment:
                for aug_fn in standard_augs + channel_augs:
                    try:
                        aug = aug_fn(audio, sr)
                        aug = pad_or_trim(aug)
                        X.append(extract_features_v1(aug, sr))
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
        print("ERROR: no audio")
        sys.exit(1)

    n_auth = sum(1 for _, l in files if l == 1)
    n_unauth = sum(1 for _, l in files if l == 0)
    print(f"V3 (Channel augmentation)")
    print(f"Found {n_auth} authorized + {n_unauth} unauthorized files")

    print("Extracting features + augmenting (9 augs per sample)...")
    X, y = build_dataset(files, do_augment=True)
    print(f"Total samples: {len(X)}  (feature dim: {X.shape[1]})")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    svm = SVC(kernel="rbf", C=1.0, gamma="scale", probability=True)
    svm.fit(X_train, y_train)
    y_pred = svm.predict(X_test)
    print(f"\nTest Accuracy: {accuracy_score(y_test, y_pred):.3f}")
    print(classification_report(y_test, y_pred,
                                target_names=["unauthorized", "authorized"]))

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump({"svm": svm, "scaler": scaler, "version": "v3"}, f)
    print(f"Saved → {MODEL_PATH}")


if __name__ == "__main__":
    train()
