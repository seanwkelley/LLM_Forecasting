# LLM Forecasting Project - Context for Claude

**Version:** 3.9.0 Multi-Action System with Parameter Sensitivity & Backstory Reframing
**Last Updated:** February 14, 2026
**Status:** Production Ready - Parameter Sensitivity Fixed

---

## Project Overview

This is a **geopolitical conflict simulation** using LLM agents to model crisis escalation and forecast government collapse probability. The simulation features a sophisticated multi-action decision-making system where domain experts propose actions and government leaders approve/veto them.

### Core Concept
- **11 LLM agents** with distinct personas, worldviews, and cognitive traits
- Agents engage in **multi-action decision making** (3-6 concurrent actions per faction per period)
- **Domain experts** (Military, Intelligence, Diplomatic, Economic) propose 1-3 actions each
- **President/Government leader** reviews and approves/vetoes proposals based on strategic judgment
- Actions have **real consequences** that update simulation state
- **Effect resolution** handles cumulative effects, diminishing returns, contradictions, and synergies
- A separate **aggregator LLM** forecasts probability of government collapse

### Research Question
**What is the probability that Tethys's (smaller power) government will be toppled?**

---

## Latest Improvements: v3.8.2 - v3.9.0 (February 2026)

### v3.9.0 - Parameter Sensitivity & Backstory Reframing

**Problem 1 (R simulation):** Agents were insensitive to scenario parameters. `format_situation_for_agent()` converted numeric parameters to categories, hiding fine-grained differences. `international_support` was completely invisible. Proposal/approval prompts only received crisis_level + 200 chars.

**Solution:** Added exact numeric values (`[exact: +0.05]`) alongside worldview-filtered descriptions in `format_situation_for_agent()`. Added `international_support`. Passed all 5 parameters to `build_proposal_prompt()` and `build_approval_prompt()`.

**Result:** Novaris action overlap between low and high threat scenarios dropped to 33% (was near-100%). Collapse probability range 0.385–0.635 across contrasting scenarios.

**Problem 2 (Python forecasting):** Systematic downward bias in collapse probability forecasting (ensemble mean ~0.35 vs truth ~0.58) due to shared Tethys-resilient backstory anchoring.

**Solution:** Added 5 backstory variants (aggressor, vulnerability, escalation, domestic, inertia) — same facts, different editorial framing. "Reframe" condition cycles agents through all 6 variants.

**Result:** MSE reduced from 0.055–0.057 (baseline) to 0.021–0.023 (reframe), a 58–61% improvement.

**Files Modified:**
- `src/agent_decision.R` — `format_situation_for_agent()` (exact numeric values, international_support)
- `src/multi_action_system.R` — `build_proposal_prompt()`, `build_approval_prompt()` (full parameter blocks)
- `forecasting/run_multiscenario_experiment.py` — 5 backstory variants, reframe condition, agent-level logging

### v3.8.5 - State Threading for Multi-Action Factions (CRITICAL FIX)

**Problem:** Multi-action factions (Novaris, Tethys) were losing ~30 direct state mutations from `execute_action()` due to R's copy-on-modify semantics. The returned state was discarded; only `result$effects` were captured (and many actions don't set these).

**Solution:** State threading - state is now passed through sequential `execute_action()` calls:
```r
# In resolve_multiple_action_effects():
execution_result <- execute_action(action_name, agent, target_agent, state)
result <- execution_result$result
state <- execution_result$state  # Thread state: preserves direct mutations
```

**Key architectural change:**
- Actions now execute **sequentially** (not in parallel) to preserve state
- Direct mutations preserved via state threading
- Accumulator still used for GDP/territory/costs, synergy detection, reporting
- Synergies and contradiction penalties applied directly to threaded state
- `apply_effects_to_state()` no longer called from main multi-action path
- Peace talks diminishing returns (`peace_talks_count`) now works correctly

### v3.8.4 - Probabilistic External Events & State Handlers

**Problem:** 5 event types (naval, air, cyber, information, economic) were generated but had no state handlers - producing zero state changes.

**Solution:** Added handlers for all 15 event types with probabilistic effectiveness:

| Event Type | Effectiveness | Primary Effects |
|------------|--------------|-----------------|
| Military escalation | 75% | crisis +0.5-1.5, military_balance |
| Military de-escalation | 70% | crisis -0.3-1.0 |
| Diplomatic progress | 70% | crisis -0.5-2.0, int'l support |
| Diplomatic breakdown | 75% | crisis +0.5-2.0 |
| Sanctions imposed | 80% | sanctions +0.05-0.15 |
| Sanctions eased | 75% | sanctions -0.05-0.10 |
| Humanitarian crisis | 85% | crisis +0.5-1.0, int'l support |
| Wild card | 60% | crisis +1.0-3.0, various |
| Naval incident | 65% | crisis, military_balance |
| Air incident | 65% | crisis, military_balance |
| Cyber incident | 60% | crisis, military_balance |
| Information warfare | 50% | int'l support, crisis |
| Economic event | 65% | sanctions, crisis |

**Additional fixes:**
- GDP effects now applied in multi-action path (was silently lost)
- Period 2 hardcoded baseline corrected to match pre_invasion preset
- Sanctions double-counting eliminated
- International support properly clamped to [0, 1]

### v3.8.3 - Discussion Memory & CSV Fixes

- Agents now receive discussion transcripts as context for proposals
- Fixed CSV export issues for multi-action results

### v3.8.2 - Temporal Prompt Structure

- Fixed prompt temporal ordering: Current Situation (end of previous period) -> Current Period Developments -> Forecast
- External events now have both mechanical state effects AND narrative effects (agents read and respond strategically)

### v3.8.1 - XML-Tagged Prompts

- XML semantic tags for structured prompts: 100% parsing success rate
- Mixed LLM strategy: Qwen (proposals), DeepSeek (approval), Gemini (aggregation)
- Multi-domain warfare events: Naval, Cyber, Air, Information
- Enhanced action diversity: naval_deployment, cyber_attack, coalition_building, etc.

---

## Current Version: v3.8 Multi-Action System

### Key Innovation
Replaced single-action decision-making with realistic multi-track governance:

**Old System (v3.7):**
- 1 action per faction per period
- Decision maker chooses single best action
- 6 total actions per period (6 factions)
- Result: Low action diversity (8 unique actions in 3 periods)

**New System (v3.8):**
- **Domain experts propose** 1-3 actions in their area
- **President approves/vetoes** each proposal
- **3-6 concurrent actions** per major faction per period
- **Effect resolution** with cumulative, contradictory, synergistic logic
- Target: 15-20 unique actions in 3 periods

### How Multi-Action Works

1. **Pre-action Coordination** - All faction agents discuss strategy
2. **Domain Expert Proposals:**
   - Military → proposes military/defense actions (PRIMARY/SECONDARY/TERTIARY)
   - Intelligence → proposes intel/covert actions
   - Diplomatic → proposes diplomatic actions
   - Economic → proposes economic actions
3. **Presidential Approval:**
   - Reviews all proposals holistically
   - Approves/vetoes based on strategic judgment (NOT crisis-reactive)
   - Considers contradictions, resources, coherence
4. **Multi-Action Execution:**
   - Approved actions execute **sequentially** with state threading (preserves direct mutations)
   - Effect resolution handles:
     - **Cumulative effects** (additive across domains)
     - **Diminishing returns** (2nd military action 60% as effective)
     - **Contradictions** (peace talks + sabotage = diplomatic crisis)
     - **Synergies** (intel gathering + sabotage = +20% effectiveness)
     - **Resource constraints** (total cost < 10-15% GDP)

---

## Architecture

### File Structure

```
LLM_Forecasting/
├── config.R                          # Configuration, agent definitions, event probabilities
├── run_simulation_with_actions.R     # Main simulation entry point
├── generate_prompts_v2.R            # Generates TRUE + CONTROL forecasting prompts
│
├── src/
│   ├── multi_action_system.R         # v3.8: Domain proposal & presidential approval
│   ├── multi_action_effects.R        # v3.8.5: Effect resolution with state threading
│   ├── agent_decision.R              # Decision routing (multi-action vs single-action)
│   ├── action_execution.R            # Execute actions, direct state mutations (~30)
│   ├── simulation_with_actions.R     # Main simulation loop, external event handlers
│   ├── event_generator.R             # External event generation (15 types)
│   ├── forecast_prompts_public_v2.R  # Prompt construction (state→text, actions→news)
│   ├── control_condition.R           # 3-layer randomization for CONTROL prompts
│   ├── interaction_engine.R          # Agent communication, CSV export
│   ├── agent_system.R                # Agent creation, LLM calls
│   ├── state_manager.R               # State tracking and logging
│   ├── aggregator.R                  # Probability assessment
│   └── ... (other support files)
│
└── docs/guides/
    ├── MULTI_ACTION_SYSTEM_GUIDE.md  # Complete v3.8.5 documentation
    ├── FACTION_OBJECTIVES.md         # Faction capabilities and goals
    └── CLAUDE.md                     # This file
```

### Key Functions

**Multi-Action System (`src/multi_action_system.R`):**
- `generate_domain_proposals()` - Single LLM call generates all domain proposals
- `presidential_approval()` - President reviews and approves/vetoes
- `extract_approved_actions()` - Returns list of approved actions

**Effect Resolution (`src/multi_action_effects.R`):**
- `resolve_multiple_action_effects()` - Main effect resolution with state threading
- `detect_contradictions()` - Finds incompatible actions
- `detect_synergies()` - Finds complementary actions
- `apply_effects_to_state()` - Utility function (no longer called from main path)

**Prompt Generation (`src/forecast_prompts_public_v2.R`):**
- `generate_period_prompt()` - Builds prompt for one period
- `format_state_as_situation()` - Converts scenario_state to narrative text
- `format_actions_as_news()` - Converts agent actions to news-style reports
- `format_events_as_developments()` - Converts external events to narrative

**Control Condition (`src/control_condition.R`):**
- `permute_state_metrics()` - Constrained shuffle of metric values across periods
- `permute_event_narratives()` - Flips event beneficiaries (Novaris <-> Tethys)
- `randomize_intermediate_probabilities()` - Adds noise to probability anchors

**Simulation Loop (`src/simulation_with_actions.R`):**
- `apply_external_events()` - Handles all 15 event types with probabilistic effectiveness
- Single-action path: direct state mutation from `execute_action()`
- Multi-action path: delegates to `resolve_multiple_action_effects()`

**Decision Making (`src/agent_decision.R`):**
- Checks if `ENABLE_MULTI_ACTION_SYSTEM` is TRUE
- Major/small powers use multi-action system
- External actors use traditional single-action system
- Integration at lines 1239-1288

**CSV Export (`src/interaction_engine.R`):**
- `save_actions_to_csv()` - Saves actions to CSV (lines 1284-1339)
- Detects multi-action results (has `approved_actions` list)
- Creates one row per approved action

---

## Agents

### Novaris (Major Power - Aggressor)
- **Minister Dmitri Volkov** (government) - 68% hawk, realist
- **General Viktor Krasnov** (military) - 92% hawk, nationalist
- **Director Sergei Morozov** (intelligence) - 58% hawk, realist
- **Dr. Natasha Petrova** (economic) - 25% hawk, pragmatic technocrat
- **Deputy Minister Yuri Volkov** (political) - 95% hawk, pragmatic technocrat

### Tethys (Small Power - Defender)
- **President Elena Marchetti** (government) - 62% hawk, liberal institutionalist
- **General Olena Bondar** (military) - 88% hawk, nationalist
- **Director Maksym Savchenko** (intelligence) - 72% hawk, pragmatic technocrat
- **Minister Sofia Kovalenko** (diplomatic) - 32% hawk, liberal institutionalist
- **Minister Taras Moroz** (economic) - 28% hawk, pragmatic technocrat
- **Viktor Zelenko** (political) - 45% hawk, constructivist

### External Actors (Single-Action)
- **Ambassador William Crawford** (meridian) - Supports Tethys
- **Minister Andrei Kozlov** (valkoria) - Supports Novaris
- **Commissioner Helena Schmidt** (aurelia) - Neutral mediator
- **Under-Secretary-General Isabella Cardenas** (international_org) - Humanitarian focus

---

## Scenario: Multi-Domain Escalation Crisis

**Setup:**
- Novaris (major power) has mobilized 40% of forces on border
- Tethys (small power) has defensive and offensive capabilities
- Crisis across multiple domains: military, cyber, economic, covert
- **NO shots fired yet** - conflict is emergent
- Both sides can escalate OR de-escalate

**Key Features:**
- **Balanced scenario** - Both powers have offensive/defensive options
- Novaris has vulnerabilities (30% revenue via Tethys pipelines, cyber exposed)
- Tethys has offensive tools (precision strikes, cyber units, economic leverage)
- Pre-invasion setting - invasion possible but NOT inevitable

---

## Common Tasks for Claude

### 1. Understanding Current State
**Read these files:**
- `docs/guides/MULTI_ACTION_SYSTEM_GUIDE.md` - v3.8 system overview
- `PROJECT_STATUS.md` - Current implementation status
- `config.R` - Configuration and settings

### 2. Debugging Issues
**Key files to check:**
- `src/multi_action_system.R` - Proposal/approval logic
- `src/multi_action_effects.R` - Effect resolution
- `src/agent_decision.R` - Integration (lines 1239-1288)
- `src/interaction_engine.R` - CSV export (lines 1284-1339)

### 3. Analyzing Results
**Output files:**
- `outputs/interactions/period_XX_actions.csv` - Action decisions
- `outputs/interactions/period_XX_coordination.csv` - Pre-action discussions
- `outputs/assessment_period_XX.txt` - Probability assessments
- `outputs/assessments.csv` - Probability timeline

### 4. Measuring Action Diversity
```bash
# Count unique actions across all periods
cat outputs/interactions/period_*_actions.csv | cut -d',' -f6 | sort -u | wc -l

# Expected: 15-20 unique actions (v3.8 target)
# Baseline: 8 unique actions (v3.7)
```

### 5. Modifying Configuration
**In `config.R`:**
```r
N_PERIODS <- 3                        # Number of periods to simulate
ENABLE_MULTI_ACTION_SYSTEM <- TRUE    # Use multi-action system
SCENARIO_PRESET <- "pre_invasion"     # Scenario type
```

---

## Critical Implementation Details

### Multi-Action CSV Export (Fixed)

**Problem:** Multi-action factions showed NA values in CSV
**Cause:** Export code expected single action, multi-action stores list
**Solution:** Modified `save_actions_to_csv()` in `interaction_engine.R`:

```r
# Detect multi-action results
if (!is.null(dec$approved_actions) && length(dec$approved_actions) > 0) {
  # Create one row per approved action
  for (i in seq_along(dec$approved_actions)) {
    # Extract action details and create CSV row
  }
}
```

### Presidential Agency

**Key Design:** President has strategic agency, NOT crisis-reactive

```r
# President can CHOOSE to escalate or de-escalate
# based on worldview, not mechanical crisis response

# Liberal institutionalist might de-escalate even in high crisis
# Nationalist might escalate even in low crisis
# Realist makes calculated strategic choices
```

### Effect Resolution Logic

**Cumulative:**
```r
# Actions in different domains stack additively
military_buildup (+5%) + peace_talks (-1.5 crisis) → both apply
```

**Diminishing Returns:**
```r
# 2nd action in same category: effectiveness × 0.6
military_buildup (+5%) + defensive_fortification (+3%)
→ +5% + (+3% × 0.6) = +8% total
```

**Contradictions:**
```r
# peace_talks + sabotage (if detected 30% chance)
→ +3.0 crisis, -15 international support
→ peace talks fail
```

**Synergies:**
```r
# intelligence_gathering + sabotage → +20% sabotage effectiveness
# military_buildup + defensive_fortification → -0.5 crisis (deterrence)
# peace_talks + coalition_building → -0.3 crisis, +0.2 success
```

---

## Forecasting Prompt Generation Pipeline

### Overview
After simulation completes, `generate_prompts_v2.R` generates two sets of forecasting prompts:
1. **TRUE condition** - Real simulation data, preserving causal relationships
2. **CONTROL condition** - 3-layer randomization breaks info->outcome connection

### Pipeline Flow
```
simulation_state.rds
  → generate_prompts_v2.R (entry point)
    → forecast_prompts_public_v2.R (prompt construction)
      → format_state_as_situation()     # State → narrative text
      → format_actions_as_news()        # Actions → news reports
      → format_events_as_developments() # Events → narrative
    → control_condition.R (CONTROL only)
      → permute_state_metrics()         # Constrained shuffle
      → permute_event_narratives()      # Flip beneficiaries
      → randomize_intermediate_probabilities()  # Add noise
```

### Temporal Structure
Each period prompt follows: **Current Situation** (end of previous period) -> **Current Period Developments** (events/actions happening now) -> **Forecast question**

### Control Condition Design (3 Layers)
1. **Metric permutation** - Constrained shuffle of state metrics across periods (max jump limits per metric)
2. **Event narrative flipping** - Swaps Novaris <-> Tethys, aggressor <-> defender in event descriptions
3. **Probability randomization** - Adds noise to intermediate probability anchors

**What stays the same:** Agent actions (preserved to maintain local coherence), overall narrative structure, prompt format.
**What changes:** State metric values, event beneficiaries, probability anchors - breaks the information -> outcome causal chain.

---

## Known Issues & Solutions

### Issue: DeepSeek parsing failures (~50% failure rate)
**Cause:** Inconsistent formatting - DeepSeek sometimes added preambles, strategic labels
**Status:** ✅ FIXED (v3.8.1) - XML-tagged prompts + strict formatting requirements = 100% success
**Implementation:** Added warnings, examples, explicit "DO NOT" lists, XML structure tags

### Issue: NA values in CSV (proposed_by, target, success columns)
**Cause:** Empty fields showing "NA" instead of empty strings
**Status:** ✅ FIXED - Replace NA with empty strings before CSV export, added na="" parameter

### Issue: "cannot open file 'verify_cross_expertise_loaded_v2.R'"
**Cause:** Verification scripts were removed during cleanup
**Status:** ✅ FIXED - Removed source() calls from run_simulation_with_actions.R

### Issue: CSV shows NA values for major/small power
**Cause:** CSV export didn't handle multi-action list
**Status:** ✅ FIXED - Modified save_actions_to_csv() to iterate over approved_actions

### Issue: Multi-action system runs when disabled
**Cause:** Missing enable flag check
**Status:** ✅ FIXED - Added check for ENABLE_MULTI_ACTION_SYSTEM in agent_decision.R

### Issue: Sprintf format error (crisis_level)
**Cause:** crisis_level changed from int to float, but format used %d
**Status:** ✅ FIXED - Changed format specifier from %d to %.0f

---

## Performance Targets

| Metric | Baseline (v3.0) | v3.7 | v3.8 Target |
|--------|-----------------|------|-------------|
| Total actions (3 periods) | 18 | 18 | 36-42 |
| Unique actions | 14 | 8 | 15-20 |
| Actions/period | 6 | 6 | 12-14 |
| Unique/period | 1.4 | 2.67 | 5-6.67 |

**Success Criteria:**
- ✅ Pass: 15+ unique actions in 3 periods
- ⚠️ Review: 12-14 unique actions
- ❌ Fail: <12 unique actions

---

## Quick Reference

### Run Simulation
```bash
cd /d/Northeastern/LLM_Forecasting
export OPENROUTER_API_KEY="your-key-here"
Rscript run_simulation_with_actions.R
```

### Check Results
```bash
# View actions
cat outputs/interactions/period_01_actions.csv

# Count unique actions
cat outputs/interactions/period_*_actions.csv | cut -d',' -f6 | sort -u | wc -l

# View assessments
cat outputs/assessment_period_1.txt
```

### Enable/Disable Multi-Action
```r
# In config.R
ENABLE_MULTI_ACTION_SYSTEM <- TRUE   # Use multi-action (v3.8)
ENABLE_MULTI_ACTION_SYSTEM <- FALSE  # Fallback to single-action
```

---

## Research Context

### Purpose
Test whether LLM-based simulations can generate realistic geopolitical dynamics and produce calibrated forecasts of government collapse probability.

### Applications
1. **Forecasting accuracy** - Compare LLM vs human expert predictions
2. **Action diversity** - Measure realistic variety of strategic responses
3. **Agent dynamics** - Study how internal disagreements affect outcomes
4. **Scenario sensitivity** - Test impact of different initial conditions

### Current Focus (v3.8)
**Improving action diversity** through multi-action proposal system to generate more realistic strategic behavior.

---

## Tips for Working with This Codebase

### 1. When Debugging
- Check console output for "PROPOSED ACTIONS" and "APPROVAL DECISIONS"
- Verify CSV has multiple rows per major faction
- Look for "Multi-action X/Y (priority)" in result_message column

### 2. When Making Changes
- Multi-action system is in `src/multi_action_system.R` and `src/multi_action_effects.R`
- Integration point is `src/agent_decision.R` lines 1239-1288
- CSV export is `src/interaction_engine.R` lines 1284-1339
- Always test with 1-period run first before full 3-period test

### 3. When Analyzing Results
- Action diversity is the key metric
- Check for both quantity (total actions) and quality (unique actions)
- Look for realistic patterns (hawks propose offensive, doves propose diplomatic)
- Verify President shows strategic agency (not mechanical crisis response)

### 4. When Adding Features
- Multi-action system is modular - can be toggled via config flag
- External actors still use single-action system (by design)
- Effect resolution is in separate file for easier tuning
- **Multi-action path:** State mutations happen via state threading in `resolve_multiple_action_effects()` - do NOT add calls to `apply_effects_to_state()` there
- **Single-action path:** State mutations happen directly in `execute_action()` and are applied in the simulation loop
- External event effects go through handlers in `simulation_with_actions.R`

---

## Version History

- **v3.9.0** (Current - February 14, 2026) - Parameter sensitivity fix (exact numeric values in agent prompts, international_support visible, full params in proposal/approval prompts), backstory reframing for forecasting (6 variants, 58-61% MSE reduction), agent-level prediction logging
- **v3.8.5** (February 8, 2026) - State threading for multi-action factions, sequential execution preserving ~30 direct mutations, synergies/contradictions/GDP/territory applied directly to threaded state
- **v3.8.4** (February 7, 2026) - Probabilistic external events with 15 event handlers, GDP application fix, Period 2 baseline fix, sanctions double-counting fix
- **v3.8.3** (February 2026) - Discussion memory for agent proposals, CSV export fixes
- **v3.8.2** (February 2026) - Temporal prompt structure fix, external events as dual-purpose (mechanical + narrative)
- **v3.8.1** (February 1, 2026) - XML-tagged prompts, 100% parsing success, multi-domain events
- **v3.8** (January 2026) - Multi-action proposal system
- **v3.7** - Cross-expertise recommendations, balanced scenario
- **v3.6** - Cross-expertise attempt (failed, caused decline in diversity)
- **v3.5** - Pre-invasion scenario, external actor drift
- **v3.0** - Baseline with 49 actions, single-action system

---

## Documentation Index

**Current Guides (docs/guides/):**
- `MULTI_ACTION_SYSTEM_GUIDE.md` - Complete v3.8.5 system documentation (effect resolution, event handlers, prompt pipeline, control condition)
- `FACTION_OBJECTIVES.md` - Faction capabilities and strategic options
- `COMPREHENSIVE_COMPARISON.md` - Version performance comparison
- `CLAUDE.md` - This file

**Main Docs:**
- `docs/README.md` - Project overview
- `START_HERE.md` - Quick reference

---

**Status:** v3.9.0 - Parameter sensitivity fixed, backstory reframing implemented. Simulation dataset should be regenerated with v3.9.0 for parameter-sensitive agent actions.

**Primary Contact:** See GitHub issues for questions/contributions.
