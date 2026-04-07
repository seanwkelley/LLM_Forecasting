"""
Conflict Forecasting Experiment -- External LLM forecasters predict
next-period escalation direction from completed conflict simulation data.

Each forecaster receives a window of escalation history (EI, actions, state)
and predicts the next-period escalation change direction (UP / FLAT / DOWN)
with a probability distribution.

Design:
  - Load completed conflict sim results (JSON from run_conflict_sim.py)
  - For each period t, build a forecaster prompt with history up to t,
    then evaluate against the actual t+1 outcome
  - Multiple forecasters per period (different personas)
  - Evaluate via Brier score and accuracy

Usage:
    # Quick test (1 scenario, 5 forecasters)
    python conflict/run_conflict_forecast.py \\
        --results-dir outputs/simulations/conflict \\
        --n-forecasters 5 --model llama

    # Full run with ToM
    python conflict/run_conflict_forecast.py \\
        --results-dir outputs/simulations/conflict \\
        --n-forecasters 5 --model llama --tom
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

from conflict.agents_config import get_tom_context


# ---------------------------------------------------------------------------
# Forecaster personas -- diverse analytical styles for conflict
# ---------------------------------------------------------------------------

FORECASTER_PERSONAS = [
    {
        "id": "escalation_analyst",
        "name": "Escalation Dynamics Analyst",
        "prompt": (
            "You are an escalation dynamics analyst specializing in conflict spirals. "
            "You study how actions and counter-actions drive escalation. Look at the "
            "pattern of recent actions -- mutual escalation tends to persist, while "
            "asymmetric responses create instability."
        ),
    },
    {
        "id": "stability_analyst",
        "name": "Strategic Stability Analyst",
        "prompt": (
            "You are a strategic stability analyst. You believe conflicts tend toward "
            "equilibrium. When escalation is extreme, there are strong pressures to "
            "de-escalate. When tensions are low, provocations become more likely. "
            "Look for reversion to the mean."
        ),
    },
    {
        "id": "military_analyst",
        "name": "Military Balance Analyst",
        "prompt": (
            "You are a military analyst focused on the balance of power. You believe "
            "military capabilities and resource levels drive escalation decisions. "
            "When one side has an advantage, they may press it. When resources are "
            "depleted, expect de-escalation."
        ),
    },
    {
        "id": "diplomatic_watcher",
        "name": "Diplomatic Process Analyst",
        "prompt": (
            "You are a diplomatic process analyst. You focus on the diplomatic "
            "signals and de-escalatory actions. Peace talks and humanitarian gestures "
            "often precede broader de-escalation. But diplomatic failures can trigger "
            "rapid escalation. Watch for shifts in diplomatic tone."
        ),
    },
    {
        "id": "sanctions_analyst",
        "name": "Economic Sanctions Analyst",
        "prompt": (
            "You are an economic sanctions analyst. You study how economic pressure "
            "affects conflict behavior. Rising sanctions constrain the aggressor's "
            "options and may force de-escalation, but they can also trigger desperate "
            "escalatory moves. Watch resource levels and sanctions trends."
        ),
    },
    {
        "id": "pattern_analyst",
        "name": "Historical Pattern Analyst",
        "prompt": (
            "You are a historical pattern analyst who studies conflict cycles. "
            "You look for repeating patterns in escalation sequences: provocation-"
            "response spirals, cooling-off periods, and threshold effects where "
            "escalation suddenly accelerates. History rhymes."
        ),
    },
    {
        "id": "game_theorist",
        "name": "Game Theory Analyst",
        "prompt": (
            "You are a game theory analyst. You think about conflicts as strategic "
            "games where each side's moves depend on expectations about the other. "
            "Look for Nash equilibrium tendencies, commitment problems, and "
            "signaling dynamics."
        ),
    },
    {
        "id": "risk_assessor",
        "name": "Risk Assessment Analyst",
        "prompt": (
            "You are a geopolitical risk assessor. You focus on tail risks and "
            "worst-case scenarios. You're attuned to the conditions that precede "
            "rapid escalation: resource depletion, political instability, military "
            "imbalances. You tend to see downside risks others miss."
        ),
    },
    {
        "id": "bayesian_analyst",
        "name": "Probabilistic Analyst",
        "prompt": (
            "You are a Bayesian probabilistic analyst. You start from base rates "
            "(roughly equal chances of escalation, de-escalation, or stability) "
            "and update based on evidence. Be well-calibrated -- avoid extreme "
            "probabilities unless evidence is overwhelming."
        ),
    },
    {
        "id": "crisis_specialist",
        "name": "Crisis Management Specialist",
        "prompt": (
            "You are a crisis management specialist with experience in international "
            "conflict mediation. You watch for crisis triggers and off-ramps. "
            "You believe most escalation is driven by misperception and commitment "
            "traps. Look for signals that either side is looking for an exit."
        ),
    },
]


DEMOGRAPHIC_PERSONAS = [
    {
        "id": "retired_general",
        "name": "Retired General",
        "prompt": (
            "You are a 64-year-old retired three-star general with 35 years of military "
            "service including two combat deployments. You've seen escalation spirals "
            "firsthand and trust your operational instincts developed from decades of "
            "experience. You're skeptical of diplomatic solutions and prefer reading "
            "the military balance."
        ),
    },
    {
        "id": "ir_professor",
        "name": "International Relations Professor",
        "prompt": (
            "You are a 55-year-old international relations professor specializing in "
            "conflict escalation. You think in terms of deterrence theory, security "
            "dilemmas, and historical precedents. You distrust simplistic narratives "
            "and prefer systematic analysis grounded in IR theory."
        ),
    },
    {
        "id": "cautious_diplomat",
        "name": "Cautious Senior Diplomat",
        "prompt": (
            "You are a 51-year-old career diplomat who has served in multiple conflict "
            "zones. You tend to see de-escalation opportunities others miss and are "
            "always thinking about face-saving off-ramps. You've been burned by "
            "hawkish groupthink before and prefer cautious, nuanced assessments."
        ),
    },
    {
        "id": "young_analyst",
        "name": "Junior Intelligence Analyst",
        "prompt": (
            "You are a 26-year-old junior intelligence analyst fresh out of graduate "
            "school. You're eager and detail-oriented, closely reading every data "
            "point. You tend to be confident in pattern-matching and believe in the "
            "predictive power of recent trends. You rely heavily on textbook frameworks."
        ),
    },
    {
        "id": "contrarian_pundit",
        "name": "Contrarian Foreign Policy Pundit",
        "prompt": (
            "You are a 48-year-old foreign policy commentator known for contrarian "
            "takes. You believe conventional wisdom about conflicts is usually wrong "
            "at turning points. Escalation expectations often overshoot, and peace "
            "breaks out when least expected. You're aggressive in your conviction."
        ),
    },
    {
        "id": "conflict_historian",
        "name": "Conflict Historian",
        "prompt": (
            "You are a 62-year-old historian specializing in 20th century conflicts. "
            "You think in terms of historical analogies -- which past conflicts does "
            "this resemble? You believe escalation dynamics follow recognizable patterns "
            "but that each conflict has unique features that can defy historical parallels."
        ),
    },
    {
        "id": "ngo_worker",
        "name": "Humanitarian NGO Director",
        "prompt": (
            "You are a 39-year-old humanitarian aid worker who has operated in conflict "
            "zones for 15 years. You focus on civilian impact indicators and ground-truth "
            "signals that desk analysts miss. You think humanitarian crises create "
            "pressure for de-escalation but can also trigger desperate moves."
        ),
    },
    {
        "id": "defense_consultant",
        "name": "Defense Industry Consultant",
        "prompt": (
            "You are a 44-year-old defense industry consultant who advises governments "
            "on military procurement. You're methodical, consider multiple scenarios, "
            "and weight them probabilistically. You understand the logistics and "
            "resource constraints that ultimately determine what's feasible in conflicts."
        ),
    },
    {
        "id": "behavioral_scientist",
        "name": "Behavioral Conflict Researcher",
        "prompt": (
            "You are a 42-year-old behavioral scientist studying decision-making under "
            "stress. You see conflicts as driven by cognitive biases -- groupthink, "
            "escalation of commitment, loss aversion, and sunk cost fallacy. You look "
            "for signs of psychological traps in the conflict dynamics."
        ),
    },
    {
        "id": "geopolitical_strategist",
        "name": "Geopolitical Strategist",
        "prompt": (
            "You are a 53-year-old geopolitical strategist at a think tank. You think "
            "about big-picture structural forces -- alliance dynamics, economic "
            "interdependence, domestic political pressures. You're patient and look "
            "for regime changes rather than period-to-period noise."
        ),
    },
]


FORECASTER_SYSTEM = """\
You are an expert geopolitical analyst forecasting escalation dynamics in a \
simulated conflict between Novaris (a major power) and Tethys (a smaller defender).

{persona_prompt}

Your task: Given the conflict history below, predict the NEXT period's escalation change.

You must output a JSON object with:
- "predicted_ei": your point estimate for the next period's Escalation Index (0-10 scale)
- "prob_up": probability escalation goes UP (>0.1 change), between 0.0 and 1.0
- "prob_down": probability escalation goes DOWN (>0.1 change), between 0.0 and 1.0
- "prob_flat": probability escalation stays FLAT (within 0.1), between 0.0 and 1.0
- "reasoning": brief explanation (1-2 sentences)

The three probabilities MUST sum to 1.0.

Respond with ONLY valid JSON. No other text."""


# ---------------------------------------------------------------------------
# Forecast prompt builder
# ---------------------------------------------------------------------------

def build_forecast_prompt(
    escalation_history: list[float],
    actions_log: list[dict],
    current_period: int,
    state_info: dict | None = None,
    shock_info: str = "",
    window: int = 10,
    tom: bool = False,
) -> str:
    """Build the user prompt for a forecaster at period t."""
    parts = []
    parts.append(f"=== FORECAST REQUEST: Period {current_period + 1} -> {current_period + 2} ===\n")

    start = max(0, current_period + 1 - window)
    end = current_period + 1

    parts.append("## Escalation History")
    parts.append(f"{'Period':>6} | {'EI':>6} | {'Change':>8} | {'Novaris Action':>20} | {'Tethys Action':>20}")
    parts.append(f"{'------':>6} | {'------':>6} | {'--------':>8} | {'--------------------':>20} | {'--------------------':>20}")

    for i in range(start, end):
        ei = escalation_history[i]
        if i > 0:
            delta = escalation_history[i] - escalation_history[i - 1]
            delta_str = f"{delta:+7.2f}"
        else:
            delta_str = "    n/a"

        if i < len(actions_log):
            nov_act = actions_log[i].get("novaris_action", "n/a")
            teth_act = actions_log[i].get("tethys_action", "n/a")
        else:
            nov_act = "n/a"
            teth_act = "n/a"

        parts.append(f"{i+1:6d} | {ei:6.2f} | {delta_str} | {nov_act:>20} | {teth_act:>20}")

    # Summary statistics
    ei_visible = escalation_history[start:end]
    if len(ei_visible) >= 2:
        parts.append(f"\n## Summary Statistics")
        avg = np.mean(ei_visible)
        std = np.std(ei_visible)
        last = ei_visible[-1]
        prev = ei_visible[-2]
        last_change = last - prev
        direction = "ESCALATING" if last_change > 0.1 else "DE-ESCALATING" if last_change < -0.1 else "STABLE"

        parts.append(f"- Current Escalation Index: {last:.2f}/10.0 ({direction}, {last_change:+.2f})")
        parts.append(f"- {len(ei_visible)}-period average: {avg:.2f}")
        parts.append(f"- EI std: {std:.2f}")

        # Trend info
        changes = [ei_visible[j] - ei_visible[j-1] for j in range(1, len(ei_visible))]
        up_periods = sum(1 for c in changes if c > 0.1)
        down_periods = sum(1 for c in changes if c < -0.1)
        flat_periods = len(changes) - up_periods - down_periods
        parts.append(f"- Recent periods: {up_periods} escalating, {down_periods} de-escalating, {flat_periods} stable")

        # Streak
        streak = 0
        if changes:
            last_dir = "up" if changes[-1] > 0.1 else "down" if changes[-1] < -0.1 else "flat"
            for c in reversed(changes):
                d = "up" if c > 0.1 else "down" if c < -0.1 else "flat"
                if d == last_dir:
                    streak += 1
                else:
                    break
            parts.append(f"- Current streak: {streak} consecutive {last_dir} period(s)")

    # State info
    if state_info:
        parts.append(f"\n## Current Conflict State")
        for key, val in state_info.items():
            parts.append(f"- {key.replace('_', ' ').title()}: {val}")

    # Shock info
    if shock_info:
        parts.append(f"\n## Active Special Conditions")
        parts.append(shock_info)

    # Theory of Mind context
    if tom:
        parts.append(get_tom_context())

    parts.append(f"\n## Your Prediction")
    parts.append(f"Predict the escalation change from period {current_period + 1} to {current_period + 2}.")
    parts.append("UP = escalation index increases by more than 0.1")
    parts.append("DOWN = escalation index decreases by more than 0.1")
    parts.append("FLAT = escalation index changes by less than 0.1")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# LLM API call
# ---------------------------------------------------------------------------

def call_forecaster(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    model: str = "meta-llama/llama-3.1-8b-instruct",
    temperature: float = 0.7,
    max_retries: int = 3,
    max_tokens: int = 200,
) -> dict | None:
    """Call the LLM forecaster and parse the response."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                tokens = resp.json().get("usage", {}).get("total_tokens", 0)
                return _parse_forecast(content, tokens)
            elif resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            else:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return None

    return None


def _parse_forecast(text: str, tokens: int = 0) -> dict | None:
    """Parse LLM JSON response into forecast dict."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[^{}]*\}", text)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        else:
            return None

    try:
        prob_up = float(data.get("prob_up", 0.33))
        prob_down = float(data.get("prob_down", 0.33))
        prob_flat = float(data.get("prob_flat", 0.34))
    except (TypeError, ValueError):
        return None

    total = prob_up + prob_down + prob_flat
    if total <= 0:
        return None
    prob_up /= total
    prob_down /= total
    prob_flat /= total

    predicted_ei = data.get("predicted_ei")
    try:
        predicted_ei = float(predicted_ei) if predicted_ei is not None else None
    except (TypeError, ValueError):
        predicted_ei = None

    return {
        "prob_up": round(prob_up, 4),
        "prob_down": round(prob_down, 4),
        "prob_flat": round(prob_flat, 4),
        "predicted_ei": predicted_ei,
        "reasoning": str(data.get("reasoning", "")),
        "tokens": tokens,
    }


# ---------------------------------------------------------------------------
# Evaluation metrics
# ---------------------------------------------------------------------------

def classify_change(ei_now: float, ei_next: float, threshold: float = 0.1) -> str:
    """Classify escalation change as UP, DOWN, or FLAT."""
    change = ei_next - ei_now
    if change > threshold:
        return "UP"
    elif change < -threshold:
        return "DOWN"
    else:
        return "FLAT"


def brier_score(forecast: dict, actual: str) -> float:
    """Compute Brier score for a three-class forecast."""
    actual_vec = {"UP": [1, 0, 0], "DOWN": [0, 1, 0], "FLAT": [0, 0, 1]}[actual]
    pred = [forecast["prob_up"], forecast["prob_down"], forecast["prob_flat"]]
    return sum((p - a) ** 2 for p, a in zip(pred, actual_vec))


def log_score(forecast: dict, actual: str) -> float:
    """Compute log score."""
    prob_map = {"UP": "prob_up", "DOWN": "prob_down", "FLAT": "prob_flat"}
    prob = max(forecast[prob_map[actual]], 1e-6)
    return -np.log(prob)


def compute_f1(rows: list[dict], classes: tuple = ("UP", "DOWN", "FLAT")) -> dict:
    """Compute per-class and macro F1."""
    results = {}
    f1s = []
    for cls in classes:
        tp = sum(1 for r in rows if r["pred_class"] == cls and r["actual"] == cls)
        fp = sum(1 for r in rows if r["pred_class"] == cls and r["actual"] != cls)
        fn = sum(1 for r in rows if r["pred_class"] != cls and r["actual"] == cls)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        results[cls] = {"precision": precision, "recall": recall, "f1": f1}
        f1s.append(f1)
    results["macro_f1"] = float(np.mean(f1s))
    return results


# ---------------------------------------------------------------------------
# Main experiment runner
# ---------------------------------------------------------------------------

def run_forecast_experiment(
    results_dir: str,
    n_forecasters: int = 5,
    api_key: str = "",
    model: str = "meta-llama/llama-3.1-8b-instruct",
    temperature: float = 0.7,
    history_window: int = 10,
    start_period: int = 5,
    output_dir: str | None = None,
    tom: bool = False,
    persona_list: list[dict] | None = None,
) -> dict:
    """Run the forecasting experiment on completed conflict simulation data."""
    results_path = Path(results_dir)
    scenario_files = sorted(results_path.glob("scenario_*.json"))

    if not scenario_files:
        print(f"[ERROR] No scenario files in {results_dir}")
        return {}

    available = persona_list if persona_list is not None else FORECASTER_PERSONAS
    personas = available[:n_forecasters]

    if output_dir is None:
        out_path = results_path / "forecasting"
    else:
        out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    csv_path = out_path / "forecast_results.csv"
    detail_path = out_path / "forecast_details.json"

    print("=" * 70)
    print(f"CONFLICT FORECASTING EXPERIMENT")
    print(f"Results dir: {results_dir}")
    print(f"Scenarios:   {len(scenario_files)}")
    print(f"Forecasters: {n_forecasters} ({', '.join(p['id'] for p in personas)})")
    print(f"Model:       {model}")
    print(f"ToM:         {'YES' if tom else 'NO'}")
    print(f"Start from:  period {start_period + 1}")
    print(f"Output:      {out_path}")
    print("=" * 70)

    all_rows = []
    all_details = []
    total_calls = 0
    total_tokens = 0
    t0 = time.time()

    for s_idx, scenario_file in enumerate(scenario_files):
        with open(scenario_file) as f:
            data = json.load(f)

        sid = data["summary"]["scenario_id"]
        ei_history = data["escalation_history"]
        actions_log = data.get("actions_log", [])
        n_periods = len(ei_history)

        print(f"\n[{s_idx+1}/{len(scenario_files)}] {sid} ({n_periods} periods)")

        for t in range(start_period, n_periods - 1):
            actual = classify_change(ei_history[t], ei_history[t + 1])

            # Extract state info at period t from actions_log
            state_info = None
            if t < len(actions_log):
                log_t = actions_log[t]
                state_info = {}
                for key in ["military_balance", "territory_controlled", "sanctions_level"]:
                    if key in log_t:
                        state_info[key] = log_t[key]

            user_prompt = build_forecast_prompt(
                escalation_history=ei_history,
                actions_log=actions_log,
                current_period=t,
                state_info=state_info,
                window=history_window,
                tom=tom,
            )

            for persona in personas:
                sys_prompt = FORECASTER_SYSTEM.format(persona_prompt=persona["prompt"])

                forecast = call_forecaster(
                    system_prompt=sys_prompt,
                    user_prompt=user_prompt,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    max_tokens=400 if "qwen" in model else 200,
                )

                total_calls += 1

                if forecast is None:
                    forecast = {
                        "prob_up": 0.333,
                        "prob_down": 0.333,
                        "prob_flat": 0.334,
                        "predicted_ei": ei_history[t],
                        "reasoning": "FALLBACK",
                        "tokens": 0,
                    }
                    source = "fallback"
                else:
                    source = "llm"
                    total_tokens += forecast.get("tokens", 0)

                bs = brier_score(forecast, actual)
                ls = log_score(forecast, actual)

                pred_class = max(
                    [("UP", forecast["prob_up"]),
                     ("DOWN", forecast["prob_down"]),
                     ("FLAT", forecast["prob_flat"])],
                    key=lambda x: x[1],
                )[0]

                actual_ei = ei_history[t + 1]
                pred_ei = forecast.get("predicted_ei")
                ei_error = abs(pred_ei - actual_ei) if pred_ei is not None else None

                row = {
                    "scenario_id": sid,
                    "period": t + 1,
                    "forecaster_id": persona["id"],
                    "actual": actual,
                    "pred_class": pred_class,
                    "correct": int(pred_class == actual),
                    "prob_up": forecast["prob_up"],
                    "prob_down": forecast["prob_down"],
                    "prob_flat": forecast["prob_flat"],
                    "predicted_ei": round(pred_ei, 4) if pred_ei is not None else "",
                    "actual_ei": round(actual_ei, 4),
                    "ei_error": round(ei_error, 4) if ei_error is not None else "",
                    "brier_score": round(bs, 4),
                    "log_score": round(ls, 4),
                    "source": source,
                }
                all_rows.append(row)

                all_details.append({
                    **row,
                    "reasoning": forecast["reasoning"],
                    "actual_change": round(ei_history[t+1] - ei_history[t], 4),
                })

                time.sleep(0.5)

            if (t - start_period) % 5 == 0:
                n_done = len(all_rows)
                f1 = compute_f1(all_rows)["macro_f1"]
                bs_mean = np.mean([r["brier_score"] for r in all_rows])
                print(f"  t={t+1:3d} | actual={actual:4s} | "
                      f"running: F1={f1:.3f}, brier={bs_mean:.3f} "
                      f"({n_done} forecasts)")

        _save_csv(csv_path, all_rows)

    elapsed = time.time() - t0

    with open(detail_path, "w") as f:
        json.dump(all_details, f, indent=2)

    _print_summary(all_rows, total_calls, total_tokens, elapsed, out_path)

    return {"rows": all_rows, "details": all_details}


def _save_csv(path: Path, rows: list[dict]):
    """Save forecast results to CSV."""
    if not rows:
        return
    fieldnames = [
        "scenario_id", "period", "forecaster_id", "actual", "pred_class",
        "correct", "prob_up", "prob_down", "prob_flat",
        "predicted_ei", "actual_ei", "ei_error",
        "brier_score", "log_score", "source",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{k: r[k] for k in fieldnames} for r in rows])


def _print_summary(rows, total_calls, total_tokens, elapsed, out_path):
    """Print experiment summary statistics."""
    if not rows:
        print("\n[WARN] No forecasts completed")
        return

    print(f"\n{'='*70}")
    print("CONFLICT FORECASTING SUMMARY")
    print(f"{'='*70}")

    n = len(rows)
    fallbacks = sum(1 for r in rows if r["source"] == "fallback")
    acc = np.mean([r["correct"] for r in rows]) * 100
    brier = np.mean([r["brier_score"] for r in rows])
    log_s = np.mean([r["log_score"] for r in rows])

    print(f"  Total forecasts:  {n}")
    print(f"  LLM calls:        {total_calls}")
    print(f"  Fallbacks:        {fallbacks} ({fallbacks/n*100:.1f}%)")
    print(f"  Total tokens:     {total_tokens:,}")
    print(f"  Elapsed:          {elapsed:.1f}s")
    print()

    # EI prediction metrics
    ei_errors = [r["ei_error"] for r in rows
                 if r["ei_error"] != "" and r["ei_error"] is not None]
    mae = np.mean(ei_errors) if ei_errors else float("nan")

    print(f"  Overall accuracy: {acc:.1f}%")
    print(f"  Mean Brier score: {brier:.4f}  (uniform baseline: 0.667)")
    print(f"  Mean log score:   {log_s:.4f}  (uniform baseline: 1.099)")
    print(f"  EI MAE:           {mae:.4f}")
    print(f"  EI predictions:   {len(ei_errors)}/{n} returned a value")

    # Target distribution
    actuals = [r["actual"] for r in rows]
    n_up = actuals.count("UP")
    n_down = actuals.count("DOWN")
    n_flat = actuals.count("FLAT")
    print(f"\n  Target distribution:")
    print(f"    UP:   {n_up:4d} ({n_up/n*100:.1f}%)")
    print(f"    DOWN: {n_down:4d} ({n_down/n*100:.1f}%)")
    print(f"    FLAT: {n_flat:4d} ({n_flat/n*100:.1f}%)")

    # --- Naive baselines ---
    print(f"\n  Naive baselines:")

    # Majority class
    majority = max(n_up, n_down, n_flat)
    majority_acc = majority / n * 100
    majority_cls = "UP" if n_up == majority else "DOWN" if n_down == majority else "FLAT"
    majority_brier = np.mean([
        brier_score({"prob_up": 1.0 if majority_cls == "UP" else 0.0,
                      "prob_down": 1.0 if majority_cls == "DOWN" else 0.0,
                      "prob_flat": 1.0 if majority_cls == "FLAT" else 0.0}, a)
        for a in actuals
    ])
    print(f"    Majority class ({majority_cls}):  acc={majority_acc:.1f}%, brier={majority_brier:.4f}")

    # Frequency-weighted
    freq_up, freq_down, freq_flat = n_up / n, n_down / n, n_flat / n
    freq_forecast = {"prob_up": freq_up, "prob_down": freq_down, "prob_flat": freq_flat}
    freq_brier = np.mean([brier_score(freq_forecast, a) for a in actuals])
    print(f"    Frequency-weighted:    brier={freq_brier:.4f}")

    # Persistence
    persistence_correct = 0
    persistence_brier_total = 0.0
    persistence_n = 0
    for sid in sorted(set(r["scenario_id"] for r in rows)):
        s_periods = {}
        for r in rows:
            if r["scenario_id"] == sid:
                s_periods[r["period"]] = r["actual"]
        sorted_periods = sorted(s_periods.keys())
        for i, t in enumerate(sorted_periods):
            if i == 0:
                continue
            prev_actual = s_periods[sorted_periods[i - 1]]
            actual_here = s_periods[t]
            pers_forecast = {
                "prob_up": 1.0 if prev_actual == "UP" else 0.0,
                "prob_down": 1.0 if prev_actual == "DOWN" else 0.0,
                "prob_flat": 1.0 if prev_actual == "FLAT" else 0.0,
            }
            persistence_correct += int(prev_actual == actual_here)
            persistence_brier_total += brier_score(pers_forecast, actual_here)
            persistence_n += 1
    if persistence_n > 0:
        pers_acc = persistence_correct / persistence_n * 100
        pers_brier = persistence_brier_total / persistence_n
        print(f"    Persistence (last dir): acc={pers_acc:.1f}%, brier={pers_brier:.4f}")

    print(f"    Uniform (1/3 each):    brier=0.6667")

    # F1 scores
    f1_results = compute_f1(rows)
    print(f"\n  Macro F1: {f1_results['macro_f1']:.3f}")
    print(f"  Per-class F1:")
    print(f"    {'Class':>5s} | {'Prec':>5s} | {'Rec':>5s} | {'F1':>5s}")
    print(f"    {'-----':>5s} | {'-----':>5s} | {'-----':>5s} | {'-----':>5s}")
    for cls in ["UP", "DOWN", "FLAT"]:
        c = f1_results[cls]
        print(f"    {cls:>5s} | {c['precision']:.3f} | {c['recall']:.3f} | {c['f1']:.3f}")

    # Per-forecaster breakdown
    print(f"\n  Per-forecaster performance:")
    print(f"  {'Forecaster':>20s} | {'Acc':>5s} | {'Brier':>6s} | {'F1':>5s} | {'MAE':>6s} | {'N':>4s}")
    print(f"  {'--------------------':>20s} | {'-----':>5s} | {'------':>6s} | {'-----':>5s} | {'------':>6s} | {'----':>4s}")

    forecaster_ids = sorted(set(r["forecaster_id"] for r in rows))
    for fid in forecaster_ids:
        f_rows = [r for r in rows if r["forecaster_id"] == fid]
        f_acc = np.mean([r["correct"] for r in f_rows]) * 100
        f_brier = np.mean([r["brier_score"] for r in f_rows])
        f_f1 = compute_f1(f_rows)["macro_f1"]
        f_errs = [r["ei_error"] for r in f_rows
                  if r["ei_error"] != "" and r["ei_error"] is not None]
        f_mae = np.mean(f_errs) if f_errs else float("nan")
        print(f"  {fid:>20s} | {f_acc:5.1f} | {f_brier:6.4f} | {f_f1:.3f} | {f_mae:5.3f} | {len(f_rows):4d}")

    # Per-scenario breakdown
    print(f"\n  Per-scenario performance:")
    scenario_ids = sorted(set(r["scenario_id"] for r in rows))
    for sid in scenario_ids:
        s_rows = [r for r in rows if r["scenario_id"] == sid]
        s_acc = np.mean([r["correct"] for r in s_rows]) * 100
        s_brier = np.mean([r["brier_score"] for r in s_rows])
        print(f"    {sid}: acc={s_acc:.1f}%, brier={s_brier:.4f} ({len(s_rows)} forecasts)")

    # Ensemble
    print(f"\n  Ensemble performance (average across forecasters):")
    ensemble_rows = []
    ensemble_brier_total = 0.0
    ensemble_ei_errors = []
    ensemble_n = 0

    for sid in scenario_ids:
        for t in sorted(set(r["period"] for r in rows if r["scenario_id"] == sid)):
            period_rows = [r for r in rows if r["scenario_id"] == sid and r["period"] == t]
            if not period_rows:
                continue
            avg_up = np.mean([r["prob_up"] for r in period_rows])
            avg_down = np.mean([r["prob_down"] for r in period_rows])
            avg_flat = np.mean([r["prob_flat"] for r in period_rows])
            actual = period_rows[0]["actual"]

            ens_forecast = {"prob_up": avg_up, "prob_down": avg_down, "prob_flat": avg_flat}
            ens_pred = max(ens_forecast, key=ens_forecast.get).replace("prob_", "").upper()
            ensemble_rows.append({"pred_class": ens_pred, "actual": actual})
            ensemble_brier_total += brier_score(ens_forecast, actual)

            valid_eis = [r["predicted_ei"] for r in period_rows
                         if r["predicted_ei"] != "" and r["predicted_ei"] is not None]
            if valid_eis:
                ens_ei = np.mean(valid_eis)
                actual_ei = period_rows[0]["actual_ei"]
                ensemble_ei_errors.append(abs(ens_ei - actual_ei))

            ensemble_n += 1

    if ensemble_n > 0:
        ens_correct = sum(1 for r in ensemble_rows if r["pred_class"] == r["actual"])
        ens_acc = ens_correct / ensemble_n * 100
        ens_brier = ensemble_brier_total / ensemble_n
        ens_f1 = compute_f1(ensemble_rows)["macro_f1"]
        ens_mae = np.mean(ensemble_ei_errors) if ensemble_ei_errors else float("nan")
        print(f"    Ensemble accuracy:  {ens_acc:.1f}%")
        print(f"    Ensemble Brier:     {ens_brier:.4f}")
        print(f"    Ensemble macro F1:  {ens_f1:.3f}")
        print(f"    Ensemble EI MAE:    {ens_mae:.4f}")
        print(f"    Ensemble N:         {ensemble_n} period-predictions")

    # Save summary
    summary = {
        "total_forecasts": n,
        "total_calls": total_calls,
        "fallbacks": fallbacks,
        "total_tokens": total_tokens,
        "elapsed_seconds": round(elapsed, 1),
        "overall_accuracy": round(acc, 2),
        "macro_f1": round(f1_results["macro_f1"], 4),
        "per_class_f1": {cls: round(f1_results[cls]["f1"], 4) for cls in ["UP", "DOWN", "FLAT"]},
        "mean_brier": round(brier, 4),
        "mean_log_score": round(log_s, 4),
        "ei_mae": round(mae, 4) if not np.isnan(mae) else None,
        "baselines": {
            "majority_acc": round(majority_acc, 2),
            "majority_brier": round(majority_brier, 4),
            "frequency_brier": round(freq_brier, 4),
            "persistence_acc": round(pers_acc, 2) if persistence_n > 0 else None,
            "persistence_brier": round(pers_brier, 4) if persistence_n > 0 else None,
            "uniform_brier": 0.6667,
        },
        "ensemble_accuracy": round(ens_acc, 2) if ensemble_n > 0 else None,
        "ensemble_macro_f1": round(ens_f1, 4) if ensemble_n > 0 else None,
        "ensemble_brier": round(ens_brier, 4) if ensemble_n > 0 else None,
    }
    with open(out_path / "forecast_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Results saved to: {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Conflict forecasting experiment")
    parser.add_argument("--results-dir", type=str, required=True,
                        help="Directory with completed conflict sim results")
    parser.add_argument("--n-forecasters", type=int, default=5,
                        help="Number of forecaster personas (max 10)")
    parser.add_argument("--model", type=str, default="llama",
                        choices=["llama", "deepseek", "claude", "qwen"],
                        help="LLM model for forecasters")
    parser.add_argument("--tom", action="store_true",
                        help="Enable Theory of Mind (show agent personas)")
    parser.add_argument("--persona-type", type=str, default="strategy",
                        choices=["strategy", "demographic"],
                        help="Persona type: 'strategy' (analytical styles) or 'demographic' (people)")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--history-window", type=int, default=10)
    parser.add_argument("--start-period", type=int, default=5)
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    model_map = {
        "llama": "meta-llama/llama-3.1-8b-instruct",
        "deepseek": "deepseek/deepseek-v3.2",
        "claude": "anthropic/claude-sonnet-4",
        "qwen": "qwen/qwen3-235b-a22b-2507",
    }

    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        try:
            from archive.wargame_forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except ImportError:
            pass
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set")
        sys.exit(1)

    persona_list = DEMOGRAPHIC_PERSONAS if args.persona_type == "demographic" else FORECASTER_PERSONAS

    output_dir = args.output_dir
    if output_dir is None:
        suffix = "forecasting"
        if args.persona_type == "demographic":
            suffix += "_demographic"
        if args.tom:
            suffix += "_tom"
        output_dir = str(Path(args.results_dir) / suffix)

    run_forecast_experiment(
        results_dir=args.results_dir,
        n_forecasters=min(args.n_forecasters, len(persona_list)),
        api_key=api_key,
        model=model_map[args.model],
        temperature=args.temperature,
        history_window=args.history_window,
        start_period=args.start_period,
        output_dir=output_dir,
        tom=args.tom,
        persona_list=persona_list,
    )


if __name__ == "__main__":
    main()
