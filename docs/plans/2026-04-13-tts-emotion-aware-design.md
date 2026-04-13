# Emotion-Aware TTS — Design Doc

**Date**: 2026-04-13
**Status**: Approved, implementing
**Owner**: Fengshou (with Claude)

## Motivation

The Step 3 Video Report explicitly requires: *"reflect on the notion of emotion-aware
VA and discuss if your VA has a general mood or not and why."* Our current
implementation uses `window.speechSynthesis` (Web Speech API) on the frontend — the
exact "simple API" Caroline showed on Module 6 slide 23 as a limited approach. It
cannot modulate intonation, and we weren't even modulating fundamentals — every
response was spoken in the same flat voice. We had no story for the emotion-aware
reflection question.

Additionally, Laura's architecture diagram correctly places TTS as a backend module
at the end of the pipeline; our current frontend-only implementation breaks that
visual claim.

## Design

Two layers work together:

### Layer 1 — NLG emits emotion tags

NLG already decides *what* to say. It should also decide the intended *emotional
register* of what it says, because semantic context lives here (Caroline's principle:
"NLG 管说什么"). `nlg.process()` returns `{"text": str, "emotion": str}`.

`emotion ∈ {happy, excited, calm, apologetic, neutral}` — five categories chosen to
map cleanly onto Module 6 Page 35's emotion-prosody table while staying tractable.

Emotion is derived in three tiers:

1. **Hard failure**: `api_response["type"] == "error"` (exception caught by app.py)
   → `apologetic`
2. **Soft failure**: expected data field is empty/missing (e.g., `cast=[]`, `temperature=None`,
   `duration=-1`) → `apologetic`
3. **Normal**: intent → emotion lookup table → `happy/excited/calm/neutral`

This tiered approach means failed lookups automatically sound regretful, even when
the NLG template is the same "Sorry, couldn't find..." fallback string. This is a
concrete example of **adaptive emotional response** beyond static intent mapping —
a good demo moment.

### Layer 2 — TTS consumes emotion tags via two backends

Symmetric with the NLG template/LLM toggle: user picks backend at request time.

#### Backend A — `pyttsx3` (simple API, demonstrates lecture's fundamentals-only limit)

Maps emotion → rate/volume deltas directly from Module 6 Page 35:

```
happy      → rate +30,  volume +0.15   # fast + loud
excited    → rate +40,  volume +0.20   # faster + louder
calm       → rate -25,  volume -0.15   # slow + soft
apologetic → rate -10,  volume -0.10   # slightly slow + soft
neutral    → rate  0,   volume  0
```

Base rate 170 wpm, base volume 0.85. pyttsx3 saves to a temp WAV/AIFF, read bytes,
base64 encode, send to frontend.

Academic framing for the report: "this demonstrates the limit — we modulate the
three fundamentals (rate, volume, pitch) per the lecture's prosody glossary, but
intonation contour is not accessible via simple APIs."

#### Backend B — OpenAI `gpt-4o-mini-tts` (neural TTS, demonstrates modern architecture)

Maps emotion → natural-language instruction:

```
happy      → "Speak with warm, cheerful enthusiasm."
excited    → "Speak with upbeat energy, slightly faster tempo."
calm       → "Speak in a gentle, soothing tone, slightly slower."
apologetic → "Speak in a hesitant, slightly apologetic tone."
neutral    → "Speak in a clear, friendly, informative tone."
```

Voice: `nova` (warm female default). Response format `mp3`.

Academic framing: "this demonstrates the neural approach — prosody embedding in
the model consumes natural-language style instructions, producing coherent
intonation the simple API cannot."

### Flask wiring

`/api/pipeline`:
- Reads new form field `tts_backend` (default `pyttsx3`)
- After NLG, unpacks `{text, emotion}`
- Calls `tts_module.process(text, emotion, backend=tts_backend)` in try/except
- On success: base64-encodes MP3 bytes, adds `audio_b64` to response
- On failure: `audio_b64=None`, frontend falls back to browser Web Speech API
- Response also includes `emotion` field for UI display/debug

### Frontend

- `index.html`: add a second `<select id="tts-backend">` next to the NLG dropdown
  (options: `pyttsx3` / `openai`)
- `main.js sendPipeline()`:
  - Send `tts_backend` in FormData
  - On response: `if (d.audio_b64) new Audio('data:audio/mp3;base64,' + d.audio_b64).play(); else speak(d.answer);`
  - Keep `speak()` as fallback for network/TTS failures

## Data Flow

```
Audio/text → /api/pipeline
           ↓
       ASR (if audio)
           ↓
     Intent Detection
           ↓
       Fulfillment ─→ external APIs (TMDB, OpenWeather) or PetState
           ↓ (success or exception-caught error object)
           NLG (template|llm)
           ↓ returns {text, emotion}   ← emotion derived here
           TTS (pyttsx3|openai)
           ↓ returns MP3 bytes         ← emotion drives prosody
       base64 + JSON response
           ↓
       Frontend plays audio (or speak() fallback)
```

## Files changed

| File | Change |
|------|--------|
| `pipeline/nlg.py` | `process()` returns dict; new `_derive_emotion(intent, api_response)` |
| `pipeline/tts.py` | **NEW** — two backends, shared emotion interface |
| `app.py` | `/api/pipeline` unpacks NLG dict, calls TTS, adds `audio_b64` to response; startup warning for missing OPENAI_API_KEY |
| `static/index.html` | Add TTS backend `<select>` next to NLG toggle |
| `static/js/main.js` | Send `tts_backend`; play `audio_b64` or fallback to `speak()` |
| `requirements.txt` | Add `openai>=1.0`, `pyttsx3>=2.90` |
| `.env` | (user) add `OPENAI_API_KEY=sk-...` |

## Non-goals / YAGNI

- **Not** doing SSML-based edge-tts as a third backend (pyttsx3 + OpenAI is a cleaner
  pedagogical contrast: simple API vs neural TTS)
- **Not** refactoring fulfillment module to emit structured errors — we keep the
  "empty field detection" heuristic in NLG
- **Not** adding Ekman's 6 emotions — 5 is enough for our 22 intents and maps
  cleanly to the prosody table
- **Not** adding per-user voice preferences or voice customization UI

## Testing checklist

- Each emotion category produces audible difference in pyttsx3 (rate/volume)
- OpenAI responds in < 2 seconds for typical response (~50 chars)
- Failure path: typing a nonsense movie title ("get_movie_cast" → empty cast) →
  NLG says "Sorry I couldn't find..." → TTS sounds apologetic
- Failure path: killing network mid-request → frontend falls back to browser TTS
  silently (no crash)
- pyttsx3 on macOS: confirm save_to_file produces playable audio (AIFF or WAV)
- Fresh start: app runs without OPENAI_API_KEY if only pyttsx3 is used

## Report narrative (for Laura)

> For TTS we implemented two backends mirroring the NLG template/LLM split, so we
> can directly demonstrate the contrast Caroline drew in Module 6 between simple
> APIs and neural TTS.
>
> First, the NLG module now emits an emotion tag alongside the answer text —
> decoupling "what to say" from "how to say it" as the lecture emphasized. The
> emotion is derived in three tiers: hard failures from fulfillment exceptions
> become *apologetic*, soft failures (empty API responses, unknown movies) also
> become *apologetic*, and successful intents map to happy/excited/calm/neutral.
> This means when you ask Atlas about a movie it can't find, it doesn't just say
> "Sorry" — it actually sounds sorry.
>
> The pyttsx3 backend illustrates the simple-API limit: we modulate rate and
> volume per the lecture's prosody table — happy gets +30 wpm and +0.15 loudness,
> calm gets the opposite. But intonation contour is not controllable at this
> layer, so the voice remains mechanical.
>
> The OpenAI `gpt-4o-mini-tts` backend illustrates modern neural TTS. We translate
> the emotion tag into a natural-language instruction like "speak with warm,
> cheerful enthusiasm", which the model's prosody embedding consumes. This
> produces coherent intonation the simple API cannot.
>
> Atlas's general mood is energetic and friendly, but within that base, mood
> shifts per-intent and per-outcome through this emotion-tag pipeline — a
> concrete, code-level implementation of the emotion-aware VA concept.
