# Speaker Verification — Current State & Domain Shift Investigation

> Living notes for Fengshou. Captures the problem, what we tried, what we learned,
> and what to do next. Doubles as raw material for the Step 3 video report's
> "Limitations & Error Analysis" section.

---

## TL;DR

- **On the iPhone-recorded training data**: every model version achieves ~100% F1.
- **On browser-recorded audio**: every version fails (confidence ~0.0–0.07, far below 0.5 threshold).
- **Root cause**: WebRTC's learned non-linear DSP (AGC / AEC / ANS) + Opus lossy codec
  creates a domain not covered by the training distribution. No amount of linear /
  synthetic augmentation reproduces it faithfully.
- **Real fix** = match enrollment device to demo device. Record 10 browser samples
  **on the MacBook that will be used for demo**, then retrain.
- **Quick win not yet tested**: disable WebRTC DSP via `getUserMedia` constraints
  (`noiseSuppression: false`, `autoGainControl: false`, `echoCancellation: false`).
  This could dramatically reduce the domain gap for free.

---

## 1. What's the problem?

The user verification module trains an SVM over MFCC features. Training data:
- `data/voices/authorized/`: ~12 iPhone-recorded m4a files (Fengshou, Laura, Tan).
- `data/voices/unauthorized/`: ~200 iPhone-recorded m4a files from the rest of the class.

The trained model works perfectly on held-out iPhone samples:
| Model | Authorized avg conf | Unauthorized avg conf |
|-------|---------------------|-----------------------|
| V1 (original) | 0.997 | < 0.01 |
| V5 | 1.000 | < 0.01 |

But when Fengshou records himself through the browser UI:
- V1/V5: confidence consistently **0.000**
- V7 (with real Opus codec simulation): confidence **0.001–0.067** — slightly non-zero
  but still nowhere near the 0.5 threshold.

## 2. Why does it fail? The "domain" gap

Training audio (iPhone Voice Memo):
```
voice → iPhone mic → light Apple DSP → AAC high-bitrate → m4a file
```

Browser audio (the deployed pipeline):
```
voice → laptop mic → Windows/macOS audio stack → WebRTC DSP (AGC + AEC + ANS)
      → Opus low-bitrate encode → WebM blob → decode → Web Audio resample 48k→16k
      → WAV buffer
```

The critical differences:
- **AGC** (Automatic Gain Control) — non-linear dynamic range compression
- **AEC** (Echo Cancellation) — removes assumed reverb components
- **ANS** (Automatic Noise Suppression) — **learning-based** (Google's RNNoise or
  equivalent). Makes hard decisions to zero out frequency bands it classifies as noise.
- **Opus** at ~48 kbps — psychoacoustic lossy codec, discards perceptually-masked
  frequencies
- Multiple resampling stages

MFCC's `mean` vector encodes *"average spectral shape"* — this is exactly what the
browser chain distorts most. SVM learns a decision boundary in iPhone-shaped MFCC
space; browser-shaped MFCC vectors land in unseen regions and get rejected.

This is **covariate shift** / **domain shift** in the textbook sense.

## 3. What we tried — V1 through V7

All versions save to `models/user_verify_svm_v{N}.pkl`. Select at runtime via
environment variable:
```bash
# PowerShell
$env:VERIFY_MODEL="user_verify_svm_v5.pkl"; python app.py

# cmd
set VERIFY_MODEL=user_verify_svm_v5.pkl && python app.py

# bash/macOS
VERIFY_MODEL=user_verify_svm_v5.pkl python app.py
```

### V1 — baseline (original by Henry)
- **Features**: `mean + std` of MFCC = 40 dims
- **Augmentations**: noise, pitch shift, time stretch, time shift, volume (5 per sample)
- **Training data result**: perfect
- **Browser result**: confidence = 0.000 consistently

### V2 — drop mean, add delta features (channel-invariant attempt)
- **Features**: `std + Δ-std + ΔΔ-std` = 60 dims. The mean MFCC carries channel info
  (microphone frequency response), so dropping it should help cross-channel generalization.
- **Result**: Training perfect. Browser now passes... **but for the wrong reason.**
- **Adversarial finding**: sustained vowel glides like 嗷呜 at a specific tempo
  pass verification. The model is now a **speech-rate detector**, not a speaker ID.
  Dropping mean lost timbre information, so the remaining `std` features just
  encode articulation dynamics.
- **Lesson**: feature engineering has unintended decision-boundary consequences.
  This is a *great* example for the video report.

### V3 — keep V1 features, add channel augmentations
- **Features**: same as V1
- **Augmentations added**: downsample+upsample, band-pass 300–4000 Hz, high-pass
  100 Hz, random EQ tilt
- **Result**: still fails on browser. Linear filters don't reproduce WebRTC's
  non-linear DSP.

### V4 — combine V2 features + V3 augmentations
- **Features**: V2 (60 dims, no mean)
- **Augmentations**: V3 set
- **Result**: inherits V2's rate-sensitivity issue; barely usable.

### V5 — "kitchen sink": full features + compound augmentation + class balancing
- **Features**: `mean + std + Δ-std + ΔΔ-std` = 80 dims (preserve timbre AND dynamics)
- **Augmentations**: V3 set + compound augmentations stacking 2-3 degradations
- **SVM**: `class_weight='balanced'` to correct 12:200 imbalance
- **Result**: training perfect; browser still fails.

### V6 — aggressive WebRTC-like non-linear degradation (pure Python)
- **New augmentations** (not in V3/V5):
  - `aug_compress`: `sign(y) * |y|**0.5` — simulates AGC compression
  - `aug_spectral_subtract`: estimate noise floor from quiet frames, subtract
    from magnitude spectrum — simulates ANS artifacts
  - `aug_specaugment`: zero out random frequency bands in STFT domain —
    simulates ANS making hard decisions
  - `aug_mulaw`: 8-bit μ-law quantization round-trip — simulates codec grain
  - `aug_opus_bandwidth`: band-limit 50–7000 Hz matching Opus wideband profile
  - Four compound chains stacking the above
- **Result**: still fails on browser.

### V7 — V6 + real Opus codec round-trip via ffmpeg
- **What's added**: actual `libopus` encode → decode via ffmpeg subprocess, at random
  bitrates 24/32/48/64 kbps. This is the *most faithful* simulation of the browser
  codec possible without actually running WebRTC.
- **Training time**: ~15–30 min (ffmpeg process per augmented sample)
- **Result**: browser confidence 0.001–0.067 — **measurably better than V5's 0.000**,
  but still far below 0.5 threshold.

## 4. Why even V7 can't close the gap

Here's the honest ceiling of what we attempted:

| Effect modeled | Linear filter? | Non-linear? | Learning-based? |
|----------------|----------------|-------------|-----------------|
| Opus codec | — | ✅ (V7 via libopus) | ✅ (V7) |
| AGC | — | ✅ (V6 compress) | — |
| Band-limiting | ✅ | — | — |
| ANS (real RNNoise) | — | **partial** (V6 spectral sub) | ❌ **cannot simulate** |

ANS is a trained neural network making per-frame decisions about what's noise.
Our `aug_spectral_subtract` and `aug_specaugment` are coarse static approximations.
This is likely why even V7's confidence stays near zero — the ANS-induced distortion
is specific enough that no static simulation lands in its distribution.

## 5. What actually works (not yet executed)

### 5a. Disable WebRTC DSP at source (zero-cost, untested)

`getUserMedia` supports constraints to disable DSP:

```javascript
navigator.mediaDevices.getUserMedia({
    audio: {
        echoCancellation: false,
        noiseSuppression: false,   // ← kills RNNoise
        autoGainControl: false,
    }
});
```

Both Chrome and Safari respect these. This would bypass the worst offenders
entirely; the audio reaching Flask would be much closer to iPhone training data.

**Action**: modify `static/js/main.js` (the three `setupMic(...)` calls) and
`static/record.html`'s `getUserMedia` to pass these constraints, then retest with
V1 or V5 model. Possibly no retraining needed.

### 5b. Target-domain enrollment (the right fix)

Record ~10 browser samples through the exact deployment combination:
- Same device (the MacBook that will demo)
- Same browser (Chrome, since Chrome's WebRTC behavior is the most tested)
- Same microphone (whatever will be used during demo — built-in or Yeti)

Then retrain V5. This is literally how Siri/Alexa work in production —
per-user-per-device enrollment.

**Tools already built**:
- `static/record.html` — browser-based enrollment page (name + record + auto-save
  to `data/voices/authorized/`)
- `app.py /api/collect_sample` — backend endpoint
- `training/test_verify.py` — can test any model version against any directory

Flow (5 minutes of real work):
1. `python app.py`
2. Open `http://localhost:5000/static/record.html`
3. Name: `fengshou`, Target: Authorized, Duration: 3s
4. Record 10 clips with varied content (different sentences, not all "hey atlas"):
   greetings, counting, weather queries, etc.
5. `python training/train_verification_v5.py`
6. `python training/test_verify.py user_verify_svm_v5.pkl` — the new
   `fengshou-browser-*.wav` files should all PASS with conf > 0.9
7. Restart Flask, test UI — should hit conf > 0.5 reliably

### 5c. Combined: 5a + 5b

Best of both: disable DSP constraints + record on deployment device. Minimal
domain shift left.

## 6. Hardware heterogeneity — the teammate problem

Concern raised: Tan uses AirPods Pro 2; Laura's setup unknown. If Fengshou's
browser samples train the model, will Tan/Laura still fail?

**Yes, they will fail**, and that's **correct behavior** for speaker verification:
- Speaker verification is fundamentally per-user
- Every deployment (Siri, Alexa Voice ID) requires per-user-per-device enrollment
- Model shouldn't accept arbitrary people — that's the whole point of verification

**Demo strategy**:
- Fengshou demos voice verification (passes, because he enrolled)
- Tan/Laura use text bypass (`atlas123`) with a professional explanation:

> *"Speaker verification in production systems (Siri, Alexa Voice ID) requires
> per-user-per-device enrollment because the speaker + microphone + front-end DSP
> triple constitutes a unique acoustic domain. Our experiments (V3–V7 including
> real libopus codec simulation) confirmed that this channel gap cannot be closed
> through synthetic augmentation alone. For the demo, we show Fengshou's enrolled
> path; each user would enroll on their own target device in production."*

This is a **strong** answer. It shows understanding, not weakness.

## 7. Decision: MacBook enrollment

Demo will be on MacBook Pro. Yeti on Windows ≠ MacBook mic. **Enroll on MacBook.**

Post-dinner checklist:
1. Sync project to MacBook (git clone or transfer)
2. Install deps in MacBook venv
3. Copy model weight files (`models/intent_bert/model.pth`, `user_verify_svm*.pkl`,
   wake word weights)
4. Fill `.env` with API keys
5. Confirm `python app.py` runs and UI is reachable
6. **First try 5a** (just edit `getUserMedia` constraints in main.js + record.html,
   then test with existing V5 model). Maybe no retraining needed.
7. If step 6 insufficient → record 10 browser samples on MacBook (Chrome) →
   `python training/train_verification_v5.py` → verify PASS in UI
8. Decide demo-day mic: built-in or Yeti. **Whichever you use for demo, use for
   enrollment too.** If deciding to use Yeti at demo, bring it, plug into MacBook,
   and re-record the 10 samples through it.

## 8. Files / locations

### Training scripts
- `training/train_verification.py` — V1 (original)
- `training/train_verification_v2.py` — delta features
- `training/train_verification_v3.py` — V1 features + channel augmentation
- `training/train_verification_v4.py` — V2 features + channel augmentation
- `training/train_verification_v5.py` — 80-dim features + compound aug + balanced SVM
- `training/train_verification_v6.py` — V5 + WebRTC-like non-linear degradation
- `training/train_verification_v7.py` — V6 + real ffmpeg Opus round-trip
- `training/test_verify.py` — evaluate any model against any directory

### Runtime
- `pipeline/user_verification.py` — dispatches feature extractor by model version
- `app.py /api/collect_sample` — save browser recordings to authorized/

### UI
- `static/record.html` — browser enrollment page
- `static/js/main.js` — main frontend (contains `setupMic` with `getUserMedia` calls
  that need DSP-disable constraints added)

### Data
- `data/voices/authorized/` — iPhone samples (12 files: 4 each for Fengshou/Laura/Tan)
- `data/voices/unauthorized/` — iPhone samples (~200 files from rest of class)
- `raw_recordings/` (in "CSI5180 Project Plan (Claude)" parent dir) — original
  Activity-1 m4a files; `training/import_team_recordings.py` can pull Fengshou/Tan
  near+other clips into authorized/ if we want more content diversity

### Model files (pickle format)
- `models/user_verify_svm.pkl` — currently V1 (or V5 if recent)
- `models/user_verify_svm_original.pkl` — backup of V1
- `models/user_verify_svm_v{2..7}.pkl` — each variant

## 9. For the video report

This whole journey is **the deliverable**. Professor explicitly wants:

> *"I am not so much interested in tables with machine learning results… I am
> more interested in analysis of examples. Make sure you include positive
> (success) examples and negative (failure) examples for EACH module and explain,
> provided how you created that module, why those positive/negative examples
> happen."*

We have textbook content:
- **Positive**: iPhone training set — confidence 1.0, model works perfectly
- **Negative 1**: browser recording fails at confidence 0.0
  - *Why*: WebRTC DSP + Opus domain shift, detailed above
- **Negative 2 (adversarial)**: in V2, 嗷呜 at a specific tempo passes verification
  - *Why*: dropping mean MFCC shifted decision boundary from timbre to prosody
  - **Great** for showing rigorous error analysis
- **Engineering effort**: V3→V4→V5→V6→V7 ablation progression, including real
  libopus simulation — shows systematic exploration of the solution space
- **Resolution**: target-domain enrollment, contextualized against production
  practice (Siri/Alexa voice ID)

Frame it as: *"We discovered that our clean-training setup generalized perfectly
in-distribution but exhibited significant covariate shift in deployment. We
systematically characterized the shift (V3–V7), identified its root cause
(non-linear learned DSP in WebRTC that linear augmentation cannot reproduce),
and resolved it via target-domain enrollment — the same strategy used by
production voice-ID systems."*

---

**Last updated**: 2026-04-12 evening, before dinner, right before switching to
MacBook for enrollment & demo prep.
