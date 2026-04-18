# Atlas VA — CSI 5180 Voice Assistant

> CSI 5180: Topics in AI — Virtual Assistants | uOttawa Winter 2026 | Group 18

A movie & virtual pet voice assistant with a 7-module pipeline.

## Team

- Fengshou Xu (300036335)
- Ruiheng Tan (300102229)
- Laura Jin (300174154)

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API keys
cp .env.example .env
# Edit .env and fill in your keys (see API Keys section below)

# 3. Run
python app.py
```

Then open **http://localhost:5000** in Chrome.

On first launch, Whisper and DistilBERT models will be downloaded automatically (~1 GB). Subsequent launches are instant.

## API Keys (`.env`)

| Key | Required for | Free tier | Required? |
|-----|-------------|-----------|-----------|
| `TMDB_API_KEY` | Movie intents | Yes | Yes |
| `OPENWEATHER_API_KEY` | Weather intent | Yes | Yes |
| `OPENAI_API_KEY` | Neural TTS (OpenAI) | Pay-per-use | No — falls back to local TTS |

Register for free at:
- TMDB: https://www.themoviedb.org/settings/api
- OpenWeatherMap: https://openweathermap.org/api

## Pretrained Models

Model weights are included in the repo for convenience:

| File | Module | Size |
|------|--------|------|
| `models/user_verify_svm_v2.pkl` | User Verification (SVM) | ~50 KB |
| `models/wake_word_cnn.pth` | Wake Word Detection (CNN) | ~250 KB |
| `models/intent_bert/model.pth` | Intent Detection (DistilBERT) | ~260 MB |
| `models/intent_bert/label_maps.json` | Intent/Slot label mapping | ~1 KB |

If `model.pth` is missing (too large for GitHub), download from:
- [Google Drive](https://drive.google.com/drive/folders/1NmHjJKRqhKSu88bOJMxzTEnIdoQA2VMK?usp=sharing)
- [Dropbox](https://www.dropbox.com/scl/fo/9ikktf9d3rx9jajckh1st/ABlV6hiniWJ4rs-d5mpAhN8?rlkey=axp5xk5cspp7tib14zuprn4t3&st=cwbjz46i&dl=0)

Or retrain locally:
```bash
python training/train_intent.py     # ~30s on GPU, ~15 min on CPU
```

## Usage

### Voice Mode
1. **Verify** — Speak into the mic (or type bypass passcode "Doro")
2. **Wake** — Say "Hey Atlas" (or type it)
3. **Talk** — Click the mic button and ask a question

### Text Bypass
Type directly in the "Ask Atlas anything..." input box and click Send.

### Developer Mode
Expand "Developer Mode — Intent Bypass" to manually inject any intent with custom slots.

### Example Queries

| Category | Example | What happens |
|----------|---------|-------------|
| Movie | "Who starred in Inception?" | Returns cast list from TMDB |
| Movie | "What are some trending movies?" | Returns current trending list |
| Weather | "What's the weather in Ottawa?" | Returns temperature + conditions |
| Timer | "Set a timer for 5 minutes" | Starts countdown timer |
| Pet | "Feed Doro some fish" | Hunger +25, mood reaction |
| Pet | "Play with Ryan" (pet = Doro) | Rejected: wrong pet name |
| Pet | Feed when hunger >= 95 | Refused: "Doro is already full!" |
| Pet | "Feed Doro an orange" | 50% chance of favorite food reaction |

### NLG / TTS Toggle
- **NLG**: Switch between `Template` (reliable) and `LLM (SmolLM2)` (varied but less reliable)
- **TTS**: Switch between `Local` (pyttsx3, offline) and `Neural (OpenAI)` (requires API key)

## Pipeline

```
Audio → [1. Verify] → [2. Wake] → [3. ASR] → [4. Intent] → [5. Fulfillment] → [6. NLG] → [7. TTS] → Audio
         SVM            CNN        Whisper    DistilBERT     API/PetState      Template    pyttsx3
         voiceprint     MFCC+CNN   small.en   joint model    TMDB/Weather      or LLM      or OpenAI
```

## Project Structure

```
CSI_5180_VA/
├── app.py                          # Flask server — pipeline orchestrator
├── requirements.txt                # Python dependencies
├── .env.example                    # API key template
│
├── pipeline/                       # 7 pipeline modules
│   ├── user_verification.py        # Module 1: SVM speaker verification
│   ├── wake_word.py                # Module 2: CNN wake word detection
│   ├── asr.py                      # Module 3: Whisper ASR + silence gate
│   ├── intent_detection.py         # Module 4: DistilBERT joint intent+slot
│   ├── fulfillment.py              # Module 5: API calls + PetState
│   ├── nlg.py                      # Module 6: Template + SmolLM2 generation
│   ├── tts.py                      # Module 7: pyttsx3 + OpenAI TTS
│   └── utils/
│       ├── movie.py                # TMDB API wrapper
│       └── weather.py              # OpenWeatherMap API wrapper
│
├── training/                       # Model training scripts
│   ├── train_intent.py             # DistilBERT fine-tuning
│   ├── train_verification.py       # SVM training (v1)
│   ├── train_verification_v2.py    # SVM training (v2, channel-robust)
│   ├── train_wake_word.py          # CNN training
│   └── import_team_recordings.py   # Voice data import utility
│
├── models/                         # Trained model weights
│   ├── intent_bert/
│   │   ├── model.pth               # DistilBERT weights
│   │   └── label_maps.json         # Intent + slot label lists
│   ├── user_verify_svm_v2.pkl      # SVM verification model
│   └── wake_word_cnn.pth           # CNN wake word model
│
├── data/
│   ├── intents/training_data.py    # 22 intents, ~600 training sentences
│   ├── voices/                     # Speaker verification audio
│   └── Wakeword/                   # Wake word detection audio
│
├── static/                         # Frontend
│   ├── index.html                  # Main UI
│   ├── css/style.css               # Dark theme styling
│   ├── js/main.js                  # UI logic, recording, playback
│   └── js/doro3d.js                # Three.js 3D pet animations
│
└── TASKS.md                        # Task assignments
```

## System Requirements

- Python 3.9+
- Chrome browser (recommended — tested, mic recording works)
- ~2 GB disk (models + dependencies)
- GPU optional (CPU works, just slower on first ASR call)

## Known Limitations

- Voice verification only reliably recognizes team members (limited training data)
- Wake word can trigger on phonetically similar phrases ("Hey Alice")
- ASR may hallucinate on silent/very noisy input (mitigated with energy gate)
- Weather disambiguation limited to single city name (no multi-turn "which country?")
- SmolLM2 LLM mode produces inconsistent quality; template mode is recommended
