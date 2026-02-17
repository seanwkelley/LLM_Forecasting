# Multi-Agent Wargame Simulation

**Version 3.8.5** | **February 11, 2026**

A sophisticated LLM-based geopolitical simulation modeling conflict dynamics with **11 autonomous agents** across fictionalized countries. Features multi-action systems, cognitive frameworks, and dynamic state tracking. Includes a Python-based multi-agent forecasting system that uses **information sharding** to create ensemble diversity.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 Overview

This simulation creates a realistic geopolitical crisis scenario where AI agents with distinct worldviews, cognitive biases, and strategic objectives make sequential decisions that shape the outcome of an international conflict.

### Key Features

- **🤖 11 Autonomous Agents** with cognitive frameworks (rationality, paranoia, deception capacity)
- **⚔️ Multi-Action System** - Domain experts propose, presidents approve (3-6 concurrent actions per faction)
- **🔄 State Threading** - Sequential execution preserving ~30 direct state mutations
- **🎲 Probabilistic Events** - 15 external event types with 50-85% effectiveness
- **📊 68 Executable Actions** across 7 categories (diplomatic, military, economic, intelligence, etc.)
- **🧠 Mixed LLM Strategy** - Qwen (proposals), Claude Sonnet 4 (decisions), Gemini (aggregation)
- **🌐 Dynamic State Tracking** - GDP, military balance, territory, crisis level, sanctions

---

## 🚀 Quick Start

### Prerequisites

- R 4.2+ with packages: `httr`, `jsonlite`, `xml2`
- OpenRouter API key ([get one here](https://openrouter.ai))

### Installation

```bash
# Clone the repository
git clone https://github.com/seanwkelley/LLM_Forecasting.git
cd LLM_Forecasting

# Install R packages
Rscript install_packages.R

# Set your API key
export OPENROUTER_API_KEY="your-api-key-here"
```

### Run Simulation

```bash
# Run full 10-period simulation (~2-3 hours)
Rscript run_simulation_with_actions.R

# Generate 100 parametrically varied 1-period scenarios (~25 hours)
Rscript generate_multiscenario_dataset.R
```

**Outputs:** Results saved to `outputs/` directory
- `simulation_state.rds` - Complete state object
- `simulation_summary_*.txt` - Action log
- `interactions/period_*_actions.csv` - All decisions and outcomes
- `human_forecasting/` - Forecasting prompts for human participants
- `multiscenario/` - 100 parametric scenarios with ground truth

---

## 📖 Documentation

### Active Documentation

| Document | Covers |
|----------|--------|
| **[EXPERIMENT_NOTES.md](EXPERIMENT_NOTES.md)** | Active experiment log -- market + conflict status, key findings |
| **[MARKET_EXPERIMENT.md](docs/MARKET_EXPERIMENT.md)** | Market domain: simulation design, PID analysis (3 conditions), forecasting results |
| **[RESULTS_FORECASTING_AND_PID.md](docs/RESULTS_FORECASTING_AND_PID.md)** | Cross-domain: LMM forecasting methods/results, conflict PID analysis, market vs conflict comparison |

Legacy R wargame documentation is in `docs/archive/`.

### Current Experiments (Feb 18)

- **Market simulation** (complete): 7 LLM trading agents, double-auction clearing, PID analysis shows significant emergent coordination (EC = 0.032, p = 0.002). Forecasting with Theory of Mind significantly reduces prediction error (p = 0.027).
- **Conflict simulation** (complete): 7 LLM geopolitical agents, escalation dynamics. PID shows 3.3x more emergent coordination than market (EC = 0.106, p = 0.000). Personas are unnecessary for synergy in conflict (no-persona EC = 0.115 vs persona EC = 0.106) -- opposite of market where personas are required. Theory of Mind significantly *increases* prediction error (p = 0.010).
- See `docs/RESULTS_FORECASTING_AND_PID.md` for full statistical methods and results.

---

## 🎭 The Scenario

### Factionalized Countries

**Novaris (Major Power)**
- Nationalist populist government with historical grievances
- Claims Tethys as "inseparable territory"
- 4 agents: General, Minister, Economic Advisor, Intelligence Director

**Tethys (Smaller Power)**
- Democratic government defending sovereignty
- Asymmetric capabilities (cyber, precision strikes)
- 4 agents: President, General, Diplomat, Intelligence Director

**External Actors**
- **Meridian** - Allied democracy providing support
- **Valkoria** - Aligned autocracy coordinating with Novaris
- **Aurelia** - Neutral power balancing interests
- **International Org** - Mediator seeking humanitarian access

---

## 🔬 Research Applications

### Forecasting

The simulation generates **forecasting prompts** for human participants to test:
- LLM vs. human forecasting accuracy
- Impact of information quality on predictions
- Temporal dynamics of geopolitical forecasts

**Control Condition:** Randomized data to distinguish genuine predictive skill from pattern recognition

### Multi-Agent Dynamics

Explore how:
- Cognitive biases affect decision-making under uncertainty
- Multi-action coordination impacts strategic diversity
- External events shape crisis trajectories
- Deception and information asymmetry influence outcomes

---

## 📊 Key Metrics

### Action Diversity

| Metric | v3.7 Baseline | v3.8.5 Current |
|--------|---------------|----------------|
| Actions per period | 6 | 12-16 |
| Unique actions (10 periods) | 15-20 | 35-45 |
| Multi-domain warfare | Limited | Naval, Cyber, Air, Information |

### State Evolution

- **Crisis Level:** 0-10 scale tracking escalation intensity
- **Military Balance:** -1 to +1 (Novaris advantage → Tethys advantage)
- **Economic Impact:** GDP changes, sanctions levels, resource embargos
- **Territory Control:** 0-1 proportion of original territory held

---

## 🛠️ Technical Architecture

### State Threading (v3.8.5)

Multi-action factions execute actions **sequentially** with explicit state threading:

```r
state <- initial_state
for (action in approved_actions) {
  execution_result <- execute_action(action, state)
  state <- execution_result$state  # Preserve mutations
}
```

**Impact:** All ~30 direct state mutations now preserved (GDP, territory, sanctions, etc.)

### Probabilistic External Events

15 event types with realistic success rates:
- **Battlefield Development** (75% effectiveness)
- **Cyber Incidents** (65% effectiveness)
- **Economic Shocks** (80% effectiveness)
- **Diplomatic Developments** (50% effectiveness)

### Mixed LLM Strategy

| Task | Model | Rationale |
|------|-------|-----------|
| **Proposals** | Qwen 2.5 72B | Creative, domain-appropriate suggestions |
| **Approvals** | Claude Sonnet 4 | Strategic judgment, reliable parsing |
| **Aggregation** | Gemini 2.0 Flash | Fast probability assessments |

---

## Project Structure

```
LLM_Forecasting/
├── README.md                        # This file
├── EXPERIMENT_NOTES.md              # Active experiment log
├── config.R                         # Model & scenario configuration
├── src/                             # Core R wargame simulation (16 files)
│   ├── simulation_with_actions.R      # Main simulation loop
│   ├── multi_action_system.R          # Proposal/approval system
│   ├── multi_action_effects.R         # State threading & effects
│   └── ...
├── market/                          # Python market simulation
│   ├── engine.py                      # Double-auction clearing, order book
│   ├── agents_config.py               # 7 trading agent personas
│   ├── run_market_sim.py              # Simulation runner
│   ├── run_market_forecast.py         # Forecasting experiment
│   ├── run_market_pid.py              # PID analysis runner
│   ├── analyze_forecasts.R            # LMM statistical analysis
│   └── ...
├── conflict/                        # Python conflict simulation
│   ├── engine.py                      # Escalation mechanics, state tracking
│   ├── agents_config.py               # 7 geopolitical agent personas
│   ├── run_conflict_sim.py            # Simulation runner
│   ├── run_conflict_forecast.py       # Forecasting experiment
│   ├── run_conflict_pid.py            # PID analysis runner
│   ├── analyze_forecasts.R            # LMM statistical analysis
│   └── ...
├── docs/                            # Documentation
│   ├── RESULTS_FORECASTING_AND_PID.md # Cross-domain: forecasting, PID, methods
│   ├── MARKET_EXPERIMENT.md           # Market domain: design, PID, forecasting
│   └── archive/                       # Legacy R wargame documentation
├── outputs/                         # Experiment results
│   ├── market_sim_llama_10s30p_persona/ # Market: LLM with personas
│   ├── market_sim_llama_10s30p/         # Market: LLM no-persona
│   ├── market_sim_baseline_10s30p/      # Market: rule-based baseline
│   ├── conflict_sim_llama/              # Conflict: LLM with personas
│   ├── conflict_sim_llama_no_persona/   # Conflict: LLM no-persona
│   ├── conflict_sim_baseline/           # Conflict: rule-based baseline
│   └── ...
└── archive/                         # Archived code & old outputs
```

---

## 🔄 Version History

### v3.8.5 (February 8-9, 2026) - State Threading & Multi-Target Fix
- **State threading** for multi-action factions (preserves ~30 mutations)
- **Probabilistic external events** (15 types, 50-85% effectiveness)
- **Multi-target resolution** for diplomatic actions
- **Symmetric thresholds** (<5% or >95% early termination)
- **Model switch** to Claude Sonnet 4 (100% parsing success)

### v3.8.2 (February 2, 2026) - Discussion Memory
- Agents see previous period discussions
- Conversational continuity across periods
- LLM message summarization (Gemini 2.5 Flash)

### v3.8.1 (February 1, 2026) - XML-Tagged Prompts
- 100% parsing success with structured prompts
- Multi-domain events (naval, cyber, air, information)
- Enhanced action diversity (68 total actions)

### v3.8 (January 31, 2026) - Multi-Action System
- Domain experts propose 1-3 actions each
- Presidential approval/veto process
- Parallel execution with effect resolution

---

## 📝 Citation

If you use this simulation in your research, please cite:

```bibtex
@software{kelley2026multiagent,
  author = {Kelley, Sean W.},
  title = {Multi-Agent Wargame Simulation v3.8.5},
  year = {2026},
  url = {https://github.com/seanwkelley/LLM_Forecasting}
}
```

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🤝 Contributing

This is an active research project. For questions or collaboration:
- **Email:** seanwkelley@gmail.com
- **Issues:** [GitHub Issues](https://github.com/seanwkelley/LLM_Forecasting/issues)

---

## 🙏 Acknowledgments

Built with assistance from **Claude** (Anthropic)

**Related Work:**
- Benjamin et al. (2025) - LLM forecasting capabilities
- Multi-agent reinforcement learning literature
- Geopolitical crisis modeling frameworks

---

**Status:** Active Research | **Last Updated:** February 18, 2026

**Recent Updates:**
- **Feb 18:** No-persona conflict sim + PID: personas unnecessary for synergy in conflict (no-persona EC=0.115 vs persona EC=0.106), opposite of market. Three-condition comparison in `docs/STATISTICAL_ANALYSIS.md`
- **Feb 18:** Conflict PID analysis: EC = 0.106 (p=0.000), 3.3x more emergent coordination than market. 100% positive triplet G3
- **Feb 17:** Statistical analysis with period-within-scenario clustering. ToM helps market (p=0.027) but hurts conflict (p=0.010). See `docs/STATISTICAL_ANALYSIS.md`
- **Feb 16:** Market and conflict forecasting experiments complete (6 conditions, 7,200 LLM forecasts)
- **Feb 15-16:** Market PID analysis: personas recover 79% of baseline emergent coordination (EC=0.032, p=0.002)
- **Feb 14:** Backstory reframing reduces forecast MSE by 58-61%
- **Feb 11:** Multi-scenario dataset generation, information sharding, persona-rewrite infrastructure
- **Feb 9:** State threading & probabilistic events implemented
