# Documentation Index

**Current Version:** v3.6 - Cross-Expertise & External Observer Forecasting

---

## 🚀 Getting Started

**New to this project?** Start here:

1. **[START_HERE.md](START_HERE.md)** - Quickest path to running simulations
2. **[README.md](README.md)** - Project overview and setup
3. **[CLAUDE.md](CLAUDE.md)** - For AI assistants working on this project

---

## 📚 Core Documentation

### System Understanding
- **[CURRENT_SYSTEM_GUIDE.md](CURRENT_SYSTEM_GUIDE.md)** - Comprehensive system overview
  - 11-agent architecture
  - Cognitive frameworks (worldviews, deception, trust)
  - Action execution system (49 actions)
  - All v3.6 features

- **[CODE_STRUCTURE.md](CODE_STRUCTURE.md)** - Codebase organization guide
  - File purposes and dependencies
  - Modification guide
  - Active vs archived files

### Configuration & Scenarios
- **[SCENARIO_CONFIGURATION.md](SCENARIO_CONFIGURATION.md)** - All scenarios and mechanics
  - Pre-invasion scenario (Scenario 0)
  - Limited incursion, full invasion, occupation scenarios
  - External actor drift mechanics
  - Action repetition diminishing returns

### Version History
- **[VERSION_CHANGELOG.md](VERSION_CHANGELOG.md)** - All versions from v1.0 to v3.6

---

## 🎮 Feature Guides

### Action System
- **[ACTION_EXECUTION_GUIDE.md](ACTION_EXECUTION_GUIDE.md)** - How actions work
  - 49 actions across 7 categories
  - Success probabilities
  - State consequences

### Decision Making
- **[PRE_ACTION_COORDINATION.md](PRE_ACTION_COORDINATION.md)** - How agents coordinate
  - Round 1: Individual recommendations
  - Round 2: Deliberation and consensus
  - Final decision synthesis
  - **NEW in v3.6:** Cross-expertise prompts

### External Actors
- **[INDEPENDENT_EXTERNAL_ACTORS.md](INDEPENDENT_EXTERNAL_ACTORS.md)** - External actor system
- **[GUARANTEED_EXTERNAL_ENGAGEMENT.md](GUARANTEED_EXTERNAL_ENGAGEMENT.md)** - Action selection rules

### Forecasting
- **[CONTROL_CONDITION_GUIDE.md](CONTROL_CONDITION_GUIDE.md)** - Forecasting experiments
  - TRUE vs CONTROL conditions
  - **NEW in v3.6:** External observer vs full-info prompts

---

## 🔧 Implementation Details (v3.6)

### Cross-Expertise Implementation
**File:** `src/interaction_engine.R` (lines 823-854)

**Change:** Agents can now recommend actions outside their traditional domain.

**Key language added to Round 1 prompts:**
```
You bring [ROLE] EXPERTISE to this decision, but you can recommend ANY action.

EXPERTISE DOES NOT MEAN CONSTRAINT:
- A military expert CAN recommend diplomacy (if force has diminishing returns)
- An economic expert CAN recommend strikes (if decisive action costs less)
- A diplomat CAN recommend covert ops (if it creates leverage)
```

**Expected impact:**
- Action diversity: 14 → 25-35 unique actions
- Cross-expertise rate: 0% → 15-20%

### External Observer Forecasting
**File:** `src/forecast_prompts_external_observer_v36.R`

**Purpose:** Generate realistic forecasting prompts matching human information constraints.

**Key functions:**
- `is_action_publicly_observable()` - Filters covert ops
- `describe_action_externally()` - Translates to public descriptions
- `generate_analyst_commentary()` - Adds external analysis
- `generate_forecast_prompt_external()` - Creates prompts

**Hides:** Internal coordination, successful covert ops, classified intelligence
**Shows:** Public actions, observable metrics, analyst commentary, detected covert ops

**Usage:**
```r
source("src/forecast_prompts_external_observer_v36.R")
state <- readRDS("outputs/simulation_state.rds")
prompts <- generate_all_forecast_prompts_external(state,
  output_file = "outputs/forecasting_prompts_EXTERNAL_OBSERVER.txt")
```

---

## 📊 Analysis & Results

### Latest Simulation Results
- **[simulation_analysis_report.md](simulation_analysis_report.md)** - Most recent run analysis
  - Baseline (pre-v3.6) results
  - Action diversity: 14/49 actions
  - Collapse probability trajectory: 30% → 18% → 55%

### Testing
- **[test_v36_implementations.R](test_v36_implementations.R)** - Automated tests
  - Cross-expertise prompts
  - External observer filtering
  - Observability rules

---

## 📦 Archived Documentation

Older implementation guides and version-specific docs are in:
- **[archive/](archive/)** - Historical documentation
- **[ARCHIVE_INDEX.md](ARCHIVE_INDEX.md)** - Archive contents

Archived in this cleanup:
- v3.6 delivery summaries (consolidated above)
- v3.2 implementation guides
- Historical bug fixes and troubleshooting

---

## 🗺️ Quick Reference

### Run Simulations
```bash
# Main simulation
Rscript run_simulation_with_actions.R

# Test v3.6 features
Rscript test_v36_implementations.R

# Generate external observer prompts
Rscript examples/generate_external_observer_prompts.R
```

### Key Files by Function

**Core Simulation:**
- `run_simulation_with_actions.R` - Main entry point
- `src/simulation_engine_with_actions.R` - Core loop
- `src/agent_decision.R` - Agent decision logic
- `src/interaction_engine.R` - Coordination system
- `src/action_execution.R` - Action effects

**Configuration:**
- `config.R` - All settings (scenarios, API, agents)

**Analysis:**
- `src/forecast_prompts.R` - Full-info forecasting (original)
- `src/forecast_prompts_external_observer_v36.R` - External observer (v3.6)
- `compare_forecasts.R` - Compare LLM vs human forecasts

---

## ❓ Common Questions

### Which scenario should I use?
- **Scenario 0 (Pre-invasion):** Emergence dynamics, invasion may/may not happen
- **Scenario 1 (Limited incursion):** 2-5% territory, moderate crisis
- **Scenario 2 (Full invasion):** 8-15% territory, high crisis
- **Scenario 3 (Occupation):** 20-35% territory, maximum crisis

### How do I enable cross-expertise?
It's already enabled in v3.6! Check `src/interaction_engine.R` lines 823-854.

### How do I generate human-realistic forecasting prompts?
Use `examples/generate_external_observer_prompts.R` after running a simulation.

### Where are the 49 actions defined?
See `src/enhanced_action_space_v36.R` for strategic direction mappings, or `ACTION_EXECUTION_GUIDE.md` for full action descriptions.

---

## 📝 Contributing

When adding new features:
1. Update relevant section in **CURRENT_SYSTEM_GUIDE.md**
2. Add entry to **VERSION_CHANGELOG.md**
3. Update this index if adding new documentation
4. Archive old implementation guides to `archive/`

---

**Last updated:** 2026-01-31 (v3.6 release)
