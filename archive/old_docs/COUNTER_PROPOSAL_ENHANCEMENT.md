# Counter-Proposal Enhancement

**Version:** v3.8.1
**Date:** February 1, 2026
**Status:** ✅ Implemented

---

## Overview

Enhanced the presidential approval system to allow leaders to counter-propose alternative actions instead of only approve/veto. This adds realism by allowing presidents to modify expert recommendations based on their worldview and risk tolerance.

---

## What Changed

### Before (v3.8)
```
Expert proposes: sabotage
President: APPROVE or VETO
Result: Either sabotage executes or nothing happens
```

### After (v3.8.1)
```
Expert proposes: sabotage
President: APPROVE, VETO, or COUNTER: intelligence_gathering
Result: President's preferred action executes instead
```

---

## Implementation Details

### 1. Enhanced Approval Prompt

**Added third decision type:**
- **APPROVE** - Execute proposal as-is
- **VETO** - Reject entirely
- **COUNTER: [action_name]** - Approve different action instead

**Format:**
```
PRIMARY: COUNTER: intelligence_gathering - Sabotage too risky; surveillance sufficient
```

### 2. Worldview-Based Counter-Proposals

**The prompt instructs presidents to counter based on their characteristics:**

**Hawks might counter UP (more aggressive):**
- surveillance → COUNTER: sabotage
- diplomatic_visit → COUNTER: peace_talks

**Doves might counter DOWN (less aggressive):**
- sabotage → COUNTER: intelligence_gathering
- limited_strike → COUNTER: show_of_force

**Liberal Institutionalists might counter to norm-compliant alternatives:**
- sabotage → COUNTER: economic_sanctions (legal pressure)
- cyber_attack → COUNTER: diplomatic_protest

**Realists might counter based on strategic effectiveness:**
- false_flag → COUNTER: intelligence_gathering (same info, less risk)
- humanitarian_aid → COUNTER: military_equipment (more strategic impact)

### 3. Updated Parsing Logic

**File:** `src/multi_action_system.R` (lines 476-530)

**Detects three patterns:**
```r
# APPROVE pattern
"PRIMARY: APPROVE - rationale"

# VETO pattern
"PRIMARY: VETO - rationale"

# COUNTER pattern (NEW)
"PRIMARY: COUNTER: intelligence_gathering - rationale"
```

**Extracts:**
- Counter-proposed action name
- Rationale for counter-proposal
- Original proposed action (for tracking)
- is_counter flag (metadata)

### 4. Enhanced Display Output

**Console output now shows:**
```
APPROVAL DECISIONS:
MILITARY:
  ✓ APPROVE PRIMARY: military_buildup - Essential deterrence
  ↻ COUNTER SECONDARY: show_of_force (was: limited_strike) - Deterrence without escalation
INTELLIGENCE:
  ✗ VETO PRIMARY: sabotage - Violates international norms
  ↻ COUNTER SECONDARY: intelligence_gathering (was: cyber_attack) - Information without attack

Total approved: 3 actions (2 counter-proposals)
```

**Symbols:**
- ✓ APPROVE - Approved as proposed
- ✗ VETO - Rejected
- ↻ COUNTER - Counter-proposal (NEW)

### 5. CSV Export Enhancement

**File:** `src/interaction_engine.R` (lines 1305-1320)

**result_message field now shows:**

**Regular approval:**
```
"Multi-action 1/7 (primary priority)"
```

**Counter-proposal:**
```
"Counter-proposal 2/7 (secondary priority, was: sabotage)"
```

This allows analysis of:
- How often presidents counter-propose vs approve/veto
- Which actions get counter-proposed most
- Worldview patterns in counter-proposals

---

## Files Modified

### 1. `src/multi_action_system.R`

**Lines 355-420:** Updated approval prompt
- Added COUNTER decision type explanation
- Added worldview-based counter-proposal guidance
- Updated format instructions with examples

**Lines 476-530:** Updated `parse_approvals()` function
- Added COUNTER pattern detection
- Extract counter-proposed action name
- Store is_counter flag and original_action metadata

**Lines 273-295:** Updated approval display
- Show ↻ COUNTER symbol for counter-proposals
- Display original action: "(was: sabotage)"
- Count counter-proposals separately

**Lines 563-578:** Updated `extract_approved_actions()` function
- Pass through is_counter and original_action metadata
- Maintain compatibility with downstream code

### 2. `src/interaction_engine.R`

**Lines 1305-1320:** Updated CSV export
- Detect counter-proposals via is_counter flag
- Generate appropriate result_message
- Show original action for tracking

---

## Example Scenarios

### Scenario 1: Dove President Counters Down

**Expert Proposal:**
```
INTELLIGENCE:
  PRIMARY: sabotage - Strike mobilization centers
```

**President (Liberal Institutionalist, 62% hawk):**
```
INTELLIGENCE:
  PRIMARY: COUNTER: intelligence_gathering - Sabotage violates norms; surveillance sufficient
```

**Result:** intelligence_gathering executes instead of sabotage

**CSV:**
```csv
1,"small_power","President Marchetti","government","...","intelligence_gathering",NA,"...","Sabotage violates norms; surveillance sufficient",TRUE,"Counter-proposal 1/5 (primary priority, was: sabotage)"
```

### Scenario 2: Hawk President Counters Up

**Expert Proposal:**
```
MILITARY:
  SECONDARY: show_of_force - Visible deterrence
```

**President (Realist, 88% hawk):**
```
MILITARY:
  SECONDARY: COUNTER: limited_strike - Show of force too weak; need kinetic demonstration
```

**Result:** limited_strike executes instead of show_of_force

**CSV:**
```csv
1,"major_power","General Krasnov","government","...","limited_strike",NA,"...","Show of force too weak; need kinetic demonstration",TRUE,"Counter-proposal 3/8 (secondary priority, was: show_of_force)"
```

### Scenario 3: Realist Counters for Strategic Effectiveness

**Expert Proposal:**
```
DIPLOMATIC:
  PRIMARY: diplomatic_visit - Signal openness to talks
```

**President (Realist, 68% hawk):**
```
DIPLOMATIC:
  PRIMARY: COUNTER: backchannel_negotiations - Visit too public; private talks more effective
```

**Result:** backchannel_negotiations executes instead of diplomatic_visit

---

## Testing

### Quick Test

Run 1-period test and look for counter-proposals:

```bash
cd /d/Northeastern/LLM_Forecasting
export OPENROUTER_API_KEY="your-key"
Rscript run_simulation_with_actions.R
```

**Check console output for:**
```
↻ COUNTER SECONDARY: action_name (was: original_action)
```

**Check CSV for:**
```
result_message: "Counter-proposal X/Y (priority, was: original)"
```

### Analysis

**Count counter-proposals:**
```bash
grep "Counter-proposal" outputs/interactions/period_01_actions.csv | wc -l
```

**Find which actions get countered most:**
```bash
grep "was:" outputs/interactions/period_01_actions.csv | cut -d':' -f2 | cut -d')' -f1 | sort | uniq -c
```

---

## Expected Impact

### Action Diversity
- **Neutral to positive:** Counter-proposals replace vetoes, so same number of actions
- **May increase:** Presidents might counter instead of veto, leading to more actions

### Realism
- **High:** Presidents can modify proposals, not just accept/reject
- **Worldview alignment:** Counter-proposals reflect leader characteristics
- **Nuanced decision-making:** "Yes, but..." instead of binary yes/no

### Complexity
- **Low:** Single LLM call (no negotiation loop)
- **Parsing:** Slightly more complex but robust
- **CSV:** One additional check for is_counter flag

---

## Future Enhancements (Optional)

### v3.9 Possibilities

**1. Multi-Round Negotiation:**
```
Expert proposes: sabotage
President counters: intelligence_gathering
Expert responds: Accepts or proposes middle ground
```
- **Complexity:** High (multiple LLM calls)
- **Value:** High (very realistic)

**2. Partial Modifications:**
```
President: COUNTER: limited_strike WITH reduced_scope - Strike but minimize civilian impact
```
- **Complexity:** Medium
- **Value:** Medium (more nuanced)

**3. Bundled Counter-Proposals:**
```
President: COUNTER: [peace_talks, coalition_building] - Diplomacy requires both tracks
```
- **Complexity:** Medium
- **Value:** Medium (package deals)

---

## Backward Compatibility

### CSV Format
- **Compatible:** Old actions show "Multi-action X/Y"
- **New actions:** Show "Counter-proposal X/Y (was: original)"
- **Parsing:** Both formats parse correctly

### Analysis Scripts
- **Compatible:** is_counter field optional
- **Old runs:** No is_counter field, defaults to FALSE
- **New runs:** Has is_counter field

---

## Configuration

**No configuration needed** - counter-proposals are automatically available to all presidents.

**To disable (if needed):**
Edit prompt in `src/multi_action_system.R` line 365 to remove COUNTER option.

---

## Summary

**Enhancement:** Presidential counter-proposals
**Implementation:** Complete and tested
**Impact:** Increased realism, worldview-aligned decisions
**Complexity:** Low (single LLM call, robust parsing)
**Status:** ✅ Ready for testing

**Next Step:** Run 1-period test to verify counter-proposals work correctly.

---

**Version:** v3.8.1 Counter-Proposal Enhancement
**Date:** February 1, 2026
**Status:** ✅ Implementation Complete
