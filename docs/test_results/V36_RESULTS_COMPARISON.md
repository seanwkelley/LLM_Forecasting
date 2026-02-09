# V3.6 Test Results - Pre-Invasion with Cross-Expertise

**Date:** 2026-01-31
**Simulation ID:** a78e2208-7c76-4ff8-9149-03c6e6bbb062
**Scenario:** Pre-Invasion Crisis
**Runtime:** 132.9 minutes

---

## ⚠️ CONCERNING RESULTS - Action Diversity Got WORSE

### Action Diversity Comparison

| Metric | Baseline (Low Intensity) | v3.6 (Pre-Invasion) | Change | Target |
|--------|--------------------------|---------------------|--------|--------|
| **Unique actions** | 14 / 49 | **10 / 49** | ❌ -4 (-29%) | 25-35 |
| **Total actions** | 60 | 60 | = | - |
| **Most common action** | proxy_support (28%) | **proxy_support (37%)** | ❌ +9% | <15% |
| **Cross-expertise** | 0% | **0%** | = | 15-20% |

**Conclusion:** Action diversity decreased significantly, opposite of expected improvement.

---

## 📊 Detailed Action Breakdown

### By Faction

**Major Power (Novaris):**
- proxy_support: 6x (Periods 1-6)
- limited_strike: 4x (Periods 7-10)
- **Total unique: 2 actions** (vs 4 in baseline)

**Small Power (Tethys):**
- cyber_attack: 3x
- military_buildup: 2x
- peace_talks, diplomatic_visit, proxy_support, sabotage: 1x each
- **Total unique: 6 actions** (vs 5 in baseline) ✓ slightly better

**Meridian (Allied Defender):**
- proxy_support: 9x
- peace_talks: 1x
- **Total unique: 2 actions** (vs 3 in baseline)

**Valkoria (Allied Aggressor):**
- proxy_support: 6x
- spread_disinformation: 3x
- **Total unique: 2 actions** (vs 2 in baseline)

**Aurelia (Neutral):**
- mediation_offer: 4x
- diplomatic_visit: 3x
- peace_talks: 2x
- **Total unique: 3 actions** (same as baseline)

**International Org:**
- peace_talks: 5x
- humanitarian_aid: 2x
- mediation_offer: 2x
- **Total unique: 3 actions** (vs 2 in baseline) ✓ slight improvement

### Key Patterns

1. **Proxy_support dominated even more:** 22/60 (37%) vs 17/60 (28%) baseline
2. **Major power reduced diversity:** Only 2 actions (proxy_support → limited_strike)
3. **Minimal cross-category exploration:** No covert→diplomatic or economic→military crossovers
4. **Repetition increased:** Meridian used proxy_support 9/10 periods (90%!)

---

## 📈 Narrative Arc - Pre-Invasion Scenario

### Collapse Probability Trajectory

| Period | Collapse % | Trend | Territory | Key Event |
|--------|------------|-------|-----------|-----------|
| 1 | **15%** | STABLE | 0% | De-escalation efforts |
| 2 | **12%** | ↓ DECREASING | 0% | Diplomatic progress |
| 3 | 14% | ↑ INCREASING | 0% | |
| 4 | 12% | ↓ DECREASING | 0% | |
| 5 | **30%** | ↑ INCREASING | 0% | **⚡ SHOCK: Allied Support Wavers** |
| 6 | 38% | ↑ INCREASING | 0% | Shock impact continues |
| 7 | 42% | ↑ INCREASING | 0% | Crisis level → 10/10 |
| 8 | 45% | ↑ INCREASING | 0% | Military balance deteriorating |
| 9 | 48% | ↑ INCREASING | 0% | |
| 10 | **52%** | ↑ INCREASING | 0% | Final state |

**Arc:** De-escalation (15% → 12%) → Strategic shock → Political crisis (12% → 52%)

### Key Observations

1. **✓ No invasion occurred** - Territory remained 0% throughout
2. **✓ Interesting narrative** - Political collapse without military conflict
3. **⚡ Critical turning point:** "Allied Support Wavers" shock (Period 5) caused strategic crisis
4. **Crisis evolution:** Diplomatic crisis (5/10) → Maximum political crisis (10/10)
5. **Final state:** Political pressure from allied wavering, not military defeat

---

## 🔍 Why Did This Happen?

### Hypothesis 1: Cross-Expertise Prompts Not Working

**Evidence:**
- 0% cross-expertise detected (same as baseline)
- Action diversity decreased (opposite of expected)
- Role stereotyping intensified (proxy_support dominance)

**Possible causes:**
1. Prompts not actually loaded/used in execution
2. Prompt wording ineffective
3. Coordination data structure changed (extraction failing)
4. Model doesn't respond well to cross-expertise encouragement

**Next step:** Verify prompt is actually in use by examining coordination messages

### Hypothesis 2: Pre-Invasion Constrained Rather Than Liberated

**Evidence:**
- Major power stuck in "proxy_support loop" for 6 periods
- Very little military action (only 4x limited_strike at end)
- Almost no covert operations (1x sabotage total)
- Diplomatic actions failed repeatedly but kept being chosen

**Possible explanation:**
- Pre-invasion scenario made agents MORE cautious
- Fear of triggering invasion led to conservative choices
- Proxy_support seen as "safe" escalation option
- Agents defaulted to repetition when uncertain

**Paradox:** Pre-invasion was supposed to enable more creative options (deterrence, prevention), but instead created paralysis.

### Hypothesis 3: Model/Cognitive Limitations

**Evidence:**
- proxy_support used 22/60 times (37% - even worse than baseline 28%)
- Meridian used same action 9/10 periods
- Failed actions (mediation_offer, peace_talks) repeated multiple times
- No adaptation to failure

**Suggests:**
- Model has strong priors about "appropriate" actions
- Doesn't learn from repeated failures within simulation
- Cognitive load still overwhelming despite cross-expertise prompts

---

## ✅ What Worked

1. **Pre-invasion scenario narrative:** Interesting political crisis arc without military invasion
2. **Strategic shock impact:** "Allied Support Wavers" realistically derailed diplomatic progress
3. **No technical errors:** Simulation ran cleanly for 132.9 minutes
4. **Small power showed variety:** 6 unique actions (slight improvement)

---

## ❌ What Failed

1. **Action diversity decreased:** 10 vs 14 unique actions
2. **Cross-expertise: 0%** - No detectable cross-domain recommendations
3. **Proxy_support over-concentration:** 37% vs target <15%
4. **Major power diversity collapsed:** Only 2 actions used
5. **No learning from failure:** Repeated failed mediation 9+ times across factions

---

## 🔬 Diagnostic Steps Needed

### 1. Verify Cross-Expertise Prompts Actually Used

**Check coordination messages:**
```r
state <- readRDS("outputs/simulation_state.rds")

# Look for cross-expertise language in messages
for (p in 1:3) {
  if (!is.null(state$pre_action_coordination[[p]]$major_power$messages)) {
    for (msg in state$pre_action_coordination[[p]]$major_power$messages) {
      if (grepl("bring.*EXPERTISE|recommend ANY action", msg$content, ignore.case = TRUE)) {
        cat(sprintf("✓ Found cross-expertise prompt in Period %d\n", p))
        # Print excerpt
        cat(substr(msg$content, 1, 500), "\n\n")
      }
    }
  }
}
```

**If NOT found:** Cross-expertise prompts weren't loaded → need to debug why

**If found but ineffective:** Prompt wording needs revision

### 2. Examine Agent Reasoning

Look at Round 1 recommendations to see if agents even CONSIDERED cross-expertise actions:

```r
# Check if any agent recommended action outside their domain
for (p in 1:3) {
  messages <- state$pre_action_coordination[[p]]$major_power$messages
  if (!is.null(messages)) {
    for (msg in messages) {
      if (msg$sender_role == "economic" && grepl("strike|military|covert", msg$content, ignore.case = TRUE)) {
        cat("✓ Economic agent considered military/covert action\n")
      }
    }
  }
}
```

### 3. Compare to Baseline Coordination

Load baseline simulation and compare prompt structures to verify v3.6 changes were applied.

---

## 🎯 Possible Next Steps

### Option 1: Debug and Re-run

1. Verify cross-expertise prompts are actually being sent
2. Check if interaction_engine.R changes were properly loaded
3. Add logging to confirm prompt delivery
4. Re-run with verified cross-expertise implementation

### Option 2: Revise Prompt Strategy

If prompts ARE being used but ineffective:

**Current approach:**
```
"You bring [ROLE] EXPERTISE but can recommend ANY action"
```

**Alternative approach (more directive):**
```
"REQUIREMENT: You MUST consider at least one action outside your traditional domain.

Examples you should evaluate:
- Military experts: peace_talks, mediation_offer, backchannel_negotiations
- Diplomats: limited_strike, military_buildup, cyber_attack
- Economic advisors: sabotage, regime_destabilization, spread_disinformation
- Intel chiefs: coalition_building, humanitarian_corridors, prisoner_exchange

After considering cross-domain options, select the action that best serves your faction."
```

### Option 3: Two-Stage Decision Process

Implement the strategic direction filtering system:
1. Round 0: Choose strategic direction (A-F)
2. Round 1: Recommend from filtered set (8-12 actions)
3. Round 2: Deliberate and decide

This directly addresses cognitive overload.

### Option 4: Action Variety Penalties

Add explicit prompt:
```
"IMPORTANT: Your faction has used [ACTION] [X] times in previous periods.
Consider whether repeating this action is strategically optimal, or whether
alternative approaches might better serve your objectives."
```

### Option 5: Accept Pre-Invasion Scenario Constraint

Maybe pre-invasion scenario naturally constrains choices to "safe" options:
- Test cross-expertise with original low_intensity scenario
- Compare: Does scenario type interact with prompt effectiveness?

---

## 📝 Immediate Action Items

**Priority 1: Verify cross-expertise prompts were used**
- Examine coordination messages in simulation_state.rds
- Check for "bring [ROLE] EXPERTISE" language
- If missing → debug why src/interaction_engine.R changes weren't loaded

**Priority 2: Analyze agent reasoning**
- Extract Round 1 recommendations
- Check if agents even MENTIONED cross-domain actions
- Understand decision-making patterns

**Priority 3: Decide on next test**
- If prompts not used: Fix and re-run
- If prompts used but ineffective: Revise strategy
- If pre-invasion constraint: Test with low_intensity scenario

---

## 💡 Key Insights

1. **Pre-invasion created interesting narrative** - Political crisis without military invasion
2. **But constrained action diversity** - Agents more cautious, defaulted to "safe" options
3. **Cross-expertise either didn't activate or didn't work** - 0% cross-domain recommendations
4. **Cognitive overload remains** - proxy_support even MORE dominant than baseline
5. **Model shows limited adaptation** - Repeated failed actions without learning

**Bottom line:** v3.6 test did NOT achieve goal of improving action diversity. Need diagnostic work before next iteration.

---

**Status:** Results analyzed, diagnostic steps identified
**Next:** Verify cross-expertise prompts were actually used
