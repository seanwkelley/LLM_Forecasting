# Current System Guide - Multi-Agent Wargame Simulation

**Last Updated:** January 2026
**Version:** 3.6 (Pre-Invasion Scenario + External Actor Drift + Action Repetition)

## Quick Start

**To run the complete, current simulation:**
```bash
Rscript run_simulation_with_actions.R
```

That's it! The simulation now includes:
- ✅ 11 intra-country actors with distinct roles
- ✅ Cognitive frameworks (worldviews, deception mechanics, rationality traits)
- ✅ **Pre-action coordination** - agents discuss before deciding actions
- ✅ 49 executable actions across 7 categories
- ✅ **Independent external actors** - each makes own decisions (Meridian, Valkoria, Aurelia, UN/EU)
- ✅ **External actor drift** (v3.6) - alignments shift based on events and state changes
- ✅ **Pre-invasion scenario** (v3.6) - optional emergent conflict starting condition
- ✅ **Action repetition tracking** (v3.6) - diminishing returns for repeated peace_talks
- ✅ Dynamic state tracking (GDP, military strength, territory, crisis level)
- ✅ Information asymmetry and trust dynamics
- ✅ Probabilistic outcomes and cascading effects
- ✅ **Guaranteed diplomatic engagement** - all external actors engage every period
- ✅ Automated human forecasting prompt generation

---

## What This System Does

This is a sophisticated multi-agent LLM simulation that models geopolitical conflict between:
- **Novaris** (Major Power/Aggressor)
- **Tethys** (Smaller Power/Defender)
- **Meridian** (Allied Major Power supporting Tethys)
- **Aurelia** (Neutral Regional Power)
- **International Organizations** (UN/EU-style)

### Central Research Question
**What is the probability that Tethys's government will be toppled?**

### How It Works (Each Period)

1. **External Events Generated** - Economic shocks, battlefield shifts, wild cards
2. **Pre-Action Coordination** - Agents within each faction discuss and debate what action to take (2 rounds)
3. **Action Decisions** - Each faction leader chooses action based on team input
4. **Actions Execute** - Real consequences: GDP changes, military strength, territory control
5. **Post-Action Discussion** - Agents react to results, coordinate responses (4-6 exchanges)
6. **Aggregator Assesses** - Separate LLM evaluates collapse probability
7. **State Updates** - All changes logged for next period

---

## Current File Structure

### Core Execution Files (USE THESE)

| File | Purpose | Status |
|------|---------|--------|
| **`run_simulation_with_actions.R`** | Main entry point - RUN THIS | ✅ CURRENT |
| **`config.R`** | Agent definitions, scenario settings | ✅ CURRENT |
| **`src/integrated_agent_system.R`** | Cognitive framework (worldviews, deception) | ✅ CURRENT |
| **`src/enhanced_action_space.R`** | 49 actions across 7 categories | ✅ CURRENT |
| **`src/action_execution.R`** | Executes actions, updates state | ✅ CURRENT |
| **`src/agent_decision.R`** | Agents choose actions via LLM | ✅ CURRENT |
| **`src/simulation_with_actions.R`** | Main simulation loop with actions | ✅ CURRENT |
| **`src/aggregator.R`** | Probability assessment | ✅ CURRENT |
| **`src/event_generator.R`** | External events | ✅ CURRENT |
| **`src/interaction_engine.R`** | Agent-to-agent communication | ✅ CURRENT |
| **`src/state_manager.R`** | Logging and state management | ✅ CURRENT |
| **`src/forecast_prompts.R`** | Human forecasting prompts (true + control) | ✅ CURRENT |
| **`src/control_condition.R`** | Control condition generation | ✅ CURRENT (NEW v3.2) |
| **`src/analysis.R`** | Visualization and analysis | ✅ CURRENT |

### Legacy Files (ARCHIVED - For Reference Only)

These files have been moved to `archive/` and are superseded by current implementations:

| Archived File | Replaced By | Reason |
|---------------|-------------|--------|
| `src/action_space.R` | `src/enhanced_action_space.R` | Old 27-action system replaced by 49-action system |
| `src/agent_system.R` | `src/integrated_agent_system.R` | Basic agents replaced by cognitive framework |
| `src/simulation.R` | `src/simulation_with_actions.R` | No action execution → Full action system |
| `run_simulation.R` | `run_simulation_with_actions.R` | Basic mode → Full cognitive + actions |
| `run_enhanced_simulation.R` | `run_simulation_with_actions.R` | Intermediate state (cognitive only, no actions) |

### Documentation (Current)

| File | Purpose |
|------|---------|
| **`CURRENT_SYSTEM_GUIDE.md`** | This file - authoritative current state |
| **`README.md`** | Project overview and installation |
| **`ACTION_EXECUTION_GUIDE.md`** | Detailed action system reference |
| **`SCENARIO_CONFIGURATION.md`** | How to configure scenarios |
| **`CONTROL_CONDITION_GUIDE.md`** | Control condition methodology (NEW v3.2) |
| **`CLAUDE.md`** | Project context for Claude AI |
| **`QUICKSTART.md`** | Quick setup guide |

All other documentation has been archived to `archive/documentation/`.

---

## The 11 Agents

### Major Power (Novaris) - 4 Agents
- **Military Chief of Staff** - Hawk 0.8, Policy 0.9, Alignment 0.95
- **Defense Minister** - Hawk 0.7, Policy 0.9, Alignment 0.9
- **Economic Advisor** - Hawk 0.3, Policy 0.7, Alignment 0.5 (cost concerns)
- **Intelligence Director** - Hawk 0.6, Policy 0.85, Alignment 0.8

### Smaller Power (Tethys) - 4 Agents
- **President** - Hawk 0.5, Policy 1.0, Alignment 0.95
- **Military Commander** - Hawk 0.85, Policy 0.9, Alignment 0.95
- **Foreign Minister** - Hawk 0.3, Policy 0.85, Alignment 0.9 (seeks diplomacy)
- **Opposition Leader** - Hawk 0.6, Policy 0.4, Alignment 0.6 (political survival)

### External Actors - 4 Independent Agents
- **Allied Defender (Meridian)** - Hawk 0.6, supports Tethys, provides military/economic aid
- **Allied Aggressor (Valkoria)** - Hawk 0.7, supports Novaris, provides diplomatic/economic support
- **Neutral Regional Power (Aurelia)** - Hawk 0.2, seeks mediation, prioritizes stability
- **International Organization (UN/EU)** - Hawk 0.1, humanitarian focus, civilian protection

**Each external actor acts independently** with their own decision-making and objectives

Each agent has:
- **Worldview** (realist, liberal institutionalist, nationalist, pragmatic technocrat, etc.)
- **Deception capacity** (0-1, ability to deceive)
- **Deception willingness** (0-1, moral reluctance)
- **Analytical ability** (0-1, detect deception)
- **Information access** (0-1, intelligence visibility)
- **Rationality traits** (bounded rationality, loss aversion, etc.)

---

## The 49 Actions

### 1. DIPLOMATIC (6)
`diplomatic_visit`, `peace_talks`, `trade_negotiation`, `cultural_exchange`, `humanitarian_aid`, `mediation_offer`

### 2. INTELLIGENCE (5)
`intelligence_gathering`, `surveillance_operation`, `counterintelligence`, `spread_disinformation`, `propaganda_campaign`

### 3. ECONOMIC (6)
`trade_agreement`, `economic_sanctions`, `financial_aid`, `resource_embargo`, `currency_manipulation`, `cyber_theft`

### 4. MILITARY POSTURE (6)
`military_buildup`, `naval_deployment`, `air_patrols`, `troop_movements`, `joint_exercises`, `arms_development`

### 5. COVERT OPERATIONS (6 - HIGH RISK)
`sabotage`, `assassination_attempt`, `regime_destabilization`, `proxy_support`, `false_flag_operation`, `cyber_attack`

### 6. OPEN CONFLICT (6 - KINETIC)
`border_incursion`, `limited_strike`, `full_scale_attack`, `occupation`, `blockade`, `siege_warfare`

### 7. WMD (5 - EXTREME)
`nuclear_development`, `chemical_weapons`, `biological_program`, `tactical_nuclear_use`, `strategic_nuclear_strike`

**See `ACTION_EXECUTION_GUIDE.md` for complete action details, success probabilities, and effects.**

---

## Scenario Configuration

### Change Scenario Intensity
Edit `config.R` line 17:
```r
SCENARIO_PRESET <- "medium_intensity"  # Options: pre_invasion, low_intensity, medium_intensity, high_intensity, stalemate
```

### Available Scenarios

| Preset | Territory | Crisis | Military Balance | Description |
|--------|-----------|--------|------------------|-------------|
| **pre_invasion** (v3.6) | 0% | 5/10 | -0.15 to 0.0 | Escalating tensions, no invasion yet - emergent conflict |
| **low_intensity** | 2-5% | 7/10 | -0.1 to 0.0 | Limited border incursion |
| **medium_intensity** | 5-12% | 9/10 | -0.3 to -0.1 | Full-scale invasion (DEFAULT) |
| **high_intensity** | 15-25% | 10/10 | -0.5 to -0.3 | Total war, cities under siege |
| **stalemate** | 8-15% | 6/10 | -0.1 to 0.1 | Frozen conflict, stable frontlines |

**See `SCENARIO_CONFIGURATION.md` for detailed scenario effects.**

---

## Installation

### Prerequisites
```bash
# R version 4.0 or higher
install.packages(c("httr", "jsonlite", "ggplot2", "dplyr", "tidyr", "igraph", "uuid"))
```

### API Key Setup
```bash
# Set OpenRouter API key
export OPENROUTER_API_KEY='your-api-key-here'
```

Or in R:
```r
Sys.setenv(OPENROUTER_API_KEY = 'your-api-key-here')
```

### Run Simulation
```bash
Rscript run_simulation_with_actions.R
```

---

## Output Files

### Automatic Outputs
- **`outputs/simulation_summary_TIMESTAMP.txt`** - Complete simulation narrative
- **`outputs/run_TIMESTAMP/period_X_assessment.json`** - Each period's assessment
- **`outputs/assessments.csv`** - Probability timeline
- **`outputs/simulation_state.rds`** - Complete state for analysis
- **`data/interactions/period_N/*.json`** - Full interaction logs
- **`data/agent_states/*.csv`** - Agent position evolution
- **`data/networks/*.csv`** - Interaction network data

### Human Forecasting Outputs
- **`outputs/forecasting_prompts_true.txt`** - TRUE condition prompts (actual simulation dynamics)
- **`outputs/forecasting_prompts_control.txt`** - CONTROL condition prompts (randomized for validation)
- **`outputs/forecasting_answer_key.txt`** - LLM forecasts for comparison
- **`outputs/forecasting_template.csv`** - Data entry template for both conditions

**NEW in v3.2:** Control condition generation for experimental validation
- Tests whether forecasters can distinguish signal from noise
- Three-layer constrained randomization (metrics, events, probabilities)
- See `CONTROL_CONDITION_GUIDE.md` for detailed methodology

---

## Analysis

### Load and Analyze Results
```r
source("src/analysis.R")

# Analyze completed simulation
analyze_simulation("outputs")

# Generates:
# - probability_timeline.png
# - network_period_X.png
# - transcripts.txt
# - Summary statistics
```

### Compare LLM vs Human Forecasts
```r
source("src/forecast_prompts.R")

state <- readRDS("outputs/simulation_state.rds")

# Generate both TRUE and CONTROL condition prompts
files <- create_forecasting_worksheet(
  state,
  output_dir = "outputs",
  generate_control = TRUE
)

# Compare forecasts
human_true <- c(0.25, 0.30, 0.35, ...)  # Forecasts on true condition
human_control <- c(0.38, 0.42, 0.37, ...)  # Forecasts on control condition

comparison_true <- compare_forecasts(state, human_true)
print(comparison_true)

# Analyze control condition performance
mean_control_variance <- var(human_control)
base_rate <- 0.35
# Low variance near base rate indicates proper signal/noise discrimination
```

---

## Key Features

### Cognitive Framework
- **Worldviews** shape how agents interpret information (realist sees threats, liberal sees cooperation opportunities)
- **Deception mechanics** allow agents to lie or mislead based on capacity vs. target's analytical ability
- **Information asymmetry** - intelligence directors see everything, opposition leaders see little
- **Trust dynamics** - deception damages relationships, cooperation builds trust

### Action System
- **Probabilistic outcomes** - Success rates based on capabilities, force ratios, information access
- **Cascading effects** - Actions affect GDP, military strength, territory, crisis level
- **Attrition modeling** - Combat reduces capabilities over time
- **Economic costs** - Military actions drain GDP
- **Detection risk** - Covert operations can be exposed with diplomatic consequences
- **Action repetition tracking** (v3.6) - Diminishing returns for repeated actions
  - Peace talks: -15% base probability per attempt (floor 10%)
  - Tracks attempt count in `state$peace_talks_count`
  - Simulates entrenchment and credibility erosion

### External Actor Drift (v3.6)
- **Dynamic alignment** - External actors can shift positions based on conflict developments
- **Drift parameters** per actor:
  - `base_alignment`: pro_tethys, pro_novaris, neutral, neutral_humanitarian
  - `alignment_strength`: 0-1 (higher = more stable)
  - `drift_sensitivity`: 0-1 (higher = more responsive)
- **Drift triggers**:
  - Crisis level ≥9: +0.10
  - Territory >15%: +0.15 (galvanizes support)
  - Sanctions >60%: -0.10 for pro-Novaris actors
  - Nuclear use: +0.30 (major shock)
  - Atrocities: +0.10
  - Military victories: ±0.05
  - Economic pressure: -0.05
- **Drift calculation**: `magnitude = |score| × sensitivity × (1 - strength)`
- **Directions**: more_assertive, more_accommodating, stable
- **Examples**:
  - Meridian may reduce support if Tethys repeatedly fails
  - Aurelia may abandon neutrality after atrocities
  - Valkoria may distance from Novaris under heavy sanctions

### State Tracking
```r
state$scenario_state <- list(
  crisis_level = 0-10,
  military_balance = -1 to 1,
  sanctions_level = 0-1,
  territory_controlled = 0-1,
  nuclear_used = TRUE/FALSE
)

state$faction_capabilities <- list(
  major_power_military = 0.6-2.0,
  small_power_military = 0.3-1.0,
  major_power_gdp = 50-150B,
  small_power_gdp = 15-50B
)
```

---

## Research Applications

### Forecasting Accuracy
- Compare LLM aggregator forecasts to human expert predictions
- Test calibration (are probability estimates accurate?)
- Measure information processing (how do forecasts update with new data?)
- **NEW:** Control condition tests overfitting and signal/noise discrimination
  - Do forecasters maintain predictions when information is randomized?
  - Can they distinguish genuine patterns from noise?
  - See `CONTROL_CONDITION_GUIDE.md` for methodology

### Agent Dynamics
- How do internal faction disagreements affect outcomes?
- Do hawks vs. doves produce different trajectories?
- Can economic advisors restrain military hawks?

### Action Effectiveness
- Do covert operations achieve goals better than open conflict?
- Can economic sanctions prevent military escalation?
- How effective is diplomacy after violence begins?

### Worldview Effects
- Do realists choose military actions more often?
- Do liberals prefer economic/diplomatic tools?
- How do worldviews interact with hawk/dove orientation?

### Escalation Dynamics
- What triggers nuclear threshold crossing?
- Can conflicts de-escalate after major violence?
- Do military buildups cause preemptive attacks?

### Pre-Invasion Dynamics (v3.6)
- Run `pre_invasion` scenario to test whether LLMs choose war or peace
- Measure factors leading to escalation vs. diplomatic resolution
- Compare agent decision-making before vs. after conflict starts
- Test preventive diplomacy effectiveness

### External Actor Drift (v3.6)
- How do external actors respond to atrocities vs. military victories?
- Does economic pressure cause alignment shifts?
- Can neutral powers be pulled into conflicts?
- Do allies remain committed when their side is losing?

### Action Repetition Effects (v3.6)
- How many peace talks attempts before agents give up?
- Does diminishing effectiveness lead to earlier use of force?
- Can repeated failures paradoxically increase escalation?

---

## Customization

### Modify Agent Personas
Edit `config.R`:
```r
AGENTS$major_economic_advisor$hawk_dove <- 0.1  # Make more dovish
AGENTS$major_economic_advisor$objective_alignment <- 0.2  # Reduce alignment
```

### Add New Events
```r
EXTERNAL_EVENTS <- c(EXTERNAL_EVENTS, list(
  list(
    type = "cyber_attack",
    name = "Major Cyber Attack",
    probability = 0.15,
    impact = "Critical infrastructure disrupted"
  )
))
```

### Change Simulation Length
```r
N_PERIODS <- 15  # 15 periods = 105 days (default is 10 periods)
```

---

## Troubleshooting

### API Key Issues
```r
# Verify key is set
Sys.getenv("OPENROUTER_API_KEY")
```

### Memory Issues
- Reduce `N_PERIODS` in config.R
- Set `SAVE_FULL_TRANSCRIPTS <- FALSE`

### Wrong Script Executed
- Make sure you're running `run_simulation_with_actions.R`
- NOT `run_simulation.R` or `run_enhanced_simulation.R` (archived)

### Actions Not Executing
- Check console output for "Action Decision & Execution Phase"
- Verify `src/enhanced_action_space.R` is loaded
- Check that scenario context mentions "ACTIVE WARFARE"

---

## Version History

### v3.6 (Current) - January 2026
- ✅ **Pre-invasion scenario** - Emergent conflict option where invasion hasn't occurred yet
- ✅ **External actor drift mechanics** - Alignments shift based on crisis, territory, atrocities, nuclear use, economics
- ✅ **Action repetition tracking** - Diminishing returns for repeated peace_talks (and extensible to other actions)
- ✅ Drift parameters for all 4 external actors (Meridian, Valkoria, Aurelia, International Org)
- ✅ Crisis-responsive drift triggers (crisis ≥9, territory >15%, sanctions >60%, nuclear use)
- ✅ Event-responsive drift (atrocities, military victories, economic pressure)

### v3.2 - January 2026
- ✅ Full 49-action execution system
- ✅ Complete cognitive framework (worldviews, deception, rationality)
- ✅ Pre-action coordination (agents discuss before deciding actions)
- ✅ Independent external actors (4 separate factions, not 1 coordinated group)
- ✅ Guaranteed diplomatic engagement (all external actors engage every period)
- ✅ Configurable scenario presets
- ✅ Human forecasting prompt generation (TRUE condition)
- ✅ **NEW:** Control condition generation for experimental validation
  - Three-layer constrained randomization
  - Tests overfitting and signal/noise discrimination
  - Previous LLM probability removed from human prompts (now binary outcome only)
- ✅ Comprehensive state tracking

### v2.0 (Archived) - December 2025
- Cognitive framework added (worldviews, deception)
- No action execution (agents discuss only)
- Basic 27-action taxonomy (not executable)

### v1.0 (Archived) - November 2025
- Basic 11-agent system
- Simple personas (hawk/dove, policy adherence)
- Interaction engine
- Aggregator assessments

---

## Getting Help

1. **Check this guide first** - Authoritative current documentation
2. **See ACTION_EXECUTION_GUIDE.md** - Detailed action reference
3. **See SCENARIO_CONFIGURATION.md** - Scenario setup
4. **Check archived docs** in `archive/documentation/` for historical reference
5. **Examine outputs** in `outputs/simulation_summary_*.txt` for detailed logs

---

## File Locations

**Current Working Directory:** `D:\Northeastern\LLM_Forecasting`

**Key Directories:**
- `src/` - All source code
- `outputs/` - Simulation results
- `data/` - Interaction logs, agent states, networks
- `archive/` - Deprecated files (for reference)

**Run the simulation:**
```bash
cd D:\Northeastern\LLM_Forecasting
Rscript run_simulation_with_actions.R
```

---

**This is the authoritative guide to the current system. All other documentation is either supplementary or archived.**
