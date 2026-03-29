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
