# Atlas VA — Module-by-Module Guide

This document explains each pipeline module with concrete input/output examples.

## Pipeline Overview

```
Audio → [1. Verify] → [2. Wake] → [3. ASR] → [4. Intent] → [5. Fulfillment] → [6. NLG] → [7. TTS] → Audio
```

Each module is independent and has a `process()` method. The orchestrator (`app.py`) chains them together.

---

## Module 1: User Verification (`pipeline/user_verification.py`)

**Purpose**: Confirm the speaker is an authorized user via voiceprint.

**How it works**:
- Extracts MFCC features from audio (20 coefficients + deltas)
- Feeds features into a pre-trained SVM classifier
- SVM outputs P(authorized) — compared against threshold (0.5)

**Example**:
```python
from pipeline.user_verification import process, bypass

# Voice verification
result = process(audio_numpy_array)
# → {"verified": True, "confidence": 0.847}

# Bypass with passcode
result = bypass("Doro")
# → {"verified": True}
```

**Feature versions**:
| Version | Features | Dims | Notes |
|---------|----------|------|-------|
| v1 | mean + std MFCC | 40 | Simple, channel-sensitive |
| v2 | std MFCC + delta-std + delta2-std | 60 | Channel-robust (default) |
| v5 | mean + std + delta-std + delta2-std | 80 | Most features |

---

## Module 2: Wake Word Detection (`pipeline/wake_word.py`)

**Purpose**: Detect the wake phrase "Hey Atlas" in audio.

**How it works**:
- Extracts 13 MFCCs from 2-second audio clip → spectrogram image (13 x 81)
- Feeds into a 2-layer CNN (Conv2d → Pool → Conv2d → Pool → FC → sigmoid)
- Output is P(wake word present)

**Example**:
```python
from pipeline.wake_word import process, bypass

result = process(audio_numpy_array)
# → {"detected": True, "confidence": 0.923}

result = bypass("hey atlas")
# → {"detected": True}

result = bypass("hello")
# → {"detected": False}
```

**CNN architecture**:
```
Input: (1, 1, 13, 81) — single-channel MFCC spectrogram
  → Conv2d(1→16, 3x3) + ReLU + MaxPool(2x2)    → (1, 16, 6, 40)
  → Conv2d(16→32, 3x3) + ReLU + MaxPool(2x2)   → (1, 32, 3, 20)
  → Flatten → Dropout(0.3)                       → (1, 1920)
  → Linear(1920→32) + ReLU + Dropout(0.3)        → (1, 32)
  → Linear(32→1) + Sigmoid                       → (1, 1)  ∈ [0, 1]
```

---

## Module 3: ASR (`pipeline/asr.py`)

**Purpose**: Convert speech audio to text using OpenAI Whisper.

**How it works**:
- Uses Whisper `small.en` (244M params, English-only)
- Domain prompt biases decoder toward Atlas vocabulary
- Silence gate (RMS < 0.01) prevents hallucination on empty audio

**Example**:
```python
from pipeline.asr import ASRModule

asr = ASRModule(model_name="small.en")

text = asr.process(audio_numpy_array)
# → "What's the weather in Ottawa?"

# Silent audio → None (blocked by energy gate)
text = asr.process(silent_audio)
# → None
```

---

## Module 4: Intent Detection (`pipeline/intent_detection.py`)

**Purpose**: Classify user intent + extract slot entities from text.

**How it works**:
- DistilBERT encoder produces 768-dim embeddings per token
- Intent head: [CLS] token → 2-layer MLP → 22 intent classes
- Slot head: all tokens → linear → BIO slot labels (per token)
- Slot labels are grouped using BIO scheme (B-CITY, I-CITY → one "city" slot)

**Example**:
```python
from pipeline.intent_detection import IntentDetector

detector = IntentDetector()

result = detector.process("What's the weather in Ottawa?")
# → {"intent": "weather",
#    "confidence": 0.98,
#    "slots": {"city": "Ottawa"}}

result = detector.process("Who starred in Inception?")
# → {"intent": "get_movie_cast",
#    "confidence": 0.95,
#    "slots": {"title": "Inception"}}

result = detector.process("Feed Doro some fish")
# → {"intent": "feed_pet",
#    "confidence": 0.97,
#    "slots": {"food_type": "fish"}}
```

**22 intents**: greetings, goodbye, oos, set_timer, weather, 8 movie intents, 9 pet intents.

**Slot types**: CITY, DURATION, FOOD_TYPE, GENRE, NAME, TIME_WINDOW, TITLE, TOY, TREAT_TYPE.

---

## Module 5: Fulfillment (`pipeline/fulfillment.py`)

**Purpose**: Execute the detected intent — call APIs, update state.

**How it works**:
- Routes by intent type → `process_weather()`, `process_movies()`, `process_pet()`, etc.
- Weather: OpenWeatherMap geocoding → weather fetch (metric units)
- Movies: TMDB search → details (cast, plot, rating, runtime, director, similar)
- Pet: Updates `PetState` (hunger/happiness/energy/cleanliness), with cap detection and name validation

**Example**:
```python
from pipeline.fulfillment import FulfillmentModule

fm = FulfillmentModule()

# Weather
result = fm.process({"intent": "weather", "slots": {"city": "Ottawa"}})
# → {"type": "weather", "city": "Ottawa", "country": "CA",
#    "temperature": 12.5, "description": "clear sky", "windspeed": 3.2}

# Movie
result = fm.process({"intent": "get_movie_cast", "slots": {"title": "Inception"}})
# → {"type": "movie", "title": "Inception",
#    "cast": ["Leonardo DiCaprio", "Tom Hardy", ...],
#    "runtime": 148, "runtime_str": "2h 28m", ...}

# Pet (successful)
result = fm.process({"intent": "feed_pet", "slots": {}, "transcript": "feed doro"})
# → {"type": "pet", "action": "feed_pet", "pet_name": "Doro",
#    "before": {"hunger": 50, ...}, "status": {"hunger": 75, ...},
#    "food_type": "food"}

# Pet (cap hit)
# (if hunger is already >= 95)
# → {"type": "pet", "action": "feed_pet", "pet_name": "Doro",
#    "cap_warning": {"stat": "hunger", "level": "max", ...}}

# Pet (wrong name)
result = fm.process({"intent": "feed_pet", "slots": {}, "transcript": "feed ryan"})
# → {"type": "pet", "action": "feed_pet", "error": "wrong_name",
#    "pet_name": "Doro", "spoken_name": "ryan"}
```

---

## Module 6: NLG (`pipeline/nlg.py`)

**Purpose**: Generate a natural-language response from fulfillment data.

**Two modes**:
- **Template**: Deterministic, hand-crafted responses per intent. Reliable.
- **LLM**: SmolLM2-360M-Instruct generates varied responses. Less reliable.

**How it works (template)**:
- Look up intent → handler function (e.g., `_template_feed_pet`)
- Handler formats data into 2-3 randomized template variants
- Pet templates append mood reactions ("Doro looks really happy!")

**How it works (LLM)**:
- Build system+user message pair (role persona + fulfillment data)
- Apply chat template → tokenize → generate (temperature=0.7, max 80 tokens)
- Keep first sentence only (`_first_sentence` handles abbreviations like "Dr.")
- Fall back to template on empty/error output

**Example**:
```python
from pipeline import nlg

# Template mode
result = nlg.process(
    {"intent": "feed_pet", "slots": {}},
    {"type": "pet", "pet_name": "Doro", "food_type": "fish",
     "before": {"happiness": 50}, "status": {"happiness": 70}},
    method="template"
)
# → {"text": "Doro happily ate the fish! Doro seems happy.", "emotion": "happy"}

# Cap warning
result = nlg.process(
    {"intent": "feed_pet", "slots": {}},
    {"type": "pet", "pet_name": "Doro",
     "cap_warning": {"stat": "hunger", "level": "max"}},
    method="template"
)
# → {"text": "Doro is already full! Maybe wait a bit before feeding again.",
#    "emotion": "calm"}
```

**Emotion tags**: happy, excited, calm, apologetic, neutral — consumed by TTS for prosody.

---

## Module 7: TTS (`pipeline/tts.py`)

**Purpose**: Convert text + emotion tag to spoken audio.

**Two backends**:
- **pyttsx3**: OS-level TTS (SAPI5/nsss). Fast, offline, basic quality. Emotion controls rate/volume.
- **OpenAI**: Neural TTS (gpt-4o-mini-tts). High quality, requires API key + internet.

**Prosody by emotion (pyttsx3)**:
| Emotion | Rate delta | Volume delta |
|---------|-----------|--------------|
| happy | +50 wpm | +0.15 |
| excited | +70 wpm | +0.15 |
| calm | -45 wpm | -0.20 |
| apologetic | -30 wpm | -0.15 |
| neutral | 0 | 0 |

**Example**:
```python
from pipeline.tts import process

audio_bytes, mime_type = process("Hello!", emotion="happy", backend="pyttsx3")
# → (b'\x52\x49\x46\x46...', "audio/wav")
```

---

## Full Pipeline Example

User says: **"What movies are similar to Inception?"**

```
Step 1 — Verify: (already unlocked)
Step 2 — Wake:   (already awake)
Step 3 — ASR:    "What movies are similar to Inception?" 
Step 4 — Intent: {"intent": "get_similar_movies", "confidence": 0.94,
                  "slots": {"title": "Inception"}}
Step 5 — Fulfill: {"type": "movie", "title": "Inception",
                   "similar": ["Shutter Island", "The Prestige", ...]}
Step 6 — NLG:    {"text": "If you liked Inception, you might enjoy:
                   Shutter Island, The Prestige, Interstellar, 
                   The Matrix, Memento.",
                  "emotion": "neutral"}
Step 7 — TTS:    audio/wav bytes (neutral prosody)
```

User says: **"Feed Doro some fish"**

```
Step 3 — ASR:    "Feed Doro some fish"
Step 4 — Intent: {"intent": "feed_pet", "slots": {"food_type": "fish"}}
Step 5 — Fulfill: {"type": "pet", "action": "feed_pet", "pet_name": "Doro",
                   "food_type": "fish",
                   "before": {"hunger": 44, ...},
                   "status": {"hunger": 69, ...}}
Step 6 — NLG:    {"text": "Doro happily ate the fish! Doro seems full.",
                  "emotion": "happy"}
Step 7 — TTS:    audio/wav bytes (fast + loud prosody)
```
