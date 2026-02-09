# Forecasting Feature - Quick Reference

## What This Does

After running a simulation, the system automatically generates **forecasting prompts** that you can give to human participants. This lets you compare LLM forecasts vs human predictions based on the same information.

## Quick Workflow

### 1. Run Simulation
```r
source("src/simulation.R")
state <- start_simulation()
```

### 2. Generate Forecasting Materials
```r
source("src/analysis.R")
analyze_simulation("outputs")
```

**This creates 3 files:**
- `forecasting_prompts.txt` - Give to humans (no answers shown)
- `forecasting_answer_key.txt` - LLM forecasts for your reference
- `forecasting_template.csv` - Easy data entry template

### 3. Distribute to Forecasters

Send `forecasting_prompts.txt` to your human participants. Each period includes:
- Background information (events, interactions from previous periods)
- Current scenario state
- A question asking for probability forecast
- Space for confidence level and reasoning

### 4. Collect Responses

Option A: **Use the CSV template**
```csv
period,day,forecaster_name,probability_forecast,confidence,llm_forecast
1,7,Alice,25,Medium,28.5
2,14,Alice,30,High,31.2
```

Option B: **Enter manually in R**
```r
alice_forecasts <- c(0.25, 0.30, 0.35, 0.40, 0.42, 0.45, 0.48, 0.50, 0.52, 0.55)
```

### 5. Compare Results

```r
source("src/forecast_prompts.R")
state <- load_simulation_state("outputs")

# Compare forecasts
comparison <- compare_forecasts(state, alice_forecasts,
                                human_names = rep("Alice", 10))
print(comparison)

# Metrics
mean(comparison$abs_difference)  # Mean absolute error
cor(comparison$llm_forecast, comparison$human_forecast)  # Correlation
```

## What Forecasters See

### Period 1 (Initial)
- Initial scenario description
- Starting conditions
- Agent composition
- Question: Probability of collapse by Day 7?

### Period 2+ (Updates)
- Previous LLM forecast
- Events that occurred in previous periods
- Key interactions and discussions
- Current situation summary
- Question: Probability of collapse by Day X?

## Key Features

✅ **Progressive Information**: Each period builds on previous information
✅ **LLM Forecast Included**: Option to show/hide previous LLM prediction
✅ **Structured Format**: Easy to parse and analyze
✅ **Reasoning Capture**: Prompts ask for brief explanations
✅ **Multiple Forecasters**: Easy to collect and compare multiple humans

## Analysis Examples

### Compare Multiple Forecasters
```r
alice <- c(0.25, 0.30, 0.35, 0.40, 0.42, 0.45, 0.48, 0.50, 0.52, 0.55)
bob <- c(0.30, 0.35, 0.40, 0.45, 0.48, 0.50, 0.52, 0.54, 0.56, 0.58)

comp_alice <- compare_forecasts(state, alice)
comp_bob <- compare_forecasts(state, bob)

# Who's more accurate?
mean(comp_alice$abs_difference)
mean(comp_bob$abs_difference)
```

### Visualize Comparison
```r
library(ggplot2)

comparison$forecaster <- "Human"
llm_data <- data.frame(
  period = comparison$period,
  probability = comparison$llm_forecast,
  forecaster = "LLM"
)

combined <- rbind(
  data.frame(period = comparison$period,
             probability = comparison$human_forecast,
             forecaster = "Human"),
  llm_data
)

ggplot(combined, aes(x = period, y = probability, color = forecaster)) +
  geom_line() +
  geom_point() +
  labs(title = "LLM vs Human Forecasts",
       x = "Period", y = "Probability of Collapse") +
  theme_minimal()
```

### Calculate Brier Score
```r
# Assume actual outcome is known (e.g., government did collapse at period 8)
actual_collapse_period <- 8

# Calculate Brier scores
calc_brier <- function(forecasts, actual_period, forecast_periods) {
  outcome <- ifelse(forecast_periods >= actual_collapse_period, 1, 0)
  mean((forecasts - outcome)^2)
}

human_brier <- calc_brier(comparison$human_forecast,
                          actual_collapse_period,
                          comparison$period)
llm_brier <- calc_brier(comparison$llm_forecast,
                       actual_collapse_period,
                       comparison$period)

cat(sprintf("Human Brier Score: %.3f\n", human_brier))
cat(sprintf("LLM Brier Score: %.3f\n", llm_brier))
```

## Research Design Options

### Blind vs Unblind
**Blind**: Remove the "PREVIOUS MODEL FORECAST" section from prompts
**Unblind**: Show LLM's previous forecast (default)

To create blind prompts, edit the prompt after generation:
```r
prompts <- generate_all_forecast_prompts(state)
# Manually remove PREVIOUS MODEL FORECAST sections
```

### Sequential vs Batch
**Sequential**: Give forecasters one period at a time
**Batch**: Give all periods at once (faster but less realistic)

### Expert vs Novice
Recruit both domain experts and general forecasters to test expertise effects.

### Aggregation Studies
Collect multiple forecasts per period and test aggregation methods:
- Simple average
- Median
- Weighted by confidence
- Extremized average

## Tips for Researchers

1. **Pilot Test**: Run a short simulation (3 periods) to test workflow
2. **Clear Instructions**: Provide forecasters with definitions and examples
3. **Time Limits**: Consider whether to impose time limits on forecasts
4. **Incentives**: Consider accuracy-based incentives for human forecasters
5. **Reasoning**: Always collect brief reasoning - very valuable for analysis
6. **Multiple Scenarios**: Run several simulations for robust comparisons

## Common Questions

**Q: How many forecasters do I need?**
A: Minimum 10-20 for statistical power. More if testing expertise effects.

**Q: Should I show the LLM's previous forecast?**
A: Depends on research question. Both conditions are interesting!

**Q: How long does forecasting take per person?**
A: ~10-15 minutes for 10 periods (1-2 min per forecast).

**Q: Can I modify the prompts?**
A: Yes! Edit `src/forecast_prompts.R` to customize format.

**Q: How do I handle missing periods?**
A: Use `NA` for missing forecasts in the comparison function.

## Output Files Location

All forecasting files are saved to `outputs/`:
```
outputs/
├── forecasting_prompts.txt       # Give to humans
├── forecasting_answer_key.txt    # Your reference
└── forecasting_template.csv      # Data entry
```

## Next Steps

1. Review `FORECASTING_EXAMPLE.md` for detailed examples
2. Run a test simulation with 2-3 periods
3. Practice using the forecasting functions
4. Design your research protocol
5. Recruit forecasters!

Happy forecasting! 📊
