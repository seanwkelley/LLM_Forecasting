"""Resolve questions by pulling ForecastBench's own resolution sets.

ForecastBench publishes resolution sets nightly at
    https://github.com/forecastingresearch/forecastbench-datasets
        /tree/main/datasets/resolution_sets

Each file (e.g. ``2026-04-12_resolution_set.json``) contains one entry per
(question_id, resolution_date) pair with the ground-truth ``resolved_to``
(binary 0.0 or 1.0).  We match our question instances to these entries by
``(id_orig, resolution_date)``.

No external data-source API calls, no question-text regex parsing — we trust
ForecastBench's own resolution logic, which is maintained by their team and
resolves all 500 questions consistently.

Notes on timing:
  - Resolutions appear 1-2 days after each resolution_date (subject to
    source data lag; FRED monthly series can take weeks).
  - Re-run ``resolve`` periodically until everything you care about is filled.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime
from pathlib import Path

from forecast_bench.agent_forecast.config import OUT_DIR, TODAY


RESOLUTIONS_CACHE = OUT_DIR / "resolutions.json"
RESOLUTION_SETS_DIR = OUT_DIR / "forecastbench_snapshots" / "resolution_sets"
DATASETS_REPO_RAW = (
    "https://raw.githubusercontent.com/forecastingresearch/forecastbench-datasets/"
    "main/datasets/resolution_sets"
)


# ── Download resolution sets ──────────────────────────────────────────────

def _list_remote_resolution_sets() -> list[str]:
    """Return filenames of every resolution set file on GitHub."""
    url = ("https://api.github.com/repos/forecastingresearch/forecastbench-datasets/"
           "contents/datasets/resolution_sets")
    req = urllib.request.Request(
        url, headers={"User-Agent": "forecastbench-agent-forecast"})
    with urllib.request.urlopen(req, timeout=20) as r:
        items = json.loads(r.read())
    names = [i["name"] for i in items
             if i["type"] == "file" and i["name"].endswith("_resolution_set.json")]
    names.sort()
    return names


def download_resolution_set(question_set_name: str,
                             dest_dir: Path = RESOLUTION_SETS_DIR,
                             force: bool = False) -> Path | None:
    """Download the resolution set matching a question-set filename.

    Maps e.g. ``2026-04-12-llm.json`` -> ``2026-04-12_resolution_set.json``.

    Returns the local path or None if the resolution set hasn't been
    published yet (or download failed).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    # 2026-04-12-llm.json -> 2026-04-12
    stem = question_set_name.replace("-llm.json", "")
    res_name = f"{stem}_resolution_set.json"
    dest = dest_dir / res_name
    if dest.exists() and not force:
        return dest
    url = f"{DATASETS_REPO_RAW}/{res_name}"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            dest.write_bytes(r.read())
        print(f"Downloaded {res_name}")
        return dest
    except Exception as e:
        print(f"[resolve] could not fetch {res_name}: {e}")
        return None


# ── Match and cache ───────────────────────────────────────────────────────

def _build_index(resolution_path: Path) -> dict[tuple[str, str], dict]:
    """Return a dict keyed by (id, resolution_date) -> resolution entry."""
    d = json.loads(resolution_path.read_text(encoding="utf-8"))
    entries = d.get("resolutions", d if isinstance(d, list) else [])
    index = {}
    for e in entries:
        key = (e["id"], e["resolution_date"])
        index[key] = e
    return index


def resolve_all(questions: list[dict], refresh: bool = False,
                 download: bool = True) -> dict[str, dict]:
    """Match each question instance to its ForecastBench resolution entry.

    If ``download`` is True, pulls the latest resolution sets from GitHub
    (one per question_set referenced in the input).  If ``refresh`` is True,
    re-downloads and re-indexes even if cached.
    """
    cache = {}
    if RESOLUTIONS_CACHE.exists() and not refresh:
        cache = json.loads(RESOLUTIONS_CACHE.read_text(encoding="utf-8"))

    # Group questions by question_set so we fetch each resolution file once
    by_set: dict[str, list] = {}
    for q in questions:
        by_set.setdefault(q["question_set"], []).append(q)

    for qset, items in by_set.items():
        res_path = None
        if download:
            res_path = download_resolution_set(qset, force=refresh)
        if res_path is None:
            # Fall back to whatever local file we have
            stem = qset.replace("-llm.json", "")
            candidate = RESOLUTION_SETS_DIR / f"{stem}_resolution_set.json"
            if candidate.exists():
                res_path = candidate
        if res_path is None:
            for q in items:
                cache.setdefault(q["id"], {"resolved": False,
                                            "reason": "no_resolution_set"})
            continue

        index = _build_index(res_path)
        for q in items:
            if q["id"] in cache and cache[q["id"]].get("resolved"):
                continue
            key = (q["id_orig"], q["resolution_date"])
            entry = index.get(key)
            if entry is None:
                cache[q["id"]] = {
                    "resolved": False,
                    "reason": "not_yet_in_resolution_set",
                    "resolution_date": q["resolution_date"],
                }
                continue
            cache[q["id"]] = {
                "resolved": bool(entry.get("resolved", False)),
                "outcome": float(entry["resolved_to"])
                           if entry.get("resolved_to") is not None else None,
                "direction": entry.get("direction"),
                "resolution_date": entry["resolution_date"],
                "source": entry.get("source"),
                "resolver": "forecastbench",
            }

    RESOLUTIONS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    RESOLUTIONS_CACHE.write_text(json.dumps(cache, indent=2, default=str),
                                  encoding="utf-8")
    return cache
