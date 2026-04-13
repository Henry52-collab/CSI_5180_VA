"""
Test a verification model against the training data.

Usage:
    python training/test_verify.py                              # default model (user_verify_svm.pkl)
    python training/test_verify.py user_verify_svm_v2.pkl       # test v2
    python training/test_verify.py user_verify_svm_v3.pkl
    python training/test_verify.py user_verify_svm_v4.pkl

To run against BROWSER-recorded samples (after using static/record.html):
    put them in data/voices/browser_test/ then:
    python training/test_verify.py user_verify_svm_v2.pkl data/voices/browser_test
"""

import os
import sys
import librosa

# Select which model to load BEFORE importing pipeline.user_verification
if len(sys.argv) > 1:
    os.environ["VERIFY_MODEL"] = sys.argv[1]

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.user_verification import process, _load_model, MODEL_PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUTH_DIR = os.path.join(BASE_DIR, "data", "voices", "authorized")
UNAUTH_DIR = os.path.join(BASE_DIR, "data", "voices", "unauthorized")


def test_file(path):
    audio, sr = librosa.load(path, sr=16000, mono=True)
    result = process(audio, sr=sr)
    return result["confidence"], result["verified"]


def test_dir(dir_path, label):
    files = sorted([f for f in os.listdir(dir_path) if f.endswith(".wav")])
    if not files:
        print(f"  (no wav files in {dir_path})")
        return

    print(f"\n=== {label} ({len(files)} files) ===")
    confidences = []
    passes = 0
    for fname in files:
        path = os.path.join(dir_path, fname)
        try:
            conf, verified = test_file(path)
            confidences.append(conf)
            if verified:
                passes += 1
            status = "PASS" if verified else "FAIL"
            print(f"  [{status}] {fname:50s} confidence={conf:.3f}")
        except Exception as e:
            print(f"  [ERR]  {fname:50s} {e}")

    if confidences:
        avg = sum(confidences) / len(confidences)
        print(f"  -- average confidence: {avg:.3f}  ({passes}/{len(files)} PASS)")


if __name__ == "__main__":
    print(f"Testing model: {MODEL_PATH}")
    try:
        _load_model()
    except Exception as e:
        print(f"Model load FAILED: {e}")
        sys.exit(1)

    # Optional: test on a custom directory passed as 2nd arg
    if len(sys.argv) > 2:
        custom_dir = sys.argv[2]
        test_dir(custom_dir, f"CUSTOM: {custom_dir}")
    else:
        test_dir(AUTH_DIR, "AUTHORIZED (should score HIGH)")
        test_dir(UNAUTH_DIR, "UNAUTHORIZED (should score LOW)")
