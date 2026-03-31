# Atlas VA — Task Board

> **Deadline:** Demo Apr 14 | Video Apr 17
> **How to use:** Pick any unclaimed task, write your name next to it. Work top-to-bottom within each phase. Tasks in the same phase can be done in parallel.

Legend: `[ ]` = open, `[A]`/`[B]`/`[C]` = claimed, `[x]` = done

---

## Phase 1: Training Data (START IMMEDIATELY — blocks Phase 2)

All training data uses **inline annotation** format from Activity 2:

```
"who is in Inception/B-TITLE"
"tell me the cast of The/B-TITLE Dark/I-TITLE Knight/I-TITLE"
```

Slot labels stay UPPERCASE. Each sentence on its own line in a Python list. Aim for **variety in phrasing** (not just swapping entity names). Include some sentences **without slots** where applicable (e.g., "feed the pet" with no food_type is valid).

**All training data goes in `data/intents/training_data.py`.** Each intent has a named list (e.g., `get_movie_cast_examples = [...]`). The `intent_map` dict at the bottom registers all intents. Run `python data/intents/training_data.py` to check progress.

### Basic intents — already in repo (152 sentences)

These 5 intents were adapted from Activity 2 and are **already filled in** `training_data.py`:

| Intent | Count | Status |
|--------|-------|--------|
| `greetings` | 30 | Done — copied as-is |
| `goodbye` | 30 | Done — copied as-is |
| `oos` | 50 | Done — Activity 2 (30) + abo supplement (20) |
| `set_timer` | 30 | Done — `/B-NAME` tags removed |
| `weather` | 32 | Done — `/B-DAY` `/I-DAY` tags removed |

No task needed for these — just review them if you want.

### Task 1: [x] Movie intents — batch A (done by abo)

~~Write training sentences for get_movie_cast, get_similar_movies, get_movie_plot (30 each).~~

Completed: 90 sentences integrated into `training_data.py`.

### Task 2: [x] Movie intents — batch B (done by abo)

~~Write training sentences for get_movies_by_genre, get_movie_rating, get_movie_director (25-30 each).~~

Completed: 90 sentences integrated into `training_data.py`. German genre names replaced with English equivalents.

### Task 3: [x] Movie intents — batch C + OOS supplement (done by abo)

~~Write training sentences for get_trending_movies, get_upcoming_movies, supplement OOS.~~

Completed: 23 + 20 + 20 = 63 sentences integrated into `training_data.py`.

### Task 4: [x] Pet intents — batch A (Frank + Fengshou + Claude)

~~Write training sentences for feed_pet, play_with_pet, pet_the_cat.~~

Completed: 34 + 25 + 20 = 79 sentences integrated into `training_data.py`.

### Task 5: [x] Pet intents — batch B (Claude)

~~Write training sentences for wash_pet, put_to_sleep, wake_up_pet.~~

Completed: 20 + 20 + 20 = 60 sentences integrated into `training_data.py`.

### Task 6: [x] Pet intents — batch C (Claude)

~~Write training sentences for give_treat, check_status, rename_pet.~~

Completed: 20 + 20 + 20 = 60 sentences integrated into `training_data.py`.

---

## Phase 2: ML Modules (can start once you have Activity code)

### Task 7: [Henry] User Verification module

Build the speaker verification module (Module 1).

- Extract MFCC features (20 coefficients) from audio using `librosa`
- Train a binary SVM classifier (`sklearn`): authorized (team voices) vs unauthorized (other students)
- Data augmentation: noise injection, pitch shifting, time stretching
- Data source: Activity 1 voice recordings
- Output: `models/user_verify_svm.pkl`
- Bypass: passcode input

**Deliverables:**
- `pipeline/user_verification.py` — module with `process(audio)` and `bypass(code)`
- `training/train_verification.py` — training script

### Task 8: [Henry] Wake Word Detection module

Build the wake word detection module (Module 2).

- Adapt Activity 1 CNN model for "Hey Atlas" detection
- Extract MFCC spectrogram features from audio
- Load pre-trained model weights from Activity 1
- Optional: collect more samples, apply data augmentation
- Bypass: type "Hey Atlas"

**Deliverables:**
- `pipeline/wake_word.py` — module with `process(audio)` and `bypass(text)`
- `training/train_wake_word.py` — training script (if retraining)
- `models/wake_word_cnn.pth` — model weights

### Task 9: [ ] ASR + TTS modules

Build the ASR module (Module 3) and TTS module (Module 7). Both are out-of-the-box.

**ASR:**
- Use `openai-whisper` package, `base` model, English only
- Input: audio numpy array or file path
- Output: transcribed text string
- Bypass: user types transcription manually

**TTS:**
- Use `pyttsx3` (offline) or `gTTS` (online)
- Input: text string
- Output: spoken audio
- No bypass needed (last step)

**Deliverables:**
- `pipeline/asr.py` — module with `process(audio)` and `bypass(text)`
- `pipeline/tts.py` — module with `process(text)`

---

## Phase 3: Core Logic (can partially overlap with Phase 2)

### Task 10: [ ] Intent Detection — BERT training

Fine-tune DistilBERT for joint intent classification + slot filling. **Depends on:** Tasks 1-6 (training data).

- Adapt Activity 2 notebook code into a standalone training script
- Reuse: `parse_example()`, `align_labels_with_tokens()`, training loop, eval
- Combine all 22 intent lists into one dataset, do train/test split (80/20)
- Train joint model, evaluate intent accuracy + slot F1
- Save model weights + label maps (intent list, slot label list)

**Deliverables:**
- `training/train_intent.py` — training script
- `models/intent_bert/model.pth` — trained weights
- `models/intent_bert/label_maps.json` — `{"intent_labels": [...], "slot_labels": [...]}`
- `pipeline/intent_detection.py` — module with `process(text)` returning `{"intent": str, "slots": dict}`

### Task 11: [ ] Fulfillment module

Build the fulfillment module (Module 5).

- TMDB API: search movie by title, get cast, similar, plot, genre discover, trending, rating, director, upcoming
- OpenWeatherMap API: query current weather by city name
- Pet state machine: `PetState` class with dict of attributes (hunger/happiness/energy/cleanliness, 0-100), `apply(intent, slots)` method
- Timer: parse duration string, return seconds
- Route all 22 intents to the correct handler
- Bypass: accept pre-canned JSON

**Deliverables:**
- `pipeline/fulfillment.py` — module with `process(intent_data)` and `bypass(json)`

### Task 12: [ ] NLG module — template + LLM

Build the answer generation module (Module 6) with BOTH approaches.

**Template-based:**
- Write response templates for all 22 intents
- Use `random.choice()` among 2-3 templates per intent for variety
- Pet intents: generate text describing state changes
- Must handle edge cases (missing data, API errors)

**LLM prompt-based:**
- Load a decoder-only model from HuggingFace (e.g., `distilgpt2`)
- Write prompts that include the JSON API response
- Generate natural language from the prompt
- Extract only the relevant sentence from LLM output

**Deliverables:**
- `pipeline/nlg.py` — module with `process(intent_data, api_response, method="template"|"llm")`

---

## Phase 4: Integration

### Task 13: [ ] Pipeline orchestrator + state machine

Wire all 7 modules into a sequential pipeline.

- System states: LOCKED → UNLOCKED → AWAKE → LISTENING → PROCESSING
- State transitions triggered by module outputs
- Central `PipelineOrchestrator` class that calls modules in order
- Error handling: if any module fails, offer bypass
- Awake timeout: return to sleep after N seconds of inactivity

**Deliverables:**
- `pipeline/orchestrator.py`
- `pipeline/__init__.py`

### Task 14: [ ] Flask backend — API routes + audio

Build the web server that connects frontend to pipeline.

- Routes: `/api/verify`, `/api/wake`, `/api/pipeline`, `/api/state`
- Accept audio uploads (WAV/WebM from browser MediaRecorder)
- Convert browser audio format to numpy array for modules
- Return JSON responses with pipeline results
- Serve frontend static files

**Deliverables:**
- `app.py` — Flask application
- `requirements.txt`
- `.env.example` — template for API keys

### Task 15: [ ] Frontend UI

Build the web interface.

- **Status bar:** show current system state (Locked/Unlocked/Awake/Processing)
- **Mic button:** record audio using browser MediaRecorder API
- **Bypass panel:** passcode input, "Hey Atlas" button, text input for ASR, intent dropdown
- **Pipeline progress:** visual indicator showing which module is running
- **NLG toggle:** switch between template and LLM output
- **Display areas:** weather result, movie results, timer countdown
- **Pet display:** character visual + 4 progress bars (hunger/happiness/energy/cleanliness)

**Deliverables:**
- `templates/index.html`
- `static/css/style.css`
- `static/js/main.js`

---

## Phase 5: Polish + Testing

### Task 16: [ ] Integration testing

Test the full end-to-end pipeline.

- Test each module individually first
- Test full pipeline: voice → verification → wake word → ASR → intent → fulfillment → NLG → TTS
- Test all bypasses work correctly
- Test at least 1 intent from each category (basic, movie, pet)
- Fix any bugs found

---

## Separate: Demo + Video (whole team, discuss together)

These are **not** individual tasks — plan and execute as a group.

**Demo (Apr 14):**
- 3-min in-class live demo
- Slides due night of Apr 13
- Script the demo flow, assign speaking parts
- Prepare bypass fallbacks in case of live failures

**Video Report (Apr 17):**
- 10-min video (12 min max), covers all 7 modules
- Each member presents their modules (~3.3 min each)
- Show NLG comparison: template vs LLM for same query
- Include architecture diagram

---

## Dependencies

```
Tasks 1-6 (training data)  ──→  Task 10 (BERT training)  ──→  Task 13 (orchestrator)
Tasks 7, 8, 9 (ML modules) ──→  Task 13 (orchestrator)    ──→  Task 16 (testing)
Task 11 (fulfillment)      ──→  Task 13 (orchestrator)
Task 12 (NLG)              ──→  Task 13 (orchestrator)
                                 Task 14 (backend)         ──→  Task 16 (testing)
                                 Task 15 (frontend)        ──→  Task 16 (testing)
```

**Critical path:** Tasks 1-6 → Task 10 → Task 13 → Task 16

---

## Suggested Assignment (just a suggestion — self-assign!)

| Person | Phase 1 (data) | Phase 2 (ML) | Phase 3 (core) | Phase 4 (integration) | Phase 5 |
|--------|----------------|--------------|----------------|----------------------|---------|
| A | Tasks 1, 4 | Task 7 | Task 10 | Task 13 | Task 16 |
| B | Tasks 2, 5 | Task 8 | Task 11 | Task 14 | — |
| C | Tasks 3, 6 | Task 9 | Task 12 | Task 15 | — |

16 individual tasks (not quite 3x but close). Demo + Video are whole-team efforts.
