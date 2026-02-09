# Action Execution System Guide

## Overview

Your simulation now has **full action execution capabilities**. Agents don't just discuss strategies—they **execute concrete military, economic, diplomatic, intelligence, covert, and WMD actions** that have real consequences on the simulation state.

---

## Quick Start

**Run the enhanced simulation:**
```r
source("run_simulation_with_actions.R")
```

That's it! The simulation will now:
1. ✅ Agents analyze situation through their worldview
2. ✅ Each faction chooses a concrete action
3. ✅ Actions are executed with probabilistic outcomes
4. ✅ State updates (GDP, military strength, territory, crisis level)
5. ✅ Agents discuss results
6. ✅ Aggregator predicts government collapse probability

---

## Action Categories (49 Total Actions)

### 1. DIPLOMATIC (6 actions)
Build relationships, negotiate peace, mediate conflicts.

| Action | Description | Effects |
|--------|-------------|---------|
| `diplomatic_visit` | High-level visit to strengthen ties | Trust +0.05, Relations improved |
| `peace_talks` | Initiate formal negotiations | Crisis -1, Opens settlement window |
| `trade_negotiation` | Negotiate trade agreement | Economic cooperation +0.1 |
| `cultural_exchange` | People-to-people connections | Soft power +0.05 |
| `humanitarian_aid` | Provide aid | International support +0.1, Cost $0.5B |
| `mediation_offer` | Offer to mediate | 40% chance: Crisis -2 |

**Example:**
```
Period 1:
External faction (Meridian) → diplomatic_visit to Tethys
Result: Trust increases, relations improved
Crisis Level: 5 → 5 (no change)
```

### 2. INTELLIGENCE (5 actions)
Gather information, conduct surveillance, spread disinformation.

| Action | Description | Effects |
|--------|-------------|---------|
| `intelligence_gathering` | Collect info on adversary | Information gained, Quality = access level |
| `surveillance_operation` | Establish ongoing monitoring | Success = deception capacity; If detected: Trust -0.3 |
| `counterintelligence` | Protect against enemy intel | Defensive capability +0.15 |
| `spread_disinformation` | Deception campaign | 70% success rate; If exposed: Trust -0.5, Reputation -0.2 |
| `propaganda_campaign` | Shape public opinion | Domestic support +0.05, Cost $0.1B |

**Example:**
```
Period 2:
Major power faction (Novaris) → spread_disinformation
Success: 70% × deception_capacity (0.9) = 63% chance
Result: SUCCESS - Enemy confused (+0.2 confusion)
If FAILED: Exposed - Trust damage -0.5, International reputation -0.2
```

### 3. ECONOMIC (6 actions)
Trade agreements, sanctions, embargoes, financial warfare.

| Action | Description | Effects |
|--------|-------------|---------|
| `trade_agreement` | Economic cooperation | Both sides GDP +2%, Interdependence +0.15 |
| `economic_sanctions` | Impose penalties | Target GDP -15% (major power), -10% (ally), -2% (small power)<br>Actor cost -4.5%<br>Crisis +1 |
| `financial_aid` | Provide monetary support | $2B aid, Target stability +0.1, Actor influence +0.1 |
| `resource_embargo` | Block critical resources | Target GDP -12%, Military capability -0.05, Crisis +2 |
| `currency_manipulation` | Economic warfare | 60% success: Target financial instability +0.15, GDP -8% |
| `cyber_theft` | Steal secrets | 80% × deception: Economic advantage +0.05<br>If detected: Diplomatic crisis |

**Example:**
```
Period 3:
External faction (Meridian) → economic_sanctions on Novaris
Effects:
  - Novaris GDP: $100B → $85B (-15%)
  - Meridian GDP: $200B → $195.5B (-4.5% blowback)
  - Sanctions level: 0.15 → 0.30
  - Crisis level: 5 → 6
```

### 4. MILITARY POSTURE (6 actions)
Build forces, deploy assets, prepare for conflict.

| Action | Description | Effects |
|--------|-------------|---------|
| `military_buildup` | Increase capabilities | Military strength +0.05, Cost $5B, Crisis +1 |
| `naval_deployment` | Deploy naval forces | Power projection +0.1, Cost $1.5B, Crisis +1 |
| `air_patrols` | Establish air presence | Air superiority +0.05, Cost $0.8B, Crisis +0.5 |
| `troop_movements` | Position ground forces | Readiness +0.1, Cost $2B, Crisis +2 |
| `joint_exercises` | Train with allies | Alliance cohesion +0.1, Coordination +0.05, Cost $1B |
| `arms_development` | Develop new weapons | Technological edge +0.08, Future capability +0.15, Cost $10B |

**Example:**
```
Period 4:
Major power faction (Novaris) → military_buildup
Effects:
  - Novaris military strength: 1.0 → 1.05
  - Novaris GDP: $85B → $80B (cost)
  - Crisis level: 6 → 7
```

### 5. COVERT OPERATIONS (6 actions - HIGH RISK)
Sabotage, assassination, regime change, proxy wars.

| Action | Description | Detection Risk | Success Effects | Failure/Detected Effects |
|--------|-------------|----------------|-----------------|-------------------------|
| `sabotage` | Damage infrastructure | 1 - deception_capacity | Infrastructure -0.15, Economic disruption -0.08, Military -0.05 | **Detected:** Diplomatic crisis, International condemnation +0.3, Crisis +3 |
| `assassination_attempt` | Target leadership | Very high | **30% success:** Leadership eliminated, Chaos +0.5, Instability +0.4, Crisis +5 | **Failed/Detected:** Act of war, International outrage +0.5, Crisis = 10 |
| `regime_destabilization` | Undermine government | 1 - deception_capacity | Political instability +0.2, Opposition +0.15, Legitimacy -0.2 | **Detected:** Crisis +2 |
| `proxy_support` | Support non-state actors | 1 - deception_capacity | Proxy capability +0.2, Indirect pressure +0.15, Cost $1B | **Detected:** Diplomatic fallout |
| `false_flag_operation` | Deception op | 1 - deception_capacity | **Success:** Enemy blamed, International support +0.2, Justification for action | **Detected:** Credibility destroyed, Isolation +0.4, Crisis +4 |
| `cyber_attack` | Attack systems | 1 - deception_capacity | Infrastructure disruption +0.12, Economic damage +0.06 | **Detected:** Attribution confirmed, Crisis +2 |

**Example:**
```
Period 5:
Major power faction (Novaris) → sabotage on Tethys infrastructure
Deception capacity: 0.9 → Detection risk: 10%
Roll: 0.08 → SUCCESS (not detected)
Effects:
  - Tethys infrastructure damage: 0.15
  - Tethys economic disruption: 0.08
  - Tethys military degradation: 0.05
  - No diplomatic fallout (covert)

If detected (roll > 0.9):
  - Diplomatic crisis: MAJOR
  - International condemnation: +0.3
  - Crisis level: 7 → 10
```

### 6. OPEN CONFLICT (6 actions - KINETIC WARFARE)
Border incursions, strikes, invasions, sieges.

| Action | Description | Success Calculation | Success Effects | Failure Effects |
|--------|-------------|---------------------|-----------------|-----------------|
| `border_incursion` | Limited border op | min(0.85, force_ratio × 0.6) | Territory +2%, Casualties: Attacker 50, Defender 120<br>Attrition -2%<br>Crisis = 10 | **Repelled:** Casualties: Attacker 200, Defender 80 |
| `limited_strike` | Precision strike | min(0.9, 0.5 + info_access × 0.4) | Military degradation -8%, Casualties: Military 80, Civilian 15<br>Defender capability: ×0.92 (small) or ×0.95 (major)<br>Crisis = 10 | **Missed:** Civilian casualties 50, International condemnation +0.3 |
| `full_scale_attack` | Major offensive | min(0.75, force_ratio × 0.5) | Territory +5-15%, Casualties: Attacker 800, Defender 1500<br>Equipment losses: Attacker 50, Defender 120<br>Attacker capability: ×0.85, Defender: ×0.70 (small) or ×0.80 (major)<br>Military balance -0.3<br>Crisis = 10 | **Stalled:** Casualties: Attacker 1200, Defender 900<br>Attacker capability: ×0.80 |
| `occupation` | Occupy territory | — | Occupation established, Ongoing cost $3B/period<br>Insurgency risk 0.3<br>Military tied down: ×0.90 | — |
| `blockade` | Naval/economic blockade | Requires major power or allied power | Effectiveness 0.7, Target economic damage -20%<br>Resupply blocked<br>Cost $1.5B/period<br>Crisis = 10 | **Small power:** Effectiveness only 0.3 |
| `siege_warfare` | Besiege cities | — | Humanitarian crisis +0.5<br>International condemnation +0.4<br>Civilian casualties 500<br>Crisis = 10 | — |

**Force Ratio Calculation:**
```r
if (attacker = major_power) {
  force_ratio = major_power_military / small_power_military
} else {
  force_ratio = small_power_military / major_power_military
}

# Example: Novaris (1.05) attacks Tethys (0.6)
force_ratio = 1.05 / 0.6 = 1.75

# full_scale_attack success probability:
success_prob = min(0.75, 1.75 × 0.5) = 0.75 (75% chance)
```

**Example:**
```
Period 6:
Major power faction (Novaris) → full_scale_attack on Tethys
Force ratio: 1.05 / 0.6 = 1.75
Success probability: min(0.75, 1.75 × 0.5) = 0.75 (75%)
Roll: 0.63 → SUCCESS

Effects:
  - Territory controlled: 0% → 8.5% (random 5-15%)
  - Casualties:
    - Novaris: 800 soldiers, 50 equipment
    - Tethys: 1500 soldiers, 120 equipment
  - Military strength:
    - Novaris: 1.05 → 0.89 (×0.85 attrition)
    - Tethys: 0.6 → 0.42 (×0.70 defender losses)
  - Military balance: -0.3
  - Crisis level: 10 (maximum)
```

### 7. WMD (5 actions - EXTREME)
Nuclear, chemical, biological weapons.

| Action | Description | Effects |
|--------|-------------|---------|
| `nuclear_development` | Build nuclear weapons | Nuclear capability +0.3, Cost $15B<br>International sanctions risk 0.6<br>Crisis +3 |
| `chemical_weapons` | Develop chemical weapons | Chemical capability +0.5, Cost $2B<br>International condemnation +0.4 |
| `biological_program` | Biological weapons research | Biological capability +0.4, Cost $5B<br>Isolation risk 0.5 |
| `tactical_nuclear_use` | Use tactical nuke | **EXTREME:** Nuclear threshold crossed<br>Casualties 5000, Territory destroyed 2%<br>Radiation contamination<br>International isolation = 1.0<br>Retaliation probability 80%<br>Sanctions level = 1.0 (maximum)<br>Crisis = 10 |
| `strategic_nuclear_strike` | Strategic nuclear exchange | **CATASTROPHIC:** Nuclear war<br>Civilization ending<br>Casualties: 50-200 million<br>**SIMULATION ENDS** |

**Example:**
```
Period 7:
Major power faction (Novaris) → tactical_nuclear_use
Result: NUCLEAR WEAPON USED

Effects:
  - Casualties: 5000
  - Territory destroyed: 2%
  - Radiation: TRUE
  - International isolation: 1.0 (complete)
  - Sanctions: 1.0 (maximum)
  - Retaliation probability: 80%
  - Crisis: 10 (maximum)

*** SIMULATION CONTINUES WITH NUCLEAR ESCALATION RISK ***

If strategic_nuclear_strike:
  - Casualties: 50-200 million
  - *** SIMULATION ENDS: nuclear_war ***
```

---

## How It Works

### 1. Action Decision Phase (Each Period)

**For each faction:**
1. Most senior agent (government > military > other) makes decision
2. Agent analyzes situation through worldview filter
3. LLM chooses action based on:
   - Role (military favors military actions, diplomats favor negotiations)
   - Worldview (realists favor force, liberals favor cooperation)
   - Hawk/dove score (hawks choose aggressive actions)
   - Current crisis level
   - Recent events
   - Faction capabilities

**Decision format:**
```
ACTION: military_buildup
TARGET: none
REASONING: Given our realist worldview and the enemy's recent provocations,
we must strengthen our military position to deter further aggression. The
force ratio currently favors us, and consolidating this advantage is critical.
EXPECTED_OUTCOME: Increased military readiness will deter enemy attacks and
give us negotiating leverage in any future talks.
```

### 2. Action Execution

**Action dispatcher:**
```r
execute_action(action, actor, target, state)
  → Determines action category
  → Calls appropriate handler:
     - execute_diplomatic_action()
     - execute_intelligence_action()
     - execute_economic_action()
     - execute_military_posture_action()
     - execute_covert_action()
     - execute_conflict_action()
     - execute_wmd_action()
```

**Each handler:**
1. Calculates success probability (if applicable)
2. Rolls for outcome
3. Applies effects to state:
   - Updates GDP
   - Updates military strength
   - Updates territory controlled
   - Updates crisis level
   - Updates sanctions level
4. Returns result object with effects

### 3. State Updates

**Tracked state variables:**
```r
state$scenario_state <- list(
  crisis_level = 0-10,
  military_balance = -1 to 1,
  sanctions_level = 0-1,
  territory_controlled = 0-1,
  nuclear_used = TRUE/FALSE,
  blockade_active = TRUE/FALSE
)

state$faction_capabilities <- list(
  major_power_military = 0.6-2.0,
  small_power_military = 0.3-1.0,
  major_power_gdp = 50-150 (billions),
  small_power_gdp = 15-50 (billions)
)
```

**Effects cascade:**
```
Action → Immediate effects → State update → Next period's context
```

### 4. Agent Discussion Phase

After actions execute, agents discuss:
- What just happened
- Results of actions
- Whether to continue, escalate, or deescalate

### 5. Aggregator Assessment

Aggregator LLM receives:
- External events
- Actions taken by each faction
- Results of those actions
- Current state (GDP, military strength, territory, crisis)
- Agent discussions

Outputs:
- Probability of government collapse (0-1)
- Confidence (LOW/MEDIUM/HIGH)
- Key factors explaining assessment
- Trend (INCREASING/STABLE/DECREASING)

---

## Example Full Period

```
========== PERIOD 3 (Day 21) ==========

1. Generating external events...
  - New Sanctions Package: International sanctions target major power
  - Major Battlefield Shift: Significant territorial gains

2. Action Decision & Execution Phase...

--- MAJOR_POWER Faction Decision ---
Decision maker: Major Power Defense Minister (Novaris)
ACTION: economic_sanctions
TARGET: Tethys
REASONING: As defense minister with realist worldview, I recognize that
economic pressure can weaken the enemy's war-fighting capability without
risking our forces. Sanctions will degrade their economy and reduce their
ability to sustain military operations.
EXPECTED_OUTCOME: Tethys GDP will decline, limiting their military spending
and potentially causing domestic unrest.

Executing: economic_sanctions
  ✓ Action executed: economic_sanctions
  → Economic sanctions imposed - target GDP -15.0%

Effects:
  - Tethys GDP: $30B → $25.5B
  - Novaris GDP: $80B → $76B (blowback)
  - Sanctions level: 0.15 → 0.30
  - Crisis level: 7 → 8

--- SMALL_POWER Faction Decision ---
Decision maker: Smaller Power President (Tethys)
ACTION: diplomatic_visit
TARGET: Meridian
REASONING: With our liberal institutionalist worldview, we believe
international cooperation is key to our survival. By strengthening ties with
Meridian, we can secure more military and economic aid. Personal diplomacy
may convince them to increase support.
EXPECTED_OUTCOME: Meridian will provide additional military aid package and
financial support to offset sanctions.

Executing: diplomatic_visit
  ✓ Action executed: diplomatic_visit
  → High-level visit strengthens alliance ties

Effects:
  - Trust Meridian-Tethys: +0.05
  - Diplomatic relations: improved
  - Alliance cohesion: strengthened

--- EXTERNAL Faction Decision ---
Decision maker: Allied Major Power Representative (Meridian)
ACTION: financial_aid
TARGET: Tethys
REASONING: As pragmatic technocrats, we assess that Tethys needs immediate
economic support to counter Novaris sanctions. Providing aid maintains
regional balance of power and prevents collapse of our ally.
EXPECTED_OUTCOME: Tethys stabilizes economically, continues resistance.

Executing: financial_aid
  ✓ Action executed: financial_aid
  → $2.0B financial aid provided

Effects:
  - Tethys stability: +0.1
  - Meridian influence in Tethys: +0.1
  - Meridian GDP: $195.5B → $193.5B
  - Aid amount: $2B

3. Running agent interactions...
  [Agents discuss the sanctions, the diplomatic outreach, and aid package]
  Completed 5 interactions

4. Updating scenario state...
  Battlefield event applies: Military balance shifts
  Action effects applied

5. Running aggregator assessment...
  Probability of government collapse: 42.0%
  Confidence: MEDIUM
  Trend: INCREASING
```

---

## Capabilities Summary

✅ **49 distinct actions** across 7 categories
✅ **Probabilistic outcomes** based on capabilities and force ratios
✅ **State tracking**: GDP, military strength, territory, crisis level, sanctions
✅ **Cascading effects**: Actions affect future capabilities
✅ **Attrition modeling**: Combat reduces military strength
✅ **Economic costs**: Military actions cost GDP
✅ **Detection risk**: Covert operations can be exposed
✅ **Trust dynamics**: Deception and aggression damage relationships
✅ **Crisis escalation**: Actions increase crisis level, can trigger war
✅ **Nuclear threshold**: WMD use can end simulation
✅ **Action logs**: Complete record of decisions and outcomes

---

## Research Questions You Can Answer

1. **Escalation Dynamics**
   - Do military buildups lead to preemptive attacks?
   - Can economic sanctions prevent military conflict?
   - What triggers cross nuclear threshold?

2. **Action Effectiveness**
   - Do covert operations achieve goals better than open conflict?
   - How effective are sanctions vs. military force?
   - Can diplomacy reverse escalation after violence begins?

3. **Worldview Effects on Action Choice**
   - Do realists choose military actions more often?
   - Do liberals prefer economic/diplomatic tools?
   - How do hawks vs. doves select actions?

4. **Information Asymmetry**
   - Does better intelligence lead to more effective strikes?
   - Do covert ops succeed more with high deception capacity?
   - Can poor info access lead to catastrophic decisions?

5. **Economic Warfare**
   - How much economic damage before government collapses?
   - Do sanctions cause regime change or entrenchment?
   - Can aid prevent collapse?

6. **Force Ratios**
   - What military balance prevents conflict?
   - Does overwhelming force deter or provoke?
   - How does attrition affect long conflicts?

---

## Next Steps

1. **Run the simulation:**
   ```r
   source("run_simulation_with_actions.R")
   ```

2. **Examine outputs:**
   - `outputs/simulation_summary_TIMESTAMP.txt` - Full summary
   - `outputs/run_TIMESTAMP/period_X_assessment.json` - Each period's assessment
   - Console output - Detailed action log

3. **Experiment:**
   - Modify agent hawk/dove scores in `config.R`
   - Change worldview assignments
   - Adjust force ratios
   - Compare outcomes

4. **Analyze:**
   - Which actions were chosen most often?
   - What triggered major escalations?
   - Did economic or military actions dominate?
   - How did worldviews affect choices?

---

## File Reference

| File | Purpose |
|------|---------|
| `src/action_execution.R` | **NEW** - Executes 49 actions, updates state |
| `src/agent_decision.R` | **NEW** - Agents choose actions via LLM |
| `src/simulation_with_actions.R` | **NEW** - Main simulation loop with action phase |
| `run_simulation_with_actions.R` | **NEW** - Run script |
| `config.R` | Agent definitions (unchanged) |
| `src/integrated_agent_system.R` | Worldviews, deception (unchanged) |
| `src/aggregator.R` | Probability assessment (unchanged) |

**Your original simulation is preserved** - the action execution is an enhancement, not a replacement!
