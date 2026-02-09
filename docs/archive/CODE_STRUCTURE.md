# Codebase Structure Guide

**Version:** 3.6 | **Last Cleanup:** 2026-01-31

This document explains the organization and purpose of all active code files.

---

## 📂 Directory Structure

```
LLM_Forecasting/
├── config.R                                  # Central configuration
├── run_simulation_with_actions.R            # ✅ MAIN ENTRY POINT
├── run_single_period_collapse_test.R        # Single-period test script
├── compare_forecasts.R                      # Compare LLM vs human forecasts
├── src/                                     # Source code
│   ├── Core Simulation
│   │   ├── simulation_with_actions.R        # Main simulation loop
│   │   ├── agent_system.R                   # Basic agent structures
│   │   ├── integrated_agent_system.R        # Cognitive frameworks (worldviews, deception, trust)
│   │   ├── event_generator.R                # External events and shocks
│   │   └── state_manager.R                  # State tracking and logging
│   ├── Decision Making
│   │   ├── agent_decision.R                 # Action selection via LLM
│   │   ├── interaction_engine.R             # Agent coordination (v3.6: cross-expertise)
│   │   └── aggregator.R                     # Probability assessment
│   ├── Action System
│   │   ├── action_execution.R               # Execute actions, update state
│   │   ├── action_space.R                   # Legacy action definitions
│   │   ├── enhanced_action_space.R          # 49-action system
│   │   └── enhanced_action_space_v36.R      # Strategic direction mappings
│   ├── Forecasting
│   │   ├── forecast_prompts.R               # Full-info prompts (original)
│   │   ├── forecast_prompts_external_observer_v36.R  # External observer prompts (v3.6)
│   │   └── control_condition.R              # Control condition generation
│   ├── Utilities
│   │   ├── fictionalized_scenarios.R        # Named countries, scenario generation
│   │   ├── scenario_backstories.R           # Agent backstories
│   │   ├── strategic_direction_functions.R  # Two-stage decision helpers (not yet integrated)
│   │   └── analysis.R                       # Visualization and analysis
│   └── archive/                             # Archived/deprecated code
├── examples/
│   └── generate_external_observer_prompts.R # Usage example for v3.6
├── outputs/                                 # Simulation results
│   ├── simulation_state.rds
│   ├── assessments.csv
│   ├── simulation_summary_*.txt
│   └── forecasting_prompts_*.txt
└── archive/                                 # Archived documentation & code
    ├── v3.6_implementation/                 # Implementation docs
    └── src_deprecated/                      # Deprecated source files
```

---

## 🎯 Active Files by Purpose

### Entry Points

| File | Purpose | When to Use |
|------|---------|-------------|
| **run_simulation_with_actions.R** | Main simulation with full action execution | Primary entry point |
| run_single_period_collapse_test.R | Test single period execution | Debugging/testing |
| compare_forecasts.R | Compare LLM vs human forecasts | After collecting human data |

### Core Simulation Loop

**File:** `src/simulation_with_actions.R`
- Main simulation loop across periods
- Calls: event generation → coordination → decision → action execution → assessment
- **Dependencies:** agent_system.R, event_generator.R, interaction_engine.R, aggregator.R, state_manager.R, agent_decision.R, action_execution.R

### Agent Systems

**1. Basic Agent Structures**
- **File:** `src/agent_system.R`
- **Purpose:** Agent data structures (name, role, faction)
- **Used by:** simulation_with_actions.R

**2. Cognitive Frameworks**
- **File:** `src/integrated_agent_system.R`
- **Purpose:** Worldviews, deception mechanics, trust dynamics, information access
- **Used by:** run_simulation_with_actions.R (loaded first)
- **Key functions:**
  - `create_enhanced_agent()` - Adds cognitive traits
  - `calculate_deception_success()` - Deception mechanics
  - `update_trust()` - Trust erosion/building

### Decision Making

**1. Coordination** (v3.6: Cross-Expertise)
- **File:** `src/interaction_engine.R`
- **Purpose:** Intra-faction coordination
  - Round 1: Individual recommendations (lines 823-854: cross-expertise prompts)
  - Round 2: Deliberation and consensus
  - Final: Decision synthesis
- **Key change in v3.6:** Agents can recommend outside their traditional domain

**2. Action Selection**
- **File:** `src/agent_decision.R`
- **Purpose:** Agents choose specific actions via LLM
- **Includes:** External actor alignment drift calculations

**3. Probability Assessment**
- **File:** `src/aggregator.R`
- **Purpose:** LLM evaluates collapse probability each period

### Action System

**1. Action Execution**
- **File:** `src/action_execution.R`
- **Purpose:** Execute actions, calculate success, update state
- **Includes:**
  - Success probability calculation
  - State consequences (GDP, military, territory changes)
  - Action repetition tracking (peace_talks diminishing returns)

**2. Action Space Definitions**

| File | Purpose | Status |
|------|---------|--------|
| action_space.R | Legacy action definitions | Active (loaded by integrated_agent_system.R) |
| enhanced_action_space.R | 49-action system definitions | Active (loaded by various files) |
| enhanced_action_space_v36.R | Strategic direction mappings | Active (for two-stage decision - not yet integrated) |

**Note:** Multiple action_space files exist for backward compatibility. Consolidation planned but requires careful dependency checking.

### Forecasting & Analysis

**1. Forecasting Prompt Generation**

| File | Purpose | When to Use |
|------|---------|-------------|
| forecast_prompts.R | Full-info prompts | Original system, shows internal coordination |
| **forecast_prompts_external_observer_v36.R** | External observer prompts | **Recommended for humans** (realistic info constraints) |

**2. Control Conditions**
- **File:** `src/control_condition.R`
- **Purpose:** Generate control vs treatment forecasting conditions

**3. Analysis**
- **File:** `src/analysis.R`
- **Purpose:** Visualization, statistics, network analysis

### Events & Scenarios

**1. External Events**
- **File:** `src/event_generator.R`
- **Purpose:** Generate battlefield shifts, economic shocks, diplomatic developments, wild cards

**2. Scenario Generation**
- **File:** `src/fictionalized_scenarios.R`
- **Purpose:** Named countries (Novaris, Tethys, Meridian, etc.), dynamic situation descriptions

**3. Agent Backstories**
- **File:** `src/scenario_backstories.R`
- **Purpose:** Agent personalities, backgrounds, motivations

### Utilities

**1. State Management**
- **File:** `src/state_manager.R`
- **Purpose:** Logging, state tracking, data persistence

**2. Strategic Direction (Not Yet Integrated)**
- **File:** `src/strategic_direction_functions.R`
- **Purpose:** Two-stage decision process helpers
- **Status:** Created but not integrated into main flow
- **Future use:** Reduce cognitive load (49 actions → 8-12 filtered options)

---

## 🔗 Dependency Chain

```
run_simulation_with_actions.R
├── config.R
├── src/integrated_agent_system.R
│   └── src/action_space.R (indirectly)
└── src/simulation_with_actions.R
    ├── src/agent_system.R
    ├── src/event_generator.R
    ├── src/interaction_engine.R (v3.6: cross-expertise)
    ├── src/aggregator.R
    ├── src/state_manager.R
    ├── src/agent_decision.R
    └── src/action_execution.R
        └── src/enhanced_action_space.R (indirectly)
```

---

## 🔧 Key Configuration Points

### config.R Sections

1. **API Configuration** (lines 1-10)
   - OpenRouter API key
   - Model selection (qwen/qwen3-235b-a22b-2507)

2. **Scenario Presets** (lines 20-80)
   - **pre_invasion** - Scenario 0 (no invasion yet)
   - **low_intensity** - Scenario 1 (2-5% territory)
   - **medium_intensity** - Scenario 2 (8-15% territory)
   - **high_intensity** - Scenario 3 (20-35% territory)

3. **Agent Definitions** (lines 100-300)
   - 11 agents with roles, worldviews, cognitive traits

4. **External Actor Drift Parameters** (lines 489-634)
   - Alignment shift triggers for Meridian, Valkoria, Aurelia, Int'l Org

---

## 📝 Modification Guide

### To Enable Pre-Invasion Scenario

**File:** `run_simulation_with_actions.R`

Find (around line 80):
```r
simulation_state <- initialize_simulation_with_actions(
  agents = config$agents,
  n_periods = 10,
  scenario_preset = "low_intensity"  # ← Change this
)
```

Change to:
```r
scenario_preset = "pre_invasion"
```

### To Modify Cross-Expertise Prompts

**File:** `src/interaction_engine.R` (lines 823-854)

The cross-expertise language is in the Round 1 prompt generation. Look for:
```r
sprintf("You bring %s EXPERTISE to this decision, but you can recommend ANY action...")
```

### To Add New Actions

1. **Define action:** `src/enhanced_action_space.R`
2. **Add execution logic:** `src/action_execution.R`
3. **Add to strategic mappings:** `src/enhanced_action_space_v36.R` (if using two-stage)

### To Change External Observer Filtering

**File:** `src/forecast_prompts_external_observer_v36.R`

Key functions:
- `is_action_publicly_observable()` - Controls what's visible
- `describe_action_externally()` - Translates actions to public descriptions

---

## 🗑️ Archived Files

### Recently Archived (2026-01-31)

**Documentation:**
- `archive/v3.6_implementation/` - All v3.6 delivery summaries and guides
- `archive/IMPLEMENTATION_SUMMARY_v3.2.md`
- `archive/CLEANUP_SUMMARY.md`

**Code:**
- `archive/src_deprecated/simulation.R` - Old simulation without actions

**Why archived:** Superseded by current versions or consolidated into main documentation

---

## ❓ Common Questions

### Why do both agent_system.R and integrated_agent_system.R exist?
- **agent_system.R:** Basic agent data structures
- **integrated_agent_system.R:** Adds cognitive frameworks (worldviews, deception, trust)
- Both are active - integrated_agent_system.R extends agent_system.R
- **Future:** Could consolidate, but requires careful testing

### Why multiple action_space files?
- **action_space.R:** Legacy definitions, still referenced
- **enhanced_action_space.R:** Current 49-action system
- **enhanced_action_space_v36.R:** Strategic direction mappings (for two-stage decision)
- **Future:** Consolidate once all dependencies are mapped

### Is forecast_prompts_external_observer_v36.R actually used?
- Yes! It's a standalone module for generating external observer prompts
- Usage: `Rscript examples/generate_external_observer_prompts.R`
- Not loaded by main simulation (it processes simulation results afterward)

### What's the difference between simulation.R and simulation_with_actions.R?
- **simulation.R:** OLD - deprecated, no action execution
- **simulation_with_actions.R:** CURRENT - full action execution system
- simulation.R archived to `archive/src_deprecated/`

---

## 🔍 Finding Things

**Looking for:**
- **Action definitions?** → `src/enhanced_action_space.R`
- **How actions are executed?** → `src/action_execution.R`
- **Cross-expertise prompts?** → `src/interaction_engine.R` lines 823-854
- **External observer logic?** → `src/forecast_prompts_external_observer_v36.R`
- **Scenario configs?** → `config.R` lines 20-80
- **Agent cognitive traits?** → `src/integrated_agent_system.R`
- **Alignment drift?** → `config.R` lines 489-634 AND `src/agent_decision.R`

---

**Last updated:** 2026-01-31 (Post-cleanup)
