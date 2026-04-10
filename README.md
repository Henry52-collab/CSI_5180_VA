# Atlas — CSI 5180 Voice Assistant

> CSI 5180: Topics in AI — Virtual Assistants | uOttawa Winter 2026 | Group 18

A movie & virtual pet voice assistant with a 7-module pipeline.

## Team

- Fengshou Xu (300036335)
- Ruiheng Tan (300102229)
- Laura Jin (300174154)

## Pipeline

```
User Verification → Wake Word → ASR → Intent Detection → Fulfillment → NLG → TTS
     (Locked)       (Sleep)    (Ready)     (NLU)          (Action)     (Answer) (Speech)
```

## Domains

- **Specialized Domain:** Movie information retrieval (TMDB API) — 8 intents
- **Control System:** Virtual pet simulation (stateful) — 9 intents
- **Basic:** OOS, Greetings, Goodbye, Timer, Weather — 5 intents

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in API keys
python app.py
```

## Pretrained Models

Trained model weights are **not committed** to the repo (too large for GitHub).
You have three options:

1. **GitHub Release** — download the latest release assets from the
   [Releases page](https://github.com/Henry52-collab/CSI_5180_VA/releases)
2. **Shared cloud drives:**
   - Dropbox: https://www.dropbox.com/scl/fo/9ikktf9d3rx9jajckh1st/ABlV6hiniWJ4rs-d5mpAhN8?rlkey=axp5xk5cspp7tib14zuprn4t3&st=cwbjz46i&dl=0
   - Google Drive: https://drive.google.com/drive/folders/1NmHjJKRqhKSu88bOJMxzTEnIdoQA2VMK?usp=sharing
3. **Retrain locally** (only if you have CUDA or patience):
   ```bash
   python training/train_intent.py     # ~30s on GPU, ~15min on CPU
   ```

Place the downloaded files into the expected folders:
```
models/intent_bert/model.pth
models/intent_bert/label_maps.json
```

## Project Structure

```
atlas/
├── app.py                  # Flask web server
├── pipeline/               # 7 pipeline modules
├── training/               # Model training scripts
├── models/                 # Trained weights (gitignored)
├── data/intents/           # Intent training data
├── static/                 # Frontend assets
├── templates/              # HTML templates
└── TASKS.md                # Task board
```

## Task Board

See [TASKS.md](TASKS.md) for current progress and task assignments.
