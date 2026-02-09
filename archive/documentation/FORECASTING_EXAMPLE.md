# Human Forecasting Example

This document shows what the forecasting prompts look like that human participants will receive.

## How It Works

After running a simulation, the system automatically generates:
1. **Forecasting prompts** - Given to human forecasters (no answers)
2. **Answer key** - Shows LLM aggregator's forecasts for comparison
3. **CSV template** - For easy data entry of human forecasts

## Example: Period 1 Prompt

```
FORECASTING TASK - PERIOD 1

You are participating in a geopolitical forecasting exercise. Based on the
information below, please estimate the probability (0-100%) that the smaller
power's government will collapse or be removed from power by the end of
Period 1 (Day 7).

INITIAL SCENARIO:
A major power has initiated territorial operations against a smaller power.
The smaller power is mounting defensive resistance. International reactions
are developing.

INITIAL CONDITIONS:
- Military Balance: Slight advantage to defender (home territory advantage)
- International Sanctions: Initial sanctions package in place against major power
- External Support: Moderate international support for smaller power
- Day: 0 (start of conflict)

AGENT COMPOSITION:
Major Power: 4 decision-makers (military, government, economic, intelligence)
Smaller Power: 4 decision-makers (president, military, diplomat, opposition)
External Actors: 3 representatives (allied power, neutral power, international org)

QUESTION:
What is the probability (0-100%) that the smaller power's government will be
removed from power by Day 7?

Your forecast: ___%

Confidence (Low/Medium/High): _______

Brief reasoning:
```

## Example: Period 2 Prompt

```
FORECASTING TASK - PERIOD 2

You are participating in a geopolitical forecasting exercise. Based on the
information below, please estimate the probability (0-100%) that the smaller
power's government will collapse or be removed from power by the end of
Period 2 (Day 14).

SCENARIO UPDATE:
Day 7 of simulated conflict between major power and smaller power.

PREVIOUS MODEL FORECAST:
End of Period 1: 28.5%

EVENTS THAT HAVE OCCURRED:

Period 1 (Days 1-7):
  - Military Aid Package: Allied power provides advanced weapons to smaller power
  - Battlefield Development: Simulated frontline stabilizes with defensive advantages

KEY INTERACTIONS AND DISCUSSIONS:

Period 1 Key Discussions:
  - Discuss economic costs of the operation and resource allocation (intra_faction_coordination)
  - Coordinate defensive strategy and resource prioritization (intra_faction_coordination)
  - Coordinate international response to the conflict (intra_faction_coordination)
  - Backchannel discussion about potential ceasefire conditions (inter_faction_negotiation)
  - Discussion of military aid and support levels (external_engagement)

CURRENT SITUATION (Start of Period 2):
Day 7: Conflict continues. Estimated probability of government collapse: 28.5%.
Military aid strengthening defensive position, international sanctions beginning
to impact major power economy.

QUESTION:
Based on all information above, what is the probability (0-100%) that the
smaller power's government will be removed from power by the end of Period 2 (Day 14)?

Your forecast: ___%

Confidence (Low/Medium/High): _______

Brief reasoning (2-3 sentences):
```

## Using the Forecasting System

### Step 1: Run Simulation
```r
source("src/simulation.R")
state <- start_simulation()
```

### Step 2: Generate Forecasting Materials
```r
source("src/analysis.R")
analyze_simulation("outputs")
```

This creates three files in `outputs/`:
- `forecasting_prompts.txt` - Give to human forecasters
- `forecasting_answer_key.txt` - LLM aggregator's forecasts
- `forecasting_template.csv` - For entering human forecasts

### Step 3: Collect Human Forecasts

Participants fill out the prompts or use the CSV template:

**forecasting_template.csv:**
```csv
period,day,forecaster_name,probability_forecast,confidence,llm_forecast
1,7,"",NA,"",28.5
2,14,"",NA,"",31.2
3,21,"",NA,"",35.8
...
```

Becomes:
```csv
period,day,forecaster_name,probability_forecast,confidence,llm_forecast
1,7,"Alice",25,Medium,28.5
2,14,"Alice",30,Medium,31.2
3,21,"Alice",40,High,35.8
...
```

### Step 4: Compare Forecasts

```r
source("src/forecast_prompts.R")

# Load simulation
state <- load_simulation_state("outputs")

# Enter human forecasts (0-1 scale)
alice_forecasts <- c(0.25, 0.30, 0.40, 0.38, 0.42, 0.45, 0.50, 0.48, 0.52, 0.55)

# Compare
comparison <- compare_forecasts(state, alice_forecasts)
print(comparison)
```

Output:
```
  period day llm_forecast human_forecast difference abs_difference
1      1   7        0.285          0.250     -0.035          0.035
2      2  14        0.312          0.300     -0.012          0.012
3      3  21        0.358          0.400      0.042          0.042
...
```

### Step 5: Analyze Forecast Accuracy

```r
# Mean absolute error
mean(comparison$abs_difference)

# Correlation
cor(comparison$llm_forecast, comparison$human_forecast)

# Plot comparison
library(ggplot2)
ggplot(comparison, aes(x = period)) +
  geom_line(aes(y = llm_forecast, color = "LLM")) +
  geom_line(aes(y = human_forecast, color = "Human")) +
  geom_point(aes(y = llm_forecast, color = "LLM")) +
  geom_point(aes(y = human_forecast, color = "Human")) +
  labs(title = "LLM vs Human Forecasts",
       x = "Period", y = "Probability", color = "Forecaster") +
  theme_minimal()
```

## Research Applications

This forecasting system enables:

1. **LLM vs Human Comparison**: Do LLM agents make better/worse forecasts than humans?

2. **Calibration Analysis**: Are LLM or human forecasts better calibrated?

3. **Information Processing**: How do forecasters update based on new information?

4. **Expertise Effects**: Do domain experts outperform LLMs? General forecasters?

5. **Aggregation**: Does averaging multiple human forecasts beat the LLM?

6. **Temporal Patterns**: Who adapts better to new information over time?

## Tips for Forecasters

**For Human Participants:**
- Read all information carefully before forecasting
- Consider how new events change the balance of power
- Note what the LLM's previous forecast was and why you agree/disagree
- Provide reasoning to help understand your forecasting process
- Update forecasts based on all cumulative information, not just the latest period

**For Researchers:**
- Give forecasters the same information the LLM aggregator sees
- Consider blind vs unblind conditions (showing previous LLM forecast or not)
- Collect confidence levels to assess calibration
- Ask for brief reasoning to understand decision processes
- Test with multiple scenarios/simulations for robust comparisons

## Data Generated

The system produces structured data for analysis:
- Period-by-period forecasts from both LLM and humans
- Confidence levels
- Forecast reasoning
- Event history
- Interaction summaries
- Easy comparison metrics (MAE, correlation, Brier scores)

Perfect for academic papers on LLM forecasting capabilities! 📊
