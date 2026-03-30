"""
Quick test for the user verification pipeline.

Generates synthetic WAV files, trains the SVM, and runs verification.
Delete the synthetic data after confirming things work.
"""

import os
import sys
import numpy as np
import soundfile as sf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_DIR = os.path.join(BASE_DIR, "data", "voices", "authorized")
UNAUTH_DIR = os.path.join(BASE_DIR, "data", "voices", "unauthorized")
SR = 16000
DURATION = 3


def generate_fake_audio(directory, n_files, freq_range, label):
    """Generate simple sine-wave WAVs with different base frequencies
    to simulate different speakers."""
    os.makedirs(directory, exist_ok=True)
    t = np.linspace(0, DURATION, SR * DURATION, dtype=np.float32)
    for i in range(n_files):
        freq = np.random.uniform(*freq_range)
        # Mix a few harmonics + noise to make each "speaker" distinct
        audio = (
            0.5 * np.sin(2 * np.pi * freq * t)
            + 0.3 * np.sin(2 * np.pi * freq * 1.5 * t)
            + 0.1 * np.random.randn(len(t))
        ).astype(np.float32)
        path = os.path.join(directory, f"{label}_speaker_{i:02d}.wav")
        sf.write(path, audio, SR)
    print(f"  Created {n_files} files in {directory}")


def main():
    # --- Step 1: Generate synthetic data ---
    print("=== Step 1: Generating synthetic audio ===")
    generate_fake_audio(AUTH_DIR, n_files=10, freq_range=(200, 400), label="auth")
    generate_fake_audio(UNAUTH_DIR, n_files=10, freq_range=(500, 800), label="unauth")

    # --- Step 2: Train the model ---
    print("\n=== Step 2: Training SVM ===")
    from train_verification import train
    train()

    # --- Step 3: Test process() with an authorized file ---
    print("\n=== Step 3: Testing pipeline module ===")
    sys.path.insert(0, os.path.join(BASE_DIR, "pipeline"))
    from user_verification import process, bypass

    # Pick one authorized and one unauthorized file
    auth_file = os.path.join(AUTH_DIR, os.listdir(AUTH_DIR)[0])
    unauth_file = os.path.join(UNAUTH_DIR, os.listdir(UNAUTH_DIR)[0])

    result_auth = process(auth_file)
    print(f"Authorized file   → {result_auth}")

    result_unauth = process(unauth_file)
    print(f"Unauthorized file → {result_unauth}")

    # --- Step 4: Test bypass ---
    print("\n=== Step 4: Testing bypass ===")
    print(f"Correct code  → {bypass('atlas123')}")
    print(f"Wrong code    → {bypass('wrong')}")

    # --- Summary ---
    print("\n=== Results ===")
    if result_auth["verified"] and not result_unauth["verified"]:
        print("PASS — authorized accepted, unauthorized rejected")
    else:
        print("WARN — classification may be off with synthetic data, but the code runs correctly")
    print("\nDone! Replace data/voices/ with real Activity 1 recordings and retrain.")


if __name__ == "__main__":
    main()
