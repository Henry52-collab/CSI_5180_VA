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
const $btnWakeBypass = document.getElementById("btn-wake-bypass");
const $wakeResult    = document.getElementById("wake-result");

// Pipeline
const $btnPipelineMic    = document.getElementById("btn-pipeline-mic");
const $inputPipeline     = document.getElementById("input-pipeline");
const $btnPipelineBypass = document.getElementById("btn-pipeline-bypass");
const $nlgMethod         = document.getElementById("nlg-method");
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
    const fd = new FormData();
    fd.append("text", "hey atlas");

    $wakeResult.innerHTML = '<span class="text-muted">Waking...</span>';
    const result = await apiPost("/api/wake", fd);

    if (result.success) {
        $wakeResult.innerHTML = '<span class="success">Atlas is awake!</span>';
        setSystemState("awake");
    } else {
        $wakeResult.innerHTML = '<span class="error">Wake word not detected.</span>';
    }
});


// ============================================================================
// Pipeline
// ============================================================================

async function sendPipeline(formData) {
    formData.append("nlg_method", $nlgMethod.value);

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

        // Update pet if relevant
        if (d.fulfillment && d.fulfillment.type === "pet") {
            updatePet(d.fulfillment);
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
            refs.fill.style.backgroundColor = barColor(val);
            refs.val.textContent = val;
        }
    }

    // Trigger 3D animation if available
    const action = petData.action;
    if (action && typeof window.doroPlayAnimation === "function") {
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
// Chat log
// ============================================================================

function addChat(role, text) {
    const div = document.createElement("div");
    div.className = "chat-msg " + role;
    div.textContent = (role === "user" ? "You: " : "Atlas: ") + text;
    $chatMessages.appendChild(div);
    $chatMessages.scrollTop = $chatMessages.scrollHeight;
}


// ============================================================================
// Mic recording (push-to-hold)
// ============================================================================

function setupMic(button, sendCallback) {
    let recorder = null;
    let chunks = [];

    button.addEventListener("mousedown", async (e) => {
        e.preventDefault();
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            chunks = [];
            recorder = new MediaRecorder(stream);
            recorder.ondataavailable = (ev) => chunks.push(ev.data);
            recorder.onstop = () => {
                stream.getTracks().forEach((t) => t.stop());
                const blob = new Blob(chunks, { type: recorder.mimeType });
                sendCallback(blob);
            };
            recorder.start();
            button.classList.add("recording");
        } catch (err) {
            console.error("Mic access denied:", err);
        }
    });

    const stop = () => {
        if (recorder && recorder.state === "recording") {
            recorder.stop();
            button.classList.remove("recording");
        }
    };

    button.addEventListener("mouseup", stop);
    button.addEventListener("mouseleave", stop);

    // Touch support for mobile
    button.addEventListener("touchstart", (e) => {
        e.preventDefault();
        button.dispatchEvent(new MouseEvent("mousedown"));
    });
    button.addEventListener("touchend", (e) => {
        e.preventDefault();
        stop();
    });
}

// Wire up mic buttons
setupMic($btnVerifyMic, async (blob) => {
    const fd = new FormData();
    fd.append("file", blob, "recording.webm");
    $verifyResult.innerHTML = '<span class="text-muted">Verifying...</span>';
    const result = await apiPost("/api/verify", fd);
    if (result.success) {
        $verifyResult.innerHTML = '<span class="success">Verified!</span>';
        setSystemState("unlocked");
    } else {
        $verifyResult.innerHTML = '<span class="error">Verification failed.</span>';
    }
});

setupMic($btnWakeMic, async (blob) => {
    const fd = new FormData();
    fd.append("file", blob, "recording.webm");
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
    fd.append("file", blob, "recording.webm");
    await sendPipeline(fd);
});


// ============================================================================
// Init
// ============================================================================

setSystemState("locked");
clearPipelineProgress();
