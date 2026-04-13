# Day Plan — 2026-04-13 (Monday, day before demo)

> Hard deadline: **23:59 tonight** — submit presentation PDF to Brightspace.
> Missing it = automatic 0 / 15% presentation grade.

---

## Today's Priorities

| P | Task | Deadline | Cost of failure |
|---|------|----------|-----------------|
| **P0** | Submit presentation PDF to Brightspace | **23:59** | **0 / 15%** |
| **P0** | MacBook demo works end-to-end (even with bypass) | 22:00 | Demo crashes on stage |
| **P1** | Voice verify passes on MacBook for Fengshou | 14:00 | Fall back to text bypass (acceptable) |
| **P1** | Tan + Laura have speaking scripts | 18:00 | Messy rehearsal at 6 PM |

---

## 🌅 Morning → 12:00 (Move to MacBook + Fix Verify)

| Time | Task |
|------|------|
| 07:30–08:00 | Breakfast + coffee + re-read `VERIFICATION_NOTES.md` §5 and §7 |
| 08:00–08:45 | **Move project to MacBook**: git push from Windows → MacBook git pull (or USB/cloud). Copy all weight files in `models/`. Fill `.env` with API keys. |
| 08:45–09:15 | **Install deps on MacBook**: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`. Install Chrome if missing. |
| 09:15–09:30 | **Smoke test**: `python app.py`, open `http://localhost:5000`. UI, intent bypass, timer, Doro all functional. |
| 09:30–09:45 | **Attempt 1: getUserMedia DSP constraints** (zero-cost fix from VERIFICATION_NOTES §5a): add `{ echoCancellation: false, noiseSuppression: false, autoGainControl: false }` to every `navigator.mediaDevices.getUserMedia()` call in `static/js/main.js` (`setupMic`) and `static/record.html`. Restart Flask. |
| 09:45–10:00 | **Test V5 with DSP disabled**: if browser recording confidence > 0.5 → done, skip to 10:30. |
| 10:00–10:30 | **Attempt 2 (if needed): record 10 browser samples** via `record.html`, retrain `python training/train_verification_v5.py`. |
| 10:30–10:45 | Verify main UI login passes with conf > 0.5 stably. |
| 10:45–12:00 | **Presentation skeleton**: open PowerPoint/Keynote, create 8 slide titles (see slide structure below). |

**12:00 Checkpoint**:
- ✅ Flask runs on MacBook
- ✅ Voice verify either works or bypass script is ready
- ✅ PPT has outline + all slide titles

---

## 🌤️ 12:00 → 18:00 (PPT + Rehearsal Prep)

| Time | Task |
|------|------|
| 12:00–13:00 | Lunch. Meanwhile, message **Tan and Laura** via Discord: confirm demo runs on MacBook, confirm speaking part assignments (see below). |
| 13:00–15:00 | **Fill PPT content** (8 slides): 1 title sentence + 3 bullets + key screenshot per slide. **Don't dump text.** Finish all content. |
| 15:00–15:30 | **Draw architecture diagram** (slide 3): 7-module pipeline. Excalidraw or PowerPoint shapes — keep it simple. |
| 15:30–16:30 | **Read-through #1**: time yourself. **Target 3–4 min** (over 4 min = cut off). Trim excess. |
| 16:30–17:00 | **Demo end-to-end smoke test**: walk through full flow: verify → wake → "what's the weather in Ottawa" → "feed the pet fish" → "set timer for 30 seconds". Note all glitches. |
| 17:00–18:00 | Fix smoke-test bugs. Send talking points to Tan & Laura (~1 min each, 3 people total ≈ 3-4 min). |

**18:00 Checkpoint**:
- ✅ All 8 PPT slides complete
- ✅ Self read-through ≤ 4 minutes
- ✅ Demo walks cleanly end-to-end
- ✅ Tan/Laura have their scripts

---

## 🌙 18:00 → 23:00 (Polish + Submit)

| Time | Task |
|------|------|
| 18:00–19:00 | Dinner. **DO NOT nap.** ⚠️ |
| 19:00–20:00 | **PPT polish**: unify fonts/sizes, trim redundant text, align images. |
| 20:00–21:00 | **Full rehearsal ×2**: present live against PPT. Each run timed, target 3:30 to leave margin. |
| 21:00–21:30 | **Final demo smoke test**: walk through full flow one more time on MacBook. **No code changes after this point.** |
| 21:30–22:00 | **Push project to GitHub** (code submission uses this). Upload model.pth to GitHub Release. |
| 22:00–22:30 | **Export PPT to PDF**. Filename per instructor convention (e.g. `Group18-Presentation.pdf`). |
| 22:30–23:00 | **Submit PDF on Brightspace**. Screenshot submission receipt. |
| 23:00–23:30 | Buffer for slippage earlier in day. |
| 23:30 | **Bed.** Demo is tomorrow 2:30 PM — need to be sharp. |

**23:00 Hard Checkpoint**:
- ✅ **PDF submitted to Brightspace** (screenshot for proof)
- ✅ Demo runs end-to-end on MacBook
- ✅ Code pushed to GitHub latest
- ✅ All 3 members know their speaking parts

---

## 📄 Slide Structure (8 slides, 3–4 minutes)

Per the presentation PDF requirements:

| # | Slide | Speaker | Time |
|---|-------|---------|------|
| 1 | Title: Atlas VA · Group 18 · Fengshou / Tan / Laura | Fengshou | 20s |
| 2 | Overview: Virtual pet Doro + movie assistant + basics (weather/timer/greetings) | Fengshou | 30s |
| 3 | Architecture diagram (7-module pipeline) | Tan | 30s |
| 4 | UI screenshots + 3-column layout explanation | Tan | 30s |
| 5 | Intent/Fulfillment example 1: Specialized Domain (Movies: `get_movie_cast`) | Laura | 40s |
| 6 | Intent/Fulfillment example 2: Interactive Control (Doro pet: `feed` → animation + stats bars) | Laura | 40s |
| 7 | Intent/Fulfillment example 3: Basics (timer auto-triggers countdown from NLG result) | Fengshou | 30s |
| 8 | Conclusion: what works well, known limitations (verify channel shift) | Fengshou | 20s |

3 speakers × ~1 minute each = satisfies "ALL members talk" requirement.

---

## ⚠️ Fallback Scripts

**If verify still broken by afternoon**: switch to bypass `atlas123` for demo. In the talk, 10-second framing:

> *"For voice verification, our MFCC+SVM system shows strong in-distribution
> performance but suffers domain shift when the microphone chain changes —
> production systems like Siri solve this with per-device enrollment. For today's
> demo we use the bypass path; the technical video report details our full
> ablation study (V1–V7 including real Opus codec simulation)."*

This is **stronger** than "it doesn't work." Shows understanding.

**If MacBook setup has issues** at 09:30: fall back to Windows + Yeti. Recording was validated here. Demo works even if the hardware isn't ideal.

---

## 🔗 Dependencies / Inputs Needed From Team

- **Tan**: confirm which parts he's handling, his talking points
- **Laura**: same. Her architecture diagram from Discord (the sketch) is a good starting point but needs edits (see below)
- **Laura's diagram edits** (per our chat earlier): TTS is client-side (frontend `window.speechSynthesis`), no `PipelineOrchestrator`, add OpenWeatherMap API, add Doro pet in interactive control. File-path bug already fixed in latest.

---

**Last updated**: 2026-04-13 morning, pre-MacBook move.
