# Causal Discovery Agent Design
**Project:** LLM Multi-Agent Simulation & Forecasting
**Date:** February 2026
**Status:** Implementation Phase

---

## Overview

This document outlines the design for a causal discovery layer added to the existing multi-agent simulation framework. The goal is to determine whether multi-agent LLM groups can recover the known causal structure of the market and conflict engines through targeted interventional queries.

**Primary DV:** Graph recovery quality (adjacency matrix Hamming distance, precision/recall on edges) across communication conditions.

**Secondary DV:** Does PID-measured epistemic synergy (edge-level) predict recovery quality? If so, this validates PID as a measure beyond behavioral coordination.

**Model:** Llama 3.3 70B or DeepSeek V3 via OpenRouter. Larger than simulation agents (Llama 8B) due to the reasoning demands of causal inference.

---

## Architecture

| Layer | Agents | Role | Status |
|---|---|---|---|
| **Simulation agents** | 7 market / 7 conflict | Pursue objectives, generate outcome data | Existing (persona condition) |
| **Causal modeler agents** | 3 per condition | Recover causal structure via interventions | New |

Causal modeler agents observe persona simulation output (which has significant synergy and richer behavioral structure) and query the engine via interventional rollouts. They do not participate in the simulation.

---

## Intervention Interface

Uniform across both engines. Three intervention types, all with **clamp-and-react** semantics: fix the target variable, re-run the engine for N periods, let all other agents react normally.

```python
# Single-agent intervention
intervention = {
    "type": "action" | "trait" | "event",
    "target": {
        "agent_id": "producer_A",
        "param": "limit_price",
        "value": 85.0
    },
    "run_periods": 3,
}

# Role-level intervention (market) — overrides ALL agents of a role
intervention = {
    "type": "trait",
    "target": {"role": "producer", "param": "production_cost", "value": 200},
    "run_periods": 3,
}

# Faction-level intervention (conflict) — overrides ALL agents in a faction
intervention = {
    "type": "trait",
    "target": {"faction": "novaris", "param": "hawk_dove", "value": 0.1},
    "run_periods": 3,
}
```

### Intervention types

| Type | What it tests | Market example | Conflict example |
|------|--------------|----------------|------------------|
| **Action** | `action → outcome` | Force producer_A limit_price = 85 | Force agent to play "military_buildup" |
| **Trait** | `trait → action → outcome` | Set production_cost = 50 | Set hawk_score = 0.2 |
| **Event** | `event → params → actions → outcome` | Force supply_disruption shock | Force border_incident event |

All three levels are needed to recover the full graph. Action interventions test the bottom of the causal chain. Trait interventions test the middle. Event interventions test the top.

**Trait interventions work differently across domains:** In the market, traits like `production_cost` are both prompt inputs AND hard engine constraints (`validate_order()` enforces them mechanistically). In conflict, `hawk_score` is prompt-only — the LLM mediates the effect. Noisier conflict trait interventions are themselves an interesting finding about how strongly LLM agents respect assigned dispositions.

### Implementation

**Market:** Current `run_period()` takes orders as input. Action overrides replace orders before `clear_market()`. Trait overrides patch `AgentState` fields before the LLM call. Event overrides inject/suppress shocks in `apply_shocks()`.

**Conflict:** Action overrides replace agent recommendations before `aggregate_faction_action()`. Trait overrides modify `hawk_dove` in the system prompt. Event overrides inject/suppress shocks in `apply_shocks()`.

### Budget

**Initial:** 30 interventions per agent. Calibrate down after pilot — observe where diminishing returns occur, then set the multi-agent budget per-agent below that inflection point. The goal is a sweet spot where single agents cannot recover the full graph but coordinated groups can.

---

## Ground Truth Causal Structure

### Market Engine

Derived from `market/engine.py`, `market/agents_config.py`, `market/shocks.py`.

#### Primary causal graph (cyclic)

```
INITIALIZATION:
  scenario_config
    ├─ base_price → production_cost (producer)
    ├─ base_price → demand_value (consumer)
    ├─ demand_intensity → demand_per_period (consumer)
    └─ cost_spread → production_cost divergence

SHOCKS (exogenous):
  shock_type/magnitude → agent_params
    ├─ supply_disruption → production_cost (×1.2–1.8)
    ├─ demand_surge → demand_per_period (×1.3–1.8)
    ├─ demand_drop → demand_per_period (×0.4–0.7)
    ├─ cost_reduction → production_cost (×0.6–0.85)
    ├─ storage_crisis → storage_cost (×2.0–4.0)
    └─ subsidy → cash (+500–2000)

AGENT DECISION (per period):
  production_cost ──→ agent_orders_t  (price floor for producers)
  demand_value ─────→ agent_orders_t  (price ceiling for consumers)
  price_history_t-1 → agent_orders_t  (trend signal, esp. speculators)
  cash_t ───────────→ agent_orders_t  (quantity ceiling for buyers)
  inventory_t ──────→ agent_orders_t  (quantity ceiling for sellers)

CLEARING (deterministic):
  agent_orders_t → clearing_price_t  (midpoint of marginal matched pair)

FEEDBACK (cyclic):
  clearing_price_t → fills → cash_{t+1} / inventory_{t+1}
  cash_{t+1} / inventory_{t+1} → agent_orders_{t+1}
  agent_orders_{t+1} → clearing_price_{t+1}

DIAGNOSTIC (not causal):
  production_cost ─┐
  demand_value ────┴→ fundamental_price  (computed output, NOT a cause of clearing_price)
```

#### Key causal facts

- **`clear_market()`**: Clearing price is deterministic from the order book. The ONLY direct causes of `clearing_price_t` are submitted limit prices and quantities.
- **`validate_order()`**: Orders truncated (not rejected) to agent capacity. Cash constrains buy quantity; inventory constrains sell quantity; role-specific params set price floors/ceilings.
- **`apply_period_costs()`**: Storage costs drain cash. Producers replenish inventory at `production_cost`. Consumers deplete inventory, gain `demand_value` per unit.
- **`compute_fundamental_price()`**: Shares common causes with clearing price but neither causes the other. Agents that infer `fundamental_price → clearing_price` are wrong — this is the critical confound.

#### Persona-driven structure

With personas, each agent has a distinct decision function (Momentum Rider buys uptrends, Value Contrarian fades them, etc.). The synergy pairs from PID (EC = 0.032, p = 0.002) reflect real interaction patterns mediated through the clearing mechanism. This creates a richer structure for modelers to discover than the no-persona case (EC = 0.005, ns).

---

### Conflict Engine

Derived from `conflict/engine.py`, `conflict/agents_config.py`.

#### Primary causal graph (cyclic)

```
AGENT DECISION:
  hawk_score_i ──────────→ action_recommendation_i_t  (prompt-mediated)
  escalation_index_{t-1} → action_recommendation_i_t  (agents respond to state)
  resources_i_t ─────────→ action_recommendation_i_t  (affordability constraint)
  faction_state_t ───────→ action_recommendation_i_t  (GDP, military, stability)

AGGREGATION (within faction, deterministic):
  action_recommendations (all faction agents) → faction_action_t
    weighted by role × action_category matrix
    snapped to nearest action in action space

ESCALATION (deterministic):
  novaris_action_t + tethys_action_t → escalation_index_t
    interaction_modifier:
      both escalate  → ×1.2 (amplification)
      both de-escalate → ×1.3 (peace momentum)
      mixed         → ×0.8 (dampening)
    momentum: -0.06 × (EI - 5.0) (mean reversion)

STATE UPDATES (deterministic, multiple):
  escalation_index_t → military_balance_t+1
  escalation_index_t → sanctions_level_t+1
  escalation_index_t → international_support_t+1
  escalation_index_t → GDP_t+1 (damage at high EI)
  escalation_index_t → political_stability_t+1
  GDP_t+1 → resources_t+1 (regeneration)
  faction_action_t → military_strength_t+1 (buildup/depletion)

FEEDBACK (cyclic):
  escalation_index_t → faction_state_{t+1} → action_recommendations_{t+1}
  resources_t → action_choice_t → costs → resources_{t+1}

SHOCKS (exogenous):
  border_incident (11%/period) → escalation_index (+0.5 to +1.5)
  diplomatic_crisis (8%) → escalation_index (+0.3 to +0.8)
  peace_initiative (12%) → escalation_index (-1.0 to -0.3)
  ceasefire_pressure (6%) → escalation_index (-0.8 to -0.2)
  economic_crisis (10%) → novaris_resources (×0.6–0.8)
  military_incident (10%) → military_balance (±0.15)
  international_pressure (8%) → sanctions_level (+0.1 to +0.3)
```

#### Key causal facts

- **Aggregation is weighted, not equal**: Role weights range from 0.5 to 2.0 depending on role × action category. Military Chief has 2.0× weight on military actions; Economic Advisor has 0.5×. A modeler that assumes equal aggregation will misestimate effect sizes.
- **Interaction modifier creates nonlinearity**: Two actions with delta=0.5 each produce 1.2 EI increase (mutual escalation) vs. 0.0 (mixed signals). This means `action_A → EI` depends on `action_B` — the effect is not separable.
- **16 actions** (not 15 as originally noted): ranging from troop_withdrawal (-1.0) to full_scale_attack (+2.5), each with a resource cost.
- **Mean reversion**: System pushes toward EI=5.0 with force proportional to deviation. This makes extreme states self-correcting, which modelers need to distinguish from agent de-escalation behavior.

#### Attractor dynamics and per-scenario hawk/dove shift

The escalation index converges to a **scenario-specific attractor** determined by the balance of three forces:

**1. Agent pressure.** Each agent's desired escalation change is `(hawk_dove - 0.5) * multiplier`, where multiplier=3.0 in mid-range EI (2–8) and drops to 1.0 at extremes (EI<2 or EI>8). Agents above hawk_dove=0.5 push EI up; agents below push it down. The per-faction deltas are weighted-averaged (role × action category weights), producing one continuous delta per faction per period.

**2. Mean reversion.** `momentum = -0.06 * (EI - 5.0)` — a weak restoring force centered at EI=5.0. At EI=8.0 this contributes -0.18/period; at EI=2.0 it contributes +0.18/period. Weak enough that agent pressure dominates in mid-range.

**3. Interaction modifier.** Both factions escalating → 1.2× amplification. Both de-escalating → 1.3× amplification. Mixed → 0.8× dampening. This positive feedback means consensus compounds: when agents agree, the effect overshoots the linear sum.

The attractor is the EI where these forces balance (net delta ≈ 0). With the base agent templates (hawk_dove scores: 0.85, 0.55, 0.25, 0.50, 0.45, 0.75, 0.30; weighted average ≈ 0.52), the net pressure is mildly escalatory (+0.445/period in mid-range). EI drifts up until the extreme-EI multiplier reduction (3.0→1.0) and mean reversion counterbalance it, stabilizing around EI ≈ 8.0.

**Per-scenario hawk_dove_shift** breaks this single-attractor degeneracy. Each scenario config includes a `hawk_dove_shift` drawn from U(-0.25, +0.10), applied to all agents in `create_agents()` with clamping to [0.05, 0.95]. This shifts the break-even point:

| hawk_dove_shift | Net agent pressure | Attractor EI |
|-----------------|-------------------|-------------|
| +0.10 | strongly escalatory | ~9–10 |
| 0.00 | mildly escalatory | ~8.0 |
| -0.05 | near break-even | ~4–5 |
| -0.10 | mildly de-escalatory | ~3–4 |
| -0.20 | strongly de-escalatory | ~0–2 |

The asymmetric range [-0.25, +0.10] centers near -0.075 (the approximate break-even shift), yielding roughly equal numbers of escalating and de-escalating scenarios. Cross-scenario EI standard deviation increases from ~0.20 (no shift) to ~2.7 (with shift).

#### Key differences from market for causal discovery

| Feature | Market | Conflict |
|---------|--------|----------|
| Agent→outcome mediation | Individual orders → clearing | Weighted aggregation → faction action → EI |
| Trait mechanism | Hard engine constraint | Prompt-only (LLM-mediated) |
| Nonlinearity | Marginal pair (mild) | Interaction modifier (strong) |
| State variables | 3 (cash, inventory, price) | 8+ (EI, GDP, military, stability, etc.) |
| Feedback complexity | Single loop | Multiple interlocking loops |
| PID synergy | EC = 0.032 (persona-dependent) | EC = 0.106 (domain-driven) |

Conflict is expected to be harder to recover.

---

## Experimental Conditions

### Communication structures

| # | Condition | Agents | Per-Agent Budget | Communication | Key question |
|---|-----------|--------|-----------------|---------------|-------------|
| 1 | **Single agent** | 1 | 30 | N/A | Baseline: how far can one agent get? |
| 2 | **Independent** | 5 | 6 each | None -- vote to merge graphs | Emergent epistemic coordination |
| 3 | **Debate** | 2 | 15 each (alternating) | Shared results + debate injection | Does social pressure affect inference? |
| 4 | **Specialization** | 3+1 | ~10 each (proportional) | Variable subsets + LLM aggregator | Designed complementary coverage |

Crossed with **2 engines** (market, conflict) = 8 cells. All conditions use total budget=30 for fair comparison.

**Implementation status (Feb 24):** All 4 structures implemented in `causal_discovery/multi_agent/`. Dry-run verified for all 8 conditions. Sequential sharing was dropped from the original 5-condition design in favor of the more informative debate structure (which subsumes sequential sharing's evidence-building with the addition of adversarial hypothesis testing).

### Per-condition procedure

1. Modeler agents receive observational data from the persona simulation runs
2. Agents scan for correlational patterns (candidate edges)
3. Agents propose and execute interventions (clamp-and-react rollouts)
4. Agents update their running causal hypothesis (edge confidence matrix)
5. After budget exhaustion, agents declare a final candidate graph
6. Score against ground truth

### Multi-agent graph aggregation

In multi-agent conditions (independent, debate, specialization), each agent produces its own declared graph. These are merged into a single group graph using one of four aggregation strategies (`causal_discovery/multi_agent/aggregation.py`):

**1. Majority vote** — Include an edge if >50% of agents declare it. For 5 independent agents, an edge needs ≥3 votes.

```
Agent A declares: shock → resources, hawk_score → escalation_index
Agent B declares: shock → resources, hawk_score → agent_recommendation
Agent C declares: shock → resources

Majority vote result: shock → resources (3/3 ✓), hawk_score → escalation_index (1/3 ✗),
                      hawk_score → agent_recommendation (1/3 ✗)
```

**2. Confidence-weighted vote** — Weight each agent's edge declaration by its confidence level (high=3, medium=2, low=1). Include edge if weighted sum exceeds `n_agents × 3 / 2`. This means a single high-confidence declaration from one agent can't override the group, but two medium-confidence declarations can.

```
Agent A: shock → resources (high, weight=3)
Agent B: shock → resources (low, weight=1)
Threshold for 2 agents: 2 × 3 / 2 = 3.0
Weighted sum: 3 + 1 = 4 > 3 → included
```

**3. Union** — Include an edge if ANY agent declares it. Maximizes recall at the expense of precision. Useful when individual agents explore different parts of the graph and under-declaration is the primary failure mode.

**4. Intersection** — Include an edge only if ALL agents declare it. Maximizes precision at the expense of recall. Acts as a conservative filter — only edges with unanimous agreement survive.

The choice of aggregation strategy interacts with the communication condition. In the **independent** condition, agents explore independently, so union captures the broadest coverage while intersection filters to only the most robust findings. In the **specialization** condition, agents cover different variable subsets, so union is the natural merge (each specialist contributes edges from their assigned region). The **debate** condition produces 2 graphs from adversarial partners, where intersection captures consensus and union captures the full space of plausible edges.

---

## Scoring

### Graph recovery (primary DV)

**Adjacency matrix Hamming distance** on cyclic directed graphs. For each possible directed edge, the ground truth says present/absent, the agent says present/absent. Count disagreements.

Both engines have feedback loops, so the ground truth is cyclic. Scoring allows cycles — no DAG assumption. This is mechanically the same as SHD (count edge additions, deletions, reversals) applied to an adjacency matrix without acyclicity constraint.

**Supplementary metrics:**
- Precision: fraction of reported edges that are correct
- Recall: fraction of true edges that are reported
- Per-edge difficulty analysis: which edges are hardest to recover?

### PID synergy (secondary DV)

**Design:** Edge-level PID (Option B from design discussion).

- **Source variables:** Agent_i's confidence on edge_k, Agent_j's confidence on edge_k (discretized: absent / uncertain / present)
- **Target variable:** Ground truth for edge_k (binary: exists or not)
- **Unit of analysis:** Each edge, pooled across scenarios
- **Method:** Williams-Beer Imin (consistent with existing PID analyses)

Synergy means the pair jointly identifies edges that neither identifies alone. This is **epistemic coordination** — a novel application of PID beyond behavioral coordination.

**Key analysis:** Correlate EC with graph recovery quality (Hamming distance) across scenarios and conditions. If higher synergy predicts better recovery, PID is validated as a measure of epistemic coordination.

PID is most meaningful in the **independent** condition, where synergy is emergent (not designed). Structured conditions (sequential, debate, specialization) test whether designed coordination beats emergent coordination.

---

## Agent Design

### Causal hypothesis representation

Agents maintain a **confidence matrix** over possible directed edges. For N variables, this is an N×N matrix where each cell is a confidence level (absent / uncertain / present) for the directed edge row→col.

### Agent loop (per intervention)

1. Review current hypothesis and observational/interventional evidence
2. Identify the most informative intervention to run next (information gain)
3. Specify intervention (type, target, value, run_periods)
4. Receive engine response (outcome trajectory)
5. Update confidence matrix based on observed vs. expected outcomes
6. Repeat until budget exhausted

The agent loop is implemented as a **multi-turn LLM conversation** (`agent.py:run_single_agent`). The full conversation history — including all past proposals, results, and hypothesis updates — is carried forward, so the agent can reason over its accumulated evidence without explicit memory management.

#### Intervention selection prompting

Intervention selection is entirely LLM-driven. The `build_intervention_prompt()` in `prompts.py` provides the agent with its current hypothesis, past results, remaining budget, and available intervention types, then enforces six critical rules:

1. **No repetition** — Never repeat an intervention already run. If the same variable was already tested with the same type, choose a different variable or type.
2. **Type diversity** — Use all three intervention types (action, trait, event). If you haven't used events yet, use one now.
3. **Extreme values** — Use extreme values to maximize detectable effects. For traits, try 0 or 10× the normal value. For events, use magnitude ≥ 2.0.
4. **No futile retries** — If an intervention showed "no detectable effect", do not retry the same thing. Try a different variable or a much more extreme value.
5. **Direct vs. indirect** — Distinguish direct from indirect causation. If X → Y → Z, intervening on X changes Z but X does not directly cause Z. To test whether X directly causes Z, you must also intervene on the mediator Y.
6. **Common causes** — Correlation between two variables may be due to a common cause. Intervene on the suspected cause to test this.

The agent must also specify what it expects to observe if the hypothesized edge exists vs. does not exist, enforcing an explicit hypothesis-testing structure:

```json
{
    "intervention": {"type": "trait", "target": {...}, "run_periods": 3, "description": "..."},
    "hypothesis_being_tested": "Does hawk_score cause escalation_index directly?",
    "expected_if_edge_exists": "Escalation index increases when hawk_score is set to 0.9",
    "expected_if_no_edge": "Escalation index unchanged despite hawk_score override"
}
```

After each intervention executes, the result deltas are fed back and the agent produces a structured hypothesis update — marking edges as confirmed, disconfirmed, or still uncertain, plus listing `key_uncertainties` that inform the next intervention choice. This creates an iterative uncertainty-reduction loop where the agent maintains a running set of unknowns and selects the intervention that would most reduce that set.

#### Guardrails

The agent loop includes several guardrails in `agent.py`:

- **Duplicate detection** (line 524): Interventions are keyed by `(type, json(target))`. If an agent proposes an already-run intervention, it is skipped and the agent is told to propose something different.
- **Invalid type rejection** (line 450): If the agent invents a type outside `{action, trait, event}`, the proposal is rejected with a corrective message.
- **Variable specialization** (line 493): In the specialization condition, agents are restricted to a subset of variables. Out-of-scope proposals are rejected.
- **Target normalization** (lines 472–489): The loop normalizes variant key names (e.g., `"shock"` → `"shock_type"`, `"action"` → `"value"`) so minor format deviations from the LLM don't cause execution failures.

### Interleaving

Agents may interleave structure discovery (which edges exist?) and effect estimation (how strong are they?) within a single intervention. Whether LLM agents do this spontaneously vs. rigidly separating phases is a behavioral outcome of interest.

### Confound awareness

Agents need to be aware of three classes of confound:

- **Agent reactivity**: Forcing one agent's action changes other agents' responses (mediated through market/conflict state). Naive pairwise testing ignores this mediation.
- **Feedback loops**: Effects propagate forward in time and loop back. An intervention at period t affects period t+1 through state updates.
- **Common causes**: Variables may be correlated without direct causal connection (e.g., fundamental_price and clearing_price in market).

Whether agents demonstrate this awareness spontaneously or need prompting is itself an outcome.

#### Prompting strategies for confound mitigation

The prompt design in `prompts.py` addresses each confound class:

**Path collapse prevention.** The intervention prompt's Rule 5 explicitly instructs agents to distinguish direct from indirect causation: "If X → Y → Z, intervening on X changes Z but X does not DIRECTLY cause Z. To test whether X directly causes Z, you must also intervene on the mediator Y." This is reinforced by the expanded return variables (Fix 1 in pilot findings), which make mediators like `agent_orders` and `faction_action` visible in intervention trajectories. Without visible mediators, path collapse is inevitable regardless of prompting.

**Common cause awareness.** Rule 6 instructs agents to consider that "correlation between two variables may be due to a COMMON CAUSE, not direct causation. Intervene on the suspected cause to test this." The system prompt for both domains also states "Correlation does not imply causation. Two variables may be correlated because they share a common cause." Despite this, the `fundamental_price → clearing_price` confound trap persisted in 3/3 pilot runs — the model observes the correlation but never designs an intervention that tests the common-cause hypothesis (e.g., intervening on `fundamental_price` directly to see if clearing_price changes). This suggests explicit prompting is necessary but insufficient for common cause reasoning.

**Feedback loop awareness.** The system prompts note that "Feedback loops exist: A may cause B which causes A in the next period." The declaration prompt asks agents to report `feedback_loops` as a separate output field, encouraging them to consider cyclical structure. The 3-period rollout window (`run_periods=3`) is long enough for one feedback cycle to manifest but short enough that multi-hop effects remain distinguishable from direct effects.

---

## Implementation Plan

### Phase 1: Intervention interface
- [x] Add `run_intervention()` to market engine (action, trait, event overrides)
- [x] Add `run_intervention()` to conflict engine (action, trait, event overrides)
- [x] Define ground truth adjacency matrices for both engines
- [x] Implement scoring functions (Hamming distance, precision, recall)

### Phase 2: Single-agent pilot
- [x] Design causal modeler agent prompts (hypothesis representation, intervention proposal)
- [x] Run single agent, market domain, 30 intervention budget
- [x] Evaluate: can the agent recover any structure? Where does it fail?
- [x] Run single agent, conflict domain (multi-turn + faction-level overrides)
- [x] Cross-domain comparison (3 replicates × 2 domains, budget=30)
- [x] Calibrate budget / improve prompts based on pilot failure modes

### Phase 3: Multi-agent conditions
- [x] Implement 4 communication structures (single, independent, debate, specialization) in `causal_discovery/multi_agent/`
- [x] Extract reusable agent pipeline (`agent.py`: AgentResult, setup_domain, run_single_agent)
- [x] Graph aggregation (`aggregation.py`: majority_vote, confidence_weighted, union, intersection)
- [x] Causal-discovery-specific personas (`config.py`: 5 reasoning strategies, maximalist/minimalist debate pair, variable subgraphs)
- [x] CLI runner + full sweep (`runner.py`, `run_all.py`)
- [x] Dry-run verification: all 8 conditions (4 structures x 2 domains) pass at budget=30
- [ ] Run all conditions on both engines with live LLM calls
- [ ] Score graph recovery across conditions

### Phase 4: PID analysis
- [ ] Adapt edge-level PID measurement
- [ ] Compute EC across conditions
- [ ] Correlate synergy with recovery quality

### Phase 5: Analysis
- [x] Cross-domain comparison (market vs. conflict recovery difficulty) — preliminary (single-agent)
- [ ] Communication structure effects on recovery and synergy
- [ ] Per-edge difficulty analysis
- [ ] Intervention efficiency analysis (which agents make informative interventions?)

---

## Pilot Findings (Feb 2026)

### Early iterations (market only, pre-infrastructure fixes)

| Run | Budget | Key Result |
|-----|--------|------------|
| 5-int v1 | 5 | Recovered shock→production_cost→orders→price chain. Missed feedback loops. |
| 30-int v1 | 30 | **Confound trap**: model declared fundamental_price→clearing_price (false positive). Repeated similar interventions — poor budget efficiency. |
| 15-int v2 | 15 | Better prompting reduced repetition. Still classified indirect effects as direct (e.g., shock→clearing_price without noting mediation through production_cost). |

### Cross-domain comparison (Feb 21, budget=30, 3 replicates, multi-turn)

All runs use Llama 3.3 70B via OpenRouter, multi-turn conversation, role/faction-level trait overrides.

| Domain | Mean F1 | Mean Precision | Mean Recall | Mean HD | True Edges |
|--------|---------|----------------|-------------|---------|------------|
| **Market** | 0.256 ± 0.052 | 0.487 ± 0.109 | 0.174 ± 0.036 | 23.3 ± 1.9 | 23 |
| **Conflict** | 0.235 ± 0.130 | 0.500 ± 0.136 | 0.159 ± 0.098 | 20.3 ± 1.7 | 21 |

Per-replicate:

| Run | P | R | F1 | HD | Edges | Dup | No-effect |
|-----|---|---|----|----|-------|-----|-----------|
| Market seed42 | 0.571 | 0.174 | 0.267 | 22 | 7/23 | 3 | 9 |
| Market seed43 | 0.333 | 0.130 | 0.188 | 26 | 9/23 | 1 | 10 |
| Market seed44 | 0.556 | 0.217 | 0.312 | 22 | 9/23 | 3 | 9 |
| Conflict seed42 | 0.333 | 0.048 | 0.083 | 22 | 3/21 | 8 | 4 |
| Conflict seed43 | 0.667 | 0.286 | 0.400 | 18 | 9/21 | 7 | 2 |
| Conflict seed44 | 0.500 | 0.143 | 0.222 | 21 | 6/21 | 10 | 1 |

### Per-edge recovery rates

**Market — reliably recovered edges (3/3 replicates):**
- `production_cost → fundamental_price`, `demand_value → fundamental_price` (diagnostic outputs)
- `agent_orders → clearing_price`, `agent_orders → volume` (clearing mechanism)

**Market — never recovered (0/3):** All shock edges, all feedback loops, all state-update edges (clearing_price → cash/inventory/price_history), all trait→order edges except inventory→orders (1/3).

**Market — consistent false positives:** `fundamental_price → clearing_price` (3/3), `demand_per_period → clearing_price` (2/3), `demand_value → clearing_price` (2/3).

**Conflict — best recovered edges:**
- `shock → military_balance` (3/3)
- `shock → sanctions_level` (2/3), `faction_action → escalation_index` (2/3)

**Conflict — never recovered (0/3):** The full decision chain (`hawk_score → agent_recommendation → faction_action`), all EI state updates (EI → GDP, EI → political_stability, EI → sanctions, EI → international_support), all cross-variable updates (gdp → resources, sanctions → gdp, military_strength → military_balance).

**Conflict — consistent false positives:** `hawk_score → escalation_index` (3/3 — path collapse), `escalation_index → faction_action` (2/3 — skips aggregation).

### Key failure modes

**Shared across domains:**

1. **Under-declaration** — The model declares only 3-9 edges out of 21-23 true edges. Recall (~16%) is the bottleneck. It only reports edges it directly tested and misses all state-update and feedback edges it never probed. The declaration prompt doesn't sufficiently encourage exhaustive enumeration.

2. **Path collapse / indirect-as-direct** — The model collapses multi-step causal paths into direct edges. Market: `demand_value → clearing_price` instead of `demand_value → agent_orders → clearing_price`. Conflict: `hawk_score → escalation_index` instead of `hawk_score → agent_recommendation → faction_action → escalation_index`. The model observes end-to-end effects and declares them as direct without testing mediators.

**Market-specific:**

3. **Confound trap** — `fundamental_price → clearing_price` is hallucinated in 3/3 runs. They share common causes (production_cost, demand_value) but the model never intervenes on the mediator to distinguish correlation from causation. This was predicted as the critical confound in the ground truth design.

**Conflict-specific:**

4. **Severe duplication** — 7-10 duplicate interventions per run (vs 1-3 for market). The model exhausts novel intervention ideas by ~intervention 15 and starts repeating. The conflict domain has fewer parameter dimensions to vary (hawk_dove is the main trait vs production_cost, demand_value, demand_per_period, storage_cost in market).

5. **Aggregation invisibility** — The `agent_recommendation → faction_action` edge is recovered 0/3 times. The weighted aggregation step is invisible because the model never comparatively tests individual agent overrides vs faction-level overrides to observe the dilution effect.

6. **Higher variance** — F1 ranges from 0.083 to 0.400 across replicates (market: 0.188 to 0.312). Conflict outcomes are more sensitive to which interventions the model happens to choose early, which determines the exploration trajectory for remaining budget.

### Architecture decisions

**Role/faction-level trait overrides:** Added `"role"` key (market) and `"faction"` key (conflict) to trait intervention targets. When present, ALL matching agents are overridden instead of one. This produces detectable signals even for infra-marginal agents. Backward compatible — single-agent `"agent_id"` still works.

**Multi-turn conversation:** Replaced stateless 2-message `call_llm()` calls with persistent message history. The model sees the full conversation including all past interventions, results, and its own reasoning. Largely eliminates repetition in market (1-3 duplicates), partially in conflict (7-10 duplicates due to limited parameter space).

**Domain CLI:** `run_pilot.py` supports `--domain market|conflict`, routing to `run_pilot()` or `run_conflict_pilot()` with domain-appropriate setup, warm-up, history formatting, intervention execution, and scoring.

### Recall improvement fixes (Feb 21)

Root cause analysis identified **data observability** as the primary bottleneck, not model reasoning quality. Two models (Llama 3.3 70B and DeepSeek V3) produced identical failure patterns on the original return variables, proving the issue was structural.

**Fix 1: Expanded return variables (both domains)**

Market trajectories originally returned only 3 variables (clearing_price, volume, fundamental_price). The key mediator `agent_orders` was never visible, so no model could distinguish direct from indirect effects (e.g., `production_cost → clearing_price` vs `production_cost → agent_orders → clearing_price`).

Added aggregate order stats and agent state to market rollout:
- `avg_bid_price`, `avg_ask_price` (scalar proxies for agent_orders)
- `total_bid_qty`, `total_ask_qty` (quantity proxies for agent_orders)
- `total_cash`, `total_inventory` (agent state proxies)

Added intermediate variables to conflict rollout:
- Faction-level state: `{faction}_gdp`, `{faction}_military_strength`, `{faction}_political_stability`
- Recommendation proxies: `{faction}_rec_escalation` (mean escalation delta of agent recommendations)
- Action proxies: `{faction}_action_delta` (escalation delta of chosen faction action)

These are mapped back to ground truth variable names via `_to_generic_var()` for scoring.

**Fix 2: Evidence summary (programmatic, no LLM)**

New `build_evidence_summary()` function scans all `InterventionResult` objects and builds per-variable tables of what moved when. Provided to the model at declaration time so it doesn't need to recall evidence from a long conversation.

**Fix 3: Per-variable enumeration declaration prompt**

Rewrote declaration prompt to ask the model to enumerate parents and children for EACH variable, with explicit instruction to err on the side of inclusion. Includes low-confidence edges in the output schema.

**Fix 4: Truncated declaration context**

Replaced the full multi-turn conversation (69k+ tokens after 30 interventions) with a fresh 2-message conversation (system prompt + declaration prompt with evidence summary). Eliminates context saturation at declaration time.

**Fix 5: Invalid intervention type guard**

DeepSeek V3 occasionally invented invalid intervention types (e.g., "terminate") when stuck. Added validation that rejects anything not in `("action", "trait", "event")` and asks the model to propose a valid intervention instead.

### Results after fixes (Feb 21)

| Run | Domain | Model | Precision | Recall | F1 | HD |
|-----|--------|-------|-----------|--------|----|----|
| Baseline (3-rep avg) | Market | Llama 3.3 70B | 0.487 | 0.174 | 0.256 | 23.3 |
| + all fixes | Market | DeepSeek V3 | 0.417 | 0.652 | 0.508 | 17 |
| Baseline (3-rep avg) | Conflict | Llama 3.3 70B | 0.500 | 0.159 | 0.235 | 20.3 |
| + all fixes | Conflict | DeepSeek V3 | 0.300 | 0.286 | 0.293 | 19 |

Market recall improved **17% → 65%** (3.7× increase). F1 nearly doubled from 0.256 to 0.508. The expanded return variables allowed the model to correctly identify mediator edges like `production_cost → agent_orders` and `cash → agent_orders` instead of declaring the collapsed `production_cost → clearing_price`.

Conflict recall improved **16% → 29%** (1.8× increase). Smaller improvement because conflict causal chains are longer (3 hops: `hawk_score → agent_recommendation → faction_action → escalation_index`) and the interaction modifier creates nonlinearities that are harder to detect via single-variable interventions.

---

## Open Questions

1. **~~Recall bottleneck~~** — ~~Single-agent recall is ~16% in both domains at budget=30.~~ **Largely resolved for market** (recall now 65% with expanded return vars + evidence summary). Conflict recall (29%) still has room for improvement — the longer causal chains and interaction modifier nonlinearities remain challenging.

2. **Conflict duplication** — Fixed by invalid type guard (prevents "terminate" loops) but the fundamental issue of limited parameter space remains. Conflict has fewer independent knobs to turn than market.

3. **Number of scenarios** — 10 scenarios per condition gives 150-230 edge-level observations for PID (depending on variable count). May need 20+ for reliable Williams-Beer estimation.

4. **Variable granularity** — Current: 12 market / 13 conflict variables. Both are at the limit of what a single agent can probe with 30 interventions. Consider whether coarser graphs (collapsing agent_recommendation + faction_action) would be more appropriate for single-agent recovery.

5. **~~Prompt engineering~~** — ~~Structured explicit-enumeration declaration may dramatically improve recall.~~ **Implemented** — per-variable enumeration with evidence summary. Combined with expanded return vars, this was effective for market domain.

6. **Model comparison** — DeepSeek V3 and Llama 3.3 70B produced identical results on the original (limited) return vars, confirming data observability as the bottleneck rather than model quality. Systematic model comparison on the improved pipeline is still needed.

7. **Conflict nonlinearity** — The interaction modifier (mutual escalation ×1.2, mixed ×0.8) means `action_A → EI` depends on `action_B`. Single-variable interventions cannot fully capture this. May need multi-variable interventions or factorial designs.
