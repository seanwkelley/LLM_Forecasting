# V3.6 Part 2: Cross-Expertise + Realistic Human Forecasting

## Delivery Summary

Two critical improvements to enhance simulation realism and action diversity:

---

## **Part 1: Cross-Expertise Recommendations**

### Problem
Agents were implicitly constrained to their role stereotypes:
- Military chiefs → 90% military actions
- Diplomats → 85% diplomatic actions
- Economic advisors rarely recommend strikes even when economically optimal

**Real-world reality:** Experts DO recommend outside their domain when strategically sound.

### Solution
Modified role guidance from **PRESCRIPTIVE** → **DESCRIPTIVE**

- Emphasize expertise, but allow any recommendation
- Military expert CAN recommend peace_talks (when force exhausted)
- Economic expert CAN recommend strikes (when one blow cheaper than attrition)
- Diplomat CAN recommend covert ops (when it creates negotiation leverage)

### Expected Impact
- **+20-30% action diversity** through cross-expertise recommendations
- More realistic deliberation (matches real cabinet discussions)
- Reduces role stereotyping

### Files Delivered
- 📄 `CROSS_EXPERTISE_PROMPT_UPDATES.md` - Complete implementation guide with code

---

## **Part 2: Realistic Human Forecasting (External Observer)**

### Problem
Current system shows humans **too much** internal information:
- ❌ "Key Interactions and Discussions" (internal coordination)
- ❌ Cabinet meeting topics ("Review military strategy", "Debate escalation")
- ❌ Full visibility into agent positions and decision processes

**This is unrealistic** - real forecasters only see what's "in the news"

### Solution: External Observer Perspective

**Humans now see only:**
- ✅ Public actions (strikes, sanctions, diplomatic visits)
- ✅ Observable outcomes (territory changes from front-line reports)
- ✅ External events (economic shocks, international reactions)
- ✅ Observable metrics (estimated territory, sanctions, aid)
- ✅ Analyst commentary (what independent experts say)
- ✅ Detected covert ops (exposed operations become visible)

**Humans do NOT see:**
- ❌ Internal coordination meetings
- ❌ Agent debates and positions
- ❌ Classified intelligence assessments
- ❌ Successful covert operations
- ❌ Private diplomatic communications
- ❌ Decision-making processes

### Key Features

**1. Action Filtering**
```r
is_action_publicly_observable(action, success, detected)
```
- Public actions (military strikes, sanctions) → always visible
- Covert actions (sabotage, cyber) → only if detected or failed
- Gradated visibility based on realism

**2. External Descriptions**
```r
describe_action_externally(action_record)
```
- "limited_strike executed" → "Novaris conducted precision military strikes"
- Removes internal details, shows only observable effects

**3. Analyst Commentary**
```r
generate_analyst_commentary(state, actions)
```
- Simulates independent expert analysis
- Based only on publicly observable patterns
- Examples:
  - "Analysts assess significant territorial control..."
  - "Defense experts observe stronger resistance than predicted..."

**4. Information Limits Reminder**
- Explicit list of what forecasters do NOT have access to
- Matches real-world forecasting conditions

### Research Value

**New research questions enabled:**

1. **Information advantage:** Do LLM aggregators (full info) outperform humans (external observer)?

2. **Realism:** Does external observer condition match real-world forecasting tournaments?

3. **Information value:** How much does internal knowledge improve forecasts?

4. **Comparison validity:** Can now compare to real-world forecasts (same info constraints)

### Files Delivered
- 📄 `forecast_prompts_external_observer_v36.R` - Complete new implementation
- 📄 `HUMAN_FORECASTING_REALISM_UPDATE.md` - Detailed guide and examples

---

## Implementation Summary

### Cross-Expertise Recommendations

**Where:** `src/interaction_engine.R`, Round 1 prompt

**Changes:**
1. Add `get_role_expertise_description(role)` function
2. Modify Round 1 prompt to emphasize expertise without constraining choice
3. Add explicit examples of cross-expertise recommendations

**Effort:** ~30 minutes

**Expected result:** +20-30% action diversity

---

### External Observer Forecasting

**Where:** New file or replace `src/forecast_prompts.R`

**Options:**

**Option A (Recommended): Run Both Systems**
```r
# Keep current for comparison
source("src/forecast_prompts.R")
prompts_full <- generate_all_forecast_prompts(state,
  "outputs/forecasts_full_info.txt")

# Add new external observer
source("src/forecast_prompts_external_observer_v36.R")
prompts_external <- generate_all_forecast_prompts_external(state,
  "outputs/forecasts_external_observer.txt")

# Research question: Does full info help?
```

**Option B: Replace Current System**
```bash
cp src/forecast_prompts_external_observer_v36.R src/forecast_prompts.R
```

**Effort:** 10 minutes (if replacing), 20 minutes (if running both)

**Expected result:** More realistic, ecologically valid forecasting task

---

## Example: Before vs After

### Human Forecast - BEFORE (Unrealistic)

```
PERIOD 2 FORECAST

KEY INTERACTIONS:
- Review military strategy and assess progress
- Debate whether to escalate or consolidate
- Negotiation over peace terms
- Coordination on military aid

ACTIONS TAKEN:
- Major power: full_scale_attack (SUCCESS)
- Small power: military_buildup (SUCCESS)
- Meridian: financial_aid (SUCCESS)

Based on this information, forecast probability...
```

**Problem:** Forecaster knows internal deliberations, all faction choices, success/failure

---

### Human Forecast - AFTER (Realistic External Observer)

```
PERIOD 2 FORECAST

You are an EXTERNAL OBSERVER (similar to news consumer).

REPORTED EVENTS:
Day 3: Novaris launched major military offensive - territorial gains reported
Day 5: Tethys increased military readiness and force levels
Day 6: Meridian Alliance provided financial aid package

OBSERVABLE METRICS (Day 7):
- Estimated territory under Novaris control: ~8%
- Conflict intensity: Very High
- International sanctions: Significant
- External aid to Tethys: Substantial

ANALYST COMMENTARY:
"Military analysts note that while the aggressor has made gains, defender
resistance remains stronger than initially predicted."

"Diplomatic observers note negotiation attempts, though skepticism remains
about willingness to make necessary concessions."

INFORMATION LIMITS:
You do NOT have access to internal deliberations, classified intelligence,
or private communications.

Based on publicly observable information, forecast probability...
```

**Improvement:** Only observable facts, realistic constraints, analyst perspectives

---

## Testing & Validation

### Test Cross-Expertise

After implementation:

```r
# Run simulation
Rscript run_simulation_with_actions.R

# Check for cross-expertise
coordination <- read.csv("outputs/all_coordination.csv")

cross_expertise <- coordination %>%
  filter(
    (sender_role == "military" & grepl("peace|diplomatic", content)) |
    (sender_role == "diplomatic" & grepl("strike|attack", content)) |
    (sender_role == "economic" & grepl("covert|sabotage", content))
  )

cat("Cross-expertise recommendations:", nrow(cross_expertise), "\n")
cat("Percentage:", nrow(cross_expertise)/nrow(coordination)*100, "%\n")
```

**Success criteria:** 15-20% of recommendations are cross-expertise

---

### Test External Observer

```r
# Generate both versions
source("src/forecast_prompts.R")
source("src/forecast_prompts_external_observer_v36.R")

state <- readRDS("outputs/simulation_state.rds")

prompts_full <- generate_all_forecast_prompts(state)
prompts_external <- generate_all_forecast_prompts_external(state)

# Compare length (external should be shorter - less info)
cat("Full info prompt length:", nchar(prompts_full[[2]]), "\n")
cat("External observer length:", nchar(prompts_external[[2]]), "\n")

# Check for internal info leakage
if (grepl("internal|coordination|deliberation", prompts_external[[2]])) {
  warning("Internal information detected in external observer prompt!")
}
```

**Success criteria:**
- External observer prompts are 30-50% shorter
- No "internal", "coordination", or "deliberation" keywords
- Contains "analyst commentary" and "information limits"

---

## Research Applications

### Experiment Design

**Treatment 1: Full Information**
- Show humans everything (current system)
- Include internal deliberations, all actions

**Treatment 2: External Observer**
- Show only publicly observable info (new system)
- Matches real-world forecasting

**Treatment 3: LLM Aggregator**
- Has full internal knowledge
- Current aggregator system

**Research Questions:**
1. Does full information improve forecast accuracy?
2. Can external observers still make accurate predictions?
3. How much advantage does internal knowledge provide?
4. Do LLMs outperform humans with external observer constraint?

---

## Summary

### Files Delivered

**Cross-Expertise:**
- 📄 `CROSS_EXPERTISE_PROMPT_UPDATES.md` (implementation guide)

**External Observer:**
- 📄 `forecast_prompts_external_observer_v36.R` (complete code)
- 📄 `HUMAN_FORECASTING_REALISM_UPDATE.md` (guide + rationale)

**This summary:**
- 📄 `V36_PART2_DELIVERY_SUMMARY.md`

### Expected Improvements

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Action diversity** | 15-20 unique | 25-35 unique | +60% |
| **Cross-expertise recommendations** | <5% | 15-20% | +300% |
| **Human forecast realism** | Unrealistic (full info) | Realistic (external observer) | Ecological validity ✓ |
| **Research comparability** | Can't compare to real-world | Can compare to tournaments | Validity ✓ |

---

## Quick Start

### 1. Enable Cross-Expertise (30 min)
1. Open `CROSS_EXPERTISE_PROMPT_UPDATES.md`
2. Add `get_role_expertise_description()` function
3. Update Round 1 prompt as specified
4. Test simulation

### 2. Enable External Observer (20 min)
1. Copy `forecast_prompts_external_observer_v36.R` to `src/`
2. Source it in your simulation script
3. Generate external observer prompts alongside current prompts
4. Compare outputs

### 3. Validate Both (15 min)
1. Check for cross-expertise recommendations in coordination logs
2. Verify external observer prompts don't leak internal info
3. Run test suite from guides

---

**Total implementation time: ~1 hour**

**Expected payoff:**
- More realistic action diversity
- Ecologically valid human forecasting
- New research questions enabled
- Better comparison to real-world forecasting

**Ready to implement!**
