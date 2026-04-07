# Notes for Paper & App Updates

## Paper Notes

### Data Quality: DAG Cycle Rates
Models occasionally produce causal networks containing cycles (feedback loops),
violating the DAG constraint. Cycle rates by model:

| Model | Cycle rate |
|-------|-----------|
| Llama 8B | 12/100 (12%) |
| Llama 70B | 1/100 (1%) |
| DeepSeek V3 | 1/100 (1%) |
| Qwen3-235B | 0/100 (0%) |
| Gemini Flash Lite | TBD |

Cycles typically represent genuine feedback loops (e.g., management decisions →
legal rulings → public controversy → management decisions). Larger models are
better at conforming to the DAG constraint. Should report this as a data quality
metric and note that cyclic graphs may affect betweenness centrality computation.

**Action**: Add cycle rate to a data quality table in the paper. Include Gemini.
Consider excluding cyclic questions from betweenness-based analyses or noting as limitation.

### SSR Definition (DONE)
H = {negate_high, strengthen, negate_critical, strengthen_critical}
L = {negate_low, strengthen_low, negate_peripheral, strengthen_peripheral, irrelevant}

### Asymmetry Index (DONE)
Now uses all negate vs all strengthen (5 types each).

### Terminology (DONE)
- "Critical path" → "shortest path" throughout paper and figures
- CPP → SPP (Shortest-Path Premium)

### Methods sections still needed in belief_sensitivity.tex
- Reasoning embedding analysis (structural vs control cosine similarity)
- Cross-model DAG agreement (permutation tests on node/edge Jaccard, spectral distance)
- Within-question Kendall τ as primary importance-sensitivity metric

### Key findings to incorporate into Results
- **UMAP clustering**: Reasoning clusters by question, not by model or importance tier.
  Meteo France questions have loosest clusters; prediction market questions tightest.
- **Gemini node Jaccard**: Notably low (0.05-0.08) vs other model pairs (0.12-0.16).
  Gemini picks different causal factors than other models.
- **Structural ablation**: Nodes-only within-question τ = 0.205 (p < .0001, 66% positive).
  Weaker than probing τ ≈ 0.4 but significant. On-path vs off-path also significant (p < .001).
- **Network size**: Small networks (3-5 nodes) have near-zero τ — insufficient importance
  variance. Medium and large both work. SSR robust across sizes.

---

## App Notes

### Pre-Selected Questions: Model Attribution
The pre-selected questions in the explore view don't clearly indicate which
model generated the DAG on the individual question detail page.

**Action**: Add a model badge/label to the question detail page header.

### Interactive Probe Model Mismatch
The interactive probe panel defaults to Llama 3.3 70B, but the pre-selected
questions may have been generated with a different model.

**Action**: Default the probe model to match the model that generated the DAG.

### Pre-Selected Data Regeneration
After all runs complete, regenerate the pre-selected question data for all 5 models:
```bash
cd belief-sensitivity-explorer
npx tsx scripts/prepare-data.ts ../outputs/sensitivity/causal/70b_one_turn/question_results
```
Support browsing across models (currently single-model only).
