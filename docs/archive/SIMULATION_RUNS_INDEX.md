# Simulation Runs Index

**Last Updated:** 2026-01-31 20:15

---

## ✅ V3.7 SUCCESS - Current Best Result

### outputs_V37_SUCCESS_preinvasion_3periods_cross_expertise_balanced/
**Status:** ✅ COMPLETE - **PARTIAL SUCCESS**
**Description:** Cross-expertise + Balanced scenario test (60% improvement!)
**Completed:** 2026-01-31 19:25-20:09 (40.8 minutes)
**Configuration:**
- Scenario: Pre-invasion (Multi-Domain Escalation Crisis - BALANCED)
- Periods: 3 (21 days)
- Cross-expertise: ✅ ENABLED in decision prompts
- Balanced scenario: ✅ Both powers have offensive/defensive options
- Purpose: Test combined fixes (cross-expertise + scenario rebalance)

**Results:**
- Unique actions: **8** (vs baseline 5) - **+60% improvement** ✅
- Dominant action: 28% proxy_support (vs 50%) - **reduced dominance** ✅
- Action space utilization: 16.3% (vs 10.2%) - **improved** ✅
- **Tethys offensive thinking:** 6 sabotage recommendations across 3 periods ✅
- Action diversity per period: **2.67 unique/period** (vs baseline 1.4)

**Status:** PARTIAL SUCCESS - significant improvement but below 15-20 action target

**Next:** Run 7-10 periods to hit target range

---

## ❌ Failed Attempts

### outputs_V37_FAILED_API_AUTH_20260131_180709/
**Status:** ❌ FAILED - API authentication
**Description:** Initial v3.7 attempt failed due to missing API key
**Failed:** 2026-01-31 18:07-18:12
**Issue:** Missing OPENROUTER_API_KEY environment variable
**Action:** Directory retained for reference but contains no useful data

---

## 📊 Key Comparison Runs

### outputs_BASELINE_low_intensity_10periods/
**Description:** Baseline simulation (pre-v3.6, no cross-expertise)
**Completed:** 2026-01-31 1:07 PM
**Configuration:**
- Scenario: Low intensity (limited incursion)
- Periods: 10 (70 days)
- Cross-expertise: ❌ Not implemented
- Runtime: 133.3 minutes

**Results:**
- Unique actions: 14 / 49 (29%)
- Most common: proxy_support (28%)
- Cross-expertise: 0%
- Narrative: 30% → 18% → 55% collapse probability

**Purpose:** Baseline for comparison

---

### outputs_V36_FAILED_preinvasion_10periods_no_cross_expertise/
**Description:** v3.6 test FAILED (cross-expertise not loaded)
**Completed:** 2026-01-31 4:47 PM
**Configuration:**
- Scenario: Pre-invasion
- Periods: 10 (70 days)
- Cross-expertise: ❌ Code existed but NOT loaded
- Runtime: 132.9 minutes

**Results:**
- Unique actions: 10 / 49 (20%) - WORSE than baseline!
- Most common: proxy_support (37%) - WORSE than baseline!
- Cross-expertise: 0%
- Narrative: 15% → 12% → 52% collapse (no invasion)

**What happened:**
- Cross-expertise prompts were in code but not actually used
- Pre-invasion scenario constrained choices more than expected
- Action diversity decreased instead of improving

**Purpose:** Demonstrates importance of verification; shows pre-invasion alone doesn't improve diversity

---

## 📁 Archived Older Runs

**Location:** `archive/old_simulation_runs/`

Contains development and test runs from earlier sessions:
- outputs_archive_20260128_* (10 runs)
- outputs_archive_20260129_* (4 runs)
- outputs_archive_20260130_* (2 runs)

These are kept for reference but not part of the main v3.6 analysis.

---

## 📈 Next Planned Runs

### After Current 3-Period Test Completes:

**If action diversity improves:**
- Run full 10-period simulation with cross-expertise
- Compare to baseline
- Generate external observer forecasting prompts

**If action diversity doesn't improve:**
- Try alternative approaches:
  - Two-stage strategic direction filtering
  - Action variety penalties
  - More directive prompts
  - Test with low_intensity scenario (vs pre-invasion)

---

## 🔍 Quick Reference

**Find specific run:**
```bash
# Baseline for comparison
cd outputs_BASELINE_low_intensity_10periods

# Failed v3.6 test (lessons learned)
cd outputs_V36_FAILED_preinvasion_10periods_no_cross_expertise

# Current test (when complete)
cd outputs
```

**Load simulation state:**
```r
# Baseline
baseline <- readRDS("outputs_BASELINE_low_intensity_10periods/simulation_state.rds")

# Failed test
failed <- readRDS("outputs_V36_FAILED_preinvasion_10periods_no_cross_expertise/simulation_state.rds")

# Current (after completion)
current <- readRDS("outputs/simulation_state.rds")
```

**Compare action diversity:**
```r
baseline_actions <- unlist(baseline$action_decisions)
failed_actions <- unlist(failed$action_decisions)
current_actions <- unlist(current$action_decisions)

cat("Baseline unique:", length(unique(baseline_actions)), "\n")
cat("Failed test unique:", length(unique(failed_actions)), "\n")
cat("Current unique:", length(unique(current_actions)), "\n")
```

---

## 📝 Notes

- Auto-archive function in run_simulation_with_actions.R automatically moves old outputs/
- Timestamp format: YYYYMMDD_HHMMSS (from simulation start time)
- Each archived run contains:
  - simulation_state.rds (complete state)
  - assessments.csv (probability trajectory)
  - simulation_summary_*.txt (narrative summary)
  - assessment_period_*.txt (period-by-period analysis)

---

**Status Key:**
- 🏃 RUNNING - Simulation in progress
- ✅ COMPLETE - Simulation finished successfully
- ❌ FAILED - Technical or implementation issue
- 📊 BASELINE - Reference comparison point
