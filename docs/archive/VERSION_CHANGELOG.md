# Version Changelog

**Project:** Multi-Agent Wargame Simulation
**Current Version:** 3.9.0 (February 2026)

---

## v3.9.0 (February 14, 2026) - Parameter Sensitivity & Backstory Reframing

### Agent Parameter Sensitivity Fix

**Problem:** Agents were insensitive to scenario parameter differences. `format_situation_for_agent()` in `agent_decision.R` converted numeric parameters to categorical text (e.g., military_balance of -0.15 became "Unfavorable" or "Balanced" depending on worldview), hiding fine-grained differences. The `international_support` parameter was completely invisible to agents. The proposal and approval prompts only received `crisis_level` + 200 chars of static narrative.

**Solution:**

#### 1. Exact Numeric Values in Agent Situation Context (`agent_decision.R`)
- **Military balance**: Added `[exact: +0.05]` tag alongside worldview-filtered description
- **Sanctions level**: Added `[exact: 35%]` tag alongside categorical label
- **Crisis level**: Changed from rounded integer to one decimal (`7.3/10` not `7/10`)
- **Territory controlled**: Changed to one decimal precision (`12.5%` not `13%`), consistent label
- **International support**: Added entirely (was completely missing). Shows percentage with worldview-flavored interpretation

#### 2. Full Parameters in Proposal Prompts (`multi_action_system.R`)
- **`build_proposal_prompt()`**: Replaced minimal `Crisis Level: X/10 + Situation: [200 chars]` with full `CURRENT SCENARIO PARAMETERS` block showing all 5 numeric parameters with exact values
- **`build_approval_prompt()`**: Added same `CURRENT SCENARIO PARAMETERS` block in leader profile section
- Both prompts now instruct agents to calibrate proposals/decisions to exact parameter values

**Files Modified:**
- `src/agent_decision.R` — `format_situation_for_agent()` (lines 989-1125)
- `src/multi_action_system.R` — `build_proposal_prompt()` and `build_approval_prompt()`

**Test Results (3 contrasting 1-period scenarios):**

| Scenario | Crisis | Mil. Balance | Territory | P(Collapse) |
|----------|--------|-------------|-----------|-------------|
| Low threat | 3 | +0.08 | 2% | 0.385 |
| Medium threat | 6 | -0.10 | 20% | 0.606 |
| High threat | 9 | -0.28 | 38% | 0.635 |

- Novaris action overlap (low vs high): **33%** (3 shared of 9 unique)
- Tethys action overlap (low vs high): **25%** (3 shared of 12 unique)
- Collapse probability range: **0.250** across scenarios
- Novaris escalation tracks crisis: posturing (low) → limited strikes (medium) → sabotage + cyber + currency manipulation (high)

---

### Backstory Perspective Reframing for Forecasting

**Problem:** Systematic downward bias in collapse probability forecasting (ensemble mean ~0.35 vs ground truth ~0.58). All forecasting agents read the same Tethys-resilient backstory ("defender's advantage", "international support growing"), anchoring predictions low.

**Solution:** Added 5 reframed backstory variants (same facts, different analytical lens) and a "reframe" forecasting condition that cycles agents through all 6 variants.

#### Backstory Variants Added (`forecasting/run_multiscenario_experiment.py`)
- **Original**: Tethys-resilient framing (existing `INITIAL_SCENARIO`)
- **Aggressor**: Novaris-advantaged lens ("decisive conventional superiority", "no state has committed troops")
- **Vulnerability**: Clinical risk framing ("historically high failure rates", "compounding vulnerabilities")
- **Escalation**: Crisis momentum ("tightening spiral", "forces positioned become forces that act")
- **Domestic**: Internal politics (opposition parties, ethnic minorities, economic pain eroding support)
- **Inertia**: Status quo framing ("no shots fired", "states degrade slowly rather than collapse suddenly")

#### Reframe Condition
- Agents cycle through `BACKSTORY_VARIANTS[i % 6]` — each agent reads a different framing
- Full information (no sharding), default system prompt
- Added to `condition_map`: `"reframe": ("none", None, "reframe")`

#### Agent-Level Prediction Logging
- Per-agent metadata tracked (agent_id, model, backstory_variant/domain)
- Saved to `agent_predictions_*.csv` for diagnostic analysis

**Results (50 scenarios, 10 agents, 4 models):**

| Condition | MSE | vs Baseline |
|-----------|-----|-------------|
| Baseline | 0.0550-0.0572 | — |
| Reframe (6 variants) | 0.0214-0.0229 | **-58% to -61%** |
| Domain shard | 0.1367 | +143% (worse) |

**Files Modified:**
- `forecasting/run_multiscenario_experiment.py` — Added 5 variant constants, `BACKSTORY_VARIANTS` list, "reframe" condition handling, agent-level logging

---

## v3.8.5 (February 8-9, 2026) - State Threading & Multi-Target Fix

### Critical Fixes

#### 1. State Threading for Multi-Action Factions
**Problem:** Multi-action factions (Novaris, Tethys) were losing ~30 direct state mutations due to R's copy-on-modify semantics. Actions executed in parallel, each receiving the original state, so mutations from earlier actions were discarded.

**Solution:** Sequential execution with explicit state threading:
```r
state <- initial_state
for (action in approved_actions) {
  execution_result <- execute_action(action, state)
  state <- execution_result$state  # Thread state through
}
```

**Impact:**
- ✅ All ~30 direct state mutations now preserved (GDP, territory, sanctions, military balance, etc.)
- ✅ Actions see cumulative effects from previous actions in same period
- ✅ State changes properly propagate through action chains

**Files Modified:**
- `src/multi_action_effects.R` - Sequential execution loop (lines 15-50)

---

#### 2. Probabilistic External Events
**Problem:** External events generated but had no effect handlers - all were no-ops.

**Solution:** Implemented state handlers for all 15 event types with 50-85% effectiveness probabilities:
- Battlefield Development, Civilian Casualties, Humanitarian Crisis
- Economic Development, Diplomatic Development, Naval/Cyber/Air/Information Incidents
- International Response, Peace Initiative, Strategic Resource Discovery
- Political Development, Media Coverage, Intelligence Leak

**Impact:**
- ✅ Events now directly modify state (territory, crisis, sanctions, support)
- ✅ Realistic success/failure rates for different event types
- ✅ Agents can observe event outcomes in state changes

**Files Modified:**
- `src/simulation_with_actions.R` - Event handlers (lines 550-635)

---

#### 3. GDP Effect Application for Multi-Action
**Problem:** GDP effects not applied to multi-action factions - `action$agent_id` was NULL.

**Solution:** Use faction identity for GDP effects when agent_id is NULL:
```r
if (is.null(action$agent_id) && !is.null(faction)) {
  country <- if (faction == "major_power") "Novaris" else "Tethys"
  # Apply GDP effect using country
}
```

**Impact:**
- ✅ Economic actions now affect GDP for multi-action factions
- ✅ War bonds, trade negotiations, resource embargos have proper economic impact

**Files Modified:**
- `src/multi_action_effects.R` - GDP effect application (lines 200-220)

---

#### 4. Symmetric Early Termination Thresholds
**Problem:** Asymmetric thresholds (<5% or >90%) caused simulations to end prematurely at 94% collapse probability.

**Solution:** Symmetric thresholds: <5% (stability achieved) or >95% (collapse imminent)

**Impact:**
- ✅ Balanced early termination criteria
- ✅ Simulations complete all periods unless truly decided

**Files Modified:**
- `src/simulation_with_actions.R` - Threshold check (line 641)

---

#### 5. Multi-Target Resolution for Diplomatic Actions
**Problem:** Actions targeting "Meridian,Aurelia" failed to resolve - treated as single string that didn't match any agent. This caused diplomatic coordination to lose +15% alliance bonus.

**Solution:** Split comma-separated targets and match each individually:
```r
target_names <- trimws(strsplit(target_name, ",")[[1]])
for (tname in target_names) {
  # Try to match tname against agents
  if (match_found) break
}
```

**Impact:**
- ✅ Multi-target diplomatic actions correctly resolve
- ✅ Alliance bonuses properly applied (+15% success probability)
- ✅ Coalition building and intelligence sharing work as intended

**Files Modified:**
- `src/multi_action_effects.R` - Target resolution (lines 73-93)
- `src/agent_decision.R` - Target resolution for single-action path (lines 1330-1344)

---

#### 6. Decision Maker Model Switch
**Problem:** DeepSeek v3 outputting malformed tokens that broke parser.

**Solution:** Switched to Claude Sonnet 4 for approval decisions:
```r
DECISION_MAKER_MODEL <- "anthropic/claude-sonnet-4"
```

**Impact:**
- ✅ 100% parsing success maintained
- ✅ High-quality strategic judgment
- ✅ Reliable XML tag adherence

**Files Modified:**
- `config.R` - Model selection (line 21)

---

## v3.8.2 (February 2, 2026) - Discussion Memory & Conversational Continuity

### Major Improvements

#### 1. Discussion Memory System
**Why Added:** Agents had no recollection of previous discussions, causing repetitive arguments and loss of conversational context.

**What Changed:**
- Added `discussion_memory` field to state object
- Agents see previous period discussions before current coordination
- Smart summarization of long discussions (>500 chars) using Gemini 2.5 Flash

**Impact:**
- ✅ Agents can reference what they previously said
- ✅ Debates evolve instead of repeating
- ✅ Conversational continuity across periods

**Files Modified:**
- `src/state_manager.R` - Memory storage
- `src/interaction_engine.R` - Memory retrieval and display

---

## v3.8.1 (February 1, 2026) - XML-Tagged Prompts + 100% Parsing Success

### Major Improvements

#### 1. XML-Tagged Prompts
**Why Added:** DeepSeek approval decisions had ~50% parsing failure rate due to inconsistent formatting (preambles, strategic labels, etc.).

**What Changed:**
- Added XML semantic tags to structure long prompts
- Proposal prompt: `<meeting_context>`, `<task>`, `<domain_experts>`, `<required_format>`
- Approval prompt: `<leader_profile>`, `<proposals>`, `<strategic_options>`, `<format_requirements>`
- Coordination prompts: `<agent_identity>`, `<situation_context>`, `<response_format>`
- Forecast prompts: `<task_description>`, `<scenario_update>`, `<historical_context>`

**Implementation:**
- Added strict formatting requirements with warnings and explicit "DO NOT" lists
- Included multiple examples of correct format
- Clear rules section with 7 specific formatting requirements

**Results:**
- ✅ **100% parsing success rate** (0 failures across 10+ decision points in 5-period test)
- ✅ Improved LLM adherence to complex guidelines
- ✅ Better structure for maintaining context in long prompts

**Files Modified:**
- `src/multi_action_system.R` - Proposal and approval prompts (lines 110-187, 385-494)
- `src/interaction_engine.R` - Coordination prompts (lines 796-870, 931-990)
- `src/forecast_prompts.R` - Forecasting prompts (lines 19-51, 126-157)
- `src/agent_system.R` - Agent response prompt (lines 126-165)

---

#### 2. Multi-Domain Events
**Why Added:** Previous events were limited to traditional battlefield developments. Modern conflicts include cyber, naval, air, and information warfare.

**What Changed:**
- Added multi-domain event types to event generator
- Naval Incidents (maritime confrontations, blockades)
- Cyber Incidents (network intrusions, infrastructure attacks)
- Air Incidents (airspace violations, intercepts)
- Information Warfare (disinformation campaigns, propaganda)

**Impact:**
- More diverse strategic environment
- Actions now match event types (cyber_attack in response to Cyber Incident)
- Better representation of modern multi-domain warfare

---

#### 3. Enhanced Action Diversity
**Why Added:** Needed more varied action types beyond basic military/diplomatic categories.

**New Actions Successfully Generating:**
- **Naval:** `naval_deployment`, `show_of_force`, `increased_patrols`
- **Cyber:** `cyber_attack`, `cyber_theft`, `enhanced_cyber_defense`
- **Intelligence:** `share_intelligence`, `enhanced_surveillance`
- **Diplomatic:** `coalition_building`, `prisoner_exchange`, `formal_ceasefire_proposal`, `public_diplomacy_campaign`
- **Economic:** `resource_embargo`, `currency_manipulation`

**Results:**
- Dramatic improvement in action variety
- Sophisticated multi-domain strategies emerging
- Creative responses to specific event types

---

#### 4. Mixed LLM Strategy
**Why Added:** Different models excel at different tasks. Optimization for best performance and cost.

**Model Assignments:**
| Component | Model | Purpose |
|-----------|-------|---------|
| **Agent Proposals** | Qwen 2.5 72B | Creative domain-appropriate suggestions |
| **Approval Decisions** | DeepSeek v3 | Strategic judgment with consistent formatting |
| **Aggregation** | Gemini 2.0 Flash | Probability assessments and trend analysis |

**Impact:**
- Better quality responses for each task type
- Consistent parsing with DeepSeek (100% success)
- Cost-effective aggregation with Gemini

---

#### 5. Bug Fixes
**NA Values in CSV:**
- Replaced NA with empty strings in CSV export
- Added `na=""` parameter to `write.csv()`

**Sprintf Format Error:**
- Fixed crisis_level format mismatch (%d → %.0f)

**Archive Path:**
- Corrected output archive path to `archive/old_simulation_runs/`

---

### Test Results (5-Period Simulation)

**Parsing Performance:**
- ✅ 100% success rate (0 failures)
- ✅ All 10 decision points successfully parsed
- ✅ No manual intervention required

**Action Diversity:**
- 36 total actions executed (6-8 per faction per period)
- 20+ unique action types across 5 periods
- Multi-domain strategies observed
- Counter-proposals working correctly

**Narrative Quality:**
- Dramatic arc: 28% → 38% → 53% → 78% → 56% collapse probability
- Realistic dynamics: Aggressor Breakthrough (P4) → Aggressor Military Failure (P5)
- Strategic reversals and shock events creating compelling narrative

---

### Documentation Updates

**Updated Files:**
- `docs/README.md` - Version 3.8.1, XML tags, mixed LLM strategy
- `docs/START_HERE.md` - Latest improvements section
- `docs/guides/CLAUDE.md` - v3.8.1 features, parsing success, known issues
- `docs/guides/MULTI_ACTION_SYSTEM_GUIDE.md` - Status: Production Ready
- `docs/VERSION_CHANGELOG.md` - This changelog

---

## v3.8 (January 31, 2026) - Multi-Action Proposal System

### Major Features

**Multi-Action Decision Making:**
- Domain experts (Military, Intelligence, Diplomatic, Economic) propose 1-3 actions each
- Presidential approval system - leader reviews and approves/vetoes proposals
- Parallel execution - 3-6 concurrent actions per faction per period
- Effect resolution - cumulative effects, diminishing returns, contradictions, synergies

**Files Added:**
- `src/multi_action_system.R` - Proposal and approval system
- `src/multi_action_effects.R` - Effect resolution logic

**Impact:**
- Increased action diversity from 8 unique actions (v3.7) to 15-20 target (v3.8)
- More realistic government decision-making processes
- Better representation of multi-track diplomacy and strategy

**Documentation:**
- `docs/guides/MULTI_ACTION_SYSTEM_GUIDE.md` - Complete system guide
- `docs/guides/FACTION_OBJECTIVES.md` - Faction capabilities
- `docs/guides/COMPREHENSIVE_COMPARISON.md` - Version comparison

---

## v3.7 (January 2026) - Cross-Expertise Recommendations + Balanced Scenario

### Features
- Cross-expertise recommendations - agents can suggest actions outside their domain
- Balanced scenario - both major and small powers have offensive/defensive capabilities
- Scenario rebalancing to avoid predetermined outcomes

**Impact:**
- Unfortunately caused action diversity decline (8 unique actions vs 14 baseline)
- Led to development of v3.8 multi-action system

---

## v3.6 (January 31, 2026) - Pre-Invasion Scenario + External Actor Drift + Action Repetition

### Major Features Added

#### 1. Pre-Invasion Scenario (v3.6)
**Why Added:** All previous scenarios assumed invasion had already occurred. Need ability to model escalation dynamics before conflict starts and test whether agents choose war or peace.

**What Changed:**
- Added `pre_invasion` scenario preset to `SCENARIO_PRESETS` in `config.R`
- Invasion is now **emergent** - may or may not happen based on agent decisions
- `is_pre_invasion` flag added to scenario state

**Scenario Parameters:**
- Territory controlled: 0% (no invasion yet)
- Crisis level: 5/10 (elevated but not maximum)
- Military balance: -0.15 to 0.0 (major power advantage but not overwhelming)
- Sanctions: 10% (limited warning sanctions)
- Situation: "Troops massing on border, ultimatums issued, no shots fired yet"

**Files Modified:**
- `config.R` (lines 21-34) - Added pre_invasion preset
- `SCENARIO_CONFIGURATION.md` - Documented new scenario
- `README.md`, `CURRENT_SYSTEM_GUIDE.md`, `START_HERE.md` - Updated scenario lists

**Documentation:**
- All scenario configuration docs updated to include 5 scenarios (was 4)

**Impact:**
- Enables testing of escalation vs. de-escalation dynamics
- Research question: Do LLMs choose war when given a choice?
- Comparison to historical pre-war crises (Ukraine Jan-Feb 2022, Iraq 2002-2003)

---

#### 2. External Actor Alignment Drift (v3.6)
**Why Added:** External actors' positions were static throughout simulation. In reality, alignments shift based on atrocities, military outcomes, economic pressure, nuclear threats.

**What Changed:**
- Added `alignment_drift` parameters to all 4 external actors in `config.R`
- Implemented `calculate_alignment_drift()` function in `agent_decision.R`
- Drift calculated each period based on state and events

**Drift Parameters (per actor):**
- `base_alignment`: Starting position (pro_tethys, pro_novaris, neutral, neutral_humanitarian)
- `alignment_strength`: Commitment level (0-1, higher = more stable)
- `drift_sensitivity`: Responsiveness to events (0-1, higher = more reactive)
- Various positive/negative triggers specific to each actor

**Drift Triggers:**
- **Crisis level ≥9**: +0.10 drift toward action
- **Territory >15%**: +0.15 drift (galvanizes support for defender)
- **Sanctions >60%**: -0.10 drift for pro-Novaris actors (economic pressure)
- **Nuclear use**: +0.30 drift (major shock to all actors)
- **Atrocities**: +0.10 drift (humanitarian response)
- **Military victories**: ±0.05 drift (bandwagoning or support)
- **Economic factors**: -0.05 drift toward accommodation

**Drift Calculation:**
```
drift_magnitude = |drift_score| × sensitivity × (1 - strength)
drift_direction = "more_assertive" | "more_accommodating" | "stable"
```

**Files Modified:**
- `src/agent_decision.R` (lines 309-420) - Drift calculation function
- `config.R` (lines 489-634) - Drift parameters for all 4 external actors
- Agent prompts now include drift context when magnitude >0.02

**Documentation:**
- `SCENARIO_CONFIGURATION.md` - Complete drift mechanics section
- `CURRENT_SYSTEM_GUIDE.md` - External Actor Drift feature section
- `README.md` - Mentioned in overview

**Examples:**
- **Meridian** (pro-Tethys, strength=0.7, sensitivity=0.4):
  - If Tethys repeatedly fails militarily: drift toward reducing support
  - If Novaris commits atrocities: drift toward more assertive support
- **Aurelia** (neutral, strength=0.5, sensitivity=0.6):
  - Highly responsive to events
  - Energy crisis: drift toward accommodating Novaris
  - Refugee crisis: drift toward supporting Tethys
- **Valkoria** (pro-Novaris, strength=0.65, sensitivity=0.5):
  - Heavy sanctions: drift away from Novaris (economic cost)
  - Novaris success: drift toward stronger support

**Impact:**
- Dynamic international environment (not static alliances)
- Realistic alliance commitment variation
- Research applications: test when allies abandon losing side

---

#### 3. Action Repetition Tracking (v3.6)
**Why Added:** Repeated diplomatic actions should have diminishing effectiveness. Real-world peace talks that fail repeatedly entrench positions.

**What Changed:**
- Implemented action repetition tracking for `peace_talks` in `action_execution.R`
- Tracks `state$peace_talks_count` and applies diminishing returns
- Framework extensible to other actions

**Peace Talks Diminishing Returns:**
- Base probability: 30%
- Diminishing factor: `max(0.1, 1 - (count - 1) * 0.15)`
- Each failed attempt reduces effectiveness by 15%
- Floor: 10% minimum (never impossible, but increasingly futile)
- Also applies penalty if losing side proposes (appears desperate)

**Formula:**
```r
state$peace_talks_count <- state$peace_talks_count + 1
diminishing_factor <- max(0.1, 1 - (state$peace_talks_count - 1) * 0.15)
base_prob <- 0.30 * diminishing_factor
```

**Example Progression:**
- 1st peace_talks: 30% × 1.0 = 30% success
- 2nd peace_talks: 30% × 0.85 = 25.5%
- 3rd peace_talks: 30% × 0.70 = 21%
- 4th peace_talks: 30% × 0.55 = 16.5%
- 5th peace_talks: 30% × 0.40 = 12%
- 6th+ peace_talks: 30% × 0.10 = 3% (floor)

**Files Modified:**
- `src/action_execution.R` (lines 101-140) - Peace talks execution with tracking
- Result messages indicate total attempts and diminishing factor

**Documentation:**
- `SCENARIO_CONFIGURATION.md` - Action repetition mechanics section
- `CURRENT_SYSTEM_GUIDE.md` - Action system subsection
- `README.md` - Mentioned in overview

**Impact:**
- More realistic diplomatic dynamics
- Agents must consider timing of peace initiatives
- Research question: Does diminishing effectiveness lead to earlier force use?

---

### Technical Details

**Scenario Configuration:**
```
v3.2: 4 scenarios (low, medium, high, stalemate)
v3.6: 5 scenarios (pre_invasion, low, medium, high, stalemate)
```

**External Actor Parameters:**
```r
# Example: Meridian
alignment_drift = list(
  base_alignment = "pro_tethys",
  alignment_strength = 0.7,      # Fairly committed
  drift_sensitivity = 0.4,        # Moderately responsive
  negative_triggers = c("tethys_military_failure", "domestic_opposition", ...),
  positive_triggers = c("novaris_atrocity", "tethys_success", ...)
)
```

**State Tracking:**
- `state$peace_talks_count` - Number of peace_talks attempts
- `state$scenario_state$is_pre_invasion` - Pre-invasion scenario flag
- Drift magnitude logged to console when >0.02

---

### Documentation Updates

**Updated Documentation:**
- `README.md` - Version 3.6, pre-invasion scenario, drift mechanics, action repetition
- `CURRENT_SYSTEM_GUIDE.md` - v3.6 features, scenario table, mechanics, research applications
- `SCENARIO_CONFIGURATION.md` - Pre-invasion scenario, drift mechanics, repetition tracking
- `START_HERE.md` - What's new v3.6, scenario options
- `VERSION_CHANGELOG.md` - This changelog (v3.6 section)

**No New Files:**
- All features integrated into existing architecture
- No breaking changes to file structure

---

### Migration Guide

**From v3.2 to v3.6:**

**No breaking changes** - v3.6 is fully backward compatible with v3.2.

**What you get automatically:**
- Pre-invasion scenario available as option
- External actor drift calculated each period (logged when significant)
- Peace talks diminishing returns applied automatically

**No code changes needed** - just run:
```bash
Rscript run_simulation_with_actions.R
```

**To use pre-invasion scenario:**
```r
# Edit config.R line 17:
SCENARIO_PRESET <- "pre_invasion"
```

**Expected differences in output:**
- Console shows drift notifications when magnitude >0.02
- Peace talks results show attempt count and diminishing factor
- Pre-invasion scenarios show escalation from 0% territory

**Configuration options:**
- All v3.2 options unchanged
- New: Choose `pre_invasion` scenario preset
- New: Adjust drift parameters in `config.R` (lines 489-634)
- New: Modify diminishing returns in `action_execution.R` (line 107)

---

## v3.2 (January 21, 2026) - Pre-Action Coordination + Independent External Actors

### Major Features Added

#### 1. Pre-Action Coordination (v3.1)
**Why Added:** Agents were taking actions without discussing or coordinating first, which was unrealistic for military and diplomatic decision-making.

**What Changed:**
- Added `run_pre_action_coordination()` function to `interaction_engine.R`
- Modified `agent_decision.R` to run coordination before action decisions
- Decision makers now receive team input before choosing actions

**How It Works:**
- All agents in a faction participate (if 2+ agents)
- Two rounds of discussion:
  - Round 1: Each agent shares initial position
  - Round 2: Agents respond to each other's perspectives
- Intelligence directors brief on threats
- Military commanders recommend options
- Economic advisors warn about costs
- Foreign ministers suggest diplomatic alternatives
- Faction leader makes final decision considering all input

**Files Modified:**
- `src/interaction_engine.R` (+165 lines)
- `src/agent_decision.R` (~50 lines changed)
- `src/simulation_with_actions.R` (+3 lines)
- `README.md` (updated flow description)

**Documentation:**
- `PRE_ACTION_COORDINATION.md` - Complete feature documentation

**Impact:**
- ~16 additional messages per period (pre-action coordination)
- More realistic decision-making process
- Better representation of cabinet meetings, war councils, intelligence briefings

---

#### 2. Independent External Actors (v3.1.1)
**Why Added:** All external actors (Meridian, Valkoria, Aurelia, International Org) were coordinating as a single "external" faction, which was unrealistic since they have conflicting interests.

**What Changed:**
- Split "external" faction into 4 independent factions
- Each external actor now makes own decisions

**The 4 Independent External Actors:**
1. **Meridian** (Allied Defender) - Supports Tethys, provides military/economic aid
2. **Valkoria** (Allied Aggressor) - Supports Novaris, provides diplomatic/economic support
3. **Aurelia** (Neutral Power) - Mediates, seeks regional stability
4. **International Org** (UN/EU) - Humanitarian focus, civilian protection

**Files Modified:**
- `config.R` (lines 151-190) - Changed faction assignments
- `src/agent_decision.R` (line 536) - Updated faction list from 3 to 6 factions
- `src/interaction_engine.R` (lines 59-101) - Updated post-action discussion scenarios
- `README.md` (lines 161-169) - Updated external actors section

**Documentation:**
- `INDEPENDENT_EXTERNAL_ACTORS.md` - Complete feature documentation

**Impact:**
- 6 factions now act per period (was 3)
- More complex strategic environment
- Realistic alliance dynamics (Meridian vs Valkoria competition)
- Better representation of international relations

---

#### 3. Guaranteed External Engagement (v3.1.2)
**Why Added:** External actor engagement was probabilistic (Valkoria 60%, Aurelia 40%, Int'l Org 50%) with no clear rationale, while Meridian was guaranteed. Inconsistent during active warfare.

**What Changed:**
- Removed all probability checks for external engagement
- All external actors now engage every period (100% guaranteed)

**Rationale:**
- **Realism**: During active warfare, allies are constantly engaged
- **Consistency**: If Meridian engages every period, Valkoria should too
- **Research Value**: More consistent data, removes random noise
- **Active Conflict Context**: Crisis level typically 6-10, requires sustained diplomatic channels

**Files Modified:**
- `src/interaction_engine.R` (lines 77, 87, 99) - Removed `runif()` probability checks

**Documentation:**
- `GUARANTEED_EXTERNAL_ENGAGEMENT.md` - Complete feature documentation

**Impact:**
- ~15 additional messages per period
- Consistent diplomatic activity across all periods
- Better network analysis (no missing edges from random non-engagement)
- Total: ~106 messages per period (up from ~90)

---

### Technical Details

**New Faction Structure:**
```
v3.0: 3 factions → 2 combatants + 1 external group
v3.2: 6 factions → 2 combatants + 4 independent external actors
```

**Period Flow (v3.2):**
```
1. External Events Generation
2. Pre-Action Coordination (2 rounds per faction with 2+ agents)
3. Action Decision (6 factions decide independently)
4. Action Execution (real state changes)
5. Post-Action Discussion (all external actors engage guaranteed)
6. Aggregator Assessment
7. State Update
```

**Interaction Count Per Period:**
- Pre-action coordination: ~16 messages (8 agents × 2 rounds, factions with 2+ agents)
- Post-action: Novaris internal: ~20 messages
- Post-action: Tethys internal: ~20 messages
- Post-action: Novaris ↔ Tethys: ~10 messages
- Post-action: Meridian → Tethys: ~10 messages (guaranteed)
- Post-action: Valkoria → Novaris: ~10 messages (guaranteed)
- Post-action: Aurelia → mediation: ~10 messages (guaranteed)
- Post-action: Int'l Org → humanitarian: ~10 messages (guaranteed)
- **Total: ~106 messages per period**

**Cost Impact:**
- 10 periods × 106 messages = ~1,060 LLM calls per simulation
- Additional cost vs v3.0: ~31 messages per period × 10 = ~310 additional calls
- Time: ~15-20 minutes per simulation (was ~12-15 minutes)

---

### Documentation Updates

**New Documentation:**
- `PRE_ACTION_COORDINATION.md` - Pre-action coordination feature guide
- `INDEPENDENT_EXTERNAL_ACTORS.md` - Independent external actors guide
- `GUARANTEED_EXTERNAL_ENGAGEMENT.md` - Guaranteed engagement guide
- `VERSION_CHANGELOG.md` - This file

**Updated Documentation:**
- `CURRENT_SYSTEM_GUIDE.md` - Updated to v3.2, new features, flow description
- `START_HERE.md` - Updated quick facts, what's new section
- `CLAUDE.md` - Updated simulation flow, external actors, interaction engine
- `README.md` - Updated flow description, external actors section

**Archived Documentation:**
- Moved 16 old documentation files to `archive/documentation/`
- Created `ARCHIVE_INDEX.md` - Complete index of archived files
- Created `CLEANUP_SUMMARY.md` - Documentation consolidation summary

---

## v3.0 (January 2026) - Full Action Execution System

### Features
- ✅ 49 executable actions across 7 categories
- ✅ Dynamic state tracking (GDP, military strength, territory, crisis level)
- ✅ Probabilistic outcomes based on capabilities
- ✅ Cascading effects (combat attrition, economic costs)
- ✅ Detection risk for covert operations
- ✅ Configurable scenario presets (low, medium, high intensity, stalemate)
- ✅ Complete cognitive framework (worldviews, deception, rationality)
- ✅ Human forecasting prompt generation

### Files
- `src/enhanced_action_space.R` - 49-action system
- `src/action_execution.R` - Action execution engine
- `src/simulation_with_actions.R` - Main simulation loop with actions
- `run_simulation_with_actions.R` - Main entry point

### Documentation
- `ACTION_EXECUTION_GUIDE.md` - Complete action reference
- `SCENARIO_CONFIGURATION.md` - Scenario setup guide

---

## v2.0 (December 2025) - Cognitive Framework

### Features
- ✅ Cognitive framework (worldviews, deception mechanics, rationality traits)
- ✅ Information asymmetry (different agents see different intelligence)
- ✅ Trust dynamics (deception damages relationships)
- ❌ No action execution (agents only discuss)
- ❌ Basic 27-action taxonomy (not executable)

### Files (Archived)
- `src/agent_system.R` - Basic cognitive agents
- `src/action_space.R` - 27-action taxonomy (reference only)
- `run_enhanced_simulation.R` - Cognitive-only runner

---

## v1.0 (November 2025) - Basic Multi-Agent System

### Features
- ✅ 11-agent system with distinct roles
- ✅ Simple personas (hawk/dove, policy adherence, objective alignment)
- ✅ Interaction engine (agent-to-agent communication)
- ✅ Aggregator assessments (probability estimates)
- ❌ No cognitive framework
- ❌ No action execution

### Files (Archived)
- `run_simulation.R` - Basic runner

---

## Migration Guide

### From v3.0 to v3.2

**No breaking changes** - v3.2 is fully backward compatible with v3.0.

**What you get automatically:**
- Pre-action coordination happens before action decisions
- External actors act independently (not as single group)
- All external engagement guaranteed every period

**No code changes needed** - just run:
```bash
Rscript run_simulation_with_actions.R
```

**Expected differences in output:**
- More messages per period (~106 vs ~75)
- 6 faction decision sections (not 3)
- Pre-action coordination logs for multi-agent factions
- Consistent external engagement every period

**Configuration options:**
- Coordination length: Modify `n_rounds` in `interaction_engine.R` (default: 2)
- All other options unchanged from v3.0

### From v2.0 to v3.2

**Breaking changes:**
- Actions now execute with real state effects
- Must use `run_simulation_with_actions.R` (not `run_enhanced_simulation.R`)

**Migration steps:**
1. Use new main runner: `Rscript run_simulation_with_actions.R`
2. Update any references to "external" faction → specific faction names
3. Expect different outputs (actions execute, state changes)

### From v1.0 to v3.2

**Breaking changes:**
- Cognitive framework required
- Action execution system required
- Must use `run_simulation_with_actions.R`

**Migration steps:**
1. Review `config.R` for new agent properties (worldviews, deception, etc.)
2. Use new main runner: `Rscript run_simulation_with_actions.R`
3. Review `ACTION_EXECUTION_GUIDE.md` for action system

---

## Testing

### Verify v3.2 Features

**1. Pre-Action Coordination:**
```bash
Rscript run_simulation_with_actions.R
# Look for: "→ Pre-action coordination within [FACTION] faction..."
# Should see 2 rounds of discussion before action decisions
```

**2. Independent External Actors:**
```bash
# Check console output shows 6 faction decisions (not 3):
# - MAJOR POWER
# - SMALL POWER
# - MERIDIAN
# - VALKORIA
# - AURELIA
# - INTERNATIONAL ORG
```

**3. Guaranteed External Engagement:**
```bash
# Check post-action discussions show all 4 external actors every period:
# - External: Meridian → Tethys
# - External: Valkoria → Novaris
# - External: Aurelia → mediation
# - External: Int'l Org → humanitarian
# No random variation - should appear every period
```

### Verify Output Files

```r
# Load simulation state
state <- readRDS("outputs/simulation_state.rds")

# Check pre-action coordination records
length(state$pre_action_coordination)  # Should equal n_periods

# Check faction actions
table(sapply(state$faction_actions, function(a) a$faction))
# Should show 6 factions: major_power, small_power, meridian, valkoria, aurelia, international_org

# Check interaction counts per period
sapply(state$interactions_history, function(period) {
  period$interaction_count
})
# Should be consistent across periods (~106 messages each)
```

---

## Future Roadmap

### Potential v3.3 Features
- Coalition formation (external actors coordinate on specific issues)
- Multi-agent external powers (Meridian has President + Foreign Minister + Military)
- Resource constraints for external actors (limited aid budgets)
- Public opinion in external countries (domestic pressure on support)
- Learning from outcomes (agents adjust based on coordination effectiveness)

### Research Priorities
- Calibration against historical conflicts (Russia-Ukraine data)
- LLM vs human forecasting comparison
- Sensitivity analysis on initial conditions
- Multiple simulation scenarios for robustness

---

## Version Summary Table

| Version | Date | Key Features | Entry Point | Status |
|---------|------|--------------|-------------|--------|
| **v3.9.0** | Feb 14, 2026 | Parameter sensitivity fix, backstory reframing, agent-level logging | `run_simulation_with_actions.R` | ✅ **CURRENT** |
| v3.8.5 | Feb 8-9, 2026 | State threading, multi-target fix, probabilistic external events | `run_simulation_with_actions.R` | ✅ Superseded |
| v3.8.1 | Feb 1, 2026 | XML-tagged prompts, 100% parsing success, Multi-domain events | `run_simulation_with_actions.R` | ✅ Superseded |
| v3.8 | Jan 31, 2026 | Multi-action proposal system, Presidential approval | `run_simulation_with_actions.R` | ✅ Superseded |
| v3.7 | Jan 2026 | Cross-expertise, Balanced scenario | `run_simulation_with_actions.R` | ✅ Superseded |
| v3.6 | Jan 31, 2026 | Pre-invasion scenario, External actor drift, Action repetition | `run_simulation_with_actions.R` | ✅ Superseded |
| v3.2 | Jan 21, 2026 | Pre-action coordination, Independent external actors, Guaranteed engagement | `run_simulation_with_actions.R` | ✅ Superseded |
| v3.0 | Jan 2026 | 49 actions, Dynamic state, Probabilistic outcomes | `run_simulation_with_actions.R` | ✅ Superseded |
| v2.0 | Dec 2025 | Cognitive framework, No action execution | `run_enhanced_simulation.R` | 📦 Archived |
| v1.0 | Nov 2025 | Basic 11-agent system | `run_simulation.R` | 📦 Archived |

---

**Last Updated:** February 14, 2026
**Current Version:** 3.9.0
