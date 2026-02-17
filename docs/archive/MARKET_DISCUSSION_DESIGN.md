# Market Discussion Phase: Pre-Trade Communication Design

**Status:** Design sketch (not yet implemented)
**Date:** February 2026
**Depends on:** Market simulation (Phases 1-4 complete)

## Motivation

Currently, trading agents act independently: they see market history and their own state, submit orders, and the market clears. There is no direct communication between agents.

Real markets often have communication channels — open outcry floors, pre-market chatter, analyst calls, chat rooms. Adding a discussion phase tests whether explicit communication improves on the emergent coordination that personas already create, or whether it enables collusion and manipulation.

### Research Questions

1. **Price efficiency:** Does discussion move prices closer to fundamental value?
2. **Bluffing:** Do agents strategically misrepresent their intentions?
3. **Synergy:** Does communication increase or decrease PID emergence capacity?
4. **Collusion:** Can producers coordinate to hold margins? Can consumers coordinate to push prices down?
5. **Manipulation:** Can speculators profit by misleading others through cheap talk?

## Design

### Modified Period Flow

```
Current:
  1. Apply shocks → 2. Generate ticks → 3. Collect orders → 4. Clear → 5. Fill → 6. Costs → 7. Record

Proposed:
  1. Apply shocks → 2. Generate ticks → 3. DISCUSSION ROUND(S) → 4. Collect orders → 5. Clear → 6. Fill → 7. Costs → 8. Record
```

### Discussion Round Structure

Each agent posts a public market commentary before trading begins. Discussion is **cheap talk** — non-binding. Agents can say one thing and do another.

**What agents share (public):**
- Price outlook (bullish / bearish / neutral)
- Fair price estimate (a number)
- Brief commentary (1-2 sentences of reasoning)
- Confidence level (high / medium / low)

**What remains private:**
- Actual order details (price, quantity, side)
- Cash, inventory, costs
- True strategic intent

### Prompt Design

#### Discussion System Prompt

```
You are {agent_id}, a {role} in a commodity market.
{persona}

Before trading begins this period, participants are sharing their
market outlook. Share your analysis, but remember: anything you
say is public. You may be strategic about what you reveal.

You must output JSON:
{
    "price_outlook": "bullish" | "bearish" | "neutral",
    "fair_price_estimate": <number>,
    "commentary": "<1-2 sentences on your market view>",
    "confidence": "high" | "medium" | "low"
}
```

#### Discussion User Prompt

Same market history and private state as the order prompt, but instructions ask for commentary rather than an order.

#### Modified Order Prompt (with discussion transcript)

After discussion, each agent sees others' commentaries when building their order:

```
## Pre-Trade Discussion

**producer_A** (high confidence): BEARISH — fair value ~$98.50
  "Inventory is building up across the market. Expect downward pressure."

**speculator_A** (medium confidence): BULLISH — fair value ~$105.00
  "Momentum is strong after three up periods. Trend should continue."

**consumer_C** (high confidence): NEUTRAL — fair value ~$101.00
  "Market seems fairly valued. No urgency to buy aggressively."

NOTE: Other participants' statements are non-binding. They may act
differently from what they said. Consider whether their statements
are sincere or strategic.
```

### Multi-Round Discussion (Optional)

**Round 1:** Each agent posts independently (7 parallel LLM calls)
**Round 2:** Each agent responds to others' commentary (7 more calls)
**Then:** Submit actual orders (7 calls)

Total: 21 calls/period (3x current cost). Single-round discussion: 14 calls/period (2x).

## Implementation Sketch

### New Functions

```python
def run_discussion_round(
    agents: list[Agent],
    market_state: MarketState,
    agent_states: dict[str, AgentState],
    shock_description: str = "",
) -> dict[str, dict]:
    """
    Each agent shares market outlook. All calls in parallel.
    Returns {agent_id: {price_outlook, fair_price_estimate, commentary, confidence}}.
    """
    commentaries = {}
    for agent in agents:
        prompt = build_discussion_prompt(
            agent, market_state, agent_states[agent.id], shock_description
        )
        commentary = call_llm(agent.system_prompt, prompt)
        commentaries[agent.id] = commentary
    return commentaries


def format_discussion_transcript(
    commentaries: dict[str, dict],
    exclude_agent: str = None,
    anonymous: bool = False,
) -> str:
    """
    Format discussion for inclusion in order prompt.
    exclude_agent: don't show agent its own comment.
    anonymous: hide agent identities.
    """
    lines = ["## Pre-Trade Discussion", ""]
    for i, (agent_id, c) in enumerate(commentaries.items()):
        if agent_id == exclude_agent:
            continue
        label = f"Participant {i+1}" if anonymous else f"**{agent_id}**"
        lines.append(
            f"{label} ({c['confidence']} confidence): "
            f"{c['price_outlook'].upper()} — "
            f"fair value ~${c['fair_price_estimate']:.2f}"
        )
        lines.append(f'  "{c["commentary"]}"')
        lines.append("")
    lines.append(
        "NOTE: Other participants' statements are non-binding. "
        "They may act differently from what they said. "
        "Consider whether their statements are sincere or strategic."
    )
    return "\n".join(lines)
```

### Main Loop Modification

```python
# In run_llm_simulation(), before order collection:
discussion = {}
if enable_discussion:
    discussion = run_discussion_round(
        agents, market_state, agent_states, shock_desc
    )
    discussion_log[period] = discussion

# Modified order collection
for agent in agents:
    transcript = format_discussion_transcript(
        discussion, exclude_agent=agent.id, anonymous=anonymous_mode
    )
    order = agent.get_order(
        agent_state, market_state, price_ticks,
        shock_desc, discussion_transcript=transcript
    )
```

### CLI Additions

```
--discussion          Enable pre-trade discussion round
--discussion-rounds   Number of discussion rounds (default: 1)
--anonymous           Hide agent identities in discussion
--binding             Force agents to trade consistently with stated outlook
```

## Experimental Conditions

| Condition | Discussion | Cheap talk? | Identities visible? |
|-----------|-----------|-------------|---------------------|
| **Baseline** (existing) | None | n/a | n/a |
| **Transparent talk** | 1 round | Yes (can bluff) | Yes (agent IDs) |
| **Anonymous talk** | 1 round | Yes (can bluff) | No (anonymous) |
| **Binding commitment** | 1 round | No (must follow) | Yes |
| **Extended debate** | 2 rounds | Yes | Yes |

## Metrics

### Price Efficiency
- Mean |price - fundamental| per period
- Convergence speed: how many periods until price is within 5% of fundamental

### Bluffing Detection
- **Stated-action consistency:** Does stated outlook match order direction?
  - Producer says "bullish" but sells aggressively = bluff
  - Speculator says "bearish" but submits buy order = bluff
- **Bluffing rate** by agent role (expect speculators > producers > consumers)
- **Bluffing profitability:** Do bluffers earn more than honest agents?

### PID Synergy
- Run same PID analysis on discussion vs no-discussion conditions
- Compare emergence capacity: does communication increase/decrease EC?

### Collusion Detection
- **Producer price coordination:** Do producers converge on similar fair_price_estimates?
- **Bid-ask spread:** Does discussion narrow or widen the spread?
- **Consumer surplus:** Do consumers pay more when producers can discuss?

### Discussion Dynamics
- **Sentiment consensus:** Do agents converge to same outlook over 2 rounds?
- **Influence asymmetry:** Which agent's stated outlook best predicts final clearing price?
- **Information revelation:** Do agents reveal more private info than strategically optimal?

## Expected Findings

### Best Case
- Transparent discussion improves price efficiency (faster convergence to fundamental)
- Speculators bluff significantly more than producers/consumers
- Higher EC in discussion condition (communication enables richer coordination)
- Anonymous discussion prevents collusion while preserving information sharing

### Worst Case
- Discussion enables producer collusion (prices systematically above fundamental)
- All agents bluff (discussion becomes pure noise)
- EC decreases (agents herd to consensus, losing diversity)

## Connection to Other Work

### Adversarial Experiment (Decision Making)
The discussion phase is analogous to the debate rounds in the adversarial experiment. A strategic agent could use discussion to manipulate others' beliefs — the market equivalent of the "personal agent" hijacking consensus.

### Theory of Mind
Discussion naturally creates a ToM dynamic: agents must reason about whether others' statements are sincere. The explicit "consider whether statements are sincere or strategic" prompt activates this reasoning.

### Mechanism Design
The conditions map to real market structure questions:
- **Transparent talk** = open outcry / chat rooms (LIBOR scandal)
- **Anonymous talk** = dark pool pre-trade indications
- **Binding commitment** = limit order book (orders are binding)
- **No discussion** = sealed bid auction

## Cost Estimate

| Condition | Calls/period | 30 periods | 10 scenarios |
|-----------|-------------|------------|--------------|
| Baseline (no discussion) | 7 | 210 | 2,100 |
| 1-round discussion | 14 | 420 | 4,200 |
| 2-round discussion | 21 | 630 | 6,300 |

With Llama 8B at ~$0.001/call: $2.10 → $4.20 → $6.30 per full experiment.
Runtime: ~2x to 3x current (~2-4 hours for 10 scenarios).
