# Multi-Action System Data Flow

**Version:** v3.8.1
**Date:** February 1, 2026

---

## Overview

This document explains how data flows through the multi-action system and what gets saved to each CSV file. This clarifies the relationship between coordination discussions, domain expert proposals, and final approved actions.

---

## The Three-Step Process

### Step 1: External Events
- System generates random events (battlefield developments, diplomatic incidents, etc.)
- Provides context for agent discussions

### Step 2: Pre-Action Coordination
- **What happens:** All agents in a faction discuss and debate what to do
- **Output:** Each agent recommends ONE action with rationale
- **Saved to:** `period_XX_coordination.csv`

### Step 3a: Domain Expert Proposals (NEW in v3.8)
- **What happens:** Domain experts generate detailed proposals
- **Output:** Each expert proposes 1-3 actions (primary/secondary/tertiary)
- **Saved to:** `period_XX_proposals.csv` (NEW in v3.8.1)

### Step 3b: Presidential Approval
- **What happens:** President reviews all proposals and decides
- **Output:** Approve, veto, or counter-propose each action
- **Saved to:** `period_XX_actions.csv`

### Step 3c: Action Execution
- **What happens:** Approved actions execute and affect game state
- **Output:** Success/failure, effects on crisis level, military balance, etc.
- **Saved to:** `period_XX_actions.csv` (success field)

---

## CSV Files Explained

### 1. `period_XX_coordination.csv` - Pre-Action Discussion

**Purpose:** Captures the initial debate where agents recommend single actions

**Columns:**
- `period` - Period number
- `faction` - Faction code (major_power, small_power, etc.)
- `topic` - Discussion topic (e.g., "What action should we take?")
- `round` - Round number (1st recommendations, 2nd responses)
- `timestamp` - When message was sent
- `sender_name` - Agent who spoke
- `sender_role` - Their role (military, intelligence, diplomatic, economic, political, government)
- `hawk_dove` - Their hawk/dove score (0-1)
- `policy_adherence` - How much they follow faction policy
- `objective_alignment` - How aligned with faction objectives
- `worldview` - Their worldview (realist, liberal_institutionalist, etc.)
- `content` - What they said

**Example Row:**
```csv
1,"major_power","STRATEGIC DECISION: What action should we take?",1,"2026-02-01 10:12:05","Minister Dmitri Volkov","government",0.68,0.85,0.8,"realist","1. RECOMMENDED ACTION: **proxy_support**
2. RATIONALE: We achieve strategic erosion without direct exposure..."
```

**What it shows:**
- Minister Volkov (realist, 68% hawk) recommends proxy_support
- His rationale: deniable pressure without provocation
- This is round 1 (initial recommendations)

**What it DOESN'T show:**
- The domain expert proposals that come next
- What actions actually got approved
- Multi-action proposals (those come in Step 3a)

---

### 2. `period_XX_proposals.csv` - Domain Expert Proposals (NEW)

**Purpose:** Bridges the gap between coordination and final actions

**Columns:**
- `period` - Period number
- `faction` - Faction code
- `faction_name` - Human-readable name (Novaris, Tethys)
- `domain` - Which domain (military, intelligence, diplomatic, economic)
- `priority` - Priority level (primary, secondary, tertiary)
- `proposed_by` - Expert name
- `proposed_by_role` - Expert role
- `proposed_by_hawk` - Expert's hawk/dove score
- `proposed_action` - Action name
- `rationale` - Why they propose it
- `target` - Target of action (if applicable)
- `timestamp` - When proposed

**Example Rows:**
```csv
period,faction,faction_name,domain,priority,proposed_by,proposed_by_role,proposed_by_hawk,proposed_action,rationale,target,timestamp
1,"major_power","Novaris","military","primary","General Viktor Krasnov","military",0.92,"limited_strike","Hit their forward command nodes and degrade response time",NA,"2026-02-01 10:14:29"
1,"major_power","Novaris","military","secondary","General Viktor Krasnov","military",0.92,"show_of_force","Visible mobilization freezes their decision-making",NA,"2026-02-01 10:14:29"
1,"major_power","Novaris","intelligence","primary","Director Sergei Morozov","intelligence",0.58,"proxy_support","Let irregulars harass supply lines at minimal cost",NA,"2026-02-01 10:14:29"
```

**What it shows:**
- General Krasnov proposed 2 military actions (limited_strike as primary, show_of_force as secondary)
- Director Morozov proposed proxy_support as intelligence primary
- Each expert's hawk score and rationale

**Relation to coordination:**
- General Krasnov recommended "limited_strike" in coordination (round 1)
- He now formally proposes it as military PRIMARY
- Plus he adds SECONDARY and possibly TERTIARY options

---

### 3. `period_XX_actions.csv` - Final Decisions and Execution

**Purpose:** Shows what president decided for each proposal and execution results

**Columns:**
- `period` - Period number
- `faction` - Faction code
- `faction_name` - Human-readable name
- `decision_maker` - President/leader name
- `decision_maker_role` - Their role (government)
- `proposed_by` - Who proposed (from proposals CSV)
- `proposed_by_role` - Their role
- `proposed_action` - What was proposed
- `final_action` - What was executed (may differ if counter-proposed)
- `approval_status` - approved, vetoed, or counter_proposed
- `domain` - Which domain
- `priority` - Priority level
- `target` - Target of action
- `proposal_rationale` - Expert's reasoning
- `decision_rationale` - President's reasoning
- `success` - Whether action succeeded (TRUE/FALSE/NA for vetoed)
- `result_message` - Summary of outcome

**Example Rows:**

**Approved:**
```csv
1,"major_power","Novaris","Minister Dmitri Volkov","government","General Viktor Krasnov","military","limited_strike","limited_strike","approved","military","primary",NA,"Hit forward command nodes...","Limited strike delivers strategic advantage...",TRUE,"Approved action 1/10 (primary priority)"
```

**Vetoed:**
```csv
1,"small_power","Tethys","President Elena Marchetti","government","Director Maksym Savchenko","intelligence","sabotage","sabotage","vetoed","intelligence","primary",NA,"Strike mobilization centers...","Sabotage violates international norms...",NA,"Vetoed action 3/10 (primary priority)"
```

**Counter-Proposed:**
```csv
1,"small_power","Tethys","President Elena Marchetti","government","General Olena Bondar","military","limited_strike","show_of_force","counter_proposed","military","primary",NA,"Hit forward logistics...","Limited strike risks escalation; visible demonstration better...",TRUE,"Counter Proposed action 1/7 (primary priority)"
```

**What it shows:**
- Complete audit trail: who proposed → what they proposed → who decided → what they decided → why → outcome
- All proposals (approved, vetoed, counter-proposed)
- Execution success/failure

---

## Complete Example: Tracing One Action Through All Files

Let's trace **limited_strike** for Tethys through all three files:

### Step 2: Coordination CSV
```csv
1,"small_power","STRATEGIC DECISION",1,"2026-02-01","General Olena Bondar","military",0.88,...,"1. RECOMMENDED ACTION: **sabotage**
2. RATIONALE: Hit forward logistics hubs..."
```
- General Bondar (hawk) recommends sabotage in initial discussion
- Note: She recommends sabotage, but will propose limited_strike formally

### Step 3a: Proposals CSV
```csv
1,"small_power","Tethys","military","primary","General Olena Bondar","military",0.88,"limited_strike","Hit forward logistics hubs and send message",NA,"2026-02-01"
```
- General Bondar formally proposes limited_strike as military PRIMARY
- Slightly different from her coordination recommendation

### Step 3b: Actions CSV (Presidential Decision)
```csv
1,"small_power","Tethys","President Elena Marchetti","government","General Olena Bondar","military","limited_strike","show_of_force","counter_proposed","military","primary",NA,"Hit forward logistics...","Limited strike risks uncontrollable escalation...",TRUE,"Counter Proposed action 1/7"
```
- President Marchetti (liberal institutionalist, 62% hawk) counter-proposes
- Changes limited_strike → show_of_force (kinetic to non-lethal)
- Rationale: "risks uncontrollable escalation"
- Worldview alignment: dove counters DOWN to less aggressive option

---

## Analysis Workflows

### 1. Understanding Internal Debate

**Question:** What did agents discuss vs. what experts formally proposed?

```r
# Load coordination
coord <- read.csv("outputs/interactions/period_01_coordination.csv")

# Load proposals
proposals <- read.csv("outputs/interactions/period_01_proposals.csv")

# Compare
coord_recommendations <- coord %>%
  filter(round == 1) %>%
  select(sender_name, sender_role, content)

expert_proposals <- proposals %>%
  select(proposed_by, proposed_by_role, domain, priority, proposed_action, rationale)

# See how coordination influenced formal proposals
```

### 2. Presidential Decision Patterns

**Question:** Which types of actions get vetoed most often?

```r
actions <- read.csv("outputs/interactions/period_01_actions.csv")

# Veto rates by action type
veto_analysis <- actions %>%
  group_by(proposed_action, decision_maker) %>%
  summarise(
    total = n(),
    vetoed = sum(approval_status == "vetoed"),
    veto_rate = vetoed / total * 100
  ) %>%
  arrange(desc(veto_rate))
```

### 3. Expert vs President Alignment

**Question:** Do presidents follow expert recommendations?

```r
# Join proposals with actions to see alignment
expert_vs_president <- proposals %>%
  left_join(actions, by = c("period", "faction", "domain", "priority", "proposed_action")) %>%
  mutate(
    followed = case_when(
      approval_status == "approved" ~ "Followed",
      approval_status == "vetoed" ~ "Rejected",
      approval_status == "counter_proposed" ~ "Modified",
      TRUE ~ "Unknown"
    )
  )

# Analyze by expert hawk score
expert_vs_president %>%
  group_by(proposed_by_hawk_category = cut(proposed_by_hawk, breaks = c(0, 0.4, 0.7, 1)),
           followed) %>%
  count()
```

### 4. Worldview Consistency

**Question:** Do liberal institutionalists veto norm-violating actions?

```r
# Define norm-violating actions
norm_violations <- c("sabotage", "cyber_attack", "false_flag_operation", "assassination")

# Check if liberal institutionalists veto these
liberal_vetos <- actions %>%
  filter(proposed_action %in% norm_violations) %>%
  # Cross-reference with agent worldviews (would need to load agent data)
  select(decision_maker, proposed_action, approval_status, decision_rationale)
```

---

## Data Flow Diagram

```
External Events
      ↓
┌─────────────────────────────────────────┐
│ STEP 2: Pre-Action Coordination         │
│ - Agents discuss                         │
│ - Each recommends 1 action               │
│ - Saved to: coordination.csv             │
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│ STEP 3a: Domain Expert Proposals (NEW)  │
│ - Military expert: 1-3 actions           │
│ - Intelligence expert: 1-3 actions       │
│ - Diplomatic expert: 1-3 actions         │
│ - Economic expert: 1-3 actions           │
│ - Saved to: proposals.csv (NEW!)        │
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│ STEP 3b: Presidential Approval          │
│ - Review all proposals                   │
│ - Approve / Veto / Counter each one      │
│ - Decision based on worldview & strategy │
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│ STEP 3c: Action Execution               │
│ - Approved actions execute               │
│ - Effects on game state                  │
│ - Saved to: actions.csv                  │
└─────────────────────────────────────────┘
```

---

## Summary

**Three CSV Files, Three Purposes:**

1. **coordination.csv** - Initial discussion (who recommends what in debate)
2. **proposals.csv** - Formal proposals (domain experts propose 1-3 actions each)
3. **actions.csv** - Final decisions (president approves/vetoes/counters + execution)

**Key Improvement in v3.8.1:**
- Added proposals.csv to show the bridge between coordination and final actions
- Now you can see: discussion → proposals → decisions → execution
- Complete audit trail of multi-action decision-making process

---

**Version:** v3.8.1
**Date:** February 1, 2026
**Status:** ✅ Implemented and documented
