# LLM Forecasting: Probing Causal Structure in Belief Updates

**April 2026** | Northeastern University

This repository contains code, data, and paper drafts for two related research threads on LLM forecasting:

1. **Belief Sensitivity** (primary, active) — Tests whether LLM probability updates are *internally consistent* with their own elicited causal models. Submitted to ARR May 2026.
2. **Known Causal Models** — Tests whether LLMs can discover known causal structures through interventional queries on simulation engines (commodity market and geopolitical conflict).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Belief Sensitivity (Primary Active Work)

**Question:** When an LLM produces a probability estimate alongside a causal DAG explaining its reasoning, does it update beliefs *in proportion to the structural importance* of challenged factors?

**Paper:** `paper/methods_and_results.tex` (target: ARR May 2026)

### Pipeline

A four-stage pipeline applied to each forecasting question:

1. **Causal Forecast** — LLM produces an initial probability p₀ and a causal DAG (6–10 factor nodes + 1 outcome node + directed edges with mechanisms)
2. **Network Analysis** — Pure computation: betweenness centrality, outcome mediation, shortest-path membership. Selects ~21 probe targets per question
3. **Probe Generation** — LLM writes natural-language counterfactual probes targeting specific structural elements (14 probe types: node negate/strengthen at 3 importance tiers, edge negate/strengthen for shortest-path/peripheral, edge reverse, edge structural, missing node, irrelevant control)
4. **Probed Forecast** — Each probe is presented in a fresh single-turn conversation. The model produces an updated probability pᵢ.

The key DV is the **absolute log-odds shift** |Δlogit|, regressed on topological predictors via linear mixed-effects models.

### Models (7 total, 5 architecture families, all via OpenRouter)

| Model | Params | Family |
|---|---|---|
| Llama 3.1 8B Instruct | 8B | Meta |
| Llama 3.3 70B Instruct | 70B | Meta |
| Qwen3 32B | 32B | Alibaba |
| Qwen3 235B | 235B MoE | Alibaba |
| DeepSeek V3 | 685B MoE | DeepSeek |
| Gemini 2.5 Flash Lite | — | Google |
| GPT-OSS 120B | 117B MoE | OpenAI |

### Data

- **116 high-complexity questions** filtered from 500 ForecastBench questions using a GPT-5.4 complexity classifier
- All questions have late-2025 resolution dates (after all training cutoffs)
- 7 models × 116 questions × ~21 probes = ~17,000 successful probe responses
- Categories: Conflict & Security (37), Technology (24), Politics & Governance (18), Health & Science (15), Society & Culture (10), Climate & Energy (7), Finance & Economics (5)

### Key Results

- **Topological predictors significantly predict probe sensitivity** across all 7 models in shared-slope LME (betweenness β=0.044, p<.001 in log-odds; outcome mediation β=0.050, p<.001). Per-model slopes range from Gemini (strongest) to Llama 8B (only model with non-significant slope).
- **Cross-model DAG convergence**: Same-question DAGs are significantly more similar across models than chance (semantic nGED = 0.83 vs. null = 1.01, p<.001), confirming models converge on similar causal representations.
- **Robustness**: Effect survives test-retest, edge permutation placebo, structural ablation ("ignore this factor"), network size variation (6–10 vs. 12–16 nodes), temperature sensitivity (T=0.0–1.0), spurious context, and persuasiveness control (high/low importance probes equally persuasive, p=.17).

### Quick Start

```bash
# Install
pip install -r requirements.txt
export OPENROUTER_API_KEY="your-key-here"

# Run main pipeline (single model, single question for testing)
python forecast_bench/run_sensitivity.py --model gpt-oss --max-questions 1

# Full run on 116 high-complexity questions for one model
python forecast_bench/run_sensitivity.py --model gpt-oss \
    --questions-file forecast_bench/high_complexity_questions.json
```

### Analysis

```bash
# Build LME data, fit models in R, generate tables
python -m forecast_bench.lme_analysis
Rscript forecast_bench/lme_analysis.R

# Regenerate paper tables
python forecast_bench/gen_dag_table.py
python forecast_bench/gen_elo_tables.py
```

### Causal Forecast Lab (Interactive Explorer)

Live web app for browsing DAGs, probe texts, and shifts per question/model:
**`belief-sensitivity-explorer/`** (separate Next.js project, deployed to Vercel)

Source: [github.com/seanwkelley/causal-forecast-lab](https://github.com/seanwkelley/causal-forecast-lab)

---

## Known Causal Models (Second Project)

**Question:** Can LLM agents recover known causal structures by performing targeted interventional experiments on simulation engines?

**Code:** `known_causal_models/` (see `known_causal_models/README.md` for details)

### Domains

- **Market** — 7 LLM trading agents in a double-auction commodity market (12 variables, 23 ground-truth edges)
- **Conflict** — 7 LLM geopolitical agents across two factions (13 variables, 26 ground-truth edges)
- **Causal discovery** — Pipeline for LLM agents to perform interventional queries (clamp-and-react rollouts) and accumulate a causal graph
- **Forecast multi** — Multi-agent forecasting framework with 13 conditions per domain (4 communication structures × 4 information levels)

### Status

- **Causal discovery pipeline (full-graph-per-turn)**: Best result Gemini 3.1 Pro F1=0.667, Qwen 397B F1=0.513, GPT-OSS F1=0.512
- **Key finding**: Models plateau at ~10–15 interventions, can't distinguish direct vs. indirect effects, don't prune, and stop exploring once comfortable
- **Explorer**: `known_causal_models/causal_discovery/explorer.html` — interactive visualization of intervention results

See `known_causal_models/docs/` for design notes, prior simulation/PID writeups, and the historical research log.

---

## Project Structure

```
LLM_Forecasting/
├── README.md                         # This file
├── forecast_bench/                   # Belief sensitivity pipeline (main paper)
│   ├── run_sensitivity.py              # Main pipeline runner
│   ├── prompts_causal.py               # Stage 1/2/3 prompt templates (neutral)
│   ├── network_analysis.py             # Graph centrality + probe target selection
│   ├── analysis_causal.py              # SSR, mean shifts, etc.
│   ├── lme_analysis.py                 # Build LME data CSVs
│   ├── lme_analysis.R                  # Fit LME models, generate LaTeX tables
│   ├── classify_question_complexity.py # GPT-5.4 complexity filter (500 → 116 questions)
│   ├── classify_question_topic.py      # GPT-4o-mini topic classifier
│   ├── run_test_retest.py              # Test-retest reliability
│   ├── run_temperature_sensitivity.py  # Temperature ablation
│   ├── run_scrambled_dag.py            # Edge permutation placebo
│   ├── run_ablation.py                 # Structural ablation ("ignore this factor")
│   ├── run_spurious_context.py         # Spurious context control
│   ├── run_propagation.py              # Network propagation analysis
│   ├── run_superforecasting_dag.py     # Superforecasting prompt comparison
│   ├── run_factor_ranking.py           # Convergent/incremental validity
│   ├── rate_probe_persuasiveness.py    # Persuasiveness judge (validation)
│   ├── high_complexity_questions.json  # 116 filtered ForecastBench questions w/ topics
│   └── ...
│
├── paper/                            # Belief sensitivity paper
│   ├── methods_and_results.tex         # Active paper draft
│   ├── references.bib
│   ├── figures/                        # main/, supplement/, internal/, archive/
│   ├── tables/                         # main/, supplement/, archive/ (.tex)
│   └── methods_style_guide.md
│
├── known_causal_models/              # Second paper: causal discovery on simulations
│   ├── causal_discovery/               # Interventional discovery pipeline
│   ├── conflict/                       # Geopolitical simulation engine
│   ├── market/                         # Commodity market simulation engine
│   ├── forecast_multi/                 # Multi-agent forecasting framework
│   ├── simulation/                     # R-based simulation tools
│   └── README.md                       # Detailed module docs
│
├── belief-sensitivity-explorer/      # Causal Forecast Lab (separate Next.js repo)
│
├── outputs/                          # Experiment results (gitignored)
│   └── sensitivity/causal/             # Per-model question results
│
└── archive/                          # Legacy code & old outputs
```

---

## Documentation

| Document | Covers |
|---|---|
| **[paper/methods_and_results.tex](paper/methods_and_results.tex)** | Belief sensitivity paper draft (methods + results + appendix) |
| **[paper/methods_style_guide.md](paper/methods_style_guide.md)** | Writing conventions for the paper |
| **[paper/figure_style_guide.md](paper/figure_style_guide.md)** | Figure conventions |
| **[known_causal_models/README.md](known_causal_models/README.md)** | Causal discovery + simulation engines |
| **[belief-sensitivity-explorer/README.md](belief-sensitivity-explorer/README.md)** | Interactive explorer (Next.js) |

---

## Citation

If you use this work, please cite:

```bibtex
@misc{kelley2026belief,
  author = {Kelley, Sean W. and Riedl, Christoph},
  title  = {Probing Belief Sensitivity in {LLM} Forecasters: Do Causal Structure and Importance Predict Belief Updates?},
  year   = {2026},
  note   = {Manuscript under review}
}
```

---

## License

MIT License — see LICENSE file for details

---

## Contact

- **Email:** se.kelley@northeastern.edu
- **Issues:** [GitHub Issues](https://github.com/seanwkelley/LLM_Forecasting/issues)

---

**Status:** Active Research | **Last Updated:** April 29, 2026
