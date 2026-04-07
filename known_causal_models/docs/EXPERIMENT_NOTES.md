# Experiment Notes

**Last Updated:** February 28, 2026

## Multi-Agent Forecasting Framework (Feb 23) — ACTIVE

### Motivation

The causal discovery phase established ground truth causal graphs for both domains (market: 23 edges, conflict: 26 edges). The existing forecasting experiments (Phase 1) tested a single factor — Theory of Mind — finding it helps in market (+17 MSE, p=0.027) and hurts in conflict (+0.286 MSE, p=0.010). The multi-agent forecasting framework (Phase 2) decomposes this further by independently varying **what forecasters know** (information level) and **how they communicate** (communication structure).

Key architectural decision: use **rule-based baseline simulations** as the forecasting target. This is supported by findings that rule-based agents produce the richest mechanistic dynamics (highest emergence capacity in market) and that the causal graphs are fully characterized for these engines.

### Design

**13 conditions per domain** (communication × information level):

| | L0 (time-series) | L1 (random vars) | L2 (causal graph) | L3 (graph + ToM) |
|---|---|---|---|---|
| **Single** | ✓ | ✓ | ✓ | ✓ |
| **Independent (5)** | ✓ | ✓ | ✓ | ✓ |
| **Debate (2×3 rounds)** | ✓ | | ✓ | ✓ |
| **Specialization (3+1)** | | | ✓ | ✓ |

**Information levels:**
- **L0**: Time-series history only (price/volume/fundamental or EI/actions)
- **L1**: + random 50% of expanded variables (no causal framing — controls for "more data")
- **L2**: + full causal graph in natural language + all expanded variables (knows *what affects what*)
- **L3**: + mechanistic agent decision rules with exact thresholds and multipliers (knows *how* each edge works — e.g., "hawks (score > 0.6): target_delta = +0.5 to +1.5", "mutual escalation ×1.2")

**Communication structures:**
- **Single**: 1 generic analyst, 1 LLM call/period
- **Independent**: 5 diverse personas, averaged post-hoc, 5 calls/period
- **Debate**: 2 opposing analysts (momentum vs fundamental / escalation spiral vs stability), 3 rounds (predict → critique → finalize), 6 calls/period
- **Specialization**: 3 subgraph specialists (supply/demand/shock or military/economic/political) + 1 LLM aggregator, 4 calls/period

**Key statistical contrasts:**
1. L1 vs L2 — does causal structure help beyond more data?
2. Independent vs Debate/Specialization — does deliberation help?
3. Interaction: does graph knowledge help MORE with deliberation?

**LLM call budget:** ~12,500 per domain (25,000 total). Llama 8B via OpenRouter: ~$1-2, ~4-6 hours.

### Implementation

**Phase 0: Data preparation** — Complete (Feb 23)
- Augmented `conflict/run_conflict_sim.py` baseline to log per-period state: military_balance, territory_controlled, sanctions_level, international_support, per-faction resources/gdp/military_strength/political_stability
- Augmented `market/run_market_sim.py` baseline to log per-period agent states (cash/inventory) and order aggregates (avg_bid/ask_price, total_bid/ask_qty)
- Re-ran both baselines: 10 scenarios × 30 periods, seed 42

**Phase 1-4: `forecast_multi/` package** — Complete (Feb 23)

| File | Purpose |
|------|---------|
| `domain.py` | MarketDomain / ConflictDomain adapters (data loading, prompt building, classification) |
| `llm_client.py` | Re-exports LLMClient from forecast_bench + forecast-specific parser |
| `evaluation.py` | Brier score, log score, F1, baselines (uniform/majority/frequency), ensemble averaging |
| `causal_text.py` | Adjacency matrix → structured natural language (edges grouped by functional role) |
| `config.py` | Design matrix, 5 ensemble personas/domain, debate pairs, specialization subgraphs |
| `info_builder.py` | L0–L3 information level builders |
| `single.py` | SingleForecaster — 1 call/period |
| `independent.py` | IndependentEnsemble — N parallel + average |
| `debate.py` | DebateForecaster — 2 agents × 3 multi-turn rounds |
| `specialization.py` | SpecializationForecaster — 3 specialists + LLM/mechanistic aggregator |
| `runner.py` | CLI, experiment loop, checkpoint/resume, CSV + JSON output |

### Output Format

**Per-condition directory** (`outputs/forecast_multi/{domain}_{comm}_{level}/`):
- `forecast_results.csv` — one row per individual forecast (scenario_id, period, communication, info_level, forecaster_id, round, probabilities, scores)
- `forecast_details.json` — same + reasoning text
- `forecast_summary.json` — aggregate metrics + baselines
- `checkpoint.json` — resume support

### Results (Feb 23-24, Llama 3.1 8B, 10 scenarios × 30 periods)

All 26 conditions complete. ~25,000 LLM calls total, ~13 hours runtime.

#### Brier Score (probability calibration, lower = better, uniform baseline = 0.667)

**Conflict:**

|  | L0 | L1 | L2 | L3 |
|--|----|----|----|----|
| **Single** | 0.705 | 0.722 | 0.688 | **0.671** |
| **Independent** | 0.704 | 0.718 | 0.704 | 0.723 |
| **Debate** | 0.728 | — | 0.724 | 0.774 |
| **Specialization** | — | — | 0.698 | 0.715 |

**Market:**

|  | L0 | L1 | L2 | L3 |
|--|----|----|----|----|
| **Single** | 0.721 | **0.715** | 0.722 | 0.733 |
| **Independent** | 0.824 | 0.833 | 0.765 | 0.771 |
| **Debate** | 0.816 | — | 0.798 | 0.771 |
| **Specialization** | — | — | 0.741 | 0.753 |

#### Mean Absolute Error (point prediction accuracy, lower = better)

**Conflict (EI units, range ~5-12):**

|  | L0 | L1 | L2 | L3 |
|--|----|----|----|----|
| **Single** | 0.467 | 0.458 | 0.461 | 0.470 |
| **Independent** | **0.379** | 0.398 | 0.416 | 0.435 |
| **Debate** | 0.390 | — | 0.429 | 0.455 |
| **Specialization** | — | — | 0.449 | 0.453 |

**Market (price units, range ~80-120):**

|  | L0 | L1 | L2 | L3 |
|--|----|----|----|----|
| **Single** | 7.16 | 6.80 | 7.32 | 7.38 |
| **Independent** | 6.74 | 6.81 | 6.76 | **6.74** |
| **Debate** | 7.33 | — | 7.39 | 7.28 |
| **Specialization** | — | — | 7.03 | 7.10 |

#### Key Findings

**1. Brier vs MAE tell divergent stories.** Brier score (probability calibration) favors single forecasters; MAE (point prediction) favors multi-agent ensembles. This is the classic wisdom-of-crowds effect: averaging multiple noisy point estimates reduces error, but averaging poorly calibrated probability distributions does not improve calibration.

**2. Multi-agent helps point predictions but hurts probability calibration.**
- Conflict MAE: Independent_L0 (0.379) beats single_L0 (0.467) by 19%
- Market MAE: Independent_L3 (6.74) beats single_L3 (7.38) by 8.7%
- But Brier: single is best in both domains

**3. More information hurts point predictions.** In both domains, L0 (time-series only) produces the best MAE within each communication structure. Adding causal graphs (L2) or mechanistic rules (L3) makes point estimates worse — the models overthink with structural information.

**4. Causal structure helps probability calibration (conflict only).** L2 beats L1 for both single (-0.034 Brier) and independent (-0.015 Brier) in conflict. In market, the effect is inconsistent.

**5. Debate is consistently worst.** Highest Brier scores and highest MAE in most comparisons. Multi-turn deliberation amplifies errors rather than correcting them.

**6. Only one condition beats uniform Brier baseline.** Conflict single_L3 (0.671 vs 0.667) — full mechanistic transparency with a single forecaster. No market condition beats uniform.

### Status

| Phase | Status | Details |
|-------|--------|---------|
| 0. Data preparation | **Complete** | Baseline sims augmented + re-run (10×30, both domains) |
| 1. Core module (domain, llm_client, evaluation) | **Complete** | Imports verified, tested against real data |
| 2. Graph text + config | **Complete** | Market: 1978 chars, Conflict: 2118 chars |
| 3. Info builder (L0–L3) | **Complete** | Tested: L0=0, L1≈70, L2≈2150, L3≈3500 chars |
| 4. Single + Independent | **Complete** | |
| 5. Debate + Specialization | **Complete** | |
| 6. Runner + CLI | **Complete** | Checkpoint/resume, auto-named output dirs |
| 7. Full experiment | **Complete** | All 26 conditions (13 × 2 domains), ~25,000 LLM calls |
| 8. Statistical analysis | **Next** | LMM in R, key contrasts |

### Usage

```bash
# Single condition
python -m forecast_multi.runner \
    --domain market --communication single --info-level L0 \
    --baseline-dir outputs/market_baseline --model llama

# With resume support
python -m forecast_multi.runner \
    --domain market --communication debate --info-level L2 \
    --baseline-dir outputs/market_baseline --model llama --resume

# Subset of scenarios for testing
python -m forecast_multi.runner \
    --domain market --communication single --info-level L0 \
    --baseline-dir outputs/market_baseline --model llama --scenarios 0 1
```

### Files
- `forecast_multi/` — Full package (13 modules)
- `conflict/run_conflict_sim.py` — Augmented baseline state logging (lines 248-260)
- `market/run_market_sim.py` — Augmented baseline order/state logging (lines 249-265)
- `causal_discovery/ground_truth.py` — Adjacency matrices reused for L2/L3 prompts
- Baseline data: `outputs/market_baseline/` (10 scenarios, 30 periods, augmented)
- Baseline data: `outputs/conflict_baseline/` (10 scenarios, 30 periods, augmented)

### Next Steps

1. **Merge CSVs** — Concatenate all condition CSVs into `combined_results.csv` for R analysis
2. **Statistical analysis** — `brier_score ~ communication * info_level + (1|scenario_id/period)` and `value_error ~ communication * info_level + (1|scenario_id/period)` in R with lme4
3. **Key contrasts** — L1 vs L2 (does causal structure help beyond more data?), single vs multi-agent, Brier vs MAE divergence
4. **Convergence analysis** — For debate conditions, analyze whether agents converge or diverge across rounds
5. **Specialist contribution analysis** — For specialization, compare specialist-only vs aggregator improvement
6. **Investigate Brier/MAE divergence** — Why do ensembles help point predictions but hurt probability calibration? Examine individual forecaster calibration curves

---

## Belief Sensitivity Experiment (Feb 20-23) — ACTIVE

### Motivation

The market and conflict experiments measure how LLM agents *coordinate* and how external forecasters *predict* outcomes. The belief sensitivity experiment asks a complementary question: **how robust are LLM forecasts to targeted challenges?**

When an LLM produces a probability estimate for a real-world event, does it:
- Anchor too strongly (barely shift regardless of challenge)?
- Update rationally (shift proportional to challenge strength)?
- Cave easily (large shifts from weak challenges)?

This reveals calibration properties that PID and forecasting experiments cannot detect.

### Two Modes

#### Flat-Reasons Mode (`--mode reasons`, default)

**Pipeline (3 stages):**

| Stage | Input | Output | Shared? |
|-------|-------|--------|---------|
| 1. Initial forecast | Binary question | Probability + 3-5 explicit reasons (each rated high/medium/low importance) | Yes |
| 2. Probe generation | Each reason × 5 types | Targeted challenge (negation, counterfactual, weakening, strengthening, irrelevant) | Yes |
| 3. Probed forecast | Challenge + context | Updated probability | No — differs by condition |

**Experimental factors:**

| Factor | Levels |
|--------|--------|
| Condition | one-turn, multi-turn |
| Probe type | negation, counterfactual, weakening, strengthening, irrelevant |
| Reason importance | high, medium, low |

~20 probes per question, ~650 calls for 50 questions × 2 conditions.

#### Causal Network Mode (`--mode causal`)

Replaces flat reasons with a directed causal graph. Probes target structural elements of the graph, providing a network-theoretic basis for measuring probe importance.

**Pipeline (4 stages):**

| Stage | Input | Output | LLM? |
|-------|-------|--------|------|
| 1. Causal forecast | Binary question | Probability + causal graph (4-8 factor nodes, 1 outcome, directed edges with mechanisms) | Yes |
| 1.5. Network analysis | Causal graph | Node centralities, edge betweenness, composite importance scores, ~16 probe targets, network visualization (PNG) | No |
| 2. Probe generation | Each target | One probe per structural target | Yes |
| 3. Probed forecast | Probe + network context | Updated probability | Yes |

**10 probe types across 3 categories:**

| Probe Type | Category | Target | Count | Purpose |
|---|---|---|---|---|
| `node_negate_high` | node | High-centrality node | 2 | Core hypothesis test |
| `node_negate_medium` | node | Medium-centrality node | 1 | Calibration check |
| `node_negate_low` | node | Low-centrality node | 1 | Baseline comparison |
| `node_strengthen` | node | High-centrality node | 2 | Asymmetry test (neg vs pos) |
| `edge_negate_critical` | edge | Critical-path edge | 2 | Edge importance test |
| `edge_negate_peripheral` | edge | Non-critical edge | 1 | Edge baseline |
| `edge_reverse` | edge | Critical-path edge | 1 | Direction sensitivity |
| `edge_spurious` | edge | Missing-edge candidate | 2 | Spurious acceptance |
| `missing_node` | structural | LLM-generated | 2 | Structural vulnerability |
| `irrelevant` | structural | LLM-generated | 2 | Control (should not shift) |

**Network analysis metrics (per node):**
- In/out-degree, betweenness centrality, closeness centrality, PageRank
- Path relevance (fraction of shortest paths to outcome passing through node)
- Composite importance: 0.3 × betweenness + 0.2 × PageRank + 0.2 × out_degree_norm + 0.3 × path_relevance

**Core hypothesis**: Probing structurally important elements (high-centrality nodes, critical-path edges) should produce larger probability shifts than probing peripheral elements.

**Network visualization**: Each elicited causal graph is saved as a PNG plot (`outputs/network_plots/q_{id}_network.png`). Factor nodes are colored by composite importance (blue gradient — darker = higher), outcome node shown as a gold square, critical-path edges highlighted in red. Plots are generated automatically during the pipeline run and retroactively for cached results on resume.

~18 probes per question, ~3,700 calls for 50 questions × 2 conditions.

### Conditions (both modes)

| Condition | Description |
|-----------|-------------|
| **One-turn** | Fresh 2-message API call per probe (system + user). No memory of prior probes. |
| **Multi-turn** | Growing messages array. Model sees all prior probes and its own responses. |

### Analysis Metrics

**Base metrics (both modes):**
1. **Anchoring**: Mean/median absolute shift, % no-change (<1%), % small-shift (<5%)
2. **Sensitivity by probe type**: Mean shift per type
3. **Conversational drift**: Spearman correlation of probe order vs cumulative shift
4. **Condition comparison**: Paired t-test + Cohen's d (multi-turn vs one-turn)

**Reasons-mode specific:**
5. **Sensitivity by importance**: high vs medium vs low reason importance

**Causal-mode specific (6 network metrics):**
5. **Importance-sensitivity correlation**: Spearman(composite_importance, |shift|) — does centrality predict sensitivity?
6. **Structural sensitivity ratio (SSR)**: mean_shift(high-importance) / mean_shift(low-importance) — >1 = calibrated
7. **Sensitivity by probe category**: node vs edge vs structural mean shifts
8. **Critical path premium**: mean_shift(on-path) - mean_shift(off-path)
9. **Spurious acceptance rate**: fraction of spurious probes where |shift| ≥ 0.05
10. **Asymmetry index**: mean_shift(negation) / mean_shift(strengthening) — >1 = negativity bias

### Smoke Test Results (Causal, 2 questions, one-turn, Feb 23)

| Metric | Value |
|--------|-------|
| API calls | 64 (0 failures, 0 parse failures) |
| Mean absolute shift | 0.141 |
| SSR | 1.10 (slight calibration to importance) |
| Importance-sensitivity rho | 0.19 (weak positive — expected with n=2) |
| Critical path premium | +0.007 |
| Spurious acceptance | 85.7% (6/7 spurious probes accepted) |
| Asymmetry index | 0.86 (slight confirmation bias) |
| Irrelevant probe mean shift | 0.078 (lowest — good control) |

### Full Run Results (Causal, Llama 3.3 70B, one-turn, Feb 24)

50 questions, 784 successful probes (50 shared causal stages cached).

**Anchoring:**

| Metric | Value |
|--------|-------|
| N probes | 784 |
| Mean absolute shift | 8.64pp |
| Median absolute shift | 6.0pp |
| % no change (<1pp) | 4.1% |
| % small shift (<5pp) | 32.7% |

**Sensitivity by Probe Type:**

| Probe Type | Mean Shift | Median Shift | n |
|---|---|---|---|
| node_strengthen | **15.14pp** | 15.5pp | 100 |
| missing_node | **14.22pp** | 14.5pp | 100 |
| node_negate_high | 9.94pp | 7.5pp | 100 |
| edge_spurious | 9.04pp | 8.0pp | 84 |
| node_negate_medium | 7.74pp | 6.0pp | 50 |
| edge_negate_critical | 6.87pp | 6.0pp | 100 |
| node_negate_low | 6.40pp | 5.0pp | 50 |
| edge_negate_peripheral | 5.64pp | 4.5pp | 50 |
| edge_reverse | 5.26pp | 4.5pp | 50 |
| irrelevant | **1.46pp** | 1.0pp | 100 |

**Key findings at n=50:**

1. **Structural sensitivity is well-calibrated.** The importance gradient holds clearly: high-importance node negations (9.94pp) > medium (7.74pp) > low (6.40pp). Critical-path edge negations (6.87pp) > peripheral (5.64pp).

2. **Strengthen probes cause the largest shifts (15.14pp).** Models are more responsive to confirmatory evidence than to negation — asymmetry index < 1 indicates confirmation bias (strengthen/negate ratio ~1.52).

3. **Missing node probes are highly effective (14.22pp).** The model readily incorporates novel causal factors not in its original network, suggesting vulnerability to framing effects.

4. **Irrelevant probes are well-controlled (1.46pp).** The lowest shift of any probe type, confirming the model doesn't shift indiscriminately. This validates the experimental design.

5. **Spurious edge acceptance remains high (9.04pp mean shift).** Spurious edges produce shifts comparable to high-importance node negations, suggesting the model doesn't robustly validate proposed causal links.

6. **Edge reversal has minimal impact (5.26pp).** Reversing causal direction on critical-path edges produces less shift than negating them entirely, suggesting models are more sensitive to existence than directionality of causal links.

### Statistical Significance (Welch t-tests, two-tailed)

**One-way ANOVA**: F(9, 774) = 51.71, p << 0.001, η² = 0.376 — probe type explains 37.5% of the variance in probability shift.

**Importance gradient (node negations):**

| Comparison | Mean A | Mean B | t | p | sig | Cohen's d |
|---|---|---|---|---|---|---|
| High vs Low | 9.94pp | 6.40pp | 3.44 | 5.9e-4 | *** | 0.50 |
| High vs Medium | 9.94pp | 7.74pp | 1.95 | 0.051 | ns | 0.30 |
| Medium vs Low | 7.74pp | 6.40pp | 1.30 | 0.193 | ns | 0.26 |

The full high-vs-low gradient is significant (p<0.001, medium effect), but adjacent tiers are not individually significant — the gradient exists but the steps are noisy.

**Key significant differences:**

| Comparison | Mean A | Mean B | t | p | sig | Cohen's d |
|---|---|---|---|---|---|---|
| Strengthen vs Negate (high) | 15.14pp | 9.94pp | 5.21 | 1.9e-7 | *** | 0.74 |
| Spurious edge vs Irrelevant | 9.04pp | 1.46pp | 13.24 | ~0 | *** | 2.10 |
| Missing node vs Irrelevant | 14.22pp | 1.46pp | 16.19 | ~0 | *** | 2.29 |
| Low negation vs Irrelevant | 6.40pp | 1.46pp | 7.32 | 2.5e-13 | *** | 1.63 |
| Spurious edge vs Critical edge negation | 9.04pp | 6.87pp | 3.31 | 9.3e-4 | *** | 0.50 |
| Node negation (high) vs Edge negation (critical) | 9.94pp | 6.87pp | 3.50 | 4.7e-4 | *** | 0.49 |
| Edge negation vs Edge reversal (critical) | 6.87pp | 5.26pp | 2.27 | 0.023 | * | 0.42 |

**Not significant:**

| Comparison | Mean A | Mean B | p | Interpretation |
|---|---|---|---|---|
| Strengthen vs Missing node | 15.14pp | 14.22pp | 0.345 | Both produce ~15pp shifts |
| High vs Medium negation | 9.94pp | 7.74pp | 0.051 | Borderline |
| Critical vs Peripheral edge | 6.87pp | 5.64pp | 0.083 | Edge importance gradient is weak |

**Key takeaway:** Spurious edges cause significantly larger shifts than negating actual critical-path edges (9.04pp vs 6.87pp, p<0.001, d=0.50). The model is more responsive to invented causal structure than to challenges against its own reasoning. All probe types produce significantly larger shifts than irrelevant controls (even the weakest — peripheral edge negation at 5.64pp vs 1.46pp, p<1e-10).

### Status

| Phase | Status | Details |
|-------|--------|---------|
| 1. Reasons-mode pipeline | Complete | 5 files in `forecast_bench/` |
| 2. Reasons-mode runs | Complete | 50 questions × 2 conditions |
| 3. Causal-mode pipeline | **Complete** | 3 new files + runner modifications |
| 4. Causal-mode smoke test | **Complete** | 2 questions × one-turn, 100% success |
| 5. Causal-mode full run (one-turn) | **Complete** | 50 questions, 784 probes, Llama 3.3 70B |
| 5b. Causal-mode full run (multi-turn) | **Next** | 50 questions × multi-turn condition |
| 6. Cross-mode comparison | Pending | Compare flat-reasons vs causal network results |

### Files
- `forecast_bench/llm_client.py` — OpenRouter client (single-shot + multi-turn)
- `forecast_bench/questions.py` — ForecastBench loader (HuggingFace + fallback)
- `forecast_bench/prompts.py` — Flat-reasons prompt templates (stages 1-3)
- `forecast_bench/prompts_causal.py` — Causal network prompt templates (stages 1-3)
- `forecast_bench/network_analysis.py` — Graph centrality, composite importance, target selection, network visualization (networkx + matplotlib)
- `forecast_bench/run_sensitivity.py` — Main pipeline runner (`--mode reasons|causal`)
- `forecast_bench/analysis.py` — Flat-reasons metrics (anchoring, drift, condition comparison)
- `forecast_bench/analysis_causal.py` — Network-specific metrics (SSR, path premium, false negative rate, asymmetry)

### Usage

```bash
# --- Flat-reasons mode (default) ---
python forecast_bench/run_sensitivity.py --max-questions 2 --condition one-turn
python forecast_bench/run_sensitivity.py --max-questions 50 --condition both
python forecast_bench/analysis.py outputs/sensitivity_llama_one-turn outputs/sensitivity_llama_multi-turn

# --- Causal network mode ---
python forecast_bench/run_sensitivity.py --mode causal --max-questions 2 --condition one-turn
python forecast_bench/run_sensitivity.py --mode causal --max-questions 50 --condition both
python forecast_bench/analysis_causal.py outputs/sensitivity_causal_llama_one-turn outputs/sensitivity_causal_llama_multi-turn

# Resume interrupted run (either mode)
python forecast_bench/run_sensitivity.py --mode causal --max-questions 50 --condition both --resume
```

### Next Steps

**Immediate:**

- [x] Run causal mode one-turn: 50 questions, Llama 3.3 70B — **Complete** (784 probes, Feb 24)
- [x] Run causal analysis — **Complete** (experiment_summary.json saved)
- [ ] Run causal mode multi-turn: `--mode causal --max-questions 50 --condition multi-turn` (~1,850 calls)
- [ ] Run causal analysis on both output dirs + condition comparison
- [ ] Core hypothesis test: compute importance-sensitivity Spearman rho with `analysis_causal.py` (SSR, asymmetry index, critical path premium)

**Analysis (after multi-turn run):**

- [ ] Cross-mode comparison — compare flat-reasons vs causal network results on the same 50 questions. Does structural framing change the model's sensitivity pattern?
- [ ] Spurious acceptance deep dive — spurious acceptance produces 9.04pp mean shift (comparable to high-importance negation). Characterize which spurious edges are accepted vs rejected (outcome-adjacent? semantically plausible?)
- [ ] Graph quality analysis — assess the elicited causal graphs: are they DAGs? How many edges on average? Do they vary meaningfully across questions? Correlate graph complexity (density, n_nodes) with sensitivity patterns
- [ ] SSR stability — does the structural sensitivity ratio hold at >1 across questions, or is it driven by a few outliers?
- [ ] Confirmation bias investigation — strengthen (15.14pp) >> negate_high (9.94pp). Is this consistent across question types or driven by specific domains?

**Extensions:**

- [ ] Model comparison — run causal mode on DeepSeek V3 or a larger model to see if structural calibration improves with scale
- [ ] Connect to causal discovery — the causal discovery experiment tests whether LLMs can *recover* ground-truth graphs; causal sensitivity tests whether they can *defend* self-constructed graphs. Compare failure modes (path collapse in discovery vs spurious acceptance in sensitivity)
- [ ] Importance weight tuning — the composite importance formula (0.3×betweenness + 0.2×PageRank + 0.2×out_degree + 0.3×path_relevance) was chosen heuristically. Post-hoc analysis: which single metric best predicts actual sensitivity?

---

## Causal Discovery (Feb 19-20) — IN PROGRESS

### Motivation

The market and conflict experiments establish that LLM agent groups exhibit emergent coordination (PID synergy) and that persona knowledge helps/hurts forecasting depending on domain. The causal discovery experiment asks: **can LLM agents recover the known causal structure of these simulations through targeted interventional queries?**

This extends the framework from behavioral coordination → epistemic coordination. If groups of modeler agents can recover more of the causal graph than individuals (especially when their edge-level PID synergy is high), it validates PID as a measure of epistemic coordination.

### Pilot Results (Single Agent, Budget=30, 3 Replicates Each)

All runs use Llama 3.3 70B via OpenRouter, multi-turn conversation, role/faction-level overrides.

**Cross-domain comparison (Feb 21):**

| Domain | Mean F1 | Mean Precision | Mean Recall | Mean SHD | True Edges |
|--------|---------|----------------|-------------|---------|------------|
| **Market** | 0.256 ± 0.052 | 0.487 ± 0.109 | 0.174 ± 0.036 | 23.3 ± 1.9 | 23 |
| **Conflict** | 0.235 ± 0.130 | 0.500 ± 0.136 | 0.159 ± 0.098 | 20.3 ± 1.7 | 21 |

**Per-replicate detail:**

| Run | P | R | F1 | SHD | Edges | Dup | No-effect |
|-----|---|---|----|----|-------|-----|-----------|
| Market seed42 | 0.571 | 0.174 | 0.267 | 22 | 7/23 | 3 | 9 |
| Market seed43 | 0.333 | 0.130 | 0.188 | 26 | 9/23 | 1 | 10 |
| Market seed44 | 0.556 | 0.217 | 0.312 | 22 | 9/23 | 3 | 9 |
| Conflict seed42 | 0.333 | 0.048 | 0.083 | 22 | 3/21 | 8 | 4 |
| Conflict seed43 | 0.667 | 0.286 | 0.400 | 18 | 9/21 | 7 | 2 |
| Conflict seed44 | 0.500 | 0.143 | 0.222 | 21 | 6/21 | 10 | 1 |

### Key Findings

**Shared failure modes (both domains, baseline Llama runs):**

1. **Under-declaration** — The model declares only 3-9 edges out of 21-23 true edges. Recall is the bottleneck (~16%). It only reports edges it directly tested and misses all state-update and feedback edges it never probed.

2. **Path collapse / indirect-as-direct** — The model collapses multi-step causal paths into direct edges. Market: `demand_value → clearing_price` instead of `demand_value → agent_orders → clearing_price`. Conflict: `hawk_score → escalation_index` instead of `hawk_score → agent_recommendation → faction_action → escalation_index`.

**Market-specific:**

3. **Confound trap** — `fundamental_price → clearing_price` is hallucinated in 3/3 runs. They share common causes (production_cost, demand_value) but the model never intervenes on the mediator to distinguish correlation from causation.

4. **Reliable core recovery** — The clearing mechanism (`agent_orders → clearing_price`, `agent_orders → volume`) is recovered 3/3 times. The diagnostic output edges (`production_cost → fundamental_price`, `demand_value → fundamental_price`) are also reliable. But everything else (shock effects, feedback loops, state updates) is missed.

**Conflict-specific:**

5. **Severe duplication** — 7-10 duplicate interventions per run (vs 1-3 for market). The model exhausts novel intervention ideas by ~intervention 15 and starts repeating. The conflict domain has fewer parameter dimensions to vary (hawk_dove is the main trait vs production_cost, demand_value, demand_per_period, etc. in market).

6. **Decision chain missed** — `agent_recommendation → faction_action` is recovered 0/3 times. The aggregation step (weighted voting within factions) is invisible to the model because it never tested individual vs faction-level overrides comparatively.

7. **Higher variance** — F1 ranges from 0.083 to 0.400 across replicates (market: 0.188 to 0.312). The conflict domain outcome is more sensitive to which interventions the model happens to choose.

### Root Cause Analysis & Fixes (Feb 21)

**Root cause: Data observability, not model quality.** Two models (Llama 3.3 70B and DeepSeek V3) produced identical failure patterns on the original return variables. Market trajectories only returned 3 variables (clearing_price, volume, fundamental_price), making intermediate variables like `agent_orders` invisible. Without seeing mediators change, no model could distinguish direct from indirect effects.

**Fixes applied:**

1. **Expanded return variables** — Market: added aggregate order stats (avg_bid/ask_price, total_bid/ask_qty) and agent state (total_cash, total_inventory) as scalar proxies for `agent_orders`, `cash`, `inventory`. Conflict: added faction-level state ({faction}_gdp, _military_strength, _political_stability), recommendation escalation deltas, and faction action deltas.

2. **Evidence summary** — Programmatic (no LLM) function that scans all intervention results and builds per-variable tables of what moved when. Provided at declaration time so the model doesn't need to recall from a long conversation.

3. **Per-variable enumeration** — Rewrote declaration prompt to enumerate parents/children for each variable. Instructs model to err on the side of inclusion (include moderate-evidence edges).

4. **Truncated declaration context** — Fresh 2-message conversation for declaration instead of full 69k-token multi-turn history. Eliminates context saturation.

5. **Invalid intervention type guard** — Rejects invented types (e.g., "terminate") and asks the model to propose a valid action/trait/event intervention.

**Results after fixes (single runs, DeepSeek V3):**

| Run | Domain | Model | Precision | Recall | F1 | SHD |
|-----|--------|-------|-----------|--------|----|----|
| Baseline (3-rep avg) | Market | Llama 3.3 70B | 0.487 | 0.174 | 0.256 | 23.3 |
| + all fixes | Market | DeepSeek V3 | 0.417 | 0.652 | 0.508 | 17 |
| Baseline (3-rep avg) | Conflict | Llama 3.3 70B | 0.500 | 0.159 | 0.235 | 20.3 |
| + all fixes | Conflict | DeepSeek V3 | 0.300 | 0.286 | 0.293 | 19 |

Market recall jumped 17% → 65% (F1 nearly doubled). Conflict recall improved 16% → 29% — smaller gain because conflict chains are longer (3 hops vs 2) and the interaction modifier creates nonlinearities harder to detect with single-variable interventions.

### Infrastructure Decisions

- **Role-level trait overrides**: `{"role": "producer", "param": "production_cost", "value": 200}` overrides ALL producers, not just one. Same for `{"faction": "novaris", ...}` in conflict. Solves the infra-marginal agent problem.
- **Multi-turn conversation**: Persistent message history replaces stateless 2-message calls. Model sees full history including past interventions and its own reasoning. Eliminates repetition (mostly — conflict still has duplication due to limited parameter space).
- **JSON mode**: Added `response_format: {"type": "json_object"}` to API calls for reliable structured output.
- **Domain CLI**: `--domain market|conflict` routes to `run_pilot()` or `run_conflict_pilot()` with auto-selected output directories.

### Status

| Phase | Status | Details |
|-------|--------|---------|
| 1. Intervention interface | Complete | Market + conflict, 3 types each, role/faction-level |
| 2. Ground truth + scoring | Complete | Adjacency matrices, SHD, precision/recall |
| 3. Single-agent pilot (market) | **Complete** | 3 replicates @ budget=30, F1=0.256±0.052 |
| 4. Infrastructure fixes | Complete | Role-level overrides, multi-turn conversation |
| 5. Single-agent pilot (conflict) | **Complete** | 3 replicates @ budget=30, F1=0.235±0.130 |
| 6. Recall improvement | **Complete** | Expanded return vars, evidence summary, truncated context -> Market F1=0.508, Conflict F1=0.293 |
| 7. Multi-agent conditions | **Complete** | 4 structures x 2 domains, dry-run + live (Llama 3.3 70B) |
| 8. Causal forecasting test | **In progress** | Rolling window, 4 conditions (discovered/GT/no_graph/adaptive), market live done, conflict pending |
| 9. PID analysis | **Next** | Edge-level epistemic coordination |

### Files

- `causal_discovery/intervention.py` — Clamp-and-react rollouts (action, trait, event), expanded return vars
- `causal_discovery/run_pilot.py` — Single-agent pilot runner (market + conflict, multi-turn, truncated declaration)
- `causal_discovery/prompts.py` — Causal modeler agent prompts, evidence summary builder
- `causal_discovery/prompts_tests.py` — Shared prompts for supplementary tests (forecast, graph revision, Oracle QA, hidden variable)
- `causal_discovery/ground_truth.py` — Ground truth adjacency matrices + scoring
- `causal_discovery/test_intervention.py` — Smoke tests for intervention interface
- `causal_discovery/causal_forecast.py` — Causal forecasting test: rolling window, 4 conditions + per-step adaptive revision
- `causal_discovery/multi_agent/` — Multi-agent causal discovery package (Feb 24):
  - `agent.py` — Extracted single-agent pipeline (AgentResult dataclass, setup_domain, run_single_agent)
  - `aggregation.py` — Graph merging: majority_vote, confidence_weighted_vote, union_merge, intersection_merge
  - `config.py` — 5 causal reasoning personas, maximalist/minimalist debate pair, variable subgraphs per domain
  - `prompts_multi.py` — Prompt builders: persona injection, specialist constraints, debate injection, LLM aggregator
  - `independent.py` — N=5 agents in parallel, persona-diverse, vote to merge
  - `debate.py` — 2 agents alternate interventions from shared budget, share results + debate injection
  - `specialization.py` — 3 variable-subset specialists + 1 LLM aggregator
  - `runner.py` — CLI for single condition (`python -m causal_discovery.multi_agent.runner`)
  - `run_all.py` — Sweep all conditions x both domains, produces comparison.json
- `docs/CAUSAL_DISCOVERY_DESIGN.md` — Full design document
- Baseline results: `outputs/causal_discovery/pilot_runs/run_{1,2,3}_seed{42,43,44}/`
- Baseline results: `outputs/causal_discovery/conflict_pilot_runs/run_{1,2,3}_seed{42,43,44}/`
- Post-fix results: `outputs/causal_discovery/pilot_runs/recall_fix_test/` (market, DeepSeek V3)
- Post-fix results: `outputs/causal_discovery/conflict_pilot_runs/recall_fix_test/` (conflict, DeepSeek V3)
- Forecast results: `outputs/causal_discovery/causal_forecast/{domain}_{model}/`

### Multi-Agent Implementation (Feb 24)

**Design:** 4 communication structures (single, independent, debate, specialization) x 2 domains, all with total budget=30 for fair comparison.

| Condition | Agents | Per-Agent Budget | Design |
|-----------|--------|-----------------|--------|
| Single | 1 | 30 | Baseline (reuses run_pilot.py) |
| Independent | 5 diverse personas | 6 each | Interventionist, correlational, structural, feedback_hunter, parsimony |
| Debate | 2 opposing | 15 each (alternating) | Maximalist (high recall) vs minimalist (high precision) |
| Specialization | 3 + 1 aggregator | ~10 each (proportional) | Supply/demand/dynamics (market) or military/economic/political (conflict) |

**Aggregation methods:** majority vote, confidence-weighted (high=3, medium=2, low=1), union merge, intersection merge. Specialization also uses an LLM aggregator that sees all specialists' declared edges + evidence summaries.

**Key design decisions:**
- Budget split is fair: all conditions use exactly 30 total interventions
- Independent personas are causal-reasoning-specific (not reused from forecast_multi)
- Debate uses global dedup across both agents to prevent redundant interventions
- Specialization enforces variable constraints: specialists can only target their assigned variables for trait interventions, but see full observation data
- All conditions share the same domain setup (warmup, snapshots) via `setup_domain()`

**Dry-run verification (Feb 24):** All 8 conditions (4 x 2 domains) pass with budget=30. Scores identical in dry-run due to deterministic mock responses.

### Live Results (Feb 24, Llama 3.3 70B via OpenRouter, budget=30, seed=42)

**Market Domain (12 variables, 23 true edges):**

| Condition | Primary Method | F1 | Precision | Recall | LLM Calls |
|-----------|---------------|-----|-----------|--------|-----------|
| **Single** | — | **0.517** | 0.429 | 0.652 | 58 |
| Independent | majority_vote | 0.444 | 0.455 | 0.435 | 70 |
| Debate | union | 0.500 | 0.424 | 0.609 | 57 |
| Specialization | llm_aggregator | 0.508 | 0.400 | **0.696** | 65 |

**Conflict Domain (13 variables, 26 true edges):**

| Condition | Primary Method | F1 | Precision | Recall | LLM Calls |
|-----------|---------------|-----|-----------|--------|-----------|
| Single | — | 0.444 | 0.417 | 0.476 | 57 |
| Independent | majority_vote | 0.294 | 0.385 | 0.238 | 70 |
| **Debate** | union | **0.531** | **0.464** | **0.619** | 52 |
| Specialization | llm_aggregator | 0.303 | 0.417 | 0.238 | 60 |

**Key findings:**

1. **Debate wins on conflict (+20% F1 over single).** The maximalist/minimalist debate structure produced the best conflict F1 (0.531 vs 0.444 single). Shared evidence from alternating interventions helps both agents build better graphs than either could alone.

2. **Single agent wins on market.** The full 30-intervention budget concentrated in one agent (F1=0.517) slightly outperforms all multi-agent structures. Specialization comes closest (0.508) with the best recall (0.696).

3. **Independent consistently underperforms.** With only 6 interventions per agent (30/5), none can build reliable causal models. Market F1=0.444, conflict F1=0.294 — worst in both domains.

4. **Specialization is domain-dependent.** Works well on market (F1=0.508, best recall 0.696) where variable subgraphs (supply/demand/dynamics) map cleanly to the true causal structure. Fails on conflict (F1=0.303) where the subgraphs (military/economic/political) don't align well — many cross-domain causal links are missed.

5. **Debate agents converge.** In both domains, maximalist and minimalist agents declare identical graphs. Shared evidence dominates persona differences — the debate injection doesn't meaningfully differentiate their conclusions.

6. **Budget fragmentation is the main bottleneck.** The gap between single (30 interventions) and independent (6 each) shows that intervention count drives accuracy more than diversity. Debate (15 each + shared evidence) partially mitigates this.

### Single-Agent Per-Edge Breakdown

Detailed per-edge analysis of the single-agent baseline (budget=30, Llama 3.3 70B, seed=42). Plots saved in `outputs/causal_discovery/multi_agent/plots/`.

**Market — True Positives (15/23 recovered):**

| Edge | Notes |
|------|-------|
| `production_cost → agent_orders` | Core mechanism |
| `demand_value → agent_orders` | Core mechanism |
| `demand_per_period → agent_orders` | Core mechanism |
| `cash → agent_orders` | State constraint |
| `inventory → agent_orders` | State constraint |
| `agent_orders → clearing_price` | Clearing mechanism |
| `agent_orders → volume` | Clearing mechanism |
| `production_cost → cash` | Period costs |
| `production_cost → inventory` | Period costs |
| `production_cost → fundamental_price` | Diagnostic output |
| `demand_value → cash` | Period costs |
| `demand_value → fundamental_price` | Diagnostic output |
| `demand_per_period → inventory` | Period costs |
| `storage_cost → cash` | Period costs |
| `shock → cash` | Shock effect |

**Market — False Negatives (8/23 missed):**

| Edge | Failure Mode |
|------|-------------|
| `shock → production_cost` | Agent tested shock but attributed effects directly to downstream variables |
| `shock → demand_per_period` | Same — path collapse through shock |
| `shock → storage_cost` | Same |
| `storage_cost → agent_orders` | Never tested storage_cost's effect on orders |
| `price_history → agent_orders` | Feedback loop — never probed |
| `clearing_price → cash` | Feedback loop — never probed |
| `clearing_price → inventory` | Feedback loop — never probed |
| `clearing_price → price_history` | Feedback loop — never probed |

All 4 feedback edges (`clearing_price → cash/inventory/price_history`, `price_history → agent_orders`) were missed — the agent never designed interventions to test the feedback loop.

**Market — False Positives (20 spurious edges):**

Path collapse is the dominant pattern. The agent observes end-to-end effects from interventions and declares direct edges:
- `shock → agent_orders/clearing_price/volume/inventory/fundamental_price` (5 edges) — shock's effects are mediated through parameters, but declared as direct
- `demand_per_period → clearing_price/volume/cash/fundamental_price` (4 edges) — mediated through agent_orders
- `demand_value → clearing_price/volume/inventory` (3 edges) — mediated through agent_orders
- `production_cost → clearing_price/volume` (2 edges) — mediated through agent_orders
- `cash → clearing_price/volume/inventory` (3 edges) — cash constrains orders, not prices directly
- `agent_orders → cash/inventory` (2 edges) — reversed feedback (clearing_price mediates)
- `inventory → cash` (1 edge) — spurious

**Conflict — True Positives (10/21 recovered, scored against pre-Feb 27 ground truth):**

> **NOTE (Feb 27):** Ground truth updated to 26 edges. Added 6 state feedback edges
> (gdp/military_strength/political_stability/sanctions/international_support/military_balance
> → agent_recommendation) via `compute_state_modifier`. Removed spurious
> `escalation_index → sanctions_level` (sanctions driven by faction_action, not EI).
> The TP below for `escalation_index → sanctions_level` is now a false positive under the
> new ground truth. Results below are historical; re-run with Qwen models in progress.

| Edge | Notes |
|------|-------|
| `shock → escalation_index` | Direct shock effect |
| `shock → resources` | Economic crisis effect |
| `shock → military_balance` | Military incident effect |
| `shock → sanctions_level` | International pressure effect |
| `hawk_score → agent_recommendation` | Disposition → decision |
| `agent_recommendation → faction_action` | Aggregation step |
| `escalation_index → gdp` | State update |
| `escalation_index → sanctions_level` | State update |
| `faction_action → resources` | Action cost |
| `faction_action → sanctions_level` | Escalatory actions increase sanctions |

**Conflict — False Negatives (11/21 missed):**

| Edge | Failure Mode |
|------|-------------|
| `faction_action → escalation_index` | Agent never tested faction_action's direct effect on EI |
| `faction_action → military_strength` | Never probed |
| `faction_action → territory_controlled` | Never probed |
| `escalation_index → agent_recommendation` | Feedback loop — never tested |
| `escalation_index → political_stability` | State update — never tested |
| `escalation_index → international_support` | State update — never tested |
| `resources → agent_recommendation` | Affordability constraint — never tested |
| `gdp → resources` | Cross-variable state update |
| `sanctions_level → gdp` | Cross-variable state update |
| `military_strength → military_balance` | Cross-variable state update |
| `military_balance → territory_controlled` | Cross-variable state update |

The entire state-update and cross-variable chain is missed. The agent focused its budget on shock/hawk_score/agent_recommendation interventions and never tested EI or faction_action as causal *sources*.

**Conflict — False Positives (14 spurious edges):**

Path collapse from `hawk_score` is the worst offender (6 FP edges):
- `hawk_score → escalation_index/resources/gdp/military_strength/political_stability/sanctions_level` — all mediated through `agent_recommendation → faction_action → ...` but declared direct

`agent_recommendation` also shows path collapse (5 FP edges):
- `agent_recommendation → escalation_index/military_strength/resources/sanctions_level/territory_controlled` — mediated through `faction_action`

Other: `escalation_index → resources` (1), `faction_action → gdp` (1), `shock → gdp` (1).

**Per-node summary:**

| Market Node | TP | FP | FN | | Conflict Node | TP | FP | FN |
|-------------|----|----|----|-|---------------|----|----|------|
| orders | 6 | 4 | 2 | | escalation | 4 | 3 | 6 |
| cash | 5 | 5 | 2 | | agent_rec | 2 | 5 | 3 |
| clearing_price | 1 | 5 | 3 | | faction_act | 4 | 3 | 3 |
| inventory | 3 | 4 | 2 | | resources | 2 | 4 | 3 |
| shock | 1 | 5 | 3 | | hawk_score | 1 | 6 | 0 |
| demand_qty | 2 | 4 | 1 | | sanctions | 4 | 2 | 2 |
| prod_cost | 4 | 2 | 1 | | gdp | 1 | 3 | 2 |
| volume | 1 | 4 | 0 | | shock | 4 | 1 | 0 |
| demand_val | 3 | 3 | 0 | | mil_strength | 0 | 2 | 2 |
| fund_price | 2 | 1 | 0 | | territory | 0 | 1 | 2 |
| stor_cost | 1 | 0 | 2 | | mil_balance | 1 | 0 | 2 |
| price_hist | 0 | 0 | 2 | | pol_stability | 0 | 1 | 1 |
| | | | | | intl_support | 0 | 0 | 1 |

Key patterns:
- **Market `clearing_price`**: only 1 TP (orders → clearing_price) but 5 FP — the agent treats it as a sink for everything
- **Conflict `hawk_score`**: 1 TP, 6 FP — worst precision of any node, all due to path collapse
- **Market `price_history`**: 0 TP, 0 FP, 2 FN — completely invisible to the agent (feedback loop)
- **Conflict `intl_support`, `pol_stability`, `territory`**: mostly missed, the agent never reached these peripheral state variables

See network plots: `outputs/causal_discovery/multi_agent/plots/single_agent_networks.png` and per-node bar chart: `outputs/causal_discovery/multi_agent/plots/single_agent_node_breakdown.png`.

**Aggregation method comparison (market independent):**

| Method | F1 | Notes |
|--------|-----|-------|
| majority_vote | 0.444 | Edge if >50% of agents declare |
| confidence_weighted | 0.444 | Weighted by high/medium/low confidence |
| union | 0.449 | Edge if any agent declares |

Aggregation method made little difference — the bottleneck is per-agent evidence quality, not merging strategy.

### Usage

```bash
# Single condition
python -m causal_discovery.multi_agent.runner \
    --domain market --communication independent --budget 30 --dry-run

# Full sweep
python -m causal_discovery.multi_agent.run_all --budget 30 --dry-run

# Live run (requires OPENROUTER_API_KEY)
python -m causal_discovery.multi_agent.run_all --budget 30
```

### To-Do

**Immediate (before live runs):**

- [ ] Run 3 replicates on market with DeepSeek V3 + all fixes (current results are single runs — need variance estimates)
- [ ] Run 3 replicates on conflict with DeepSeek V3 + all fixes
- [ ] Investigate conflict recall gap (29% vs market 65%) — try: (a) multi-variable interventions to detect interaction modifier, (b) explicitly prompt model about aggregation step, (c) longer rollout periods (run_periods=5 instead of 3) to let longer chains propagate
- [ ] Ground truth edge audit: `storage_cost -> agent_orders` doesn't hold in rule-based sim — consider removing (1/23 edges)

**Multi-agent live runs (Phase 7):**

- [x] Implement 4 communication structures (single, independent, debate, specialization)
- [x] Design specialization assignments (variable subsets per domain)
- [x] Dry-run verification: all 8 conditions pass
- [x] Run all 4 conditions x 2 domains with live LLM calls (Llama 3.3 70B, budget=30)
- [x] Compare aggregation methods: majority vote vs confidence-weighted vs union — minimal difference (~0.005 F1)
- [x] Analyze multi-agent vs single-agent: debate wins conflict (+20%), single wins market; independent underperforms everywhere
- [ ] Run 3 replicates per condition for variance estimates
- [ ] Investigate debate convergence: both agents declare identical graphs — does debate injection need stronger persona enforcement?

**PID analysis (Phase 8):**

- [ ] Adapt edge-level PID for causal discovery (source: agent_i confidence on edge_k, target: ground truth)
- [ ] Determine number of scenarios needed for reliable Williams-Beer estimation (currently estimated 10-20+)
- [ ] Correlate EC with graph recovery quality across conditions

**Other:**

- [ ] Model comparison on improved pipeline (Llama 3.3 70B vs DeepSeek V3 vs others)
- [ ] Consider whether conflict ground truth needs coarser granularity (collapse agent_recommendation + faction_action?) to be recoverable at budget=30

### Qwen Model Comparison (Feb 27)

**Motivation:** Test causal discovery across a wider parameter range than Llama offers. Qwen family has 7B, 72B, and 235B (MoE) variants on OpenRouter, enabling a clean scaling comparison.

**Models — Llama scaling comparison:**
| Model | Parameters | OpenRouter ID |
|-------|-----------|---------------|
| Llama 3.1 8B | 8B | `meta-llama/llama-3.1-8b-instruct` |
| Llama 3.3 70B | 70B | `meta-llama/llama-3.3-70b-instruct` |

**Models — Qwen scaling comparison (to-do):**
| Model | Parameters | OpenRouter ID |
|-------|-----------|---------------|
| Qwen 2.5 7B | 7B | `qwen/qwen-2.5-7b-instruct` |
| Qwen 2.5 72B | 72B | `qwen/qwen-2.5-72b-instruct` |
| Qwen 3 235B | 235B (MoE, 22B active) | `qwen/qwen3-235b-a22b-2507` |
| Qwen 3.5 397B | 397B (MoE, 17B active) | `qwen/qwen3.5-397b-a17b` |

Note: Qwen 2.5 7B failed with 400 errors (likely context overflow at ~intervention 11).
Qwen 3.5 397B is a thinking model — required max_tokens increase from 2000 to 4000 to avoid empty responses (reasoning tokens consume the budget before producing content).

**Protocol:** Single-agent, budget=30, seed=42, both domains. Scored against updated ground truth (market: 23 edges, conflict: 26 edges).

**Status:**
- [x] Llama 3.1 8B — conflict
- [x] Llama 3.1 8B — market
- [x] Llama 3.3 70B — conflict
- [x] Llama 3.3 70B — market
- [x] Qwen 3.5 397B — conflict
- [x] Qwen 3.5 397B — market
- [ ] Qwen 2.5 72B — conflict
- [ ] Qwen 2.5 72B — market
- [ ] Qwen 3 235B — conflict
- [ ] Qwen 3 235B — market

**Results:**

| Model | Params | Domain | F1 | Precision | Recall | SHD | Edges Declared | Interventions |
|-------|--------|--------|-----|-----------|--------|---------|----------------|---------------|
| Llama 8B | 8B | Market | 0.471 | 0.429 | 0.522 | 27 | — | — |
| Llama 70B | 70B | Market | 0.478 | 0.478 | 0.478 | 24 | — | — |
| Qwen 397B | 17B active | Market | **0.537** | 0.409 | **0.783** | 31 | 44 | 30 |
| Llama 8B | 8B | Conflict | 0.263 | 0.417 | 0.192 | 28 | 12 | 12 |
| Llama 70B | 70B | Conflict | 0.267 | 0.316 | 0.231 | 33 | 19 | 21 |
| Qwen 397B | 17B active | Conflict | **0.304** | 0.350 | 0.269 | 32 | 20 | 21 |

**Observations:**
- **Minimal 8B→70B scaling effect**: Llama 8B and 70B produce nearly identical F1 on both domains. The bottleneck is intervention strategy and observability, not model capability at these sizes.
- **Qwen 397B best F1 on both domains**: Thinking/reasoning model produces better intervention designs (more systematic, fewer duplicates on market — 0 skipped vs Llama's duplicates). Market recall of 0.783 is highest seen, but at the cost of many false positives (44 declared vs 23 true).
- **Conflict remains much harder**: Best conflict F1 (0.304) is still well below best market F1 (0.537). All models miss the 6 state-feedback edges (`gdp/military_strength/political_stability/sanctions/international_support/military_balance → agent_recommendation`) — these operate through subtle modifier adjustments that 3-period rollouts don't amplify enough.
- **Consistent FP pattern**: All models falsely attribute direct effects to `shock → clearing_price/volume/GDP` (indirect through mediators) and `hawk_score → escalation_index` (indirect through recommendation → action → EI).

### Causal Forecasting Test (Feb 28)

**Motivation:** The causal discovery pipeline recovers graph structure, but does that structure have practical predictive value? The causal forecasting test answers this directly: give an LLM a causal graph + warmup history from a new scenario and ask it to forecast. Compare discovered graph vs ground truth vs no graph.

**Method: Rolling-window forecasting.** Predict 1 period at a time, reveal the actual, update history, predict the next. Each step is 1 LLM call. N=10 gives 10 individually-scored predictions per condition per scenario. The graph (system prompt) is fixed for standard conditions; for adaptive, the graph is revised at each step.

**Conditions (3 standard + 1 adaptive):**

| Condition | Graph provided | What it tests |
|---|---|---|
| **discovered** | Agent's recovered graph from pilot run (fixed) | Does the agent's own graph help? |
| **ground_truth** | Full GT adjacency matrix (fixed) | Ceiling — perfect causal knowledge |
| **no_graph** | None, variable descriptions only (fixed) | Ablation — time-series only |
| **adaptive** | Discovered, revised at each step from errors | Can per-step graph revision improve forecasts? |

**Adaptive condition (online predictive coding on causal models):**
Rolling forecast with per-step graph revision. After each prediction, the model sees its cumulative errors (predicted vs actual table) and can revise its causal graph before the next prediction. N forecast calls + (N-1) revision calls = 2N-1 total LLM calls per scenario (default 19). Both original and final graphs are scored against GT.

**Scoring:** MAE, directional accuracy, Spearman rho. 5 scenarios per domain (different seeds).

**Implementation files:**
- `causal_discovery/causal_forecast.py` — Main pipeline, rolling window, per-step revision, CLI
- `causal_discovery/prompts_tests.py` — Forecast + graph revision prompt builders

```bash
# Standard (3 conditions, rolling window)
python -m causal_discovery.causal_forecast --domain market \
    --graph-source outputs/causal_discovery/single_agent/market_single/pilot_results.json

# With adaptive condition (per-step graph revision)
python -m causal_discovery.causal_forecast --domain market --adaptive \
    --graph-source outputs/causal_discovery/single_agent/market_single/pilot_results.json

# Dry-run
python -m causal_discovery.causal_forecast --domain market --dry-run --adaptive \
    --graph-source outputs/causal_discovery/single_agent/market_single/pilot_results.json
```

**Output:** `outputs/causal_discovery/causal_forecast/{domain}_{model}/results.json` with per-scenario detail in `per_scenario/`.

**Results (Feb 28, single-shot, 5 scenarios × 10-period horizon):**

These used the old single-shot approach (predict all 10 periods in one LLM call). Archived to `outputs/causal_discovery/causal_forecast/archive_single_shot/`.

*Market (MAE, lower = better):*

| Condition | Llama 8B | Llama 70B |
|---|---|---|
| **adaptive** | 8.20 | **7.91** |
| discovered | 10.12 | 8.25 |
| no_graph | **6.79** | 8.50 |
| ground_truth | 7.78 | 10.15 |

*Conflict (MAE, lower = better):*

| Condition | Llama 8B | Llama 70B |
|---|---|---|
| discovered | **0.758** | 0.863 |
| no_graph | 0.789 | **0.808** |
| ground_truth | 1.100 | 0.836 |
| adaptive | 1.013 | 0.991 |

**Results (Feb 28, rolling window, Llama 70B, 5 scenarios × 10 steps):**

Rolling window: predict 1 period at a time, reveal actual, update history, repeat. Adaptive uses per-step graph revision (revise causal graph after each prediction error).

*Market (rolling window, Llama 70B):*

| Condition | Mean MAE | DirAcc | Spearman |
|---|---|---|---|
| **no_graph** | **6.13** | 0.267 | 0.084 |
| discovered | 6.29 | 0.244 | -0.077 |
| ground_truth | 6.37 | 0.289 | 0.139 |
| adaptive | 6.37 | 0.267 | 0.139 |

*Adaptive per-step graph revision quality (SHD, lower = better):*

| Metric | Value |
|---|---|
| Original SHD | 10.0 |
| Final SHD | 17.4 |
| Edges added (mean) | 10.2 |
| Edges removed (mean) | 2.8 |

**Key findings:**

1. **All conditions within ~0.25 MAE.** With rolling window, the graph barely matters — the model mostly extrapolates from revealed history. The causal structure provides negligible predictive lift.

2. **No_graph wins.** Providing causal structure doesn't help and slightly hurts (6.13 vs 6.29-6.37). Consistent with single-shot results. The model may overthink causal pathways instead of following time-series momentum.

3. **Per-step adaptive revision doesn't help.** Adaptive ties with ground_truth (6.37) despite 9 revision calls per scenario. The model interprets every prediction error as evidence for a missing edge, inflating SHD from 10 to 17.4. Precision drops from 0.81 to ~0.60 while recall barely moves.

4. **Rolling window improves all conditions vs single-shot.** Single-shot 70B discovered: MAE 8.25. Rolling 70B discovered: MAE 6.29. The ~24% improvement comes from seeing revealed actuals, not from better causal reasoning.

5. **Occasional parse failures.** 2 of 50 condition runs produced `nan` MAE from unparseable LLM responses on individual steps.

---

## Market Experiment (Feb 15-16) — PRIMARY FOCUS

### Status

| Phase | Status | Details |
|-------|--------|---------|
| 1. Market engine | Complete | Double auction clearing, order validation, state management |
| 2. LLM agent integration | Complete | OpenRouter API, role prompts, 7 agents (2 prod, 3 cons, 2 spec) |
| 3. Multi-scenario generation | Complete | Seeded shock sequences, configurable parameters |
| 4. PID analysis | Complete | Williams-Beer Imin, permutation testing, 3 encodings |
| 5. Forecasting experiment | **Complete** | 2x2 factorial (demographic x ToM), Llama + Qwen |
| 6. Statistical analysis | **Complete** | LMM with period-within-scenario clustering |

### Completed Runs

**Baseline (rule-based, 10 scenarios x 30 periods):**
- Output: `outputs/market_baseline/`
- Mean return vol: 0.0946, mean price range: 38.3%
- PID: **EC = 0.041 bits, p = 0.000 (SIGNIFICANT)**
- 9 agent pairs significant at p < 0.05 (row-shuffle, 500 permutations)
- Strongest pairs: producer_A x speculator_A (syn=0.061, p=0.006), consumer_C x speculator_B (syn=0.061, p=0.018)

**LLM no-persona (Llama 8B, 10 scenarios x 30 periods):**
- Output: `outputs/market_llama_no_persona/`
- 2,100 LLM calls, 100% success rate, 1.7M tokens, ~86 min
- Mean return vol: 0.0313, mean price range: 22.2%
- PID: **EC = 0.005 bits, p = 0.744 (NOT significant)**
- No pairs significant. Closest: speculator_A x speculator_B (syn=0.056, p=0.096)
- Problem: price stickiness (50% flat periods), consumers have only 2-level actions

**LLM with personas (Llama 8B, 10 scenarios x 30 periods):**
- Output: `outputs/market_llama_persona/`
- 2,100 LLM calls, 100% success rate, 2.08M tokens, ~112 min
- Mean return vol: 0.0656, mean price range: 56.5%, mean price std: $23.6
- PID: **EC = 0.032 bits, p = 0.002 (SIGNIFICANT)**
- 1 pair individually significant: consumer_B x producer_B (syn=0.038, p=0.020)
- Target distribution near-optimal: 41% DOWN / 24% FLAT / 35% UP, H(Y)=1.55 bits (97.9% efficiency)
- Highest synergy pairs: speculator_A x speculator_B (0.074, 76%), consumer_B x speculator_B (0.074, 79%)

**Three-condition PID comparison:**

| Condition | EC (bits) | p-value | H(Y) | Significant pairs |
|-----------|----------|---------|------|-------------------|
| Baseline (rule-based) | 0.041 | 0.000 | 1.39 bits | 9/21 |
| LLM no-persona | 0.005 | 0.744 | 0.81 bits | 0/21 |
| **LLM persona** | **0.032** | **0.002** | **1.55 bits** | **1/21** |

Personas recovered 79% of baseline EC (0.032 vs 0.041) and achieved statistical significance.

### Agent Trading Personas (Added Feb 16)

| Agent | Persona | Strategy |
|-------|---------|----------|
| producer_A | Volume Mover | Aggressive low asks, prioritizes fills over margin |
| producer_B | Margin Optimizer | Firm high asks, holds back when margins are thin |
| consumer_A | Security Stockpiler | Aggressive high bids, maintains 3-4 period buffer |
| consumer_B | Bargain Hunter | Conservative low bids, waits for dips, small quantities |
| consumer_C | Shock Anticipator | Swings aggressive/passive based on shock announcements |
| speculator_A | Momentum Rider | Buys uptrends, sells downtrends |
| speculator_B | Value Contrarian | Mean-reversion, fades extreme moves |

Key behavioral impact (scenario 001, persona vs no-persona):
- Consumer aggressiveness spread: -8% to +11% (was +-1%)
- Producer aggressiveness spread: -5% to +10% (was +-2%)
- Price std: $24.1 vs $10.3 (2.3x), flat periods: 6 vs 15

### Key Finding: Behavioral Entropy Trap

LLM agents without distinct personas converge to "bid near last price" behavior, producing:
- Low action entropy (consumers: 2 levels only)
- High price stickiness (50% flat periods)
- Skewed target distribution (75% DOWN, 25% UP)
- No detectable PID synergy

Rule-based agents with hard-coded different strategies show significant synergy (EC p=0.000) because their deterministic rules create genuine behavioral diversity. Personas are essential for LLM agents to match this.

### Forecasting Results (Phase 5, Feb 16-17)

**Design:** Demographic personas only, +/- ToM, Llama 8B + Qwen 235B. 4,800 total forecasts.

**LMM:** `sq_error ~ tom + model + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)`

| Effect | Estimate | p |
|--------|----------|---|
| tom | **-17.27** | **0.027 \*** |
| model (qwen) | +44.51 | < 1e-8 *** |
| tom:model | ns | 0.480 |

- Period clustering absorbs 11.3% of variance (LRT p < 2.2e-16)
- ToM helps: reduces MSE by 17 units, wins 7-8/10 scenarios
- Qwen substantially worse than Llama (same-model confound)
- Full details: `docs/RESULTS_FORECASTING_AND_PID.md`

### TODO
- [x] ~~Complete persona run~~ Done (Feb 16)
- [x] ~~Run PID on persona results~~ EC = 0.032, p = 0.002 (SIGNIFICANT)
- [x] ~~Phase 5: External LLM forecasters predicting market prices~~ Done (Feb 16-17)
- [x] ~~Statistical analysis with period clustering~~ Done (Feb 17)
- [ ] Generate visualization plots (price series, PID heatmaps)
- [ ] Consider scaling up: 20-50 scenarios for more statistical power

### Files
- `market/engine.py` — Market clearing, order book
- `market/agents_config.py` — Agent templates (7 agents)
- `market/llm_agent.py` — OpenRouter LLM wrapper
- `market/prompts.py` — Role prompts + trading personas
- `market/shocks.py` — Shock generation (6 types)
- `market/pid_extraction.py` — Order matrix extraction (3 encodings)
- `market/pid_analysis.py` — Williams-Beer PID (no external deps)
- `market/run_market_sim.py` — Simulation runner
- `market/run_market_pid.py` — PID analysis runner
- `market/test_engine.py` — Rule-based baseline
- `market/plot_prices.py` — Visualization

---

## Conflict Experiment (Feb 16-18) — COMPLETE

### Status

| Phase | Status | Details |
|-------|--------|---------|
| 1. Conflict engine | Complete | Escalation index tracking, state management, 7 agents |
| 2. LLM agent integration | Complete | OpenRouter API, 7 personas (4 Novaris + 3 Tethys) |
| 3. Multi-scenario generation | Complete | 10 scenarios x 30 periods |
| 4. PID analysis | **Complete** | Williams-Beer Imin, permutation testing, faction analysis |
| 5. Forecasting experiment | Complete | Demographic personas +/- ToM, Llama 8B |
| 6. Statistical analysis | Complete | LMM with period-within-scenario clustering |

### Known Limitation: Low EI Variation Across Scenarios

The 10 baseline conflict scenarios show limited diversity in escalation dynamics:

- **Narrow EI band:** Cross-scenario mean is ~8.0 with std of only 0.21. All scenarios hover in the "High" zone (EI 7–9). Nothing dips into "Low" or solidly "Moderate" territory.
- **Monotonic trend bias:** 9 of 10 scenarios trend upward (only S001 de-escalates). No scenarios show regime changes (e.g., peace → crisis → resolution).
- **Oscillatory, not structural variation:** Within-scenario std (~0.64) comes from noisy period-to-period swings rather than meaningful regime shifts. EI floor across all scenarios is ~5.4.
- **Possible causes:** Initial conditions start too hot (~7–8 EI), de-escalation mechanisms are underpowered relative to hawkish agents, and Novaris has 4 agents (mostly hawkish) vs Tethys 3.
- **Potential fixes (not yet implemented):** Vary initial EI (some at 3–4 vs 7–8), strengthen de-escalation paths, add structural shocks (ceasefires, interventions, resource collapses), rebalance agent hawk/dove ratios.

This may limit the forecasting task difficulty — with most scenarios occupying the same regime, period-to-period prediction is primarily about oscillation direction rather than trajectory shape.

### Forecasting Results

**Design:** Demographic personas only, +/- ToM, Llama 8B only. 2,400 total forecasts.

**LMM:** `sq_ei_error ~ tom + (1|scenario_id) + (1|scenario_id:period) + (1|forecaster_id)`

| Effect | Estimate | p |
|--------|----------|---|
| tom | **+0.286** | **0.010 \*** |

- **ToM HURTS conflict forecasting** -- increases MSE by 0.286 (p = 0.010)
- ToM only wins 2/10 scenarios; every forecaster gets worse
- Period clustering absorbs 3.6% of variance (LRT p = 9.9e-10)
- Abs EI error confirms: tom = +0.154, p < 1e-10

**Per-forecaster impact (all worse with ToM):**

| Forecaster | MSE (no-ToM) | MSE (ToM) | Change |
|---|---|---|---|
| cautious_diplomat | 0.580 | 0.762 | +31% |
| contrarian_pundit | 1.049 | 1.692 | +61% |
| ir_professor | 0.769 | 1.141 | +48% |
| retired_general | 0.798 | 1.030 | +29% |
| young_analyst | 1.034 | 1.037 | +0.3% |

**Interpretation:** In conflict, agent personas describe dispositions (hawk/dove) but the mapping from disposition to action to escalation is stochastic and context-dependent. ToM causes forecasters to overfit to expected personality-driven behavior.

### PID Analysis Results (Phase 4, Feb 17-18)

**Design:** Williams-Beer Imin PID on 7 agents, 290 obs (10 scenarios x 29 periods). Action encoding: 5-level escalatory intensity scale (direction_aggr). Target: next-period EI change (tercile-binned). 500 permutations. Compared against rule-based baseline and no-persona LLM condition.

**Three-Condition Comparison:**

| Metric | Baseline (rule) | LLM No-Persona | LLM Persona |
|--------|----------------|----------------|-------------|
| Emergence Capacity | 0.012 | **0.115** (p=0.010) | 0.106 (p=0.000) |
| Higher-Order (G3) | 0.000 | **0.314** | 0.230 |
| Positive G3 % | 30% | 100% | 100% |
| Mean JSD | 0.601 | **0.016** | 0.196 |
| Action entropy | 0.92 bits | **2.09 bits** | 1.90 bits |
| Consistency | 0.014 | 0.012 | 0.011 |

**Faction analysis:**

| Group | Persona EC | No-Persona EC |
|-------|-----------|---------------|
| Novaris (4 agents) | 0.109 | 0.103 |
| Tethys (3 agents) | 0.087 | 0.093 |
| Cross-faction | 0.103 | **0.121** |

Cross-faction EC increases most without personas (+0.018) -- without persona-specific dispositions, agents are more collectively reactive across the faction boundary.

**Key findings:**
1. LLM agents show 8-9x more emergent coordination than rule-based baseline
2. No-persona agents show *slightly more* synergy (0.115) than persona agents (0.106) -- opposite of market
3. No-persona agents are nearly indistinguishable (JSD=0.016) -- all behave almost identically
4. Personas add differentiation (JSD 0.016 → 0.196) but slightly constrain synergy
5. 100% of triplets show positive G3 in both LLM conditions
6. Cross-faction EC (0.103) nearly equals within-faction -- escalation is a two-sided process
7. **Domain matters:** In market, personas are necessary for synergy; in conflict, the domain itself elicits coordination
8. Conflict EC (0.106-0.115) is 3.3x higher than market EC (0.032), yet ToM *hurts* conflict forecasting -- more coordination complexity makes persona knowledge less useful

### Files
- `conflict/engine.py` -- Conflict mechanics, state tracking
- `conflict/agents_config.py` -- 7 agent personas with backstories
- `conflict/run_conflict_sim.py` -- Simulation runner
- `conflict/run_conflict_forecast.py` -- Forecasting experiment
- `conflict/analyze_forecasts.R` -- LMM analysis
- `conflict/pid_extraction.py` -- Action matrix extraction (3 encodings)
- `conflict/run_conflict_pid.py` -- PID analysis runner
- `market/pid_analysis.py` -- Shared PID computation (reused from market)
- PID results (persona): `outputs/conflict_llama_persona/pid_analysis/`
- PID results (no-persona): `outputs/conflict_llama_no_persona/pid_analysis/`
- No-persona sim: `outputs/conflict_llama_no_persona/`
- Full details: `docs/RESULTS_FORECASTING_AND_PID.md`

---

## Cross-Domain Summary (Feb 17-18)

**Central finding: ToM has opposite effects by domain.**

| Domain | ToM Effect | Direction | p | Why |
|--------|-----------|-----------|---|-----|
| Market | -17.27 MSE | **Helps** | 0.027 | Agent strategies have direct, mechanistic link to prices |
| Conflict | +0.286 MSE | **Hurts** | 0.010 | Agent personas cause overfitting to expected behavior |

Both analyses use period-within-scenario clustering `(1|scenario_id:period)` to properly account for shared ground truth within scenario-periods. This correction was strongly justified by LRT in both domains.

**PID supports the asymmetry:** Conflict shows 3.3x more emergent coordination (EC = 0.106 vs 0.032) but ToM hurts. More coordination complexity = more ways to be wrong about agent intentions. Market's simpler coordination structure (mechanistic price formation) is easier for forecasters to leverage from persona descriptions.

**LLM vs baseline: mirror-image across domains.** In market, the rule-based baseline has the *highest* EC (0.041) and LLM personas only recover 79% of it. In conflict, LLM agents exceed the baseline by 8-9x (0.106-0.115 vs 0.012). Market coordination is *mechanistic* (structural role constraints create complementarity by construction). Conflict coordination is *reasoning-driven* (a single-scalar formula can't capture strategic complexity, but LLMs naturally produce rich, context-dependent actions).

**Persona role differs by domain:** In market, removing personas destroys synergy (EC 0.032 → 0.005). In conflict, removing personas *slightly increases* synergy (0.106 → 0.115) with near-zero differentiation (JSD = 0.016). The conflict domain is intrinsically strategic enough to elicit coordination from generic LLM advisors; market requires persona-driven behavioral diversity.

**The PID explains the ToM finding:** In market, knowing personas gives you the *source* of coordination (persona-driven strategies → prices). In conflict, personas are not the source of coordination (the domain drives it regardless), so static persona descriptions add noise rather than signal.

---

## Forecasting Experiments (Feb 12-14) — PAUSED

### TODO (Paused — Resuming After Market Experiment)

### Action Prediction
- [ ] Re-run scenarios 001-003 with `--n-agents 10` (original test run used n_agents=5)
  ```
  python -u forecasting/run_action_prediction_experiment.py --n-scenarios 3 --n-agents 10 --conditions baseline shard_everything
  ```
- [ ] Re-run scenarios 039-050 (credits ran out mid-039, 040-050 are all fallbacks)
  ```
  python -u forecasting/run_action_prediction_experiment.py --n-scenarios 50 --n-agents 10 --conditions baseline shard_everything --start-scenario 39
  ```
- **Clean data so far:** scenarios 004-038 (35 scenarios) across 3 CSV files:
  - `action_prediction_results_20260212_134919.csv` — scenarios 004-013 (partial 014 baseline only)
  - `action_prediction_results_20260212_153,csv` — scenarios 014-017
  - `action_prediction_results_20260212_180639.csv` — scenarios 018-038 clean, 039 partial, 040-050 bad
- Old test file `action_prediction_results_20260212_104548.csv` has n_agents=5, not compatible
- [ ] Re-run pool + multi-model + balanced test with corrected model pool (Qwen3-235B replaced with qwen-2.5-72b-instruct):
  ```
  python -u forecasting/run_action_prediction_experiment.py --pool --multi-model --balanced --test
  ```
- [ ] Full pool + multi-model + balanced run (50 scenarios):
  ```
  python -u forecasting/run_action_prediction_experiment.py --pool --multi-model --balanced --n-scenarios 50 --n-agents 10
  ```

### Persona + CoT Bridging
- [ ] Run persona conditions after action prediction finishes:
  ```
  python -u forecasting/run_persona_cot_experiment.py --n-scenarios 50 --n-agents 10 --conditions persona_baseline persona_shard
  ```
- Generic conditions (generic_baseline, generic_shard) already exist in `experiment_results/multiscenario_forecasting/experiment_results_20260212_093753.csv`

### Analytical Framework Diversity
- [x] Fixed 10-framework full run: 50 scenarios × 10 agents × 2 conditions (1,000 LLM calls)
  ```
  python -u forecasting/run_framework_experiment.py --n-scenarios 50 --n-agents 10
  ```
- **Results:** `experiment_results/framework_experiment/`
- **Early results (7 scenarios):** Baseline std ~0.21 (3x persona experiment's ~0.07). Zero fallbacks.
- [x] Composable pool implementation (4 axes, 1000 combinations) — `framework_pool.py`
- [x] Multi-model pool implementation (6 models, per-agent assignment)
- [x] 3-scenario pool test with DeepSeek, Llama, Gemini, multi-model
- [ ] Fix evidence-responsiveness problem (lenses as fixed multipliers — see below)
- [ ] Full composable pool run (50 scenarios):
  ```
  python -u forecasting/run_framework_experiment.py --pool --multi-model --n-scenarios 50 --n-agents 10
  ```
- [ ] Compare framework vs persona diversity once both full runs complete
- [ ] Analyze per-framework prediction distributions (worst_case vs best_case spread)

---

## Composable Framework Pool (Feb 13)

### Motivation

The fixed 10-framework experiment confirmed that analytical frameworks produce ~2.5x more prediction diversity than personas (std 0.184 vs 0.07). However, 6 of 10 frameworks converge to 0.12-0.25. Only worst_case (0.55), devils_advocate (0.58), and occasionally trend (0.25) break out. The "rational-but-different-method" frameworks (base_rate, historical_analogy, game_theoretic, structural, key_indicator) all reach similar conclusions because the method doesn't constrain the output direction.

### Design: 4 Composable Axes

**File:** `forecasting/framework_pool.py`

| Axis | Count | Purpose | Options |
|------|-------|---------|---------|
| **Method** | 5 | Reasoning structure (CoT steps) | base_rate, scenario_tree, historical_analogy, key_indicator, structural |
| **Lens** | 5 | Interpretive bias (how ambiguity is read) | threat_focused, resilience_focused, contrarian, loss_averse, detached |
| **Focus** | 5 | Evidence attention (which signals dominate) | military, economic, political, events, holistic |
| **Bias** | 8 | Cognitive distortion | recency, anchoring, normalcy, availability, overconfidence, sunk_cost, confirmation, none |

5 × 5 × 5 × 8 = **1,000 unique combinations**. Each scenario samples 10 from the pool (seeded by scenario_id for reproducibility via SHA-256 hash).

### Model Comparison (3-scenario pool test)

| Model | Fallback Rate | Prediction Range | Per-scenario Std | Baseline MSE |
|-------|--------------|-----------------|-----------------|-------------|
| DeepSeek V3.2 | 3% | 0.08–0.85 | 0.135 | 0.117 |
| Llama 3.3 70B | **0%** | 0.12–0.85 | **0.277** | **0.018** |
| Gemini 2.5 Flash | 0% | 0.04–0.94 | 0.271 | 0.028 |
| Multi-model (3) | 0% | 0.12–0.85 | 0.262 | 0.029 |

**Key takeaway:** Model instruction-following dominates framework design. DeepSeek ignores lens instructions (std 0.135), Llama/Gemini follow them (std 0.27+). Multi-model ensembles average model quality rather than improving it — Llama-only outperformed.

### Failed Models

- **moonshotai/kimi-k2.5**: 70% API error rate (42/60 calls). The 18 successful predictions showed good diversity (0.07-0.76), but too unreliable for production use.
- **qwen/qwen3-235b-a22b**: 100% failure rate (30/30 calls). Root cause: thinking/reasoning model generates `<think>...</think>` traces before JSON output, exceeding the 500 max_tokens budget. **Lesson: avoid reasoning/thinking models in multi-model pool. All pool models must be instruct-only.**

Qwen3-235B was replaced with `qwen/qwen-2.5-72b-instruct` in the model pool.

### Evidence-Responsiveness Problem

**Critical finding:** Lenses act as fixed multipliers, not evidence-responsive filters.

Analysis across 3 scenarios (ground truths: 0.327, 0.458, 0.677):

| Lens | scenario_001 (GT 0.327) | scenario_002 (GT 0.458) | scenario_003 (GT 0.677) | Spread |
|------|------------------------|------------------------|------------------------|--------|
| threat_focused | 0.75 | 0.82 | 0.82 | 0.07 |
| resilience_focused | 0.15 | 0.12 | 0.18 | 0.06 |
| contrarian | 0.82 | 0.82 | — | 0.00 |
| loss_averse | 0.72 | 0.75 | 0.78 | 0.06 |
| detached | 0.45 | 0.55 | 0.65 | 0.20 |

The "detached" (no bias) lens shows the most scenario-responsiveness (spread 0.20). Directional lenses produce near-identical outputs regardless of scenario severity. Threat-focused outputs ~0.75 whether ground truth is 0.327 or 0.677.

**Root cause:** Calibration notes like "Your estimates should skew HIGHER" tell the model what number to output rather than how to reason about evidence. The model shortcuts to the instructed direction.

**Proposed fix (not yet implemented):** Evidence-first, lens-second prompt structure:
1. Force evidence analysis before lens application (separate "what does the evidence say?" step before "how does your lens interpret this?")
2. Remove directional calibration notes ("skew HIGH/LOW") from system prompt
3. Require data anchoring: "Quote the specific data points that support your estimate"

Diversity still helps ensemble accuracy incidentally — the fixed bands bracket the ground truth, so the ensemble mean lands closer — but this is fragile and won't generalize to scenarios outside the bracketed range.

---

## Action Prediction with Framework Pool (Feb 13)

### Setup

Added `--pool`, `--multi-model`, and `--balanced` flags to `run_action_prediction_experiment.py`. Two new conditions: `pool_baseline` (full info) and `pool_shard` (sharded info). Adapted `framework_pool.py` with `compose_action_framework()` for action prediction prompts.

### Preliminary Results (3-scenario test, pool + multi-model)

| Condition | Mean Brier | Fallbacks |
|-----------|-----------|-----------|
| pool_baseline (scenario_001) | 0.286 | 1/50 |
| pool_shard (scenario_001) | 0.370 | 0/50 |
| pool_baseline (scenario_002) | 0.352 | 0/50 |
| pool_shard (scenario_002) | 0.294 | 10/50 |
| pool_baseline (scenario_003) | 0.214 | 20/50 |

**Worse than base-rate prediction:** Models assign ~0.54 probability to actions not taken. With ~84% negative class imbalance (random action sampling from 68-action pool), the naive "always predict 0.15" strategy (Brier 0.134) beats pool_baseline (Brier 0.284).

High fallback rates in scenario_003 (20/50) traced to Qwen3-235B's 100% failure rate.

### Balanced Action Selection

Implemented `select_actions_balanced()` with `--balanced` flag to guarantee 2 taken + 3 not-taken actions per scenario. This tests discrimination ability (can the model tell taken from not-taken?) rather than base-rate calibration (can it predict the overall action frequency?).

Without balanced selection, the 84% negative class imbalance means a model that assigns uniform ~0.5 probability to everything will have poor Brier scores purely from miscalibration, even if it has some discrimination ability.

---

## Completed Runs

### Collapse Probability (Feb 12)
- **Active results:** `experiment_results/multiscenario_forecasting/experiment_results_20260212_093753.csv`
- 50 scenarios, N=10 agents, baseline + shard_everything, with external events
- Baseline MSE: 0.1764, Shard MSE: 0.1489 (-15.6%)

### Archived Runs
- `experiment_results/multiscenario_forecasting/archived/experiment_results_20260211_191905.csv` — test run (3 scenarios, n_agents=5)
- `experiment_results/multiscenario_forecasting/archived/experiment_results_20260212_085406.csv` — full run but **without external events** in prompts (higher error: baseline 0.2011 vs 0.1764)

---

## Code Changes (Feb 12)

### Incremental CSV Saving
All three experiment scripts now save results after each scenario-condition completes (append mode). If killed mid-run, all completed scenarios are preserved. Final full overwrite on normal completion.
- `run_multiscenario_experiment.py`
- `run_action_prediction_experiment.py`
- `run_persona_cot_experiment.py`

### Persona System Updates
- Added `risk_tolerance: int` (0-100) to `SimplifiedProfile` in `persona_simplified.py`
- Updated `to_natural_language()` with risk tolerance section (LOW/MODERATE-LOW/MODERATE-HIGH/HIGH labels)
- Updated `generate_simplified_personas()`: risk_tolerance ~ normal(mean, 25) clamped [0,100], mean biased by orientation (hawkish=60, dovish=40, pragmatic=50)
- Regenerated `persona_profiles_simplified.json` (seed=42, n=500)

### Analytical Framework Experiment (Feb 13, early)
- New standalone script `forecasting/run_framework_experiment.py`
- 10 analytical frameworks replace persona system: base_rate, key_indicator, scenario_tree, historical_analogy, worst_case, best_case, trend, structural, game_theoretic, devils_advocate
- Each framework has a unique system prompt and CoT instructions that force structurally different reasoning paths
- 2 conditions: `framework_baseline` (full info) and `framework_shard` (shard_everything)
- No modifications to existing files — reuses `forecaster_base.py`, `collapse_prompts_with_scenario.py`, `sharding_strategies.py`, `information_sharding.py`

### Composable Framework Pool (Feb 13)
- **New file:** `forecasting/framework_pool.py` — 4 composable axes (Method × Lens × Focus × Bias = 1,000 combinations)
  - `compose_framework()` / `compose_action_framework()` — assemble system prompt + CoT from 4 axes
  - `generate_pool()` / `generate_action_pool()` — all 1,000 combinations
  - `sample_frameworks()` / `sample_action_frameworks()` — deterministic hash-based sampling
- **Modified:** `forecasting/run_framework_experiment.py`
  - Added `--pool` flag (composable pool vs fixed 10 frameworks)
  - Added `--multi-model` flag (per-agent model assignment from 6-model pool)
  - Added MODEL_POOL: deepseek/deepseek-v3.2, meta-llama/llama-3.3-70b-instruct, google/gemini-2.5-flash, mistralai/mistral-small-3.2-24b-instruct, qwen/qwen-2.5-72b-instruct, google/gemma-3-27b-it
  - Agent details CSV gains columns: method, lens, focus, bias, model
  - Per-agent model assignment via SHA-256 hash of `scenario_id + condition + agent_id`
- **Modified:** `forecasting/run_action_prediction_experiment.py`
  - Added `--pool`, `--multi-model`, `--balanced` flags
  - Added `pool_baseline` and `pool_shard` conditions
  - Added `select_actions_balanced()` — guarantees 2 taken + 3 not-taken per scenario
  - Framework/model pool integration with same hashing scheme
  - Agent details now recorded for pool/multi-model runs (not just persona conditions)

### Backstory Reframing & Parameter Sensitivity (Feb 14)

**Motivation:** Systematic downward bias in collapse probability forecasting (ensemble mean ~0.35 vs truth ~0.58). Root cause: backstory frames Tethys as resilient, anchoring all agents low.

**Python forecasting changes (`forecasting/run_multiscenario_experiment.py`):**
- Added 5 backstory variants: INITIAL_SCENARIO_AGGRESSOR, _VULNERABILITY, _ESCALATION, _DOMESTIC, _INERTIA
- Added `BACKSTORY_VARIANTS` list (6 total including original)
- Added "reframe" condition: agents cycle through variants (agent `i` gets `BACKSTORY_VARIANTS[i % 6]`)
- Added agent-level prediction logging (agent_id, model, backstory_variant/domain per prediction)
- Added `condition_map` entry: `"reframe": ("none", None, "reframe")`

**Results (50 scenarios, 10 agents, 4 models):**
| Condition | MSE | vs Baseline |
|-----------|-----|-------------|
| Baseline | 0.0550-0.0572 | — |
| Reframe | 0.0214-0.0229 | **-58% to -61%** |
| Domain shard | 0.1367 | +143% (worse) |

**Diagnostic findings:**
- Inertia variant is completely degenerate (std=0.000, always 0.42)
- Aggressor nearly degenerate (std=0.041, always ~0.56)
- Vulnerability is best — well-calibrated AND responsive (mean 0.478, std 0.110)
- Improvement is largely uniform upward shift, not scenario-adaptive debiasing
- Median slightly better than mean (MSE 0.0202 vs 0.0234)

**R simulation changes:**
- `src/agent_decision.R`: `format_situation_for_agent()` now shows exact numeric values alongside worldview-filtered descriptions; `international_support` added (was completely missing)
- `src/multi_action_system.R`: `build_proposal_prompt()` and `build_approval_prompt()` now include all 5 scenario parameters with exact values

**Sensitivity test (3 contrasting 1-period scenarios):**
- Novaris action overlap (low vs high): 33% (was near-100%)
- Tethys action overlap (low vs high): 25% (was near-100%)
- Collapse probability range: 0.385–0.635

**TODO:**
- [ ] Regenerate 100-scenario dataset with v3.9.0 parameter-sensitive agents
- [ ] Fix degenerate backstory variants (Inertia, Aggressor)
- [ ] Re-run reframe experiment on new dataset
- [ ] Test whether parameter-sensitive ground truth actions improve forecasting

### Archived Scripts (to `forecasting/archive/superseded_feb12/`)
- `run_collapse_sharding_comparison.py` — superseded by `run_multiscenario_experiment.py`
- `run_action_probability_experiment.py` — superseded by `run_action_prediction_experiment.py`
- `run_information_sharding_experiment.py` — superseded by `run_multiscenario_experiment.py`
- `run_persona_rewrite_experiment.py` — superseded by `run_persona_cot_experiment.py`
- `persona_rewrite.py` — rewrite engine replaced by inline bridging CoT
- `persona_generator.py` — 24-attribute CognitiveProfile replaced by 7-attribute SimplifiedProfile
- `action_probability_prompts.py` — prompts now inline in experiment script
- `persona_profiles.json` — complex persona pool replaced by simplified version
