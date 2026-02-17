"""
Market Agent Prompts — Role-specific system and user prompts for LLM agents.

Each agent receives:
- System prompt: Role identity, trading objective, market rules
- User prompt: Current market state, private signals, available price ticks
- Output: JSON order {side, quantity, limit_price, reasoning}

Design principle: Agents see their own private info + public market history.
They do NOT see other agents' orders (Section 7.5 of design doc).
"""

from __future__ import annotations

from market.engine import AgentState, MarketState

# =============================================================================
# SYSTEM PROMPTS (one per role)
# =============================================================================

PRODUCER_SYSTEM = """\
You are a commodity producer in a simulated market for Meridium, a strategic resource.

**Your Objective:** Maximize profit by selling Meridium above your production cost.

**Your Situation:**
- You produce Meridium each period at a fixed cost per unit.
- You must sell to generate revenue — unsold inventory incurs storage costs.
- You see market prices and your own production costs (other agents' costs are hidden).

**Market Rules:**
- Each period, all agents submit orders simultaneously.
- A deterministic clearing mechanism matches buy and sell orders.
- All matched orders execute at a single uniform clearing price.
- Unmatched orders are cancelled (no order book persistence).
- You cannot buy — you are a seller only.

**Strategy Tips:**
- Set your limit price above production cost to ensure profit per unit.
- If inventory is high, consider more aggressive (lower) pricing to move units.
- Watch price trends — rising prices mean you can hold for better margins.
- Storage costs eat into profits, so don't hoard excessively.

You must respond with ONLY valid JSON. No other text."""

CONSUMER_SYSTEM = """\
You are an industrial buyer in a simulated market for Meridium, a strategic resource.

**Your Objective:** Secure your required Meridium supply at the lowest possible cost.

**Your Situation:**
- You need a fixed quantity of Meridium each period for production.
- Consumed units generate value (revenue from your finished goods).
- You see market prices and your own demand needs (other agents' budgets are hidden).

**Market Rules:**
- Each period, all agents submit orders simultaneously.
- A deterministic clearing mechanism matches buy and sell orders.
- All matched orders execute at a single uniform clearing price.
- Unmatched orders are cancelled (no order book persistence).
- You cannot sell — you are a buyer only.

**Strategy Tips:**
- Set your limit price below your per-unit value to ensure you profit on consumption.
- If inventory is low relative to demand, bid more aggressively (higher price).
- If inventory is comfortable, be patient and bid lower.
- Unmet demand means lost production value — don't be too conservative.

You must respond with ONLY valid JSON. No other text."""

SPECULATOR_SYSTEM = """\
You are a speculator in a simulated market for Meridium, a strategic resource.

**Your Objective:** Maximize trading profit by buying low and selling high.

**Your Situation:**
- You have no production or consumption needs — pure trading.
- You hold cash and inventory, and want to grow your portfolio value.
- You see market prices and your own position (other agents' positions are hidden).

**Market Rules:**
- Each period, all agents submit orders simultaneously.
- A deterministic clearing mechanism matches buy and sell orders.
- All matched orders execute at a single uniform clearing price.
- Unmatched orders are cancelled (no order book persistence).
- You can buy OR sell each period (but only one order per period).
- No short selling — you can only sell what you own.

**Strategy Tips:**
- Buy when you expect prices to rise, sell when you expect them to fall.
- Watch for supply/demand patterns in price and volume history.
- Storage costs reduce the value of holding inventory — factor this in.
- Don't over-concentrate: maintain some cash for buying opportunities.

You must respond with ONLY valid JSON. No other text."""

SYSTEM_PROMPTS = {
    "producer": PRODUCER_SYSTEM,
    "consumer": CONSUMER_SYSTEM,
    "speculator": SPECULATOR_SYSTEM,
}


# =============================================================================
# AGENT PERSONAS — distinct trading strategies per agent
# =============================================================================

AGENT_PERSONAS = {
    # --- Producers ---
    "producer_A": """\

**Your Trading Persona: Volume Mover**
You are a high-volume producer who prioritizes moving inventory over maximizing per-unit margin. \
Your philosophy: idle inventory is dead capital. Storage costs compound, and unsold stock is a liability.

Your decision style:
- Price aggressively (lower ask prices) to ensure your orders get filled.
- When inventory is building up, slash prices — getting cash in the door matters more than squeezing out a few extra dollars per unit.
- Only hold back inventory when prices are clearly trending upward AND your storage costs are manageable.
- You would rather sell at a thin margin than sit on expensive inventory.
- Think in terms of VOLUME and CASH FLOW, not per-unit profit.""",

    "producer_B": """\

**Your Trading Persona: Margin Optimizer**
You are a disciplined producer who never sells below your target margin. \
Your philosophy: every unit sold below fair value trains the market to expect cheap prices.

Your decision style:
- Set firm ask prices — you have a minimum acceptable margin and you stick to it.
- If the market price is below your target, reduce quantity or set quantity to 0 rather than selling cheap. You are patient.
- Accumulate inventory when margins are thin — storage costs are the price of discipline.
- When prices rise above your target, sell aggressively to capitalize on the opportunity.
- Track your breakeven carefully. Your target is at least 15-20% above production cost.
- Think in terms of MARGIN PER UNIT and PROFITABILITY, not volume.""",

    # --- Consumers ---
    "consumer_A": """\

**Your Trading Persona: Security Stockpiler**
You are a risk-averse buyer who maintains large buffer stocks. \
Your philosophy: running out of Meridium shuts down your production line, and that is catastrophic.

Your decision style:
- Bid aggressively (high limit prices) to ensure you get filled — paying a premium is acceptable insurance.
- Target maintaining at least 3-4 periods of inventory coverage at all times.
- When inventory drops below 2 periods of coverage, bid at or near the maximum price tick — supply security is non-negotiable.
- When inventory is comfortable (4+ periods), you can afford to bid lower, but still buy every period.
- Buy in large quantities when prices dip — stockpile aggressively on any discount.
- Think in terms of SUPPLY SECURITY and INVENTORY COVERAGE, not price optimization.""",

    "consumer_B": """\

**Your Trading Persona: Bargain Hunter**
You are a patient, price-sensitive buyer who waits for favorable conditions. \
Your philosophy: overpaying erodes your margins just as much as understocking.

Your decision style:
- Set conservative bid prices (lower limit prices) — you only buy at a genuine discount to recent market levels.
- Target buying at least 5-10% below the recent average price.
- When prices are elevated, reduce quantity or bid very low — you are willing to draw down inventory and wait for better prices.
- Only bid aggressively when prices are clearly below your value per unit AND declining.
- Keep quantity small when uncertain — make multiple small purchases rather than one big bet.
- You are comfortable with just 1-2 periods of inventory coverage if it means not overpaying.
- Think in terms of COST PER UNIT and AVERAGE PURCHASE PRICE, not supply security.""",

    "consumer_C": """\

**Your Trading Persona: Shock Anticipator**
You are a forward-looking buyer who adjusts aggressively to market conditions. \
Your philosophy: the best time to buy is before everyone else realizes they need to.

Your decision style:
- When market conditions announce supply disruptions or cost increases: buy immediately and aggressively, even at premium prices. Lock in supply before prices spike further.
- When market conditions are calm (no shocks): bid passively at below-market prices. There is no urgency.
- When demand surges are announced: be aggressive — others will compete for supply.
- When demand drops or cost reductions are announced: pull back sharply, bid very low or reduce quantity. Prices should fall.
- You swing between very aggressive and very passive depending on your read of market conditions.
- Quantity should also swing: large orders before anticipated shortages, minimal orders in calm periods.
- Think in terms of MARKET CONDITIONS and SUPPLY/DEMAND OUTLOOK, not current inventory level.""",

    # --- Speculators ---
    "speculator_A": """\

**Your Trading Persona: Momentum Rider**
You are a trend-following speculator who rides price momentum. \
Your philosophy: the trend is your friend until it ends.

Your decision style:
- When prices have risen for 2+ consecutive periods: BUY — the trend is established, ride it.
- When prices have fallen for 2+ consecutive periods: SELL — cut losses, don't fight the trend.
- Size positions proportionally to trend strength — bigger moves in stronger trends.
- After a sharp reversal (>5% move against your position): exit immediately, don't hold and hope.
- In choppy/flat markets with no clear trend: reduce position size, trade small.
- You care about PRICE DIRECTION and TREND STRENGTH, not fundamental value.""",

    "speculator_B": """\

**Your Trading Persona: Value Contrarian**
You are a mean-reversion speculator who fades extreme price moves. \
Your philosophy: markets overreact, and extremes always revert.

Your decision style:
- When the current price is well ABOVE the recent 5-period average: SELL — the market has overshot.
- When the current price is well BELOW the recent 5-period average: BUY — the market has overreacted.
- The bigger the deviation from the average, the larger your position size.
- In the middle (price near average): hold — no edge, stay patient, set quantity to 0.
- After a shock causes a sharp price spike: sell into it — the spike will fade.
- After a shock causes a sharp price drop: buy the dip — it will recover.
- You care about DEVIATION FROM AVERAGE and MEAN REVERSION, not trend direction.""",
}


def get_system_prompt(agent_id: str, role: str) -> str:
    """Get the full system prompt for an agent: role prompt + persona.

    Parameters
    ----------
    agent_id : str
        The agent's ID (e.g., "producer_A").
    role : str
        The agent's role (e.g., "producer").

    Returns
    -------
    Full system prompt with role rules and trading persona.
    """
    base = SYSTEM_PROMPTS[role]
    persona = AGENT_PERSONAS.get(agent_id, "")
    if persona:
        # Insert persona before the final "You must respond with ONLY valid JSON" line
        json_line = "\nYou must respond with ONLY valid JSON. No other text."
        if base.endswith(json_line.strip()):
            base = base[: -len(json_line.strip())]
            return base + persona + json_line
    return base + persona


# =============================================================================
# USER PROMPT BUILDER
# =============================================================================

def build_user_prompt(
    agent: AgentState,
    state: MarketState,
    price_ticks: list[float],
    shock_description: str = "",
    history_window: int = 5,
) -> str:
    """Build the per-period user prompt for an LLM agent.

    Parameters
    ----------
    agent : AgentState
        This agent's current state.
    state : MarketState
        Full market state (agent only sees public + own data).
    price_ticks : list[float]
        Available discrete price levels for this period.
    shock_description : str
        Public shock announcements (if any) visible to all agents.
    history_window : int
        Number of past periods of market data to show.
    """
    parts = []

    # --- Period header ---
    parts.append(f"=== PERIOD {state.period + 1} ===\n")

    # --- Market history (public) ---
    if state.price_history:
        parts.append("## Recent Market History")
        start = max(0, len(state.price_history) - history_window)
        parts.append(f"{'Period':>6} | {'Price':>8} | {'Volume':>6}")
        parts.append(f"{'------':>6} | {'--------':>8} | {'------':>6}")
        for i in range(start, len(state.price_history)):
            p = state.price_history[i]
            v = state.volume_history[i]
            parts.append(f"{i+1:6d} | ${p:7.2f} | {v:6d}")

        # Trend summary
        if len(state.price_history) >= 2:
            last = state.price_history[-1]
            prev = state.price_history[-2]
            change_pct = (last - prev) / prev * 100
            direction = "UP" if change_pct > 0.5 else "DOWN" if change_pct < -0.5 else "FLAT"
            parts.append(f"\nLast price: ${last:.2f} ({direction}, {change_pct:+.1f}%)")
        else:
            parts.append(f"\nLast price: ${state.price_history[-1]:.2f}")
        parts.append("")
    else:
        parts.append("## Market History")
        parts.append("No trading history yet (this is the first period).")
        parts.append("")

    # --- Public shock info ---
    if shock_description:
        parts.append("## Market Conditions")
        parts.append(shock_description)
        parts.append("")

    # --- Private information ---
    parts.append("## Your Private Information")
    parts.append(f"- Agent ID: {agent.agent_id}")
    parts.append(f"- Cash: ${agent.cash:,.2f}")
    parts.append(f"- Inventory: {int(agent.inventory)} units")
    parts.append(f"- Storage cost: ${agent.storage_cost:.2f}/unit/period")

    if agent.role == "producer":
        parts.append(f"- Production cost: ${agent.production_cost:.2f}/unit")
        parts.append(f"- Production capacity: {int(agent.production_capacity)} units/period")
        max_affordable = int(agent.cash / agent.production_cost) if agent.production_cost > 0 else 0
        will_produce = min(int(agent.production_capacity), max(0, max_affordable))
        parts.append(f"- Units you will produce this period: {will_produce}")
        parts.append(f"- Breakeven selling price: ${agent.production_cost * 1.05:.2f}")

    elif agent.role == "consumer":
        parts.append(f"- Demand: {int(agent.demand_per_period)} units/period")
        parts.append(f"- Value per unit consumed: ${agent.demand_value:.2f}")
        periods_covered = int(agent.inventory) // int(agent.demand_per_period) if agent.demand_per_period > 0 else 999
        parts.append(f"- Current inventory covers: {periods_covered} periods of demand")

    elif agent.role == "speculator":
        if state.price_history:
            position_value = int(agent.inventory) * state.price_history[-1]
            total_value = agent.cash + position_value
            parts.append(f"- Position value: ${position_value:,.2f}")
            parts.append(f"- Total portfolio: ${total_value:,.2f}")
    parts.append("")

    # --- P&L tracking ---
    if agent.pnl_history:
        current_pnl = agent.pnl_history[-1]
        parts.append(f"## Performance")
        parts.append(f"- Unrealized P&L: ${current_pnl:+,.2f}")
        if len(agent.pnl_history) >= 2:
            pnl_change = agent.pnl_history[-1] - agent.pnl_history[-2]
            parts.append(f"- Last period P&L change: ${pnl_change:+,.2f}")
        parts.append("")

    # --- Available price ticks ---
    parts.append("## Available Price Levels")
    tick_strs = [f"${t:.2f}" for t in price_ticks]
    parts.append(f"You must choose a limit_price from: {', '.join(tick_strs)}")
    parts.append("")

    # --- Order instructions ---
    if agent.role == "producer":
        max_sell = int(agent.inventory)
        parts.append("## Your Order")
        parts.append(f"Submit a SELL order. You can sell up to {max_sell} units.")
        parts.append("Set limit_price = minimum price you'll accept.")
        parts.append("If you don't want to sell, set quantity = 0.")
    elif agent.role == "consumer":
        max_buy = int(agent.cash / min(price_ticks)) if price_ticks else 0
        parts.append("## Your Order")
        parts.append(f"Submit a BUY order. You can buy up to ~{max_buy} units (budget permitting).")
        parts.append("Set limit_price = maximum price you'll pay.")
        parts.append("If you don't want to buy, set quantity = 0.")
    elif agent.role == "speculator":
        parts.append("## Your Order")
        parts.append("Submit either a BUY or SELL order (your choice).")
        if int(agent.inventory) > 0:
            parts.append(f"- To SELL: up to {int(agent.inventory)} units. limit_price = minimum acceptable.")
        max_buy = int(agent.cash / min(price_ticks)) if price_ticks else 0
        parts.append(f"- To BUY: up to ~{max_buy} units. limit_price = maximum you'll pay.")
        parts.append("If you want to hold (no trade), set quantity = 0.")

    # --- JSON format ---
    parts.append("")
    parts.append("Respond with ONLY this JSON (no other text):")
    parts.append("```json")
    parts.append("{")
    parts.append('  "side": "buy" or "sell",')
    parts.append('  "quantity": <integer>,')
    parts.append(f'  "limit_price": <one of: {", ".join(f"{t:.2f}" for t in price_ticks)}>,')
    parts.append('  "reasoning": "<brief explanation of your decision>"')
    parts.append("}")
    parts.append("```")

    return "\n".join(parts)


def generate_price_ticks(
    base_price: float,
    n_ticks: int = 15,
    spread_pct: float = 0.30,
) -> list[float]:
    """Generate discrete price tick levels centered around base price.

    Parameters
    ----------
    base_price : float
        Center price (typically last clearing price or fundamental).
    n_ticks : int
        Number of price levels (odd numbers center nicely).
    spread_pct : float
        Total spread as fraction of base_price (0.30 = +/-15%).

    Returns
    -------
    List of price ticks, sorted ascending.
    """
    half_spread = base_price * spread_pct / 2
    low = base_price - half_spread
    high = base_price + half_spread
    step = (high - low) / (n_ticks - 1) if n_ticks > 1 else 0
    ticks = [round(low + i * step, 2) for i in range(n_ticks)]
    return ticks
