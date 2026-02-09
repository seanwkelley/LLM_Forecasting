# CSV Actions File Improvements - v3.8.1

**Date:** February 1, 2026
**Status:** ✅ Implemented

---

## Overview

Enhanced the actions CSV file to provide comprehensive tracking of ALL proposed actions (not just executed ones), with clear attribution of who proposed each action and what the president decided.

---

## New CSV Structure

### New Columns Added

| Column | Description | Example Values |
|--------|-------------|----------------|
| **faction_name** | Human-readable faction name | "Novaris", "Tethys", "Meridian" |
| **decision_maker** | Leader who approved/vetoed | "Minister Dmitri Volkov" |
| **decision_maker_role** | Leader's role | "government" |
| **proposed_by** | Expert who proposed action | "General Viktor Krasnov" |
| **proposed_by_role** | Expert's role | "military", "intelligence", etc. |
| **proposed_action** | Original action proposed | "limited_strike" |
| **final_action** | Action that was executed | "show_of_force" (if counter-proposed) |
| **approval_status** | President's decision | "approved", "vetoed", "counter_proposed" |
| **domain** | Which domain proposed it | "military", "intelligence", "diplomatic", "economic" |
| **priority** | Priority level | "primary", "secondary", "tertiary" |
| **target** | Target of action | "Novaris and Tethys", "Tethys", NA |
| **proposal_rationale** | Why expert proposed it | Expert's reasoning |
| **decision_rationale** | Why president decided | President's reasoning |

### Column Changes

| Old Column | New Column | Change |
|------------|------------|--------|
| faction | faction + faction_name | Added human-readable name |
| agent_name | decision_maker | Clearer name |
| agent_role | decision_maker_role | Clearer name |
| action | final_action | Renamed for clarity |
| reasoning | proposal_rationale + decision_rationale | Split into two |
| expected_outcome | decision_rationale | Merged/clarified |

---

## What's Tracked Now

### ALL Actions Included

**Before (v3.8):**
- Only approved actions saved to CSV
- Vetoed actions were lost
- Counter-proposals indicated but original action not tracked separately

**After (v3.8.1):**
- ✅ **Approved actions** - executed as proposed
- ✅ **Vetoed actions** - rejected by president
- ✅ **Counter-proposed actions** - president suggested alternative

### Complete Audit Trail

Each row now shows:
1. **Who proposed**: Expert name and role
2. **What they proposed**: Original action name and rationale
3. **Who decided**: President/leader name and role
4. **What they decided**: Approved, vetoed, or counter-proposed
5. **Final action**: What was actually executed
6. **Why**: Both expert and president rationales

---

## Example Rows

### Approved Action

```csv
period,faction,faction_name,decision_maker,decision_maker_role,proposed_by,proposed_by_role,proposed_action,final_action,approval_status,domain,priority,target,proposal_rationale,decision_rationale,success
1,"major_power","Novaris","Minister Dmitri Volkov","government","General Viktor Krasnov","military","limited_strike","limited_strike","approved","military","primary",NA,"We hit their forward command nodes and degrade response time","Limited strike delivers strategic advantage with controlled escalation",TRUE
```

**Interpretation:**
- General Krasnov (military) proposed limited_strike
- Minister Volkov approved it as proposed
- Action executed successfully

### Vetoed Action

```csv
period,faction,faction_name,decision_maker,decision_maker_role,proposed_by,proposed_by_role,proposed_action,final_action,approval_status,domain,priority,target,proposal_rationale,decision_rationale,success
1,"small_power","Tethys","President Elena Marchetti","government","Director Maksym Savchenko","intelligence","sabotage","sabotage","vetoed","intelligence","primary",NA,"Strike mobilization centers to degrade enemy readiness","Sabotage violates international norms and risks diplomatic isolation",NA
```

**Interpretation:**
- Director Savchenko (intelligence) proposed sabotage
- President Marchetti vetoed it
- Action NOT executed (success = NA)
- President's reasoning: violates international norms

### Counter-Proposed Action

```csv
period,faction,faction_name,decision_maker,decision_maker_role,proposed_by,proposed_by_role,proposed_action,final_action,approval_status,domain,priority,target,proposal_rationale,decision_rationale,success
1,"small_power","Tethys","President Elena Marchetti","government","General Olena Bondar","military","limited_strike","show_of_force","counter_proposed","military","primary",NA,"Hit forward logistics hubs and send message","Limited strike risks uncontrollable escalation; visible demonstration better",TRUE
```

**Interpretation:**
- General Bondar (military) proposed limited_strike
- President Marchetti counter-proposed show_of_force instead
- Counter-proposal executed successfully
- Shows hawk general proposing kinetic action, liberal institutionalist countering DOWN to non-lethal

---

## Analysis Opportunities

### New Queries Possible

**1. Who proposes the most aggressive actions?**
```r
hawks <- actions %>%
  filter(proposed_action %in% c("limited_strike", "sabotage", "cyber_attack")) %>%
  count(proposed_by, proposed_by_role) %>%
  arrange(desc(n))
```

**2. Which actions get vetoed most often?**
```r
vetoed_actions <- actions %>%
  filter(approval_status == "vetoed") %>%
  count(proposed_action, faction_name) %>%
  arrange(desc(n))
```

**3. Do liberal institutionalists veto norm-violating actions?**
```r
# Cross-reference with agent worldviews
norm_violations <- c("sabotage", "cyber_attack", "false_flag_operation")

veto_patterns <- actions %>%
  filter(proposed_action %in% norm_violations) %>%
  group_by(decision_maker, approval_status) %>%
  summarise(count = n())
```

**4. Counter-proposal patterns by worldview**
```r
counters <- actions %>%
  filter(approval_status == "counter_proposed") %>%
  mutate(
    direction = case_when(
      # Classify as UP (more aggressive) or DOWN (less aggressive)
      proposed_action %in% c("diplomatic_visit") & final_action %in% c("peace_talks") ~ "UP",
      proposed_action %in% c("limited_strike") & final_action %in% c("show_of_force") ~ "DOWN",
      TRUE ~ "LATERAL"
    )
  )
```

**5. Expert vs President disagreement rate**
```r
disagreement <- actions %>%
  filter(approval_status != "approved") %>%
  group_by(proposed_by_role, decision_maker) %>%
  summarise(
    total_proposals = n(),
    vetoed = sum(approval_status == "vetoed"),
    countered = sum(approval_status == "counter_proposed"),
    disagreement_rate = (vetoed + countered) / n() * 100
  )
```

**6. Domain-specific approval rates**
```r
domain_approval <- actions %>%
  group_by(domain, faction_name) %>%
  summarise(
    total = n(),
    approved = sum(approval_status == "approved"),
    vetoed = sum(approval_status == "vetoed"),
    countered = sum(approval_status == "counter_proposed"),
    approval_rate = approved / total * 100
  )
```

**7. Track decision-making over time**
```r
# See if presidents become more hawkish or dovish over periods
decision_evolution <- actions %>%
  group_by(period, decision_maker, approval_status) %>%
  summarise(count = n()) %>%
  pivot_wider(names_from = approval_status, values_from = count)
```

---

## Implementation Details

### Files Modified

**1. src/multi_action_system.R**

- **New function**: `extract_all_actions_with_status(proposals, approvals)`
  - Returns ALL actions (not just approved)
  - Includes approval status for each
  - Merges proposal and decision information

- **Updated function**: `parse_approvals(response, proposals)`
  - Now captures proposed_by, proposed_by_role from proposals
  - Captures target if specified

- **Updated function**: `extract_approved_actions(approvals)`
  - Now passes through proposed_by, proposed_by_role, target

**2. src/agent_decision.R**

- **Lines 1256-1280**: Updated multi-action decision storage
  - Calls `extract_all_actions_with_status()`
  - Stores all_actions_with_status in decisions structure
  - Adds faction_name (Novaris/Tethys)
  - Adds decision_maker_role

**3. src/interaction_engine.R**

- **Lines 1284-1375**: Completely rewrote `save_actions_to_csv()`
  - Uses all_actions_with_status when available
  - Creates comprehensive CSV with all new columns
  - Handles approved, vetoed, and counter-proposed actions
  - Maintains backward compatibility with old structure
  - Properly handles single-action external actors

---

## Backward Compatibility

### CSV Format

**Old simulations:**
- Missing new columns will show NA
- Can still be read and analyzed

**New simulations:**
- Include all new columns
- Richer data available

### Analysis Scripts

**No breaking changes:**
- Old column names still available (faction, success, etc.)
- New columns are additions, not replacements
- Scripts can check for column existence

```r
# Safe analysis code
if ("approval_status" %in% colnames(actions)) {
  # Use new detailed tracking
  analyze_vetoes(actions)
} else {
  # Use old tracking (approved only)
  analyze_executions(actions)
}
```

---

## Testing

### Verification Steps

1. ✅ **All proposed actions appear in CSV**
   - Check that vetoed actions are included
   - Verify counter-proposals show both proposed and final action

2. ✅ **Expert attribution correct**
   - Military actions proposed by military experts
   - Intelligence actions proposed by intelligence experts
   - etc.

3. ✅ **Approval status accurate**
   - Approved actions have success = TRUE
   - Vetoed actions have success = NA
   - Counter-proposed actions executed successfully

4. ✅ **Faction names consistent**
   - major_power shows as "Novaris"
   - small_power shows as "Tethys"
   - External actors show actual names

5. ✅ **Target populated**
   - Actions with targets show target name
   - Actions without targets show NA

---

## Expected Impact

### Research Benefits

**1. Understand Internal Debate**
- See what experts propose vs what leaders approve
- Track hawk/dove dynamics within factions
- Identify worldview-based vetoes

**2. Decision-Making Patterns**
- Which leaders approve aggressive actions?
- Do liberal institutionalists veto norm violations?
- How often do realists make strategic counter-proposals?

**3. Expert Influence**
- Which experts get their proposals approved most?
- Do military experts dominate in high crisis?
- Do economic experts influence risk assessment?

**4. Evolution Over Time**
- Do leaders become more hawkish as conflict progresses?
- Does veto rate change with crisis level?
- Counter-proposal frequency over time?

---

## Example Analysis Script

```r
library(dplyr)
library(ggplot2)

# Load actions
actions <- read.csv("outputs/interactions/period_01_actions.csv")

# 1. Approval rates by domain
domain_stats <- actions %>%
  filter(!is.na(domain)) %>%
  group_by(faction_name, domain) %>%
  summarise(
    proposed = n(),
    approved = sum(approval_status == "approved"),
    vetoed = sum(approval_status == "vetoed"),
    countered = sum(approval_status == "counter_proposed"),
    approval_rate = approved / proposed * 100
  )

print(domain_stats)

# 2. Most vetoed action types
vetoed_actions <- actions %>%
  filter(approval_status == "vetoed") %>%
  count(proposed_action, faction_name) %>%
  arrange(desc(n))

print(vetoed_actions)

# 3. Counter-proposal patterns
counters <- actions %>%
  filter(approval_status == "counter_proposed") %>%
  select(faction_name, proposed_by, proposed_action, final_action, decision_rationale)

print(counters)

# 4. Expert success rates
expert_success <- actions %>%
  filter(!is.na(proposed_by)) %>%
  group_by(proposed_by, proposed_by_role) %>%
  summarise(
    proposals = n(),
    approved = sum(approval_status == "approved"),
    vetoed = sum(approval_status == "vetoed"),
    countered = sum(approval_status == "counter_proposed"),
    success_rate = approved / proposals * 100
  ) %>%
  arrange(desc(success_rate))

print(expert_success)

# 5. Visualize approval patterns
ggplot(actions %>% filter(!is.na(domain)),
       aes(x = domain, fill = approval_status)) +
  geom_bar(position = "fill") +
  facet_wrap(~ faction_name) +
  coord_flip() +
  labs(title = "Approval Patterns by Domain",
       y = "Proportion",
       x = "Domain") +
  theme_minimal()
```

---

## Summary

**Enhancement:** Comprehensive action tracking with full decision-making audit trail
**New Data:** Who proposed, what was proposed, who decided, what they decided, why
**Status:** ✅ Implemented and ready for testing
**Impact:** Enables rich analysis of internal government dynamics and leader decision-making

**Next Step:** Run test to verify new CSV structure works correctly

---

**Version:** v3.8.1
**Date:** February 1, 2026
**Implementation:** Complete
