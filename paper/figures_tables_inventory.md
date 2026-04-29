# Figures & Tables Inventory

Organized into four categories: **Main Methods**, **Main Results**, **Supplement Methods**, **Supplement Results**. Each entry includes a one-line summary of what it *shows*.

## Folder structure

```
paper/
├── figures/
│   ├── main/          # active main-paper figures
│   ├── supplement/    # active supplement figures
│   ├── internal/      # figures for internal reference only (not in paper)
│   └── archive/       # superseded / deprecated figures
└── tables/
    ├── main/          # active main-paper tables (.tex)
    ├── supplement/    # active supplement tables (.tex)
    └── archive/       # superseded / deprecated tables
```

All paths below are relative to `paper/`.

---

## Main Paper — Methods

### Figures

| # | Name | Path | Shows |
|---|------|------|-------|
| 1 | Methods overview | `figures/main/LLM_Forecasting_Methods.png` | The four-stage pipeline (causal forecast → network analysis → probe generation → probed forecast) and how probe targets are selected from the DAG. |

### Tables

| # | Label | Source | Shows |
|---|-------|--------|-------|
| 1 | `tab:probe_types` | `methods_and_results.tex` (inline) | The 21-probe allocation per question: 14 probe types across four categories (strengthen, negate, structural challenge, control), spanning high/medium/low-importance nodes and shortest-path/peripheral edges. |
| 2 | `tab:probe_instructions` | `methods_and_results.tex` (inline) | The exact text instruction passed to the probe-generation LLM for each of the 14 probe types; demonstrates that importance tier is not revealed to the generator. |
| 3 | `tab:probe_examples` | `methods_and_results.tex` (inline) | All 14 probe types applied to one high-complexity exemplar (Khamenei, GPT-OSS 120B); ranges from $-0.05$ to $+0.30$ in shift and illustrates how structure and direction combine. |

---

## Main Paper — Results

### Figures

| # | Name | Path | Shows |
|---|------|------|-------|
| 2 | Exemplar networks | `figures/main/exemplar_networks_combined.{pdf,png}` | Side-by-side DAGs for the same question across models — models converge on similar causal factors but differ in how they wire them up. |
| 3 | Initial probabilities | `figures/main/initial_probabilities.{pdf,png}` | Three panels: **(a)** $p_0$ density distributions by model, **(b)** cross-model Spearman $\rho$ heatmap showing moderate pairwise agreement on $p_0$ (ρ = 0.55--0.77), **(c)** calibration curves against prediction-market consensus at freeze time (Metaculus, Polymarket, Manifold, INFER; 111 of 116 questions — 5 data-source items from ACLED/Wikipedia excluded). Models tend to be under-confident at high predicted probabilities. |
| 4 | Probe effects | `figures/main/probe_effects.{pdf,png}` | Headline result: \|Δlogit\| by probe category × model, with high-importance > medium > low and asymmetry between negate and strengthen probes. |
| 5 | Coherence | `figures/main/coherence.{pdf,png}` | Four-panel coherence summary: (a) \|Δ\| scales monotonically with stated-impact rating; (b) confident reasoning produces larger shifts than hedging; (c) Bayesian coherence (shift slightly anti-correlated with initial probability); (d) targeted-probe reasoning more self-similar than control-probe reasoning. |

*Question categories* (topic breakdown of the 116 questions) — reported in text only; per-domain counts appear in methods §Questions (conflict \& security 40, technology 27, politics \& governance 18, health \& science 13, finance \& markets 6, economics 5, society \& culture 4, climate \& energy 3). Source PNG lives in `figures/internal/` for reference.

*Validation* (previously `figures/validation.{pdf,png}`) — converted to a main-paper table; see `tab:validation_summary` below. Source PNG moved to `figures/internal/`.

*Coherence forest plot* (previously `figures/coherence_forest.{pdf,png}`) — archived. Pooled-LME story carried by the 4-panel `coherence` figure.

### Tables

| # | Label | Source | Shows |
|---|-------|--------|-------|
| 4 | `tab:lme_topology` | `tables/main/lme_topology_combined_table.tex` | Core result: node betweenness and outcome mediation both significantly predict \|Δlogit\| at the pooled level ($\beta = 0.0093, 0.0105$, $p<.001$); 6 of 7 models show the effect individually. Combines prior Model A / Model B shared-slope and per-model tables. |
| 5 | `tab:lme_direct_main` | `tables/main/lme_direct_main_table.tex` | Direct causes (one hop from the outcome) produce larger probability shifts than indirect causes, after controlling for other topological predictors. |
| 6 | `tab:factor_ranking` | `tables/main/lme_factor_ranking_summary_table.tex` | Factor ranking has **convergent validity** (stated rank predicts betweenness, $\beta = -0.336$) *and* **incremental validity** (topology adds information beyond stated rank). |
| 7 | `tab:elo_regression` | `tables/main/elo_regression_table.tex` | Elo-ranked question difficulty predicts belief-sensitivity metrics (mean absolute shift, reasoning judge rating, uncertainty judge rating) beyond what $\|p_0 - 0.5\|$ explains — harder questions produce smaller shifts, more reasoning effort, and less hedging. |
| 8 | `tab:validation_summary` | `tables/main/validation_summary_table.tex` | Four GPT-OSS validation checks: **(A)** importance→\|Δ\| correlation survives residualizing on persuasiveness; **(B)** forced-ignore ablation — shift still tracks betweenness ($\beta=0.0161$) and path relevance ($\beta=0.0167$) when the model is told to disregard the factor; **(C)** grounding coefficient degrades under random edge rewiring (intact $\beta=0.0111$ vs permuted $\beta=0.0090$, ~19% drop); **(D)** effect replicates at both 6–10 and 12–16 node DAGs. |

*Cross-model DAG agreement* (previously `tab:cross_model_agreement`) — reported in text only. The single headline (mean nGED $= 0.881$ vs null $0.998 \pm 0.0003$, $p < .001$, 21 model pairs) doesn't warrant a table.

---

## Supplement — Methods

### Figures

| # | Name | Path | Shows |
|---|------|------|-------|
| S1 | Network probing diagram | `figures/supplement/network_probing_diagram.png` | Illustrative walk-through of the four probe categories (negate node, add missing node, add spurious edge, reverse edge direction) on one example DAG. |
| S2 | Causal Forecast Lab | `figures/supplement/causal_forecast_lab.jpg` | Four-panel walk-through of the interactive web application: (a) landing page, (b) question detail view with per-model initial probabilities and interactive probe panel, (c) force-directed DAG visualization with live sensitivity metrics, (d) per-probe results table with shift magnitudes and expanded reasoning. |

### Tables

| # | Label | Source | Shows |
|---|-------|--------|-------|
| S1 | `tab:elo_exemplars` | `tables/supplement/elo_exemplars_table.tex` | Exemplar questions at the extremes of the Elo difficulty tournament — easy questions are data-anchored extrapolations, hard questions involve geopolitical contingencies and long-horizon technology bets. |

---

## Supplement — Results

### Figures

| # | Name | Path | Shows |
|---|------|------|-------|
| S3 | Temperature exemplar pair | `figures/supplement/temperature_exemplar_pair.{pdf,png}` | Same-question DAGs at $T=0.0$ vs $T=1.0$ — temperature-induced variation is largely cosmetic (paraphrased node labels) rather than structural. |
| S4 | Propagation decay | `figures/supplement/propagation_decay_combined.jpg` | Probe-effect magnitude and reach attenuate monotonically with graph distance from the probed node — structural locality is honored. |

#### Reported in text only (no figure)

- Test–retest reliability — per-model Spearman $\rho$ already listed in methods §Robustness.
- Temperature sensitivity — mean $p_0$ range and pairwise nGED cited inline; exemplar pair (S3) handles the visual.
- Cross-model nGED — headline number ($0.88$ vs null $1.00$, $p<.001$) in the Results intro prose.
- Network size — summarized in `tab:validation_summary` Panel D.
- Structural ablation — covered by `tab:validation_summary` Panel B.
- Null test / edge permutation placebo — covered by `tab:validation_summary` Panel C.
- Spurious context control — headline rate reported in text: 0/116 contamination, $\rho = 0.728$, MAE $= 0.085$.
- Superforecasting DAG comparison — qualitative differences in prose.

### Tables

| # | Label | Source | Shows |
|---|-------|--------|-------|
| S2 | `tab:dag_characteristics` | `tables/supplement/dag_characteristics_table.tex` | Descriptive DAG properties by model — mean node count, edge count, density, depth across the 7 models on 116 questions. |
| S3 | `tab:lme_direct_interaction` | `tables/supplement/lme_direct_interaction_table.tex` | Per-model interaction between direct-vs-indirect predictor and model — tests whether direct-cause sensitivity varies systematically across models. |
| S4 | `tab:lme_ranking_combined` | `tables/supplement/lme_ranking_combined_table.tex` | Full-detail version of `tab:factor_ranking` Panel B (rank + betweenness jointly predicting \|Δlogit\|). |
| S5 | `tab:lme_ranking_convergent` | `tables/supplement/lme_ranking_convergent_table.tex` | Full-detail version of `tab:factor_ranking` Panel A (rank predicts betweenness). |

---

## Internal Reference (not in paper)

Figures generated for analysis but not included in the paper; kept in `figures/internal/` for reference:

- `question_categories.{pdf,png}` — topic breakdown visualization (reported as text counts in methods instead).
- `validation.{pdf,png}` — 3-panel validation figure (now a table: `tab:validation_summary`).
- `test_retest.{pdf,png}` — per-model retest reliability (reported as $\rho$ range in text).
- `temperature_sensitivity.{pdf,png}` — cross-temperature nGED plot (exemplar pair kept; this summary goes to text).
- `network_size.{pdf,png}` — grounding coefficients at different DAG sizes (now a panel in `tab:validation_summary`).
- `null_test.{pdf,png}` — edge-permutation null test (now in `tab:validation_summary`).
- `structural_ablation.{pdf,png}` — ignore-this-factor ablation (now in `tab:validation_summary`).
- `spurious_context_control.{pdf,png}` — irrelevant-preamble contamination (reported as 0/116 in text).
- `propagation_decay.{pdf,png}` — older/alternate propagation figure; active supplement version is `propagation_decay_combined.jpg`.
- `cross_model_ged.{pdf,png}` — cross-model DAG similarity (now in `tab:cross_model_agreement`).
- `superforecasting_dag_comparison.{pdf,png}` — qualitative DAG comparison under superforecasting prompt (reported as text).
- `Presentation1/` — slide-deck material (not paper content).

---

## Archive (superseded / deprecated)

**Figures** (`figures/archive/`):
- `pipeline_diagram.{pdf,png}`, `probe_procedure_diagram.{pdf,png}` — superseded by combined `LLM_Forecasting_Methods.png`.
- `coherence_forest.{pdf,png}` — per-model coherence breakdown no longer shown.
- `superforecasting_analysis.{pdf,png}` — content didn't match the SF-prompt experiment the filename implied.

**Tables** (`tables/archive/`):
- `lme_model_a_shared_table.tex`, `lme_model_b_shared_table.tex`, `lme_model_a_table.tex`, `lme_model_b_table.tex` — superseded by `lme_topology_combined_table.tex`.
- `lme_ablation_node_betw_table.tex`, `lme_ablation_node_pr_table.tex`, `lme_ablation_combined_table.tex` — superseded by `tab:validation_summary` Panel B.
- `lme_permutation_table.tex`, `lme_structural_robustness_table.tex`, `lme_scrambled_table.tex` — placebo results consolidated into `tab:validation_summary` Panel C (`lme_permutation_table.tex` may still be referenced if full detail is needed; currently sits in `figures/archive/` from earlier moves).
- Duplicates of `elo_exemplars_table.tex` and `elo_regression_table.tex` that were in `figures/supplementary/`.

---

## Notes

- **Generation scripts updated to new paths**:
    - Active main: `gen_coherence.py`, `gen_exemplar_networks.py` → `paper/figures/main`.
    - Active supplement: `gen_propagation_decay.py` → `paper/figures/supplement`.
    - Internal: `gen_validation_figure.py`, `gen_hedge_figure.py`, `gen_lme_figure.py`, `gen_new_figures.py`, `gen_elo_vs_extremity.py`, `analyze_cross_model_ged.py`, `analyze_factor_ranking.py`, `analyze_reasoning_similarity.py`, `analyze_superforecasting_dag.py` → `paper/figures/internal`.
    - Archive: `gen_pipeline_diagram.py`, `gen_coherence_forest.py`, `gen_probe_diagram.py` → `paper/figures/archive`.
    - Tables: `lme_analysis.R`, `gen_elo_tables.py`, `gen_model_table.py` → `paper/tables/archive` as staging; curated active versions live in `tables/main/` or `tables/supplement/` and need to be manually copied after regeneration.
- **Monolithic `generate_figures.py` archived** to `forecast_bench/archive/`. Shared utilities (`MODEL_DIRS`, `COLORS`, `_load_all_runs`, `_IMPORTANCE_TIER`, `_EMBED_PROBE_NORMALIZE`) extracted into `forecast_bench/shared_utils.py`. Active consumers (`gen_coherence.py`, `lme_analysis.py`) updated to import from `shared_utils` instead. Individual `gen_*.py` scripts are now the canonical way to regenerate each figure.
- `figures/supplementary/` still exists as an empty directory because Windows held a file handle during move; it's safe to remove manually.
- `tab:factor_ranking` currently renders at `\resizebox{0.75\linewidth}`; if the paper returns to two-column, revisit sizing.
- `figures/supplement/network_probing_diagram.png` was renamed from `Network Probing Diagram.png` (space-free for LaTeX). Caption should frame the DAG as an illustrative example of how probing works — no reference to a specific model or run.
- `ground_truth_resolutions.json` is missing from current outputs dir; calibration in `initial_probabilities.png` panel (c) currently uses prediction-market freeze values. To get calibration against resolved outcomes, regenerate this file on the 116 high-complexity set.
