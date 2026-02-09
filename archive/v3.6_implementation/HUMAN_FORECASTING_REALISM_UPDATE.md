# Human Forecasting Realism Update (v3.6)

## Problem Statement

**Current system** shows humans too much internal information that would NOT be available to external observers:
- ❌ "Key Interactions and Discussions" (internal coordination meetings)
- ❌ Interaction topics like "Review military strategy", "Debate escalation options"
- ❌ Full visibility into what agents discussed
- ❌ Knowledge of internal decision-making processes

**Real-world reality:**
- Forecasters see publicly observable events (attacks, sanctions, diplomatic meetings)
- Forecasters see analyst commentary and estimates
- Forecasters do NOT see internal deliberations, classified plans, or decision processes

This creates an unrealistic advantage for human forecasters and makes comparison to real-world forecasting invalid.

---

## Solution: External Observer Perspective

**New approach:** Humans see only what they would see "in the news":

### What IS Visible (External Observer Can See):
- ✅ **Public actions**: Military strikes, sanctions, diplomatic visits, humanitarian aid
- ✅ **Observable outcomes**: Territory changes (from front-line reports), casualty reports
- ✅ **Public statements**: Announced policies, public meetings
- ✅ **External events**: Economic shocks, international reactions
- ✅ **Observable metrics**: Estimated territory control, sanctions levels, aid flows
- ✅ **Analyst commentary**: What independent experts say based on public info
- ✅ **Detection of failed covert ops**: Exposed operations become visible

### What is NOT Visible (Hidden from External Observer):
- ❌ **Internal coordination**: Cabinet meetings, war council debates
- ❌ **Agent positions**: Who recommended what internally
- ❌ **Classified intelligence**: Actual intelligence assessments
- ❌ **Deception attempts**: Disinformation unless exposed
- ❌ **Trust dynamics**: Internal relationships between officials
- ❌ **Successful covert ops**: Sabotage, assassinations that aren't detected
- ❌ **Private communications**: Diplomatic backchannels, secret negotiations

---

## Implementation

### File: `forecast_prompts_external_observer_v36.R`

**Key Functions:**

1. **`is_action_publicly_observable(action, success, detected)`**
   - Determines if action would be visible to external observers
   - Public actions (strikes, sanctions) → always visible
   - Covert actions (sabotage, cyber) → only visible if detected or failed

2. **`describe_action_externally(action_record)`**
   - Translates internal action to external observer description
   - "limited_strike executed" → "Novaris conducted precision military strikes"
   - Removes details about success/failure unless observable

3. **`generate_analyst_commentary(state, recent_actions)`**
   - Simulates independent analyst perspectives
   - Based only on observable patterns
   - Examples:
     - "Analysts note significant territorial control..."
     - "Defense experts observe stronger than predicted resistance..."
     - "Economic analysts note sanctions pressure..."

4. **`generate_forecast_prompt_external(state, period)`**
   - Main function creating realistic forecasting prompts
   - Only includes observable information
   - Explicitly reminds forecasters of information limits

---

## Example Comparison

### Current System (Unrealistic)

```
PERIOD 2 FORECAST

KEY INTERACTIONS AND DISCUSSIONS:
Period 1 Key Discussions:
  - Review military strategy and assess progress (intra_faction_coordination)
  - Debate whether to escalate or consolidate (intra_faction_coordination)
  - Negotiation over peace terms (inter_faction_negotiation)
  - Coordination on military aid (external_engagement)

PREVIOUS PERIOD ACTIONS:
- Major power chose: full_scale_attack
- Small power chose: military_buildup
- Meridian chose: financial_aid
```

**Problem:** Forecaster knows internal deliberation topics, all faction actions, and decision process

---

### New System (Realistic External Observer)

```
PERIOD 2 FORECAST

You are an EXTERNAL OBSERVER with access only to publicly available information.

REPORTED EVENTS AND ACTIONS:
Day 3: Novaris launched major military offensive - territorial gains reported
Day 5: Tethys increased military readiness and force levels
Day 6: Meridian Alliance provided financial aid package

OBSERVABLE METRICS (as of Day 7):
- Estimated territory under Novaris control: ~8% (based on front-line reports)
- Conflict intensity assessment: Very High (based on reported military activity)
- International sanctions: Significant
- External aid to Tethys: Substantial

INDEPENDENT ANALYST COMMENTARY:
Military analysts note that while the aggressor has made gains, the defender's
resistance remains stronger than initially predicted.

Diplomatic observers note negotiation attempts, though skepticism remains about
willingness to make necessary concessions.

OTHER FORECASTER ASSESSMENT:
One forecasting model estimated 32% probability of government collapse by end of Period 1.

REMINDER - Information Limits:
You do NOT have access to:
- Internal deliberations within either government
- Classified intelligence or military plans
- Private diplomatic communications
- Undisclosed covert operations
```

**Improvement:** Only observable facts, analyst commentary, no internal knowledge

---

## Integration

### Option A: Replace Current System

```bash
# Backup current
cp src/forecast_prompts.R src/forecast_prompts_old.R

# Replace with new version
cp src/forecast_prompts_external_observer_v36.R src/forecast_prompts.R

# Update function calls
# Change: generate_forecast_prompt() → generate_forecast_prompt_external()
```

### Option B: Run Both (Compare)

Keep both versions and generate two sets of prompts:

```r
# Generate both versions
prompts_full_info <- generate_all_forecast_prompts(state,
  output_file = "outputs/human_forecasts_full_info.txt")

prompts_external <- generate_all_forecast_prompts_external(state,
  output_file = "outputs/human_forecasts_external_observer.txt")

# Research question: Do forecasters with full info do better?
```

---

## Research Value

### New Research Questions Enabled:

1. **Information advantage:** Do LLM aggregators (with full info) outperform humans (external observer)?

2. **Realism:** Does external observer condition match real-world forecasting accuracy?

3. **Information value:** How much does internal deliberation knowledge improve forecasts?

4. **Analyst commentary:** Do independent analyst comments help or introduce bias?

5. **Comparison validity:** Can we now compare simulation forecasts to real-world tournament forecasts (which also use public info)?

---

## Usage

### Generate External Observer Prompts

```r
# Load the new system
source("src/forecast_prompts_external_observer_v36.R")

# Load completed simulation
state <- readRDS("outputs/simulation_state.rds")

# Generate prompts
prompts <- generate_all_forecast_prompts_external(
  state,
  output_file = "outputs/human_forecasting_prompts_external.txt",
  control_condition = FALSE
)

# Also generate control condition
prompts_control <- generate_all_forecast_prompts_external(
  state,
  output_file = "outputs/human_forecasting_prompts_control.txt",
  control_condition = TRUE
)
```

### Human Forecaster Instructions

Provide to human participants:

```
INSTRUCTIONS FOR FORECASTERS

You will receive a series of forecasting prompts representing periods in a
geopolitical conflict simulation.

IMPORTANT: You are an EXTERNAL OBSERVER. You have access only to:
- Publicly reported actions and events
- Observable metrics (territory, sanctions, aid)
- Independent analyst commentary

You do NOT have access to:
- Internal government deliberations or decisions
- Classified intelligence assessments
- Private diplomatic communications
- Covert operations (unless detected/exposed)

This mirrors real-world forecasting conditions where you would rely on news media,
open-source analysis, and publicly available data.

Please provide:
1. Probability estimate (0-100%)
2. Confidence level (Low/Medium/High)
3. Brief reasoning (2-3 sentences focusing on observable factors)
```

---

## Validation

### Check External Observer Filtering

```r
# Test action observability
test_actions <- list(
  list(action = "military_buildup", success = TRUE, detected = FALSE),
  list(action = "sabotage", success = TRUE, detected = FALSE),  # Should be hidden
  list(action = "sabotage", success = FALSE, detected = TRUE),  # Should be visible
  list(action = "peace_talks", success = FALSE, detected = FALSE)  # Always visible
)

for (action in test_actions) {
  obs <- is_action_publicly_observable(action$action, action$success, action$detected)
  desc <- describe_action_externally(action)
  cat(sprintf("%s (success=%s, detected=%s): Observable=%s, Desc='%s'\n",
              action$action, action$success, action$detected, obs,
              if(is.null(desc)) "HIDDEN" else desc))
}
```

**Expected output:**
```
military_buildup: Observable=TRUE, Desc='Novaris increased military readiness'
sabotage (success, not detected): Observable=FALSE, Desc='HIDDEN'
sabotage (failed, detected): Observable=TRUE, Desc='Novaris accused of sabotage'
peace_talks: Observable=TRUE, Desc='Novaris initiated peace negotiations - talks stalled'
```

---

## Comparison to Current System

| Aspect | Current System | New External Observer |
|--------|---------------|----------------------|
| **Internal coordination topics** | ✅ Visible | ❌ Hidden |
| **Agent recommendations** | ✅ Visible | ❌ Hidden |
| **Public actions** | ✅ Visible | ✅ Visible |
| **Covert actions (successful)** | ✅ Visible | ❌ Hidden |
| **Covert actions (detected)** | ✅ Visible | ✅ Visible |
| **Observable metrics** | ✅ Visible | ✅ Visible (estimated) |
| **Analyst commentary** | ❌ Not included | ✅ Included |
| **LLM forecast from previous period** | ❌ Not included | ✅ Included (as data point) |
| **Information limits reminder** | ❌ Not included | ✅ Explicit |

---

## Expected Impact

### Forecast Accuracy Changes:

**Hypothesis:** Human forecasts will be:
- **Less accurate** (less information available)
- **More realistic** (matches real-world forecasting conditions)
- **More variable** (different analysts interpret public info differently)

**LLM advantage:**
- LLM aggregator has full internal knowledge
- Can assess internal dynamics, agent positions, deception
- Should outperform external observer humans

**Research value:**
- Can now compare to real-world forecasting tournaments (similar info constraints)
- Can measure value of internal information access
- More ecologically valid forecasting task

---

## Next Steps

1. **Decide:** Replace current system or run both in parallel?

2. **Test:** Generate prompts from existing simulation to verify format

3. **Validate:** Check that covert operations are properly hidden/revealed

4. **Document:** Update human forecaster instructions

5. **Analyze:** Compare forecast accuracy with full info vs external observer

---

## Rollback

If issues arise:

```bash
# Restore original
mv src/forecast_prompts_old.R src/forecast_prompts.R

# Or just use old function name
generate_all_forecast_prompts(state, ...)  # Old system
```

---

**Summary:**

- ✅ Created realistic external observer perspective
- ✅ Hides internal deliberations and covert ops
- ✅ Includes analyst commentary
- ✅ Explicit information limits
- ✅ More ecologically valid
- ✅ Enables comparison to real-world forecasting

**File:** `forecast_prompts_external_observer_v36.R`

**Ready to deploy!**
