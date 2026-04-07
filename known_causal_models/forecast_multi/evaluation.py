"""
Evaluation Metrics — shared scoring functions for the forecasting framework.

Factored out from market/run_market_forecast.py and conflict/run_conflict_forecast.py.
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Classification metrics
# ---------------------------------------------------------------------------

def brier_score(forecast: dict, actual: str) -> float:
    """Compute Brier score for a three-class forecast.

    Brier = sum((predicted_prob - actual_indicator)^2) for each class.
    Lower is better. Perfect = 0, uniform baseline = 0.667.
    """
    actual_vec = {
        "UP":   [1, 0, 0],
        "DOWN": [0, 1, 0],
        "FLAT": [0, 0, 1],
    }[actual]
    pred = [forecast["prob_up"], forecast["prob_down"], forecast["prob_flat"]]
    return sum((p - a) ** 2 for p, a in zip(pred, actual_vec))


def log_score(forecast: dict, actual: str) -> float:
    """Compute log score (negative log probability of actual outcome).

    Lower is better. Perfect = 0, uniform baseline = 1.099.
    """
    prob_map = {"UP": "prob_up", "DOWN": "prob_down", "FLAT": "prob_flat"}
    prob = max(forecast[prob_map[actual]], 1e-6)  # clip to avoid log(0)
    return -np.log(prob)


def compute_f1(
    rows: list[dict],
    classes: tuple[str, ...] = ("UP", "DOWN", "FLAT"),
) -> dict:
    """Compute per-class and macro F1 from forecast rows.

    Each row must have 'pred_class' and 'actual' keys.
    """
    results = {}
    f1s = []
    for cls in classes:
        tp = sum(1 for r in rows if r["pred_class"] == cls and r["actual"] == cls)
        fp = sum(1 for r in rows if r["pred_class"] == cls and r["actual"] != cls)
        fn = sum(1 for r in rows if r["pred_class"] != cls and r["actual"] == cls)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        results[cls] = {"precision": precision, "recall": recall, "f1": f1}
        f1s.append(f1)
    results["macro_f1"] = float(np.mean(f1s))
    return results


def pred_class_from_probs(forecast: dict) -> str:
    """Return the predicted class (UP/DOWN/FLAT) from highest probability."""
    return max(
        [("UP", forecast["prob_up"]),
         ("DOWN", forecast["prob_down"]),
         ("FLAT", forecast["prob_flat"])],
        key=lambda x: x[1],
    )[0]


# ---------------------------------------------------------------------------
# Baseline forecasters
# ---------------------------------------------------------------------------

def compute_baselines(rows: list[dict]) -> dict:
    """Compute baseline Brier/log scores for comparison.

    Baselines:
    - uniform: 1/3 each class
    - majority: 100% on the most common class
    - frequency: class distribution as probabilities
    - persistence: 100% on the previous period's direction
    """
    if not rows:
        return {}

    actuals = [r["actual"] for r in rows]
    n = len(actuals)
    counts = {c: actuals.count(c) for c in ("UP", "DOWN", "FLAT")}

    # Uniform: always predict 1/3 each
    uniform_forecast = {"prob_up": 1/3, "prob_down": 1/3, "prob_flat": 1/3}
    uniform_brier = np.mean([brier_score(uniform_forecast, a) for a in actuals])
    uniform_log = np.mean([log_score(uniform_forecast, a) for a in actuals])

    # Majority: always predict the most common class
    majority_class = max(counts, key=counts.get)
    majority_forecast = {
        "prob_up": 1.0 if majority_class == "UP" else 0.0,
        "prob_down": 1.0 if majority_class == "DOWN" else 0.0,
        "prob_flat": 1.0 if majority_class == "FLAT" else 0.0,
    }
    majority_brier = np.mean([brier_score(majority_forecast, a) for a in actuals])
    majority_log = np.mean([log_score(majority_forecast, a) for a in actuals])

    # Frequency: predict class distribution
    freq_forecast = {
        "prob_up": counts["UP"] / n,
        "prob_down": counts["DOWN"] / n,
        "prob_flat": counts["FLAT"] / n,
    }
    freq_brier = np.mean([brier_score(freq_forecast, a) for a in actuals])
    freq_log = np.mean([log_score(freq_forecast, a) for a in actuals])

    return {
        "class_distribution": {k: round(v / n, 3) for k, v in counts.items()},
        "uniform": {"brier": round(float(uniform_brier), 4), "log": round(float(uniform_log), 4)},
        "majority": {
            "class": majority_class,
            "brier": round(float(majority_brier), 4),
            "log": round(float(majority_log), 4),
        },
        "frequency": {"brier": round(float(freq_brier), 4), "log": round(float(freq_log), 4)},
    }


# ---------------------------------------------------------------------------
# Ensemble aggregation
# ---------------------------------------------------------------------------

def ensemble_forecasts(forecasts: list[dict]) -> dict:
    """Average probabilities and point estimates across forecasts.

    Each forecast dict must have prob_up, prob_down, prob_flat.
    May optionally have a point estimate key (predicted_price or predicted_ei).
    """
    if not forecasts:
        return {}

    avg_up = np.mean([f["prob_up"] for f in forecasts])
    avg_down = np.mean([f["prob_down"] for f in forecasts])
    avg_flat = np.mean([f["prob_flat"] for f in forecasts])

    result = {
        "prob_up": round(float(avg_up), 4),
        "prob_down": round(float(avg_down), 4),
        "prob_flat": round(float(avg_flat), 4),
        "reasoning": "Ensemble average",
    }

    # Average point estimates if available
    for key in ("predicted_price", "predicted_ei"):
        vals = [f[key] for f in forecasts if key in f and f[key] is not None]
        if vals:
            result[key] = round(float(np.mean(vals)), 4)

    return result
