# Post-Demo Fixes — Atlas VA

Fixes implemented based on peer review feedback (4 reviewers).
Each fix corresponds to a git checkpoint commit.

## Completed

| CP | Fix | Files | Reviewer |
|----|-----|-------|----------|
| 1 | Pet stat natural decay (all 4 stats) + cap detection (refuse action at limit with friendly message) + awake-gated decay | fulfillment.py, nlg.py, app.py | D |
| 2 | Pet name validation — keyword regex on ASR transcript | fulfillment.py, nlg.py, app.py | A |
| 3 | Pet template mood reactions ("Doro looks really happy!") | nlg.py | D |
| 4 | check_status included in name validation | fulfillment.py | — |
| 5 | Two-layer name check: require pet name OR generic ref in transcript | fulfillment.py | — |
| 6 | Skip animation when action is refused | main.js | — |
| 7 | Catch wrong name after generic ref ("wash my pet feibi") | fulfillment.py | — |
| 8 | Movie runtime (extract from TMDB, show in rating/plot templates) | fulfillment.py, nlg.py | A |
| 9 | TTS prosody deltas increased for pyttsx3 | tts.py | A, D |
| 10 | Stop button (cancel recording / interrupt TTS) | index.html, style.css, main.js | — |
| 11 | ASR silence gate + domain prompt cleanup (remove "2012 or 1999") | asr.py | — |
| 12 | Weather: show country in response for disambiguation | nlg.py | A |
| 13 | UI: collapse debug panels, reduce visual density | style.css, index.html | A |

## Not Fixed (Documented Limitations)

| Issue | Why | Reviewer |
|-------|-----|----------|
| Voice verification only recognizes one member | Needs retraining with more voice samples + possible model switch (ECAPA-TDNN) | A, C, D |
| Wake word too sensitive ("lalala" triggers) | Needs synthetic data augmentation + threshold tuning | A, D |
| ASR "Petoro" (merges "Pet Doro") | Whisper word-boundary error on proper nouns — no code-level fix | — |
| TTS emotion hard-coded per intent, not detected from text | By design — intent→emotion mapping is deterministic and reliable. Dynamic sentiment analysis on one-sentence outputs would add complexity for minimal gain at this scale. | D |
| Weather country disambiguation ("London" = UK or Canada?) | OpenWeatherMap geocoding returns the top match. Full disambiguation would need a follow-up question flow (multi-turn) which is out of scope for the current single-turn pipeline. The country field is now shown when available. | A |

## Assumptions

- SILENCE_RMS_THRESHOLD = 0.01 for ASR silence gate. May need tuning per environment.
- Pet stat decay rates (DECAY_PER_SEC) are tuned for demo visibility, not realism.
- Cap thresholds (>= 95 for max, <= 5 for min) chosen to prevent decay-induced bypass at exactly 100.
- _first_sentence abbreviation list covers common English titles; may miss rare ones.
- Pet name regex won't catch names embedded inside other words (e.g., ASR merging "Pet Doro" → "Petoro").
