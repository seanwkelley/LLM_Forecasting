# Test Instructions - v3.8.1 CSV Improvements

**Date:** February 1, 2026
**Status:** Ready to test

---

## What Was Implemented

### 1. Fixed Detailed Action Log Error ✅
- No more crashes at end of simulation
- Displays multi-action and single-action correctly

### 2. Enhanced Actions CSV ✅
- **NEW:** Tracks ALL actions (approved, vetoed, counter-proposed)
- **NEW:** Shows who proposed each action (expert name + role)
- **NEW:** Shows approval_status column
- **NEW:** Consistent power naming (faction_name column)
- **NEW:** Target properly populated

### 3. NEW: Proposals CSV ✅
- **Bridges the gap** between coordination and final actions
- Shows what each domain expert proposed
- Includes expert's hawk/dove score
- Shows all proposals before presidential decision

---

## Understanding the Data Flow

### Your Question: "Are coordination and proposals different?"

**YES, they are separate steps with the same agents:**

#### Step 2: Pre-Action Coordination
- **When:** After external events
- **Who:** ALL agents discuss together
- **Format:** Open debate, each recommends ONE action
- **Saved to:** `period_XX_coordination.csv`

**Example:**
```
General Krasnov: "I recommend limited_strike because..."
Minister Volkov: "I recommend proxy_support because..."
Dr. Petrova: "I recommend peace_talks because..."
```

#### Step 3a: Domain Expert Proposals (NEW in v3.8)
- **When:** After coordination discussion
- **Who:** Only domain experts (military, intelligence, diplomatic, economic)
- **Format:** Structured proposals, 1-3 actions PER DOMAIN
- **Saved to:** `period_XX_proposals.csv` (NEW!)

**Example:**
```
MILITARY (General Krasnov):
  PRIMARY: limited_strike
  SECONDARY: show_of_force
  TERTIARY: troop_movements

INTELLIGENCE (Director Morozov):
  PRIMARY: proxy_support
  SECONDARY: sabotage
  TERTIARY: false_flag_operation
```

### Why Both?

**Coordination = Cabinet meeting debate**
- Everyone discusses strategy
- Considers costs, risks, alternatives
- Informal discussion format

**Proposals = Formal expert recommendations**
- Experts present options in their domain
- Structured primary/secondary/tertiary
- Professional menu of choices

**Same agents, different roles:**
- General Krasnov discusses in coordination
- General Krasnov formally proposes as military expert

---

## How to Test

### Step 1: Set API Key

**IMPORTANT:** Use OpenRouter key (starts with `sk-or-v1-`), NOT OpenAI key.

```bash
cd /d/Northeastern/LLM_Forecasting
export OPENROUTER_API_KEY="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"
```

Or from the OpenAI key you provided, you'll need to get an OpenRouter key from https://openrouter.ai/

### Step 2: Run Test

```bash
Rscript run_simulation_with_actions.R
```

### Step 3: Check Output Files

**Three CSV files will be created:**

1. **`outputs/interactions/period_01_coordination.csv`**
   - Pre-action discussion
   - All agents' recommendations

2. **`outputs/interactions/period_01_proposals.csv`** ← NEW!
   - Domain expert formal proposals
   - Shows what each expert proposed (primary/secondary/tertiary)

3. **`outputs/interactions/period_01_actions.csv`**
   - Final decisions (approved/vetoed/counter)
   - Execution results

---

## What to Look For

### In Coordination CSV

```bash
head -20 outputs/interactions/period_01_coordination.csv
```

**Expected:** Each agent recommends ONE action with rationale

**Example row:**
```csv
1,"major_power","STRATEGIC DECISION",1,"2026-02-01","General Viktor Krasnov","military",0.92,...,"1. RECOMMENDED ACTION: **limited_strike**..."
```

### In Proposals CSV (NEW!)

```bash
head -20 outputs/interactions/period_01_proposals.csv
```

**Expected:** Each domain expert has 1-3 rows (primary/secondary/tertiary)

**Example rows:**
```csv
period,faction,faction_name,domain,priority,proposed_by,proposed_by_role,proposed_by_hawk,proposed_action,rationale
1,"major_power","Novaris","military","primary","General Viktor Krasnov","military",0.92,"limited_strike","Hit forward command nodes..."
1,"major_power","Novaris","military","secondary","General Viktor Krasnov","military",0.92,"show_of_force","Visible mobilization freezes..."
1,"major_power","Novaris","intelligence","primary","Director Sergei Morozov","intelligence",0.58,"proxy_support","Let irregulars harass..."
```

### In Actions CSV

```bash
head -20 outputs/interactions/period_01_actions.csv
```

**Expected:** ALL proposals (approved, vetoed, counter-proposed)

**Example rows:**
```csv
period,faction,faction_name,decision_maker,proposed_by,proposed_action,final_action,approval_status,success
1,"major_power","Novaris","Minister Dmitri Volkov","General Viktor Krasnov","limited_strike","limited_strike","approved",TRUE
1,"small_power","Tethys","President Elena Marchetti","Director Maksym Savchenko","sabotage","sabotage","vetoed",NA
1,"small_power","Tethys","President Elena Marchetti","General Olena Bondar","limited_strike","show_of_force","counter_proposed",TRUE
```

---

## Quick Analysis Commands

### Count Proposals by Domain

```bash
tail -n +2 outputs/interactions/period_01_proposals.csv | cut -d',' -f4 | sort | uniq -c
```

**Expected output:**
```
  3 military
  3 intelligence
  2 diplomatic
  2 economic
```

### Count Approval Outcomes

```bash
tail -n +2 outputs/interactions/period_01_actions.csv | cut -d',' -f11 | sort | uniq -c
```

**Expected output:**
```
 12 approved
  5 counter_proposed
  3 vetoed
```

### See Which Actions Were Vetoed

```bash
grep '"vetoed"' outputs/interactions/period_01_actions.csv | cut -d',' -f6,9
```

**Expected:** Norm-violating actions from liberal institutionalist

### Trace One Action Through All Files

**Example: Trace General Krasnov's limited_strike:**

```bash
# 1. In coordination
grep "General Viktor Krasnov" outputs/interactions/period_01_coordination.csv | head -1

# 2. In proposals
grep "limited_strike" outputs/interactions/period_01_proposals.csv

# 3. In actions (final decision)
grep "limited_strike" outputs/interactions/period_01_actions.csv
```

---

## API Key Note

**The simulation uses OpenRouter, not OpenAI directly.**

- Your key: `sk-proj-k2Ai1...` = OpenAI key (won't work)
- Need: `sk-or-v1-...` = OpenRouter key (will work)

**Found in your history:**
```
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
```

Use this one, or get a new OpenRouter key from https://openrouter.ai/

---

## Expected Test Results

### Console Output

```
========== PERIOD 1 (Day 7) ==========

1. Generating external events...
  Generated 3 events

2. Pre-action coordination (intra-faction debate)...
  → Pre-action coordination within MAJOR POWER faction...
    [Agents discuss...]

3. Action decision & execution...
  → Generating domain expert proposals for MAJOR_POWER...

    PROPOSED ACTIONS:
    MILITARY (General Viktor Krasnov):
      PRIMARY: limited_strike
      SECONDARY: show_of_force
      TERTIARY: troop_movements
    [...]

  → Presidential review of proposals...

    APPROVAL DECISIONS:
    MILITARY:
      ✓ APPROVE PRIMARY: limited_strike
      ✓ APPROVE SECONDARY: show_of_force
      ↻ COUNTER TERTIARY: defensive_pact (was: troop_movements)
    [...]

  Saving interactions to CSV...
  Saved coordination to CSV: outputs/interactions/period_01_coordination.csv
  Saved proposals to CSV: outputs/interactions/period_01_proposals.csv
  Saved actions to CSV: outputs/interactions/period_01_actions.csv
```

### Files Created

```
outputs/interactions/
├── period_01_coordination.csv    (Step 2: Discussion)
├── period_01_proposals.csv       (Step 3a: Expert proposals) ← NEW!
└── period_01_actions.csv         (Step 3b: Final decisions)
```

---

## Summary

### What's New in v3.8.1

1. ✅ **Proposals CSV** - Shows domain expert proposals (bridges coordination → actions)
2. ✅ **Enhanced Actions CSV** - ALL actions (approved/vetoed/counter), complete attribution
3. ✅ **Fixed log error** - Detailed action log works correctly
4. ✅ **Consistent naming** - faction_name column (Novaris/Tethys)
5. ✅ **Target populated** - Actions show their targets

### Data Flow

```
External Events
     ↓
Coordination (discussion) → coordination.csv
     ↓
Domain Proposals (formal) → proposals.csv (NEW!)
     ↓
Presidential Approval → actions.csv
     ↓
Execution (success/fail) → actions.csv (success column)
```

### Ready to Test!

```bash
cd /d/Northeastern/LLM_Forecasting
export OPENROUTER_API_KEY="sk-or-v1-[your-key]"
Rscript run_simulation_with_actions.R
```

---

**Version:** v3.8.1
**Date:** February 1, 2026
**Status:** ✅ Ready for testing
