"""
Train a Wake Word Detection CNN model (PyTorch).

Adapted from Activity 1 WakeWord notebook (Keras → PyTorch).

Expects wake word data organized as:
    data/wake_word/positive/  — "Hey Atlas" WAV recordings
    data/wake_word/negative/  — non-wake-word WAV recordings (near-miss + other)

If no data/wake_word/ directory exists, falls back to reusing
data/voices/ (all recordings are "Hey Atlas") as positive class
and generates synthetic negatives for training.

Outputs:
    models/wake_word_cnn.pth — trained CNN model weights
"""

import os
import sys
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
import librosa
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# ---------------------------------------------------------------------------
# Constants (from Activity 1 WakeWord notebook)
# ---------------------------------------------------------------------------
TARGET_SR = 16000
DURATION = 2
NUM_SAMPLES = TARGET_SR * DURATION
N_MFCC = 13
WINDOW_SEC = 0.025
HOP_SEC = 0.025

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAKE_WORD_DIR = os.path.join(BASE_DIR, "data", "Wakeword")
POSITIVE_DIR = os.path.join(WAKE_WORD_DIR, "positive")
NEGATIVE_DIR = os.path.join(WAKE_WORD_DIR, "negative")
VOICES_DIR = os.path.join(BASE_DIR, "data", "voices")
MODEL_PATH = os.path.join(BASE_DIR, "models", "wake_word_cnn.pth")

EPOCHS = 50
BATCH_SIZE = 8
LEARNING_RATE = 0.001


# ---------------------------------------------------------------------------
# MFCC extraction (from Activity 1)
# ---------------------------------------------------------------------------
def extract_mfcc(file_path):
    """Extract MFCC spectrogram from a WAV file. Returns shape (N_MFCC, time_steps)."""
    y, sr = librosa.load(file_path, sr=TARGET_SR, mono=True)

    # Pad or trim to fixed length
    if len(y) < NUM_SAMPLES:
        y = np.pad(y, (0, NUM_SAMPLES - len(y)))
    else:
        y = y[:NUM_SAMPLES]

    n_fft = int(WINDOW_SEC * sr)
    hop_length = int(HOP_SEC * sr)

    mfcc = librosa.feature.mfcc(
        y=y, sr=sr,
        n_mfcc=N_MFCC,
        n_fft=n_fft,
        hop_length=hop_length,
    )
    return mfcc


def extract_mfcc_from_array(audio, sr=TARGET_SR):
    """Extract MFCC from a numpy array."""
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
# Data augmentation (from Activity 1)
# ---------------------------------------------------------------------------
def augment_time_shift(y, shift_max=0.2):
    shift = int(np.random.uniform(-shift_max, shift_max) * len(y))
    return np.roll(y, shift)


def augment_volume(y, volume_range=(0.7, 1.3)):
    scale = np.random.uniform(*volume_range)
    return y * scale


def augment_noise(y, noise_factor=0.005):
    noise = np.random.randn(len(y)) * noise_factor
    return y + noise


def generate_synthetic_negatives(n_samples):
    """Generate synthetic non-wake-word audio (noise/tones) for negative class."""
    negatives = []
    for i in range(n_samples):
        choice = np.random.choice(["noise", "tone", "silence"])
        if choice == "noise":
            audio = np.random.randn(NUM_SAMPLES).astype(np.float32) * 0.3
        elif choice == "tone":
            freq = np.random.uniform(100, 1000)
            t = np.linspace(0, DURATION, NUM_SAMPLES, dtype=np.float32)
            audio = 0.5 * np.sin(2 * np.pi * freq * t) + 0.1 * np.random.randn(NUM_SAMPLES).astype(np.float32)
        else:
            audio = np.random.randn(NUM_SAMPLES).astype(np.float32) * 0.01
        negatives.append(extract_mfcc_from_array(audio))
    return negatives


# ---------------------------------------------------------------------------
# CNN Model (adapted from Activity 1 Keras model → PyTorch)
# ---------------------------------------------------------------------------
class WakeWordCNN(nn.Module):
    """CNN for wake word detection. Input: (batch, 1, N_MFCC, time_steps)."""

    def __init__(self, n_mfcc=N_MFCC, n_time_steps=81):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 16, kernel_size=3, padding=1)
        self.pool1 = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1)
        self.pool2 = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(0.3)

        # Calculate flattened size after conv+pool layers
        h = n_mfcc // 2 // 2   # after 2x MaxPool on height
        w = n_time_steps // 2 // 2  # after 2x MaxPool on width
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
# Dataset building
# ---------------------------------------------------------------------------
def load_wav_files(directory):
    """Load all WAV files from a directory, return list of file paths."""
    paths = []
    if not os.path.isdir(directory):
        return paths
    for fname in os.listdir(directory):
        if fname.lower().endswith((".wav", ".flac", ".mp3")):
            paths.append(os.path.join(directory, fname))
    return paths


def build_dataset():
    """Build X (MFCC spectrograms) and y (labels) arrays."""
    X, y = [], []

    # --- Load positive samples (wake word) ---
    positive_files = []
    if os.path.isdir(POSITIVE_DIR):
        positive_files = load_wav_files(POSITIVE_DIR)
        print(f"Found {len(positive_files)} positive files in {POSITIVE_DIR}")
    else:
        # Fallback: use all voice recordings (they're all "Hey Atlas")
        for subdir in ["authorized", "unauthorized"]:
            d = os.path.join(VOICES_DIR, subdir)
            positive_files += load_wav_files(d)
        print(f"No wake_word/positive dir found. Using {len(positive_files)} voice recordings as positive samples.")

    for fpath in positive_files:
        try:
            mfcc = extract_mfcc(fpath)
            X.append(mfcc)
            y.append(1)

            # Augment positive samples
            audio, sr = librosa.load(fpath, sr=TARGET_SR, mono=True)
            if len(audio) < NUM_SAMPLES:
                audio = np.pad(audio, (0, NUM_SAMPLES - len(audio)))
            else:
                audio = audio[:NUM_SAMPLES]

            for aug_fn in [augment_time_shift, augment_volume, augment_noise]:
                aug_audio = aug_fn(audio)
                X.append(extract_mfcc_from_array(aug_audio))
                y.append(1)
        except Exception as e:
            print(f"  skipping {fpath}: {e}")

    n_positive = len(y)

    # --- Load negative samples (not wake word) ---
    negative_files = load_wav_files(NEGATIVE_DIR)
    if negative_files:
        print(f"Found {len(negative_files)} negative files in {NEGATIVE_DIR}")
        for fpath in negative_files:
            try:
                mfcc = extract_mfcc(fpath)
                X.append(mfcc)
                y.append(0)

                audio, sr = librosa.load(fpath, sr=TARGET_SR, mono=True)
                if len(audio) < NUM_SAMPLES:
                    audio = np.pad(audio, (0, NUM_SAMPLES - len(audio)))
                else:
                    audio = audio[:NUM_SAMPLES]

                for aug_fn in [augment_time_shift, augment_volume, augment_noise]:
                    aug_audio = aug_fn(audio)
                    X.append(extract_mfcc_from_array(aug_audio))
                    y.append(0)
            except Exception as e:
                print(f"  skipping {fpath}: {e}")
    else:
        # Generate synthetic negatives to match positive count
        print(f"No negative files found. Generating {n_positive} synthetic negatives.")
        synthetic = generate_synthetic_negatives(n_positive)
        for mfcc in synthetic:
            X.append(mfcc)
            y.append(0)

    return np.array(X), np.array(y)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def train():
    print("Building dataset...")
    X, y = build_dataset()

    n_pos = np.sum(y == 1)
    n_neg = np.sum(y == 0)
    print(f"Total: {len(X)} samples ({n_pos} positive, {n_neg} negative)")
    print(f"MFCC shape per sample: {X[0].shape}")

    # Add channel dimension: (N, MFCC, time) → (N, 1, MFCC, time)
    X = X[:, np.newaxis, :, :]
    n_time_steps = X.shape[3]

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # Convert to tensors
    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.FloatTensor(y_train).unsqueeze(1)
    X_test_t = torch.FloatTensor(X_test)
    y_test_t = torch.FloatTensor(y_test).unsqueeze(1)

    train_ds = TensorDataset(X_train_t, y_train_t)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)

    # Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = WakeWordCNN(n_mfcc=N_MFCC, n_time_steps=n_time_steps).to(device)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    print(f"\nTraining on {device} for {EPOCHS} epochs...")
    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)

            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()

        if (epoch + 1) % 10 == 0:
            avg_loss = running_loss / len(train_loader)
            print(f"  Epoch {epoch+1}/{EPOCHS} — loss: {avg_loss:.4f}")

    # Evaluate
    model.eval()
    with torch.no_grad():
        X_test_t = X_test_t.to(device)
        y_pred_prob = model(X_test_t).cpu().numpy()
        y_pred = (y_pred_prob > 0.5).astype(int).flatten()

    print(f"\nAccuracy: {accuracy_score(y_test, y_pred):.2f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["not_wake", "wake"]))

    # Save model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    torch.save({
        "model_state_dict": model.state_dict(),
        "n_mfcc": N_MFCC,
        "n_time_steps": n_time_steps,
    }, MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    train()
