"""
Bootstrap — pre-download all ML models used by Atlas VA.

Run this ONCE after `pip install -r requirements.txt`. Downloads (~800MB total):
    - OpenAI Whisper small.en (~460MB)
    - Hugging Face distilbert-base-uncased (intent detection backbone, ~260MB)
    - Hugging Face distilgpt2 (NLG LLM backend, ~330MB)

After this, `python app.py` starts in seconds because everything is cached on disk.

    $ python bootstrap.py
"""

import sys


def _step(n, total, msg):
    print(f"\n[{n}/{total}] {msg}")


TOTAL_STEPS = 3


def download_whisper():
    _step(1, TOTAL_STEPS, "Whisper small.en (speech recognition, ~460MB)...")
    try:
        import whisper
        whisper.load_model("small.en")
        print("      OK.")
    except Exception as e:
        print(f"      FAILED: {e}")
        print("      You can still run app.py — it will retry the download on startup.")
        return False
    return True


def download_distilbert():
    _step(2, TOTAL_STEPS, "distilbert-base-uncased (intent detection backbone, ~260MB)...")
    try:
        from transformers import AutoTokenizer, AutoModel
        AutoTokenizer.from_pretrained("distilbert-base-uncased")
        AutoModel.from_pretrained("distilbert-base-uncased")
        print("      OK.")
    except Exception as e:
        print(f"      FAILED: {e}")
        print("      This is REQUIRED — intent detection will not work without it.")
        return False
    return True


def download_smollm2():
    _step(3, TOTAL_STEPS, "SmolLM2-360M-Instruct (NLG LLM backend, ~720MB)...")
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        AutoTokenizer.from_pretrained("HuggingFaceTB/SmolLM2-360M-Instruct")
        AutoModelForCausalLM.from_pretrained("HuggingFaceTB/SmolLM2-360M-Instruct")
        print("      OK.")
    except Exception as e:
        print(f"      FAILED: {e}")
        print("      Non-fatal — the 'template' NLG mode still works without this.")
        return False
    return True


def main():
    print("=" * 60)
    print("  ATLAS VA — Bootstrap (one-time model download)")
    print("=" * 60)
    print("  Downloading ~1450MB of ML weights. This takes 3-15 minutes")
    print("  depending on your connection. Files are cached in:")
    print("    - ~/.cache/whisper/        (Whisper)")
    print("    - ~/.cache/huggingface/    (DistilBERT, SmolLM2)")
    print("=" * 60)

    results = []
    results.append(("Whisper small.en",              download_whisper()))
    results.append(("distilbert-base-uncased",       download_distilbert()))
    results.append(("SmolLM2-360M-Instruct",         download_smollm2()))

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    for name, ok in results:
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}] {name}")
    print("=" * 60)

    if all(ok for _, ok in results):
        print("\nDone. Run `python app.py` to start the assistant.\n")
        return 0
    else:
        print("\nSome downloads failed. app.py will try again on startup.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
