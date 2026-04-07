"""
Domain Adapters — MarketDomain and ConflictDomain.

Encapsulate domain-specific data loading, prompt building, and evaluation
so that the forecasting framework is domain-agnostic.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

# Project root for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from causal_discovery.ground_truth import (
    MARKET_VARIABLES,
    CONFLICT_VARIABLES,
    get_market_ground_truth,
    get_conflict_ground_truth,
)


# ---------------------------------------------------------------------------
# Market Domain
# ---------------------------------------------------------------------------

class MarketDomain:
    name = "market"
    target_variable = "clearing_price"
    target_key = "predicted_price"          # JSON key in LLM response
    direction_threshold = 0.005             # 0.5% for UP/DOWN/FLAT
    variables = MARKET_VARIABLES

    # --- Data loading ---

    def load_scenarios(self, data_dir: Path) -> list[dict]:
        """Load scenario JSON files from a baseline output directory."""
        files = sorted(data_dir.glob("scenario_*.json"))
        scenarios = []
        for f in files:
            with open(f) as fh:
                scenarios.append(json.load(fh))
        return scenarios

    def get_n_periods(self, scenario: dict) -> int:
        return len(scenario["price_history"])

    def get_target_history(self, scenario: dict) -> list[float]:
        return scenario["price_history"]

    def get_actual(self, scenario: dict, period: int) -> float:
        return scenario["price_history"][period]

    def classify_direction(self, current: float, next_val: float) -> str:
        ret = (next_val - current) / current
        if ret > self.direction_threshold:
            return "UP"
        elif ret < -self.direction_threshold:
            return "DOWN"
        return "FLAT"

    # --- Prompt building ---

    def build_base_prompt(
        self, scenario: dict, period: int, window: int = 10,
    ) -> str:
        """Build the base user prompt for forecasting at period t.

        Shows price/volume/fundamental history up to t, summary stats.
        Pattern from market/run_market_forecast.py:build_forecast_prompt.
        """
        prices = scenario["price_history"]
        volumes = scenario["volume_history"]
        fundamentals = scenario["fundamental_history"]

        parts = []
        parts.append(
            f"=== FORECAST REQUEST: Period {period + 1} -> {period + 2} ===\n"
        )

        start = max(0, period + 1 - window)
        end = period + 1

        parts.append("## Market History")
        parts.append(
            f"{'Period':>6} | {'Price':>8} | {'Volume':>6} | "
            f"{'Fundamental':>12} | {'Return':>8}"
        )
        parts.append(
            f"{'------':>6} | {'--------':>8} | {'------':>6} | "
            f"{'------------':>12} | {'--------':>8}"
        )

        for i in range(start, end):
            p = prices[i]
            v = volumes[i]
            f_val = fundamentals[i]
            if i > 0:
                ret = (prices[i] - prices[i - 1]) / prices[i - 1] * 100
                ret_str = f"{ret:+7.2f}%"
            else:
                ret_str = "    n/a"
            parts.append(
                f"{i+1:6d} | ${p:7.2f} | {int(v):6d} | "
                f"${f_val:11.2f} | {ret_str}"
            )

        # Summary statistics
        prices_visible = prices[start:end]
        if len(prices_visible) >= 2:
            parts.append("\n## Summary Statistics")
            avg = np.mean(prices_visible)
            std = np.std(prices_visible)
            last = prices_visible[-1]
            prev = prices_visible[-2]
            last_ret = (last - prev) / prev * 100
            direction = (
                "UP" if last_ret > 0.5
                else "DOWN" if last_ret < -0.5
                else "FLAT"
            )

            parts.append(f"- Current price: ${last:.2f} ({direction}, {last_ret:+.1f}%)")
            parts.append(f"- {len(prices_visible)}-period average: ${avg:.2f}")
            parts.append(f"- Price std: ${std:.2f}")
            parts.append(
                f"- Price vs fundamental: "
                f"${last - fundamentals[period]:+.2f} "
                f"({'above' if last > fundamentals[period] else 'below'} fundamental)"
            )

            returns = [
                (prices_visible[j] - prices_visible[j - 1]) / prices_visible[j - 1]
                for j in range(1, len(prices_visible))
            ]
            up_periods = sum(1 for r in returns if r > 0.005)
            down_periods = sum(1 for r in returns if r < -0.005)
            flat_periods = len(returns) - up_periods - down_periods
            parts.append(
                f"- Recent periods: {up_periods} up, {down_periods} down, "
                f"{flat_periods} flat"
            )

            streak = 0
            if returns:
                last_dir = (
                    "up" if returns[-1] > 0.005
                    else "down" if returns[-1] < -0.005
                    else "flat"
                )
                for r in reversed(returns):
                    d = (
                        "up" if r > 0.005
                        else "down" if r < -0.005
                        else "flat"
                    )
                    if d == last_dir:
                        streak += 1
                    else:
                        break
                parts.append(f"- Current streak: {streak} consecutive {last_dir} period(s)")

        # Shock info from fundamental changes
        if period > 0:
            fund_change = (fundamentals[period] - fundamentals[period - 1]) / fundamentals[period - 1]
            if abs(fund_change) > 0.03:
                direction = "increased" if fund_change > 0 else "decreased"
                parts.append("\n## Active Market Conditions")
                parts.append(
                    f"Fundamental value {direction} by {abs(fund_change)*100:.1f}% "
                    f"(now ${fundamentals[period]:.2f})"
                )

        parts.append(f"\n## Your Prediction")
        parts.append(
            f"Predict the price direction from period {period + 1} to {period + 2}."
        )
        parts.append("UP = price increases by more than 0.5%")
        parts.append("DOWN = price decreases by more than 0.5%")
        parts.append("FLAT = price changes by less than 0.5%")

        return "\n".join(parts)

    # --- Expanded variables for L1/L2/L3 ---

    def get_expanded_variables(self, scenario: dict, period: int) -> dict[str, float]:
        """Return all observable variables at period t for info-level enrichment."""
        orders_log = scenario.get("orders_log", [])
        entry = orders_log[period] if period < len(orders_log) else {}

        prices = scenario["price_history"]
        volumes = scenario["volume_history"]
        fundamentals = scenario["fundamental_history"]

        result = {
            "clearing_price": prices[period],
            "volume": volumes[period],
            "fundamental_price": fundamentals[period],
        }

        # Augmented fields (from Phase 0b)
        if "avg_bid_price" in entry:
            result["avg_bid_price"] = entry["avg_bid_price"]
        if "avg_ask_price" in entry:
            result["avg_ask_price"] = entry["avg_ask_price"]
        if "total_bid_qty" in entry:
            result["total_bid_qty"] = entry["total_bid_qty"]
        if "total_ask_qty" in entry:
            result["total_ask_qty"] = entry["total_ask_qty"]

        # Agent state aggregates
        agent_states = entry.get("agent_states", {})
        if agent_states:
            all_cash = [s["cash"] for s in agent_states.values()]
            all_inv = [s["inventory"] for s in agent_states.values()]
            result["total_cash"] = round(sum(all_cash), 2)
            result["total_inventory"] = sum(all_inv)
            result["mean_cash"] = round(np.mean(all_cash), 2)
            result["mean_inventory"] = round(np.mean(all_inv), 2)

        # Derived: price vs fundamental spread
        if fundamentals[period] > 0:
            result["price_fundamental_spread"] = round(
                (prices[period] - fundamentals[period]) / fundamentals[period], 4
            )

        # Derived: return if period > 0
        if period > 0:
            result["last_return"] = round(
                (prices[period] - prices[period - 1]) / prices[period - 1], 4
            )

        return result

    # --- Causal graph ---

    def get_causal_graph(self) -> tuple[np.ndarray, list[str]]:
        return get_market_ground_truth(), MARKET_VARIABLES

    def get_mechanistic_tom(self) -> str:
        """Return rule-based agent decision rules for L3 prompts."""
        return """\

## Agent Decision Rules (Mechanistic Theory of Mind)

These rule-based agents determine orders deterministically:

**Producers (sell only):**
- Set ask price = production_cost × (1 + margin), where margin depends on inventory level
- When inventory > 2× production rate: slash margin to move goods (aggressive selling)
- When inventory is low: hold firm on 15-20% margins above production cost
- Quantity = min(production_per_period, inventory)

**Consumers (buy only):**
- Set bid price = demand_value × (1 - discount), discount depends on inventory needs
- When inventory < demand_per_period: bid aggressively (up to demand_value)
- When well-stocked: reduce bid to 5-10% below market, may skip buying
- Quantity = demand_per_period (capped by cash / bid_price)

**Speculators (buy or sell):**
- Compare current price to moving average of recent prices
- If price > moving average: sell (mean reversion expectation)
- If price < moving average: buy
- Position size proportional to deviation magnitude
- Exit on sharp reversals (> 3% contra move)

**Key mechanistic interactions:**
- Clearing price is where cumulative buy orders intersect cumulative sell orders
- If total_bid_qty > total_ask_qty: upward price pressure
- If total_ask_qty > total_bid_qty: downward price pressure
- Agent cash and inventory constrain order sizes (budget constraint is hard)
"""

    def get_system_prompt(self, persona_prompt: str = "") -> str:
        """Return the system prompt for a market forecaster."""
        return f"""\
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

    def parse_point_estimate(self, data: dict) -> float | None:
        """Extract point estimate from parsed LLM response."""
        val = data.get("predicted_price")
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    def point_estimate_error(self, predicted: float, actual: float) -> dict:
        """Compute point estimate error metrics."""
        error = abs(predicted - actual)
        pct_error = error / actual * 100 if actual != 0 else float("inf")
        return {
            "value_error": round(error, 4),
            "value_pct_error": round(pct_error, 4),
        }


# ---------------------------------------------------------------------------
# Conflict Domain
# ---------------------------------------------------------------------------

class ConflictDomain:
    name = "conflict"
    target_variable = "escalation_index"
    target_key = "predicted_ei"
    direction_threshold = 0.1               # 0.1 for UP/DOWN/FLAT
    variables = CONFLICT_VARIABLES

    # --- Data loading ---

    def load_scenarios(self, data_dir: Path) -> list[dict]:
        files = sorted(data_dir.glob("scenario_*.json"))
        scenarios = []
        for f in files:
            with open(f) as fh:
                scenarios.append(json.load(fh))
        return scenarios

    def get_n_periods(self, scenario: dict) -> int:
        return len(scenario["escalation_history"])

    def get_target_history(self, scenario: dict) -> list[float]:
        return scenario["escalation_history"]

    def get_actual(self, scenario: dict, period: int) -> float:
        return scenario["escalation_history"][period]

    def classify_direction(self, current: float, next_val: float) -> str:
        delta = next_val - current
        if delta > self.direction_threshold:
            return "UP"
        elif delta < -self.direction_threshold:
            return "DOWN"
        return "FLAT"

    # --- Prompt building ---

    def build_base_prompt(
        self, scenario: dict, period: int, window: int = 10,
    ) -> str:
        """Build the base user prompt for conflict forecasting at period t.

        Pattern from conflict/run_conflict_forecast.py:build_forecast_prompt.
        """
        ei_history = scenario["escalation_history"]
        actions_log = scenario.get("actions_log", [])

        parts = []
        parts.append(
            f"=== FORECAST REQUEST: Period {period + 1} -> {period + 2} ===\n"
        )

        start = max(0, period + 1 - window)
        end = period + 1

        parts.append("## Escalation History")
        parts.append(
            f"{'Period':>6} | {'EI':>6} | {'Change':>8} | "
            f"{'Novaris Action':>20} | {'Tethys Action':>20}"
        )
        parts.append(
            f"{'------':>6} | {'------':>6} | {'--------':>8} | "
            f"{'--------------------':>20} | {'--------------------':>20}"
        )

        for i in range(start, end):
            ei = ei_history[i]
            if i > 0:
                delta = ei_history[i] - ei_history[i - 1]
                delta_str = f"{delta:+7.2f}"
            else:
                delta_str = "    n/a"

            if i < len(actions_log):
                nov_act = actions_log[i].get("novaris_action", "n/a")
                teth_act = actions_log[i].get("tethys_action", "n/a")
            else:
                nov_act = "n/a"
                teth_act = "n/a"

            parts.append(
                f"{i+1:6d} | {ei:6.2f} | {delta_str} | "
                f"{nov_act:>20} | {teth_act:>20}"
            )

        # Summary statistics
        ei_visible = ei_history[start:end]
        if len(ei_visible) >= 2:
            parts.append("\n## Summary Statistics")
            avg = np.mean(ei_visible)
            std = np.std(ei_visible)
            last = ei_visible[-1]
            prev = ei_visible[-2]
            last_change = last - prev
            direction = (
                "ESCALATING" if last_change > 0.1
                else "DE-ESCALATING" if last_change < -0.1
                else "STABLE"
            )

            parts.append(
                f"- Current Escalation Index: {last:.2f}/10.0 "
                f"({direction}, {last_change:+.2f})"
            )
            parts.append(f"- {len(ei_visible)}-period average: {avg:.2f}")
            parts.append(f"- EI std: {std:.2f}")

            changes = [
                ei_visible[j] - ei_visible[j - 1]
                for j in range(1, len(ei_visible))
            ]
            up_periods = sum(1 for c in changes if c > 0.1)
            down_periods = sum(1 for c in changes if c < -0.1)
            flat_periods = len(changes) - up_periods - down_periods
            parts.append(
                f"- Recent periods: {up_periods} escalating, "
                f"{down_periods} de-escalating, {flat_periods} stable"
            )

            streak = 0
            if changes:
                last_dir = (
                    "up" if changes[-1] > 0.1
                    else "down" if changes[-1] < -0.1
                    else "flat"
                )
                for c in reversed(changes):
                    d = (
                        "up" if c > 0.1
                        else "down" if c < -0.1
                        else "flat"
                    )
                    if d == last_dir:
                        streak += 1
                    else:
                        break
                parts.append(f"- Current streak: {streak} consecutive {last_dir} period(s)")

        # State info from augmented log
        if period < len(actions_log):
            entry = actions_log[period]
            state_keys = [
                "military_balance", "territory_controlled",
                "sanctions_level", "international_support",
            ]
            state_vals = {k: entry[k] for k in state_keys if k in entry}
            if state_vals:
                parts.append("\n## Current Conflict State")
                for key, val in state_vals.items():
                    parts.append(f"- {key.replace('_', ' ').title()}: {val}")

        parts.append(f"\n## Your Prediction")
        parts.append(
            f"Predict the escalation change from period {period + 1} to {period + 2}."
        )
        parts.append("UP = escalation index increases by more than 0.1")
        parts.append("DOWN = escalation index decreases by more than 0.1")
        parts.append("FLAT = escalation index changes by less than 0.1")

        return "\n".join(parts)

    # --- Expanded variables for L1/L2/L3 ---

    def get_expanded_variables(self, scenario: dict, period: int) -> dict[str, float]:
        """Return all observable variables at period t."""
        actions_log = scenario.get("actions_log", [])
        entry = actions_log[period] if period < len(actions_log) else {}
        ei_history = scenario["escalation_history"]

        result = {
            "escalation_index": ei_history[period],
        }

        # Augmented fields (from Phase 0a)
        augmented_keys = [
            "military_balance", "territory_controlled",
            "sanctions_level", "international_support",
            "novaris_resources", "tethys_resources",
            "novaris_gdp", "tethys_gdp",
            "novaris_military_strength", "tethys_military_strength",
            "novaris_political_stability", "tethys_political_stability",
        ]
        for k in augmented_keys:
            if k in entry:
                result[k] = entry[k]

        # Derived: EI change
        if period > 0:
            result["last_ei_change"] = round(
                ei_history[period] - ei_history[period - 1], 4
            )

        # Actions
        if "novaris_action" in entry:
            result["novaris_action"] = entry["novaris_action"]
        if "tethys_action" in entry:
            result["tethys_action"] = entry["tethys_action"]

        return result

    # --- Causal graph ---

    def get_causal_graph(self) -> tuple[np.ndarray, list[str]]:
        return get_conflict_ground_truth(), CONFLICT_VARIABLES

    def get_mechanistic_tom(self) -> str:
        """Return rule-based agent decision rules for L3 prompts."""
        return """\

## Agent Decision Rules (Mechanistic Theory of Mind)

Each faction has agents with hawk_dove scores (0=dove, 1=hawk) that deterministically \
select actions:

**Decision Rule:**
1. Compute `target_delta` from hawk_score and current escalation_index:
   - Hawks (score > 0.6): target_delta = +0.5 to +1.5 (push for escalation)
   - Moderates (0.4-0.6): target_delta = -0.2 to +0.3 (mild tendency)
   - Doves (score < 0.4): target_delta = -1.0 to -0.3 (push for de-escalation)
2. Select action from ACTION_SPACE whose `escalation_delta` best matches target_delta
3. If faction resources < 30% of initial: shift 0.3 toward de-escalation (cost pressure)

**Aggregation:**
- Each faction's action = weighted average of member recommendations
- Weights by role: military_commander > political_leader > diplomat > intelligence_chief
- Final faction action = closest discrete action to weighted average

**Escalation Index Update:**
- Base: EI_new = EI_old + novaris_delta + tethys_delta
- Interaction modifier: mutual escalation ×1.2, mixed ×0.8, mutual de-escalation ×1.3
- EI-dependent compression: changes compressed at extremes (near 0 or 10)
- Shocks add direct EI offsets (border_incident: +0.5, peace_initiative: -0.8, etc.)

**State Updates:**
- High EI damages GDP, reduces political stability
- Military actions adjust military_strength, territory_controlled
- Novaris escalation increases sanctions_level, tethys international_support
- GDP drives resource regeneration; sanctions damage GDP
"""

    def get_system_prompt(self, persona_prompt: str = "") -> str:
        """Return the system prompt for a conflict forecaster."""
        return f"""\
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

    def parse_point_estimate(self, data: dict) -> float | None:
        val = data.get("predicted_ei")
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    def point_estimate_error(self, predicted: float, actual: float) -> dict:
        error = abs(predicted - actual)
        return {
            "value_error": round(error, 4),
            "value_pct_error": round(error / max(actual, 0.01) * 100, 4),
        }


# ---------------------------------------------------------------------------
# Domain registry
# ---------------------------------------------------------------------------

DOMAINS = {
    "market": MarketDomain,
    "conflict": ConflictDomain,
}


def get_domain(name: str) -> MarketDomain | ConflictDomain:
    cls = DOMAINS.get(name)
    if cls is None:
        raise ValueError(f"Unknown domain: {name}. Choose from {list(DOMAINS)}")
    return cls()
