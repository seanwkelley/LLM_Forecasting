# Control Condition Guide - Experimental Design for Forecasting

**Last Updated:** January 2026

---

## Overview

This guide explains the control condition system for testing whether human and LLM forecasters can distinguish genuine predictive patterns from random noise.

### Research Question
**Can forecasters overfit their predictions to random data that superficially resembles real geopolitical dynamics?**

---

## The Problem

When observing any time series of events, there's a risk of:
1. **Overfitting** - Finding patterns that don't actually predict outcomes
2. **Narrative fallacy** - Creating causal stories from random sequences
3. **Confirmation bias** - Seeing what you expect to see

### Example
Imagine seeing: "Territory captured: 5% → 8% → 12% → Government collapses"

You might conclude: "Territorial loss causes government collapse"

But what if the sequence was actually random? What if we showed: "Territory captured: 12% → 5% → 8% → Government collapses" to another forecaster?

If both forecasters generate similar predictions, they're likely overfitting to noise rather than identifying true causal patterns.

---

## Control Condition Design

### Core Principle: Constrained Randomization

We break the information→outcome connection while maintaining **local plausibility**.

### Three-Layer Randomization

#### Layer 1: State Metrics Permutation
**What:** Shuffle metrics across periods with constraints

**Examples:**
```
TRUE CONDITION:
Period 1: Territory 5%, Crisis 9, Sanctions 50%
Period 2: Territory 8%, Crisis 8, Sanctions 55%
Period 3: Territory 12%, Crisis 9, Sanctions 60%

CONTROL CONDITION (permuted):
Period 1: Territory 8%, Crisis 8, Sanctions 60%
Period 2: Territory 12%, Crisis 9, Sanctions 50%
Period 3: Territory 5%, Crisis 9, Sanctions 55%
```

**Constraints:**
- Maximum period-to-period jump: 15% (territory), 3 levels (crisis), 20% (sanctions)
- Prevents nonsensical sequences like: 5% → 90% → 10%
- Maintains superficial plausibility

**Metrics randomized:**
- Territory controlled (0-100%)
- Crisis level (0-10)
- Sanctions level (0-100%)
- Military balance (-1 to 1)
- International support (0-100%)

#### Layer 2: Event Narrative Permutation + Flipping
**What:** Shuffle events across periods AND flip beneficiaries

**Example - Permutation:**
```
TRUE CONDITION:
Period 1: "Major sanctions package imposed on Novaris"
Period 2: "Tethys military gains ground near border"
Period 3: "International aid package arrives in Tethys"

CONTROL CONDITION:
Period 1: "International aid package arrives in Tethys"
Period 2: "Major sanctions package imposed on Novaris"
Period 3: "Tethys military gains ground near border"
```

**Example - Beneficiary Flipping (50% probability):**
```
TRUE: "Novaris captures key transportation hub, disrupting Tethys supply lines"
FLIPPED: "Tethys captures key transportation hub, disrupting Novaris supply lines"

TRUE: "Major power advances 15km on southern front"
FLIPPED: "Smaller power advances 15km on southern front"
```

**Text swaps:**
- Novaris ↔ Tethys
- Major power ↔ Smaller power
- Aggressor ↔ Defender
- Offensive ↔ Defensive

**Magnitude randomization:**
- Numbers in descriptions randomized ±30%
- "Advances 15km" → "Advances 19km" or "Advances 11km"
- Maintains plausibility while breaking exact patterns

#### Layer 3: Intermediate Probability Randomization
**What:** Randomize period-to-period probabilities while keeping **final outcome the same**

**Example:**
```
TRUE CONDITION:
Period 1: 25% collapse probability
Period 2: 30% collapse probability
Period 3: 35% collapse probability
OUTCOME: Government survived (< 50%)

CONTROL CONDITION:
Period 1: 40% collapse probability
Period 2: 28% collapse probability
Period 3: 35% collapse probability
OUTCOME: Government survived (< 50%)
```

**Why:** Forecasters should predict the same final outcome in both conditions IF they're not overfitting to intermediate noise.

---

## What Forecasters See

### TRUE CONDITION

**Information provided:**
1. **Events that occurred** (chronological, factual)
2. **Interaction topics** (what agents discussed)
3. **Public metrics:**
   - Territory controlled by aggressor (%)
   - Crisis level (0-10)
   - Sanctions level (%)
   - International support for smaller power (%)
4. **Previous period outcome** (BINARY: "Government remained in power" or "Government collapsed")
5. **Qualitative situation summary**

**Information NOT provided:**
- ❌ Previous LLM probability forecast (REMOVED as unrealistic)
- ❌ Military balance exact values
- ❌ GDP exact values
- ❌ Momentum scores
- ❌ Internal agent disagreements
- ❌ Deception/intelligence details

### CONTROL CONDITION

**Same format, but:**
- Metrics are permuted across periods
- Events are shuffled and some beneficiaries are flipped
- Event magnitudes are randomized ±30%
- Intermediate probabilities follow random walk
- Final outcome is preserved

**Marked clearly:**
```
[NOTE: This is a CONTROL CONDITION with randomized information for experimental purposes.]
```

---

## Expected Results

### If Forecasters Are Calibrated (Good)
- **TRUE condition:** Forecasts track LLM aggregator, capture genuine trends
- **CONTROL condition:** Forecasts cluster around base rate (35-40%), ignore noise

**Interpretation:** Forecasters distinguish signal from noise

### If Forecasters Overfit (Bad)
- **TRUE condition:** Forecasts match LLM aggregator
- **CONTROL condition:** Forecasts still show large variations, track random patterns

**Interpretation:** Forecasters are fitting narrative to any data, not identifying causal patterns

---

## Usage

### Generate Both Conditions
```r
source("src/forecast_prompts.R")

# Load simulation state
state <- readRDS("outputs/simulation_state.rds")

# Generate both TRUE and CONTROL prompts
files <- create_forecasting_worksheet(
  state,
  output_dir = "outputs",
  generate_control = TRUE
)

# Outputs:
# - outputs/forecasting_prompts_true.txt
# - outputs/forecasting_prompts_control.txt
# - outputs/forecasting_answer_key.txt
# - outputs/forecasting_template.csv
```

### Manual Control Generation
```r
source("src/control_condition.R")

# Load true state
true_state <- readRDS("outputs/simulation_state.rds")

# Generate control condition
control_state <- generate_control_condition(true_state)

# Compare
summary <- summarize_control_changes(true_state, control_state)
cat(summary)
```

---

## Analysis

### Compare Forecaster Performance
```r
source("src/forecast_prompts.R")

# Load responses
true_forecasts <- c(0.25, 0.30, 0.35, ...)  # Human forecasts on true condition
control_forecasts <- c(0.38, 0.42, 0.37, ...)  # Same human on control condition

llm_forecasts <- sapply(1:n_periods, function(p) {
  state$assessments_history[[p]]$probability
})

# Metrics
mae_true <- mean(abs(true_forecasts - llm_forecasts))
mae_control <- mean(abs(control_forecasts - llm_forecasts))

variance_true <- var(true_forecasts)
variance_control <- var(control_forecasts)

# Good performance:
# - Low MAE on true condition
# - High MAE on control condition (forecasts ignore noise)
# - Low variance on control condition (cluster around base rate)
```

### Statistical Tests
```r
# Test if control forecasts are significantly different from true forecasts
t.test(true_forecasts, control_forecasts)

# Test if control forecasts cluster around base rate
base_rate <- 0.35
t.test(control_forecasts, mu = base_rate)

# Test if control variance is lower than true variance
var.test(true_forecasts, control_forecasts)
```

---

## Key Features

### Constrained Randomization Prevents Nonsense
**Bad (unconstrained):**
```
Period 1: Territory 5%, Crisis 2
Period 2: Territory 95%, Crisis 10  ← Impossible jump
Period 3: Territory 3%, Crisis 1    ← Nonsensical
```

**Good (constrained):**
```
Period 1: Territory 5%, Crisis 7
Period 2: Territory 12%, Crisis 9   ← Plausible
Period 3: Territory 8%, Crisis 8    ← Still coherent locally
```

### Beneficiary Flipping Breaks Narratives
```
TRUE: "Novaris suffers major defeat, loses 200 tanks"
CONTROL: "Tethys suffers major defeat, loses 200 tanks"
```

Same event structure, opposite implications. If forecasters generate same predictions regardless, they're not using beneficiary information properly.

### Magnitude Randomization Prevents Exact Matching
```
TRUE: "GDP drops by 15 billion"
CONTROL: "GDP drops by 19 billion" (randomized ±30%)
```

Prevents forecasters from memorizing exact numbers across conditions.

---

## Experimental Design

### Between-Subjects Design
- **Group A:** Sees only TRUE condition → Make forecasts
- **Group B:** Sees only CONTROL condition → Make forecasts
- **Compare:** Group A should track LLM, Group B should cluster around base rate

### Within-Subjects Design
- **Each forecaster:** Makes predictions on BOTH conditions (randomized order)
- **Expectation:** Same person should show higher variance on TRUE vs CONTROL
- **Advantage:** Controls for individual skill differences

### Recommended Design
**Hybrid:**
1. Show TRUE condition first (Period 1-5)
2. Show CONTROL condition second (Period 6-10)
3. Don't reveal which is which
4. Measure if forecaster behavior changes when patterns become random

---

## Validation

### Checklist for Control Condition
- [ ] Metrics permuted across periods with max jump constraints
- [ ] Events shuffled across periods
- [ ] 50% of events have beneficiaries flipped
- [ ] Event magnitudes randomized ±30%
- [ ] Intermediate probabilities follow random walk
- [ ] Final outcome preserved (same government survival/collapse)
- [ ] No metric jumps exceed constraints (15% territory, 3 crisis levels, etc.)
- [ ] Narrative swaps are grammatically correct (Novaris → Tethys)

---

## Limitations

### What This Tests
✅ Ability to distinguish signal from noise
✅ Sensitivity to beneficiary information
✅ Overfitting to superficial patterns
✅ Base rate usage when information is unreliable

### What This Doesn't Test
❌ Absolute forecasting accuracy
❌ Domain knowledge
❌ Complex causal reasoning (both conditions are altered)
❌ Long-term trajectory forecasting (only 10 periods)

---

## Future Extensions

### Multiple Control Types
1. **Reversed control:** Same metrics, everything favors opposite outcome
2. **Flat control:** All metrics stay constant, events are random
3. **Extreme control:** Metrics at extremes (0% or 100%), test anchoring

### Adaptive Control
- Generate controls that match TRUE condition's statistical properties
- Control for autocorrelation, trends, variance
- More sophisticated test of pattern recognition

### Mixed Information
- Some periods TRUE, some CONTROL (randomly)
- Test if forecasters can detect when information becomes unreliable
- Measures adaptability and uncertainty calibration

---

## Implementation Details

### Files
- **`src/control_condition.R`** - Core randomization functions
- **`src/forecast_prompts.R`** - Prompt generation (modified to support control)

### Key Functions
- `generate_control_condition(state)` - Main entry point
- `permute_state_metrics(state, n_periods)` - Layer 1
- `permute_event_narratives(state, n_periods)` - Layer 2
- `randomize_intermediate_probabilities(state, n_periods)` - Layer 3
- `flip_event_beneficiary(event)` - Swap aggressor/defender
- `constrained_shuffle(values, max_jump)` - Prevents nonsensical jumps

---

## Example Output

### TRUE Condition Prompt (Period 2)
```
FORECASTING TASK - PERIOD 2

SCENARIO UPDATE:
Day 7 of simulated conflict between major power and smaller power.

PREVIOUS PERIOD OUTCOME:
End of Period 1: Government REMAINED IN POWER

PUBLICLY OBSERVABLE METRICS (End of Period 1):
- Territory controlled by aggressor: 8.3%
- Crisis level: 9/10
- Sanctions level: 52.0%
- International support for smaller power: 68.0%

EVENTS THAT HAVE OCCURRED:
Period 1 (Days 1-7):
  - Major Offensive: Combined-arms assault on three fronts, 200km advance
  - Economic Pressure: Emergency sanctions package targeting major power banks

KEY INTERACTIONS AND DISCUSSIONS:
Period 1 Key Discussions:
  - Internal Strategy (Coalition)
  - Sanctions Response (Negotiation)

QUESTION:
What is the probability (0-100%) that the smaller power's government will
be removed from power by the end of Period 2 (Day 14)?

Your forecast: ___%
```

### CONTROL Condition Prompt (Period 2)
```
[NOTE: This is a CONTROL CONDITION with randomized information for experimental purposes.]

FORECASTING TASK - PERIOD 2

SCENARIO UPDATE:
Day 7 of simulated conflict between major power and smaller power.

PREVIOUS PERIOD OUTCOME:
End of Period 1: Government REMAINED IN POWER

PUBLICLY OBSERVABLE METRICS (End of Period 1):
- Territory controlled by aggressor: 5.7%  [← Permuted]
- Crisis level: 7/10  [← Permuted]
- Sanctions level: 61.0%  [← Permuted]
- International support for smaller power: 72.0%  [← Permuted]

EVENTS THAT HAVE OCCURRED:
Period 1 (Days 1-7):
  - Economic Pressure: Emergency sanctions package targeting smaller power banks  [← Flipped!]
  - Major Offensive: Combined-arms assault on three fronts, 237km advance  [← Randomized magnitude]

KEY INTERACTIONS AND DISCUSSIONS:
Period 1 Key Discussions:
  - Sanctions Response (Negotiation)  [← Permuted]
  - Internal Strategy (Coalition)  [← Permuted]

QUESTION:
What is the probability (0-100%) that the smaller power's government will
be removed from power by the end of Period 2 (Day 14)?

Your forecast: ___%
```

---

**For detailed implementation, see `src/control_condition.R`**
**For usage examples, see `src/forecast_prompts.R`**
