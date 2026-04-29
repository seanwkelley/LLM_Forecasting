# Notes for Paper & App Updates

## Paper Notes

### Data Quality: DAG Cycle Rates (refreshed 2026-04-07, 116 questions)
Models occasionally produce causal networks containing cycles (feedback loops),
violating the DAG constraint. Cycle rates by model:

| Model | Cycle rate |
|-------|-----------|
| GPT-OSS 120B | 1/116 (0.9%) |
| DeepSeek V3 | 2/116 (1.7%) |
| Qwen3 235B | 5/116 (4.3%) |
| Llama 70B | 6/116 (5.2%) |
| Qwen3 32B | 8/116 (6.9%) |
| Gemini Flash Lite | 19/116 (16.4%) |
| Llama 8B | 20/116 (17.2%) |

Cycles typically represent genuine feedback loops (e.g., management decisions →
legal rulings → public controversy → management decisions). Larger models are
generally better at conforming to the DAG constraint, though Gemini Flash Lite
is an exception (high cycle rate despite being a frontier-tier model).

**Action**: Add cycle rate to a data quality table in the paper if reviewers ask.
Cyclic graphs are tolerated by `networkx.betweenness_centrality` so they don't
break the analysis pipeline; the centrality interpretation is still meaningful.

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

### Pre-Selected Data Regeneration (DONE — supports all 7 models)
```bash
cd belief-sensitivity-explorer
npm run prepare-data
```
Reads from `../outputs/sensitivity/causal/{model}/question_results/` for all 7
models (llama_neutral, llama_70b_neutral, deepseek_neutral, qwen_neutral,
qwen_32b_neutral, gemini_fl_neutral, gpt_oss_neutral). Joins question topics
from `../forecast_bench/high_complexity_questions.json` (assigned by
`classify_question_topic.py`).
