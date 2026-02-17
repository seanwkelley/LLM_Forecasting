# Simulation Mechanics: Sequential Action Order

**Version 3.8.5** | **Last Updated:** February 10, 2026

---

## Overview

This document explains the **sequential execution order** within each simulation period and its implications for crisis dynamics and forecasting.

---

## Period Execution Sequence

Each simulation period follows this exact order:

### 1. External Events Generation
- **Timing:** Before any faction acts
- **Types:** Battlefield developments, economic shocks, diplomatic events, cyber incidents, naval incidents, air warfare, information warfare, shock events (15 types total)
- **Probabilistic:** Events occur based on probability thresholds (e.g., 60% chance of battlefield event)
- **Effect Application:** 50-85% effectiveness rates (battlefield 85%, sanctions 70%, diplomacy 50%, etc.)

### 2. Faction Actions (Sequential Order)

Factions act in **strict sequential order**:

```
1. major_power (Novaris - aggressor)
2. small_power (Tethys - defender)
3. meridian (external actor)
4. valkoria (external actor)
5. aurelia (external actor)
6. international_org (external actor)
```

**Implementation:** See `src/agent_decision.R` line 1395

**For each faction's turn:**
- **Pre-action coordination:** Agents within faction discuss strategy (if 2+ agents)
- **Action decision:**
  - Major/small powers: Domain experts propose → President approves (3-6 actions)
  - External actors: Single action decision
- **Action execution:** Actions execute immediately with state effects applied

### 3. Post-Action Discussion
- All agents see all faction actions from this period
- Agents react to outcomes and coordinate responses

### 4. Aggregator Assessment
- Evaluates collapse probability based on complete period state
- Sees all events, all actions, all state changes

---

## Information Asymmetry

### Critical Implication: Responders See Current Actions

**Within Period N:**

| Faction | Sees When Acting | Does NOT See When Acting |
|---------|-----------------|--------------------------|
| **Novaris** (acts 1st) | Period N external events<br>Period N-1 final state (incl. Tethys's N-1 action) | Tethys's Period N action (hasn't happened yet)<br>External actors' Period N actions |
| **Tethys** (acts 2nd) | Period N external events<br>Period N-1 final state<br>**✅ Novaris's Period N action** | External actors' Period N actions |
| **External actors** (act 3rd-6th) | Period N external events<br>Period N-1 final state<br>**✅ Novaris's Period N action**<br>**✅ Tethys's Period N action** | Later external actors' actions |

### Example Cascade

**Scenario: Period 5 escalation**

1. **External event generated:** "Border skirmish intensifies" (random, pre-determined)

2. **Novaris acts first:**
   - Sees: Border skirmish + Period 4 state
   - Does NOT see: Tethys's response (hasn't happened)
   - Decision: "Launch limited offensive" → captures 3% territory
   - **State immediately updated:** `territory_controlled += 0.03`, `military_balance -= 0.10`

3. **Tethys acts second:**
   - Sees: Border skirmish + Novaris's offensive + territory loss
   - **This is reactive:** Tethys responds to current-period aggression
   - Decision: "Emergency mobilization + request international aid"
   - **State immediately updated:** `crisis_level += 1`, mobilization recorded

4. **External actors act third:**
   - See: Border skirmish + Novaris offensive + Tethys mobilization
   - **Fully informed of intra-period cascade**
   - Decisions: Meridian sends aid, Valkoria supports Novaris, etc.

5. **Period 6 begins:**
   - Now Novaris sees Tethys's Period 5 mobilization
   - Novaris can adjust strategy based on Tethys's Period 5 response

---

## Implications for Analysis

### 1. Realistic Defender Dynamics
- Defenders in real conflicts respond to aggressor moves
- Sequential order captures this: Tethys **reacts** to Novaris's current actions
- Creates realistic action-reaction cycles

### 2. Escalation Cascades Within Periods
- Single period can contain multi-step escalation:
  - Novaris offensive → triggers Tethys mobilization → triggers external aid
- All recorded as "Period N events" but have **causal sequence**

### 3. Forecasting Implications
- Forecasting prompts describe complete period outcomes
- But implicit causal structure: some actions are **initiating** (Novaris), others are **reactive** (Tethys)
- Enhanced prompts (with SHOCK descriptions) make initiating events explicit:
  > "*** SHOCK: Aggressor Breakthrough *** - captured 4.4% territory, encirclement of key city. In response, defender declared emergency mobilization."

### 4. Strategic Timing Advantage
- **Novaris has first-mover advantage:** Acts before seeing defensive response
- **Tethys has information advantage:** Sees offensive before responding
- **External actors have observational advantage:** See both sides' moves

---

## State Threading Within Factions

For multi-action factions (Novaris, Tethys), approved actions execute **sequentially** with state threading:

```r
state <- initial_state
for (action in approved_actions) {
  result <- execute_action(action, state)
  state <- result$state  # Preserve mutations
}
# Return final threaded state
```

**Example: Tethys Period 7**
1. Action 1: "mobilize_reserves" → increases military capability
2. Action 2: "request_military_aid" → sees updated capability in state
3. Action 3: "defensive_fortifications" → compounds with mobilization

All three actions see cumulative effects of prior actions **within the same faction's turn**.

---

## Design Rationale

### Why Sequential Not Simultaneous?

**Realism:**
- Real geopolitical actors don't move simultaneously
- Intelligence gathering allows observation of adversary moves
- Defenders typically respond to aggressor actions, not vice versa

**Technical:**
- R's copy-on-modify semantics require explicit state threading
- Sequential execution preserves all ~30 direct state mutations
- Parallel execution would require complex state reconciliation

**Analytical:**
- Creates identifiable causal chains for research
- Enables testing hypothesis: "Does information advantage affect outcomes?"
- Matches empirical conflict dynamics (offense-defense cycles)

---

## Verification

To verify sequential order, see:

**Code Implementation:**
- `src/agent_decision.R` line 1395: `factions <- c("major_power", "small_power", "meridian", ...)`
- `src/agent_decision.R` line 1397: `for (faction in factions)`
- `src/multi_action_effects.R` line 88: Sequential execution with state threading

**Test Output:**
Check any simulation log file:
```
Period 5:
--- MAJOR POWER Faction ---
  Action decision...
  → offensive_operation
--- SMALL POWER Faction ---
  Action decision...
  → defensive_fortifications (reacts to offensive)
--- MERIDIAN Faction ---
  Action decision...
  → military_aid_defender (reacts to both)
```

---

## Future Research Questions

1. **Timing Sensitivity:** Does first-mover advantage outweigh information advantage?
2. **Forecast Adjustment:** Do forecasters implicitly understand causal sequences from narrative descriptions?
3. **Counter-factual:** What if factions acted simultaneously? Would outcomes differ?
4. **Reaction Time:** Should defenders have probability of failing to respond within same period?

---

## Related Documentation

- **[MULTI_ACTION_SYSTEM_GUIDE.md](guides/MULTI_ACTION_SYSTEM_GUIDE.md)** - Multi-action execution
- **[STATE_THREADING_GUIDE.md](STATE_THREADING_GUIDE.md)** - State mutation preservation (if created)
- **[FORECASTING_SYSTEM.md](FORECASTING_SYSTEM.md)** - LLM forecasting methodology

---

**Status:** ✅ Documented | **Version:** 3.8.5
