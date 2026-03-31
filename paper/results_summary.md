# Structural Grounding in LLM Forecasting: Results Summary

## Research Question

When LLMs generate causal DAGs to support probability forecasts, do they actually *use* the structure they create? Specifically: do probability updates in response to probes respect the topological properties of the self-generated graph?

## Method

- 5 LLMs (Llama 8B, Llama 70B, DeepSeek V3, Qwen3 235B, Gemini Flash-Lite) + Gemini 3.1 Pro (running)
- 100 binary forecasting questions from ForecastBench
- Each model generates a causal DAG (4-8 nodes), then receives ~20 targeted probes challenging specific nodes/edges
- Probes classified as: Strengthen, Negate, Structural Challenge, Control
- Primary analysis: Linear Mixed-Effects regression (R, lme4) with random intercepts by question
- Both shared-slope (pooled) and interaction (model-specific slope) variants fitted

## Core Finding: Outcome-Directed Salience, Not General Graph Reasoning

LLMs are sensitive to **outcome-directed structural properties** (how connected is this element to the outcome?) but NOT to **generic graph centrality** for edges.

### Comprehensive Metric Comparison (Individual Models)

Each predictor tested separately with model fixed effects + random intercept by question:

| Metric | Level | β | p | Sig |
|--------|-------|---|---|-----|
| Node betweenness | Node | 0.014 | < .001 | *** |
| Path relevance (outcome-directed) | Node | 0.017 | < .001 | *** |
| Direct cause (binary) | Node | 0.012 | < .001 | *** |
| Causal depth (distance to outcome) | Node | −0.009 | < .001 | *** |
| N paths to outcome | Node | 0.001 | .256 | n.s. |
| Node degree | Node | 0.018 | < .001 | *** |
| Edge betweenness | Edge | 0.001 | .100 | n.s. |
| Edge on shortest path (binary) | Edge | 0.005 | .029 | * |
| Shortest path count through edge | Edge | 0.005 | < .001 | *** |
| Edge direct to outcome (binary) | Edge | 0.019 | < .001 | *** |

Key pattern: **outcome-directed metrics are significant at both node and edge levels**. Generic edge betweenness is the exception, not the rule.

### Combined Models: What Survives When Controlling for Everything?

**Combined Node Model** (all predictors simultaneously):

| Predictor | β | p | Survives? |
|-----------|---|---|-----------|
| Path relevance | 0.010 | < .001 | **Yes** |
| Node degree | 0.013 | < .001 | **Yes** |
| Betweenness | −0.003 | .268 | No |
| Causal depth | −0.002 | .375 | No |
| Is direct | −0.004 | .390 | No |

**Combined Edge Model** (all predictors simultaneously):

| Predictor | β | p | Survives? |
|-----------|---|---|-----------|
| Direct to outcome | 0.019 | < .001 | **Yes** |
| Edge betweenness | −0.001 | .176 | No |
| On shortest path | −0.001 | .742 | No |

**Takeaway**: The independent drivers are:
- **Nodes**: path relevance (outcome-directed connectivity) + degree (general connectivity)
- **Edges**: direct connection to the outcome node — nothing else

### Model-Specific Slopes

**Model A (Betweenness)**: Model-specific slopes NOT jointly significant (LRT χ²(4) = 7.27, p = .12). Per-model slopes:

| Model | Slope | 95% CI |
|-------|-------|--------|
| Llama 70B (ref) | 0.010 | [0.004, 0.016] |
| DeepSeek V3 | 0.006 | [−0.004, 0.016] |
| Gemini Flash-Lite | 0.019 | [0.009, 0.029] |
| Llama 8B | 0.002 | [−0.006, 0.010] |
| Qwen3 235B | 0.010 | [0.001, 0.018] |

**Model B (Path Relevance)**: Model-specific slopes ARE significant. Gemini steepest (0.040), Llama 8B shallowest (0.005).

## Validation

### Scrambled Edge Placebo (70B only)

| Condition | β₁ (betweenness) | p |
|-----------|------------------|---|
| Original 70B | 0.012 | < .001 |
| Scrambled 70B | 0.006 | .057 (n.s.) |

Grounding coefficient degrades by ~50% and loses significance.

### Structural Ablation (70B only)

Physically remove each node/edge from the DAG, re-forecast:

| Ablation predictor | β | p |
|-------------------|---|---|
| Node betweenness | 0.005 | < .001 |
| Node path relevance | 0.005 | < .001 |
| Edge betweenness | 0.002 | .41 (n.s.) |

Confirms probing pattern: node topology predicts ablation sensitivity, generic edge centrality does not.

## Intervention Category Effects

| Category | Level | Mean |Δ| |
|----------|-------|-----------|
| Strengthen | Node | 0.118 |
| Strengthen | Edge | 0.093 |
| Structural Challenge | Node | 0.087 |
| Structural Challenge | Edge | 0.083 |
| Negate | Node | 0.080 |
| Negate | Edge | 0.068 |
| Control | — | 0.037 |

Node-level probes produce larger shifts than edge-level probes within every category.

## Coherence Checks

- **Stated-impact ratings**: Judge-rated impact (1-5) correlates with |shift| — monotonic increase across ratings
- **Bayesian coherence**: Weak log-odds shift correlation with initial probability (r = −0.08, p < .001)
- **Embedding separation**: Reasoning for targeted probes more semantically similar within-question than for irrelevant probes (p < .001)

## What Structural Grounding Does NOT Predict

- **Forecast accuracy**: Grounding ρ vs Brier score: ρ = −0.002, p = .98
- **Reasoning quality**: Grounding ρ vs judge rating: ρ = −0.07, p = .13

Structural coherence is independent of forecast accuracy.

## Revised Interpretation

The initial framing — "importance weighting, not path tracing" — was **too strong**. The extended analysis shows models DO track edge-level structure, but only when it relates to the outcome:

> **LLMs exhibit outcome-directed structural sensitivity: they track which nodes and edges are connected to the outcome, but not the general topological importance of edges in the broader graph.**

This is more nuanced than "edge blind" — models show a **proximity heuristic** focused on the outcome node specifically. The independent predictors (path relevance, degree, direct-to-outcome edges) all measure different facets of "how connected is this to the thing we're forecasting?"

What they demonstrably DON'T do: weight edge probes by how many shortest paths flow through that edge in the general graph (edge betweenness). This suggests they treat the DAG as an **outcome-centric star** rather than a **flow network**.

## Running Experiments

1. **Graph-Guided Probing** (Llama 70B) — Tests whether explicit path-tracing prompts recover sensitivity to general edge topology. If edge betweenness becomes significant under prompting, the capability exists but needs elicitation.

2. **Gemini 3.1 Pro** (full pipeline, 13/100 complete) — Frontier model comparison. Does a more capable model show qualitatively different grounding?

3. **XL Networks** (12-16 nodes, 70B) — Does grounding change with graph complexity?

4. **Factor Ranking** (all 5 models, Llama 8B done, 70B in progress) — Do stated importance rankings correlate with betweenness centrality from DAGs?

## Response to Reviewer Concerns

### Concern 1: "Edge betweenness is an incomplete test of graph reasoning"

**Addressed.** We now test 4 edge metrics:
- Edge betweenness (n.s.)
- On shortest path (p = .029)
- Shortest path count (p < .001)
- Direct to outcome (p < .001)

Models ARE edge-sensitive — but only for outcome-directed edge properties.

### Concern 2: "Node vs edge probes may not be comparable"

Partially addressed by the extended edge analysis. The null is specific to *generic* edge centrality, not to edge probes in general (direct-to-outcome edges show the largest effect of any predictor).

### Concern 3: "Betweenness may proxy for semantic importance"

Factor ranking experiment (running) will test this. Combined model shows betweenness loses significance when controlling for path relevance and degree — consistent with it being a proxy.

### Concern 4: "Placebo evidence is suggestive but not decisive"

Still 70B only. Could replicate across models.

### Concern 5: "Overinterpretation of no path tracing"

**Addressed.** Revised claim from "no path tracing" to "outcome-directed sensitivity without general edge-level graph reasoning." Supported by the combined model results.
