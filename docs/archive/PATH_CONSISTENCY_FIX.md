# Path Consistency Fix

**Date:** 2026-01-31
**Issue:** Inconsistent output directory paths
**Status:** ✅ FIXED

---

## Problem

The codebase had inconsistent output directory paths:
- Main simulation files → `outputs/` ✓ correct
- Interaction CSVs → `output/interactions/` ✗ wrong (singular)

This caused files to be scattered across two directories.

---

## Fix Applied

**File Modified:** `src/interaction_engine.R`

**Changed all occurrences:**
```r
# Before (8 occurrences):
output_dir = "output/interactions"

# After:
output_dir = "outputs/interactions"
```

**Functions updated:**
- `save_interactions_to_csv()` (line 1110)
- `save_coordination_to_csv()` (line 1214)
- `save_actions_to_csv()` (line 1284)
- `combine_all_csvs()` (line 1347)

---

## Impact

**Current running simulation:**
- Still writes to old `output/interactions/` (can't change mid-run)
- Main results in `outputs/` are unaffected

**All future simulations:**
- ✅ All files will go to `outputs/` directory
- ✅ Interaction CSVs will go to `outputs/interactions/`
- ✅ One clean directory structure

---

## Cleanup Required

**After current simulation completes, run:**
```bash
bash cleanup_old_output_dir.sh
```

This will archive the old `output/` directory to `archive/output_OLD_interactions_deprecated/`

**Or manually:**
```bash
mv output archive/output_OLD_interactions_deprecated
```

---

## Verification

**Check the fix:**
```bash
grep "outputs/interactions" src/interaction_engine.R
```

**Expected output:** All default parameters now use `"outputs/interactions"`

---

## New Standard Structure

All simulation results will now go to a single directory:

```
outputs/
├── simulation_state.rds          # Main simulation state
├── assessments.csv                # Probability trajectory
├── simulation_summary_*.txt       # Narrative summary
├── assessment_period_*.txt        # Period-by-period analysis
└── interactions/                  # Detailed interaction logs
    ├── period_01_coordination.csv
    ├── period_01_actions.csv
    ├── period_02_coordination.csv
    ├── period_02_actions.csv
    └── ...
```

**No more split between `output/` and `outputs/`!**

---

## Status

- ✅ Code fixed in `src/interaction_engine.R`
- ✅ Future runs will use correct path
- ⏳ Old `output/` directory cleanup pending (after current run completes)
- ✅ Cleanup script created: `cleanup_old_output_dir.sh`

---

**Next simulation will automatically use the corrected path structure.**
