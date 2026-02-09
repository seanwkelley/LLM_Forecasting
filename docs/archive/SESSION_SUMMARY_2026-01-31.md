# Session Summary - January 31, 2026

## What We Were Working On

Testing **v3.6 cross-expertise implementation** to improve action diversity in the LLM wargame simulation.

**Goal:** Increase unique actions from baseline 14 to target 25-35 by allowing agents to recommend actions outside their traditional expertise (e.g., military experts can recommend diplomacy).

---

## Current Status: ❌ FAILED

### Three Test Runs - All Failed

| Run | Config | Unique Actions | Result |
|-----|--------|----------------|--------|
| **Baseline** | Low intensity, 10 periods | 14 | Reference point |
| **Test 1** | Pre-invasion, 10 periods | 10 | -29% (worse) |
| **Test 2** | Pre-invasion, 3 periods | 9 | -36% (worse) |
| **Test 3** | Pre-invasion, 3 periods, --vanilla | **5** | **-64% (much worse)** |

### The Problem

Cross-expertise prompts exist in code (`src/interaction_engine.R:823-854`) but **never reach the agents during execution**.

- ✅ Pre-run verification passes (finds prompts in function)
- ❌ Post-run verification fails (prompts not in actual messages)
- ❌ Agents receive OLD prompt format instead

**All three fix attempts failed:**
1. Added verification scripts
2. Cleared cached R functions with `rm()`
3. Ran with `--vanilla` flag for clean environment

**Root cause unknown.** Code path during execution appears to bypass our changes.

---

## Key Findings

1. **Action diversity got WORSE with each attempt**
   - Test 3: Only 5 unique actions out of 49 available (10% utilization)
   - Proxy_support dominance increased from 28% → 50%

2. **Pre-invasion scenario backfired**
   - Expected: More strategic freedom → more exploration
   - Actual: Less pressure → more conservative, repetitive choices

3. **Cognitive overload + role stereotyping confirmed**
   - Agents default to safe, familiar options
   - 49 actions → decision paralysis → repetition

---

## Next Steps - Alternative Approaches

Since cross-expertise implementation failed 3 times, we discussed trying:

### ⭐ Recommended: Option 1 - Direct Prompt Modification
- Inject cross-expertise language into **main action selection prompt** (not pre-action coordination)
- Simpler architecture, easier to verify

### Option 2 - Mechanical Diversity Enforcement
- Hard constraint: cannot repeat same action 2 periods in a row
- Guaranteed to force exploration

### Option 3 - Reduce Action Space
- Cut from 49 → 20-25 most relevant actions
- Eliminate cognitive overload

### Option 4 - Debug Code Path
- Add print statements throughout `interaction_engine.R`
- Trace where old prompts are coming from

### Option 5 - Simplify Agent Structure
- Combine roles to reduce coordination complexity

---

## Important Files & Locations

### Current Run Data
- **Latest results:** `D:\Northeastern\LLM_Forecasting\outputs\`
- **Summary:** `outputs\simulation_summary_20260131_184437.txt`
- **State file:** `outputs\simulation_state.rds`

### Documentation Created
- `V36_CROSS_EXPERTISE_TEST_RESULTS.md` - Detailed failure analysis
- `DOCS_INDEX.md` - Central documentation hub
- `CODE_STRUCTURE.md` - Codebase organization guide
- `ACTION_SPACE_ANALYSIS.md` - Why action space is limited
- `FACTION_OBJECTIVES.md` - Faction goals in pre-invasion scenario
- `SIMULATION_RUNS_INDEX.md` - Archive of all test runs

### Archived Runs
- `outputs_BASELINE_low_intensity_10periods/` - Reference baseline (14 unique actions)
- `outputs_V36_FAILED_preinvasion_10periods_no_cross_expertise/` - Test 1
- Previous numbered archives for earlier tests

### Key Code Files
- `src/interaction_engine.R` - Where cross-expertise prompts are (lines 823-854)
- `src/simulation_with_actions.R` - Main simulation loop
- `run_simulation_with_actions.R` - Entry point
- `config.R` - Configuration (currently: 3 periods, pre-invasion scenario)

### Verification Scripts
- `verify_cross_expertise_loaded_v2.R` - Pre-run check (passes)
- `verify_cross_expertise_used.R` - Post-run check (fails)

---

## Configuration Status

### Current Settings (config.R)
```r
N_PERIODS <- 3  # Changed from 10 for faster testing
SCENARIO_PRESET <- "pre_invasion"  # Changed from "low_intensity"
```

### To Reset to Baseline
```r
N_PERIODS <- 10
SCENARIO_PRESET <- "low_intensity"
```

---

## Quick Start Commands for Next Session

### To run baseline simulation
```bash
cd D:\Northeastern\LLM_Forecasting
Rscript run_simulation_with_actions.R
```

### To analyze latest results
```r
state <- readRDS("outputs/simulation_state.rds")
# Check action diversity
unique_actions <- unique(unlist(lapply(state$action_results, function(p) {
  sapply(p, function(a) a$action)
})))
length(unique_actions)
```

### To view documentation
```bash
cat D:\Northeastern\LLM_Forecasting\DOCS_INDEX.md
```

---

## Questions to Resolve

1. **Why are cross-expertise prompts not loading?**
   - Where is the actual prompt generation happening during execution?
   - Is there a compiled/cached version somewhere?

2. **Should we continue debugging or pivot to alternative approaches?**
   - 3 failed attempts suggest architectural issue
   - Mechanical constraints (Option 2) might be more reliable

3. **Is pre-invasion scenario the right test environment?**
   - Results suggest it reduces, not increases, creativity
   - Consider testing with low_intensity or high_intensity instead

---

## Bottom Line

**Cross-expertise implementation: 0/3 successful**
**Action diversity: Getting worse, not better**
**Next step: Try alternative approach (recommend Option 1 or 2)**

---

*Last updated: 2026-01-31 18:45*
*Session context preserved in: C:\Users\seanw\.claude\projects\C--Users-seanw\bb0d09e1-514c-4a53-9a75-3bd56334fd50.jsonl*
