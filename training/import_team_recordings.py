"""
Import team members' Activity-1 recordings (m4a) as additional authorized samples.

Existing authorized set only has "Fengshou-positive-*" and "Tan-positive-*" — i.e.
only the "hey atlas" phonetic context. This script adds the 'near' and 'other'
recordings too, tripling authorized data per speaker and covering more phonetic
contexts (better speaker generalization, less overfit to a specific phrase).

Note: these iPhone recordings do NOT solve the WebRTC browser channel mismatch —
for that you still need to collect browser-recorded samples via static/record.html.

Usage:
    python training/import_team_recordings.py
"""

import os
import sys

import librosa
import soundfile as sf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_DIR = os.path.dirname(BASE_DIR)
RAW_DIR = os.path.join(PARENT_DIR, "CSI5180 Project Plan (Claude)", "raw_recordings")
AUTH_DIR = os.path.join(BASE_DIR, "data", "voices", "authorized")

TEAM_MEMBERS = ["Fengshou", "Tan"]  # Laura has no Activity 1 recordings
SUB_DIRS = ["positive", "near", "other"]
TARGET_SR = 16000


def convert_one(src_path, dst_path):
    """Load m4a/mp3/etc with librosa, save as 16kHz mono WAV."""
    audio, _ = librosa.load(src_path, sr=TARGET_SR, mono=True)
    sf.write(dst_path, audio, TARGET_SR, subtype="PCM_16")


def main():
    if not os.path.isdir(RAW_DIR):
        print(f"ERROR: raw recordings dir not found: {RAW_DIR}")
        sys.exit(1)

    os.makedirs(AUTH_DIR, exist_ok=True)
    added = 0
    skipped = 0

    for member in TEAM_MEMBERS:
        for sub in SUB_DIRS:
            src_dir = os.path.join(RAW_DIR, sub)
            if not os.path.isdir(src_dir):
                continue
            for fname in os.listdir(src_dir):
                if not fname.lower().endswith((".m4a", ".mp3", ".wav")):
                    continue
                if not fname.lower().startswith(member.lower()):
                    continue

                # Output filename: keep role-number, force .wav
                base = os.path.splitext(fname)[0]
                dst_name = f"{base}.wav"
                dst_path = os.path.join(AUTH_DIR, dst_name)

                if os.path.exists(dst_path):
                    print(f"  [skip] already exists: {dst_name}")
                    skipped += 1
                    continue

                try:
                    src_path = os.path.join(src_dir, fname)
                    convert_one(src_path, dst_path)
                    print(f"  [ok]   {member}/{sub}: {fname} -> {dst_name}")
                    added += 1
                except Exception as e:
                    print(f"  [err]  {fname}: {e}")

    print(f"\nDone. Added {added} new authorized samples (skipped {skipped} existing).")
    print(f"Total authorized files in {AUTH_DIR}:")
    wavs = [f for f in os.listdir(AUTH_DIR) if f.endswith(".wav")]
    print(f"  {len(wavs)} WAV files")


if __name__ == "__main__":
    main()
