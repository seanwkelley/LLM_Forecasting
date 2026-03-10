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
