"""
Text-to-Speech Module (Module 7)

Two backends demonstrating the lecture's simple-API vs neural-TTS dichotomy:

    "pyttsx3"  — OS-level simple API. Emotion tag drives fundamentals only
                 (rate, volume, pitch), per Module 6 Page 35's prosody table.
                 Cannot modulate intonation → mechanical but controllable.

    "openai"   — gpt-4o-mini-tts neural model. Emotion tag is translated to a
                 natural-language instruction, which the model's prosody
                 embedding consumes. Produces coherent intonation contours that
                 simple APIs cannot.

Pipeline interface:
    process(text, emotion="neutral", backend="pyttsx3") → bytes (audio, mp3 or wav)

Emotions (5): happy, excited, calm, apologetic, neutral.
"""

import os
import subprocess
import sys
import tempfile


# ---------------------------------------------------------------------------
# Emotion → pyttsx3 prosody deltas   (Module 6 Page 35)
# ---------------------------------------------------------------------------
BASE_RATE   = 170      # words per minute, pyttsx3 default ~200
BASE_VOLUME = 0.85

PROSODY_BY_EMOTION = {
    "happy":      {"rate_delta":  50, "volume_delta":  0.15},
    "excited":    {"rate_delta":  70, "volume_delta":  0.15},
    "calm":       {"rate_delta": -45, "volume_delta": -0.20},
    "apologetic": {"rate_delta": -30, "volume_delta": -0.15},
    "neutral":    {"rate_delta":   0, "volume_delta":  0.00},
}


# ---------------------------------------------------------------------------
# Emotion → OpenAI natural-language instructions
# ---------------------------------------------------------------------------
# Tip: more detailed instructions → more expressive output. gpt-4o-mini-tts
# follows these prompts to shape prosody/intonation. Edit freely to tune the
# VA's "personality". Voices: alloy / echo / nova / shimmer / coral / ash / sage.
OPENAI_VOICE = "nova"

INSTRUCTIONS_BY_EMOTION = {
    "happy": (
        "Voice affect: bright, warm, and genuinely happy — the kind of tone a "
        "friend uses when sharing good news. "
        "Tone: cheerful and inviting, not sarcastic. "
        "Pacing: lively, with noticeable upward inflection on key positive words. "
        "Energy: smile audibly while speaking. "
        "Delivery: let the joy come through naturally — do not mumble."
    ),
    "excited": (
        "Voice affect: high energy, thrilled, almost bubbly. "
        "Tone: excited, like describing something amazing you just saw. "
        "Pacing: fast, with dynamic pitch rises on important words. "
        "Energy: animated, expressive, almost breathless in enthusiasm. "
        "Delivery: emphasize numbers, names, and superlatives with extra punch."
    ),
    "calm": (
        "Voice affect: gentle, soft, and soothing, like reading a bedtime story. "
        "Tone: warm, unhurried, reassuring. "
        "Pacing: slow and deliberate, with natural pauses between phrases. "
        "Energy: low-key and tender. "
        "Delivery: lower overall pitch; avoid any sharp or fast transitions."
    ),
    "apologetic": (
        "Voice affect: sincerely regretful, slightly hesitant, noticeably softer. "
        "Tone: genuinely sorry — imagine telling a child you couldn't find their toy. "
        "Pacing: a touch slower, with small pauses before the apology. "
        "Energy: subdued, downward inflection on apologies. "
        "Delivery: gentle and caring, never flippant or robotic."
    ),
    "neutral": (
        "Voice affect: clear, friendly, informative. "
        "Tone: like a helpful friend explaining something. "
        "Pacing: natural conversational speed. "
        "Energy: pleasant and engaged, not flat. "
        "Delivery: articulate and warm, like customer service done well."
    ),
}


# ---------------------------------------------------------------------------
# pyttsx3 backend
# ---------------------------------------------------------------------------

def _pick_english_voice(engine):
    """Force an English voice if available — otherwise pyttsx3 reads
    everything (including English words!) with the system default voice,
    which on zh-locale machines is a Chinese voice that mispronounces English.
    """
    try:
        voices = engine.getProperty("voices")
        # Tier 1 — inspect the .languages attribute (most reliable when present)
        for v in voices:
            langs = getattr(v, "languages", []) or []
            for lang in langs:
                if isinstance(lang, bytes):
                    lang = lang.decode(errors="ignore")
                if "en" in str(lang).lower():
                    engine.setProperty("voice", v.id)
                    return
        # Tier 2 — name/id keyword match (Windows SAPI5 and macOS NSSpeech names)
        keywords = ("english", "en-us", "en_us", "en-gb",
                    "zira", "david", "mark", "hazel",      # Windows
                    "alex", "samantha", "victoria", "daniel", "karen", "fred", "tom")  # macOS
        for v in voices:
            name = (v.name or "").lower()
            vid  = (v.id   or "").lower()
            if any(kw in name or kw in vid for kw in keywords):
                engine.setProperty("voice", v.id)
                return
    except Exception as e:
        print(f"[TTS] could not select English voice: {e}")


def _aiff_to_wav_bytes(aiff_path):
    """Convert AIFF → WAV using macOS-native afconvert. Chrome on macOS refuses
    to play AIFF inline and hands it off to system Media Session (the Now
    Playing widget), which is useless for a hands-free VA demo."""
    wav_path = aiff_path + ".wav"
    subprocess.run(
        ["afconvert", aiff_path, wav_path,
         "-f", "WAVE", "-d", "LEI16@22050"],
        check=True, capture_output=True,
    )
    try:
        with open(wav_path, "rb") as f:
            return f.read()
    finally:
        try: os.unlink(wav_path)
        except Exception: pass


def _process_macos_say(text, emotion):
    """macOS-native TTS via the `say` CLI command.

    pyttsx3's nsss driver crashes in Flask worker threads (needs the main
    thread's NSRunLoop). The `say` command runs as a separate process, so
    it works from any thread. Outputs AIFF → converted to WAV for Chrome.
    """
    params = PROSODY_BY_EMOTION.get(emotion, PROSODY_BY_EMOTION["neutral"])
    rate = BASE_RATE + params["rate_delta"]

    tmp = tempfile.NamedTemporaryFile(suffix=".aiff", delete=False)
    tmp.close()

    try:
        subprocess.run(
            ["say", "-o", tmp.name, "--rate", str(rate), text],
            check=True, capture_output=True, timeout=15,
        )

        if not os.path.exists(tmp.name) or os.path.getsize(tmp.name) < 100:
            raise RuntimeError("macOS say command produced empty audio")

        return _aiff_to_wav_bytes(tmp.name)
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def _process_pyttsx3(text, emotion):
    """Render text to audio bytes using OS-level simple TTS.

    macOS: delegates to `say` command (pyttsx3 nsss driver is broken in threads).
    Windows/Linux: uses pyttsx3 directly → WAV output.
    """
    if sys.platform == "darwin":
        return _process_macos_say(text, emotion)

    import pyttsx3

    params = PROSODY_BY_EMOTION.get(emotion, PROSODY_BY_EMOTION["neutral"])

    engine = pyttsx3.init()
    _pick_english_voice(engine)
    engine.setProperty("rate", BASE_RATE + params["rate_delta"])
    engine.setProperty("volume",
                       max(0.0, min(1.0, BASE_VOLUME + params["volume_delta"])))

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()

    try:
        engine.save_to_file(text, tmp.name)
        engine.runAndWait()
        engine.stop()

        if not os.path.exists(tmp.name) or os.path.getsize(tmp.name) < 100:
            raise RuntimeError("pyttsx3 produced empty audio")

        with open(tmp.name, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# OpenAI backend
# ---------------------------------------------------------------------------

_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set — OpenAI TTS unavailable. "
                "Add it to .env or switch to pyttsx3 backend."
            )
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _process_openai(text, emotion):
    """Render text to MP3 bytes via OpenAI's gpt-4o-mini-tts neural model."""
    client = _get_openai_client()
    instructions = INSTRUCTIONS_BY_EMOTION.get(emotion,
                                               INSTRUCTIONS_BY_EMOTION["neutral"])

    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=OPENAI_VOICE,
        input=text,
        instructions=instructions,
        response_format="mp3",
    )
    return response.content


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

_BACKENDS = {
    "pyttsx3": _process_pyttsx3,
    "openai":  _process_openai,
}


def mime_for_backend(backend):
    """MIME type of the audio bytes returned by a given backend.

    Used by the caller to build a data: URI for the frontend. pyttsx3 produces
    platform-native formats (WAV on Win/Linux, AIFF on macOS); OpenAI produces MP3.
    """
    if backend == "openai":
        return "audio/mpeg"
    # pyttsx3 — WAV on all platforms (macOS AIFF is post-converted via afconvert)
    return "audio/wav"


def process(text, emotion="neutral", backend="pyttsx3"):
    """Synthesize speech, return raw audio bytes.

    Args:
        text:    what to say.
        emotion: one of {happy, excited, calm, apologetic, neutral}. Unknown values
                 fall back to neutral.
        backend: "pyttsx3" (simple API) or "openai" (neural).

    Returns:
        bytes — encoded audio. Caller base64-encodes for JSON transport and
        pairs with mime_for_backend(backend) for the data: URI.

    Raises:
        ValueError:   unknown backend.
        RuntimeError: OpenAI selected but API key missing.
        Other exceptions from the underlying library propagate up — app.py catches
        them and the frontend falls back to browser TTS.
    """
    if backend not in _BACKENDS:
        raise ValueError(f"unknown TTS backend: {backend!r}")
    return _BACKENDS[backend](text, emotion)
