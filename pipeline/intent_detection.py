"""
Intent Detection module (Module 4 in the VA pipeline).

Wraps the DistilBERT joint intent + slot model trained by
`training/train_intent.py` into a clean interface for the orchestrator.

Usage:
    detector = IntentDetector()
    result = detector.process("feed my pet some fish")
    # {"intent": "feed_pet",
    #  "confidence": 0.97,
    #  "slots": {"FOOD_TYPE": "fish"}}

Or to bypass the model (e.g. for manual testing):
    result = detector.bypass("feed_pet", slots={"FOOD_TYPE": "fish"})
"""

import os
import json

import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel


# ============================================================================
# Paths — relative to project root
# ============================================================================

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
DEFAULT_MODEL_DIR = os.path.join(_PROJECT_ROOT, "models", "intent_bert")
DEFAULT_MODEL_NAME = "distilbert-base-uncased"


# ============================================================================
# Model class — must match the architecture used during training
# ============================================================================

class JointIntentSlotModel(nn.Module):
    def __init__(self, num_intents, num_slots, model_name=DEFAULT_MODEL_NAME):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        hidden_size = self.encoder.config.hidden_size

        self.intent_classifier = nn.Sequential(
            nn.Linear(hidden_size, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, num_intents),
        )
        self.slot_classifier = nn.Linear(hidden_size, num_slots)

    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state
        cls_output = sequence_output[:, 0]

        intent_logits = self.intent_classifier(cls_output)
        slot_logits = self.slot_classifier(sequence_output)
        return intent_logits, slot_logits


# ============================================================================
# Public interface
# ============================================================================

class IntentDetector:
    """
    Loads the trained joint intent + slot model and exposes a simple
    `process(text) -> dict` interface for the pipeline orchestrator.
    """

    def __init__(self, model_dir=DEFAULT_MODEL_DIR, device=None):
        self.model_dir = model_dir
        self.device = torch.device(
            device or ("cuda" if torch.cuda.is_available() else "cpu")
        )

        # Load label maps
        label_maps_path = os.path.join(model_dir, "label_maps.json")
        with open(label_maps_path, "r", encoding="utf-8") as f:
            label_maps = json.load(f)
        self.intent_labels = label_maps["intent_labels"]  # list: index == id
        self.slot_labels = label_maps["slot_labels"]

        # Build the model skeleton, then load weights
        self.model = JointIntentSlotModel(
            num_intents=len(self.intent_labels),
            num_slots=len(self.slot_labels),
        )
        weights_path = os.path.join(model_dir, "model.pth")
        self.model.load_state_dict(
            torch.load(weights_path, map_location=self.device, weights_only=True)
        )
        self.model.to(self.device)
        self.model.eval()  # inference mode (no dropout)

        # Tokenizer must match the one used during training
        self.tokenizer = AutoTokenizer.from_pretrained(DEFAULT_MODEL_NAME)

    # ------------------------------------------------------------------
    @torch.no_grad()
    def process(self, text: str) -> dict:
        """
        Run the joint model on a single text input.

        Returns:
            {
                "intent": str,          # e.g. "feed_pet"
                "confidence": float,    # softmax probability of the top intent
                "slots": {SLOT: value}, # e.g. {"FOOD_TYPE": "fish"}
            }
        """
        text = (text or "").strip()
        if not text:
            return {"intent": "oos", "confidence": 0.0, "slots": {}}

        words = text.split()

        # Tokenize (matches training settings)
        encoding = self.tokenizer(
            words,
            is_split_into_words=True,
            padding=True,
            truncation=True,
            max_length=32,
            return_tensors="pt",
        )
        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)

        intent_logits, slot_logits = self.model(input_ids, attention_mask)

        # Intent: pick argmax + softmax confidence
        intent_probs = torch.softmax(intent_logits, dim=1)[0]  # [num_intents]
        intent_idx = int(torch.argmax(intent_probs).item())
        intent_name = self.intent_labels[intent_idx]
        confidence = float(intent_probs[intent_idx].item())

        # Slots: argmax per token, then group B-/I- tags by original word
        slot_pred_ids = torch.argmax(slot_logits[0], dim=-1).cpu().tolist()
        word_ids = encoding.word_ids(batch_index=0)
        slots = self._extract_slots(words, word_ids, slot_pred_ids)

        return {
            "intent": intent_name,
            "confidence": confidence,
            "slots": slots,
        }

    # ------------------------------------------------------------------
    def bypass(self, intent: str, slots: dict = None) -> dict:
        """
        Skip the model entirely and return a hand-crafted intent.
        Used for manual testing or when the ASR output is unreliable.
        """
        if intent not in self.intent_labels:
            raise ValueError(
                f"Unknown intent '{intent}'. "
                f"Must be one of: {self.intent_labels}"
            )
        return {
            "intent": intent,
            "confidence": 1.0,
            "slots": slots or {},
        }

    # ------------------------------------------------------------------
    def _extract_slots(self, words, word_ids, slot_pred_ids):
        """
        Turn per-token BIO predictions into a {SLOT_TYPE: value} dict.

        We only look at the FIRST sub-token of each word (same rule as
        training's align_labels). Consecutive B-X / I-X of the same type
        are merged into one entity.
        """
        slots = {}
        current_type = None
        current_words = []

        prev_word_id = None
        for i, word_id in enumerate(word_ids):
            # Skip specials and continuation sub-tokens
            if word_id is None or word_id == prev_word_id:
                prev_word_id = word_id
                continue

            label = self.slot_labels[slot_pred_ids[i]]
            word = words[word_id]

            if label.startswith("B-"):
                # Flush previous entity (if any)
                if current_type:
                    slots[current_type] = " ".join(current_words)
                current_type = label[2:].lower()  #compatible with fulfillment
                current_words = [word]
            elif label.startswith("I-") and current_type == label[2:].lower(): #compatible with fulfillment
                current_words.append(word)
            else:
                # "O" or an I- that doesn't match current type — flush
                if current_type:
                    slots[current_type] = " ".join(current_words)
                    current_type = None
                    current_words = []

            prev_word_id = word_id

        # Flush any trailing entity
        if current_type:
            slots[current_type] = " ".join(current_words)

        # Strip trailing punctuation (Whisper adds ?.! to transcriptions)
        for key in slots:
            slots[key] = slots[key].strip().rstrip("?.!,;:")

        return slots


# ============================================================================
# Quick manual test
# ============================================================================

if __name__ == "__main__":
    detector = IntentDetector()

    test_sentences = [
        "hello there",
        "feed my pet some fish",
        "play with the pet using a frisbee",
        "what is the weather in Ottawa",
        "who is in Inception",
        "set a timer for 5 minutes",
        "rename my pet to Whiskers",
        "give my cat a treat",
        "what movies are trending",
        "goodbye",
    ]

    print("=" * 70)
    print("IntentDetector quick test")
    print("=" * 70)
    for text in test_sentences:
        result = detector.process(text)
        print(f"\n> {text}")
        print(f"  intent    : {result['intent']} (conf={result['confidence']:.3f})")
        print(f"  slots     : {result['slots']}")
