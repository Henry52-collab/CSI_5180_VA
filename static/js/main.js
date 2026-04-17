/*
 * Atlas VA — Frontend Logic
 *
 * ASSUMPTIONS (to verify with team):
 *   1. Audio recording uses MediaRecorder → produces WebM blobs.
 *      Backend uses librosa/soundfile which may not support WebM natively.
 *      Bypass (text input) always works as fallback.
 *   2. Push-to-hold mic: mousedown starts, mouseup stops & sends.
 *   3. TTS runs server-side (pyttsx3) — no audio playback in browser.
 *   4. /api/state is polled every 3s while pipeline panel is active.
 *   5. We do NOT enforce state gating (user can bypass any step).
 *      In a real product you'd disable panels until prior step passes.
 *
 * KNOWN ISSUES:
 *   - WebM audio format may fail on backend (see assumption 1).
 *     Fix: add pydub/ffmpeg conversion on backend, or use WAV recording.
 *   - Timer fulfillment returns seconds (e.g. 300) not a human string.
 *     NLG shows "Timer set for 300" instead of "Timer set for 5 minutes".
 */

// ============================================================================
// State
// ============================================================================

const API = "";  // same origin

let systemState = "locked";   // locked | unlocked | awake | processing
let mediaRecorder = null;
let audioChunks = [];
let statePoller = null;

// ============================================================================
// DOM refs
// ============================================================================

const $statusBadge  = document.getElementById("status-badge");
const $panelVerify  = document.getElementById("panel-verify");
const $panelWake    = document.getElementById("panel-wake");
const $panelPipeline = document.getElementById("panel-pipeline");

// Verify
const $btnVerifyMic    = document.getElementById("btn-verify-mic");
const $inputVerify     = document.getElementById("input-verify");
const $btnVerifyBypass = document.getElementById("btn-verify-bypass");
const $verifyResult    = document.getElementById("verify-result");

// Wake
const $btnWakeMic    = document.getElementById("btn-wake-mic");
const $inputWake     = document.getElementById("input-wake");
const $btnWakeBypass = document.getElementById("btn-wake-bypass");
const $wakeResult    = document.getElementById("wake-result");

// Pipeline
const $btnPipelineMic    = document.getElementById("btn-pipeline-mic");
const $inputPipeline     = document.getElementById("input-pipeline");
const $btnPipelineBypass = document.getElementById("btn-pipeline-bypass");
const $nlgMethod         = document.getElementById("nlg-method");
const $ttsBackend        = document.getElementById("tts-backend");
const $responseAnswer    = document.getElementById("response-answer");
const $responseJson      = document.getElementById("response-json");
const $pipelineResponse  = document.getElementById("pipeline-response");

// Pet
const $petName = document.getElementById("pet-name");
const bars = {
    hunger:      { fill: document.getElementById("bar-hunger"),      val: document.getElementById("val-hunger") },
    happiness:   { fill: document.getElementById("bar-happiness"),   val: document.getElementById("val-happiness") },
    energy:      { fill: document.getElementById("bar-energy"),      val: document.getElementById("val-energy") },
    cleanliness: { fill: document.getElementById("bar-cleanliness"), val: document.getElementById("val-cleanliness") },
};

// Chat
const $chatMessages = document.getElementById("chat-messages");

// Pipeline progress steps
const $progressSteps = document.querySelectorAll("#pipeline-progress .step");


// ============================================================================
// State management
// ============================================================================

function setSystemState(state) {
    systemState = state;

    $statusBadge.textContent = state.toUpperCase();
    $statusBadge.className = state;

    $panelVerify.classList.toggle("active", state === "locked");
    $panelWake.classList.toggle("active", state === "unlocked");
    $panelPipeline.classList.toggle("active", state === "awake" || state === "processing");

    if (state === "awake" && !statePoller) {
        statePoller = setInterval(pollState, 3000);
    }
    if (state === "locked" || state === "unlocked") {
        if (statePoller) { clearInterval(statePoller); statePoller = null; }
    }
}


// ============================================================================
// API helpers
// ============================================================================

async function apiPost(url, formData) {
    try {
        const resp = await fetch(API + url, { method: "POST", body: formData });
        return await resp.json();
    } catch (e) {
        return { success: false, data: { error: e.message } };
    }
}

async function apiGet(url) {
    try {
        const resp = await fetch(API + url);
        return await resp.json();
    } catch (e) {
        return null;
    }
}


// ============================================================================
// Verify
// ============================================================================

$btnVerifyBypass.addEventListener("click", async () => {
    const text = $inputVerify.value.trim();
    if (!text) return;

    const fd = new FormData();
    fd.append("text", text);

    $verifyResult.innerHTML = '<span class="text-muted">Verifying...</span>';
    const result = await apiPost("/api/verify", fd);

    if (result.success) {
        $verifyResult.innerHTML = '<span class="success">Verified!</span>';
        setSystemState("unlocked");
    } else {
        $verifyResult.innerHTML = '<span class="error">Verification failed. Try again.</span>';
    }
});

$inputVerify.addEventListener("keydown", (e) => {
    if (e.key === "Enter") $btnVerifyBypass.click();
});


// ============================================================================
// Wake
// ============================================================================

$btnWakeBypass.addEventListener("click", async () => {
    const text = $inputWake.value.trim();
    if (!text) return;

    const fd = new FormData();
    fd.append("text", text);

    $wakeResult.innerHTML = '<span class="text-muted">Waking...</span>';
    const result = await apiPost("/api/wake", fd);

    if (result.success) {
        $wakeResult.innerHTML = '<span class="success">Atlas is awake!</span>';
        setSystemState("awake");
    } else {
        $wakeResult.innerHTML = '<span class="error">Wake word not detected. Try typing "Hey Atlas".</span>';
    }
});

$inputWake.addEventListener("keydown", (e) => {
    if (e.key === "Enter") $btnWakeBypass.click();
});


// ============================================================================
// Pipeline
// ============================================================================

async function sendPipeline(formData) {
    formData.append("nlg_method", $nlgMethod.value);
    formData.append("tts_backend", $ttsBackend ? $ttsBackend.value : "pyttsx3");

    setSystemState("processing");
    setPipelineProgress("asr");

    const result = await apiPost("/api/pipeline", formData);

    if (result.success && result.data) {
        const d = result.data;

        setPipelineProgress("done");

        // Show answer
        $responseAnswer.textContent = d.answer || "(no answer)";
        $responseJson.textContent = JSON.stringify(d, null, 2);
        $pipelineResponse.style.display = "block";

        // Chat log
        if (d.transcript) addChat("user", d.transcript);
        if (d.answer) addChat("assistant", d.answer);

        // TTS — play backend-generated audio with emotion-driven prosody, or
        // fall back to browser Web Speech API if backend TTS failed.
        playAnswer(d);

        // Update pet if relevant
        if (d.fulfillment && d.fulfillment.type === "pet") {
            updatePet(d.fulfillment);
        }

        // Auto-start timer if set_timer intent
        if (d.fulfillment && d.fulfillment.type === "timer" && d.fulfillment.duration > 0) {
            timerStart(d.fulfillment.duration);
        }

        // Also poll state to catch any pet changes
        await pollState();
    } else {
        const errMsg = result.data?.error || "Pipeline failed";
        $responseAnswer.textContent = "";
        $responseJson.textContent = errMsg;
        $pipelineResponse.style.display = "block";
    }

    setSystemState("awake");
}

// Text bypass
$btnPipelineBypass.addEventListener("click", async () => {
    const text = $inputPipeline.value.trim();
    if (!text) return;

    const fd = new FormData();
    fd.append("text", text);

    $inputPipeline.value = "";
    await sendPipeline(fd);
});

$inputPipeline.addEventListener("keydown", (e) => {
    if (e.key === "Enter") $btnPipelineBypass.click();
});


// ============================================================================
// Intent/Slot Bypass
// ============================================================================

const GENRES = [
    "Action", "Adventure", "Animation", "Comedy", "Crime",
    "Documentary", "Drama", "Fantasy", "Horror", "Mystery",
    "Romance", "Science Fiction", "Thriller"
];

const $bypassIntent = document.getElementById("bypass-intent");
const $bypassSlots = document.getElementById("bypass-slots");
const $btnBypassSubmit = document.getElementById("btn-bypass-submit");

const SLOT_CONFIG = {
    get_movie_cast:    [{id: "title", placeholder: "Movie title (e.g. Inception)"}],
    get_similar_movies:[{id: "title", placeholder: "Movie title"}],
    get_movie_plot:    [{id: "title", placeholder: "Movie title"}],
    get_movie_rating:  [{id: "title", placeholder: "Movie title"}],
    get_movie_director:[{id: "title", placeholder: "Movie title"}],
    get_movies_by_genre:[{id: "genre", type: "select", options: GENRES}],
    get_trending_movies:[{id: "time_window", type: "select", options: ["day", "week"]}],
    weather:           [{id: "city", placeholder: "City name (e.g. Ottawa)"}],
    set_timer:         [{id: "duration", placeholder: "Duration (e.g. 5 minutes)"}],
    feed_pet:          [{id: "food_type", placeholder: "Food (e.g. fish)", optional: true}],
    play_with_pet:     [{id: "toy", placeholder: "Toy (e.g. ball)", optional: true}],
    give_treat:        [{id: "treat_type", placeholder: "Treat (e.g. cookie)", optional: true}],
    rename_pet:        [{id: "name", placeholder: "New name"}],
};

function renderBypassSlots() {
    const intent = $bypassIntent.value;
    const config = SLOT_CONFIG[intent];
    if (!config) {
        $bypassSlots.innerHTML = "";
        return;
    }
    $bypassSlots.innerHTML = config.map(slot => {
        if (slot.type === "select") {
            const opts = slot.options.map(o =>
                `<option value="${o.toLowerCase()}">${o}</option>`
            ).join("");
            return `<div class="bypass-row"><label>${slot.id}:</label><select id="bypass-slot-${slot.id}">${opts}</select></div>`;
        }
        return `<div class="bypass-row"><label>${slot.id}:</label><input type="text" id="bypass-slot-${slot.id}" placeholder="${slot.placeholder || ""}" /></div>`;
    }).join("");
}

$bypassIntent.addEventListener("change", renderBypassSlots);
renderBypassSlots();

$btnBypassSubmit.addEventListener("click", async () => {
    const intent = $bypassIntent.value;
    const config = SLOT_CONFIG[intent] || [];
    const slots = {};
    for (const slot of config) {
        const el = document.getElementById(`bypass-slot-${slot.id}`);
        if (el && el.value.trim()) {
            slots[slot.id] = el.value.trim().toLowerCase();
        }
    }

    const fd = new FormData();
    fd.append("intent", intent);
    fd.append("slots", JSON.stringify(slots));
    fd.append("nlg_method", $nlgMethod.value);
    fd.append("tts_backend", $ttsBackend ? $ttsBackend.value : "pyttsx3");

    setSystemState("processing");
    setPipelineProgress("done");

    const result = await apiPost("/api/pipeline", fd);

    if (result.success && result.data) {
        const d = result.data;
        $responseAnswer.textContent = d.answer || "(no answer)";
        $responseJson.textContent = JSON.stringify(d, null, 2);
        $pipelineResponse.style.display = "block";

        addChat("user", `[${intent}] ${JSON.stringify(slots)}`);
        if (d.answer) addChat("assistant", d.answer);
        playAnswer(d);

        if (d.fulfillment && d.fulfillment.type === "pet") {
            updatePet(d.fulfillment);
        }
        await pollState();
    }

    setSystemState("awake");
});


// ============================================================================
// Pipeline progress indicator
// ============================================================================

function setPipelineProgress(activeStep) {
    const order = ["asr", "intent", "fulfillment", "nlg"];
    const activeIdx = activeStep === "done" ? order.length : order.indexOf(activeStep);

    $progressSteps.forEach((el) => {
        const stepName = el.dataset.step;
        const idx = order.indexOf(stepName);
        el.classList.remove("active", "done");
        if (idx < activeIdx) el.classList.add("done");
        else if (idx === activeIdx) el.classList.add("active");
    });
}

function clearPipelineProgress() {
    $progressSteps.forEach((el) => el.classList.remove("active", "done"));
}


// ============================================================================
// Pet display
// ============================================================================

function barColor(v) {
    if (v >= 60) return "#4ade80";
    if (v >= 30) return "#fbbf24";
    return "#f87171";
}

// Map pipeline intent names to demo animation names
const INTENT_TO_ANIM = {
    feed_pet: "feed", play_with_pet: "play", pet_the_cat: "pet_cat",
    wash_pet: "wash", put_to_sleep: "sleep", wake_up_pet: "wake",
    give_treat: "treat", check_status: "status", rename_pet: "rename",
};

function updatePet(petData) {
    const status = petData.status || petData.after || petData;
    if (status.name) $petName.textContent = status.name;

    for (const [key, refs] of Object.entries(bars)) {
        const val = status[key];
        if (val !== undefined) {
            refs.fill.style.width = val + "%";
            // colour is handled by CSS gradient classes (.hunger-fill etc.)
            refs.val.textContent = val;
        }
    }

    // Trigger 3D animation only if the action actually succeeded
    const action = petData.action;
    if (action && !petData.error && !petData.cap_warning
        && typeof window.doroPlayAnimation === "function") {
        const animName = INTENT_TO_ANIM[action] || action;
        window.doroPlayAnimation(animName);
    }
}

async function pollState() {
    const state = await apiGet("/api/state");
    if (state && state.pet) {
        updatePet(state.pet);
    }
}


// ============================================================================
// TTS — prefer backend-generated audio (emotion-aware prosody), fall back to
// browser Web Speech API if the backend failed.
// ============================================================================

function playAnswer(d) {
    if (!d || !d.answer) return;

    // Cancel any in-flight speech so we don't overlap
    if (window.speechSynthesis) window.speechSynthesis.cancel();

    if (d.audio_b64) {
        const mime = d.audio_mime || "audio/mpeg";
        const audio = new Audio(`data:${mime};base64,${d.audio_b64}`);
        audio.play().catch((err) => {
            console.warn("Backend audio playback failed, falling back to browser TTS:", err);
            speak(d.answer);
        });
    } else {
        if (d.tts_error) console.warn("Backend TTS error:", d.tts_error);
        speak(d.answer);
    }
}

function speak(text) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
}


// ============================================================================
// Chat log
// ============================================================================

function addChat(role, text) {
    // Remove placeholder on first real message
    const placeholder = $chatMessages.querySelector(".chat-placeholder");
    if (placeholder) placeholder.remove();

    const div = document.createElement("div");
    div.className = "chat-msg " + role;
    div.textContent = (role === "user" ? "You: " : "Atlas: ") + text;
    $chatMessages.appendChild(div);
    $chatMessages.scrollTop = $chatMessages.scrollHeight;
}


// ============================================================================
// WebM → WAV conversion (so backend doesn't need ffmpeg)
// ============================================================================

async function blobToWav(blob) {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const arrayBuf = await blob.arrayBuffer();
    const decoded = await audioCtx.decodeAudioData(arrayBuf);
    audioCtx.close();

    const sampleRate = 16000;
    const numChannels = 1;

    // Resample to 16kHz mono (what Whisper/librosa expects)
    const offlineCtx = new OfflineAudioContext(numChannels, decoded.duration * sampleRate, sampleRate);
    const source = offlineCtx.createBufferSource();
    source.buffer = decoded;
    source.connect(offlineCtx.destination);
    source.start();
    const resampled = await offlineCtx.startRendering();
    const pcm = resampled.getChannelData(0);

    // Encode as WAV
    const wavBuf = new ArrayBuffer(44 + pcm.length * 2);
    const view = new DataView(wavBuf);
    const writeStr = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };

    writeStr(0, "RIFF");
    view.setUint32(4, 36 + pcm.length * 2, true);
    writeStr(8, "WAVE");
    writeStr(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);             // PCM
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numChannels * 2, true);
    view.setUint16(32, numChannels * 2, true);
    view.setUint16(34, 16, true);            // 16-bit
    writeStr(36, "data");
    view.setUint32(40, pcm.length * 2, true);

    for (let i = 0; i < pcm.length; i++) {
        const s = Math.max(-1, Math.min(1, pcm[i]));
        view.setInt16(44 + i * 2, s * 0x7FFF, true);
    }

    return new Blob([wavBuf], { type: "audio/wav" });
}


// ============================================================================
// Mic recording (click to start, click again to stop)
// ============================================================================

function setupMic(button, sendCallback) {
    let recorder = null;
    let chunks = [];
    let stream = null;

    const label = button.querySelector(".mic-label");

    button.addEventListener("click", async () => {
        if (recorder && recorder.state === "recording") {
            recorder.stop();
            button.classList.remove("recording");
            if (label) label.textContent = "Click to Record";
            return;
        }

        try {
            // Disable WebRTC DSP — it aggressively compresses quiet speech and
            // erases spectral detail (learning-based noise suppression), which
            // tanks both ASR accuracy and speaker-verification confidence.
            stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false,
                }
            });
            chunks = [];
            recorder = new MediaRecorder(stream);
            recorder.ondataavailable = (ev) => chunks.push(ev.data);
            recorder.onstop = async () => {
                stream.getTracks().forEach((t) => t.stop());
                const webmBlob = new Blob(chunks, { type: recorder.mimeType });
                const wavBlob = await blobToWav(webmBlob);
                sendCallback(wavBlob);
                recorder = null;
            };
            recorder.start();
            button.classList.add("recording");
            if (label) label.textContent = "Click to Send";
        } catch (err) {
            console.error("Mic access denied:", err);
        }
    });
}

// Wire up mic buttons
setupMic($btnVerifyMic, async (blob) => {
    const fd = new FormData();
    fd.append("file", blob, "recording.wav");
    $verifyResult.innerHTML = '<span class="text-muted">Verifying...</span>';
    const result = await apiPost("/api/verify", fd);
    const conf = result.data?.confidence;
    const confStr = conf !== undefined ? ` (confidence: ${(conf * 100).toFixed(1)}%)` : "";
    if (result.success) {
        $verifyResult.innerHTML = '<span class="success">Verified!</span>';
        setSystemState("unlocked");
    } else {
        // $verifyResult.innerHTML = '<span class="error">Verification failed.</span>';
        $verifyResult.innerHTML = `<span class="error">Verification failed.${confStr} Threshold: 50%</span>`;
    }
});

setupMic($btnWakeMic, async (blob) => {
    const fd = new FormData();
    fd.append("file", blob, "recording.wav");
    $wakeResult.innerHTML = '<span class="text-muted">Listening...</span>';
    const result = await apiPost("/api/wake", fd);
    if (result.success) {
        $wakeResult.innerHTML = '<span class="success">Atlas is awake!</span>';
        setSystemState("awake");
    } else {
        $wakeResult.innerHTML = '<span class="error">Wake word not detected.</span>';
    }
});

setupMic($btnPipelineMic, async (blob) => {
    const fd = new FormData();
    fd.append("file", blob, "recording.wav");
    await sendPipeline(fd);
});


// ============================================================================
// Timer
// ============================================================================

let timerInterval = null;
let timerRemaining = 5;
let timerRunning = false;

const $timerDisplay = document.getElementById("timer-display");
const $timerMin = document.getElementById("timer-min");
const $timerSec = document.getElementById("timer-sec");

function timerFormat(secs) {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
}

function timerUpdateDisplay() {
    $timerDisplay.textContent = timerFormat(timerRemaining);
    $timerDisplay.className = "";
    if (timerRunning && timerRemaining <= 10 && timerRemaining > 0) {
        $timerDisplay.className = "urgent";
    }
}

function timerStart(seconds) {
    if (seconds !== undefined) {
        timerRemaining = seconds;
    } else if (!timerRunning && timerRemaining <= 0) {
        const mins = parseInt($timerMin.value) || 0;
        const secs = parseInt($timerSec.value) || 0;
        timerRemaining = mins * 60 + secs;
    }
    if (timerRemaining <= 0) return;
    if (timerRunning) return;

    timerRunning = true;
    timerUpdateDisplay();

    timerInterval = setInterval(() => {
        timerRemaining--;
        timerUpdateDisplay();
        if (timerRemaining <= 0) {
            clearInterval(timerInterval);
            timerRunning = false;
            $timerDisplay.textContent = "00:00";
            $timerDisplay.className = "done";
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.type = "sine";
                osc.frequency.value = 880;
                gain.gain.setValueAtTime(0.3, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);
                osc.start(ctx.currentTime);
                osc.stop(ctx.currentTime + 0.8);
            } catch (e) {}
            speak("Timer is done!");
        }
    }, 1000);
}

function timerPause() {
    if (!timerRunning) return;
    clearInterval(timerInterval);
    timerRunning = false;
}

function timerReset() {
    clearInterval(timerInterval);
    timerRunning = false;
    const mins = parseInt($timerMin.value) || 0;
    const secs = parseInt($timerSec.value) || 0;
    timerRemaining = mins * 60 + secs;
    $timerDisplay.className = "";
    timerUpdateDisplay();
}

function syncTimerInputs() {
    if (!timerRunning) {
        const mins = parseInt($timerMin.value) || 0;
        const secs = parseInt($timerSec.value) || 0;
        timerRemaining = mins * 60 + secs;
        timerUpdateDisplay();
    }
}

document.getElementById("timer-start").addEventListener("click", () => timerStart());
document.getElementById("timer-pause").addEventListener("click", timerPause);
document.getElementById("timer-reset").addEventListener("click", timerReset);
$timerMin.addEventListener("input", syncTimerInputs);
$timerSec.addEventListener("input", syncTimerInputs);


// ============================================================================
// Init
// ============================================================================

setSystemState("locked");
clearPipelineProgress();
syncTimerInputs();
