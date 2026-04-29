"""
Cross-model reasoning similarity analysis.

For each question × probe_type, embed the reasoning from each model
and compute pairwise cosine similarity. This measures whether models
arrive at similar justifications for the same structural probe type.

Also analyzes failure modes: cases where models shift a lot on
irrelevant probes or fail to shift on high-importance ones.

Usage:
    python -m forecast_bench.analyze_reasoning_similarity
    python -m forecast_bench.analyze_reasoning_similarity --skip-embeddings  # reuse cached
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from collections import defaultdict

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Config ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"
OUT = BASE / "paper" / "figures" / "internal"

MODEL_DIRS = {
    "llama-8b": CAUSAL_DIR / "llama_neutral",
    "llama-70b": CAUSAL_DIR / "llama_70b_neutral",
    "deepseek": CAUSAL_DIR / "deepseek_neutral",
    "qwen-235b": CAUSAL_DIR / "qwen_neutral",
    "gemini": CAUSAL_DIR / "gemini_fl_neutral",
    "gpt-oss": CAUSAL_DIR / "gpt_oss_neutral",
    "qwen-32b": CAUSAL_DIR / "qwen_32b_neutral",
}

EMBEDDINGS_CACHE = CAUSAL_DIR / "reasoning_embeddings.npz"
EMBEDDINGS_KEYS_CACHE = CAUSAL_DIR / "reasoning_embeddings_keys.json"

import requests


def _get_api_key() -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "")
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
    return api_key


def get_embedding(text: str, api_key: str, model: str = "openai/text-embedding-3-large") -> list[float] | None:
    """Get embedding vector from OpenRouter."""
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"model": model, "input": text[:8000]},  # truncate for safety
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["data"][0]["embedding"]
        else:
            print(f"  Embedding API error: {resp.status_code}")
            return None
    except Exception as e:
        print(f"  Embedding error: {e}")
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_np, b_np = np.array(a), np.array(b)
    dot = np.dot(a_np, b_np)
    norm = np.linalg.norm(a_np) * np.linalg.norm(b_np)
    return float(dot / norm) if norm > 0 else 0.0


def load_all_reasoning() -> dict:
    """Load reasoning texts organized by (question_id, probe_type, probe_index) -> {model: reasoning}."""
    reasoning_map = defaultdict(dict)  # (qid, probe_type, idx) -> {model: reasoning}

    for model_name, model_dir in MODEL_DIRS.items():
        q_dir = model_dir / "question_results"
        if not q_dir.exists():
            print(f"  Skipping {model_name}: no question_results")
            continue

        count = 0
        for f in sorted(q_dir.glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            qid = data.get("question_id", f.stem)

            # Group probes by type, then index within type
            type_counts = defaultdict(int)
            for pr in data.get("probe_results", []):
                if not pr.get("success") or not pr.get("reasoning"):
                    continue
                ptype = pr["probe_type"]
                idx = type_counts[ptype]
                type_counts[ptype] += 1

                key = f"{qid}|{ptype}|{idx}"
                reasoning_map[key][model_name] = {
                    "reasoning": pr["reasoning"],
                    "shift": pr.get("absolute_shift"),
                    "target_id": pr.get("target_id", ""),
                    "probe_text": pr.get("probe_text", ""),
                }
                count += 1

        print(f"  {model_name}: {count} reasoning entries")

    return dict(reasoning_map)


def _load_embedding_cache() -> tuple[dict[str, int], np.ndarray | None]:
    """Load cached embeddings from numpy format. Returns (key->index map, matrix)."""
    if EMBEDDINGS_CACHE.exists() and EMBEDDINGS_KEYS_CACHE.exists():
        keys = json.loads(EMBEDDINGS_KEYS_CACHE.read_text(encoding="utf-8"))
        data = np.load(EMBEDDINGS_CACHE)
        matrix = data["embeddings"]
        key_to_idx = {k: i for i, k in enumerate(keys)}
        return key_to_idx, matrix
    return {}, None


def _save_embedding_cache(key_to_idx: dict[str, int], matrix: np.ndarray):
    """Save embeddings in numpy format."""
    keys = [""] * len(key_to_idx)
    for k, i in key_to_idx.items():
        keys[i] = k
    EMBEDDINGS_KEYS_CACHE.write_text(json.dumps(keys), encoding="utf-8")
    np.savez_compressed(EMBEDDINGS_CACHE, embeddings=matrix)


def _merge_and_save(key_to_idx, matrix, new_keys, new_embeddings):
    """Merge new embeddings into cache and save to disk."""
    new_matrix = np.array(new_embeddings, dtype=np.float32)
    if matrix is not None:
        matrix = np.vstack([matrix, new_matrix])
    else:
        matrix = new_matrix
    base_idx = len(key_to_idx)
    for j, k in enumerate(new_keys):
        key_to_idx[k] = base_idx + j
    _save_embedding_cache(key_to_idx, matrix)


def compute_embeddings(reasoning_map: dict, api_key: str) -> dict:
    """Compute embeddings for all reasoning texts. Returns {key|model: [embedding]}."""
    key_to_idx, matrix = _load_embedding_cache()
    if matrix is not None:
        print(f"Loaded {len(key_to_idx)} cached embeddings from {EMBEDDINGS_CACHE}")

    # Collect all keys we need
    all_keys = []
    for key, models in reasoning_map.items():
        for model_name in models:
            all_keys.append(f"{key}|{model_name}")

    # Find missing
    missing = [(k, reasoning_map["|".join(k.rsplit("|", 1)[0].split("|"))][k.rsplit("|", 1)[1]])
               for k in all_keys if k not in key_to_idx]

    # Simpler approach: rebuild missing list
    missing_keys = []
    missing_texts = []
    for key, models in reasoning_map.items():
        for model_name, data in models.items():
            emb_key = f"{key}|{model_name}"
            if emb_key not in key_to_idx:
                missing_keys.append(emb_key)
                missing_texts.append(data["reasoning"])

    print(f"  Need {len(missing_keys)} new embeddings")

    if not missing_keys:
        # Convert cache to dict format for downstream
        result = {}
        for k, i in key_to_idx.items():
            result[k] = matrix[i].tolist()
        return result

    # Compute missing embeddings
    new_embeddings = []
    new_keys = []
    for i, (emb_key, text) in enumerate(zip(missing_keys, missing_texts)):
        emb = get_embedding(text, api_key)
        if emb:
            new_keys.append(emb_key)
            new_embeddings.append(emb)

        if (i + 1) % 20 == 0:
            time.sleep(0.5)

        # Save incrementally every 50 embeddings
        if len(new_embeddings) > 0 and len(new_embeddings) % 50 == 0:
            _merge_and_save(key_to_idx, matrix, new_keys, new_embeddings)
            # Free memory and reload from disk
            del matrix
            key_to_idx, matrix = _load_embedding_cache()
            new_keys, new_embeddings = [], []
            print(f"  [{i+1}/{len(missing_keys)}] checkpoint saved ({len(key_to_idx)} total)")

    # Final merge
    if new_embeddings:
        _merge_and_save(key_to_idx, matrix, new_keys, new_embeddings)
        key_to_idx, matrix = _load_embedding_cache()
        print(f"  Saved {len(key_to_idx)} total embeddings")

    # Convert to dict format
    result = {}
    for k, i in key_to_idx.items():
        result[k] = matrix[i].tolist()
    return result


def analyze_similarity(reasoning_map: dict, embeddings: dict):
    """Compute pairwise model similarity for shared probes."""
    model_names = sorted(MODEL_DIRS.keys())
    pair_sims = defaultdict(list)  # (model_a, model_b) -> [similarity scores]
    type_sims = defaultdict(lambda: defaultdict(list))  # probe_type -> (model_a, model_b) -> [sims]

    for key, models in reasoning_map.items():
        parts = key.split("|")
        ptype = parts[1] if len(parts) >= 2 else "unknown"

        available = []
        for m in model_names:
            emb_key = f"{key}|{m}"
            if m in models and emb_key in embeddings:
                available.append((m, embeddings[emb_key]))

        # Pairwise comparisons
        for i in range(len(available)):
            for j in range(i + 1, len(available)):
                m_a, emb_a = available[i]
                m_b, emb_b = available[j]
                sim = cosine_similarity(emb_a, emb_b)
                pair_key = tuple(sorted([m_a, m_b]))
                pair_sims[pair_key].append(sim)
                type_sims[ptype][pair_key].append(sim)

    return pair_sims, type_sims


def analyze_failure_modes(reasoning_map: dict):
    """Identify failure cases: high shift on irrelevant, low shift on high-importance."""
    failures = {
        "irrelevant_high_shift": [],  # shifted a lot on irrelevant
        "high_importance_low_shift": [],  # didn't shift on high-importance
    }

    for key, models in reasoning_map.items():
        parts = key.split("|")
        ptype = parts[1] if len(parts) >= 2 else "unknown"
        qid = parts[0] if parts else "unknown"

        for model_name, data in models.items():
            shift = data.get("shift")
            if shift is None:
                continue

            if ptype == "irrelevant" and shift > 0.10:
                failures["irrelevant_high_shift"].append({
                    "model": model_name,
                    "question_id": qid,
                    "shift": round(shift, 3),
                    "reasoning": data["reasoning"][:300],
                    "probe_text": data["probe_text"][:200],
                })

            if ptype in ("node_negate_high", "edge_negate_critical") and shift < 0.02:
                failures["high_importance_low_shift"].append({
                    "model": model_name,
                    "question_id": qid,
                    "probe_type": ptype,
                    "shift": round(shift, 3),
                    "reasoning": data["reasoning"][:300],
                    "target_id": data["target_id"],
                })

    return failures


def print_results(pair_sims, type_sims, failures):
    """Print analysis results."""
    print("\n" + "=" * 60)
    print("CROSS-MODEL REASONING SIMILARITY")
    print("=" * 60)

    print("\n--- Overall Pairwise Similarity ---")
    for (m_a, m_b), sims in sorted(pair_sims.items()):
        mean_sim = np.mean(sims)
        std_sim = np.std(sims)
        print(f"  {m_a:12s} vs {m_b:12s}: {mean_sim:.3f} ± {std_sim:.3f} (n={len(sims)})")

    print("\n--- Similarity by Probe Type ---")
    for ptype in sorted(type_sims.keys()):
        print(f"\n  {ptype}:")
        for (m_a, m_b), sims in sorted(type_sims[ptype].items()):
            if len(sims) >= 5:
                print(f"    {m_a:12s} vs {m_b:12s}: {np.mean(sims):.3f} (n={len(sims)})")

    print("\n--- Failure Modes ---")
    print(f"\nIrrelevant probes with |shift| > 10pp: {len(failures['irrelevant_high_shift'])}")
    by_model = defaultdict(int)
    for f in failures["irrelevant_high_shift"]:
        by_model[f["model"]] += 1
    for m, c in sorted(by_model.items(), key=lambda x: -x[1]):
        print(f"  {m}: {c}")
    if failures["irrelevant_high_shift"]:
        print(f"\n  Example:")
        ex = failures["irrelevant_high_shift"][0]
        print(f"    Model: {ex['model']}, Shift: {ex['shift']}")
        print(f"    Probe: {ex['probe_text'][:150]}")
        print(f"    Reasoning: {ex['reasoning'][:150]}")

    print(f"\nHigh-importance probes with |shift| < 2pp: {len(failures['high_importance_low_shift'])}")
    by_model = defaultdict(int)
    for f in failures["high_importance_low_shift"]:
        by_model[f["model"]] += 1
    for m, c in sorted(by_model.items(), key=lambda x: -x[1]):
        print(f"  {m}: {c}")
    if failures["high_importance_low_shift"]:
        print(f"\n  Example:")
        ex = failures["high_importance_low_shift"][0]
        print(f"    Model: {ex['model']}, Type: {ex['probe_type']}, Target: {ex['target_id']}, Shift: {ex['shift']}")
        print(f"    Reasoning: {ex['reasoning'][:150]}")


def save_results(pair_sims, type_sims, failures):
    """Save results to JSON."""
    output = {
        "pairwise_similarity": {
            f"{m_a}_vs_{m_b}": {
                "mean": round(float(np.mean(sims)), 4),
                "std": round(float(np.std(sims)), 4),
                "n": len(sims),
            }
            for (m_a, m_b), sims in pair_sims.items()
        },
        "by_probe_type": {
            ptype: {
                f"{m_a}_vs_{m_b}": {
                    "mean": round(float(np.mean(sims)), 4),
                    "n": len(sims),
                }
                for (m_a, m_b), sims in type_pairs.items()
                if len(sims) >= 5
            }
            for ptype, type_pairs in type_sims.items()
        },
        "failure_modes": {
            "irrelevant_high_shift_count": len(failures["irrelevant_high_shift"]),
            "high_importance_low_shift_count": len(failures["high_importance_low_shift"]),
            "irrelevant_by_model": dict(defaultdict(int)),
            "low_shift_by_model": dict(defaultdict(int)),
        },
    }

    # Count by model
    for f in failures["irrelevant_high_shift"]:
        output["failure_modes"]["irrelevant_by_model"][f["model"]] = \
            output["failure_modes"]["irrelevant_by_model"].get(f["model"], 0) + 1
    for f in failures["high_importance_low_shift"]:
        output["failure_modes"]["low_shift_by_model"][f["model"]] = \
            output["failure_modes"]["low_shift_by_model"].get(f["model"], 0) + 1

    out_path = CAUSAL_DIR / "reasoning_similarity_analysis.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nResults saved to {out_path}")

    # Save failure examples
    failures_path = CAUSAL_DIR / "failure_mode_examples.json"
    failures_path.write_text(json.dumps(failures, indent=2, default=str), encoding="utf-8")
    print(f"Failure examples saved to {failures_path}")


def main():
    parser = argparse.ArgumentParser(description="Cross-model reasoning similarity analysis")
    parser.add_argument("--skip-embeddings", action="store_true",
                        help="Skip embedding computation, use cached only")
    args = parser.parse_args()

    print("Loading reasoning from all models...")
    reasoning_map = load_all_reasoning()
    print(f"Total probe entries: {len(reasoning_map)}")

    # Failure mode analysis (no embeddings needed)
    print("\nAnalyzing failure modes...")
    failures = analyze_failure_modes(reasoning_map)

    if args.skip_embeddings:
        if EMBEDDINGS_CACHE.exists():
            embeddings = json.loads(EMBEDDINGS_CACHE.read_text(encoding="utf-8"))
            print(f"Loaded {len(embeddings)} cached embeddings")
        else:
            print("No cached embeddings found. Run without --skip-embeddings first.")
            print_results({}, {}, failures)
            return
    else:
        api_key = _get_api_key()
        if not api_key:
            print("[ERROR] No API key for embeddings. Set OPENROUTER_API_KEY.")
            print("Running failure mode analysis only...\n")
            print_results({}, {}, failures)
            return

        print("\nComputing embeddings...")
        embeddings = compute_embeddings(reasoning_map, api_key)

    print("\nComputing pairwise similarities...")
    pair_sims, type_sims = analyze_similarity(reasoning_map, embeddings)

    print_results(pair_sims, type_sims, failures)
    save_results(pair_sims, type_sims, failures)


if __name__ == "__main__":
    main()
