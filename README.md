# Multi-Agent Simulation & Forecasting

**February 2026** | Northeastern University

LLM-based multi-agent simulations across two domains (commodity market and geopolitical conflict), with **Partial Information Decomposition (PID)** measuring emergent coordination and **LLM forecasting experiments** testing whether Theory of Mind helps or hurts prediction accuracy.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview

This project investigates how LLM agents coordinate in multi-agent simulations and whether knowledge of agent personas (Theory of Mind) improves external forecasting. Four components provide a controlled comparison:

- **Market**: 7 LLM trading agents in a double-auction commodity market. Prices emerge deterministically from agent orders.
- **Conflict**: 7 LLM geopolitical agents across two factions (Novaris vs. Tethys). Escalation dynamics emerge from strategic decisions.
- **Multi-Agent Forecasting**: Tests whether causal graph knowledge and multi-agent deliberation improve time-series forecasting. 13 experimental conditions (4 communication structures × 4 information levels) across both domains.
- **Belief Sensitivity**: Tests how robust LLM probability forecasts are by systematically challenging the model's stated assumptions and measuring probability shifts.

The market and conflict domains each run three simulation conditions (rule-based baseline, LLM without personas, LLM with personas) and a forecasting experiment where external LLM forecasters predict next-period outcomes with or without Theory of Mind context. The multi-agent forecasting framework extends this by systematically varying what forecasters know (time-series only → causal graph → mechanistic rules) and how they communicate (single → independent ensemble → debate → specialization). The belief sensitivity experiment complements these by measuring whether LLMs anchor too strongly, update rationally, or are easily swayed when their reasoning is challenged.

---

## Key Findings

### Theory of Mind has opposite effects by domain

| Domain | ToM Effect | Direction | p-value | Interpretation |
|--------|-----------|-----------|---------|----------------|
| Market | -17.27 MSE | **Helps** | 0.027 | Agent strategies have direct, mechanistic link to prices |
| Conflict | +0.286 MSE | **Hurts** | 0.010 | Agent personas cause overfitting to expected behavior |

### PID explains the asymmetry

| Metric | Market | Conflict |
|--------|--------|----------|
| Emergence Capacity (EC) | 0.032 bits (p = 0.002) | 0.106 bits (p = 0.000) |
| Baseline EC (rule-based) | 0.041 bits | 0.012 bits |
| No-persona EC | 0.005 bits (n.s.) | 0.115 bits (p = 0.010) |
| Higher-order synergy (G3) | 0.099 | 0.230 |

**Mirror-image pattern**: Market coordination is *mechanistic* -- rule-based agents have the highest EC (0.041) and personas merely recover 79% of it. Conflict coordination is *reasoning-driven* -- LLM agents exceed the baseline by 8-9x, and the domain itself elicits coordination even without personas.

**Persona role differs by domain**: In market, removing personas destroys synergy (EC 0.032 to 0.005). In conflict, removing personas *slightly increases* synergy (0.106 to 0.115) with near-zero behavioral differentiation (JSD = 0.016). The conflict domain is intrinsically strategic enough to elicit coordination from generic LLM agents.

---

## Quick Start

### Prerequisites

- Python 3.10+
- OpenRouter API key ([get one here](https://openrouter.ai))

### Installation

```bash
git clone https://github.com/seanwkelley/LLM_Forecasting.git
cd LLM_Forecasting
pip install openai pydantic numpy scipy pandas

export OPENROUTER_API_KEY="your-api-key-here"
```

### Run Market Simulation

```bash
# Run 10 scenarios x 30 periods with personas (~2 hours)
python market/run_market_sim.py --scenarios 10 --periods 30 --persona

# Run PID analysis on results
python market/run_market_pid.py

# Run forecasting experiment (demographic +/- ToM)
python market/run_market_forecast.py
```

### Run Conflict Simulation

```bash
# Run 10 scenarios x 30 periods with personas (~2 hours)
python conflict/run_conflict_sim.py --scenarios 10 --periods 30 --persona

# Run PID analysis on results
python conflict/run_conflict_pid.py

# Run forecasting experiment (demographic +/- ToM)
python conflict/run_conflict_forecast.py
```

### Run Multi-Agent Forecasting

```bash
# Re-generate baseline simulations with augmented state fields
python market/run_market_sim.py --baseline --n_scenarios 10 --n_periods 30 --seed 42
python conflict/run_conflict_sim.py --baseline --n_scenarios 10 --n_periods 30 --seed 42

# Single forecaster, time-series only (simplest condition)
python -m forecast_multi.runner \
    --domain market --communication single --info-level L0 \
    --baseline-dir outputs/market_baseline --model llama

# Independent ensemble with causal graph knowledge
python -m forecast_multi.runner \
    --domain market --communication independent --info-level L2 \
    --baseline-dir outputs/market_baseline --model llama

# Debate with full mechanistic transparency
python -m forecast_multi.runner \
    --domain conflict --communication debate --info-level L3 \
    --baseline-dir outputs/conflict_baseline --model llama

# Specialization with mechanistic aggregator
python -m forecast_multi.runner \
    --domain market --communication specialization --info-level L2 \
    --baseline-dir outputs/market_baseline --model llama \
    --mechanistic-aggregator

# Resume interrupted run
python -m forecast_multi.runner \
    --domain market --communication debate --info-level L2 \
    --baseline-dir outputs/market_baseline --model llama --resume
```

### Run Belief Sensitivity Analysis

```bash
# --- Flat-reasons mode (default) ---

# Quick smoke test (2 questions, one-turn only, ~1 min)
python forecast_bench/run_sensitivity.py --max-questions 2 --condition one-turn

# Full run (50 questions, both conditions, ~15-20 min)
python forecast_bench/run_sensitivity.py --max-questions 50 --condition both

# Analyze results (one or two output dirs)
python forecast_bench/analysis.py outputs/sensitivity_llama_one-turn outputs/sensitivity_llama_multi-turn

# --- Causal network mode ---

# Smoke test (2 questions, one-turn, ~3 min)
python forecast_bench/run_sensitivity.py --mode causal --max-questions 2 --condition one-turn

# Full run (50 questions, both conditions, ~2-3 hours)
python forecast_bench/run_sensitivity.py --mode causal --max-questions 50 --condition both

# Analyze causal results
python forecast_bench/analysis_causal.py outputs/sensitivity_causal_llama_one-turn outputs/sensitivity_causal_llama_multi-turn
```

### Statistical Analysis

```bash
# LMM analysis (requires R with lme4, lmerTest)
Rscript market/analyze_forecasts.R
Rscript conflict/analyze_forecasts.R
```

---

## Experiment Design

### Belief Sensitivity

Tests how robustly LLMs hold their forecast beliefs under targeted challenges. Two pipeline modes:

**Flat-reasons mode** (`--mode reasons`, default): A 3-stage pipeline:

1. **Initial Forecast**: LLM estimates probability for a binary question and enumerates 3-5 explicit reasons with importance ratings
2. **Probe Generation**: For each reason × 5 probe types (full factorial), a targeted challenge is generated (~20 probes)
3. **Probed Forecast**: The challenge is presented and the model provides an updated probability

**Causal network mode** (`--mode causal`): Replaces flat reasons with a directed causal graph:

1. **Causal Forecast**: LLM estimates probability and constructs a directed causal graph (4-8 factor nodes + 1 outcome node + edges with mechanisms)
2. **Network Analysis**: Pure computation (no LLM) — betweenness centrality, PageRank, path relevance, composite importance scores. Selects ~16 structurally motivated probe targets
3. **Probe Generation**: One probe per target across 10 types: node negation (high/medium/low importance), node strengthening, edge negation (critical/peripheral), edge reversal, edge fabrication, missing node, irrelevant
4. **Probed Forecast**: Challenge presented with full network context

**Core hypothesis**: Probing structurally important elements (high-centrality nodes, critical-path edges) should produce larger probability shifts than probing peripheral elements.

Both modes run under two conditions: **one-turn** (fresh API call per probe, no memory) and **multi-turn** (growing message history, model sees all prior challenges).

### Market Domain

7 LLM trading agents in a **double-auction commodity market**:

| Role | Agents | Strategy |
|------|--------|----------|
| Producer | Volume Mover, Margin Optimizer | Sell-side with different pricing strategies |
| Consumer | Security Stockpiler, Bargain Hunter, Shock Anticipator | Buy-side with different risk profiles |
| Speculator | Momentum Rider, Value Contrarian | Directional trading strategies |

- **Clearing mechanism**: Deterministic double-auction (no LLM involved in price-setting)
- **Shocks**: 6 types (supply disruption, demand surge, weather, policy, etc.)
- **Target variable**: Next-period clearing price

### Conflict Domain

7 LLM geopolitical agents across two rival factions:

| Faction | Agents | Hawk Score |
|---------|--------|------------|
| Novaris (4) | Krasnov, Volkov, Petrova, Morozov | 0.85, 0.55, 0.25, 0.50 |
| Tethys (3) | Marchetti, Bondar, Kovalenko | 0.45, 0.75, 0.30 |

- **Action space**: 15 actions from troop withdrawal (-1.0) to full-scale attack (+2.5)
- **Escalation index**: Tracks cumulative conflict intensity
- **Target variable**: Next-period escalation index

### Three Conditions Per Domain

| Condition | Description | Purpose |
|-----------|-------------|---------|
| **Baseline** | Rule-based agents (deterministic hawk/dove formula) | Non-LLM control |
| **LLM no-persona** | LLM agents with role but no personality | Tests whether domain alone elicits coordination |
| **LLM persona** | LLM agents with full backstory and personality | Tests whether identity adds to coordination |

### Multi-Agent Forecasting Framework (`forecast_multi/`)

Tests whether causal graph knowledge and multi-agent deliberation improve forecasting of aggregate outcomes (clearing price / escalation index) from rule-based baseline simulations.

**Information Levels (what the forecaster knows):**

| Level | Content | Purpose |
|-------|---------|---------|
| **L0** | Time-series history only | Baseline — pure pattern recognition |
| **L1** | + random 50% of expanded variables | Controls for "more data" vs structured data |
| **L2** | + full causal graph + all variables | Tests whether causal structure helps |
| **L3** | + mechanistic agent decision rules | Tests whether full transparency helps |

**Communication Structures (how forecasters interact):**

| Structure | Agents | Calls/period | Design |
|-----------|--------|-------------|--------|
| **Single** | 1 generic analyst | 1 | No deliberation baseline |
| **Independent** | 5 diverse personas | 5 | Post-hoc ensemble (averaged probabilities) |
| **Debate** | 2 opposing analysts | 6 | 3 rounds: predict → critique → finalize |
| **Specialization** | 3 specialists + 1 aggregator | 4 | Subgraph experts + chief analyst integration |

**Design matrix:** 13 conditions per domain (single×4, independent×4, debate×3, specialization×2). ~12,500 LLM calls per domain.

---

## Methods

### Partial Information Decomposition (PID)

We use the Williams-Beer I_min decomposition to decompose mutual information between agent pairs and the target variable into **synergy** (information available only from the pair jointly), **redundancy** (shared information), and **unique** information.

- **Emergence Capacity (EC)**: Median pairwise synergy across all agent pairs
- **Cross-faction EC**: Median synergy of only cross-faction pairs (conflict only)
- **Higher-order synergy (G3)**: Triplet coalition test -- MI(A,B,C;Y) - max(MI pairwise)
- **Permutation tests**: Row-shuffle (500 permutations) destroys temporal alignment; column-shift preserves autocorrelation but destroys cross-agent alignment

### Forecasting Experiment (Phase 1)

External LLM forecasters observe simulation history and predict next-period outcomes. 2x2 factorial design: demographic personas x Theory of Mind (agent descriptions).

- **Market**: 4 conditions (Llama/Qwen x ToM), 4,800 forecasts
- **Conflict**: 2 conditions (Llama x ToM), 2,400 forecasts
- **Statistical model**: Linear mixed-effects with nested random intercepts for period-within-scenario clustering

### Multi-Agent Forecasting (Phase 2)

Extends Phase 1 by systematically decomposing the causal graph and deliberation contributions. Forecasts are made against rule-based baseline simulation data (10 scenarios × 30 periods per domain).

- **Key question**: Does causal structure help beyond "more data"? (L1 vs L2)
- **Key question**: Does deliberation help beyond ensembling? (independent vs debate/specialization)
- **Key question**: Interaction — does graph knowledge help *more* with deliberation?
- **Statistical model**: `brier_score ~ communication * info_level + (1|scenario_id/period)` (linear mixed-effects)

---

## Documentation

| Document | Covers |
|----------|--------|
| **[EXPERIMENT_NOTES.md](EXPERIMENT_NOTES.md)** | Active experiment log -- market + conflict status, key findings |
| **[MARKET_EXPERIMENT.md](docs/MARKET_EXPERIMENT.md)** | Market domain: simulation design, PID analysis (3 conditions), forecasting results |
| **[RESULTS_FORECASTING_AND_PID.md](docs/RESULTS_FORECASTING_AND_PID.md)** | Cross-domain: LMM forecasting methods/results, conflict PID analysis, market vs conflict comparison |
| **[MOTIVATION.md](docs/MOTIVATION.md)** | Research motivation and theoretical framing |

The multi-agent forecasting framework is documented in [EXPERIMENT_NOTES.md](EXPERIMENT_NOTES.md) under "Multi-Agent Forecasting Framework". The belief sensitivity experiment is documented under "Belief Sensitivity Experiment". Legacy R wargame documentation is in `docs/archive/`.

---

## Project Structure

```
LLM_Forecasting/
├── README.md                          # This file
├── EXPERIMENT_NOTES.md                # Active experiment log
├── market/                            # Python market simulation
│   ├── engine.py                        # Double-auction clearing, order book
│   ├── agents_config.py                 # 7 trading agent personas
│   ├── run_market_sim.py                # Simulation runner
│   ├── run_market_forecast.py           # Forecasting experiment
│   ├── run_market_pid.py                # PID analysis runner
│   ├── analyze_forecasts.R              # LMM statistical analysis
│   └── ...
├── conflict/                          # Python conflict simulation
│   ├── engine.py                        # Escalation mechanics, state tracking
│   ├── agents_config.py                 # 7 geopolitical agent personas
│   ├── run_conflict_sim.py              # Simulation runner
│   ├── run_conflict_forecast.py         # Forecasting experiment
│   ├── run_conflict_pid.py              # PID analysis runner
│   ├── analyze_forecasts.R              # LMM statistical analysis
│   └── ...
├── forecast_multi/                    # Multi-agent forecasting framework
│   ├── domain.py                        # Domain adapters (MarketDomain, ConflictDomain)
│   ├── llm_client.py                    # LLM client wrapper + forecast parser
│   ├── evaluation.py                    # Brier, log score, F1, baselines, ensemble
│   ├── causal_text.py                   # Adjacency matrix → natural language
│   ├── config.py                        # Personas, subgraph assignments, design matrix
│   ├── info_builder.py                  # L0–L3 information level builders
│   ├── single.py                        # SingleForecaster (1 call/period)
│   ├── independent.py                   # IndependentEnsemble (5 calls/period)
│   ├── debate.py                        # DebateForecaster (6 calls/period, 3 rounds)
│   ├── specialization.py                # SpecializationForecaster (4 calls/period)
│   └── runner.py                        # CLI + experiment loop + checkpoint/resume
├── forecast_bench/                    # Belief sensitivity analysis
│   ├── llm_client.py                    # OpenRouter client (single + multi-turn)
│   ├── questions.py                     # ForecastBench question loader
│   ├── prompts.py                       # Flat-reasons prompt templates
│   ├── prompts_causal.py                # Causal network prompt templates
│   ├── network_analysis.py              # Graph centrality, target selection (networkx)
│   ├── run_sensitivity.py               # Pipeline runner (--mode reasons|causal)
│   ├── analysis.py                      # Flat-reasons metrics & statistics
│   └── analysis_causal.py              # Causal network metrics (SSR, path premium, etc.)
├── docs/                              # Documentation
│   ├── RESULTS_FORECASTING_AND_PID.md   # Cross-domain: forecasting, PID, methods
│   ├── MARKET_EXPERIMENT.md             # Market domain: design, PID, forecasting
│   └── archive/                         # Legacy R wargame documentation
├── src/                               # Legacy R wargame simulation
├── outputs/                           # Experiment results
│   ├── market_baseline/                 # Market: rule-based baseline (10×30, augmented)
│   ├── market_llama_persona/            # Market: LLM with personas
│   ├── market_llama_no_persona/         # Market: LLM no-persona
│   ├── conflict_baseline/               # Conflict: rule-based baseline (10×30, augmented)
│   ├── conflict_llama_persona/          # Conflict: LLM with personas
│   ├── conflict_llama_no_persona/       # Conflict: LLM no-persona
│   ├── forecast_multi/                  # Multi-agent forecasting results
│   │   ├── market_single_L0/              # Single × L0 condition
│   │   ├── market_debate_L2/              # Debate × L2 condition
│   │   └── ...                            # 13 conditions × 2 domains
│   ├── sensitivity_llama_one-turn/      # Belief sensitivity (reasons): one-turn
│   ├── sensitivity_llama_multi-turn/    # Belief sensitivity (reasons): multi-turn
│   ├── sensitivity_causal_llama_one-turn/  # Belief sensitivity (causal): one-turn
│   ├── sensitivity_causal_llama_multi-turn/ # Belief sensitivity (causal): multi-turn
│   └── ...
└── archive/                           # Archived code & old outputs
```

---

## Citation

If you use this work in your research, please cite:

```bibtex
@software{kelley2026multiagent,
  author = {Kelley, Sean W.},
  title = {Multi-Agent Simulation and Forecasting: PID Analysis of Emergent Coordination},
  year = {2026},
  url = {https://github.com/seanwkelley/LLM_Forecasting}
}
```

---

## License

MIT License - see LICENSE file for details

---

## Contributing

This is an active research project. For questions or collaboration:
- **Email:** se.kelley@northeastern.edu
- **Issues:** [GitHub Issues](https://github.com/seanwkelley/LLM_Forecasting/issues)

---

## Acknowledgments

**Models used:** Llama 3.1 8B (simulation agents + forecasters), Qwen3 235B (forecaster comparison), via [OpenRouter](https://openrouter.ai)

**Related Work:**
- Williams & Beer (2010) - Partial Information Decomposition
- Benjamin et al. (2025) - LLM forecasting capabilities

---

**Status:** Active Research | **Last Updated:** February 23, 2026
