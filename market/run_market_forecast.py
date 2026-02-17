"""
Phase 5: Market Forecasting Experiment — External LLM forecasters predict
next-period price direction from completed market simulation data.

Each forecaster receives a window of market history (prices, volumes, shocks)
and predicts the next-period price change direction (UP / FLAT / DOWN) with
a probability distribution.

Design:
  - Load completed market sim results (JSON from run_market_sim.py)
  - For each period t in each scenario, build a forecaster prompt with
    the history up to t, then evaluate against the actual t+1 outcome
  - Multiple forecasters per period (different personas / models)
  - Evaluate via Brier score and accuracy

Usage:
    # Quick test (1 scenario, 5 forecasters)
    python market/run_market_forecast.py \\
        --results-dir outputs/market_sim_llama_10s30p_persona \\
        --n-forecasters 5 --model llama

    # Full run (all scenarios, 10 forecasters)
    python market/run_market_forecast.py \\
        --results-dir outputs/market_sim_llama_10s30p_persona \\
        --n-forecasters 10 --model llama
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


# ---------------------------------------------------------------------------
# Forecaster personas — diverse analytical styles
# ---------------------------------------------------------------------------

FORECASTER_PERSONAS = [
    {
        "id": "trend_follower",
        "name": "Trend Analyst",
        "prompt": (
            "You are a trend-following market analyst. You believe price momentum "
            "is the strongest predictor. Look at recent price direction and magnitude. "
            "Trends tend to persist in the short term."
        ),
    },
    {
        "id": "mean_reverter",
        "name": "Mean Reversion Analyst",
        "prompt": (
            "You are a mean-reversion analyst. You believe prices revert to their "
            "average over time. When prices deviate far from the moving average, "
            "you expect a correction back toward the mean."
        ),
    },
    {
        "id": "volume_reader",
        "name": "Volume Analyst",
        "prompt": (
            "You are a volume-focused analyst. You believe trading volume is the key "
            "leading indicator. High volume confirms trends; low volume suggests "
            "exhaustion. Volume divergences predict reversals."
        ),
    },
    {
        "id": "fundamental",
        "name": "Fundamental Analyst",
        "prompt": (
            "You are a fundamentals-focused analyst. You compare the market price "
            "to the fundamental value. When price is above fundamental, you expect "
            "a decline; when below, you expect a rise. Fundamentals anchor prices."
        ),
    },
    {
        "id": "volatility",
        "name": "Volatility Analyst",
        "prompt": (
            "You are a volatility-focused analyst. You study the magnitude and "
            "clustering of price changes. High volatility periods tend to persist; "
            "calm periods also persist. Large moves are often followed by large moves."
        ),
    },
    {
        "id": "contrarian",
        "name": "Contrarian Analyst",
        "prompt": (
            "You are a contrarian analyst. You believe the crowd is usually wrong "
            "at extremes. After multiple periods of consistent movement in one "
            "direction, you expect a reversal. Consensus creates opportunity."
        ),
    },
    {
        "id": "shock_watcher",
        "name": "Event-Driven Analyst",
        "prompt": (
            "You are an event-driven analyst. You focus on supply/demand shocks "
            "and their aftermath. Shocks create price dislocations; prices adjust "
            "in the periods following a shock. The type of shock determines direction."
        ),
    },
    {
        "id": "pattern_matcher",
        "name": "Technical Pattern Analyst",
        "prompt": (
            "You are a technical pattern analyst. You look for repeating patterns "
            "in price sequences: double tops/bottoms, breakouts from ranges, "
            "support/resistance levels. History rhymes."
        ),
    },
    {
        "id": "bayesian",
        "name": "Probabilistic Analyst",
        "prompt": (
            "You are a Bayesian probabilistic analyst. You start from base rates "
            "(historically, prices go up, down, and flat roughly equally) and "
            "update based on evidence. Be well-calibrated — avoid extreme "
            "probabilities unless evidence is overwhelming."
        ),
    },
    {
        "id": "macro_reader",
        "name": "Macro-Structural Analyst",
        "prompt": (
            "You are a macro-structural analyst. You think about the overall market "
            "structure: are producers profitable enough to keep producing? Can "
            "consumers afford current prices? Is speculator activity stabilizing "
            "or destabilizing? Structural imbalances predict price direction."
        ),
    },
]


DEMOGRAPHIC_PERSONAS = [
    {
        "id": "veteran_trader",
        "name": "Veteran Floor Trader",
        "prompt": (
            "You are a 58-year-old retired commodities floor trader with 30 years of "
            "experience. You've seen every market cycle and trust your gut instincts "
            "developed from decades of pattern recognition. You're skeptical of "
            "quantitative models and prefer reading the 'feel' of the market."
        ),
    },
    {
        "id": "quant_phd",
        "name": "Quant Researcher",
        "prompt": (
            "You are a 31-year-old quantitative researcher with a PhD in applied "
            "mathematics. You think in terms of distributions, base rates, and "
            "statistical significance. You distrust narratives and prefer to let "
            "the numbers speak. You're careful about overconfidence."
        ),
    },
    {
        "id": "cautious_manager",
        "name": "Cautious Fund Manager",
        "prompt": (
            "You are a 47-year-old risk-averse institutional fund manager. Capital "
            "preservation is your priority. You tend to see downside risks others miss "
            "and are always thinking about worst-case scenarios. You've been burned by "
            "overconfidence before and prefer conservative estimates."
        ),
    },
    {
        "id": "young_analyst",
        "name": "Junior Analyst",
        "prompt": (
            "You are a 24-year-old junior market analyst fresh out of business school. "
            "You're eager and detail-oriented, closely reading every data point. You "
            "tend to be optimistic about market movements and believe in efficient "
            "markets. You rely heavily on textbook frameworks."
        ),
    },
    {
        "id": "contrarian_veteran",
        "name": "Contrarian Hedge Fund PM",
        "prompt": (
            "You are a 52-year-old hedge fund portfolio manager known for contrarian "
            "bets. You believe markets overshoot in both directions and that the "
            "consensus is usually wrong at turning points. You're aggressive in your "
            "conviction and not afraid to go against the crowd."
        ),
    },
    {
        "id": "econ_professor",
        "name": "Economics Professor",
        "prompt": (
            "You are a 63-year-old economics professor who studies commodity markets. "
            "You think in terms of supply/demand equilibrium, market structure, and "
            "microeconomic theory. You believe prices ultimately reflect fundamentals "
            "but can deviate significantly in the short run."
        ),
    },
    {
        "id": "day_trader",
        "name": "Active Day Trader",
        "prompt": (
            "You are a 36-year-old full-time day trader who trades on momentum and "
            "technical signals. You react quickly to price action and volume spikes. "
            "You think in terms of short-term momentum — what's moving now will "
            "keep moving. You're decisive and high-conviction."
        ),
    },
    {
        "id": "risk_analyst",
        "name": "Corporate Risk Analyst",
        "prompt": (
            "You are a 41-year-old corporate risk analyst at an energy company. "
            "Your job is to forecast commodity prices for budgeting and hedging. "
            "You're methodical, consider multiple scenarios, and weight them "
            "probabilistically. You value calibration over bold predictions."
        ),
    },
    {
        "id": "behavioral_psych",
        "name": "Behavioral Finance Expert",
        "prompt": (
            "You are a 45-year-old behavioral finance researcher. You see markets "
            "as driven by human psychology — herding, anchoring, loss aversion, "
            "and overreaction. You look for signs of behavioral biases in the "
            "price data and try to predict when psychology will drive prices."
        ),
    },
    {
        "id": "global_macro",
        "name": "Global Macro Strategist",
        "prompt": (
            "You are a 50-year-old global macro strategist at a sovereign wealth fund. "
            "You think about big-picture structural forces — supply chains, producer "
            "incentives, consumer behavior patterns. You're patient and look for "
            "regime changes rather than period-to-period noise."
        ),
    },
]


FORECASTER_SYSTEM = """\
You are an expert market forecaster analyzing a simulated commodity market (Meridium).

{persona_prompt}

Your task: Given the market history below, predict the NEXT period's price.

You must output a JSON object with:
- "predicted_price": your point estimate for the next period's clearing price (a number in dollars)
- "prob_up": probability price goes UP (>0.5% change), between 0.0 and 1.0
- "prob_down": probability price goes DOWN (>0.5% change), between 0.0 and 1.0
- "prob_flat": probability price stays FLAT (within 0.5%), between 0.0 and 1.0
- "reasoning": brief explanation (1-2 sentences)

The three probabilities MUST sum to 1.0.

Respond with ONLY valid JSON. No other text."""


# ---------------------------------------------------------------------------
# Theory of Mind context — agent persona descriptions for forecasters
# ---------------------------------------------------------------------------

TOM_CONTEXT = """\

## Market Participants (Theory of Mind)

This market has 7 trading agents with distinct strategies. Understanding their behavior \
will help you predict price movements:

**Producers (sell only):**
- **Volume Mover**: Aggressive seller who slashes prices to move inventory. Prioritizes \
cash flow over margins. When inventory builds up, expect lower asks.
- **Margin Optimizer**: Disciplined seller who holds firm on 15-20% margins above \
production cost. Will accumulate inventory rather than sell cheap. When prices are \
high, sells aggressively.

**Consumers (buy only):**
- **Security Stockpiler**: Risk-averse buyer who bids aggressively to maintain 3-4 \
periods of buffer stock. Supply security is non-negotiable — will pay premiums.
- **Bargain Hunter**: Patient buyer who only buys at 5-10% below market. Comfortable \
with low inventory if it means not overpaying. Reduces quantity when prices are high.
- **Shock Anticipator**: Forward-looking buyer who swings between very aggressive \
(before expected shortages) and very passive (calm markets). Reacts strongly to \
shock announcements.

**Speculators (buy or sell):**
- **Momentum Rider**: Trend follower who buys after 2+ up periods and sells after 2+ \
down periods. Exits on sharp reversals. Amplifies existing trends.
- **Value Contrarian**: Mean-reversion trader who sells when price is above the \
5-period average and buys when below. Fades extreme moves. Dampens trends.

**Key interaction dynamics:**
- When both speculators agree on direction, expect a strong move
- When they disagree (Momentum buying, Contrarian selling), expect a smaller move or flat
- The Stockpiler's persistent buying creates upward price pressure even in calm markets
- Supply shocks trigger aggressive buying from the Shock Anticipator, amplifying price spikes
- The Volume Mover's aggressive selling after inventory buildup can cause sudden price drops
"""


def build_forecast_prompt(
    price_history: list[float],
    volume_history: list[float],
    fundamental_history: list[float],
    current_period: int,
    shock_info: str = "",
    window: int = 10,
    tom: bool = False,
) -> str:
    """Build the user prompt for a forecaster at period t.

    The forecaster sees history up to and including period t, and must
    predict the direction of price change from t to t+1.
    """
    parts = []
    parts.append(f"=== FORECAST REQUEST: Period {current_period + 1} -> {current_period + 2} ===\n")

    # Price and volume history
    start = max(0, current_period + 1 - window)
    end = current_period + 1  # inclusive

    parts.append("## Market History")
    parts.append(f"{'Period':>6} | {'Price':>8} | {'Volume':>6} | {'Fundamental':>12} | {'Return':>8}")
    parts.append(f"{'------':>6} | {'--------':>8} | {'------':>6} | {'------------':>12} | {'--------':>8}")

    for i in range(start, end):
        p = price_history[i]
        v = volume_history[i]
        f_val = fundamental_history[i]
        if i > 0:
            ret = (price_history[i] - price_history[i - 1]) / price_history[i - 1] * 100
            ret_str = f"{ret:+7.2f}%"
        else:
            ret_str = "    n/a"
        parts.append(f"{i+1:6d} | ${p:7.2f} | {int(v):6d} | ${f_val:11.2f} | {ret_str}")

    # Summary statistics
    prices_visible = price_history[start:end]
    if len(prices_visible) >= 2:
        parts.append(f"\n## Summary Statistics")
        avg = np.mean(prices_visible)
        std = np.std(prices_visible)
        last = prices_visible[-1]
        prev = prices_visible[-2]
        last_ret = (last - prev) / prev * 100
        direction = "UP" if last_ret > 0.5 else "DOWN" if last_ret < -0.5 else "FLAT"

        parts.append(f"- Current price: ${last:.2f} ({direction}, {last_ret:+.1f}%)")
        parts.append(f"- {len(prices_visible)}-period average: ${avg:.2f}")
        parts.append(f"- Price std: ${std:.2f}")
        parts.append(f"- Price vs fundamental: ${last - fundamental_history[current_period]:+.2f} "
                      f"({'above' if last > fundamental_history[current_period] else 'below'} fundamental)")

        # Trend info
        returns = [(prices_visible[j] - prices_visible[j-1]) / prices_visible[j-1]
                    for j in range(1, len(prices_visible))]
        up_periods = sum(1 for r in returns if r > 0.005)
        down_periods = sum(1 for r in returns if r < -0.005)
        flat_periods = len(returns) - up_periods - down_periods
        parts.append(f"- Recent periods: {up_periods} up, {down_periods} down, {flat_periods} flat")

        # Streak
        streak = 0
        if returns:
            last_dir = "up" if returns[-1] > 0.005 else "down" if returns[-1] < -0.005 else "flat"
            for r in reversed(returns):
                d = "up" if r > 0.005 else "down" if r < -0.005 else "flat"
                if d == last_dir:
                    streak += 1
                else:
                    break
            parts.append(f"- Current streak: {streak} consecutive {last_dir} period(s)")

    # Shock info
    if shock_info:
        parts.append(f"\n## Active Market Conditions")
        parts.append(shock_info)

    # Theory of Mind context — agent persona descriptions
    if tom:
        parts.append(TOM_CONTEXT)

    parts.append(f"\n## Your Prediction")
    parts.append(f"Predict the price direction from period {current_period + 1} to {current_period + 2}.")
    parts.append("UP = price increases by more than 0.5%")
    parts.append("DOWN = price decreases by more than 0.5%")
    parts.append("FLAT = price changes by less than 0.5%")

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
    """Call the LLM forecaster and parse the response.

    Returns dict with prob_up, prob_down, prob_flat, reasoning or None on failure.
    """
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
    # Strip thinking tags from reasoning models (e.g., Qwen3)
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

    # Normalize to sum to 1
    total = prob_up + prob_down + prob_flat
    if total <= 0:
        return None
    prob_up /= total
    prob_down /= total
    prob_flat /= total

    # Extract predicted price
    predicted_price = data.get("predicted_price")
    try:
        predicted_price = float(predicted_price) if predicted_price is not None else None
    except (TypeError, ValueError):
        predicted_price = None

    return {
        "prob_up": round(prob_up, 4),
        "prob_down": round(prob_down, 4),
        "prob_flat": round(prob_flat, 4),
        "predicted_price": predicted_price,
        "reasoning": str(data.get("reasoning", "")),
        "tokens": tokens,
    }


# ---------------------------------------------------------------------------
# Evaluation metrics
# ---------------------------------------------------------------------------

def compute_f1(rows: list[dict], classes: list[str] = ("UP", "DOWN", "FLAT")) -> dict:
    """Compute per-class and macro F1 from forecast rows."""
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
    results["macro_f1"] = np.mean(f1s)
    return results


def classify_return(price_now: float, price_next: float, threshold: float = 0.005) -> str:
    """Classify price change as UP, DOWN, or FLAT."""
    ret = (price_next - price_now) / price_now
    if ret > threshold:
        return "UP"
    elif ret < -threshold:
        return "DOWN"
    else:
        return "FLAT"


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
    """Run the forecasting experiment on completed market simulation data.

    Parameters
    ----------
    results_dir : str
        Directory containing scenario_*.json files from run_market_sim.py.
    n_forecasters : int
        Number of distinct forecaster personas to use (max 10).
    api_key : str
        OpenRouter API key.
    model : str
        Model identifier for OpenRouter (e.g., 'meta-llama/llama-3.1-8b-instruct').
    temperature : float
        LLM temperature.
    history_window : int
        Number of past periods shown to forecasters.
    start_period : int
        First period to forecast from (need enough history).
    output_dir : str or None
        Where to save results (default: {results_dir}/forecasting/).
    tom : bool
        If True, include Theory of Mind context (trading agent persona
        descriptions) in the forecaster prompt.
    persona_list : list[dict] or None
        Custom list of forecaster persona dicts. Each must have keys
        'id', 'name', 'prompt'. If None, uses FORECASTER_PERSONAS.
    """
    results_path = Path(results_dir)
    scenario_files = sorted(results_path.glob("scenario_*.json"))

    if not scenario_files:
        print(f"[ERROR] No scenario files in {results_dir}")
        return {}

    # Select forecaster personas
    available = persona_list if persona_list is not None else FORECASTER_PERSONAS
    personas = available[:n_forecasters]

    # Output directory
    if output_dir is None:
        out_path = results_path / "forecasting"
    else:
        out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    csv_path = out_path / "forecast_results.csv"
    detail_path = out_path / "forecast_details.json"

    print("=" * 70)
    print(f"MARKET FORECASTING EXPERIMENT")
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
        prices = data["price_history"]
        volumes = data["volume_history"]
        fundamentals = data["fundamental_history"]
        n_periods = len(prices)

        # Extract shock info from orders_log
        shock_info_by_period = {}
        for entry in data.get("orders_log", []):
            t = entry.get("period", 0)
            # No shock text stored directly, but we can infer from fundamental changes
            if t > 0:
                fund_change = (fundamentals[t] - fundamentals[t-1]) / fundamentals[t-1]
                if abs(fund_change) > 0.03:
                    direction = "increased" if fund_change > 0 else "decreased"
                    shock_info_by_period[t] = (
                        f"Fundamental value {direction} by {abs(fund_change)*100:.1f}% "
                        f"(now ${fundamentals[t]:.2f})"
                    )

        print(f"\n[{s_idx+1}/{len(scenario_files)}] {sid} ({n_periods} periods)")

        for t in range(start_period, n_periods - 1):
            actual = classify_return(prices[t], prices[t + 1])
            shock_text = shock_info_by_period.get(t, "")

            user_prompt = build_forecast_prompt(
                price_history=prices,
                volume_history=volumes,
                fundamental_history=fundamentals,
                current_period=t,
                shock_info=shock_text,
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
                    # Fallback: uniform direction, last price as point estimate
                    forecast = {
                        "prob_up": 0.333,
                        "prob_down": 0.333,
                        "prob_flat": 0.334,
                        "predicted_price": prices[t],
                        "reasoning": "FALLBACK",
                        "tokens": 0,
                    }
                    source = "fallback"
                else:
                    source = "llm"
                    total_tokens += forecast.get("tokens", 0)

                bs = brier_score(forecast, actual)
                ls = log_score(forecast, actual)

                # Predicted class = highest probability
                pred_class = max(
                    [("UP", forecast["prob_up"]),
                     ("DOWN", forecast["prob_down"]),
                     ("FLAT", forecast["prob_flat"])],
                    key=lambda x: x[1],
                )[0]

                # Price prediction metrics
                actual_price = prices[t + 1]
                pred_price = forecast.get("predicted_price")
                price_error = abs(pred_price - actual_price) if pred_price is not None else None
                price_pct_error = (
                    abs(pred_price - actual_price) / actual_price * 100
                    if pred_price is not None else None
                )

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
                    "predicted_price": round(pred_price, 2) if pred_price is not None else "",
                    "actual_price": round(actual_price, 2),
                    "price_error": round(price_error, 2) if price_error is not None else "",
                    "price_pct_error": round(price_pct_error, 2) if price_pct_error is not None else "",
                    "brier_score": round(bs, 4),
                    "log_score": round(ls, 4),
                    "source": source,
                }
                all_rows.append(row)

                all_details.append({
                    **row,
                    "reasoning": forecast["reasoning"],
                    "actual_return_pct": round(
                        (prices[t+1] - prices[t]) / prices[t] * 100, 2
                    ),
                })

                # Rate limit
                time.sleep(0.5)

            # Progress
            if (t - start_period) % 5 == 0:
                n_done = len(all_rows)
                f1 = compute_f1(all_rows)["macro_f1"]
                bs_mean = np.mean([r["brier_score"] for r in all_rows])
                print(f"  t={t+1:3d} | actual={actual:4s} | "
                      f"running: F1={f1:.3f}, brier={bs_mean:.3f} "
                      f"({n_done} forecasts)")

        # Incremental CSV save after each scenario
        _save_csv(csv_path, all_rows)

    elapsed = time.time() - t0

    # Save detailed results
    with open(detail_path, "w") as f:
        json.dump(all_details, f, indent=2)

    # Compute and print summary
    _print_summary(all_rows, total_calls, total_tokens, elapsed, out_path)

    return {"rows": all_rows, "details": all_details}


def _save_csv(path: Path, rows: list[dict]):
    """Save forecast results to CSV."""
    if not rows:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "scenario_id", "period", "forecaster_id", "actual", "pred_class",
            "correct", "prob_up", "prob_down", "prob_flat",
            "predicted_price", "actual_price", "price_error", "price_pct_error",
            "brier_score", "log_score", "source",
        ])
        writer.writeheader()
        writer.writerows([{k: r[k] for k in writer.fieldnames} for r in rows])


def _print_summary(rows, total_calls, total_tokens, elapsed, out_path):
    """Print experiment summary statistics."""
    if not rows:
        print("\n[WARN] No forecasts completed")
        return

    print(f"\n{'='*70}")
    print("FORECASTING EXPERIMENT SUMMARY")
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
    # Price prediction metrics
    price_errors = [r["price_pct_error"] for r in rows
                    if r["price_pct_error"] != "" and r["price_pct_error"] is not None]
    mae_pct = np.mean(price_errors) if price_errors else float("nan")
    median_pct = np.median(price_errors) if price_errors else float("nan")

    print(f"  Overall accuracy: {acc:.1f}%")
    print(f"  Mean Brier score: {brier:.4f}  (uniform baseline: 0.667)")
    print(f"  Mean log score:   {log_s:.4f}  (uniform baseline: 1.099)")
    print(f"  Price MAE (%):    {mae_pct:.2f}%  (median: {median_pct:.2f}%)")
    print(f"  Price predictions: {len(price_errors)}/{n} returned a price")

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

    # 1. Majority class: always predict the most common class
    majority = max(n_up, n_down, n_flat)
    majority_acc = majority / n * 100
    majority_cls = "UP" if n_up == majority else "DOWN" if n_down == majority else "FLAT"
    # Brier for majority = always put 1.0 on one class
    majority_brier = np.mean([
        brier_score({"prob_up": 1.0 if majority_cls == "UP" else 0.0,
                      "prob_down": 1.0 if majority_cls == "DOWN" else 0.0,
                      "prob_flat": 1.0 if majority_cls == "FLAT" else 0.0}, a)
        for a in actuals
    ])
    print(f"    Majority class ({majority_cls}):  acc={majority_acc:.1f}%, brier={majority_brier:.4f}")

    # 2. Frequency-weighted: predict with class frequency as probabilities
    freq_up, freq_down, freq_flat = n_up / n, n_down / n, n_flat / n
    freq_forecast = {"prob_up": freq_up, "prob_down": freq_down, "prob_flat": freq_flat}
    freq_pred = max(freq_forecast, key=freq_forecast.get).replace("prob_", "").upper()
    freq_brier = np.mean([brier_score(freq_forecast, a) for a in actuals])
    freq_acc = majority_acc  # same as majority for deterministic prediction
    # F1 for frequency-weighted (same pred every time = same as majority)
    freq_rows = [{"pred_class": freq_pred, "actual": a} for a in actuals]
    freq_f1 = compute_f1(freq_rows)["macro_f1"]
    print(f"    Frequency-weighted:    acc={freq_acc:.1f}%, brier={freq_brier:.4f}, F1={freq_f1:.3f}")

    # 3. Persistence: predict previous period's actual direction
    # Group by scenario and sort by period to get previous actual
    persistence_correct = 0
    persistence_brier_total = 0.0
    persistence_rows_for_f1 = []
    persistence_n = 0
    for sid in sorted(set(r["scenario_id"] for r in rows)):
        # Get unique (period, actual) pairs for this scenario
        s_periods = {}
        for r in rows:
            if r["scenario_id"] == sid:
                s_periods[r["period"]] = r["actual"]
        sorted_periods = sorted(s_periods.keys())
        for i, t in enumerate(sorted_periods):
            if i == 0:
                continue  # no previous period to persist from
            prev_actual = s_periods[sorted_periods[i - 1]]
            actual_here = s_periods[t]
            # Persistence forecast: put 1.0 on previous direction
            pers_forecast = {
                "prob_up": 1.0 if prev_actual == "UP" else 0.0,
                "prob_down": 1.0 if prev_actual == "DOWN" else 0.0,
                "prob_flat": 1.0 if prev_actual == "FLAT" else 0.0,
            }
            persistence_correct += int(prev_actual == actual_here)
            persistence_brier_total += brier_score(pers_forecast, actual_here)
            persistence_rows_for_f1.append({"pred_class": prev_actual, "actual": actual_here})
            persistence_n += 1
    if persistence_n > 0:
        pers_acc = persistence_correct / persistence_n * 100
        pers_brier = persistence_brier_total / persistence_n
        pers_f1 = compute_f1(persistence_rows_for_f1)["macro_f1"]
        print(f"    Persistence (last dir): acc={pers_acc:.1f}%, brier={pers_brier:.4f}, F1={pers_f1:.3f}")

    # 4. Uniform: equal 1/3 probability on each class
    uniform_brier = 0.6667
    print(f"    Uniform (1/3 each):    brier={uniform_brier:.4f}")

    # F1 scores
    f1_results = compute_f1(rows)

    print(f"\n  LLM vs baselines:")
    print(f"    vs majority acc:  {acc - majority_acc:+.1f} pp")
    print(f"    vs freq brier:    {brier - freq_brier:+.4f} ({'better' if brier < freq_brier else 'worse'})")
    if persistence_n > 0:
        print(f"    vs persist brier: {brier - pers_brier:+.4f} ({'better' if brier < pers_brier else 'worse'})")
        print(f"    vs persist F1:    {f1_results['macro_f1'] - pers_f1:+.3f} ({'better' if f1_results['macro_f1'] > pers_f1 else 'worse'})")
    print(f"\n  Macro F1: {f1_results['macro_f1']:.3f}")
    print(f"  Per-class F1:")
    print(f"    {'Class':>5s} | {'Prec':>5s} | {'Rec':>5s} | {'F1':>5s}")
    print(f"    {'-----':>5s} | {'-----':>5s} | {'-----':>5s} | {'-----':>5s}")
    for cls in ["UP", "DOWN", "FLAT"]:
        c = f1_results[cls]
        print(f"    {cls:>5s} | {c['precision']:.3f} | {c['recall']:.3f} | {c['f1']:.3f}")

    # Per-forecaster breakdown
    print(f"\n  Per-forecaster performance:")
    print(f"  {'Forecaster':>20s} | {'Acc':>5s} | {'Brier':>6s} | {'F1':>5s} | {'MAE%':>6s} | {'N':>4s}")
    print(f"  {'--------------------':>20s} | {'-----':>5s} | {'------':>6s} | {'-----':>5s} | {'------':>6s} | {'----':>4s}")

    forecaster_ids = sorted(set(r["forecaster_id"] for r in rows))
    for fid in forecaster_ids:
        f_rows = [r for r in rows if r["forecaster_id"] == fid]
        f_acc = np.mean([r["correct"] for r in f_rows]) * 100
        f_brier = np.mean([r["brier_score"] for r in f_rows])
        f_f1 = compute_f1(f_rows)["macro_f1"]
        f_pe = [r["price_pct_error"] for r in f_rows
                if r["price_pct_error"] != "" and r["price_pct_error"] is not None]
        f_mae = np.mean(f_pe) if f_pe else float("nan")
        print(f"  {fid:>20s} | {f_acc:5.1f} | {f_brier:6.4f} | {f_f1:.3f} | {f_mae:5.2f}% | {len(f_rows):4d}")

    # Per-scenario breakdown
    print(f"\n  Per-scenario performance:")
    scenario_ids = sorted(set(r["scenario_id"] for r in rows))
    for sid in scenario_ids:
        s_rows = [r for r in rows if r["scenario_id"] == sid]
        s_acc = np.mean([r["correct"] for r in s_rows]) * 100
        s_brier = np.mean([r["brier_score"] for r in s_rows])
        print(f"    {sid}: acc={s_acc:.1f}%, brier={s_brier:.4f} ({len(s_rows)} forecasts)")

    # Ensemble (average probabilities and prices across forecasters)
    print(f"\n  Ensemble performance (average across forecasters):")
    ensemble_rows = []  # for F1 calculation
    ensemble_brier_total = 0.0
    ensemble_price_errors = []
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

            # Ensemble price prediction
            valid_prices = [r["predicted_price"] for r in period_rows
                           if r["predicted_price"] != "" and r["predicted_price"] is not None]
            if valid_prices:
                ens_price = np.mean(valid_prices)
                actual_price = period_rows[0]["actual_price"]
                ensemble_price_errors.append(
                    abs(ens_price - actual_price) / actual_price * 100
                )

            ensemble_n += 1

    if ensemble_n > 0:
        ens_correct = sum(1 for r in ensemble_rows if r["pred_class"] == r["actual"])
        ens_acc = ens_correct / ensemble_n * 100
        ens_brier = ensemble_brier_total / ensemble_n
        ens_f1 = compute_f1(ensemble_rows)["macro_f1"]
        ens_mae = np.mean(ensemble_price_errors) if ensemble_price_errors else float("nan")
        print(f"    Ensemble accuracy:  {ens_acc:.1f}%")
        print(f"    Ensemble Brier:     {ens_brier:.4f}")
        print(f"    Ensemble macro F1:  {ens_f1:.3f}")
        print(f"    Ensemble price MAE: {ens_mae:.2f}%")
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
        "price_mae_pct": round(mae_pct, 2) if not np.isnan(mae_pct) else None,
        "baselines": {
            "majority_acc": round(majority_acc, 2),
            "majority_brier": round(majority_brier, 4),
            "frequency_brier": round(freq_brier, 4),
            "frequency_f1": round(freq_f1, 4),
            "persistence_acc": round(pers_acc, 2) if persistence_n > 0 else None,
            "persistence_brier": round(pers_brier, 4) if persistence_n > 0 else None,
            "persistence_f1": round(pers_f1, 4) if persistence_n > 0 else None,
            "uniform_brier": 0.6667,
        },
        "ensemble_accuracy": round(ens_acc, 2) if ensemble_n > 0 else None,
        "ensemble_macro_f1": round(ens_f1, 4) if ensemble_n > 0 else None,
        "ensemble_brier": round(ens_brier, 4) if ensemble_n > 0 else None,
        "ensemble_price_mae_pct": round(ens_mae, 2) if ensemble_n > 0 and not np.isnan(ens_mae) else None,
    }
    with open(out_path / "forecast_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Results saved to: {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Market forecasting experiment")
    parser.add_argument("--results-dir", type=str, required=True,
                        help="Directory with completed market sim results")
    parser.add_argument("--n-forecasters", type=int, default=5,
                        help="Number of forecaster personas (max 10)")
    parser.add_argument("--model", type=str, default="llama",
                        choices=["llama", "deepseek", "claude", "qwen"],
                        help="LLM model for forecasters")
    parser.add_argument("--tom", action="store_true",
                        help="Enable Theory of Mind (show agent personas to forecasters)")
    parser.add_argument("--persona-type", type=str, default="strategy",
                        choices=["strategy", "demographic"],
                        help="Persona type: 'strategy' (analytical styles) or 'demographic' (people)")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--history-window", type=int, default=10,
                        help="Periods of history to show forecasters")
    parser.add_argument("--start-period", type=int, default=5,
                        help="First period to forecast from")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: {results-dir}/forecasting/)")
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
            from forecasting.config import OPENROUTER_API_KEY
            api_key = OPENROUTER_API_KEY
        except ImportError:
            pass
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set")
        sys.exit(1)

    # Select persona list
    persona_list = DEMOGRAPHIC_PERSONAS if args.persona_type == "demographic" else FORECASTER_PERSONAS

    # Auto-generate output dir name from conditions
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
