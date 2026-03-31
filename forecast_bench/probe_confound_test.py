"""
Adversarial classifier test: can a logistic regression distinguish
high-importance from low-importance node probes based on probe text
embeddings alone?

If accuracy ≈ 50%, probe text does not leak importance cues.
If accuracy >> 50%, linguistic intensity may confound the topological signal.
"""

import csv
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import requests

# ── Config ──────────────────────────────────────────────────────────────

BASE = Path(__file__).resolve().parent.parent / "outputs" / "sensitivity" / "causal"
MODEL_DIRS = {
    "Llama-3.1-8B": BASE / "llama_neutral",
    "Llama-3.3-70B": BASE / "llama_70b_neutral",
    "DeepSeek-V3": BASE / "deepseek_neutral",
    "Qwen3-235B": BASE / "qwen_neutral",
    "Gemini-Flash-Lite": BASE / "gemini_flash_lite_neutral",
    "GPT-OSS-120B": BASE / "gpt_oss_neutral",
}

# High-importance node probes vs low-importance node probes
HIGH_TYPES = {"node_negate_high", "node_strengthen"}
LOW_TYPES = {"node_negate_low", "node_strengthen_low"}

# Embedding cache
CACHE_NPZ = BASE / "probe_text_embeddings.npz"
CACHE_KEYS = BASE / "probe_text_embeddings_keys.json"


# ── Embedding helpers ───────────────────────────────────────────────────

def _get_embeddings_batch(texts: list[str], api_key: str) -> list[list[float]]:
    """Embed a batch of texts in one API call (max ~100 per call)."""
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": "openai/text-embedding-3-large", "input": [t[:8000] for t in texts]},
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()["data"]
            # Sort by index to maintain order
            data.sort(key=lambda x: x["index"])
            return [d["embedding"] for d in data]
        print(f"  Embedding API error: {resp.status_code}: {resp.text[:200]}")
        return []
    except Exception as e:
        print(f"  Embedding error: {e}")
        return []


def _load_cache():
    if CACHE_NPZ.exists() and CACHE_KEYS.exists():
        keys = json.loads(CACHE_KEYS.read_text(encoding="utf-8"))
        matrix = np.load(str(CACHE_NPZ))["embeddings"]
        return {k: i for i, k in enumerate(keys)}, matrix
    return {}, None


def _save_cache(key_to_idx, matrix):
    keys = [""] * len(key_to_idx)
    for k, i in key_to_idx.items():
        keys[i] = k
    CACHE_KEYS.write_text(json.dumps(keys), encoding="utf-8")
    np.savez_compressed(str(CACHE_NPZ), embeddings=matrix.astype(np.float32))


# ── Data loading ────────────────────────────────────────────────────────

def load_probes():
    """Load high/low node probes across all models. Returns list of dicts."""
    probes = []
    for model_name, d in MODEL_DIRS.items():
        csv_path = d / "sensitivity_results.csv"
        if not csv_path.exists():
            continue
        with open(csv_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("success", "").lower() != "true":
                    continue
                pt = row["probe_type"]
                if pt in HIGH_TYPES:
                    label = 1
                elif pt in LOW_TYPES:
                    label = 0
                else:
                    continue
                probes.append({
                    "key": f"probe|{model_name}|{row['question_id']}|{row['probe_type']}|{row.get('probe_index','')}",
                    "text": row["probe_text"],
                    "label": label,
                    "model": model_name,
                    "probe_type": pt,
                    "question_id": row["question_id"],
                })
    return probes


# ── Main ────────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        try:
            from forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except ImportError:
            pass
    if not api_key:
        try:
            from archive.wargame_forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except ImportError:
            pass
    if not api_key:
        print("Error: set OPENROUTER_API_KEY")
        sys.exit(1)

    print("Loading probes...")
    probes = load_probes()
    n_high = sum(1 for p in probes if p["label"] == 1)
    n_low = sum(1 for p in probes if p["label"] == 0)
    print(f"  High-importance: {n_high}, Low-importance: {n_low}, Total: {len(probes)}")

    # Embed probe texts
    print("Loading embedding cache...")
    key_to_idx, matrix = _load_cache()
    print(f"  Cache has {len(key_to_idx)} embeddings")

    texts_to_embed = {p["key"]: p["text"] for p in probes if p["key"] not in key_to_idx}
    if texts_to_embed:
        print(f"  Embedding {len(texts_to_embed)} new probe texts in batches...")
        new_keys, new_vecs = [], []
        items = list(texts_to_embed.items())
        BATCH_SIZE = 50
        for batch_start in range(0, len(items), BATCH_SIZE):
            batch = items[batch_start:batch_start + BATCH_SIZE]
            batch_keys = [k for k, _ in batch]
            batch_texts = [t for _, t in batch]
            embeddings = _get_embeddings_batch(batch_texts, api_key)
            if len(embeddings) == len(batch_keys):
                new_keys.extend(batch_keys)
                new_vecs.extend(embeddings)
            batch_num = batch_start // BATCH_SIZE + 1
            total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"    Batch {batch_num}/{total_batches} done ({len(new_vecs)} total)")
            time.sleep(0.3)

        if new_vecs:
            new_matrix = np.array(new_vecs, dtype=np.float32)
            if matrix is not None:
                matrix = np.vstack([matrix, new_matrix])
            else:
                matrix = new_matrix
            offset = len(key_to_idx)
            for j, k in enumerate(new_keys):
                key_to_idx[k] = offset + j
            _save_cache(key_to_idx, matrix)
            print(f"  Cache updated: {len(key_to_idx)} total")

    # Build feature matrix
    X_list, y_list, valid_probes = [], [], []
    for p in probes:
        if p["key"] in key_to_idx:
            X_list.append(matrix[key_to_idx[p["key"]]])
            y_list.append(p["label"])
            valid_probes.append(p)

    X = np.array(X_list)
    y = np.array(y_list)
    print(f"\nClassifier dataset: {X.shape[0]} probes, {X.shape[1]} dims")
    print(f"  Class balance: {y.sum()} high, {len(y) - y.sum()} low")

    # Logistic regression with 5-fold stratified CV
    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=1000, C=1.0)),
    ])
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    print("\n=== Pooled (all models) ===")
    scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy")
    print(f"  5-fold CV accuracy: {scores.mean():.3f} (+/- {scores.std():.3f})")
    print(f"  Chance level: 0.500")
    print(f"  Fold scores: {[f'{s:.3f}' for s in scores]}")

    # Per-model breakdown
    print("\n=== Per-model ===")
    for model_name in MODEL_DIRS:
        mask = np.array([p["model"] == model_name for p in valid_probes])
        if mask.sum() < 20:
            continue
        X_m, y_m = X[mask], y[mask]
        n_h = y_m.sum()
        n_l = len(y_m) - n_h
        if n_h < 5 or n_l < 5:
            print(f"  {model_name}: skipped (too few per class: {n_h}/{n_l})")
            continue
        scores_m = cross_val_score(clf, X_m, y_m, cv=cv, scoring="accuracy")
        print(f"  {model_name}: {scores_m.mean():.3f} (+/- {scores_m.std():.3f})  [n={len(y_m)}, {int(n_h)}h/{int(n_l)}l]")

    # Also test: negate-only (high vs low) — controls for strengthen/negate framing
    print("\n=== Negate-only (node_negate_high vs node_negate_low) ===")
    mask_neg = np.array([p["probe_type"] in ("node_negate_high", "node_negate_low") for p in valid_probes])
    if mask_neg.sum() >= 20:
        X_neg, y_neg = X[mask_neg], y[mask_neg]
        scores_neg = cross_val_score(clf, X_neg, y_neg, cv=cv, scoring="accuracy")
        print(f"  5-fold CV accuracy: {scores_neg.mean():.3f} (+/- {scores_neg.std():.3f})")
        print(f"  n={len(y_neg)}, {int(y_neg.sum())}h/{int(len(y_neg) - y_neg.sum())}l")

    # Strengthen-only
    print("\n=== Strengthen-only (node_strengthen vs node_strengthen_low) ===")
    mask_str = np.array([p["probe_type"] in ("node_strengthen", "node_strengthen_low") for p in valid_probes])
    if mask_str.sum() >= 20:
        X_str, y_str = X[mask_str], y[mask_str]
        scores_str = cross_val_score(clf, X_str, y_str, cv=cv, scoring="accuracy")
        print(f"  5-fold CV accuracy: {scores_str.mean():.3f} (+/- {scores_str.std():.3f})")
        print(f"  n={len(y_str)}, {int(y_str.sum())}h/{int(len(y_str) - y_str.sum())}l")

    print("\nDone.")


if __name__ == "__main__":
    main()
