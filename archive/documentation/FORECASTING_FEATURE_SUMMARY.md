# Forecasting Feature - Summary

## What Was Added

I've implemented a complete **human forecasting comparison system** that automatically generates prompts for human participants to make predictions that can be compared against the LLM aggregator's forecasts.

## New Files Created

### 1. `src/forecast_prompts.R` (320 lines)
Core forecasting functionality:
- `generate_forecast_prompt()` - Creates prompt for a specific period
- `generate_all_forecast_prompts()` - Generates all prompts for a simulation
- `compare_forecasts()` - Compares human vs LLM forecasts
- `generate_period_summary()` - Quick period summaries
- `create_forecasting_worksheet()` - Generates complete forecasting package

### 2. `FORECASTING_EXAMPLE.md`
Detailed examples showing:
- What prompts look like (Period 1 and Period 2 examples)
- Complete workflow from simulation to analysis
- Research applications
- Code examples for comparing forecasts
- Tips for forecasters and researchers

### 3. `FORECASTING_QUICKSTART.md`
Quick reference guide:
- 5-step workflow
- Analysis examples (Brier scores, visualizations)
- Research design options (blind vs unblind, sequential vs batch)
- Common questions and troubleshooting

## How It Works

### Automatic Generation
After running a simulation, the system creates:

1. **`forecasting_prompts.txt`** - Clean prompts with no answers
   - Period 1 gets initial scenario only
   - Period 2+ gets cumulative information (events, interactions, previous forecast)
   - Formatted for easy distribution to humans

2. **`forecasting_answer_key.txt`** - LLM aggregator's forecasts
   - Shows what the model predicted
   - Includes confidence, trend, and reasoning
   - For researcher reference

3. **`forecasting_template.csv`** - Data entry template
   - Pre-filled with period numbers and LLM forecasts
   - Easy columns for human predictions
   - Ready for analysis

### Information Structure

**Period 1:**
- Initial scenario description
- Starting conditions
- Agent composition
- Question: Probability by Day 7?

**Period 2+:**
- Previous LLM forecast (optional, can be removed for blind condition)
- Events from all previous periods
- Key discussion topics from all previous periods
- Current situation summary
- Question: Probability by Day X?

## Example Output

```
FORECASTING TASK - PERIOD 2

PREVIOUS MODEL FORECAST:
End of Period 1: 28.5%

EVENTS THAT HAVE OCCURRED:
Period 1 (Days 1-7):
  - Military Aid Package: Allied power provides advanced weapons
  - Battlefield Development: Frontline stabilizes with defensive advantages

KEY INTERACTIONS:
Period 1 Key Discussions:
  - Discuss economic costs (intra_faction_coordination)
  - Coordinate defensive strategy (intra_faction_coordination)
  - Backchannel ceasefire discussion (inter_faction_negotiation)

QUESTION:
What is the probability (0-100%) that the government will be removed
from power by Day 14?

Your forecast: ___%
Confidence: _____
```

## Usage

### Generate Materials
```r
source("src/analysis.R")
analyze_simulation("outputs")  # Automatically creates forecasting files
```

### Manual Generation
```r
source("src/forecast_prompts.R")
state <- load_simulation_state("outputs")

# Create all materials
create_forecasting_worksheet(state, "outputs")

# Or generate specific period
prompt <- generate_forecast_prompt(state, period = 3)
```

### Compare Forecasts
```r
# Collect human forecasts (0-1 scale)
human_probs <- c(0.25, 0.30, 0.35, 0.40, 0.42, 0.45, 0.48, 0.50, 0.52, 0.55)

# Compare
comparison <- compare_forecasts(state, human_probs)

# Metrics
mean(comparison$abs_difference)  # MAE
cor(comparison$llm_forecast, comparison$human_forecast)  # Correlation
```

## Integration Points

### Updated Files

1. **`src/analysis.R`**
   - Added automatic forecasting prompt generation
   - Calls `create_forecasting_worksheet()` at end of `analyze_simulation()`

2. **`example_usage.R`**
   - Added Examples 10-14 demonstrating forecasting features
   - Shows prompt generation, comparison, and visualization

3. **`README.md`**
   - Added section on "Human Forecasting Comparison"
   - Updated file structure to show new outputs
   - Added forecasting to overview features

## Research Applications

This feature enables studies of:

1. **Comparative Accuracy**: LLM vs human forecast accuracy
2. **Calibration**: Which forecaster is better calibrated?
3. **Information Processing**: How do forecasters update beliefs?
4. **Expertise Effects**: Do experts outperform LLMs?
5. **Aggregation**: Does averaging humans beat single LLM?
6. **Temporal Dynamics**: Who adapts better to new information?
7. **Transparency**: What reasoning do humans vs LLMs provide?

## Data Produced

### Structured Data
- Period-by-period forecasts (LLM and human)
- Confidence levels
- Forecast differences and absolute errors
- Easy CSV export for statistical analysis

### Qualitative Data
- Human reasoning/explanations
- LLM key factors explanations
- Interaction summaries showing what info was available

### Metrics
- Mean Absolute Error (MAE)
- Correlation
- Brier scores (if outcome known)
- Calibration plots
- Temporal accuracy trends

## Example Research Workflow

1. **Run Simulation**: `start_simulation()` → 10 periods
2. **Generate Prompts**: `analyze_simulation()` → creates files
3. **Recruit Forecasters**: Give them `forecasting_prompts.txt`
4. **Collect Responses**: Via CSV template or manual entry
5. **Compare**: `compare_forecasts()` → analysis
6. **Publish**: "LLM vs Expert Forecasts in Simulated Conflicts"

## Customization Options

### Modify Prompt Format
Edit `generate_forecast_prompt()` in `src/forecast_prompts.R`

### Blind Conditions
Remove "PREVIOUS MODEL FORECAST" section for blind studies

### Additional Fields
Add more questions (e.g., "What probability do you assign to negotiations?")

### Multiple Forecasters
Easy to collect and compare multiple humans:
```r
alice <- compare_forecasts(state, alice_probs)
bob <- compare_forecasts(state, bob_probs)
```

## Benefits

✅ **Automatic**: No manual prompt creation needed
✅ **Consistent**: All forecasters get same information
✅ **Cumulative**: Each period builds on previous info
✅ **Structured**: Easy to analyze and compare
✅ **Flexible**: Support for multiple research designs
✅ **Documented**: Examples and guides included

## Files Summary

**New Code:**
- `src/forecast_prompts.R` - 320 lines of forecasting logic

**New Documentation:**
- `FORECASTING_EXAMPLE.md` - Detailed examples
- `FORECASTING_QUICKSTART.md` - Quick reference
- `FORECASTING_FEATURE_SUMMARY.md` - This file

**Updated Code:**
- `src/analysis.R` - Added automatic generation
- `example_usage.R` - Added 5 new examples

**Updated Documentation:**
- `README.md` - Added forecasting section

## Total Addition
~600 lines of code + comprehensive documentation

Ready for research use! 🎯
