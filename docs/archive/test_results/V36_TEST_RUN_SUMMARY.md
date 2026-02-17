# V3.6 Test Run Summary

**Date:** 2026-01-31
**Purpose:** Test cross-expertise prompts with pre-invasion scenario for better action diversity

---

## ✅ Pre-Run Cleanup Complete

### Documentation Reorganization

**Created:**
- `DOCS_INDEX.md` - Central navigation hub
- `CODE_STRUCTURE.md` - Codebase organization guide
- `ACTION_SPACE_ANALYSIS.md` - Analysis of action space vs faction structure

**Archived:**
- All v3.6 implementation guides → `archive/v3.6_implementation/`
- Old implementation summaries → `archive/`
- Cross-expertise and strategic direction docs → `archive/v3.6_implementation/`

**Updated:**
- `README.md` - Points to DOCS_INDEX, cleaner v3.6 overview
- `DOCS_INDEX.md` - Added CODE_STRUCTURE reference

### Codebase Cleanup

**Archived:**
- `src/simulation.R` → `archive/src_deprecated/` (superseded by simulation_with_actions.R)

**Active files documented in CODE_STRUCTURE.md:**
- Clear dependency chain explained
- Purpose of each file documented
- Modification guide included

---

## 🎯 Simulation Configuration

### Scenario: Pre-Invasion (NEW!)

**Why pre-invasion for this test:**

✓ **Better action diversity potential:**
- No war footing yet - agents not locked into combat responses
- More strategic freedom - can choose escalation, de-escalation, or deterrence
- Diplomatic space - peace_talks makes sense (prevent war) vs repetitive mediation
- Covert ops more viable - sabotage, cyber, disinformation as alternatives
- Economic tools relevant - sanctions, aid as prevention rather than punishment

**Pre-invasion scenario parameters:**
- Territory controlled: **0%** (no invasion yet!)
- Crisis level: **5/10** (elevated but not maximum)
- Military balance: -0.15 to 0.0 (major power has advantage but not overwhelming)
- Sanctions: 10% (warning shots)
- International support: 50% (moderate - world watching)
- **Invasion is emergent** - may or may not happen based on agent decisions!

**Situation:**
> "ESCALATING TENSIONS: Major power (Novaris) is massing troops on the border with smaller power (Tethys). Diplomatic ultimatums have been issued demanding territorial concessions and neutrality. No shots fired yet, but military exercises are intensifying. The smaller power has begun mobilizing reserves and appealing for international support. The world is watching - invasion is possible but NOT inevitable. Both sides face a choice: escalate toward war, or find a diplomatic resolution."

---

## 🔬 Testing Hypotheses

### Hypothesis 1: Action Diversity Limited by Cognitive Overload, NOT Structural Mismatch

**Evidence from ACTION_SPACE_ANALYSIS.md:**

| Faction Type | Available Actions | Baseline Used | Utilization |
|--------------|-------------------|---------------|-------------|
| Direct Combatants | ~40 | 4-5 | 10-13% |
| Allied Actors | ~20 | 2-3 | 10-15% |
| Neutral | ~15 | 3 | 20% |
| Int'l Org | ~8 | 2 | 25% |

**Key finding:** Even direct combatants with 40 appropriate actions only used 10-13%, same utilization rate as supplementary actors. This points to cognitive constraints, not structural mismatch.

**Prediction:** If cross-expertise breaks role stereotyping, we should see improvement across ALL faction types, not just supplementary actors.

### Hypothesis 2: Cross-Expertise Will Improve Diversity

**Baseline (pre-v3.6):**
- 14 unique actions / 49 total (29%)
- 0% cross-expertise recommendations
- Heavy role stereotyping (military → military actions, diplomat → diplomatic actions)

**v3.6 cross-expertise targets:**
- **25-35 unique actions** (51-71% utilization)
- **15-20% cross-expertise rate**
- Examples: military chiefs recommending peace_talks, diplomats recommending limited_strike

### Hypothesis 3: Pre-Invasion Scenario Enables More Creativity

**Baseline scenario (limited incursion):**
- Already at war (7/10 crisis)
- Agents stuck in reactive "war mode"
- Limited room for preventive diplomacy

**Pre-invasion scenario advantages:**
- Wider strategic choice set (prevent vs escalate vs deter)
- Diplomatic actions more viable (backchannel_negotiations, mediation before shots fired)
- Economic actions more effective (sanctions as deterrent vs punishment)
- Covert ops as alternatives (cyber, disinformation instead of direct conflict)

**Combined prediction:** Cross-expertise + pre-invasion should create optimal conditions for action diversity (target: 30-40 unique actions).

---

## 🔧 Technical Changes

### Cross-Expertise Prompts (ACTIVE)

**File:** `src/interaction_engine.R` lines 823-854

**Change:** Round 1 prompt now includes:
```
You bring [ROLE] EXPERTISE to this decision, but you can recommend ANY action.

YOUR EXPERTISE:
- You understand what makes certain options FEASIBLE vs futile in your domain
- You can assess which approaches are likely to SUCCEED based on your experience
- Your perspective reveals threats and opportunities others might miss

However, EXPERTISE DOES NOT MEAN CONSTRAINT:
- A military expert CAN recommend diplomacy (if force has reached diminishing returns)
- An economic expert CAN recommend strikes (if decisive action costs less than attrition)
- A diplomat CAN recommend covert ops (if it creates leverage for negotiations)
- An intel chief CAN recommend humanitarian aid (if it builds networks for intelligence)

Recommend the action that BEST SERVES your faction, regardless of whether it fits your job title.
```

### Scenario Configuration (CHANGED)

**File:** `config.R` line 17

**Before:** `SCENARIO_PRESET <- "low_intensity"`
**After:** `SCENARIO_PRESET <- "pre_invasion"`

---

## 📊 Expected Outputs

### Action Diversity Metrics

**Compare to baseline:**
| Metric | Baseline | Target (v3.6) | Measurement |
|--------|----------|---------------|-------------|
| Unique actions | 14 | 25-35 | Count unique actions in outputs/simulation_summary_*.txt |
| Cross-expertise % | 0% | 15-20% | Analyze coordination logs for cross-domain recommendations |
| Action concentration | 28% (proxy_support) | <15% any single action | Check most common action frequency |

**Specific cross-expertise examples to look for:**
- Military agents recommending: peace_talks, backchannel_negotiations, humanitarian_corridors
- Diplomatic agents recommending: limited_strike, cyber_attack, military_buildup
- Economic agents recommending: sabotage, regime_destabilization, spread_disinformation
- Intelligence agents recommending: mediation_offer, financial_aid, coalition_building

### Narrative Outcomes

**Pre-invasion scenario possibilities:**

1. **De-escalation:** Agents choose diplomacy, crisis resolved without war
   - Expected actions: peace_talks, backchannel_negotiations, mediation_offer, financial_aid (incentives)
   - Probability of collapse: decreases toward 5-10%

2. **Deterrence:** Defensive buildup prevents invasion
   - Expected actions: military_buildup, show_of_force, coalition_building, defensive_fortification
   - Probability of collapse: stable around 15-25%

3. **Escalation → War:** Provocations lead to invasion
   - Expected actions: cyber_attack, sabotage, spread_disinformation → limited_strike → full invasion
   - Probability of collapse: increases toward 40-60%

4. **Mixed/Complex:** Some de-escalation, some provocations
   - Most interesting outcome - shows agent autonomy and emergent dynamics
   - Probability trajectory: fluctuates

### Analysis After Completion

Run these checks:

```r
# Load results
state <- readRDS("outputs/simulation_state.rds")

# 1. Action diversity
all_actions <- unlist(state$action_decisions)
unique_actions <- unique(all_actions)
cat("Unique actions:", length(unique_actions), "\n")
cat("Target: 25-35\n\n")

# 2. Cross-expertise rate
# (Requires parsing coordination messages - see analysis script)

# 3. Invasion outcome
if (state$scenario_state$territory_controlled > 0) {
  cat("OUTCOME: Invasion occurred\n")
  cat("Territory lost:", state$scenario_state$territory_controlled * 100, "%\n")
} else {
  cat("OUTCOME: Invasion prevented/avoided\n")
}

# 4. Collapse probability trajectory
assessments <- read.csv("outputs/assessments.csv")
plot(assessments$period, assessments$probability,
     type="l", main="Collapse Probability",
     xlab="Period", ylab="Probability")
```

---

## 📝 Files to Review After Run

1. **outputs/simulation_summary_YYYYMMDD_HHMMSS.txt**
   - Narrative summary
   - Action log (look for variety!)

2. **outputs/assessments.csv**
   - Probability trajectory
   - Check if invasion occurred (territory_controlled column if tracked)

3. **outputs/simulation_state.rds**
   - Complete state for analysis
   - Coordination logs in `pre_action_coordination` field

4. **Generated analysis report**
   - Will create after simulation completes

---

## ⏳ What's Running Now

**Command:**
```bash
OPENROUTER_API_KEY='...' Rscript run_simulation_with_actions.R
```

**Background task ID:** ba7d53c
**Output file:** C:\Users\seanw\AppData\Local\Temp\claude\C--Users-seanw\tasks\ba7d53c.output

**To check progress:**
```bash
tail -f C:\Users\seanw\AppData\Local\Temp\claude\C--Users-seanw\tasks\ba7d53c.output
```

**Expected runtime:** ~2-2.5 hours (based on 133 minutes for baseline)

**Model:** qwen/qwen3-235b-a22b-2507 (via OpenRouter)

---

## 🎯 Success Criteria

**Minimum success (validates cross-expertise):**
- ✓ Unique actions: >20 (vs 14 baseline)
- ✓ Cross-expertise: >10% (vs 0% baseline)
- ✓ At least 3 examples of cross-domain recommendations

**Strong success (validates both hypotheses):**
- ✓ Unique actions: 25-35
- ✓ Cross-expertise: 15-20%
- ✓ Diverse examples across all faction types
- ✓ Pre-invasion enables novel action combinations (deterrence, prevention, de-escalation)

**Exceptional success (emergent complexity):**
- ✓ Unique actions: >35
- ✓ Cross-expertise: >20%
- ✓ Interesting narrative arc (not just linear escalation)
- ✓ Invasion outcome emergent from agent choices (not predetermined)

---

## 📋 Next Steps After Completion

1. **Analyze results** - Run analysis script to measure metrics
2. **Compare to baseline** - Side-by-side comparison document
3. **Generate external observer prompts** - Test realistic forecasting system
4. **Decision:** Did cross-expertise work?
   - If YES: Consider integrating two-stage strategic direction filtering
   - If NO: Investigate why (prompt not working? Other constraints?)
5. **Iterate:** Refine based on findings

---

**Status:** 🏃 RUNNING IN BACKGROUND
**Started:** 2026-01-31 (check task output for exact time)
**Check for completion:** Use TaskOutput tool with task_id ba7d53c
