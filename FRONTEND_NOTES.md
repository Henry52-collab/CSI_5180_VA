# Frontend Notes — Assumptions & Known Issues

Written by Claude during Task 15 implementation. Review with Fengshou.

## Assumptions Made

1. **Audio format**: Browser MediaRecorder produces WebM blobs. Backend currently uses
   `soundfile.SoundFile()` and `librosa.load()` which may NOT support WebM natively.
   **Bypass (text input) always works** regardless. For audio recording to work, either:
   - Install `pydub` + `ffmpeg` on the backend to convert WebM → WAV before processing, or
   - Use a JS library to record in WAV format (e.g., `lamejs` or `recorderjs`).

2. **Push-to-hold mic**: Mousedown starts recording, mouseup stops and sends. This is
   simpler than toggle mode. Mobile support via touchstart/touchend.

3. **TTS is server-side**: `pyttsx3` plays audio through server speakers, not the browser.
   The frontend does NOT play audio back. For the demo this is fine if presenting from
   the machine running the server. For a real product, we'd use Web Speech API or
   send audio bytes back to the browser.

4. **State gating is visual only**: All three panels (verify/wake/pipeline) are shown/hidden
   based on state, but the backend doesn't enforce ordering. In theory you could POST to
   /api/pipeline without verifying first. For the demo this is fine.

5. **NLG toggle**: The dropdown switches between "template" and "llm". The LLM option uses
   distilgpt2 which will be slow on first call (model download + load). Template is instant.

6. **No /api/state polling during locked/unlocked**: We only poll pet state every 3s while
   in the "awake" state. This avoids unnecessary requests.

## Known Issues

1. **Timer NLG shows seconds, not human-readable**: `process_timer()` returns
   `{"duration": 300}` and NLG shows "Timer set for 300." Should show "5 minutes".
   Fix: either format in fulfillment or in NLG template.

2. **Movie queries need API keys**: Without TMDB_API_KEY in .env, movie fulfillment
   returns errors. The UI doesn't have special error handling for missing API keys.

3. **No conversation reset**: There's no "restart" or "lock" button to go back to the
   beginning. For the demo, just refresh the page.

4. **Chat log doesn't persist**: Refreshing clears all conversation history.

5. **WebM audio**: See assumption 1. This is the biggest risk for the live demo.
   Recommendation: use text bypass for the demo, mention mic as "also supported."

## Design Decisions

- **Dark theme**: Looks professional for demo, reduces eye strain.
- **3-panel flow**: Verify → Wake → Pipeline. Each panel shows only when relevant.
- **Pet panel always visible** in pipeline view so the audience can see stats change live.
- **Details/JSON toggle**: Click "Details" to see raw API response. Hidden by default
  to keep the UI clean during demo.
- **Conversation log**: Bottom panel showing user/assistant exchanges.

## Files

- `static/index.html` — main page structure
- `static/css/style.css` — all styles (no framework, pure CSS)
- `static/js/main.js` — all logic (vanilla JS, no framework)

## What's NOT implemented

- Timer countdown display (just shows the NLG text response)
- Pet animation/sprites (just emoji + stat bars)
- Audio playback in browser (TTS plays on server)
- Weather/movie display cards (just shows NLG text response)
