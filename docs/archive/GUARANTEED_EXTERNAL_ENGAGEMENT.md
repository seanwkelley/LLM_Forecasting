# Guaranteed External Engagement

**Implemented:** January 2026
**Version:** 3.1.2

## Change Summary

All external actor post-action engagement is now **guaranteed** (100% probability) instead of probabilistic. This ensures consistent diplomatic activity during active warfare.

---

## What Changed

### OLD System (v3.1.1)
```
Post-action discussions (probabilistic):
✅ Meridian → Tethys: 100% (guaranteed)
⚠️  Valkoria → Novaris: 60% chance
⚠️  Aurelia → mediation: 40% chance
⚠️  Int'l Org → humanitarian: 50% chance
```

**Problem:** Inconsistent - why would Meridian always engage but Valkoria only 60%?

### NEW System (v3.1.2)
```
Post-action discussions (all guaranteed):
✅ Meridian → Tethys: 100%
✅ Valkoria → Novaris: 100%
✅ Aurelia → mediation: 100%
✅ Int'l Org → humanitarian: 100%
```

**Benefit:** Consistent, realistic diplomatic engagement during active conflict.

---

## Rationale

### Why Guarantee All External Engagement?

**1. Realism**
- During active warfare, allies ARE constantly engaged
- Mediators don't randomly skip periods during crises
- Humanitarian organizations continuously monitor conflicts
- Diplomatic activity is sustained, not sporadic

**2. Consistency**
- If Meridian (Allied Defender) engages every period, Valkoria (Allied Aggressor) should too
- Both are primary supporters with similar stakes in the outcome
- No logical reason for different engagement frequencies

**3. Research Value**
- More consistent data for analyzing external actor influence
- Can compare effectiveness across all actors
- Removes random noise from engagement patterns

**4. Active Conflict Context**
- Simulation models ongoing invasion (not peacetime)
- Crisis level typically 6-10 (high intensity)
- External actors would maintain constant diplomatic channels
- Real-world examples (Ukraine): Allies engage daily, not randomly

---

## Impact on Simulation

### Interaction Count Change

**Before (v3.1.1):**
- Meridian → Tethys: ~10 messages (guaranteed)
- Valkoria → Novaris: ~6 messages (60% × 10)
- Aurelia → mediation: ~4 messages (40% × 10)
- Int'l Org → humanitarian: ~5 messages (50% × 10)
- **Expected total: ~25 messages per period**

**After (v3.1.2):**
- Meridian → Tethys: ~10 messages (guaranteed)
- Valkoria → Novaris: ~10 messages (guaranteed)
- Aurelia → mediation: ~10 messages (guaranteed)
- Int'l Org → humanitarian: ~10 messages (guaranteed)
- **Expected total: ~40 messages per period**

**Additional cost: +15 LLM calls per period** (still manageable)

### Total Interactions Per Period

**Complete breakdown (with guarantee):**
```
Pre-action coordination:         16 messages (guaranteed)
Post-action: Novaris internal:   20 messages (guaranteed)
Post-action: Tethys internal:    20 messages (guaranteed)
Post-action: Novaris ↔ Tethys:   10 messages (guaranteed)
Post-action: Meridian → Tethys:  10 messages (guaranteed)
Post-action: Valkoria → Novaris: 10 messages (guaranteed)
Post-action: Aurelia → mediation: 10 messages (guaranteed)
Post-action: Int'l Org → human:  10 messages (guaranteed)
---------------------------------------------------
Total:                          ~106 messages per period
```

**10 periods × 106 messages = ~1,060 LLM calls per simulation**

---

## Research Benefits

### 1. Consistent Data Collection
- Every period has complete external actor engagement data
- Can measure influence patterns reliably
- No missing data from random non-engagement

### 2. Alliance Dynamics
- Parallel analysis of Meridian-Tethys vs Valkoria-Novaris coordination
- Both alliances visible every period
- Can compare support strategies

### 3. Third-Party Influence
- Aurelia's mediation efforts tracked consistently
- Can measure mediation effectiveness over time
- No random gaps in mediation attempts

### 4. Humanitarian Pressure
- International Org engagement tracked every period
- Can analyze humanitarian concerns' impact on decisions
- Consistent moral/legal pressure on combatants

### 5. Network Analysis
- Complete interaction network every period
- No missing edges from probabilistic engagement
- Better centrality and influence metrics

---

## Code Changes

### Modified File
**`src/interaction_engine.R`** (lines 77-110)

### Changes Made

**1. Valkoria → Novaris (line 77)**
```r
# OLD
if (length(valkoria_agents) > 0 && length(major_agents) > 0 && runif(1) < 0.6) {

# NEW
if (length(valkoria_agents) > 0 && length(major_agents) > 0) {
```

**2. Aurelia → Mediation (line 87)**
```r
# OLD
if (length(aurelia_agents) > 0 && runif(1) < 0.4) {

# NEW
if (length(aurelia_agents) > 0) {
```

**3. International Org → Humanitarian (line 99)**
```r
# OLD
if (length(intl_org_agents) > 0 && runif(1) < 0.5) {

# NEW
if (length(intl_org_agents) > 0) {
```

**Removed:** All `runif(1) < probability` checks

---

## Examples

### Period 3 Post-Action Discussions (Guaranteed)

```
3. Running agent interactions...

Intra-faction: Novaris internal
  - Defense Minister, Military Chief, Economic Advisor, Intel Director
  - Topic: Review actions taken and coordinate response

Intra-faction: Tethys internal
  - President, Military Commander, Foreign Minister, Opposition Leader
  - Topic: Assess situation and plan next moves

Inter-faction: Novaris ↔ Tethys
  - Defense Minister ↔ Foreign Minister
  - Topic: Backchannel ceasefire discussions

External: Meridian → Tethys
  - Meridian Rep ↔ Tethys President
  - Topic: Military aid coordination

External: Valkoria → Novaris (NOW GUARANTEED)
  - Valkoria Rep ↔ Novaris Defense Minister
  - Topic: Diplomatic coordination

External: Aurelia → Tethys (NOW GUARANTEED)
  - Aurelia Rep ↔ Tethys Foreign Minister
  - Topic: Mediation proposal

External: Int'l Org → Novaris (NOW GUARANTEED)
  - UN Rep ↔ Novaris Defense Minister
  - Topic: Humanitarian access to occupied territories

Completed 7 interactions
```

---

## Performance Considerations

### Cost Analysis

**Additional LLM calls per simulation:**
- 15 more messages per period (3 previously probabilistic scenarios × 5 exchanges × 2 agents / 2)
- 10 periods = 150 additional LLM calls
- At ~$0.001 per call (average) = ~$0.15 per simulation

**Time Impact:**
- ~15 seconds per period (at 1 sec/LLM call)
- 10 periods = ~2.5 additional minutes per simulation
- Total simulation time: ~15-20 minutes (was ~12-17 minutes)

**Verdict:** Minimal impact, worth the consistency

---

## Alternative Considered (Not Implemented)

### Crisis-Dependent Probabilities
```r
# External engagement increases with crisis level
engagement_prob <- min(1.0, 0.3 + (state$scenario_state$crisis_level / 10) * 0.7)

# At crisis 10 → 100% engagement
# At crisis 5 → 65% engagement
```

**Why not chosen:**
- More complex to implement
- Harder to interpret results
- Conflict already starts at high crisis (7-9)
- Would only reduce engagement at low crisis (rare)

**Future consideration:** Could implement if simulation extends to peacetime periods

---

## Testing

To verify guaranteed engagement:

```bash
Rscript run_simulation_with_actions.R
```

**Check console output for each period:**
- Should see **7 post-action interaction scenarios** every time
- No random variation in external actor engagement
- All 4 external actors appear in post-action discussions

**Verify in logs:**
```r
# Load simulation
state <- readRDS("outputs/simulation_state.rds")

# Check interaction counts per period
sapply(state$interactions_history, function(period) {
  period$interaction_count
})

# Should be consistent across periods (no random drops)
```

---

## Summary Table

| Actor | OLD Probability | NEW Probability | Rationale |
|-------|----------------|-----------------|-----------|
| **Meridian → Tethys** | 100% | 100% | ✅ Already guaranteed |
| **Valkoria → Novaris** | 60% | **100%** | ✅ Primary ally, should match Meridian |
| **Aurelia → Mediation** | 40% | **100%** | ✅ Active mediator doesn't randomly skip |
| **Int'l Org → Humanitarian** | 50% | **100%** | ✅ Ongoing crisis needs constant monitoring |

---

**Feature Status**: ✅ **IMPLEMENTED and ACTIVE**

All external engagement is now guaranteed for consistent diplomatic activity during active warfare.
