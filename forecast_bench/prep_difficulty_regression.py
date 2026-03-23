"""
Prepare a flat CSV for the R difficulty-ELO regression analysis.

Reads:
  - difficulty_elo.json (ELO ratings per question)
  - sensitivity_results.csv from each model directory
  - reasoning_judge_ratings.json
  - uncertainty_judge_ratings.json
  - ground_truth_resolutions.json

Outputs:
  - outputs/sensitivity/causal/difficulty_regression_data.csv

One row per (model, question) with columns:
  model, question_id, elo, initial_prob, abs_dist_from_50,
  mean_shift, ssr, within_tau, spp, asymmetry_index,
  mean_judge_rating, mean_uncertainty_rating, inter_model_sd, n_probes, brier, source
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

BASE = Path(__file__).parent.parent
CAUSAL_DIR = BASE / "outputs" / "sensitivity" / "causal"

MODEL_DIRS = {
    "llama-8b": CAUSAL_DIR / "llama_one_turn",
    "llama-70b": CAUSAL_DIR / "70b_one_turn",
    "deepseek": CAUSAL_DIR / "deepseek_one_turn",
    "qwen": CAUSAL_DIR / "qwen_one_turn",
    "gemini": CAUSAL_DIR / "gemini_flash_lite_one_turn",
}

HIGH_IMPORTANCE_TYPES = {
    "node_negate_high", "node_strengthen",
    "edge_negate_critical", "edge_strengthen_critical",
}
LOW_IMPORTANCE_TYPES = {
    "node_negate_low", "node_strengthen_low",
    "edge_negate_peripheral", "edge_strengthen_peripheral",
    "irrelevant",
}
NEGATE_TYPES = {"node_negate_high", "node_negate_low", "edge_negate_critical", "edge_negate_peripheral"}
STRENGTHEN_TYPES = {"node_strengthen", "node_strengthen_low", "edge_strengthen_critical", "edge_strengthen_peripheral"}


def _spearman(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None

    def _rank(vals):
        indexed = sorted(enumerate(vals), key=lambda t: t[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx, ry = _rank(x), _rank(y)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if sx == 0 or sy == 0:
        return None
    return cov / (sx * sy)


def _kendall_tau(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if dx * dy > 0:
                concordant += 1
            elif dx * dy < 0:
                discordant += 1
    denom = concordant + discordant
    if denom == 0:
        return None
    return (concordant - discordant) / denom


def load_csv_rows(csv_path: Path) -> list[dict]:
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for field in ("initial_probability", "updated_probability", "absolute_shift",
                          "target_importance", "target_centrality_rank"):
                if row.get(field):
                    try:
                        row[field] = float(row[field])
                    except ValueError:
                        row[field] = None
                else:
                    row[field] = None
            row["success"] = str(row.get("success", "")).lower() == "true"
            row["target_on_critical_path"] = str(row.get("target_on_critical_path", "")).lower() == "true"
            # Normalize probe types
            pt = row.get("probe_type", "")
            norm = {
                "irlevant": "irrelevant", "edge_missing": "edge_spurious",
                "edge_omitted": "edge_spurious", "edge_added": "edge_fabricate",
                "edge_addition": "edge_fabricate", "edge_add": "edge_fabricate",
                "edge_add_causal": "edge_fabricate", "edge_add_direct": "edge_fabricate",
                "edge_feedback": "edge_spurious",
            }
            row["probe_type"] = norm.get(pt, pt)
            rows.append(row)
    return rows


def compute_question_metrics(rows: list[dict]) -> dict:
    """Compute per-question metrics from probe-level rows."""
    ok = [r for r in rows if r["success"] and r["absolute_shift"] is not None]
    if not ok:
        return None

    # Mean absolute shift
    shifts = [r["absolute_shift"] for r in ok]
    mean_shift = sum(shifts) / len(shifts)

    # SSR
    high = [r["absolute_shift"] for r in ok if r["probe_type"] in HIGH_IMPORTANCE_TYPES]
    low = [r["absolute_shift"] for r in ok if r["probe_type"] in LOW_IMPORTANCE_TYPES]
    if high and low:
        mean_high = sum(high) / len(high)
        mean_low = sum(low) / len(low)
        ssr = mean_high / mean_low if mean_low > 0.001 else None
    else:
        ssr = None

    # Within-question Kendall tau (importance vs |shift|)
    imp_pairs = [(r["target_importance"], r["absolute_shift"]) for r in ok
                 if r["target_importance"] is not None and r["target_importance"] > 0]
    if len(imp_pairs) >= 3:
        within_tau = _kendall_tau([p[0] for p in imp_pairs], [p[1] for p in imp_pairs])
    else:
        within_tau = None

    # SPP (shortest-path premium)
    on_path = [r["absolute_shift"] for r in ok if r["target_on_critical_path"] is True]
    off_path = [r["absolute_shift"] for r in ok if r["target_on_critical_path"] is False]
    if on_path and off_path:
        spp = sum(on_path) / len(on_path) - sum(off_path) / len(off_path)
    else:
        spp = None

    # Asymmetry index (negate / strengthen)
    neg = [r["absolute_shift"] for r in ok if r["probe_type"] in NEGATE_TYPES]
    stre = [r["absolute_shift"] for r in ok if r["probe_type"] in STRENGTHEN_TYPES]
    if neg and stre:
        mean_neg = sum(neg) / len(neg)
        mean_str = sum(stre) / len(stre)
        asym = mean_neg / mean_str if mean_str > 0.001 else None
    else:
        asym = None

    # Initial probability
    initial_prob = rows[0].get("initial_probability")

    return {
        "initial_prob": initial_prob,
        "abs_dist_from_50": abs(initial_prob - 0.5) if initial_prob is not None else None,
        "mean_shift": round(mean_shift, 6),
        "ssr": round(ssr, 4) if ssr is not None else None,
        "within_tau": round(within_tau, 4) if within_tau is not None else None,
        "spp": round(spp, 6) if spp is not None else None,
        "asymmetry_index": round(asym, 4) if asym is not None else None,
        "n_probes": len(ok),
    }


def main():
    # Load ELO ratings
    elo_path = CAUSAL_DIR / "difficulty_elo.json"
    if not elo_path.exists():
        print("ERROR: Run run_difficulty_elo.py first to generate difficulty_elo.json")
        sys.exit(1)
    elo_data = json.loads(elo_path.read_text(encoding="utf-8"))
    elo_ratings = elo_data["elo_ratings"]
    print(f"Loaded ELO ratings for {len(elo_ratings)} questions")

    # Load reasoning judge ratings
    judge_path = CAUSAL_DIR / "reasoning_judge_ratings.json"
    judge_ratings = {}
    if judge_path.exists():
        judge_ratings = json.loads(judge_path.read_text(encoding="utf-8"))
        print(f"Loaded {len(judge_ratings)} judge ratings")

    # Load uncertainty judge ratings
    unc_judge_path = CAUSAL_DIR / "uncertainty_judge_ratings.json"
    unc_judge_ratings = {}
    if unc_judge_path.exists():
        unc_judge_ratings = json.loads(unc_judge_path.read_text(encoding="utf-8"))
        print(f"Loaded {len(unc_judge_ratings)} uncertainty judge ratings")

    # Load ground truth for Brier scores
    gt_path = CAUSAL_DIR / "ground_truth_resolutions.json"
    freeze_vals = {}
    if gt_path.exists():
        gt_data = json.loads(gt_path.read_text(encoding="utf-8"))
        for qid, entry in gt_data.items():
            val = entry.get("outcome_probability")
            if val is not None:
                freeze_vals[qid] = float(val)
        print(f"Loaded {len(freeze_vals)} ground truth values")

    # Compute inter-model SD of initial probabilities
    all_initial_probs: dict[str, list[float]] = defaultdict(list)
    for model_name, model_dir in MODEL_DIRS.items():
        csv_path = model_dir / "sensitivity_results.csv"
        if not csv_path.exists():
            continue
        rows = load_csv_rows(csv_path)
        by_q = defaultdict(list)
        for r in rows:
            by_q[r["question_id"]].append(r)
        for qid, q_rows in by_q.items():
            ip = q_rows[0].get("initial_probability")
            if ip is not None:
                all_initial_probs[qid].append(ip)

    inter_model_sd = {}
    for qid, probs in all_initial_probs.items():
        if len(probs) >= 2:
            mean_p = sum(probs) / len(probs)
            var_p = sum((p - mean_p) ** 2 for p in probs) / (len(probs) - 1)
            inter_model_sd[qid] = round(math.sqrt(var_p), 6)

    # Build regression dataset
    out_rows = []
    for model_name, model_dir in MODEL_DIRS.items():
        csv_path = model_dir / "sensitivity_results.csv"
        if not csv_path.exists():
            print(f"  Skipping {model_name}: no CSV")
            continue

        rows = load_csv_rows(csv_path)
        by_q = defaultdict(list)
        for r in rows:
            by_q[r["question_id"]].append(r)

        print(f"  {model_name}: {len(by_q)} questions")

        for qid, q_rows in by_q.items():
            if qid not in elo_ratings:
                continue

            metrics = compute_question_metrics(q_rows)
            if metrics is None:
                continue

            # Mean judge rating for this model+question
            judge_vals = []
            for i in range(len(q_rows)):
                key = f"{model_name}|{qid}|{i}"
                jr = judge_ratings.get(key)
                if jr and jr.get("rating") is not None:
                    judge_vals.append(jr["rating"])
            mean_judge = round(sum(judge_vals) / len(judge_vals), 4) if judge_vals else None

            # Mean uncertainty judge rating for this model+question
            unc_vals = []
            for i in range(len(q_rows)):
                key = f"{model_name}|{qid}|{i}"
                ur = unc_judge_ratings.get(key)
                if ur and ur.get("rating") is not None:
                    unc_vals.append(ur["rating"])
            mean_unc = round(sum(unc_vals) / len(unc_vals), 4) if unc_vals else None

            # Brier score
            brier = None
            if qid in freeze_vals and metrics["initial_prob"] is not None:
                brier = round((metrics["initial_prob"] - freeze_vals[qid]) ** 2, 6)

            # Source/category from question text
            source = q_rows[0].get("source", "") if q_rows else ""

            out_rows.append({
                "model": model_name,
                "question_id": qid,
                "elo": elo_ratings[qid],
                "initial_prob": metrics["initial_prob"],
                "abs_dist_from_50": metrics["abs_dist_from_50"],
                "mean_shift": metrics["mean_shift"],
                "ssr": metrics["ssr"],
                "within_tau": metrics["within_tau"],
                "spp": metrics["spp"],
                "asymmetry_index": metrics["asymmetry_index"],
                "mean_judge_rating": mean_judge,
                "mean_uncertainty_rating": mean_unc,
                "inter_model_sd": inter_model_sd.get(qid),
                "n_probes": metrics["n_probes"],
                "brier": brier,
            })

    # Write CSV
    out_path = CAUSAL_DIR / "difficulty_regression_data.csv"
    fieldnames = [
        "model", "question_id", "elo", "initial_prob", "abs_dist_from_50",
        "mean_shift", "ssr", "within_tau", "spp", "asymmetry_index",
        "mean_judge_rating", "mean_uncertainty_rating", "inter_model_sd", "n_probes", "brier",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"\nWrote {len(out_rows)} rows to {out_path}")
    print(f"  Questions with ELO: {len(set(r['question_id'] for r in out_rows))}")
    print(f"  Models: {sorted(set(r['model'] for r in out_rows))}")


if __name__ == "__main__":
    main()
