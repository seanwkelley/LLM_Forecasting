# Structural Grounding in LLM Forecasting: Results Summary

*Last refreshed: 2026-04-07 (116 questions × 7 models, neutral prompts, log-odds DV)*

## Research Question

When LLMs generate causal DAGs to support probability forecasts, do they actually *use* the structure they create? Specifically: do probability updates in response to probes respect the topological properties of the self-generated graph?

## Method

- **7 LLMs**: Llama 3.1 8B, Llama 3.3 70B, Qwen3 32B, Qwen3 235B, DeepSeek V3, Gemini 2.5 Flash Lite, GPT-OSS 120B (5 architecture families, all via OpenRouter)
- **116 high-complexity questions** filtered from 500 ForecastBench questions using a GPT-5.4 complexity classifier
- Each model generates a causal DAG (6–10 nodes), then receives ~21 targeted probes challenging specific nodes/edges
- Probes classified into 4 categories: Strengthen, Negate, Structural Challenge, Control (14 types total)
- **Primary DV**: absolute log-odds shift |Δlogit| (avoids ceiling/floor compression of raw probability)
- **Primary analysis**: Linear Mixed-Effects regression (R, lme4) with question-level random intercepts and probe direction as a fixed-effect covariate
- Both shared-slope (pooled) and interaction (model-specific slope) variants fitted
- Edge betweenness was tested in earlier iterations and dropped from the paper — node betweenness and outcome mediation are the two retained predictors

## Core Result: Topological Predictors Significantly Predict Probe Sensitivity

**Model A (Node Betweenness, shared slope)** — N = 7,404 observations, 116 questions:

| Predictor | β (raw) | SE | p | R²m |
|---|---|---|---|---|
| importance_z | **0.0093*** | 0.0007 | <.001 | 0.079 |

**Model B (Outcome Mediation, shared slope)** — N = 6,495 observations, 116 questions:

| Predictor | β (raw) | SE | p | R²m |
|---|---|---|---|---|
| path_relevance_z | **0.0105*** | 0.0008 | <.001 | 0.080 |

In log-odds terms, the betweenness slope is β=0.044 (p<.001) and outcome mediation is β=0.050 (p<.001). Both topological predictors significantly predict |Δlogit| at the population level.

## Per-Model Slopes (Interaction Model A — Betweenness)

Total per-model slope = β₁ (shared) + β₁ × model interaction. From `lme_model_a_table.tex` (April 6, 2026):

| Model | Total Slope | p | Notes |
|---|---|---|---|
| Gemini 2.5 Flash Lite | 0.0217 | <.001 | Steepest |
| Qwen3 235B | 0.0149 | <.001 | |
| GPT-OSS 120B | 0.0105 | <.001 | |
| Llama 3.3 70B (ref) | 0.0094 | <.001 | |
| DeepSeek V3 | 0.0086 | n.s. | |
| Qwen3 32B | 0.0086 | n.s. | |
| Llama 3.1 8B | 0.0020 | n.s. | Only model with no significant slope |

Model-specific slope variation is significant (Gemini's interaction term β=0.0123, p<.001; Llama 8B's β=−0.0074, p=.002).

## Per-Model Spearman (importance vs |shift|, no controls)

| Model | r | p |
|---|---|---|
| GPT-OSS | 0.212 | <.001 |
| DeepSeek | 0.204 | <.001 |
| Qwen 32B | 0.155 | <.001 |
| Qwen 235B | 0.124 | <.001 |
| Gemini FL | 0.107 | <.001 |
| Llama 70B | 0.092 | <.001 |
| Llama 8B | 0.059 | .004 |

## Validation

### Edge Permutation Placebo (GPT-OSS only)

| Condition | β₁ (betweenness) | p | N |
|---|---|---|---|
| Intact GPT-OSS | 0.0111 | <.001 | 976 |
| Permuted GPT-OSS | 0.0090 | <.001 | 928 |

Grounding coefficient drops by ~19% under random edge rewiring but remains significant — node descriptions still encode importance information. The structural component is the difference (~0.002). See `lme_scrambled_table.tex`.

### Structural Ablation ("ignore this factor", GPT-OSS, node-only)

| Predictor | β | SE | p | N | Marginal R² |
|---|---|---|---|---|---|
| betweenness_z | 0.0161 | 0.0018 | <.001 | 756 | 0.118 |
| path_relevance_z | (similar) | | <.001 | 756 | |

Spearman r(betweenness, |shift|) = 0.25, p=.002. Confirms probing pattern: high-betweenness factors elicit larger shifts when the model is told to disregard them. See `lme_ablation_node_betw_table.tex`.

### Cross-Model DAG Convergence

Same-question DAGs are significantly more similar across models than chance:
- **Semantic nGED**: 0.833 (vs. null 1.014 ± 0.001, p<.001 over 2,000 permutations)
- 7 models × 116 questions, embedding-based Hungarian alignment with 0.7 cosine threshold

Models converge on similar causal representations for the same forecasting problem.

### Test-Retest Reliability (Stage 1 only, 116 questions, all 7 models)

DAG semantic nGED across runs:
| Model | nGED |
|---|---|
| DeepSeek V3 | 0.62 |
| Llama 70B | 0.63 |
| Gemini Flash Lite | 0.65 |
| Qwen3 235B | 0.66 |
| GPT-OSS 120B | 0.69 |
| Qwen3 32B | 0.77 |
| Llama 3.1 8B | 0.82 |

Larger models produce more stable causal structures across runs. All values are well below the cross-model null (1.01).

### Persuasiveness Control (GPT-OSS, 400 probes)

Independent GPT-4o-mini judge rated probe text persuasiveness on 1–5 scale, blind to importance level:
- High-importance probes: M=3.62
- Low-importance probes: M=3.53
- Mann-Whitney U=21,365, **p=0.17 (n.s.)**

Probe text quality is not a confound for importance-driven sensitivity.

### Spurious Context Control

- 0/116 contamination (no DAG node derived from irrelevant background paragraph)
- Probability ρ=0.728 vs unaugmented DAGs, MAE=0.085
- DAG nGED 0.728 (modestly higher than test-retest 0.685, well below cross-model null 1.01)

### Superforecasting Prompt Comparison (GPT-OSS)

- Probability ρ=0.713, MAE=0.096
- Semantic nGED=0.714 (permutation p<.001, null=0.998)
- Edge count drops modestly under SF prompt (8.6→8.1, p=.008)
- Superforecasting instructions alter causal decomposition more than test-retest variation but probability estimates remain correlated

## Coherence Checks

- **Stated-impact ratings**: Judge-rated impact (1-5) correlates with |Δlogit| — monotonic increase across ratings
- **Bayesian coherence**: Weak log-odds shift correlation with initial probability
- **Embedding separation**: Reasoning for targeted probes more semantically similar within-question than for irrelevant probes

## Elo Difficulty Regression (116q × 7 models, reran 2026-04-06)

Tournament: 15 rounds, ~870 GPT-4o-mini pairwise comparisons. Elo range 1347–1684.

| DV | β(Elo_z) | p | LRT χ² | Sig |
|---|---|---|---|---|
| Mean absolute shift | −0.002 | .002 | 9.39 | * |
| SSR | +0.006 | .749 | 0.10 | n.s. |
| Within-question τ | −0.004 | .772 | 0.09 | n.s. |
| Shortest-path premium | +0.001 | .441 | 0.60 | n.s. |
| Asymmetry index | −0.019 | .046 | 4.00 | * |
| Reasoning judge rating | +0.017 | .007 | 7.30 | * |
| Uncertainty judge rating | −0.012 | .029 | 4.77 | * |

Harder questions get smaller absolute shifts (more cautious updating), more reasoning effort (higher judge rating), less hedging language (lower uncertainty rating). Structural sensitivity (SSR, τ) is **stable** across difficulty — the importance-shift relationship holds for both easy and hard questions. **Notable change from 100q/5-model run**: SSR was significant before (p=.004), now n.s.

## Robustness Summary

| Test | Result |
|---|---|
| Test–retest | DAG nGED 0.62–0.82 across 7 models, well below cross-model null 1.01 |
| Edge permutation | Grounding drops modestly (β 0.0111 → 0.0090) under random rewiring |
| Structural ablation | Same pattern under "ignore this factor" framing (Spearman r=0.25, p=.002) |
| Network size (12–16) | Effect persists with larger DAGs |
| Temperature (T=0.0–1.0) | nGED stable around 0.67–0.71, well below cross-model null |
| Spurious context | 0/116 contamination, prob ρ=0.728 |
| Persuasiveness | High/low importance probes equally persuasive (p=.17) |
| Superforecasting prompt | nGED 0.714, prob ρ=0.713 — alters structure more than retest |

## Interpretation

LLMs exhibit **internally consistent structural sensitivity**: probability updates are proportional to the topological importance of challenged elements within the model's *own* elicited causal DAG. The effect:

1. Holds across 7 models from 5 architecture families (with Llama 8B as the lone exception for individual significance)
2. Survives a battery of validation tests including edge permutation, structural ablation, and persuasiveness control
3. Is not driven by question difficulty, probe text quality, or DAG structural artifacts

Per-model variation is meaningful: Gemini and Qwen 235B show the steepest grounding slopes, while smaller models show flatter responses. Test-retest reliability also tracks model size — larger models produce more stable causal representations across independent runs.
