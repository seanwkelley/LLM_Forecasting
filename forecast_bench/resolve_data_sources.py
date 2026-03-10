"""
Resolve data source questions from ForecastBench.

Fetches actual values at resolution_date (2025-12-28) from public APIs
and computes binary outcomes (1 = condition met, 0 = not met).

Sources:
- FRED: CSV endpoint (no API key needed)
- Yahoo Finance: chart API
- DBnomics: public API
- ACLED: manual resolution from freeze values
- Wikipedia: manual resolution

Output: JSON mapping question_id -> {outcome: 0|1, source, freeze_value, resolution_value, ...}
"""

from __future__ import annotations

import datetime
import json
import os
import requests
import sys


RESOLUTION_DATE = "2025-12-28"
FORECAST_DUE_DATE = "2025-12-21"

# For markets closed on weekends, use the closest prior trading day
# Dec 28, 2025 is a Sunday -> use Dec 26 (Friday)
TRADING_RESOLUTION_DATE = "2025-12-26"


def _get_fred_value(series_id: str, date: str = TRADING_RESOLUTION_DATE) -> float | None:
    """Fetch FRED series value near the resolution date."""
    url = (
        f"https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}&cosd=2025-12-15&coed=2025-12-31"
    )
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        return None

    # Parse CSV, find closest non-empty value to resolution date
    lines = r.text.strip().split("\n")
    best_date = None
    best_val = None
    target = datetime.date.fromisoformat(date)

    for line in lines[1:]:  # skip header
        parts = line.split(",")
        if len(parts) < 2 or not parts[1].strip():
            continue
        try:
            d = datetime.date.fromisoformat(parts[0].strip())
            v = float(parts[1].strip())
        except (ValueError, IndexError):
            continue
        # Find value closest to (but not after) resolution date
        if d <= target:
            if best_date is None or d > best_date:
                best_date = d
                best_val = v
        # Also accept values up to 3 days after if nothing before
        elif d <= target + datetime.timedelta(days=3):
            if best_date is None:
                best_date = d
                best_val = v

    return best_val


def _get_yahoo_price(ticker: str) -> float | None:
    """Fetch Yahoo Finance closing price near resolution date."""
    # Dec 22 to Jan 2
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1=1766361600&period2=1767312000&interval=1d"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        return None

    data = r.json()
    result = data["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]

    target = datetime.date(2025, 12, 26)  # Friday before Sunday Dec 28
    best_date = None
    best_val = None

    for ts, c in zip(timestamps, closes):
        dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).date()
        if dt <= target:
            if best_date is None or dt > best_date:
                best_date = dt
                best_val = c

    return best_val


def _get_dbnomics_temp(station_code: str) -> float | None:
    """Fetch temperature from DBnomics for a given station on resolution date."""
    series_id = f"celsius.{station_code}.D"
    url = (
        f"https://api.db.nomics.world/v22/series/meteofrance/TEMPERATURE/{series_id}"
        f"?observations=1"
    )
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        return None

    data = r.json()
    docs = data.get("series", {}).get("docs", [])
    if not docs:
        return None

    doc = docs[0]
    periods = doc.get("period", [])
    values = doc.get("value", [])

    # Find Dec 28, 2025
    target = RESOLUTION_DATE
    for p, v in zip(periods, values):
        if p == target:
            if v == "NA" or v is None:
                return None
            return float(v)

    # If exact date not found, try adjacent dates
    for offset in [1, -1, 2, -2]:
        d = datetime.date.fromisoformat(target) + datetime.timedelta(days=offset)
        ds = d.isoformat()
        for p, v in zip(periods, values):
            if p == ds and v != "NA" and v is not None:
                return float(v)

    return None


def resolve_all(questions_path: str, output_dir: str) -> dict:
    """Resolve all data source questions and return outcomes."""
    with open(questions_path) as f:
        qdata = json.load(f)

    # Get used question IDs
    used_ids = set()
    for d in ["70b_one_turn", "llama_one_turn", "deepseek_one_turn"]:
        qdir = os.path.join(output_dir, d, "question_results")
        if not os.path.exists(qdir):
            continue
        for fn in os.listdir(qdir):
            if fn.endswith(".json"):
                with open(os.path.join(qdir, fn)) as qf:
                    q = json.load(qf)
                    used_ids.add(q.get("question_id", ""))

    prob_sources = {"metaculus", "manifold", "polymarket", "infer"}
    results = {}

    for q in qdata["questions"]:
        qid = q["id"]
        if qid not in used_ids:
            continue

        source = q.get("source", "")
        freeze_val = q.get("freeze_datetime_value")
        question_text = q.get("question", "")

        if source in prob_sources:
            # Already have probability-based ground truth
            try:
                fv = float(freeze_val)
                if 0.0 <= fv <= 1.0:
                    results[qid] = {
                        "source": source,
                        "outcome_probability": fv,
                        "type": "prediction_market",
                    }
            except (ValueError, TypeError):
                pass
            continue

        # Data source questions - need to resolve
        outcome = None
        resolution_value = None
        method = None

        if source == "fred":
            series_id = qid  # FRED question IDs are the series IDs
            resolution_value = _get_fred_value(series_id)
            if resolution_value is not None:
                try:
                    fv_float = float(freeze_val)
                    # "Will X have increased?" -> resolution = 1 if increased
                    outcome = 1 if resolution_value > fv_float else 0
                    method = f"FRED CSV: {series_id} freeze={fv_float:.4f} res={resolution_value:.4f}"
                except (ValueError, TypeError):
                    pass

        elif source == "yfinance":
            ticker = qid  # yfinance question IDs are ticker symbols
            resolution_value = _get_yahoo_price(ticker)
            if resolution_value is not None:
                try:
                    fv_float = float(freeze_val)
                    outcome = 1 if resolution_value > fv_float else 0
                    method = f"Yahoo Finance: {ticker} freeze={fv_float:.2f} res={resolution_value:.2f}"
                except (ValueError, TypeError):
                    pass

        elif source == "dbnomics":
            # Extract station code from ID: meteofrance_TEMPERATURE_celsius.XXXXX.D
            parts = qid.split(".")
            if len(parts) >= 2:
                station_code = parts[-2]  # e.g., "07481"
                # Actually the format is meteofrance_TEMPERATURE_celsius.07481.D
                # So station code is parts[1] if we split by "."
                # Let's parse more carefully
                if "celsius." in qid:
                    station_code = qid.split("celsius.")[1].split(".")[0]
                resolution_value = _get_dbnomics_temp(station_code)
                if resolution_value is not None:
                    try:
                        fv_float = float(freeze_val)
                        # "Will temperature be higher on resolution_date than forecast_due_date?"
                        # freeze_val is the temperature on forecast_due_date
                        outcome = 1 if resolution_value > fv_float else 0
                        method = f"DBnomics: station {station_code} freeze={fv_float:.3f} res={resolution_value:.3f}"
                    except (ValueError, TypeError):
                        pass

        elif source == "wikipedia":
            # Manual resolution for known question types
            if "vaccine" in question_text.lower() and "hepatitis c" in question_text.lower():
                outcome = 0  # No Hepatitis C vaccine by Dec 2025
                method = "Manual: No Hep C vaccine developed by Dec 2025"
            elif "vaccine" in question_text.lower() and "marburg" in question_text.lower():
                outcome = 0  # No Marburg vaccine by Dec 2025
                method = "Manual: No Marburg vaccine developed by Dec 2025"
            elif "world record" in question_text.lower() and "rtens" in question_text.lower():
                # Lukas Märtens 400m freestyle record - he set it in 2024, still holds
                outcome = 1  # Still holds the record
                method = "Manual: Märtens still holds 400m freestyle WR as of Dec 2025"
            elif "elo rating" in question_text.lower() and "dom" in question_text.lower():
                # Leinier Dominguez Elo rating - need 1% increase from 2738 (>= 2765.38)
                # Per chess-rankings.com: rating stayed at 2738 through Jan 2026
                outcome = 0  # No 1% increase
                method = "Manual: Dominguez Elo stayed at 2738 (needed 2765+ for 1% increase)"

        elif source == "acled":
            # ACLED questions have freeze_value as the baseline comparison
            # These require event count data - harder to resolve
            # The freeze_values are 0 or 1 (the baseline counts)
            outcome = None
            method = "Skipped: ACLED event data not easily accessible"

        if outcome is not None:
            results[qid] = {
                "source": source,
                "outcome_probability": float(outcome),
                "resolution_value": resolution_value,
                "freeze_value": freeze_val,
                "method": method,
                "type": "resolved_data_source",
            }
        elif method:
            print(f"  SKIP {source}/{qid[:20]}: {method}")

    return results


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    questions_path = os.path.join(base, "forecastbench_questions.json")
    output_dir = os.path.join(os.path.dirname(base), "outputs", "sensitivity", "causal")

    print("Resolving data source questions...")
    results = resolve_all(questions_path, output_dir)

    # Separate by type
    pm_count = sum(1 for r in results.values() if r["type"] == "prediction_market")
    ds_count = sum(1 for r in results.values() if r["type"] == "resolved_data_source")

    print(f"\nResolved: {pm_count} prediction market + {ds_count} data source = {len(results)} total")

    print("\nData source resolutions:")
    for qid, r in sorted(results.items()):
        if r["type"] == "resolved_data_source":
            print(f"  {r['source']:10s} | outcome={r['outcome_probability']:.0f} | {r['method']}")

    # Save
    out_path = os.path.join(output_dir, "ground_truth_resolutions.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {out_path}")

    return results


if __name__ == "__main__":
    main()
