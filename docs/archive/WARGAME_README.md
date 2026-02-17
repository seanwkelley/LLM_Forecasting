# Multi-Agent Wargame Simulation

**Version 3.8.5** | **Last Updated:** February 8, 2026

A sophisticated LLM-based simulation modeling conflict dynamics with **11 intra-country actors** across fictionalized countries (Novaris, Tethys, Meridian, Aurelia). The simulation features cognitive worldviews, information asymmetry, deception mechanics, **68 executable actions**, multi-domain warfare, and dynamic state tracking to forecast probability of government collapse.

**New in v3.8.5 (February 8, 2026):**
- **State threading:** Multi-action factions now execute actions sequentially, preserving ~30 direct state mutations that were previously lost due to R copy-on-modify semantics
- **Probabilistic external events:** All 15 event types (including naval, air, cyber, information, economic) now have state handlers with 50-85% effectiveness probabilities
- **GDP effect application:** GDP changes now correctly applied for multi-action factions using faction identity
- **Forecasting prompt pipeline:** Proper temporal structure (situation -> developments -> forecast) with state-to-text and actions-to-news conversion
- **Control condition:** 3-layer randomization (metric permutation, event narrative flipping, probability noise) breaks causal chains while preserving local coherence

**v3.8.1 Features:**
- **XML-tagged prompts:** 100% parsing success rate with semantic tags
- **Mixed LLM strategy:** Qwen (proposals), DeepSeek (approval), Gemini (aggregation)
- **Multi-domain events:** Naval, Cyber, Air, Information warfare events

**v3.8 Core Features:**
- **Multi-action proposal system:** Domain experts (Military, Intelligence, Diplomatic, Economic) propose 1-3 actions each
- **Presidential approval:** Government leader reviews all proposals, approves/vetoes based on strategic judgment (not crisis-reactive)
- **Sequential execution with state threading:** Approved actions execute sequentially (3-6 per faction per period), preserving all direct state mutations
- **Effect resolution:** Cumulative effects, diminishing returns, contradictions (peace talks + sabotage), synergies (intel + sabotage)
- **Cross-expertise recommendations:** Agents can recommend actions outside their traditional domain
- **Balanced scenario:** Both major/small powers have offensive and defensive capabilities

## Quick Start

**To run the simulation:**
```bash
Rscript run_simulation_with_actions.R
```

**Documentation:**
- **[guides/MULTI_ACTION_SYSTEM_GUIDE.md](guides/MULTI_ACTION_SYSTEM_GUIDE.md)** - Complete v3.8.5 system documentation
- **[SIMULATION_MECHANICS.md](SIMULATION_MECHANICS.md)** - Sequential action order and temporal dynamics ✨ NEW
- **[FORECASTING_SYSTEM.md](FORECASTING_SYSTEM.md)** - LLM forecasting methodology and results ✨ NEW
- **[guides/CLAUDE.md](guides/CLAUDE.md)** - Project context for Claude AI
- **[guides/FACTION_OBJECTIVES.md](guides/FACTION_OBJECTIVES.md)** - Faction capabilities and goals

---

## Overview

This simulation creates a realistic wargame scenario where:
- **11 LLM agents** represent decision-makers: military, government, economic, intelligence, diplomatic roles
- Each agent has **cognitive framework**: worldview (realist, liberal, nationalist, etc.), deception capacity/willingness, information access
- Agents **execute 68 concrete actions** with real consequences: military strikes, sanctions, covert ops, diplomacy, WMD
- **Dynamic state tracking**: GDP, military strength, territory control, crisis level update based on actions
- **Information asymmetry**: intelligence directors see everything, opposition leaders see little, economic advisors see data
- **Deception mechanics**: agents can attempt to deceive based on capacity vs. target's analytical ability
- **Probabilistic outcomes**: Actions succeed/fail based on force ratios, capabilities, information access, and current military balance
- **Cascading effects**: Combat causes asymmetric attrition (winners lose less), sanctions damage GDP, covert ops risk exposure
- **Economic sustainability**: Low GDP degrades military capabilities over time
- **Action repetition tracking**: Repeated peace_talks have diminishing effectiveness (base prob reduced by 15% per attempt, floor 10%)
- **External actor drift**: External actors' alignments can shift based on crisis level, territory changes, atrocities, nuclear use, and economic factors
- **Pre-invasion scenario**: Optional starting condition where invasion hasn't occurred yet - conflict is emergent based on agent decisions
- **External events** (economic shocks, battlefield shifts, wild cards) inject uncertainty
- A separate **aggregator LLM** evaluates the probability of government collapse after each period
- All interactions and decisions are **fully logged** for analysis including deception attempts and trust changes
- **Human forecasting prompts** automatically generated to compare LLM vs human predictions

### Central Research Question
**What is the probability that the smaller power's government will be toppled?**

### Human vs LLM Forecasting (NEW in v3.2)
The system automatically generates forecasting prompts for each period that can be given to human participants. This enables direct comparison of LLM aggregator forecasts vs human expert predictions based on the same information.

**NEW:** Control condition generation tests whether forecasters can distinguish genuine patterns from noise:
- **TRUE condition**: Actual simulation dynamics with real information
- **CONTROL condition**: Constrained randomization breaks info→outcome connection while maintaining plausibility
- Tests overfitting, signal/noise discrimination, and base rate usage
- See `MULTI_ACTION_SYSTEM_GUIDE.md` (Control Condition Design section) for detailed methodology

## Project Structure

```
LLM_Forecasting/
├── config.R                         # Configuration, agent definitions, event probabilities
├── run_simulation_with_actions.R    # CURRENT ENTRY POINT - run simulation
├── generate_prompts_v2.R           # Generate TRUE + CONTROL forecasting prompts
├── README.md                        # This file
├── docs/                            # Documentation
│   ├── guides/                        # Current system guides
│   │   ├── MULTI_ACTION_SYSTEM_GUIDE.md     # v3.8.5 complete system documentation
│   │   ├── CLAUDE.md                        # Project context for Claude AI
│   │   ├── FACTION_OBJECTIVES.md            # Faction capabilities and goals
│   │   └── COMPREHENSIVE_COMPARISON.md      # Version comparison analysis
│   ├── test_results/                  # Test run results and analysis
│   └── archive/                       # Deprecated documentation
├── src/                             # Source code
│   ├── multi_action_system.R          # v3.8: Domain proposals + presidential approval
│   ├── multi_action_effects.R         # v3.8.5: Effect resolution with state threading
│   ├── action_execution.R             # Execute actions, ~30 direct state mutations
│   ├── agent_decision.R               # Decision routing (multi-action vs single-action)
│   ├── simulation_with_actions.R      # Main simulation loop, 15 external event handlers
│   ├── event_generator.R              # External event generation (15 types)
│   ├── forecast_prompts_public_v2.R   # Prompt construction (state->text, actions->news)
│   ├── control_condition.R            # 3-layer randomization for CONTROL condition
│   ├── interaction_engine.R           # Agent-to-agent communication, CSV export
│   ├── agent_system.R                 # Agent creation, LLM calls
│   ├── aggregator.R                   # Probability assessment LLM
│   ├── state_manager.R                # Logging and state management
│   ├── integrated_agent_system.R      # Cognitive framework (worldviews, deception)
│   ├── enhanced_action_space.R        # 68 actions across 7 categories
│   ├── analysis.R                     # Visualization and analysis
│   └── fictionalized_scenarios.R      # Named countries, dynamic scenarios
├── archive/                         # Deprecated files (for reference)
├── data/                            # Generated during simulation
│   ├── interactions/                  # Full interaction transcripts by period
│   ├── agent_states/                  # Agent position evolution over time
│   └── networks/                      # Interaction network data
└── outputs/                         # Simulation results
    ├── simulation_summary_*.txt       # Complete narrative
    ├── simulation_state.rds           # Complete state for analysis
    ├── assessments.csv                # Probability timeline
    ├── prompts/                       # Forecasting prompts (TRUE + CONTROL)
    └── run_*/                         # Per-run outputs
```

## Installation

### Prerequisites
- R (>= 4.0)
- Required R packages:
  ```r
  install.packages(c("httr", "jsonlite", "ggplot2", "dplyr", "tidyr", "igraph", "uuid"))
  ```

### Setup
1. Clone or download this repository
2. Set your OpenRouter API key:
   ```bash
   export OPENROUTER_API_KEY='your-api-key-here'
   ```
   Or in R:
   ```r
   Sys.setenv(OPENROUTER_API_KEY = 'your-api-key-here')
   ```

## Usage

### Running a Simulation

**Command line (RECOMMENDED):**
```bash
Rscript run_simulation_with_actions.R
```

**In R console:**
```r
source("run_simulation_with_actions.R")
```

The simulation will:
1. Initialize 11 agents with distinct personas and cognitive frameworks
2. Run for 3-10 periods (21-70 simulated days)
3. **Each period:**
   - Generate external events (including shock events that affect state)
   - **Intra-faction coordination** - agents within each faction discuss and debate strategies
   - **Domain expert proposals** (major/small powers) - Military, Intel, Diplomatic, Economic experts each propose 1-3 actions
   - **Presidential approval** - Government leader reviews all proposals, approves/vetoes based on strategic judgment
   - **Multi-action execution** - Approved actions execute sequentially with state threading (3-6 actions per faction)
   - **Effect resolution** - Cumulative effects, contradictions, synergies, diminishing returns applied to threaded state
   - **Post-action discussion** - agents react to results and coordinate responses
   - **Aggregator assessment** - probability of government collapse using full state history
4. Save all data and state automatically

**Note:** External actors (Meridian, Valkoria, Aurelia, International Org) use traditional single-action system.

### Analyzing Results

Generate summary statistics and visualizations:
```r
source("src/analysis.R")
analyze_simulation("outputs")
```

This creates:
- `probability_timeline.png` - Probability evolution over time
- `network_period_X.png` - Interaction networks for key periods
- `transcripts.txt` - Full conversation transcripts
- `forecasting_prompts.txt` - Prompts for human forecasters
- `forecasting_answer_key.txt` - LLM forecasts for comparison
- Summary statistics printed to console

## Agent Personas

### Major Power (Aggressor)
- **Military Chief of Staff** - High hawk, strong alignment
- **Defense Minister** - Moderate hawk, strong alignment
- **Economic Advisor** - Dove-leaning, weak alignment (cost concerns)
- **Intelligence Director** - Moderate hawk, moderate alignment

### Smaller Power (Defender)
- **President** - Moderate hawk, sets policy, strong alignment
- **Military Commander** - High hawk, strong alignment
- **Foreign Minister** - Dove-leaning, seeks diplomacy, strong alignment
- **Opposition Leader** - Variable, low policy adherence (political survival)

### External Actors (Independent)
- **Meridian** (Allied Defender) - Hawk 0.6, supports Tethys with military/economic aid
- **Valkoria** (Allied Aggressor) - Hawk 0.7, supports Novaris with diplomatic cover
- **Aurelia** (Neutral Power) - Hawk 0.2, seeks mediation and regional stability
- **International Organization** (UN/EU) - Hawk 0.1, humanitarian and ceasefire focus

Each external actor acts **independently**, making their own decisions based on their interests.

Each agent's behavior is driven by:
- **Hawk/Dove score** (0-1): Preference for military vs diplomatic solutions
- **Policy adherence** (0-1): Alignment with official government positions
- **Objective alignment** (0-1): Commitment to faction's central goals
- **Cognitive Rationality** (0-1): Logical vs impulsive decision-making (lowered for ultra-hawks, political figures)
- **Worldview**: Ideological lens (realist, liberal_institutionalist, nationalist_populist, pragmatic_technocrat, constructivist, revolutionary_revisionist) - now faction-aware assignment

## LLM Models

The simulation uses a **mixed model strategy** for optimal performance:

| Component | Model | Purpose |
|-----------|-------|---------|
| **Agent Proposals** | Qwen 2.5 72B | Domain expert action proposals, coordination discussions |
| **Approval Decisions** | DeepSeek v3 | Presidential review of proposals (approve/veto/counter) |
| **Aggregation** | Gemini 2.0 Flash | Probability assessments, trend analysis |

**Key Achievement:** XML-tagged prompts + strict formatting requirements = **100% parsing success rate** (tested across 10+ decision points with DeepSeek)

## Configuration

Edit `config.R` to customize:
- Number of simulation periods
- Agent personas and characteristics
- External event types and probabilities
- LLM models (via OpenRouter) - currently optimized for Qwen/DeepSeek/Gemini mix
- Logging settings

### Example Customization

```r
# Change simulation length
N_PERIODS <- 15  # 15 periods = 105 days

# Modify agent persona
AGENTS$major_economic_advisor$hawk_dove <- 0.1  # More dovish
AGENTS$major_economic_advisor$objective_alignment <- 0.2  # Less aligned

# Add new event type
EXTERNAL_EVENTS <- c(EXTERNAL_EVENTS, list(
  list(
    type = "cyber_attack",
    name = "Major Cyber Attack",
    probability = 0.15,
    impact = "Critical infrastructure disrupted by cyberwarfare"
  )
))
```

## Output Data

### Assessments (outputs/assessments.csv)
```csv
period,timestamp,probability,confidence,trend,key_factors
1,2024-01-15 10:30:00,0.25,MEDIUM,STABLE,"Initial defensive success..."
2,2024-01-15 11:15:00,0.30,MEDIUM,INCREASING,"Economic pressure mounting..."
```

### Interaction Logs (data/interactions/period_N/)
Full JSON records of each interaction including:
- Participants and their factions
- Complete message transcripts
- Interaction type and topic
- Timestamps

### Agent States (data/agent_states/)
Timeline of each agent's position evolution:
```csv
period,timestamp,hawk_dove_score,policy_adherence,objective_alignment,n_interactions
1,2024-01-15 10:30:00,0.7,0.9,0.9,3
```

### Network Data (data/networks/)
Interaction patterns between agents:
```csv
period,agent_A,agent_B,interaction_type,interaction_count
1,small_president,small_military_commander,intra_faction_coordination,2
```

## Analysis Functions

```r
# Load completed simulation
state <- load_simulation_state("outputs")

# Generate summary statistics
stats <- generate_summary_stats(state)

# Plot probability timeline
plot_probability_timeline(state, "my_plot.png")

# Visualize interaction network for period 5
plot_interaction_network(state, period = 5, "network.png")

# Export all transcripts
export_interaction_transcripts(state, "all_conversations.txt")

# Print summary report
print_summary_report(state)
```

## Research Applications

This simulation enables study of:
1. **Forecasting accuracy** - Compare LLM predictions to expert forecasts
2. **Agent dynamics** - How internal faction disagreements affect outcomes
3. **Persona effects** - Impact of hawk/dove orientation on conflict trajectories
4. **Information flow** - Network analysis of influence patterns
5. **Event sensitivity** - Which external events most shift probabilities
6. **Temporal patterns** - How forecasts evolve with new information

## Extending the Simulation

### Adding New Agents
```r
AGENTS$new_agent <- list(
  name = "Agent Name",
  faction = "major_power",  # or "small_power" or "external"
  role = "role_description",
  hawk_dove = 0.5,
  policy_adherence = 0.7,
  objective_alignment = 0.8,
  description = "Agent background and motivations"
)
```

### Custom Event Generators
```r
# In event_generator.R, add:
generate_custom_event <- function(period, context) {
  # Your event logic here
  list(
    period = period,
    timestamp = Sys.time(),
    type = "custom",
    name = "Event Name",
    description = "What happened",
    severity = 0.7
  )
}
```

### Modify Interaction Scenarios
Edit `interaction_engine.R` to:
- Change interaction frequency
- Add new interaction types (e.g., "intelligence briefing", "crisis meeting")
- Customize conversation topics based on scenario state

## Human Forecasting Comparison

The simulation automatically generates forecasting prompts for human participants to compare LLM vs human predictions.

### Generate Forecasting Materials

After running a simulation:
```r
source("src/analysis.R")
analyze_simulation("outputs")
```

This creates:
- **`forecasting_prompts.txt`** - Give these to human forecasters
- **`forecasting_answer_key.txt`** - LLM aggregator's forecasts
- **`forecasting_template.csv`** - For entering human predictions

### Example Prompt (Period 1)

Human forecasters receive:
```
FORECASTING TASK - PERIOD 1

Based on the initial scenario information, estimate the probability (0-100%)
that the smaller power's government will collapse by Day 7.

INITIAL SCENARIO:
A major power has initiated territorial operations...

QUESTION:
What is the probability that the government will be removed from power by Day 7?

Your forecast: ___%
```

### Collect and Compare Forecasts

```r
source("src/forecast_prompts.R")

# Load simulation
state <- load_simulation_state("outputs")

# Enter human forecasts (0-1 scale)
human_probs <- c(0.25, 0.30, 0.35, 0.40, 0.38, 0.42, 0.45, 0.48, 0.50, 0.52)

# Compare
comparison <- compare_forecasts(state, human_probs)
print(comparison)

# Calculate metrics
mean(comparison$abs_difference)  # Mean absolute error
cor(comparison$llm_forecast, comparison$human_forecast)  # Correlation
```

### Research Applications

- **LLM vs Human Accuracy**: Which forecasts are more accurate?
- **Calibration Analysis**: Are LLM or human forecasts better calibrated?
- **Information Processing**: How do forecasters update beliefs?
- **Expertise Effects**: Do domain experts outperform LLMs?
- **Temporal Dynamics**: Who adapts better to new information?

See **`FORECASTING_EXAMPLE.md`** for detailed examples and workflows.

## Troubleshooting

**API Key Issues:**
```r
# Verify key is set
Sys.getenv("OPENROUTER_API_KEY")

# Set manually
Sys.setenv(OPENROUTER_API_KEY = "your-key")
```

**Memory Issues with Long Simulations:**
- Reduce `N_PERIODS` in config.R
- Set `SAVE_FULL_TRANSCRIPTS <- FALSE` to reduce disk usage
- Process in batches using resume functionality

**Network Plot Errors:**
- Ensure `igraph` package is installed
- Some periods may have no interactions to plot

## License

MIT License - See LICENSE file

## Citation

If using this simulation in research:
```
Multi-Agent Wargame Simulation (2024)
LLM-based forecasting of geopolitical conflict outcomes
https://github.com/yourusername/llm-forecasting
```

## Contact

For questions or contributions, please open an issue on GitHub.
