# Multi-Agent Simulation & Forecasting

**February 2026** | Northeastern University

LLM-based multi-agent simulations across two domains (commodity market and geopolitical conflict), with **Partial Information Decomposition (PID)** measuring emergent coordination and **LLM forecasting experiments** testing whether Theory of Mind helps or hurts prediction accuracy.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Overview

This project investigates how LLM agents coordinate in multi-agent simulations and whether knowledge of agent personas (Theory of Mind) improves external forecasting. Two simulation domains provide a controlled comparison:

- **Market**: 7 LLM trading agents in a double-auction commodity market. Prices emerge deterministically from agent orders.
- **Conflict**: 7 LLM geopolitical agents across two factions (Novaris vs. Tethys). Escalation dynamics emerge from strategic decisions.

Each domain runs three simulation conditions (rule-based baseline, LLM without personas, LLM with personas) and a forecasting experiment where external LLM forecasters predict next-period outcomes with or without Theory of Mind context.

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

### Statistical Analysis

```bash
# LMM analysis (requires R with lme4, lmerTest)
Rscript market/analyze_forecasts.R
Rscript conflict/analyze_forecasts.R
```

---

## Simulation Design

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

---

## Methods

### Partial Information Decomposition (PID)

We use the Williams-Beer I_min decomposition to decompose mutual information between agent pairs and the target variable into **synergy** (information available only from the pair jointly), **redundancy** (shared information), and **unique** information.

- **Emergence Capacity (EC)**: Median pairwise synergy across all agent pairs
- **Cross-faction EC**: Median synergy of only cross-faction pairs (conflict only)
- **Higher-order synergy (G3)**: Triplet coalition test -- MI(A,B,C;Y) - max(MI pairwise)
- **Permutation tests**: Row-shuffle (500 permutations) destroys temporal alignment; column-shift preserves autocorrelation but destroys cross-agent alignment

### Forecasting Experiment

External LLM forecasters observe simulation history and predict next-period outcomes. 2x2 factorial design: demographic personas x Theory of Mind (agent descriptions).

- **Market**: 4 conditions (Llama/Qwen x ToM), 4,800 forecasts
- **Conflict**: 2 conditions (Llama x ToM), 2,400 forecasts
- **Statistical model**: Linear mixed-effects with nested random intercepts for period-within-scenario clustering

---

## Documentation

| Document | Covers |
|----------|--------|
| **[EXPERIMENT_NOTES.md](EXPERIMENT_NOTES.md)** | Active experiment log -- market + conflict status, key findings |
| **[MARKET_EXPERIMENT.md](docs/MARKET_EXPERIMENT.md)** | Market domain: simulation design, PID analysis (3 conditions), forecasting results |
| **[RESULTS_FORECASTING_AND_PID.md](docs/RESULTS_FORECASTING_AND_PID.md)** | Cross-domain: LMM forecasting methods/results, conflict PID analysis, market vs conflict comparison |

Legacy R wargame documentation is in `docs/archive/`.

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
├── docs/                              # Documentation
│   ├── RESULTS_FORECASTING_AND_PID.md   # Cross-domain: forecasting, PID, methods
│   ├── MARKET_EXPERIMENT.md             # Market domain: design, PID, forecasting
│   └── archive/                         # Legacy R wargame documentation
├── src/                               # Legacy R wargame simulation
├── outputs/                           # Experiment results
│   ├── market_llama_persona/   # Market: LLM with personas
│   ├── market_llama_no_persona/           # Market: LLM no-persona
│   ├── market_baseline/        # Market: rule-based baseline
│   ├── conflict_llama_persona/                # Conflict: LLM with personas
│   ├── conflict_llama_no_persona/     # Conflict: LLM no-persona
│   ├── conflict_baseline/             # Conflict: rule-based baseline
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

**Status:** Active Research | **Last Updated:** February 18, 2026
