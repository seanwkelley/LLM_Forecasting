"""
ForecastBench Question Loader -- Load binary forecasting questions.

Supports three sources (tried in order):
1. Local JSON file via --questions-file CLI arg
2. Bundled forecastbench_questions.json (downloaded from HuggingFace)
3. Direct fetch from HuggingFace repo (forecastingresearch/forecastbench-datasets)
4. Built-in sample questions (10 generic binary questions)

ForecastBench questions are all binary (probability 0-1). They come from
prediction markets (Manifold, Metaculus, Polymarket, INFER) and data
sources (ACLED, FRED, Wikipedia, Yahoo Finance, DBnomics).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

# HuggingFace repo for ForecastBench question sets
FORECASTBENCH_REPO = "forecastingresearch/forecastbench-datasets"
FORECASTBENCH_QUESTION_SET = "2025-12-21-llm.json"
FORECASTBENCH_URL = (
    f"https://huggingface.co/datasets/{FORECASTBENCH_REPO}"
    f"/resolve/main/datasets/question_sets/{FORECASTBENCH_QUESTION_SET}"
)

# Local bundled copy (relative to this file)
BUNDLED_PATH = Path(__file__).parent / "forecastbench_questions.json"


def load_forecastbench_questions(
    max_questions: int = 100,
    seed: int = 42,
    questions_file: str | None = None,
) -> list[dict]:
    """Load binary forecasting questions from ForecastBench.

    Each returned question is a dict with at least:
        - id: str
        - question: str
        - source: str (origin dataset/category)

    Parameters
    ----------
    max_questions : int
        Maximum number of questions to return.
    seed : int
        Random seed for reproducible subset selection.
    questions_file : str or None
        Path to local JSON file. If provided, skips other sources.

    Returns
    -------
    List of question dicts.
    """
    if questions_file:
        return _load_from_file(questions_file, max_questions, seed)

    # Try bundled local file first
    if BUNDLED_PATH.exists():
        questions = _load_forecastbench_json(BUNDLED_PATH)
        if questions:
            print(f"[INFO] Loaded {len(questions)} questions from bundled ForecastBench file")
            return _filter_and_sample(questions, max_questions, seed)

    # Try fetching from HuggingFace
    questions = _fetch_from_huggingface()
    if questions:
        return _filter_and_sample(questions, max_questions, seed)

    print("[WARNING] Could not load ForecastBench. Using built-in sample questions.")
    return _builtin_sample_questions(max_questions, seed)


def _load_from_file(path: str, max_questions: int, seed: int) -> list[dict]:
    """Load questions from a local JSON file."""
    file_path = Path(path)
    data = json.loads(file_path.read_text(encoding="utf-8"))

    # Support ForecastBench format {"questions": [...]} and plain list
    if isinstance(data, dict) and "questions" in data:
        raw = data["questions"]
    elif isinstance(data, list):
        raw = data
    else:
        raw = [data]

    questions = _parse_questions(raw)
    print(f"[INFO] Loaded {len(questions)} questions from {path}")
    return _filter_and_sample(questions, max_questions, seed)


def _load_forecastbench_json(path: Path) -> list[dict] | None:
    """Load questions from a ForecastBench-format JSON file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        forecast_due_date = data.get("forecast_due_date", "") if isinstance(data, dict) else ""
        raw = data.get("questions", []) if isinstance(data, dict) else data
        return _parse_questions(raw, forecast_due_date)
    except Exception as e:
        print(f"[INFO] Failed to load {path}: {e}")
        return None


def _fetch_from_huggingface() -> list[dict] | None:
    """Fetch latest question set directly from HuggingFace."""
    try:
        import requests

        print(f"[INFO] Fetching ForecastBench questions from HuggingFace...")
        resp = requests.get(FORECASTBENCH_URL, timeout=60)
        if resp.status_code != 200:
            print(f"[INFO] HuggingFace fetch failed: HTTP {resp.status_code}")
            return None

        data = resp.json()
        forecast_due_date = data.get("forecast_due_date", "") if isinstance(data, dict) else ""
        raw = data.get("questions", []) if isinstance(data, dict) else data
        questions = _parse_questions(raw, forecast_due_date)

        if questions:
            # Cache locally for next time
            try:
                BUNDLED_PATH.write_text(resp.text, encoding="utf-8")
                print(f"[INFO] Cached {len(questions)} questions to {BUNDLED_PATH}")
            except Exception:
                pass

        print(f"[INFO] Loaded {len(questions)} questions from HuggingFace")
        return questions

    except Exception as e:
        print(f"[INFO] HuggingFace fetch failed: {e}")
        return None


def _parse_questions(raw: list[dict], forecast_due_date: str = "") -> list[dict]:
    """Parse raw ForecastBench question dicts into standardized format.

    All ForecastBench questions are binary (probability 0-1), so no
    filtering by question type is needed. Template placeholders like
    {resolution_date} and {forecast_due_date} are filled in.
    """
    questions = []
    for i, item in enumerate(raw):
        q_text = item.get("question", item.get("text", ""))
        if not q_text or not q_text.strip():
            continue

        # Fill in template placeholders
        q_text = _fill_template(q_text, item, forecast_due_date)

        questions.append({
            "id": item.get("id", f"fb_{i}"),
            "question": q_text.strip(),
            "source": item.get("source", "forecastbench"),
            "background": item.get("background", ""),
            "resolution_criteria": item.get("resolution_criteria", ""),
            "url": item.get("url", ""),
        })

    return questions


def _fill_template(q_text: str, item: dict, forecast_due_date: str) -> str:
    """Fill ForecastBench template placeholders in question text.

    Data-source questions (ACLED, FRED, etc.) contain {resolution_date}
    and {forecast_due_date} placeholders that must be resolved.
    """
    if "{" not in q_text:
        return q_text

    # Pick the earliest resolution date (shortest horizon)
    resolution_dates = item.get("resolution_dates", [])
    resolution_date = resolution_dates[0] if resolution_dates else ""

    q_text = q_text.replace("{resolution_date}", resolution_date)
    q_text = q_text.replace("{forecast_due_date}", forecast_due_date)

    return q_text


def _filter_and_sample(
    questions: list[dict],
    max_questions: int,
    seed: int,
    _original_n: int = 51,
) -> list[dict]:
    """Filter valid questions and take a random subset.

    Uses a two-stage selection to maintain backwards compatibility:
    the first ``_original_n`` questions are chosen with
    ``rng.sample(seed)``, matching the original data-collection runs.
    Any additional questions beyond that are drawn from the remaining
    pool with ``seed + 1``, so increasing ``max_questions`` only *adds*
    new questions without changing the existing set.
    """
    # Remove questions with empty text
    questions = [q for q in questions if q.get("question", "").strip()]

    if len(questions) <= max_questions:
        return questions

    # Stage 1 — original selection (backwards compatible)
    n_first = min(_original_n, max_questions)
    rng = random.Random(seed)
    first_batch = rng.sample(questions, n_first)

    if max_questions <= _original_n:
        return first_batch

    # Stage 2 — additional questions from the remainder
    first_ids = {q.get("id") for q in first_batch}
    remaining = [q for q in questions if q.get("id") not in first_ids]
    n_extra = min(max_questions - n_first, len(remaining))
    rng2 = random.Random(seed + 1)
    extra = rng2.sample(remaining, n_extra)

    return first_batch + extra


def _builtin_sample_questions(max_questions: int, seed: int) -> list[dict]:
    """Built-in sample binary questions for testing when ForecastBench is unavailable."""
    samples = [
        {
            "id": "sample_01",
            "question": "Will the US Federal Reserve raise interest rates at its next meeting?",
            "source": "sample",
        },
        {
            "id": "sample_02",
            "question": "Will global oil prices exceed $100 per barrel by the end of the quarter?",
            "source": "sample",
        },
        {
            "id": "sample_03",
            "question": "Will the S&P 500 index close above 5000 by the end of the month?",
            "source": "sample",
        },
        {
            "id": "sample_04",
            "question": "Will there be a major cybersecurity breach affecting more than 10 million users this quarter?",
            "source": "sample",
        },
        {
            "id": "sample_05",
            "question": "Will the European Central Bank cut interest rates at its next policy meeting?",
            "source": "sample",
        },
        {
            "id": "sample_06",
            "question": "Will China's GDP growth rate exceed 5% for the current fiscal year?",
            "source": "sample",
        },
        {
            "id": "sample_07",
            "question": "Will there be a new UN Security Council resolution on climate change this year?",
            "source": "sample",
        },
        {
            "id": "sample_08",
            "question": "Will global semiconductor chip shortages ease significantly in the next 6 months?",
            "source": "sample",
        },
        {
            "id": "sample_09",
            "question": "Will the US unemployment rate fall below 3.5% this quarter?",
            "source": "sample",
        },
        {
            "id": "sample_10",
            "question": "Will Bitcoin's price exceed $100,000 by the end of the year?",
            "source": "sample",
        },
    ]
    return _filter_and_sample(samples, max_questions, seed)
