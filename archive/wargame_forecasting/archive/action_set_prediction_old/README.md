# Action Set Prediction (Archived)

**Date Archived:** February 11, 2026
**Status:** Superseded by action probability prediction

---

## What This Was

These files implemented **action set prediction** - predicting the full set of actions (out of 69 total) that each faction would take in a given period.

### Approach

- Predict complete action set (multiple actions)
- Evaluated with accuracy, precision, recall, F1
- Used multi-label classification metrics
- Compared 6 conditions across periods 1-3

### Why Archived

Superseded by **action probability prediction** approach:
- **Old:** Predict full action set (hard classification)
- **New:** Predict binary probability for 5 target actions (calibrated probabilities)

The new approach:
1. Uses Brier score (proper scoring rule)
2. Focuses on actions with 30-70% base rates (maximum sensitivity)
3. Directly comparable to collapse probability forecasting
4. Better evaluation methodology

### Files Archived

- `action_prompts.py` - Prompt templates for action set prediction
- `action_evaluation.py` - Evaluation metrics (accuracy, precision, recall, F1)
- `run_experiment_periods_1_3.py` - Experiment runner for 6 conditions
- `run_full_comparison_with_ensemble.py` - Full comparison with ensemble evaluation

### Replacement Files

See current implementation:
- `action_probability_prompts.py` - Binary probability prompts (5 actions per faction)
- `run_action_probability_experiment.py` - Sharding experiment runner
- `ACTION_PROBABILITY_RESULTS.md` - Results documentation

---

**Note:** These files are kept for reference only. Use the new action probability prediction approach for active research.
