# Archive Index

**Created:** January 2026
**Purpose:** Document archived files for historical reference

This directory contains **deprecated files** that have been superseded by current implementations. These files are preserved for reference but should **NOT** be used in active development.

---

## Why These Files Were Archived

The project evolved through three major versions:
- **v1.0** (Nov 2025): Basic 11-agent system with simple personas
- **v2.0** (Dec 2025): Added cognitive framework (worldviews, deception)
- **v3.0** (Jan 2026): **CURRENT** - Full action execution system with 49 concrete actions

Archived files represent earlier versions that are no longer the recommended implementation.

---

## Archived Source Files

### `archive/src/action_space.R`
- **Date Archived:** January 2026
- **Replaced By:** `src/enhanced_action_space.R`
- **Reason:** Original 27-action taxonomy based on Rivera et al. (2024) paper
  - Simple escalation scoring (2^x - 4)
  - Actions were categorical, not executable
  - No state updates or probabilistic outcomes
- **Current System:** 49 executable actions with real consequences across 7 categories
- **Keep For:** Historical reference, research comparing action taxonomies

### `archive/src/agent_system.R`
- **Date Archived:** January 2026
- **Replaced By:** `src/integrated_agent_system.R`
- **Reason:** Basic agent creation without cognitive features
  - Only hawk/dove, policy adherence, objective alignment
  - No worldviews, deception mechanics, or rationality traits
  - No information asymmetry modeling
- **Current System:** Full cognitive framework with worldviews, deception capacity/willingness, analytical ability, information access
- **Keep For:** Understanding evolution from simple to complex agents

### `archive/src/simulation.R`
- **Date Archived:** January 2026
- **Replaced By:** `src/simulation_with_actions.R`
- **Reason:** Original simulation loop without action execution
  - Agents only discuss strategies
  - No concrete actions with state effects
  - No GDP, military strength, or territory tracking
- **Current System:** Full action execution with probabilistic outcomes and state updates
- **Keep For:** Comparison of discussion-only vs action-based simulations

---

## Archived Run Scripts

### `archive/run_scripts/run_simulation.R`
- **Date Archived:** January 2026
- **Replaced By:** `run_simulation_with_actions.R`
- **Reason:** Basic mode entry point
  - Uses `src/agent_system.R` (basic agents)
  - Uses `src/simulation.R` (no actions)
  - No cognitive framework
- **Current System:** Full cognitive + action system
- **Keep For:** Running basic simulations for comparison studies

### `archive/run_scripts/run_enhanced_simulation.R`
- **Date Archived:** January 2026
- **Replaced By:** `run_simulation_with_actions.R`
- **Reason:** Intermediate state (v2.0)
  - Had cognitive framework (worldviews, deception)
  - Used `src/simulation.R` (no action execution)
  - Incomplete feature set
- **Current System:** Combines cognitive framework + action execution
- **Keep For:** Understanding intermediate development state

---

## Archived Documentation

### General Documentation

#### `archive/documentation/PROJECT_SUMMARY.md`
- **Date:** November 2025
- **Content:** High-level project overview from v1.0
- **Obsolete Because:** Doesn't mention action execution or cognitive framework
- **Current Version:** `CURRENT_SYSTEM_GUIDE.md`

#### `archive/documentation/SYSTEM_SUMMARY.md`
- **Date:** November 2025
- **Content:** Technical architecture summary for v1.0
- **Obsolete Because:** Missing v2.0 and v3.0 features
- **Current Version:** `CURRENT_SYSTEM_GUIDE.md`

#### `archive/documentation/ORIGINAL_FEATURES_PRESERVED.md`
- **Date:** December 2025
- **Content:** Explains what was kept from v1.0 when adding v2.0 cognitive features
- **Obsolete Because:** Transitional documentation between versions
- **Current Version:** Features are documented in `CURRENT_SYSTEM_GUIDE.md`

#### `archive/documentation/QUICKSTART.md`
- **Date:** November 2025
- **Content:** Generic quickstart for v1.0
- **Obsolete Because:** References wrong entry point (`run_simulation.R`)
- **Current Version:** Quick start section in `README.md` and `CURRENT_SYSTEM_GUIDE.md`

### Action System Documentation

#### `archive/documentation/ACTION_SPACE_GUIDE.md`
- **Date:** December 2025
- **Content:** Documents original 27-action taxonomy
- **Obsolete Because:** Describes old, non-executable action system
- **Current Version:** `ACTION_EXECUTION_GUIDE.md` (49 executable actions)

#### `archive/documentation/ACTIONS_IMPLEMENTED.md`
- **Date:** January 2026
- **Content:** Implementation status for action execution system
- **Obsolete Because:** Partial implementation notes, superseded by complete guide
- **Current Version:** `ACTION_EXECUTION_GUIDE.md`

### Cognitive Framework Documentation

#### `archive/documentation/ENHANCED_FEATURES_GUIDE.md`
- **Date:** December 2025
- **Content:** How worldviews and deception work (v2.0)
- **Obsolete Because:** Standalone guide for cognitive features only
- **Current Version:** Integrated into `CURRENT_SYSTEM_GUIDE.md`

#### `archive/documentation/RATIONALITY_DESIGN.md`
- **Date:** December 2025
- **Content:** Design document for rationality traits (bounded rationality, loss aversion, etc.)
- **Obsolete Because:** Design-phase documentation
- **Current Version:** Features documented in `CURRENT_SYSTEM_GUIDE.md`

#### `archive/documentation/RATIONALITY_IMPLEMENTATION_COMPLETE.md`
- **Date:** December 2025
- **Content:** Implementation status for rationality features
- **Obsolete Because:** Status update, no longer needed
- **Current Version:** Features documented in `CURRENT_SYSTEM_GUIDE.md`

#### `archive/documentation/INTEGRATION_EXAMPLE.md`
- **Date:** December 2025
- **Content:** How to integrate cognitive enhancements with original system
- **Obsolete Because:** Integration complete, no longer separate systems
- **Current Version:** `CURRENT_SYSTEM_GUIDE.md`

### Forecasting Documentation

#### `archive/documentation/FORECASTING_FEATURE_SUMMARY.md`
- **Date:** December 2025
- **Content:** Human forecasting feature overview
- **Obsolete Because:** Partial feature description
- **Current Version:** Section in `CURRENT_SYSTEM_GUIDE.md`

#### `archive/documentation/FORECASTING_QUICKSTART.md`
- **Date:** December 2025
- **Content:** Quick guide to forecasting features
- **Obsolete Because:** Redundant with README and main guide
- **Current Version:** Forecasting section in `README.md` and `CURRENT_SYSTEM_GUIDE.md`

#### `archive/documentation/FORECASTING_EXAMPLE.md`
- **Date:** December 2025
- **Content:** Detailed forecasting workflow examples
- **Obsolete Because:** Standalone example, now integrated
- **Current Version:** Section in `README.md`

### Bug Fixes and Change Logs

#### `archive/documentation/CHANGES.md`
- **Date:** December 2025
- **Content:** List of model updates and configuration changes
- **Obsolete Because:** Incremental change log, no longer maintained
- **Current Version:** Version history in `CURRENT_SYSTEM_GUIDE.md`

#### `archive/documentation/BUGFIX_agent_id_persistence.md`
- **Date:** December 2025
- **Content:** Documents specific bug fix for agent ID persistence
- **Obsolete Because:** Specific issue resolution, bug is fixed
- **Current Version:** N/A (bug resolved)

#### `archive/documentation/FIXED_ISSUES.md`
- **Date:** December 2025
- **Content:** List of resolved issues
- **Obsolete Because:** Historical issue tracking
- **Current Version:** N/A (issues resolved)

#### `archive/documentation/TROUBLESHOOTING.md`
- **Date:** December 2025
- **Content:** Common problems and solutions for earlier versions
- **Obsolete Because:** References old file structure and scripts
- **Current Version:** Troubleshooting section in `CURRENT_SYSTEM_GUIDE.md`

---

## When to Use Archived Files

### Research and Comparison
- **Comparing action taxonomies:** Use `archive/src/action_space.R` to see original 27-action framework
- **Testing simpler models:** Use `archive/run_scripts/run_simulation.R` for basic agent-only simulations
- **Ablation studies:** Remove cognitive features by using v1.0 components

### Understanding Project Evolution
- **See design decisions:** Read `RATIONALITY_DESIGN.md` for cognitive framework rationale
- **Understand integration:** Read `INTEGRATION_EXAMPLE.md` for how features were combined
- **Track bug fixes:** Review `BUGFIX_*.md` files for specific issues encountered

### Backwards Compatibility
- **Reproduce earlier results:** Use archived scripts to match previous simulation runs
- **Compare versions:** Run same scenario on v1.0, v2.0, v3.0 to measure feature impact

---

## Current Active Files

**DO NOT use archived files for active development. Use these instead:**

### Entry Points
- ✅ `run_simulation_with_actions.R` - Main entry point (v3.0)

### Documentation
- ✅ `CURRENT_SYSTEM_GUIDE.md` - Authoritative current documentation
- ✅ `ACTION_EXECUTION_GUIDE.md` - Complete action reference
- ✅ `SCENARIO_CONFIGURATION.md` - Scenario setup
- ✅ `README.md` - Project overview
- ✅ `CLAUDE.md` - Project context for Claude AI

### Source Code
- ✅ `src/integrated_agent_system.R` - Cognitive framework
- ✅ `src/enhanced_action_space.R` - 49-action system
- ✅ `src/action_execution.R` - Action execution and state updates
- ✅ `src/agent_decision.R` - Agent action selection
- ✅ `src/simulation_with_actions.R` - Main simulation loop
- ✅ All other files in `src/` not archived

---

## Archive Structure

```
archive/
├── src/                              # Deprecated source code
│   ├── action_space.R                # 27-action taxonomy (replaced)
│   ├── agent_system.R                # Basic agents (replaced)
│   └── simulation.R                  # No-action simulation (replaced)
├── run_scripts/                      # Deprecated entry points
│   ├── run_simulation.R              # v1.0 basic mode
│   └── run_enhanced_simulation.R     # v2.0 intermediate state
└── documentation/                    # Deprecated documentation
    ├── ACTION_SPACE_GUIDE.md         # Old action taxonomy
    ├── ENHANCED_FEATURES_GUIDE.md    # v2.0 cognitive features
    ├── RATIONALITY_DESIGN.md         # Design docs
    ├── INTEGRATION_EXAMPLE.md        # Integration guide
    ├── FORECASTING_*.md              # Forecasting docs (3 files)
    ├── ORIGINAL_FEATURES_PRESERVED.md
    ├── PROJECT_SUMMARY.md
    ├── SYSTEM_SUMMARY.md
    ├── QUICKSTART.md
    ├── ACTIONS_IMPLEMENTED.md
    ├── CHANGES.md
    ├── BUGFIX_agent_id_persistence.md
    ├── FIXED_ISSUES.md
    ├── TROUBLESHOOTING.md
    └── RATIONALITY_IMPLEMENTATION_COMPLETE.md
```

---

## Questions?

- **"Can I use archived files?"** - Yes, for research comparison or understanding project history
- **"Are archived files maintained?"** - No, they are frozen at archival date
- **"Will archived files work?"** - Possibly, but they may have unresolved bugs or missing dependencies
- **"Should I reference archived docs?"** - Only for historical context; use `CURRENT_SYSTEM_GUIDE.md` for current features

---

**For current system documentation, always refer to `CURRENT_SYSTEM_GUIDE.md`**
