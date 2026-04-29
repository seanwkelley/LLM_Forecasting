"""Orchestrator for the agent-forecast experiment.

Steps:
  1. Fetch eligible ForecastBench questions (future-resolving).
  2. For each question x model x condition, run the pipeline and append the
     trial result to trials.jsonl.
  3. Periodically (after resolution dates pass), call --resolve to populate
     ground-truth outcomes.
  4. Call --score to merge trials with resolutions, compute Brier, and print
     the per-condition and paired-test summary.

Usage:
    # One-time: drop a fresh ForecastBench snapshot at
    #   outputs/forecastbench_snapshots/questions_YYYY-MM-DD.json

    python -m forecast_bench.agent_forecast.run_experiment --select
    python -m forecast_bench.agent_forecast.run_experiment --run
    # ... wait for resolutions ...
    python -m forecast_bench.agent_forecast.run_experiment --resolve
    python -m forecast_bench.agent_forecast.run_experiment --score
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from forecast_bench.agent_forecast.config import (
    CONDITIONS, MODELS, OUT_DIR, get_openrouter_key,
)
from forecast_bench.agent_forecast.fetch_questions import (
    load_eligible_questions, save_selection,
)
from forecast_bench.agent_forecast.pipeline import run_trial
from forecast_bench.agent_forecast.resolution import resolve_all
from forecast_bench.agent_forecast.search_tool import SearchTool
from forecast_bench.llm_client import LLMClient


SELECTION_PATH = OUT_DIR / "selected_questions.json"
TRIALS_PATH = OUT_DIR / "trials.jsonl"
LOG_PATH = OUT_DIR / "run.log"


# ── Step 1: select questions ───────────────────────────────────────────────

def cmd_select(args) -> None:
    if args.download:
        from forecast_bench.agent_forecast.fetch_questions import download_latest
        download_latest()
    max_q = None if args.all else args.max_n
    questions = load_eligible_questions(
        min_days=args.min_days, max_days=args.max_days,
        max_questions=max_q)
    print(f"Selected {len(questions)} question instances at horizon "
          f"{args.min_days}-{args.max_days} days.")
    save_selection(questions, SELECTION_PATH)


# ── Step 2: run trials ─────────────────────────────────────────────────────

def _append_trial(result) -> None:
    TRIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRIALS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result.to_dict(), default=str) + "\n")


def _already_run() -> set[tuple[str, str, str]]:
    done = set()
    if not TRIALS_PATH.exists():
        return done
    with TRIALS_PATH.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
                done.add((r["question_id"], r["model"], r["condition"]))
            except (json.JSONDecodeError, KeyError):
                continue
    return done


def cmd_run(args) -> None:
    if not SELECTION_PATH.exists():
        print("Run --select first to choose questions.")
        return
    questions = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    api_key = get_openrouter_key()
    search = SearchTool(prefer="tavily")

    models = {k: MODELS[k] for k in args.models} if args.models else MODELS

    done = _already_run()
    print(f"Resuming: {len(done)} trials already in {TRIALS_PATH}")

    total_expected = len(questions) * len(models) * len(CONDITIONS)
    i = 0
    for q in questions:
        for name, mid in models.items():
            client = LLMClient(api_key=api_key, model=mid)
            for cond in CONDITIONS:
                i += 1
                key = (q["id"], name, cond)
                if key in done:
                    continue
                print(f"[{i}/{total_expected}] {q['id'][:12]}... {name} {cond}")
                try:
                    res = run_trial(q, mid, name, cond, client,
                                     search=search if cond != "no_search" else None)
                except Exception as e:
                    print(f"  error: {e}")
                    continue
                _append_trial(res)

    print(f"Done. Trials written to {TRIALS_PATH}")


# ── Step 3: resolve ────────────────────────────────────────────────────────

def cmd_resolve(args) -> None:
    if not SELECTION_PATH.exists():
        print("No selected_questions.json — nothing to resolve.")
        return
    questions = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    cache = resolve_all(questions, refresh=args.refresh)
    resolved_n = sum(1 for v in cache.values() if v.get("resolved"))
    print(f"Resolved {resolved_n}/{len(questions)} questions.")


# ── Step 4: score ──────────────────────────────────────────────────────────

def cmd_score(args) -> None:
    from forecast_bench.agent_forecast.scoring import (
        load_trials, merge_with_resolutions, score, report,
    )
    df = load_trials(TRIALS_PATH)
    df = merge_with_resolutions(df)
    if df.empty:
        print("No resolved trials to score yet.")
        return
    df = score(df, prob_col=args.prob_col)
    report(df)
    out_csv = OUT_DIR / "scored_trials.csv"
    df.to_csv(out_csv, index=False)
    print(f"\nScored data written to {out_csv}")


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")

    p_sel = sub.add_parser("select", help="pick eligible questions")
    p_sel.add_argument("--all", action="store_true",
                        help="take all eligible questions at this horizon (~250)")
    p_sel.add_argument("--max-n", type=int, default=60,
                        help="cap on selected questions (ignored if --all)")
    p_sel.add_argument("--min-days", type=int, default=14,
                        help="earliest resolution horizon (days from today)")
    p_sel.add_argument("--max-days", type=int, default=56,
                        help="latest resolution horizon")
    p_sel.add_argument("--download", action="store_true",
                        help="download the latest forecastbench snapshot first")
    p_sel.add_argument("--seed", type=int, default=42)
    p_sel.set_defaults(func=cmd_select)

    p_run = sub.add_parser("run", help="run all trials")
    p_run.add_argument("--models", nargs="*", default=None,
                        help="subset of model names to run")
    p_run.set_defaults(func=cmd_run)

    p_res = sub.add_parser("resolve", help="fetch ground-truth outcomes")
    p_res.add_argument("--refresh", action="store_true",
                        help="re-resolve even if cached")
    p_res.set_defaults(func=cmd_resolve)

    p_sco = sub.add_parser("score", help="compute Brier + compare conditions")
    p_sco.add_argument("--prob-col", default="p1",
                        choices=["p0", "p1"],
                        help="which probability column to score")
    p_sco.set_defaults(func=cmd_score)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
