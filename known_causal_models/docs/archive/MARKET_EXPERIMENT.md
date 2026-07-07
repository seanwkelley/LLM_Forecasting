# LLM Agent Market Experiment: Emergent Price Dynamics

**Date:** February 15, 2026 (updated Feb 17)
**Status:** All phases complete. PID analysis (3 conditions: baseline, no-persona, persona) with higher-order synergies and identity differentiation. Phase 5 forecasting: demographic personas +/- ToM, Llama 8B + Qwen 235B. LMM analysis with period-within-scenario clustering shows ToM significantly helps (p = 0.027).
**Motivation:** The wargame simulation's outcome (collapse_probability) is determined by a single aggregator LLM, making it an opaque, non-mechanistic target. A market simulation produces prices as the *direct arithmetic consequence* of agent orders — no aggregator LLM needed, no ambiguous outcome mapping.

---

## 1. Core Idea

Replace the geopolitical simulation with an artificial commodity market where:
- LLM agents act as **buyers, sellers, and producers** with private information
- A **deterministic market mechanism** (not an LLM) clears orders and sets prices
- The **emergent price** is the target variable for PID analysis
- Synergy = do agent pairs jointly predict future prices better than individually?

### Why This Fixes the Wargame's Problems

| Problem (Wargame) | Solution (Market) |
|---|---|
| Outcome determined by aggregator LLM | Price determined by supply/demand arithmetic |
| Opaque action → outcome mapping | Orders → price via clearing mechanism (transparent, reproducible) |
| Collapse probability tightly clustered (std=0.07) | Prices naturally vary with supply/demand shocks |
| Discretization entropy trap (3/44/3 bins) | Continuous price; or natural discretization (up/down/flat) |
| Hard to validate "ground truth" | Equilibrium price is computable from fundamentals |

---

## 2. Market Design

### 2.1 The Commodity

A single fictional commodity (e.g., "Meridium" — a strategic resource). Keeps things simple: one price, one market, one clearing mechanism.

### 2.2 Agent Roles (6-10 agents)

| Role | Count | Objective | Private Info |
|------|-------|-----------|-------------|
| **Producer** | 2-3 | Maximize revenue; has production costs | Production costs, inventory levels, planned output |
| **Consumer** | 2-3 | Minimize cost; has demand needs | Demand forecasts, budget constraints, stockpile levels |
| **Speculator** | 1-2 | Maximize trading profit | Technical indicators, historical patterns |
| **Market Maker** | 1 | Provide liquidity; earn spread | Order flow data, bid-ask spread history |

Each agent sees:
- **Public info**: Last N periods of market prices, volume, announced supply/demand
- **Private info**: Role-specific signals (see above)
- **Shared context**: Market rules, their own budget/inventory state

### 2.3 Market Mechanism (No LLM)

**Double auction with uniform price clearing:**

Each period:
1. Each agent submits orders: `{action: "buy"/"sell", quantity: int, limit_price: float}`
2. Sort buy orders descending by price, sell orders ascending by price
3. Find clearing price where supply meets demand (standard crossing algorithm)
4. Execute matched orders at clearing price
5. Update agent budgets and inventories deterministically

```python
def clear_market(buy_orders, sell_orders):
    """Deterministic price-setting. No LLM involved."""
    buys = sorted(buy_orders, key=lambda x: -x['price'])  # highest first
    sells = sorted(sell_orders, key=lambda x: x['price'])  # lowest first

    matched_qty = 0
    clearing_price = None

    b_idx, s_idx = 0, 0
    while b_idx < len(buys) and s_idx < len(sells):
        if buys[b_idx]['price'] >= sells[s_idx]['price']:
            qty = min(buys[b_idx]['remaining'], sells[s_idx]['remaining'])
            clearing_price = (buys[b_idx]['price'] + sells[s_idx]['price']) / 2
            matched_qty += qty
            # ... update remaining quantities
        else:
            break

    return clearing_price, matched_qty
```

### 2.4 Exogenous Shocks (The "Scenarios")

Each simulation run has a sequence of **supply/demand shocks** that create price variation:

| Shock Type | Effect | Frequency |
|-----------|--------|-----------|
| Supply disruption | Producers' costs increase 20-50% | ~20% of periods |
| Demand surge | Consumers' demand increases 30-60% | ~15% of periods |
| New entrant | Extra supply at low cost for 2 periods | ~10% of periods |
| Regulatory change | Trading limits or price caps | ~10% of periods |
| Information leak | One agent's private info becomes public | ~15% of periods |
| No shock | Normal trading | ~30% of periods |

Shocks are pre-generated with known parameters → ground truth "fair price" is computable from fundamentals.

### 2.5 Information Sharding (Connects to Existing Work)

Directly analogous to existing forecasting experiment:

| Condition | What agents see |
|-----------|----------------|
| **Full info** | All public + own private info |
| **Sharded** | Random subset of public info + own private info |
| **Domain shard** | Only their domain's info (e.g., producers see supply data, consumers see demand data) |
| **Reframe** | Same info, different market narrative framing |

---

## 3. PID Analysis Design

### 3.1 Variables

**Agent actions (X_i):** Each agent's order in period t, encoded as:
- **Direction**: Buy (+1), Hold (0), Sell (-1)
- **Aggressiveness**: |limit_price - last_price| / last_price (how far from market)
- **Size**: quantity / mean_quantity (normalized)

Could encode as a single composite: `direction × aggressiveness` discretized to 5 levels.

**Target (Y):** Period t+1 price, discretized:
- **Tercile binning** on price changes: DOWN / FLAT / UP (learned from distribution)
- Or: price_change = (P_{t+1} - P_t) / P_t, then qcut into 3 bins

### 3.2 Research Questions

1. **Does genuine synergy exist?** Do agent pairs jointly predict next-period price better than individually? (Permutation test)
2. **Which pairs are synergistic?** Producer × Consumer should show high synergy (they define supply and demand). Speculator × anyone might show low synergy (they react to price, don't cause it).
3. **Does information sharding affect synergy?** Full-info agents might show more redundancy (all see the same thing). Sharded agents might show more synergy (each has unique pieces of the puzzle).
4. **Does CI (complementarity index) predict ensemble forecast accuracy?** Higher synergy → better ensemble price forecasts?

### 3.3 Expected Results

| Agent Pair | Expected Synergy | Reasoning |
|-----------|-----------------|-----------|
| Producer × Consumer | HIGH | Their interaction defines the price |
| Producer × Producer | LOW (redundant) | Similar info, similar actions |
| Consumer × Consumer | LOW (redundant) | Similar info, similar actions |
| Speculator × Producer | MODERATE | Speculator amplifies producer signals |
| Market Maker × anyone | LOW (unique) | Market maker reacts to order flow, doesn't cause price |

### 3.4 Advantages over Wargame PID

1. **No discretization trap**: Price changes are naturally well-distributed
2. **Mechanistic link**: Agent orders → price is arithmetic, not LLM judgment
3. **Clear null hypothesis**: Shuffling agent orders and re-running the clearing mechanism gives you a proper null distribution
4. **Scalable**: Can run 1000+ market periods cheaply (LLM calls only for agent decisions, not for outcome determination)
5. **Interpretable synergy**: "Producer sell + Consumer buy = price" is intuitive; "Economic advisor escalation + Military general escalation = collapse probability" is not

---

## 4. Implementation Plan

### 4.1 Phase 1: Market Engine (No LLM)

Pure Python market simulator:
- Order book management
- Double auction clearing
- Agent state tracking (budget, inventory, P&L)
- Shock generation and application
- Ground truth price computation

**Files:**
- `market/engine.py` — Market clearing, order book
- `market/shocks.py` — Exogenous shock generation
- `market/agents_config.py` — Agent role definitions, initial endowments

**Test:** Run with simple rule-based agents (buy-low/sell-high) to verify clearing mechanism.

### 4.2 Phase 2: LLM Agent Integration

Each agent is an LLM call that receives:
- System prompt: Role, objective, budget, inventory
- Context: Market history, private signals, current shock info
- Output: JSON order `{action, quantity, limit_price, reasoning}`

**Files:**
- `market/llm_agent.py` — LLM agent wrapper (reuse forecaster_base.py patterns)
- `market/prompts.py` — Role-specific system prompts

**Test:** Run 10-period simulation with LLM agents, verify price series makes sense.

### 4.3 Phase 3: Multi-Scenario Generation

Run M independent market simulations with varied:
- Initial endowments
- Shock sequences (pre-generated, seeded)
- Number of agents
- Information conditions

Each simulation runs for T periods → produces T price observations per scenario.

**Target:** 50-100 scenarios × 20-50 periods = 1000-5000 price observations for PID.

### 4.4 Phase 4: PID Analysis

Reuse existing PID pipeline (`pid_analysis.py`, `pid_visualization.py`) with:
- Agent actions encoded as ordinal levels
- Target = next-period price change (tercile-binned)
- Same permutation test framework
- Same conditional analysis (by shock type instead of crisis level)

### 4.5 Phase 5: Forecasting Experiment

External LLM forecasters predict next-period price given:
- Full market history (baseline)
- Sharded market history (information sharding)
- Agent order history (can they use agent behavior as signals?)

**Connects to existing work:** Same sharding strategies, same ensemble aggregation, but with a mechanistic target.

---

## 5. Cost & Timeline Estimates

### Computational Cost

| Component | LLM Calls | Cost (Llama 8B) |
|-----------|-----------|-----------------|
| Market simulation (50 scenarios × 30 periods × 8 agents) | 12,000 | ~$5 |
| Forecasting experiment (50 scenarios × 30 periods × 10 forecasters × 3 conditions) | 45,000 | ~$20 |
| **Total** | **57,000** | **~$25** |

Much cheaper than wargame (which needs ~600-800 calls per scenario just for simulation).

### Development Timeline

| Phase | Effort | Dependencies |
|-------|--------|-------------|
| Market engine | 1 day | None |
| LLM agent integration | 1 day | Phase 1 |
| Multi-scenario generation | 0.5 days | Phase 2 |
| PID analysis | 0.5 days (reuse existing) | Phase 3 |
| Forecasting | 1 day (reuse existing) | Phase 3 |
| **Total** | **4 days** | |

---

## 6. Relationship to Existing Work

This experiment is **complementary**, not a replacement:

| Aspect | Wargame | Market |
|--------|---------|--------|
| Domain | Geopolitical crisis | Economic trading |
| Outcome mechanism | LLM aggregator | Arithmetic clearing |
| Agent interaction | Sequential (propose → approve) | Simultaneous (all submit orders) |
| Information structure | Narrative text | Structured data (prices, quantities) |
| PID target | Collapse probability | Price change |
| Existing infrastructure | Full pipeline exists | Needs market engine |

If PID shows significant synergy in the market (where the outcome is mechanistic) but not in the wargame (where the outcome is LLM-judged), that's a strong statement: **the wargame's lack of synergy is an artifact of the opaque outcome mapping, not a fundamental property of LLM multi-agent coordination.**

If PID shows no synergy in either, that's also informative: **LLM agents may genuinely not coordinate in ways that produce emergent information.**

---

## 7. Design Traps & Mitigations

### 7.1 Mechanical Synergy vs. Informational Synergy

**Risk:** In a double auction, any buy+sell crossing produces a trade. PID on (buy_order, sell_order) → current_price will detect "synergy" that is just the clearing algorithm, not genuine joint prediction.

**Mitigation:**
- PID target must be **next-period price change** (t+1), not current-period price
- This ensures we measure "does the combination of A's and B's orders at time t *predict where price goes next*?" — genuine predictive information, not mechanical matching
- **Rule-based agent baseline**: Run the same PID analysis with simple rule-based agents (e.g., zero-intelligence traders that buy/sell at random within budget). This calibrates what "trivial structural synergy" looks like from the clearing mechanism alone. LLM agent synergy must exceed this baseline to be meaningful.

### 7.2 Convergence to Degenerate Strategies

**Risk:** LLMs anchor to last price, everyone submits narrow spreads, market becomes low-variance. This recreates the entropy trap in a new domain.

**Mitigation:**
- **Inventory pressure / storage costs**: Holding inventory costs money each period, forcing agents to trade rather than hold
- **Forced liquidity needs**: Consumers *must* buy X units per period (production schedule), producers *must* sell Y units (perishable goods / cash flow needs)
- **Asymmetric time horizons**: Producers plan 5 periods ahead, speculators only care about next period
- **Asymmetric shock exposure**: Supply shock hits producers immediately, reaches consumers with a lag
- **Mild noise in private signals**: Prevents deterministic convergence
- **Monitor variance per period**: If price std drops below threshold, inject additional shocks

### 7.3 Market Maker Dominance

**Risk:** A well-prompted market maker may stabilize prices excessively (killing entropy) or absorb most trades (reducing inter-agent interaction effects).

**Mitigation:**
- **Start without market maker** — test with only producers, consumers, speculators
- **Add market maker as experimental condition** to measure its effect on synergy
- **If included**: Use passive market maker (fixed spread around last price) rather than adaptive, to avoid it becoming the dominant price-setter

### 7.4 Action Encoding for PID

**Risk:** Composite encoding (direction × aggressiveness) creates artificial correlations and is sensitive to discretization geometry.

**Mitigation:** Treat action components separately:
- **X_direction** = {-1 (sell), 0 (hold), +1 (buy)} — 3 levels
- **X_aggressiveness** = |limit_price - last_price| / last_price, binned into 3 levels (passive, moderate, aggressive)
- **X_size** = quantity / mean_quantity, binned into 3 levels (small, medium, large)

Test PID in stages:
1. **Simplest test**: PID on (direction_A, direction_B) → price_change_sign. Cleanest, most interpretable.
2. **Add aggressiveness**: PID on (direction×aggr_A, direction×aggr_B) → price_change_tercile.
3. **Full encoding**: All 3 components. Higher-dimensional but more defensible if reported alongside simpler versions.

### 7.5 "Fair Price" vs. Realized Price

**Risk:** Claiming "ground truth price is computable from fundamentals" is too strong. In a double auction, realized price depends on agent policies, liquidity, and inventory — not just supply/demand curves.

**Reframing:**
- Compute a **fundamental reference price** (theoretical equilibrium given perfect info + rational agents)
- Realized price will deviate from this due to agent bounded rationality, information asymmetry, and inventory effects
- Use **two PID targets**:
  1. **Price change**: Do agent pairs predict where price goes? (Main analysis)
  2. **Price - fundamental gap**: Do agent pairs predict market *inefficiency*? (Secondary analysis; measures whether coordination amplifies or corrects mispricing)

---

## 8. Agent Trading Personas (Added Feb 16)

### 8.1 Motivation

Initial LLM runs (no persona) showed that agents with generic role prompts converge to "bid near last price" behavior:
- Consumer aggressiveness: all within +-1% of market price
- Producer aggressiveness: all within +-2% of market price
- Result: 50% flat price periods, 2-level consumer actions, no detectable PID synergy (EC=0.005, p=0.744)

Meanwhile, rule-based agents with hard-coded different strategies showed **significant synergy** (EC=0.041, p=0.000). The LLMs needed distinct decision-making personalities to create meaningful behavioral diversity.

### 8.2 Persona Design

Each agent receives a **Trading Persona** appended to their role system prompt. Personas define decision style, not role mechanics — the role rules (sell-only, buy-only, etc.) remain unchanged.

| Agent | Persona | Core Strategy |
|-------|---------|---------------|
| producer_A | **Volume Mover** | Slash prices to move inventory. Thin margins acceptable. Cash flow > profit per unit. |
| producer_B | **Margin Optimizer** | Hold firm on target margin (15-20% above cost). Accumulate inventory rather than sell cheap. |
| consumer_A | **Security Stockpiler** | Bid aggressively to maintain 3-4 period buffer. Supply security > price optimization. |
| consumer_B | **Bargain Hunter** | Conservative bids, 5-10% below market. Wait for dips. Comfortable with 1-2 period coverage. |
| consumer_C | **Shock Anticipator** | React to market conditions. Aggressive before expected shortages, passive in calm periods. |
| speculator_A | **Momentum Rider** | Buy into uptrends, sell into downtrends. Follow price direction. Exit on reversals. |
| speculator_B | **Value Contrarian** | Buy below average, sell above average. Fade extremes. Hold when price is near average. |

### 8.3 Behavioral Impact (Pilot Results, 3 Scenarios)

| Metric | No-Persona | With Personas | Change |
|--------|-----------|--------------|--------|
| Price std (mean) | $6.7 | $23.4 | **3.5x** |
| Return volatility | 0.028 | 0.060 | **2.1x** |
| Unique prices per scenario | 14/30 | 25/30 | +79% |
| Flat periods per scenario | 16/29 | 5/29 | -69% |
| Consumer aggr. spread | +-1% | -8% to +11% | **19x** |
| Producer aggr. spread | +-2% | -5% to +10% | **7x** |

### 8.4 PID Implications

Personas should improve PID analysis by:
1. **Increasing action entropy** — more distinct action levels per agent
2. **Balancing target distribution** — more UP/DOWN/FLAT price changes instead of 75% DOWN
3. **Creating genuine information asymmetry** — a Stockpiler's aggressive bid means something different than a Bargain Hunter's aggressive bid

Expected synergy pairs:
- **producer_A (Volume) x producer_B (Margin)**: opposite pricing → aggressiveness diverges
- **consumer_A (Stockpiler) x consumer_B (Bargain)**: opposite urgency → quantity/price diverge
- **speculator_A (Momentum) x speculator_B (Contrarian)**: opposite directional signals → agreement/disagreement is informative

---

## 9. PID Analysis Results (Feb 16)

### 9.1 Baseline (Rule-Based Agents)

**EC = 0.041 bits, p = 0.000 (both surrogate methods)**

9 pairs significant at p < 0.05 (row-shuffle, 500 permutations):

| Pair | Synergy | p-value |
|------|---------|---------|
| producer_A x speculator_A | 0.061 | **0.006** |
| producer_A x speculator_B | 0.059 | **0.002** |
| consumer_C x producer_B | 0.050 | **0.000** |
| consumer_C x speculator_B | 0.061 | **0.018** |
| consumer_A x consumer_C | 0.044 | **0.000** |
| producer_B x speculator_B | 0.049 | **0.032** |
| consumer_B x producer_B | 0.022 | **0.038** |
| consumer_A x producer_A | 0.020 | **0.022** |
| consumer_B x producer_A | 0.017 | **0.042** |

Cross-role pairs dominate (producer x speculator EC=0.054, consumer x speculator EC=0.047). Within-role pairs are weak (producer x producer EC=0.002, speculator x speculator: high redundancy at 59%).

### 9.2 LLM No-Persona

**EC = 0.005 bits, p = 0.744 (not significant)**

No pairs reach p < 0.05. Target distribution skewed: 75% DOWN, 25% UP (H(Y)=0.81 bits vs baseline's 1.39 bits). Low action entropy from generic agent behavior.

Only bright spot: speculator_A x speculator_B (syn=0.056, 82% of MI, p=0.096) — the only agents with meaningful direction choice.

### 9.3 LLM vs Baseline Comparison

| Metric | LLM No-Persona | Baseline | Delta |
|--------|---------------|----------|-------|
| EC | 0.005 | 0.041 | -88% |
| Mean synergy | 0.009 | 0.034 | -74% |
| H(Y) target entropy | 0.81 bits | 1.39 bits | -42% |
| Significant pairs (p<0.05) | 0/21 | 9/21 | — |

**Interpretation:** LLM agents without personas produce less behavioral diversity than simple rule-based agents, resulting in lower price variation, lower target entropy, and no detectable synergy.

### 9.4 LLM Persona Results

**EC = 0.032 bits, p = 0.002 (row-shuffle), p = 0.000 (col-shift) — SIGNIFICANT**

Personas recovered emergent coordination. Full results:

| Metric | Baseline | LLM No-Persona | LLM Persona |
|--------|----------|----------------|-------------|
| EC (bits) | 0.041 | 0.005 | **0.032** |
| EC p-value | 0.000 | 0.744 | **0.002** |
| H(Y) target entropy | 1.39 bits | 0.81 bits | **1.55 bits** |
| Mean synergy | 0.034 | 0.009 | **0.031** |
| Significant pairs (p<0.05) | 9/21 | 0/21 | **1/21** |
| Mean price std | $9.5 | $7.8 | **$23.6** |
| Mean return vol | 9.5% | 3.1% | **6.6%** |
| Flat periods per scenario | 3.7/29 | 17.3/29 | **4.5/29** |

**Top synergy pairs (persona):**

| Pair | Synergy | Syn % | p-value |
|------|---------|-------|---------|
| speculator_A x speculator_B | 0.074 | 76.2% | 0.908 |
| consumer_B x speculator_B | 0.074 | 79.3% | 0.072 |
| producer_A x speculator_B | 0.048 | 55.7% | 0.054 |
| consumer_B x speculator_A | 0.048 | 65.7% | 0.472 |
| consumer_B x producer_B | 0.038 | 70.1% | **0.020** |

**Cross-role EC breakdown:**

| Role Pairing | Persona EC | Baseline EC |
|-------------|-----------|-------------|
| Producer x Speculator | 0.039 | 0.054 |
| Consumer x Speculator | 0.038 | 0.047 |
| Producer x Consumer | 0.010 | 0.018 |
| Within-producer | 0.015 | 0.002 |
| Within-consumer | 0.012 | 0.016 |
| Within-speculator | 0.074 | 0.023 |

**Key observations:**
1. Persona speculator pair (Momentum Rider x Value Contrarian) shows 3x more synergy than baseline speculators (0.074 vs 0.023) — opposed strategies create strong complementary signals
2. Persona synergy has higher synergy *proportions* (60-80% vs 40-50%) — more of each pair's MI is synergistic rather than redundant
3. Baseline has more individually significant pairs (9 vs 1) — likely because rule-based agents have perfectly deterministic strategies that are easier to detect statistically
4. Consumer_B (Bargain Hunter) appears in 3 of the top 5 pairs — patient value-seeking behavior generates distinctive informational signals

### 9.5 Key Findings

**1. Rule-based market agents show significant synergy.** EC = 0.041, p < 0.001. This is the first statistically significant PID result in the project. Nine agent pairs show synergy exceeding chance levels, with cross-role pairs (producer x speculator, consumer x speculator) dominating. This confirms that the market design can detect genuine emergent coordination when it exists.

**2. Generic LLM agents destroy synergy.** Despite the mechanistic market design providing better conditions for PID, LLM agents with generic prompts show NO significant synergy (EC = 0.005, p = 0.744). They converge to similar "bid near last price" behavior, producing low action entropy, price stickiness (50% flat periods), and a skewed target distribution (75% DOWN).

**3. The behavioral entropy trap.** Both the wargame and the no-persona market suffer from the same root cause: LLM agents without strong behavioral differentiation converge to similar strategies. In the wargame, this produced 88% of outcomes in one bin. In the market, it produced 75% flat/down periods and 2-level consumer actions. The underlying issue is not the domain or the clearing mechanism — it's LLM behavioral homogeneity.

**4. Personas recover emergent coordination.** Trading personas restore statistically significant synergy: EC = 0.032, p = 0.002, recovering 79% of baseline EC. Target entropy improved from 0.81 to 1.55 bits (near-optimal). The Momentum Rider x Value Contrarian speculator pair produces the highest synergy (0.074 bits, 76% synergistic) — 3x more than the baseline speculator pair — demonstrating that opposed LLM strategies create stronger complementary signals than deterministic rule diversity.

### 9.6 Implications

1. **LLM agents CAN produce emergent coordination**, but only with sufficiently distinct decision-making strategies (personas).
2. **Behavioral diversity is necessary and sufficient** — personas recovered significant synergy without changing the market mechanism, number of agents, or observation count.
3. **LLM persona synergy is qualitatively different from rule-based synergy** — higher synergy proportions (60-80% vs 40-50% of MI) but fewer individually significant pairs (1 vs 9). LLM coordination is more diffuse and harder to localize to specific pairs.
4. **The behavioral entropy trap is the central methodological finding** — any PID analysis of LLM multi-agent systems must first ensure sufficient behavioral diversity, or results will be dominated by the homogeneity artifact.

### 9.7 Higher-Order Synergies (Triplet G3)

**G3 = MI(A,B,C; Y) - max(MI_pairwise)** — measures whether agent triplets carry information beyond the best pair. Positive G3 indicates genuine higher-order synergy requiring 3+ agents.

| Metric | Baseline (rule) | No-Persona (LLM) | Persona (LLM) |
|--------|----------------|-------------------|----------------|
| Higher-Order Capacity (median G3) | 0.050 bits | 0.014 bits | **0.065 bits** |
| Mean G3 | -- | -- | 0.069 bits |
| Positive G3 triplets | -- | -- | 35/35 (100%) |

Persona LLMs exceed baseline on higher-order synergy (0.065 vs 0.050) even though pairwise EC is lower (0.032 vs 0.041). This means persona agents create richer 3-way interaction structures than hard-coded rules. No-persona LLMs show minimal higher-order synergy (0.014), consistent with the behavioral entropy trap.

**Top triplets (persona condition):**

| Triplet | G3 | MI_triplet | Best pair MI |
|---------|-----|-----------|-------------|
| consumer_B x speculator_A x speculator_B | +0.170 | 0.268 | 0.097 |
| producer_A x speculator_A x speculator_B | +0.148 | 0.245 | 0.097 |
| consumer_B x producer_A x speculator_B | +0.133 | 0.226 | 0.093 |

Speculators appear in the top triplets consistently, confirming their role as coordination nodes that bridge producer-consumer dynamics.

### 9.8 Identity-Linked Differentiation (JSD)

Following Riedl's identity-linked differentiation criterion, we measured whether agents maintain consistent, distinct behavioral profiles using Jensen-Shannon Divergence (JSD) between action distributions.

| Metric | Baseline (rule) | No-Persona (LLM) | Persona (LLM) |
|--------|----------------|-------------------|----------------|
| Mean pairwise JSD | **0.555** | 0.438 | 0.450 |
| Temporal consistency (split-half JSD) | **0.001** | 0.004 | 0.006 |
| Mean action entropy | 1.095 bits | 1.047 bits | **1.252 bits** |

**Interpretation:**

1. **Differentiation:** Baseline agents are most differentiated (JSD=0.555) due to hard-coded role-specific rules. Persona LLMs (0.450) slightly exceed no-persona (0.438), but neither reaches baseline levels. The differentiation gap comes mainly from within-role similarity — LLM agents of the same role (e.g., two consumers) are more behaviorally similar than their rule-based counterparts.

2. **Temporal consistency:** All conditions show excellent consistency (JSD < 0.01), meaning agents don't drift toward homogeneous behavior over time. Personas maintain stable behavioral identities across all 30 periods. Baseline is most consistent (0.001) since rules are deterministic; LLM stochasticity introduces slight variation (0.004-0.006).

3. **Action entropy:** Persona LLMs are the most unpredictable per-agent (1.252 bits), exceeding both baseline (1.095) and no-persona (1.047). Speculators drive this — their dual buy/sell capacity produces H ~ 2.0 bits. This higher entropy, combined with strong G3, indicates *structured variety* rather than noise.

**JSD structure (persona condition):**

| Agent pair type | Mean JSD | Interpretation |
|----------------|----------|----------------|
| Consumer x Producer | 0.998 | Maximally different (opposite sides) |
| Producer x Speculator | 0.528 | Highly different |
| Consumer x Speculator | 0.192 | Moderate overlap (both buy) |
| Within-role (same type) | 0.037 | Very similar |

The JSD structure mirrors the market's fundamental asymmetry: producers only sell, consumers only buy, speculators do both. Cross-role differentiation is structural (imposed by market rules), while within-role differentiation depends on persona quality.

### 9.9 Combined PID Picture

| Metric | Baseline | No-Persona | Persona | Persona interpretation |
|--------|----------|------------|---------|----------------------|
| EC (pairwise) | 0.041*** | 0.005 n.s. | 0.032** | Recovered 79% |
| G3 (triplet) | 0.050 | 0.014 | **0.065** | Exceeds baseline |
| Differentiation | **0.555** | 0.438 | 0.450 | Partial recovery |
| Consistency | **0.001** | 0.004 | 0.006 | All excellent |
| Action entropy | 1.095 | 1.047 | **1.252** | Most diverse |

Persona LLMs show a distinctive coordination profile: **lower pairwise synergy but higher triplet synergy than baseline, with more behavioral variety per agent but less inter-agent differentiation.** This suggests LLM coordination operates through diffuse multi-agent interactions rather than strong pairwise coupling — a qualitatively different coordination mechanism than rule-based agents.

---

## 10. Design Decisions (Resolved)

1. **Trading personas required for LLM agents.** Without personas, LLMs converge to generic "bid near market" behavior with low action entropy. Personas are not optional — they are a prerequisite for meaningful PID analysis.

2. **Price levels: 10-20 discrete ticks.** LLMs struggle with floating point intuition. If base price is $100, offer {$92, $94, ..., $108}. Prevents hallucinated outliers while providing enough granularity for a 3-bin target.

2. **Temporal PID: Phase 2.** Start with (A_t, B_t) → Y_{t+1}. If synergy is found, *then* test (A_t, A_{t-1}) → Y_{t+1} to distinguish momentum-based from information-based synergy.

3. **Inventory constraints: Simple truncation.** No short selling. Engine auto-truncates orders exceeding available inventory and sends "Warning: Insufficient Inventory" in the next prompt. No margin/bankruptcy mechanism initially.

4. **Market context: Last 5 periods of OHLCV.** Industry-standard window. Enough to see a trend without token bloat. Plus agent's current private signals.

5. **Private orders only.** Agents cannot see each other's orders. This ensures any detected synergy is **pure informational synergy** — agents arrived at the same "truth" using different pieces of the puzzle. If orders were public, PID would detect imitation/herding as synergy, which is not what we want to measure. (Public orders as a future experimental condition, not the default.)

---

## 11. Forecasting Experiment Results (Phase 5, Feb 16)

### 11.1 Experimental Design

External LLM forecasters observe market price history and predict the next-period price direction (UP/DOWN/FLAT). Each forecaster operates independently — they see the price/volume history and their own persona prompt, but NOT each other's predictions.

**2x2 factorial design:**

| | Strategy Personas | Demographic Personas |
|---|---|---|
| **No ToM** | 5 strategy-based forecasters (trend follower, mean reverter, volume reader, fundamental analyst, volatility analyst) | 5 experience-based forecasters (veteran trader, quant PhD, cautious fund manager, junior analyst, contrarian hedge fund PM) |
| **With ToM** | Same 5 strategy forecasters + descriptions of 7 trading agent personas | Same 5 demographic forecasters + descriptions of 7 trading agent personas |

**Theory of Mind (ToM):** Forecasters receive descriptions of the 7 trading agents' personas and strategies, enabling them to reason about *why* agents trade the way they do, rather than just extrapolating from price patterns.

**Common setup across all conditions:**
- Primary model: Llama 3.1 8B (`meta-llama/llama-3.1-8b-instruct`)
- Secondary model: Qwen3 235B (`qwen/qwen3-235b-a22b-2507`) — demographic conditions only
- 10 scenarios x 24 periods each (periods 6-29) x 5 forecasters = 1,200 forecasts per condition
- Market data: `outputs/market_llama_persona/` (persona trading simulation)

**Target distribution (ground truth):**

| Direction | Count | Percentage |
|-----------|-------|-----------|
| UP | 565 | 47.1% |
| DOWN | 455 | 37.9% |
| FLAT | 180 | 15.0% |

### 11.2 Naive Baselines

| Baseline | Accuracy | Brier Score | Macro F1 | Price RMSE | Description |
|----------|----------|-------------|----------|------------|-------------|
| Majority class (UP) | 47.1% | 1.058 | — | — | Always predict the most common class |
| Frequency-weighted | 47.1% | **0.612** | 0.213 | — | Predict with class-frequency probabilities |
| Persistence | 46.5% | 1.070 | 0.399 | — | Predict last period's direction repeats |
| No-change (price) | — | — | — | **9.44** | Predict next price = current price |
| Uniform (1/3 each) | 33.3% | 0.667 | — | — | Equal probability on each class |

**Key benchmarks:** Frequency-weighted Brier (0.612) for directional classification, no-change price RMSE (9.44) for price prediction. Beating both requires genuine market understanding.

### 11.3 Individual Forecaster Performance

| Condition | Accuracy | Macro F1 | Brier | Price RMSE | Price MAE% | Log Score |
|-----------|----------|----------|-------|------------|------------|-----------|
| Strategy no-ToM | 48.2% | 0.367 | 0.731 | 14.38 | 7.73% | 2.143 |
| Strategy + ToM | 49.2% | 0.359 | 0.669 | 11.77 | 6.56% | 1.443 |
| Demographic no-ToM | 49.2% | 0.353 | 0.650 | 10.49 | 5.88% | 1.153 |
| **Demographic + ToM** | **50.2%** | **0.372** | **0.630** | **9.91** | **5.63%** | **1.068** |

### 11.4 Ensemble Performance (Average Across Forecasters)

| Condition | Accuracy | Macro F1 | Brier | Price RMSE | vs Freq Brier | vs Naive RMSE |
|-----------|----------|----------|-------|------------|---------------|---------------|
| Strategy no-ToM | 52.1% | 0.390 | 0.620 | 10.04 | +0.008 (worse) | +0.60 (worse) |
| Strategy + ToM | **54.6%** | **0.407** | **0.597** | 9.57 | **-0.015 (better)** | +0.13 (worse) |
| Demographic no-ToM | 50.4% | 0.356 | 0.619 | 9.66 | +0.007 (worse) | +0.22 (worse) |
| **Demographic + ToM** | **54.6%** | 0.402 | **0.598** | **9.29** | **-0.014 (better)** | **-0.15 (better)** |
| *Freq-weighted baseline* | *47.1%* | *0.213* | *0.612* | *—* | *—* | *—* |
| *No-change baseline* | *—* | *—* | *—* | *9.44* | *—* | *—* |

### 11.5 Per-Class F1 Breakdown

| Condition | UP F1 | DOWN F1 | FLAT F1 |
|-----------|-------|---------|---------|
| Strategy no-ToM | 0.551 | 0.493 | 0.057 |
| Strategy + ToM | 0.568 | 0.500 | 0.010 |
| Demographic no-ToM | 0.578 | 0.472 | 0.011 |
| **Demographic + ToM** | **0.587** | **0.488** | **0.041** |

FLAT prediction is a universal failure across all conditions. Forecasters almost never predict FLAT despite it being 15% of outcomes. Demographic+ToM shows the least-bad FLAT F1 (0.041), 4x better than other conditions but still near zero.

### 11.6 Per-Forecaster Highlights

**Strategy personas — problematic outlier:**
The "fundamental analyst" persona consistently performs worst across both strategy conditions:

| Condition | Fundamental Brier | Next-worst Brier | Gap |
|-----------|-------------------|-----------------|-----|
| Strategy no-ToM | 0.976 | 0.741 | +0.235 |
| Strategy + ToM | 0.739 | 0.675 | +0.064 |

ToM partially rescues the fundamental analyst (Brier: 0.976 → 0.739), but it remains the worst individual forecaster. This catastrophically miscalibrated agent drags down the strategy condition's individual-level metrics.

**Demographic personas — more balanced:**

| Forecaster | no-ToM Brier | +ToM Brier | Change |
|------------|-------------|------------|--------|
| contrarian_veteran | 0.639 | — | Best individual |
| quant_phd | 0.631 | — | Close second |
| veteran_trader | 0.648 | — | Solid |
| young_analyst | 0.659 | — | Adequate |
| cautious_manager | 0.674 | — | Worst, but not catastrophic |

The demographic condition avoids the "one catastrophic forecaster" problem. All 5 forecasters stay within a narrow Brier range (0.631-0.674).

### 11.7 Key Findings

**1. Theory of Mind is the critical factor for forecasting.**

Both ToM conditions beat the frequency-weighted baseline (Brier ~0.597-0.598 vs 0.612), while both no-ToM conditions fail to beat it. Price RMSE tells the same story even more sharply: only Demographic+ToM beats the naive no-change baseline (RMSE 9.29 vs 9.44). ToM enables forecasters to reason about *why* prices move (agent motivations), not just *what* happened (price patterns). This produces better-calibrated probability estimates and more accurate price predictions.

**Statistical test (Demographic no-ToM vs +ToM):** A linear mixed-effects model on individual-level squared price error with crossed random intercepts for scenario and forecaster — `sq_error ~ tom + (1|scenario_id) + (1|forecaster_id)` (R lme4, N=2,400, Kenward-Roger df) — confirms the ToM effect: coefficient = -11.76 (p=0.043). Variance decomposition: scenario (408.4) >> forecaster (36.3) >> residual (20,148.3), indicating market regime matters far more than persona identity. Block permutation tests (50k iterations, scenario-level shuffling) corroborate: one-tailed p=0.026. The effect is medium-sized (Cohen's d=0.51) and consistent (ToM wins 7/10 scenarios).

**2. Demographic personas produce better individual forecasters.**

At the individual level, demographic personas dominate: Brier 0.630-0.650 vs 0.669-0.731 for strategy. The key difference is that strategy personas include a catastrophically miscalibrated "fundamental analyst" that biases the average. Demographic personas, grounded in realistic investor archetypes, maintain more consistent quality.

**3. At the ensemble level, persona type washes out.**

Both ToM ensembles converge to near-identical performance (Brier: 0.597 vs 0.598). The ensemble averaging absorbs the strategy condition's outlier problem. This is actually the expected benefit of ensemble methods — they're robust to individual forecaster failures.

**4. Ensemble forecasting provides modest but real value.**

Across all conditions, ensembles improve Brier by 0.03-0.11 points over individual averages. The best ensemble (Strategy+ToM, Brier=0.597) represents a 2.5% improvement over the frequency baseline — small but consistent. Price RMSE improvements are even more dramatic: individual RMSE ranges from 9.91-14.38, while ensembles compress to 9.29-10.04 — the ensemble absorbs individual miscalibration.

**5. Price RMSE is a stricter test than Brier score.**

Brier score for directional classification shows two conditions beating the frequency baseline. Price RMSE — a continuous metric with no information loss from discretization — is stricter: only one condition (Demographic+ToM ensemble) beats the naive no-change baseline. This suggests that much of the apparent directional forecasting skill comes from correctly predicting the *direction* while misjudging the *magnitude*. Price RMSE captures both.

**6. LLM forecasters cannot predict FLAT movements.**

FLAT F1 is near zero in all conditions. Forecasters overwhelmingly distribute probability between UP and DOWN, treating the market as binary rather than ternary. This mirrors findings in human forecasting literature — humans also struggle with "no change" predictions.

### 11.8 Qwen 235B Results (Cross-Model Comparison)

A secondary model — Qwen3 235B (`qwen/qwen3-235b-a22b-2507`), a reasoning model with chain-of-thought — was run on the two demographic conditions for comparison.

**Individual forecaster performance:**

| Condition | Accuracy | Macro F1 | Brier | Price RMSE |
|-----------|----------|----------|-------|------------|
| Llama Demog no-ToM | 49.2% | 0.353 | 0.650 | 10.49 |
| Llama Demog + ToM | 50.2% | 0.372 | 0.630 | 9.91 |
| Qwen Demog no-ToM | 38.4% | 0.314 | 0.715 | 12.85 |
| Qwen Demog + ToM | 40.8% | 0.307 | 0.703 | 11.84 |

**Ensemble performance:**

| Condition | Accuracy | Macro F1 | Brier | Price RMSE | vs Naive RMSE |
|-----------|----------|----------|-------|------------|---------------|
| Llama Demog no-ToM | 50.4% | 0.356 | 0.619 | 9.66 | +0.22 (worse) |
| **Llama Demog + ToM** | **54.6%** | **0.402** | **0.598** | **9.29** | **-0.15 (better)** |
| Qwen Demog no-ToM | 39.2% | 0.278 | 0.657 | 11.27 | +1.83 (worse) |
| Qwen Demog + ToM | 45.0% | 0.299 | 0.643 | 10.93 | +1.49 (worse) |

Qwen 235B is substantially worse than Llama 8B across all metrics, despite being a ~30x larger model. Diagnostic analysis reveals: Qwen is overconfident but miscalibrated (higher max probability, lower accuracy), has a DOWN bias in the no-ToM condition, and produces degenerate forecasters (the `contrarian_veteran` persona achieves only 30% accuracy with Brier 0.853). Neither Qwen ensemble beats the naive baselines.

### 11.9 Statistical Analysis (Linear Mixed Model)

To properly account for the correlated structure of the data, we fit linear mixed-effects models in R using lme4 + lmerTest with Satterthwaite degrees of freedom. We use demographic persona conditions only (+/- ToM), with model (llama/qwen) as a fixed effect.

**Critical correction (Feb 17): Period-within-scenario clustering.** Each of the 240 unique scenario-periods (10 x 24) has a single ground truth outcome, and all forecasters predict that same outcome. The `(1|scenario_id:period)` random intercept absorbs the shared difficulty within each scenario-period, giving more honest standard errors. A likelihood ratio test confirms this term is overwhelmingly justified (chi-sq = 641.5, p < 2.2e-16). See `docs/STATISTICAL_ANALYSIS.md` for full methodological details.

**Data:** N=4,800 individual forecasts across 4 conditions (2 models x 2 ToM, demographic only), 10 scenarios, 24 periods, 5 forecasters. 240 scenario-period clusters of ~20 observations each.

**Interaction test:** `sq_error ~ tom * model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)`. The tom:model interaction is non-significant (p = 0.480), confirming ToM helps both models equally. Dropped.

**Best model (main effects):**

`sq_error ~ tom + model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)`

| Fixed Effect | Coefficient | SE | df | t | p |
|-------------|-------------|------|------|-------|---------|
| Intercept (Llama, no-ToM) | 112.78 | 18.18 | 8.8 | 6.20 | 0.0002 *** |
| ToM | -17.27 | 7.81 | 4554 | -2.21 | 0.027 * |
| Qwen | +44.51 | 7.81 | 4554 | 5.70 | 1.3e-08 *** |

| Random Effect | Variance | Std.Dev | % of total |
|---------------|----------|---------|------------|
| scenario_id:period | 18,846 | 137.3 | **11.3%** |
| scenario_id | 103 | 10.1 | 0.1% |
| forecaster_id | 980 | 31.3 | 0.6% |
| Residual | 73,138 | 270.4 | 44.0% |

The period-within-scenario term absorbs **11.3%** of total variance that was previously lumped in the residual (49.6% -> 44.0%). The scenario-level intercept (0.1%) is negligible -- scenarios don't differ much on average, but they differ substantially period by period.

**Supplementary models:** Absolute price error (tom = -0.43, p = 0.001) and squared percentage error (tom = -7.40, p = 0.099) corroborate the primary finding. Cohen's d = -0.057 (small), ToM wins 7-8/10 scenarios across both models.

### 11.10 Limitations: Same-Model Confound

**Critical caveat:** The market simulation was generated using Llama 3.1 8B agents. Llama 8B forecasters are therefore predicting the behavior of agents that share their same weights, biases, and reasoning patterns. Qwen 235B forecasters are predicting agents that "think" differently.

This means the model comparison (Qwen coeff = +48.19, p < 0.0001) is confounded with a **same-model advantage**: Llama forecasters may implicitly understand Llama agents' behavioral tendencies without needing explicit descriptions. We cannot cleanly attribute Llama's superiority to model quality vs. same-model familiarity.

**Implications:**
- The model comparison should be interpreted as "same-model forecasting outperforms cross-model forecasting," not "smaller models are better at market prediction."
- The **ToM finding remains valid** — it is significant within both models (no interaction), meaning explicit agent descriptions help regardless of whether the forecaster shares the agents' underlying model.
- ToM may be especially valuable in **cross-model settings** — it partially compensates for the lack of implicit same-model understanding by providing explicit behavioral descriptions.

**To properly disentangle these effects**, a crossed design would be needed: run simulations with both Llama and Qwen agents, then have both models forecast both simulations. If Llama is genuinely better, it would win on both simulations. If it's a same-model effect, each model would win on its own simulation.

### 11.11 Information Structure

Each forecaster sees:
- **Market history:** Last 5 periods of price, volume, high, low
- **Persona prompt:** Either strategy-specific (e.g., "You are a trend-following analyst...") or demographic (e.g., "You are a 58-year-old retired floor trader...")
- **With ToM:** Additionally, descriptions of all 7 trading agent personas and their strategies

Forecasters do NOT see:
- Other forecasters' predictions
- Individual agent orders or positions
- The market clearing mechanism

This information asymmetry means forecasters must infer agent behavior from price patterns alone (no-ToM) or combine price patterns with knowledge of agent strategies (ToM).

### 11.12 Cost Analysis

| Condition | LLM Calls | Tokens | Runtime |
|-----------|-----------|--------|---------|
| Strategy no-ToM | 1,200 | 912K | 66 min |
| Strategy + ToM | 1,200 | 1,430K | 83 min |
| Demographic no-ToM | 1,200 | 934K | 71 min |
| Demographic + ToM | 1,200 | 1,448K | 80 min |
| **Total** | **4,800** | **4,724K** | **~5 hrs** |

ToM adds ~50% more tokens per call due to the included persona descriptions.

### 11.13 File Locations

| Item | Path |
|------|------|
| Forecasting script | `market/run_market_forecast.py` |
| **Llama 8B conditions** | |
| Strategy no-ToM | `outputs/market_llama_persona/forecasting/` |
| Strategy + ToM | `outputs/market_llama_persona/forecasting_tom/` |
| Demographic no-ToM | `outputs/market_llama_persona/forecasting_demographic/` |
| Demographic + ToM | `outputs/market_llama_persona/forecasting_demographic_tom/` |
| **Qwen 235B conditions** | |
| Demographic no-ToM | `outputs/market_llama_persona/forecasting_qwen_demographic/` |
| Demographic + ToM | `outputs/market_llama_persona/forecasting_qwen_demographic_tom/` |
| **Per-condition files** | |
| Per-forecast details | `{condition_dir}/forecast_details.json` |
| Per-forecast CSV | `{condition_dir}/forecast_results.csv` |
| Summary JSON | `{condition_dir}/forecast_summary.json` |
