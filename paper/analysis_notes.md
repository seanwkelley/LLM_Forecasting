# Analysis Notes — Belief Sensitivity

## Cross-Model Spread in Initial Probabilities

Mean spread (max - min across 3 models) = 0.214 ± 0.017 SE over 50 shared questions.

### Pattern: data-anchored questions converge, speculative questions diverge

| Source type     | Mean spread | n  |
|-----------------|------------:|---:|
| Manifold        |       0.281 | 11 |
| Infer           |       0.280 |  2 |
| Metaculus       |       0.256 | 11 |
| Wikipedia       |       0.250 |  3 |
| ACLED           |       0.213 |  3 |
| Polymarket      |       0.180 |  5 |
| FRED            |       0.140 |  7 |
| dbnomics        |       0.122 |  6 |
| yfinance        |       0.115 |  2 |

**High-spread questions** tend to be speculative/subjective (e.g., "Will Tesla have driverless ride-hailing?", "Will there be 1500+ Pokemon by 2030?", "Will Colbert be forced off air?"). DeepSeek-R1-Distill-70B consistently rates these much lower than both Llama models.

**Low-spread questions** tend to be data-driven with quantitative anchors (FRED economic indicators, dbnomics temperature readings, yfinance stock prices). All three models converge when the question has a concrete numerical baseline.

### Correlations with spread

- Spread vs mean probability: ρ = −0.211 (weak negative — models agree more on low-probability events)
- Spread vs network complexity (nodes/edges): ρ ≈ 0 (no relationship)

### Interpretation

This suggests that model disagreement is driven primarily by **question ambiguity**, not model architecture. When questions have clear data anchors, even models of different sizes and families converge. The divergence on speculative questions likely reflects differences in training data priors rather than reasoning capability.

### Pairwise initial probability correlations (4 models, n=51)

All pairwise Spearman correlations of initial probabilities fall in ρ = 0.58–0.68:

| Pair | ρ |
|------|--:|
| Llama-8B vs Llama-70B | 0.68 |
| Llama-8B vs DeepSeek-V3 | 0.59 |
| Llama-8B vs Qwen3-235B | 0.58 |
| Llama-70B vs DeepSeek-V3 | 0.63 |
| Llama-70B vs Qwen3-235B | 0.67 |
| DeepSeek-V3 vs Qwen3-235B | 0.67 |

Llama-8B is least correlated with other models; the three larger models (70B, DeepSeek, Qwen) cluster more tightly (ρ = 0.63–0.67).

## Cross-model DAG agreement: content vs topology

Permutation tests (5,000 permutations, two-sided) on pairwise DAG similarity reveal a dissociation between content overlap and structural topology:

- **Node Jaccard**: All 6 model pairs significant (p < .001). Same-question DAGs share ~10–16% of node labels — significantly more than cross-question pairings. Models converge on *which causal factors* to identify for a given question.
- **Edge Jaccard**: 5/6 pairs significant (p < .001), one at p = .023. Same-question DAGs share ~0.3–2.5% of edges — tiny but above chance. Some agreement on specific causal links.
- **Spectral distance**: 0/6 pairs significant (p = .11–.91). Graph topology (hub structure, path depth, connectivity patterns) is no more similar for same-question DAGs than for cross-question DAGs.

**Interpretation**: Models agree on *what concepts to include* (node content) but not *how to wire them up* (graph structure). Each model has a characteristic DAG-building style — similar number of nodes, density, and depth — that it applies uniformly regardless of the question. The topology is a model-specific habit, not a question-driven property. This means the structural sensitivity analysis (SSR, critical path, importance rankings) is probing model-specific wiring choices rather than some shared "true" causal structure.

This has implications for interpreting sensitivity results: if the DAG structure is largely model-idiosyncratic, then a model's response to structural probes reflects how it reasons about *its own* causal model, not whether the causal model is objectively correct.

## TODO: Separate calibration by reference type

The current Brier scores and calibration curves conflate two fundamentally different reference values:

- **Prediction market questions** (~40 of 48): `outcome_probability` is the market consensus probability at freeze time — a continuous [0,1] value reflecting crowd belief, NOT a binary ground truth. Brier here measures agreement with the crowd, not actual calibration.
- **Data-source questions** (~8 of 48, from FRED/Yahoo/dbnomics): `outcome_probability` is a resolved binary outcome (0 or 1) computed by comparing the actual value at resolution date to the freeze value. These are real ground-truth outcomes.

**Current issue**: both types are pooled in `_load_freeze_values()` and used identically in calibration curves and Brier scores. This is misleading — only the data-source subset provides true calibration signal.

**Action needed**: separate reporting for (1) Brier vs market consensus and (2) Brier vs resolved binary outcomes. The calibration curve should either be split into two panels or clearly labeled as "vs market" with a footnote. Table 1 "Brier (vs Market)" label is a partial fix but the underlying computation still pools both types.

---

## Why speculative questions have lower Brier scores than data-anchored

The source-stratified calibration plot (supplementary Fig. panel c) shows speculative questions (Brier=0.099) outperforming data-anchored questions (Brier=0.256). This is driven by **base rate asymmetry**, not better calibration:

| Category | n | Resolved Yes | Base rate | Mean model pred |
|----------|--:|:------------:|----------:|----------------:|
| Data-anchored | 15 | 7/15 | 47% | 0.65 |
| Speculative | 29 | 4/29 | 14% | 0.45 |

Resolution rates by source:

| Source | n | Resolved Yes | Base rate |
|--------|--:|:------------:|----------:|
| dbnomics | 6 | 0/6 | 0% |
| Manifold | 11 | 0/11 | 0% |
| Polymarket | 5 | 1/5 | 20% |
| Wikipedia | 4 | 1/4 | 25% |
| Metaculus | 11 | 3/11 | 27% |
| Infer | 2 | 0/2 | 0% |
| yfinance | 2 | 1/2 | 50% |
| FRED | 7 | 6/7 | 86% |

**Explanation**: Speculative questions have a heavily skewed base rate — 86% resolved "no." Predicting ~0.4 when the answer is 0 still yields a reasonable Brier score. Data-anchored questions are nearly 50/50, which is the hardest regime: models predict 0.65 on average when the true rate is 0.47, so overconfidence is penalized more heavily. The lower Brier score for speculative questions reflects an easier prediction problem (skewed outcomes), not superior calibration.

---

## Superforecasting Prompt Ablation

Run on **Llama-3.3-70B only**, 50 shared questions. Baseline vs superforecasting-augmented system prompt (adds outside view, granular decomposition, signal vs noise, counterfactual edge validation, base-rate calibration).

Key findings:
- **Probability correlation**: r = 0.90, p < 0.001 — prompts produce very similar forecasts
- **Node Jaccard**: z = 25 SDs above null — strong content agreement (same causal factors identified)
- **Edge Jaccard**: z = 22 SDs above null — significant but small absolute overlap
- **Spectral Distance**: z ≈ 2 SDs — marginal; graph topology is not meaningfully more similar than chance
- **DAG structural statistics**: no significant differences in node count (6.8 vs 6.7), edge count (6.8 vs 6.8), or density (0.172 vs 0.178)

**Interpretation**: The superforecasting prompt changes *which specific edges* the model draws but not the overall forecast or the set of causal factors. The model converges on the same concepts regardless of prompt framing, but wiring decisions are sensitive to instructional framing.
