# Multi-Action Proposal System Guide

**Version:** 3.9.0
**Implemented:** 2026-01-31
**Updated:** 2026-02-14 (Parameter sensitivity fix, exact numeric values in agent prompts)
**Status:** PRODUCTION READY

---

## Overview

The Multi-Action Proposal System replaces the single-action decision process for major factions (Novaris/Tethys) with a more realistic multi-track approach where:

1. **Domain experts propose** 1-3 actions in their area (Military, Intelligence, Diplomatic, Economic)
2. **President approves/vetoes** each proposal based on strategic judgment
3. **Multiple actions execute** in parallel (typically 3-6 per faction per period)
4. **Effects resolve** with cumulative, contradictory, and synergistic logic

---

## Key Features

### 1. Domain Expert Proposals

Each domain expert proposes actions ranked by priority:

**MILITARY (General, Defense Minister):**
- PRIMARY: Most important military action
- SECONDARY: Supporting military action (if resources allow)
- TERTIARY: Opportunistic military action (optional)

**INTELLIGENCE (Intelligence Director):**
- PRIMARY: Most important covert/intel action
- SECONDARY: Supporting operation
- TERTIARY: Opportunistic operation

**DIPLOMATIC (Foreign Minister, Diplomat):**
- PRIMARY: Main diplomatic action
- SECONDARY: Supporting diplomatic track

**ECONOMIC (Economic Minister):**
- PRIMARY: Main economic action
- SECONDARY: Supporting economic measure

### 2. Presidential Agency

President has **strategic choice**, not mechanical response:

**Strategic Options:**
- **DE-ESCALATE:** Approve only diplomatic/defensive, veto offensive
- **MAINTAIN POSTURE:** Approve defensive + diplomatic, veto high-risk
- **APPLY PRESSURE:** Approve some offensive alongside defensive
- **FULL ESCALATION:** Approve most/all proposals

**Decision factors:**
- President's worldview (liberal institutionalist vs realist vs nationalist)
- Hawk/dove orientation (independent of crisis level)
- Strategic judgment (can escalate in low crisis OR de-escalate in high crisis)
- Resource constraints (can't afford everything)
- Contradictions (peace talks + sabotage = risky)

### 3. Multi-Action Effect Resolution

**Cumulative Effects:**
- Actions in different domains stack additively
- Example: military_buildup + peace_talks → both effects apply

**Diminishing Returns:**
- Multiple actions in same category have diminishing effectiveness
- Example: military_buildup (+5%) + defensive_fortification (+3%) = +8% total
- Second action only 60% as effective due to saturation

**Contradictions:**
- Incompatible actions reduce effectiveness or cancel out
- Example: peace_talks + sabotage (if detected) → diplomatic crisis, peace fails
- Detection risk for covert actions

**Synergies:**
- Compatible actions amplify each other
- Examples:
  - intelligence_gathering + sabotage = +20% sabotage effectiveness
  - military_buildup + defensive_fortification = -0.5 crisis (deterrence)
  - peace_talks + coalition_building = stronger negotiating position

**Resource Constraints:**
- Total cost of approved actions cannot exceed ~10-15% of faction GDP per period
- President warned if total exceeds budget
- Expensive actions (military_buildup $5B, financial_aid $2B) vs cheap (diplomatic_visit $0.1B)

---

## Implementation Details

### Core Files

**`src/multi_action_system.R`** — Proposal and approval
- `generate_domain_proposals()` - Generate expert proposals via LLM
- `presidential_approval()` - President reviews and approves/vetoes
- `extract_approved_actions()` - Get list of approved actions

**`src/multi_action_effects.R`** — Effect resolution
- `resolve_multiple_action_effects()` - Execute actions, thread state, apply effects
- `detect_contradictions()` - Find incompatible actions
- `detect_synergies()` - Find complementary actions
- `apply_effects_to_state()` - Utility (GDP/territory/costs application)
- `convert_result_to_effects()` - Map action results to accumulator format
- `accumulate_effects()` / `scale_effects()` - Effect math

**`src/action_execution.R`** — Action execution with direct state mutations
- `execute_action()` - Execute a single action, returns result + mutated state

**`src/simulation_with_actions.R`** — Main simulation loop
- Generates external events, executes agent decisions, applies event effects to state
- Handles all 15 external event types with probabilistic effectiveness
- Processes single-action results for GDP, international support, trust

**`src/event_generator.R`** — External event generation
- `generate_external_events()` - Draw from EXTERNAL_EVENTS config
- `generate_battlefield_event()`, `generate_naval_event()`, `generate_air_event()`, etc.
- `generate_shock_event()` - High-impact rare events

**`src/agent_decision.R`** — Decision orchestration
- Multi-action flow for major/small power factions (3+ agents)
- Single-action flow for external actors (Meridian, Valkoria, Aurelia, International Org)

**`src/forecast_prompts_public_v2.R`** — Forecasting prompt generation
- `generate_public_forecast_prompt_v2()` - Convert state to intelligence briefing
- `generate_all_public_forecast_prompts_v2()` - Generate all periods for TRUE or CONTROL
- Text conversion: `military_balance_to_text()`, `crisis_level_to_text()`, etc.
- `action_to_news()` - Convert agent actions to observable news reports

**`src/control_condition.R`** — Control condition randomization
- `generate_control_condition()` - Apply 3-layer randomization
- `permute_state_metrics()` - Constrained metric shuffling
- `permute_event_narratives()` - Shuffle + flip events
- `randomize_intermediate_probabilities()` - Random walk for assessments

**`config.R`** — Configuration
- `ENABLE_MULTI_ACTION_SYSTEM` flag (default: TRUE)
- `EXTERNAL_EVENTS` - 10 event types with probabilities
- `SCENARIO_PRESETS` - Pre-invasion scenario initial state
- Agent definitions (15 agents across 6 factions)

---

## How It Works (Flow)

### Period N Action Decision Phase:

```
1. PRE-ACTION COORDINATION (unchanged)
   ├─ All faction agents discuss
   ├─ Generate recommendations
   └─ Coordination messages saved

2. DOMAIN EXPERT PROPOSALS (NEW)
   ├─ Single LLM call generates proposals for all domains
   ├─ Each domain proposes 1-3 actions (PRIMARY/SECONDARY/TERTIARY)
   └─ Based on coordination + role + hawk/dove

3. PRESIDENTIAL APPROVAL (NEW)
   ├─ President reviews all proposals
   ├─ Considers strategic coherence, contradictions, resources
   ├─ Approves/vetoes each with rationale
   └─ Strategic choice (escalate/de-escalate/maintain)

4. MULTI-ACTION EXECUTION (NEW)
   ├─ Actions execute sequentially with state threading
   │  ├─ Each execute_action() receives and returns updated state
   │  ├─ Direct mutations (crisis, sanctions, military) preserved
   │  └─ Stateful tracking (peace_talks_count) persists
   ├─ Effect accumulator tracks GDP/territory/costs in parallel
   ├─ After all actions:
   │  ├─ Apply synergy bonuses directly to state
   │  ├─ Apply contradiction penalties directly to state
   │  └─ Apply GDP, territory, costs from accumulator
   └─ Updated state returned

5. SAVE RESULTS
   ├─ Track proposals (what was suggested)
   ├─ Track approvals (what was approved/vetoed)
   └─ Track executions (what actually happened)
```

---

## External Events vs. Agent Actions (State Update Design)

The simulation has **two sources of state change**, both of which now modify state variables.

### Two Sources of Change

**1. External Events** (generated by `event_generator.R`)
- Random events drawn from `EXTERNAL_EVENTS` in `config.R`
- 10 event types: battlefield, commodity_shock, diplomatic, sanctions, military_aid_defender, public_opinion_aggressor, economic_aggressor, defender_strain, allied_support_wavers, economic_defender
- **All events now affect state** with probabilistic effectiveness (v3.8.4)
- Also provide narrative context that agents and forecasters read

**2. Agent Actions** (generated by multi-action/single-action system)
- Deliberate choices made by faction agents through coordination and presidential approval
- Execute through `resolve_multiple_action_effects()` in `multi_action_effects.R`
- Have concrete, mechanical effects on state variables (GDP, military balance, sanctions, etc.)

### External Event Effects (Probabilistic Model)

Each external event has two layers of probability:
1. **Occurrence probability** - Whether the event happens at all (configured in `config.R`)
2. **Effectiveness probability** - Whether the event produces a meaningful state change

This models real-world uncertainty: sanctions might be announced (occurrence) but fail to bite due to enforcement challenges or workarounds (effectiveness).

| Event Type | Effectiveness | State Variables Affected | Rationale |
|---|---|---|---|
| **battlefield** | 85% | `military_balance` (±0.1), `territory_controlled` (±0.02-0.08) | Physical outcomes are concrete |
| **sanctions** | 70% | `sanctions_level` (+0.05-0.10) | Enforcement challenges, workarounds |
| **military_aid_defender** | 75% | `military_balance` (+0.05), `international_support` (+0.05) | Delivery delays, quality variation |
| **allied_support_wavers** | 65% | `international_support` (-0.05) | Domestic politics are unpredictable |
| **defender_strain** | 70% | `crisis_level` (+0.5) | Escalatory pressure |
| **economic_defender** | 70% | `crisis_level` (+0.5) | Economic stress increases tension |
| **diplomatic** | 50% | `crisis_level` (-0.5) | Talks often fail or stall |
| **public_opinion_aggressor** | 55% | `crisis_level` (-0.5) | Domestic pressure is diffuse |
| **economic_aggressor** | 60% | `crisis_level` (-0.3) | Economic pressure on aggressor |
| **commodity_shock** | 60% | `crisis_level` (+0.3) | Market effects are indirect |
| **naval** | 65% | `crisis_level` (+0.3), `military_balance` (±0.02), `sanctions_level` (blockades) | Physical confrontations at sea |
| **air** | 65% | `crisis_level` (+0.3-0.5), `military_balance` (±0.02), `international_support` (no-fly zone) | Airspace violations are concrete |
| **cyber** | 60% | `crisis_level` (+0.2), `military_balance` (±0.03) | Attribution unclear, effects temporary |
| **information** | 50% | `international_support` (±0.05), `crisis_level` (±0.2) | Soft power, hard to quantify |
| **economic** | 65% | `sanctions_level` (±0.05-0.10), `crisis_level` (±0.2-0.3) | Direct economic impacts |

All effects are scaled by a **severity multiplier** (0.5-1.0) drawn per event.

### Dual Nature of External Events

External events have **two effects** that operate simultaneously:

1. **Direct state effect (mechanical):** The event probabilistically nudges a state variable. A sanctions event has a 70% chance of increasing `sanctions_level` by 0.05-0.10. This happens automatically.

2. **Narrative effect (strategic):** The event appears in agent briefings as context. Agents read it, interpret it, and choose actions in response. Those actions produce their own state changes — which may reinforce, offset, or even overshoot the direct effect.

This dual nature means the same event produces **compounding dynamics**. A commodity shock both directly increases crisis (+0.3) AND prompts agents to respond — perhaps with trade agreements that reduce crisis, or with resource hoarding that increases it further. The total impact depends on both the mechanical effect and the strategic response.

### Design Rationale

**Why probabilistic?** External events model environmental shocks that are inherently uncertain. A sanctions announcement doesn't guarantee economic impact (companies find workarounds). A diplomatic overture doesn't guarantee crisis reduction (talks can stall). The probabilistic model captures this uncertainty while still allowing events to meaningfully shape the simulation.

**Why different effectiveness rates?** Physical events (battlefield: 85%) are more deterministic than political ones (diplomatic: 50%). This reflects real-world dynamics where military outcomes are more concrete than diplomatic gestures.

**Why both direct and narrative effects?** In reality, an oil price spike has immediate market consequences (direct effect) AND triggers policy responses (narrative effect). Neither channel alone captures the full picture. The direct effect ensures events have teeth — they move metrics even if agents ignore them. The narrative effect ensures agents can strategically amplify or mitigate the impact.

### Flow Summary

```
External Event (e.g., "Commodity prices surge 18%")
    ├─── DIRECT EFFECT (automatic, probabilistic)
    │    └─ 60% chance: crisis_level += 0.3 * severity
    │
    └─── NARRATIVE EFFECT (agent-mediated)
         ├─ Agents read event as context in briefings
         ├─ Agents choose strategic response (e.g., "negotiate trade agreements")
         └─ Agent actions modify state (may offset or amplify direct effect)

Total state change = direct event effect + agent response effects
```

---

## Forecasting Prompt Generation

Simulation state is converted into human-readable intelligence briefings for forecasters. Two conditions are generated from the same simulation run: TRUE (actual data) and CONTROL (randomized data).

### Pipeline

```
1. Run simulation → outputs/simulation_state.rds
2. Run generate_prompts_v2.R
   ├─ Loads simulation_state.rds
   ├─ TRUE condition:
   │    generate_all_public_forecast_prompts_v2(state, control_condition = FALSE)
   │    └─ For each period: generate_public_forecast_prompt_v2(state, period)
   │       └─ Converts state metrics → natural language text
   │       └─ Formats events and actions as intelligence briefing
   │
   └─ CONTROL condition:
        generate_all_public_forecast_prompts_v2(state, control_condition = TRUE)
        ├─ First: generate_control_condition(state) → randomized state
        └─ Then: generate_public_forecast_prompt_v2(randomized_state, period)
```

### Prompt Structure (Per Period)

Each period's briefing has this temporal structure:

| Section | Time Reference | Source |
|---|---|---|
| **SCENARIO CONTEXT** | Constant | Background description (same every period) |
| **DEVELOPMENTS SINCE LAST PERIOD** | Days (p-2)*7+1 to (p-1)*7 | Delta between period p-2 and p-1 state metrics |
| **CURRENT SITUATION** | Day (p-1)*7 | State at end of previous period (baseline) |
| **CURRENT PERIOD DEVELOPMENTS** | Days (p-1)*7+1 to p*7 | External events + observable actions happening NOW |
| **YOUR FORECAST** | End of Day p*7 | Forecaster predicts outcome at end of this period |

The key temporal logic: **Current Situation** is the baseline (end of last period). **Current Period Developments** shows what's unfolding now. The forecaster predicts the outcome after these developments play out.

### State-to-Text Conversion

Raw simulation metrics are converted to natural language using threshold-based functions:

| Metric | Function | Example Thresholds |
|---|---|---|
| `military_balance` (-1 to +1) | `military_balance_to_text()` | >0.4: "significant defender advantage", -0.1 to 0.2: "roughly evenly matched" |
| `crisis_level` (0-10) | `crisis_level_to_text()` | >9: "maximum intensity - critical", 5-7: "elevated but showing stability" |
| `sanctions_level` (0-1) | `sanctions_to_text()` | >0.7: "comprehensive international sanctions", <0.25: "limited targeted sanctions" |
| `international_support` (0-1) | `support_to_text()` | >0.8: "overwhelming international backing", <0.4: "limited and uncertain support" |
| `territory_controlled` (0-1) | Inline logic | 0: "no territory changed hands", >0.1: "captured notable portion" |

### Actions-to-News Conversion

Agent actions are translated into news-style observable reports via `action_to_news()`. The function maps internal action names to externally observable descriptions:

| Internal Action | News Description |
|---|---|
| `military_buildup` | "deployed additional military forces to the region" |
| `peace_talks` | "initiated diplomatic talks" |
| `sabotage` (detected) | "conducted sabotage operations (later attributed)" |
| `coalition_building` | "engaged in coalition-building efforts" |
| `economic_sanctions` | "imposed economic sanctions" |
| `disinformation` (detected) | "amplified disinformation campaigns (detected by fact-checkers)" |

Covert actions are only shown if detected (based on `result$effects$detected` flag).

### Files

| File | Purpose |
|---|---|
| `generate_prompts_v2.R` | Runner script — loads state, generates TRUE + CONTROL |
| `src/forecast_prompts_public_v2.R` | Core prompt generation — text conversion, template assembly |
| `src/control_condition.R` | Control condition randomization |

### Outputs

```
outputs/human_forecasting/
├── TRUE/
│   ├── instructions.txt          # Study instructions for TRUE condition
│   ├── period_01.txt             # Period 1 briefing
│   ├── period_02.txt             # Period 2 briefing
│   └── ...
├── CONTROL/
│   ├── instructions.txt          # Study instructions for CONTROL condition
│   ├── period_01.txt             # Period 1 briefing (randomized)
│   ├── period_02.txt             # Period 2 briefing (randomized)
│   └── ...
├── forecasting_prompts_TRUE.txt     # All periods combined (TRUE)
└── forecasting_prompts_CONTROL.txt  # All periods combined (CONTROL)
```

---

## Control Condition Design

The control condition tests whether forecasters use genuine information or just pattern-match. It preserves **local plausibility** (each period reads realistically) while disrupting **global patterns** (the information-to-outcome link is broken).

### Three Layers of Randomization

```
TRUE simulation state
    │
    ├─ Layer 1: PERMUTE STATE METRICS
    │    Shuffle metric values across periods with constraints
    │    (e.g., crisis_level from period 3 might appear in period 7)
    │    Max jump constraints prevent nonsensical sequences
    │
    ├─ Layer 2: PERMUTE & FLIP EVENT NARRATIVES
    │    Shuffle events across periods
    │    50% chance per event: swap aggressor ↔ defender
    │    Randomize numeric magnitudes ±30%
    │
    └─ Layer 3: RANDOMIZE INTERMEDIATE PROBABILITIES
         Generate random walk toward same final outcome
         Final period keeps true probability
         Intermediate periods get plausible but randomized values
```

### What Changes vs. What Stays the Same

| Element | TRUE | CONTROL |
|---|---|---|
| **State metrics** (military, crisis, sanctions, support) | Actual simulation values | Permuted across periods |
| **External events** | Actual events in correct period | Shuffled across periods, beneficiaries flipped |
| **Agent actions** | Actual actions in correct period | **SAME** — preserved to maintain local coherence |
| **Final outcome** | True probability | **SAME** — preserved for anchoring |
| **Intermediate probabilities** | True assessment values | Randomized walk toward same endpoint |
| **Scenario context** | Novaris vs Tethys | **SAME** — constant across conditions |

### Why Actions Are Preserved

Actions are NOT randomized because:
1. **Local coherence**: Actions respond to events. Randomizing actions without matching events would create obviously implausible briefings ("Tethys launches peace talks" after winning a battle that never happened in this condition)
2. **The experimental question**: We're testing whether the information-to-outcome link matters, not whether the briefings "look real." The event randomization already breaks the global signal — actions are downstream of events, so the causal chain is disrupted regardless
3. **Association broken**: Even with same actions, the context they respond to (events, metrics) is different. A "military buildup" in response to an aggressor advance means something different than one in response to a diplomatic breakthrough

### Constrained Shuffling

State metrics are shuffled with **maximum jump constraints** to prevent nonsensical sequences:

| Metric | Max Period-to-Period Jump |
|---|---|
| `territory_controlled` | ±0.15 (15%) |
| `crisis_level` | ±3.0 (on 0-10 scale) |
| `sanctions_level` | ±0.20 (20%) |
| `military_balance` | ±0.30 |

The algorithm iteratively swaps elements to satisfy constraints (up to 100 iterations).

### Event Flipping

When an event's beneficiary is flipped, actor names are swapped:
- "Novaris" ↔ "Tethys"
- "major power" ↔ "smaller power"
- "aggressor" ↔ "defender"
- "offensive" ↔ "defensive"

Numeric values in descriptions are randomized ±30% (e.g., "18% surge" might become "14% surge" or "23% surge").

### Implementation

**File:** `src/control_condition.R`

| Function | Purpose |
|---|---|
| `generate_control_condition()` | Main entry — applies all 3 layers |
| `permute_state_metrics()` | Layer 1 — constrained metric shuffling |
| `constrained_shuffle()` | Helper — iterative swap with max jump constraint |
| `permute_event_narratives()` | Layer 2 — shuffle, flip, randomize events |
| `flip_event_beneficiary()` | Helper — swap aggressor/defender in event |
| `swap_actors()` | Helper — text replacement of actor names |
| `randomize_event_magnitude()` | Helper — ±30% on numbers in descriptions |
| `randomize_intermediate_probabilities()` | Layer 3 — random walk for assessments |

---

## Example Execution

### Period 1: Tethys (Defender)

**COORDINATION OUTPUT:**
- General Bondar (88% hawk): Recommends sabotage
- Intel Director Savchenko (72% hawk): Recommends sabotage
- President Marchetti (62% hawk, liberal institutionalist): Recommends military_buildup
- Diplomat Kovalenko (32% hawk): Recommends peace_talks
- Economic Minister Moroz (28% hawk): Recommends financial_aid

**DOMAIN PROPOSALS:**
```
MILITARY (General Bondar):
  PRIMARY: defensive_fortification - "Harden key positions against invasion"
  SECONDARY: military_buildup - "Increase readiness 60% → 80%"

INTELLIGENCE (Director Savchenko):
  PRIMARY: sabotage - "Strike mobilization centers while they're at 40%"
  SECONDARY: intelligence_gathering - "Map Novaris command structure"

DIPLOMATIC (Minister Kovalenko):
  PRIMARY: peace_talks - "Direct negotiations with Novaris"
  SECONDARY: coalition_building - "Shore up Meridian commitment"

ECONOMIC (Minister Moroz):
  PRIMARY: resource_embargo - "Shut down pipeline (30% of their revenue)"
```

**PRESIDENTIAL APPROVAL (President Marchetti):**
```
MILITARY:
  PRIMARY (defensive_fortification): APPROVE - "Essential defensive prep"
  SECONDARY (military_buildup): APPROVE - "We can afford both, build deterrence"

INTELLIGENCE:
  PRIMARY (sabotage): VETO - "Too escalatory while pursuing peace talks"
  SECONDARY (intelligence_gathering): APPROVE - "Useful intel, low risk"

DIPLOMATIC:
  PRIMARY (peace_talks): APPROVE - "Core strategy, aligned with values"
  SECONDARY (coalition_building): APPROVE - "Reinforces negotiating position"

ECONOMIC:
  PRIMARY (resource_embargo): VETO - "Nuclear option, save for later"
```

**APPROVED ACTIONS (5 total):**
1. defensive_fortification (Military primary)
2. military_buildup (Military secondary)
3. intelligence_gathering (Intel secondary)
4. peace_talks (Diplomatic primary)
5. coalition_building (Diplomatic secondary)

**EFFECT RESOLUTION:**
```
CUMULATIVE EFFECTS:
- defensive_fortification: +5% defense
- military_buildup: +5% military × 0.6 (diminishing returns) = +3% military
- intelligence_gathering: +info, no immediate effect
- peace_talks: -1.5 crisis
- coalition_building: -0.5 crisis × 0.6 (diminishing) = -0.3 crisis

SYNERGIES DETECTED:
- military_buildup + defensive_fortification = deterrence bonus (-0.5 crisis)
- peace_talks + coalition_building = negotiating strength (+0.2 success chance, -0.3 crisis)

TOTAL EFFECTS:
- Defense: +8%
- Crisis: -2.5 (base -1.8 + synergy -0.7)
- International support: +10%
- Cost: $9.2B
```

**RESULT:** Coherent defensive + diplomatic strategy, 5 actions executed successfully

---

## Configuration

### Enable/Disable

In `config.R`:
```r
ENABLE_MULTI_ACTION_SYSTEM <- TRUE   # Enable multi-action
ENABLE_MULTI_ACTION_SYSTEM <- FALSE  # Fallback to single-action
```

### Which Factions Use It?

**Multi-action system:**
- `major_power` (Novaris) - if 3+ agents with domain roles
- `small_power` (Tethys) - if 3+ agents with domain roles

**Single-action system:**
- External actors: `meridian`, `valkoria`, `aurelia`, `international_org`
- Any faction with <3 agents or no domain structure

### Automatic Fallback

If faction doesn't have sufficient domain experts, automatically falls back to traditional single-action system.

---

## Expected Impact on Action Diversity

### Before (Single-Action):
- 1 action per faction per period
- 6 factions × 3 periods = 18 total actions
- V3.7 result: 8 unique actions (2.67/period)

### After (Multi-Action):
- Major power: ~4-5 actions/period (domain proposals)
- Small power: ~4-5 actions/period (domain proposals)
- External actors: 1 action/period each (4 actors)
- Total: ~12-14 actions/period
- 3 periods × 12-14 actions = **36-42 total actions**
- **Expected unique: 15-20** (hitting target!)

### Projected 10-Period Run:
- ~12-14 actions/period × 10 periods = **120-140 total actions**
- **Expected unique: 30-40** (well above target!)

---

## Testing Plan

### Phase 1: Quick Test (3 periods)
- Verify system works correctly
- Check proposal generation quality
- Verify approval logic
- Confirm effect resolution
- Measure action diversity improvement

### Phase 2: Full Test (10 periods)
- Validate long-term diversity
- Check for action saturation (do we run out of new actions?)
- Verify escalation dynamics work
- Compare to all previous baselines

### Phase 3: Refinement
- Tune diminishing returns factors
- Adjust contradiction detection
- Refine synergy bonuses
- Optimize resource constraints

---

## Discussion Memory (v3.8.2)

**Added:** 2026-02-02

Agents now have access to previous period discussions, providing conversational continuity.

### How It Works

1. **2-Period Lookback:** Agents see discussions from the previous 2 periods
2. **Relevance Filtering:** Only discussions where the agent participated or involved their faction
3. **Message Selection:** First 3 + last 2 messages (if >5 total) to capture context without bloat
4. **Smart Summarization:** Messages >150 characters are summarized using LLM (google/gemini-2.5-flash)
5. **Self-Recognition:** Agent's own statements highlighted with "→ YOU said:"

### Example Prompt Section

```
=== PREVIOUS DISCUSSIONS (what colleagues said) ===

PERIOD 2 DISCUSSIONS:

  Topic: Intra-faction coordination
    → YOU said: We should prioritize defensive measures while pursuing diplomatic channels...
    - General Bondar: Military readiness remains critical given their troop movements.
    - Director Savchenko: Intel confirms mobilization accelerating on eastern border.
```

### Implementation Details

**New functions in `src/agent_decision.R`:**
- `summarize_message()` - LLM-powered summarization for long messages (>150 chars)
- `format_previous_discussions()` - Formats discussion history for agent prompts

**Updated functions in `src/multi_action_system.R`:**
- `generate_domain_proposals()` - Now accepts `state` parameter for discussion history
- `build_proposal_prompt()` - Includes previous period discussions in domain expert prompts
- `presidential_approval()` - Now accepts `state` parameter for discussion history
- `build_approval_prompt()` - Includes previous period discussions in presidential decision prompts

**Key Design Decisions:**
- **Raw data preserved:** Original messages in `state$interactions_history` are never modified
- **Display-only summarization:** Summarization only affects prompt generation, not stored data
- **Graceful fallback:** If LLM summarization fails, falls back to simple truncation
- **Affordable model:** Uses google/gemini-2.5-flash for cost efficiency
- **Full integration:** Works with both single-action (external actors) and multi-action (main factions) systems

### Benefits

- Agents can reference what they and colleagues previously said
- Creates continuity between periods (no "amnesia")
- Reduces token usage via smart summarization
- Maintains full raw data for analysis
- Works for ALL faction types (major power, small power, and external actors)

---

## Bug Fixes (v3.8.2 / v3.8.3)

### Summary Display Fix
- **Issue:** Summary .txt file showed all multi-actions as "failed" even when individual actions succeeded
- **Cause:** Multi-action `result$success` was only TRUE if ALL actions succeeded
- **Fix:** Updated `run_simulation_with_actions.R` to iterate through `individual_results` for multi-action factions
- **Result:** Summary now correctly shows each action's individual success/failure status

### Post-Action Discussions CSV Fix
- **Issue:** Post-action discussions were saved to memory but not to CSV files
- **Cause:** `save_interactions_to_csv()` was not being called after post-action discussions
- **Fix:** Added `save_interactions_to_csv(interaction_session)` call in `simulation_with_actions.R`
- **Result:** Post-action discussions now saved to:
  - `outputs/interactions/period_XX_interactions_summary.csv` - interaction metadata
  - `outputs/interactions/period_XX_interactions_messages.csv` - full message content

### Effect Accumulator Fix (v3.8.4)
- **Issue:** `accumulate_effects()` in `multi_action_effects.R` only summed `crisis_change`, `military_balance_change`, and `cost` — silently dropping `sanctions_change`, `international_support_change`, `gdp_change`, and `territory_change`
- **Cause:** Original implementation only had 3 fields; new fields were added to effect resolution but never added to the accumulator
- **Fix:** `accumulate_effects()` now sums all 6 effect dimensions. `scale_effects()` also updated to scale all 6 dimensions.
- **Impact:** Multi-action factions (Novaris/Tethys) now correctly accumulate sanctions, territory, international support, and GDP changes from their approved actions

### State Application Fix (v3.8.4)
- **Issue:** `apply_effects_to_state()` in `multi_action_effects.R` only applied `crisis_change` and `military_balance_change` to the simulation state
- **Cause:** Function was not updated when new effect dimensions were added
- **Fix:** Now applies all dimensions: `sanctions_change`, `international_support_change`, `territory_change`, with correct clamps (0-1 for all, 0-10 for crisis, -1 to +1 for military_balance)
- **Impact:** Agent actions now actually modify sanctions, territory, and international support as intended

### International Support Clamp Fix (v3.8.4)
- **Issue:** `international_support` was clamped with `min(100, ...)` but the variable range is 0-1
- **Fix:** Changed to `min(1, ...)`

### Sanctions Double-Counting Fix (v3.8.4)
- **Issue:** `economic_sanctions` action was modifying `sanctions_level` in TWO places: (1) direct mutation in `execute_action()`, and (2) via the effect accumulator/applicator, AND (3) the simulation loop re-applied `sanctions_severity` from action results
- **Cause:** Three independent code paths for sanctions were added at different times
- **Fix:** Removed the simulation loop re-application (lines 310-314 in `simulation_with_actions.R`). Sanctions now flow through: execute_action() direct mutation + accumulator path only.
- **Impact:** Sanctions no longer triple-counted per action

### External Events State Changes (v3.8.4)
- **Issue:** Only battlefield events modified simulation state. All other 9 event types (sanctions, diplomatic, economic, etc.) were narrative-only — they appeared in briefings but never changed metrics
- **Cause:** `update_scenario_state()` in `state_manager.R` had comprehensive event processing but was **dead code** — never called from `simulation_with_actions.R`. The inline event processing only handled battlefield.
- **Fix:** Wired all 10 event types to state changes in `simulation_with_actions.R` with probabilistic effectiveness (50-85% depending on event type) and severity scaling (0.5-1.0)
- **Impact:** Simulation metrics now respond to the full range of external events, producing more dynamic and realistic state evolution

### Territory Update Fix (v3.8.4)
- **Issue:** `territory_controlled` never changed from its initial value (0.0 in pre-invasion scenario)
- **Cause:** Battlefield events only updated `military_balance`, not `territory_controlled`. The dead `update_scenario_state()` had territory logic but was never called.
- **Fix:** Battlefield events now update `territory_controlled` alongside `military_balance`. Defender success reduces territory (recapture), aggressor success increases it (advance).
- **Impact:** Territory can now organically evolve from pre-invasion (0.0) through conflict phases

### Multi-Domain Event Handlers (v3.8.4 - Round 2)
- **Issue:** 5 event types generated by `event_generator.R` had NO state handlers in `simulation_with_actions.R`: `naval`, `air`, `cyber`, `information`, and `economic` (from `generate_economic_event()`)
- **Cause:** Multi-domain events (naval/air/cyber/information) were added to `event_generator.R` but handlers were never added to the simulation loop. `generate_economic_event()` produces `type = "economic"` events, which had no handler (the existing handlers were for `economic_aggressor` and `economic_defender` from config.R EXTERNAL_EVENTS).
- **Fix:** Added handlers for all 5 types with probabilistic effectiveness and impact_type-aware direction:
  - **Naval** (65%): crisis + military_balance shifts based on who benefits; blockades increase sanctions
  - **Air** (65%): crisis + military_balance; shootdowns more escalatory; no-fly zone proposals de-escalatory
  - **Cyber** (60%): crisis + military_balance based on attack target (defender vs major); defense upgrades benefit defender
  - **Information** (50%): international_support shifts based on narrative winners; disinformation/leaks increase crisis
  - **Economic** (65%): sanctions_level changes for sanctions events; crisis for commodity shocks; crisis reduction for aggressor GDP decline
- **Impact:** ~25-30% of generated events per period that were previously ignored now produce state changes

### GDP Effect Application Fix (v3.8.4 - Round 2)
- **Issue:** Multi-action factions' GDP effects were completely lost. `gdp_change` was accumulated and scaled in the effects system but never applied.
- **Cause:** GDP lives in `state$faction_capabilities` (not `state$scenario_state`), so `apply_effects_to_state()` couldn't apply it. The simulation loop (lines 399-476) also skips multi-action results because `result$effects` is NULL for multi-action factions (they have `individual_results` instead).
- **Fix:** Added GDP application to `apply_effects_to_state()` using `agent$faction` to determine which faction's GDP to modify:
  - `gdp_change` (target damage) applied to opponent's GDP as a multiplier
  - `total_cost` (action costs) deducted from own GDP
  - Floor values prevent GDP from going below realistic minimums (10B major, 5B small)
- **Impact:** Multi-action factions now properly pay for their actions and damage opponent's economy

### Period 2 Baseline Fix (v3.8.4 - Round 2)
- **Issue:** Forecast prompt's Period 2 "changes since last period" compared against hardcoded baseline values (military_balance=0.5, crisis_level=10, sanctions_level=0.45, international_support=0.75) that didn't match the pre_invasion scenario preset
- **Cause:** Original baseline was never updated when scenario changed to pre_invasion
- **Fix:** Updated to match pre_invasion config values (military_balance=-0.15, crisis_level=5, sanctions_level=0.2, international_support=0.5)
- **Impact:** Period 2 change descriptions now accurately reflect evolution from actual starting state

### Multi-Action State Threading Fix (v3.8.4 - Round 3)
- **Issue:** `resolve_multiple_action_effects()` discarded the state returned by `execute_action()` (R copy-on-modify). Many actions in `action_execution.R` rely on direct state mutations (e.g., `state$scenario_state$crisis_level <- ... + 2`) rather than setting `result$effects$crisis_change`. For multi-action factions (Novaris/Tethys), ~30 crisis_level mutations, sanctions mutations, and military_balance mutations were silently lost.
- **Cause:** Multi-action system was added later with an accumulator pattern, but `execute_action()` was designed for single-action (direct mutation + return state). The accumulator could only capture effects explicitly set in `result$effects`.
- **Fix:** State is now threaded through sequential `execute_action()` calls (`state <- execution_result$state`). Direct mutations persist. The accumulator is still used for: GDP effects (in `faction_capabilities`), territory, action costs, synergy detection, and reporting. Synergies and contradiction penalties are applied directly to state.
- **Impact:** Multi-action factions now receive the full effect of every action, identical to single-action factions. Also fixes peace_talks diminishing returns (state$peace_talks_count now persists across sequential actions).

---

## Known Limitations

1. **More LLM calls:** 2 calls per major faction (proposals + approvals) vs 1 before
   - Mitigation: External actors still 1 call, overall improvement worth cost

2. **Complexity:** More complex effect resolution
   - Mitigation: Well-tested effect resolution system with clear logic

3. **Action spam risk:** Could approve 10+ actions if President approves everything
   - Mitigation: Resource constraints, presidential judgment, diminishing returns

4. **CSV tracking:** Multiple actions per faction per period (CSV format update needed)
   - Mitigation: Can store as JSON or multiple rows per faction

---

## Next Steps

1. ✅ **Implement core system** (COMPLETE)
2. ✅ **Test 3-period run** (COMPLETE - system verified working)
3. ✅ **Analyze results** (COMPLETE - compared to v3.7 baseline)
4. ✅ **Run 10-period test** (COMPLETE - 2026-02-02)
5. ⏳ **Refine based on results** (tune parameters as needed)

---

## Test Results (10-Period Run - 2026-02-02)

**Simulation Summary:**
- **Runtime:** 88.3 minutes
- **Final Crisis Level:** 10/10
- **Final Collapse Probability:** 42% (DECREASING trend)
- **Military Balance:** 0.48 (favoring defender)

**Action Diversity Achieved:**
- 20+ unique action types used across 10 periods
- Major/small powers executed 6-9 actions per period each
- Presidential approval/veto system creating strategic coherence
- Discussion memory providing conversational continuity

**Verified Working:**
- ✅ Multi-action proposal system
- ✅ Presidential approval/veto with counter-proposals
- ✅ Discussion memory (2-period lookback with LLM summarization)
- ✅ Summary display (individual action success/failure)

---

**Status:** PRODUCTION READY

**Files to check after run:**
- `outputs/interactions/period_XX_coordination.csv` - Pre-action coordination debates
- `outputs/interactions/period_XX_proposals.csv` - Domain expert proposals
- `outputs/interactions/period_XX_actions.csv` - Action decisions and results
- `outputs/interactions/period_XX_interactions_summary.csv` - Post-action discussion metadata
- `outputs/interactions/period_XX_interactions_messages.csv` - Post-action discussion content
- `outputs/simulation_summary_*.txt` - Overall results
- Console output - Proposals, approvals, effect resolution

---

**v3.9.0 verified and production ready!**

**v3.9.0 Changes (2026-02-14):**

*Parameter sensitivity:*
- `format_situation_for_agent()` now shows exact numeric values alongside worldview-filtered descriptions
- Military balance, sanctions, territory, crisis level all include `[exact: value]` tags
- `international_support` parameter added (was completely invisible to agents)
- `build_proposal_prompt()` now includes all 5 scenario parameters with exact values in `CURRENT SCENARIO PARAMETERS` block
- `build_approval_prompt()` also includes full parameter block in leader profile
- Prompts now instruct agents to "calibrate proposals to EXACT scenario parameters"
- Test results: Novaris action overlap dropped to 33% across contrasting scenarios (was near-100%)

**v3.8.5 Changes (2026-02-08):**

*Simulation state fixes:*
- All 15 external event types now affect simulation state (probabilistic effectiveness model)
- Effect accumulator fixed to sum all 6 dimensions (was dropping 4)
- State applicator fixed to apply all dimensions (sanctions, territory, international support, GDP)
- GDP effects now properly applied for multi-action factions (target damage + action costs)
- Sanctions double-counting eliminated
- Territory now evolves organically from pre-invasion starting point
- International support clamp fixed (was 0-100, now correctly 0-1)
- Multi-domain events (naval, air, cyber, information, economic) now wired to state changes

*Multi-action state threading:*
- execute_action() state now threaded through sequential calls (was discarded via R copy-on-modify)
- ~30 direct crisis/sanctions/military mutations no longer lost for Novaris/Tethys
- Peace talks diminishing returns now work for multi-action factions
- Synergy bonuses and contradiction penalties applied directly to state

*Prompt generation:*
- Period 2 forecast baseline corrected to match pre_invasion scenario preset
- Added full documentation of prompt generation pipeline and control condition design
