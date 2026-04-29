"""Pull the latest ForecastBench question set and instantiate it for the
agent-forecast experiment.

Real schema (datasets repo, e.g., 2026-04-12-llm.json):

    {
      "forecast_due_date": "2026-04-12",
      "question_set": "2026-04-12-llm.json",
      "questions": [
        {
          "id": "SO",
          "source": "yfinance",
          "question": "Will SO's market close price on {resolution_date} be higher than its market close price on {forecast_due_date}?\\n\\nStock s...",
          "resolution_criteria": "...",
          "background": "...",
          "freeze_datetime": "2026-04-02T00:00:00+00:00",
          "freeze_datetime_value": "96.94",
          "freeze_datetime_value_explanation": "The market value.",
          "source_intro": "...",
          "resolution_dates": ["2026-04-19", "2026-05-12", "2026-07-11", ...],
          "url": "..."
        },
        ...
      ]
    }

Each data-source question has multiple resolution horizons (7d, 30d, 90d, 180d,
1y, 3y, 5y, 10y from the forecast_due_date).  We pick one horizon (default
30 days) and instantiate the template by substituting `{resolution_date}` and
`{forecast_due_date}`.

Prediction-market sources (manifold, metaculus, polymarket, infer) are
excluded by default — the freeze_datetime_value leaks the market consensus.
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import date, datetime
from pathlib import Path

from forecast_bench.agent_forecast.config import (
    BASE, ELIGIBLE_SOURCES, OUT_DIR, TODAY,
)


SNAPSHOTS_DIR = OUT_DIR / "forecastbench_snapshots"
DATASETS_REPO_RAW = (
    "https://raw.githubusercontent.com/forecastingresearch/forecastbench-datasets/"
    "main/datasets/question_sets"
)


# ── Download ───────────────────────────────────────────────────────────────

def _list_remote_question_sets() -> list[str]:
    """Return the list of question-set filenames from the GitHub API."""
    import json as _json
    url = ("https://api.github.com/repos/forecastingresearch/forecastbench-datasets/"
           "contents/datasets/question_sets")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "forecastbench-agent-forecast"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        items = _json.loads(r.read())
    names = [i["name"] for i in items
             if i["type"] == "file" and i["name"].endswith("-llm.json")
             and i["name"] != "latest-llm.json"]
    names.sort()  # chronological: older first, latest last
    return names


def download_latest(dest_dir: Path = SNAPSHOTS_DIR) -> Path:
    """Fetch the most recent dated question set into `dest_dir` and return its path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    names = _list_remote_question_sets()
    if not names:
        raise RuntimeError("No question sets found in forecastbench-datasets")
    latest = names[-1]
    dest = dest_dir / latest
    if dest.exists():
        print(f"Already have {latest}")
        return dest
    url = f"{DATASETS_REPO_RAW}/{latest}"
    print(f"Downloading {latest} ...")
    with urllib.request.urlopen(url, timeout=60) as r:
        dest.write_bytes(r.read())
    print(f"Saved to {dest}")
    return dest


def latest_local_snapshot(dir_: Path = SNAPSHOTS_DIR) -> Path | None:
    if not dir_.exists():
        return None
    snaps = sorted(dir_.glob("*-llm.json"))
    return snaps[-1] if snaps else None


# ── Load + instantiate ─────────────────────────────────────────────────────

def _pick_horizon(resolution_dates: list[str],
                   min_days: int, max_days: int,
                   today: date = TODAY) -> str | None:
    """Pick the first resolution date inside [today+min_days, today+max_days]."""
    for s in resolution_dates:
        try:
            d = datetime.fromisoformat(s).date()
        except ValueError:
            continue
        delta = (d - today).days
        if min_days <= delta <= max_days:
            return s
    return None


def _instantiate(text: str, forecast_due_date: str, resolution_date: str) -> str:
    return (text
            .replace("{forecast_due_date}", forecast_due_date)
            .replace("{resolution_date}", resolution_date))


def load_eligible_questions(
    path: Path | None = None,
    sources: set[str] = ELIGIBLE_SOURCES,
    min_days: int = 14,
    max_days: int = 56,
    max_questions: int | None = None,
) -> list[dict]:
    """Load the latest snapshot and return one instance per eligible question.

    Each returned instance has:
        id_full         : "{orig_id}@{resolution_date}"
        id_orig         : original question id
        source          : source name
        resolution_date : ISO date string for the chosen horizon
        forecast_due_date, freeze_datetime, freeze_datetime_value : passthrough
        question_raw    : original text with placeholders
        question        : instantiated text (placeholders replaced)
        horizon_days    : days from forecast_due_date to resolution_date
        raw             : the full original record for reference
    """
    if path is None:
        path = latest_local_snapshot() or download_latest()
    data = json.loads(path.read_text(encoding="utf-8"))
    fdd = data["forecast_due_date"]
    qs = data["questions"]

    instances = []
    for q in qs:
        src = (q.get("source") or "").lower()
        if src not in sources:
            continue
        res_dates = q.get("resolution_dates")
        if not isinstance(res_dates, list):
            continue
        chosen = _pick_horizon(res_dates, min_days, max_days)
        if chosen is None:
            continue
        horizon_days = (datetime.fromisoformat(chosen).date()
                        - datetime.fromisoformat(fdd).date()).days
        instance_id = f"{q['id']}@{chosen}"
        instances.append({
            "id_full": instance_id,
            "id": instance_id,  # primary id the rest of the pipeline uses
            "id_orig": q["id"],
            "source": src,
            "question_set": data.get("question_set"),
            "forecast_due_date": fdd,
            "freeze_datetime": q.get("freeze_datetime"),
            "freeze_datetime_value": q.get("freeze_datetime_value"),
            "freeze_datetime_value_explanation":
                q.get("freeze_datetime_value_explanation"),
            "resolution_date": chosen,
            "horizon_days": horizon_days,
            "question_raw": q["question"],
            "question": _instantiate(q["question"], fdd, chosen),
            "resolution_criteria": _instantiate(
                q.get("resolution_criteria", ""), fdd, chosen),
            "background": q.get("background", ""),
            "url": q.get("url"),
            "raw": q,
        })

    if max_questions is not None and len(instances) > max_questions:
        # Sample deterministically by source, stratified
        import random
        by_src: dict[str, list] = {}
        for ins in instances:
            by_src.setdefault(ins["source"], []).append(ins)
        per_src = max_questions // max(len(by_src), 1)
        picked = []
        rng = random.Random(42)
        for s, lst in by_src.items():
            lst_sorted = sorted(lst, key=lambda x: x["id_full"])
            picked.extend(rng.sample(lst_sorted, min(per_src, len(lst_sorted))))
        instances = picked[:max_questions]

    return instances


def save_selection(instances: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Don't serialize the raw field for readability
    to_save = [{k: v for k, v in i.items() if k != "raw"} for i in instances]
    out_path.write_text(json.dumps(to_save, indent=2, default=str),
                        encoding="utf-8")
    print(f"Saved {len(instances)} eligible question instances to {out_path}")
