"""
Task 10: Joint Intent Classification + Slot Filling
Fine-tune DistilBERT on our 22-intent dataset (594 sentences, inline BIO format).

Adapted from Activity 2 (JointIntentSlot_Fengshou Xu_300036335.ipynb).
Key differences from Activity 2:
  - 22 intents instead of 7
  - 594 sentences instead of ~75
  - Saves model weights + label_maps.json to disk for pipeline inference
"""

import os
import sys
import json
import random

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import AutoTokenizer, AutoModel
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from seqeval.metrics import classification_report as seq_classification_report
from seqeval.metrics import f1_score as seq_f1_score

# Make the project root importable so "from data.intents..." works
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data.intents.training_data import intent_map


# ============================================================================
# Config
# ============================================================================

MODEL_NAME = "distilbert-base-uncased"
MAX_LENGTH = 32          # max tokens per sentence (most of our examples are short)
BATCH_SIZE = 16
EPOCHS = 10
LR = 5e-5
TEST_SIZE = 0.2
SEED = 0x0d000721

OUTPUT_DIR = os.path.join(PROJECT_ROOT, "models", "intent_bert")
MODEL_PATH = os.path.join(OUTPUT_DIR, "model.pth")
LABEL_MAPS_PATH = os.path.join(OUTPUT_DIR, "label_maps.json")

# Reproducibility
random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ============================================================================
# Step 1: Parse training data (inline BIO → tokens + slots + intents)
# ============================================================================

def parse_example(sentence):
    """Split 'feed my pet some fish/B-FOOD_TYPE' into tokens + BIO slots."""
    tokens = []
    slots = []
    for word in sentence.split():
        if "/" in word:
            token, slot = word.split("/", 1)  # split on first '/' only
        else:
            token = word
            slot = "O"
        tokens.append(token)
        slots.append(slot)
    return tokens, slots


def load_dataset():
    """Walk intent_map, parse every sentence, return parallel lists."""
    all_tokens = []
    all_slots = []
    all_intents = []

    for intent_name, sentences in intent_map.items():
        for sentence in sentences:
            tokens, slots = parse_example(sentence)
            all_tokens.append(tokens)
            all_slots.append(slots)
            all_intents.append(intent_name)

    return all_tokens, all_slots, all_intents


def build_label_maps(all_slots, all_intents):
    """Build deterministic id<->label mappings."""
    # Collect every unique slot label across all sentences
    slot_set = set()
    for slot_sequence in all_slots:
        slot_set.update(slot_sequence)   # add every label from this sentence
    unique_slots = sorted(slot_set)

    # Same thing for intents (already one per sentence, so just set())
    unique_intents = sorted(set(all_intents))

    # Build both directions: name <-> id
    slot2id = {s: i for i, s in enumerate(unique_slots)}
    id2slot = {i: s for s, i in slot2id.items()}
    intent2id = {name: i for i, name in enumerate(unique_intents)}
    id2intent = {i: name for name, i in intent2id.items()}

    return unique_slots, unique_intents, slot2id, id2slot, intent2id, id2intent


# ============================================================================
# Step 2: Tokenize + align slot labels with WordPiece sub-tokens
# ============================================================================

def align_labels(all_tokens, all_slots, encodings, slot2id):
    """
    Align per-word slot labels with DistilBERT's sub-word tokenization.

    Each input word might be split into multiple sub-tokens (e.g. 'nameless'
    → 'name' + '##less'). We only let the FIRST sub-token carry the real
    label; all other positions get -100 so CrossEntropyLoss ignores them.
    """
    aligned = []
    for i in range(len(all_tokens)):
        word_ids = encodings.word_ids(batch_index=i)
        prev_word_id = None
        label_ids = []
        for word_id in word_ids:
            if word_id is None:
                # [CLS], [SEP], [PAD] etc.
                label_ids.append(-100)
            elif word_id != prev_word_id:
                # First sub-token of a new word → real label
                label_ids.append(slot2id[all_slots[i][word_id]])
            else:
                # Continuation sub-token → ignored
                label_ids.append(-100)
            prev_word_id = word_id
        aligned.append(label_ids)
    return aligned


# ============================================================================
# Step 3: PyTorch Dataset wrapping tokenized encodings + labels
# ============================================================================

class JointDataset(Dataset):
    def __init__(self, encodings, slot_labels, intent_labels):
        self.input_ids = encodings["input_ids"]
        self.attention_mask = encodings["attention_mask"]
        self.slot_labels = slot_labels      # list of list[int]
        self.intent_labels = intent_labels  # list[int]

    def __len__(self):
        return len(self.intent_labels)

    def __getitem__(self, idx):
        return {
            "input_ids": self.input_ids[idx],
            "attention_mask": self.attention_mask[idx],
            "slot_labels": torch.tensor(self.slot_labels[idx], dtype=torch.long),
            "intent_label": torch.tensor(self.intent_labels[idx], dtype=torch.long),
        }


# ============================================================================
# Step 4: Joint model (DistilBERT encoder + intent head + slot head)
# ============================================================================

class JointIntentSlotModel(nn.Module):
    def __init__(self, num_intents, num_slots, model_name=MODEL_NAME):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        hidden_size = self.encoder.config.hidden_size  # 768 for DistilBERT

        # Intent head: classify from [CLS] pooled representation
        self.intent_classifier = nn.Sequential(
            nn.Linear(hidden_size, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, num_intents),
        )

        # Slot head: classify each token independently
        self.slot_classifier = nn.Linear(hidden_size, num_slots)

    def forward(self, input_ids, attention_mask,
                intent_labels=None, slot_labels=None):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state  # [B, T, H]
        cls_output = sequence_output[:, 0]           # [B, H] — [CLS] token

        intent_logits = self.intent_classifier(cls_output)
        slot_logits = self.slot_classifier(sequence_output)

        loss = None
        if intent_labels is not None and slot_labels is not None:
            intent_loss_fn = nn.CrossEntropyLoss()
            slot_loss_fn = nn.CrossEntropyLoss(ignore_index=-100)

            intent_loss = intent_loss_fn(intent_logits, intent_labels)
            slot_loss = slot_loss_fn(
                slot_logits.view(-1, slot_logits.shape[-1]),
                slot_labels.view(-1),
            )
            loss = intent_loss + slot_loss

        return {
            "loss": loss,
            "intent_logits": intent_logits,
            "slot_logits": slot_logits,
        }


# ============================================================================
# Step 5: Training loop
# ============================================================================

def train_epoch(model, loader, optimizer, device):
    model.train()
    total_loss = 0.0
    for batch in loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        intent_labels = batch["intent_label"].to(device)
        slot_labels = batch["slot_labels"].to(device)

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            intent_labels=intent_labels,
            slot_labels=slot_labels,
        )
        loss = outputs["loss"]

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
    return total_loss / len(loader)


# ============================================================================
# Step 6: Evaluation
# ============================================================================

@torch.no_grad()
def evaluate(model, loader, id2intent, id2slot, device):
    """Compute intent accuracy (sklearn) + slot F1 (seqeval, BIO-aware)."""
    model.eval()

    intent_true_ids = []
    intent_pred_ids = []
    slot_true_seqs = []  # list of list[str]
    slot_pred_seqs = []  # list of list[str]

    for batch in loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        intent_labels = batch["intent_label"].to(device)
        slot_labels = batch["slot_labels"].to(device)

        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        intent_preds = torch.argmax(outputs["intent_logits"], dim=1)
        slot_preds = torch.argmax(outputs["slot_logits"], dim=2)

        intent_true_ids.extend(intent_labels.cpu().tolist())
        intent_pred_ids.extend(intent_preds.cpu().tolist())

        # For slots, drop the -100 positions (subwords, CLS/SEP/PAD)
        for true_seq, pred_seq in zip(slot_labels.cpu().tolist(), slot_preds.cpu().tolist()):
            true_labels = []
            pred_labels = []
            for t, p in zip(true_seq, pred_seq):
                if t != -100:
                    true_labels.append(id2slot[t])
                    pred_labels.append(id2slot[p])
            slot_true_seqs.append(true_labels)
            slot_pred_seqs.append(pred_labels)

    # Intent metrics
    intent_true_names = [id2intent[i] for i in intent_true_ids]
    intent_pred_names = [id2intent[i] for i in intent_pred_ids]
    intent_acc = sum(t == p for t, p in zip(intent_true_names, intent_pred_names)) / len(intent_true_names)

    # Slot metrics (BIO-aware via seqeval)
    slot_f1 = seq_f1_score(slot_true_seqs, slot_pred_seqs)

    return {
        "intent_acc": intent_acc,
        "intent_true": intent_true_names,
        "intent_pred": intent_pred_names,
        "slot_f1": slot_f1,
        "slot_true": slot_true_seqs,
        "slot_pred": slot_pred_seqs,
    }


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 70)
    print("Task 10: Joint Intent + Slot Training")
    print("=" * 70)

    # --- Load data ---
    all_tokens, all_slots, all_intents = load_dataset()
    print(f"\n[Data] {len(all_tokens)} sentences loaded from {len(intent_map)} intents")

    # Per-intent counts (sanity check)
    print("\n[Data] Sentences per intent:")
    for intent_name in sorted(intent_map.keys()):
        count = all_intents.count(intent_name)
        print(f"  {intent_name:.<30s} {count:>3d}")

    # --- Build label maps ---
    unique_slots, unique_intents, slot2id, id2slot, intent2id, id2intent = \
        build_label_maps(all_slots, all_intents)
    print(f"\n[Labels] {len(unique_intents)} intents, {len(unique_slots)} slot labels")

    # --- Tokenize all sentences ---
    print(f"\n[Tokenize] Loading {MODEL_NAME} tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    encodings = tokenizer(
        all_tokens,
        is_split_into_words=True,   # we pass lists of words, not raw strings
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )
    print(f"[Tokenize] Encoded shape: {encodings['input_ids'].shape}")

    # --- Align slot labels with sub-tokens ---
    aligned_slot_labels = align_labels(all_tokens, all_slots, encodings, slot2id)
    intent_label_ids = [intent2id[name] for name in all_intents]

    # --- Train/Val split (stratified by intent so each intent is in both sets) ---
    indices = list(range(len(intent_label_ids)))
    train_idx, val_idx = train_test_split(
        indices,
        test_size=TEST_SIZE,
        random_state=SEED,
        stratify=intent_label_ids,
    )
    print(f"\n[Split] train={len(train_idx)}  val={len(val_idx)}")

    def take(lst, idxs):
        return [lst[i] for i in idxs]

    train_encodings = {
        "input_ids": encodings["input_ids"][train_idx],
        "attention_mask": encodings["attention_mask"][train_idx],
    }
    val_encodings = {
        "input_ids": encodings["input_ids"][val_idx],
        "attention_mask": encodings["attention_mask"][val_idx],
    }

    train_dataset = JointDataset(
        train_encodings, take(aligned_slot_labels, train_idx), take(intent_label_ids, train_idx)
    )
    val_dataset = JointDataset(
        val_encodings, take(aligned_slot_labels, val_idx), take(intent_label_ids, val_idx)
    )

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

    # --- Build model + optimizer ---
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n[Device] {device}")

    model = JointIntentSlotModel(
        num_intents=len(unique_intents),
        num_slots=len(unique_slots),
    ).to(device)

    optimizer = AdamW(model.parameters(), lr=LR)

    # --- Training loop (with per-epoch validation + save best) ---
    print(f"\n[Train] {EPOCHS} epochs, batch_size={BATCH_SIZE}, lr={LR}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    best_score = -1.0
    best_epoch = 0

    for epoch in range(1, EPOCHS + 1):
        avg_loss = train_epoch(model, train_loader, optimizer, device)
        metrics = evaluate(model, val_loader, id2intent, id2slot, device)

        # Combined score: prioritise intent accuracy but also reward slot F1
        score = metrics["intent_acc"] + metrics["slot_f1"]
        marker = ""
        if score > best_score:
            best_score = score
            best_epoch = epoch
            torch.save(model.state_dict(), MODEL_PATH)
            marker = "  <-- saved (best)"

        print(
            f"  Epoch {epoch}/{EPOCHS}  "
            f"loss={avg_loss:.4f}  "
            f"intent_acc={metrics['intent_acc']:.4f}  "
            f"slot_f1={metrics['slot_f1']:.4f}"
            + marker
        )

    # --- Reload the best checkpoint before the final report ---
    print(f"\n[Load] Restoring best model from epoch {best_epoch}")
    model.load_state_dict(torch.load(MODEL_PATH, weights_only=True))

    # --- Save label maps alongside the model ---
    label_maps = {
        "intent_labels": unique_intents,   # index == intent id
        "slot_labels": unique_slots,        # index == slot id
    }
    with open(LABEL_MAPS_PATH, "w", encoding="utf-8") as f:
        json.dump(label_maps, f, indent=2)
    print(f"[Save] Wrote {MODEL_PATH}")
    print(f"[Save] Wrote {LABEL_MAPS_PATH}")

    # --- Final detailed report ---
    print("\n" + "=" * 70)
    print("Final Validation Report (best checkpoint)")
    print("=" * 70)

    final_metrics = evaluate(model, val_loader, id2intent, id2slot, device)

    print("\n[Intent] Classification report:")
    print(classification_report(
        final_metrics["intent_true"],
        final_metrics["intent_pred"],
        zero_division=0,
    ))

    print("[Slot] Classification report (seqeval, BIO-aware):")
    print(seq_classification_report(
        final_metrics["slot_true"],
        final_metrics["slot_pred"],
        zero_division=0,
    ))

    print(f"\n[Summary] intent_acc={final_metrics['intent_acc']:.4f}  "
          f"slot_f1={final_metrics['slot_f1']:.4f}")


if __name__ == "__main__":
    main()
