"""
Train Speaker Verification SVM — V7: V6 + real Opus codec round-trip via ffmpeg.

Reuses all V6 augmentations, plus a NEW one:
    aug_opus_ffmpeg: actual Opus encode → decode through ffmpeg subprocess,
                     faithfully reproduces browser WebM/Opus codec artifacts.

Requires ffmpeg on PATH (training-time only, not needed at deployment).
If ffmpeg is missing, the Opus aug is skipped and a warning is printed —
the rest of V6's augmentations still run.

Outputs: models/user_verify_svm_v7.pkl
"""

import os
import sys
import shutil
import subprocess
import tempfile
import numpy as np
import soundfile as sf
import librosa

# Reuse V6 infrastructure
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_verification_v6 import train, TARGET_SR


def _ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def aug_opus_ffmpeg(y, sr):
    """Round-trip through actual libopus via ffmpeg.

    Pipeline: WAV in → Opus encode (48kbps) → Opus decode → WAV out.
    Simulates the real lossy codec the browser uses.
    """
    with tempfile.TemporaryDirectory() as td:
        in_wav = os.path.join(td, "in.wav")
        opus_file = os.path.join(td, "mid.opus")
        out_wav = os.path.join(td, "out.wav")

        sf.write(in_wav, y, sr, subtype="PCM_16")

        # Encode with a random bitrate in [24, 64] kbps to vary degradation
        bitrate = np.random.choice([24, 32, 48, 64])
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-i", in_wav, "-c:a", "libopus", "-b:a", f"{bitrate}k",
             "-ar", "48000", opus_file],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-i", opus_file, "-ar", str(sr), "-ac", "1", out_wav],
            check=True,
        )

        y_out, _ = librosa.load(out_wav, sr=sr, mono=True)
        return y_out.astype(np.float32)


def aug_opus_plus_ns(y, sr):
    """Compound: Opus codec + spectral subtraction (simulates full browser path)."""
    from train_verification_v6 import aug_spectral_subtract, aug_compress
    y = aug_compress(y, sr)
    y = aug_opus_ffmpeg(y, sr)
    y = aug_spectral_subtract(y, sr)
    return y


if __name__ == "__main__":
    if not _ffmpeg_available():
        print("WARNING: ffmpeg not found on PATH.")
        print("         Install from https://ffmpeg.org/ or via choco/winget,")
        print("         then re-run. Falling back to V6 (no real Opus).")
        extra = None
    else:
        print("ffmpeg found — including real Opus codec augmentation")
        # Add Opus aug 3× (3 different bitrates per sample via randomization)
        # and one compound aug. Opus calls are slow, ~500ms each; expect long training.
        extra = [aug_opus_ffmpeg, aug_opus_ffmpeg, aug_opus_ffmpeg, aug_opus_plus_ns]

    # Save to v7 path
    model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "models", "user_verify_svm_v7.pkl",
    )
    train(extra_augs=extra, model_path=model_path, version_tag="v7")
