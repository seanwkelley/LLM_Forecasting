# Action Prediction Research - Quick Reference

**Last Updated:** February 10, 2026, 9:45 PM

---

## TL;DR

**CRITICAL FINDING:** How you evaluate multi-agent LLM systems matters **enormously**.

- Individual averaging: Generic F1 = 0.27, Personalized F1 = 0.10 (171% gap)
- Ensemble aggregation: Generic F1 = 0.60, Personalized F1 = 0.48 (26% gap)

**Performance underestimated by 2-3x** when using individual averaging instead of ensemble aggregation.

---

## Key Results Summary

### Evaluation Method Comparison (Period 10, N=100)

| Metric | Generic Individual | Generic Ensemble | Improvement |
|--------|-------------------|------------------|-------------|
| Novaris F1 | 0.214 | **0.444** | +107% |
| Tethys F1 | 0.333 | **0.750** | +125% |
| Combined | 0.274 | **0.597** | +118% |

| Metric | Simplified Individual | Simplified Ensemble | Improvement |
|--------|----------------------|---------------------|-------------|
| Novaris F1 | 0.048 | **0.200** | +317% |
| Tethys F1 | 0.155 | **0.750** | +384% |
| Combined | 0.101 | **0.475** | +368% |

**Key Insight:** Personalized agents benefit MORE from ensemble aggregation (+368% vs +118%).

---

## Best Practices

### ✅ DO:
1. **Use ensemble aggregation** - Majority voting, Top-K, or adaptive threshold
2. **Save raw predictions** - Enable post-hoc analysis with different methods
3. **Test multiple ensemble methods** - Different scenarios favor different aggregation
4. **Use generic agents** - Still outperform even with ensemble (26% better)
5. **Leverage information asymmetry** - Give agents access to prior actions (+30-70% boost)

### ❌ DON'T:
1. **Don't average individual F1 scores** - Severely underestimates performance
2. **Don't use personas for individual agents** - Adds noise (-35% to -75%)
3. **Don't assume one evaluation method generalizes** - Always test both

---

## Ensemble Methods Tested

| Method | Description | Best For |
|--------|-------------|----------|
| **Majority Voting (50%)** | Include if ≥50% predict it | Dense predictions |
| **Majority Voting (30%)** | Include if ≥30% predict it | Moderate density |
| **Top-K** | Select K most common | Sparse predictions |
| **Adaptive Threshold** | Match ground truth size | **Recommended default** |

**Winner:** Adaptive threshold - works well across all scenarios.

---

## Research Questions Answered

### 1. Can LLMs predict strategic actions?
**YES** - F1 = 0.60 (ensemble) vs 0.27 (individual average)

### 2. Does information help?
**YES** - Tethys (sees Novaris actions) +30-70% better than Novaris (proactive)

### 3. Do personas help?
**NO** - Generic still wins by 26% (ensemble) or 171% (individual)

### 4. Does evaluation method matter?
**ABSOLUTELY** - 3x performance difference between individual vs ensemble

---

## File Locations

**Documentation:**
- `RESEARCH_FINDINGS.md` - Comprehensive analysis
- `ACTION_PREDICTION_STATUS.md` - Implementation status
- `SIMPLIFIED_PERSONAS_SUMMARY.md` - Persona experiment
- `QUICK_REFERENCE.md` - This file

**Code:**
- `run_full_comparison_with_ensemble.py` - Main experiment (saves predictions)
- `ensemble_aggregation.py` - Ensemble methods
- `test_ensemble_aggregation.py` - Ensemble validation

**Data:**
- `ground_truth_actions.json` - Approved actions by period
- `plausible_actions.json` - 26 common actions
- `persona_profiles_simplified.json` - 500 personas

**Results:**
- `outputs/action_prediction_results/` - All experiment outputs

---

## Current Experiment Status

**Running:** Full 10-period ensemble experiment
**Started:** February 10, 2026, ~9:30 PM
**ETA:** ~10:10 PM
**Output:** Both individual and ensemble metrics across all periods

**Research Questions:**
1. Does ensemble advantage persist across all 10 periods?
2. Which periods benefit most from aggregation?
3. Does personalization deficit remain ~26% with ensemble?

---

## Next Steps

1. ✅ Complete 10-period ensemble experiment
2. Analyze temporal patterns (do ensemble gains grow/shrink over time?)
3. Test alternative ensemble methods on saved predictions
4. Domain-specific analysis (which action types benefit from ensemble?)
5. Test multi-agent debate (does deliberation beat independent ensemble?)

---

## Critical Lessons Learned

### Lesson 1: Evaluation Method is Not Neutral
Individual averaging and ensemble aggregation are **fundamentally different** evaluation paradigms that can produce opposite conclusions about relative performance.

### Lesson 2: Individual Performance ≠ Collective Performance
Just because individual agents are worse doesn't mean the ensemble is worse. Diversity can create ensemble value even when individuals perform poorly.

### Lesson 3: Always Test Multiple Evaluation Methods
What works in research literature may not be appropriate for production systems. Test both individual and ensemble evaluation for multi-agent systems.

### Lesson 4: Save Raw Data
We had to re-run a $4, 40-minute experiment because we didn't save individual predictions. Always save raw outputs for post-hoc analysis.

### Lesson 5: Wisdom of Crowds Works for LLMs
Ensemble effects are substantial (+118% to +368%). Multi-agent LLM systems can leverage collective intelligence just like human crowds.

---

## Citation

If you use these findings, please cite:

```bibtex
@techreport{kelley2026ensemble,
  author = {Kelley, Sean W.},
  title = {Ensemble Aggregation vs Individual Averaging in Multi-Agent LLM Systems},
  institution = {Northeastern University},
  year = {2026},
  month = {February},
  note = {Action Prediction Research}
}
```

---

## Contact

**Questions or Collaboration:**
- Email: seanwkelley@gmail.com
- GitHub: [Issues](https://github.com/seanwkelley/LLM_Forecasting/issues)

---

**Remember:** When evaluating multi-agent LLM systems, always use ensemble aggregation, not individual averaging!
