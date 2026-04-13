# Atlas VA - Code Review Findings

Based on the review of the project codebase against the original Project Proposal and Tasks list, here are the key issues and bugs identified:

## 1. Verify and Wake Bypass Hardcoding (Critical)
**Issue:** In `app.py`, the bypass logic for the `/api/verify` and `/api/wake` routes is hardcoded to expect specific text ("yes" and "hey atlas") from the frontend. This ignores the actual bypass logic implemented in the respective modules.
*   **`/api/verify`**: The frontend sends the user's input from the passcode field. The backend checks `if text.lower() == "yes":`, so the correct passcode (e.g., "atlas123") will always fail.
*   **`/api/wake`**: The backend checks `if text.lower() == "hey atlas":`. While this matches the wake word, it bypasses the module's own check.
**Fix:** Update `app.py` to pass the text input directly to `process_verify.bypass(text)` and `process_wakeword.bypass(text)`.

## 2. Missing `get_upcoming_movies` Implementation (Missing Feature)
**Issue:** The intent `get_upcoming_movies` is trained and has an NLG template, but it is not implemented in the Fulfillment module.
*   **`pipeline/utils/movie.py`**: Lacks an API call for TMDB's `/movie/upcoming` endpoint.
*   **`pipeline/fulfillment.py`**: The `process_movies` function does not handle the `get_upcoming_movies` intent. It falls through and returns an empty movie response.
**Fix:** Add `get_upcoming_movies()` to `MovieAPIModule` and handle the corresponding intent in `FulfillmentModule.process_movies()`.

## 3. Timer Duration Display Bug (Data Mismatch)
**Issue:** The frontend notes that the timer fulfillment returns raw seconds instead of a human-readable string (e.g., "Timer set for 300" instead of "5 minutes").
*   **Root Cause**: In `pipeline/fulfillment.py`, the timer result returns both `"duration"` (integer seconds) and `"duration_str"` (the original spoken string). However, in `pipeline/nlg.py`, `_template_set_timer` incorrectly fetches `"duration"` instead of `"duration_str"`.
**Fix:** In `pipeline/nlg.py`, change `duration = api_response.get("duration", "unknown")` to use `"duration_str"`.

## 4. Pet State Logic Discrepancies (Logic Bug)
**Issue:** The state changes in `pipeline/fulfillment.py` (`PetState`) do not fully match the design in the Project Proposal (Section 3.3).
*   **`wash_pet`**: Proposal states `Clean +30, Happy -10`. Code only implements `Clean +30`.
*   **`give_treat`**: Proposal states `Happy +15, Hunger +10`. Code implements `Happy +15` but `Hunger +5`.
**Fix:** Update the math in `PetState.apply()` to match the proposal's defined effects.

## 5. Missing Backend TTS Integration (Architecture)
**Issue:** Module 7 (Text-to-Speech) is defined in `TASKS.md` (Task 9) and a placeholder exists in `pipeline/tts.py` using `pyttsx3`. However, it is never called in the backend pipeline.
*   Currently, the system relies entirely on the frontend's browser-based `window.speechSynthesis`.
*   If the backend pipeline is tested independently of the frontend UI, it will not produce any audio output, which may violate the "full pipeline" requirement.
**Fix:** Integrate `TTSModule` from `pipeline/tts.py` into the `/api/pipeline` route in `app.py` or the `FulfillmentModule` (or a dedicated Orchestrator) to generate spoken audio on the server side if required.
