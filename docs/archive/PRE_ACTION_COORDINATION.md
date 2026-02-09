# Pre-Action Coordination Feature

**Added:** January 2026
**Version:** 3.1

## Overview

Agents now **coordinate and deliberate BEFORE taking actions**, not just after. This creates more realistic decision-making where intelligence directors brief leaders, economic advisors voice concerns, and hawks debate with doves before the faction chooses its action.

---

## What Changed

### OLD Flow (v3.0)
```
1. External events
2. Action decision (single agent decides alone)
3. Action execution
4. Post-action discussion (react to what happened)
5. Aggregator assessment
```

**Problem**: No coordination, no debate, no information sharing before decisions.

### NEW Flow (v3.1)
```
1. External events
2. ✨ PRE-ACTION COORDINATION (all faction agents discuss)
3. Action decision (leader considers team input)
4. Action execution
5. Post-action discussion (react to results)
6. Aggregator assessment
```

**Benefit**: Realistic cabinet meetings, war councils, intelligence briefings before major decisions.

---

## How It Works

### Step 1: Pre-Action Coordination Meeting

**For each faction** (if 2+ agents):
1. All agents in the faction participate
2. **Topic**: "What action should we take this period?"
3. **Two rounds of discussion:**
   - Round 1: Each agent shares initial position
   - Round 2: Agents respond to each other's perspectives
4. Each agent contributes based on their role:
   - **Intelligence directors**: Share intel and threat assessments
   - **Military commanders**: Recommend military options
   - **Economic advisors**: Warn about costs and economic impacts
   - **Foreign ministers**: Suggest diplomatic alternatives
   - **Opposition leaders**: Question or support government's approach

### Step 2: Leader Decides

The faction leader (government > military > other) sees:
- Current situation
- Recent events
- **All coordination input** from their team

They then choose the action, influenced by:
- Their own worldview and hawk/dove orientation
- Their team's recommendations
- Conflicting perspectives within the faction

### Step 3: Action Executes

The chosen action takes effect with real consequences.

### Step 4: Post-Action Discussion

Agents react to what happened and coordinate responses.

---

## Example Coordination Session

```
MAJOR POWER FACTION - Pre-Action Coordination

Military Chief of Staff (hawk 0.8, realist worldview):
"We must continue the offensive. Enemy forces are degraded and morale is low.
 A full-scale attack now could secure the remaining territory within weeks.
 This is the time to press our advantage."

Economic Advisor (dove 0.3, pragmatic technocrat):
"I must warn that another major offensive will cost us $10B and further
 damage our economy already strained by sanctions. Can we afford this?
 Perhaps consolidation and negotiation from strength is wiser."

Intelligence Director (hawk 0.6, realist):
"Our intelligence shows the enemy is receiving increased military aid from
 Meridian. If we don't act quickly, the window closes. However, I'm concerned
 about covert retaliation if we escalate too aggressively."

Defense Minister (decision maker, hawk 0.7):
[Considers all input]
ACTION: full_scale_attack
TARGET: Tethys
REASONING: While mindful of economic costs, intelligence confirms this is
our best window. We'll accept the financial burden to achieve strategic
objectives before enemy reinforcements arrive.
```

---

## Research Benefits

### 1. Internal Faction Dynamics
- Do economic advisors actually restrain military hawks?
- How often do intelligence assessments change decisions?
- Can doves influence hawks within the same government?

### 2. Information Asymmetry Impact
- Does better intelligence access lead to better recommendations?
- Do leaders trust intelligence directors more than other advisors?
- How does information filtering affect decision quality?

### 3. Worldview Effects on Coordination
- Do realists and liberals reach consensus or deadlock?
- How do worldview clashes affect group cohesion?
- Can mixed-worldview teams make better decisions than homogeneous ones?

### 4. Policy Adherence Tensions
- Do low-policy-adherence agents (opposition) disrupt coordination?
- How do off-policy recommendations affect final decisions?
- Can internal dissent lead to better or worse outcomes?

### 5. Decision Quality Metrics
- Do coordinated decisions lead to better outcomes than unilateral ones?
- Is there "groupthink" in highly aligned factions?
- Do diverse teams catch more risks and opportunities?

---

## Data Outputs

### Coordination Records Saved

Each period, for each faction:

```r
state$pre_action_coordination[[period]][[faction]] <- list(
  faction = "major_power",
  topic = "STRATEGIC DECISION: What action should we take this period?",
  participants = c("Defense Minister", "Military Chief", "Economic Advisor", "Intel Director"),
  messages = list(
    list(
      sender_name = "Economic Advisor",
      sender_role = "economic",
      hawk_dove = 0.3,
      worldview = "pragmatic_technocrat",
      content = "...",
      round = 1
    ),
    ...
  )
)
```

### Analysis Possibilities

1. **Sentiment analysis** of coordination discussions
2. **Influence networks** - who persuades whom
3. **Consensus metrics** - how aligned are final positions
4. **Prediction accuracy** - do advisors correctly predict action outcomes
5. **Decision quality** - compare coordinated vs unilateral decisions

---

## Configuration

### Enable/Disable Coordination

Coordination is automatic if a faction has 2+ agents.

To disable (for comparison):
```r
# In agent_decision.R, modify run_action_decision_phase:
# Comment out the coordination section (lines 543-556)
```

### Adjust Discussion Length

In `interaction_engine.R`, modify `run_pre_action_coordination`:
```r
n_rounds <- 2  # Change to 1 (quick) or 3 (extended)
```

---

## Technical Details

### Files Modified

1. **`src/interaction_engine.R`** (+165 lines)
   - Added `run_pre_action_coordination()`
   - Added helper functions for coordination prompts

2. **`src/agent_decision.R`** (~50 lines changed)
   - Modified `run_action_decision_phase()` to run coordination first
   - Modified `agent_decide_action()` to accept coordination input
   - Added coordination records to state tracking

3. **`src/simulation_with_actions.R`** (+3 lines)
   - Added `state$pre_action_coordination` initialization

4. **`README.md`** (updated)
   - Documented new coordination flow

### Function Call Chain

```
run_simulation_period_with_actions()
  → run_action_decision_phase()
    → run_pre_action_coordination() [for each faction]
      → get_agent_response() [for each agent, 2 rounds]
    → agent_decide_action() [decision maker, with coordination input]
      → generate_action_decision_prompt() [includes coordination summary]
      → call_llm() [LLM chooses action]
    → execute_agent_decision() [action takes effect]
```

---

## Example Output

```
========== PERIOD 3 (Day 21) ==========

1. Generating external events...
  Generated 2 events
  - Commodity Price Shock: Oil prices surge
  - Battlefield Development: Defender counterattack succeeds

2. Action Decision & Execution Phase...

--- MAJOR POWER Faction Decision ---
  → Pre-action coordination within MAJOR POWER faction...
    Defense Minister: We must respond to the enemy counterattack with overwhelming force...
    Military Chief of Staff: I agree but recommend we secure our supply lines first...
    Economic Advisor: Oil price surge makes this operation 50% more expensive...
    Intelligence Director: My sources indicate enemy morale is actually strengthening...
  → Decision maker: Defense Minister
    Calling LLM for Defense Minister decision...
    ✓ Parsed action: military_buildup
  ✓ Action executed: military_buildup
  → Military strength increased, cost applied to GDP

--- SMALL POWER Faction Decision ---
  → Pre-action coordination within SMALL POWER faction...
    President: Our counterattack succeeded - should we press the advantage?
    Military Commander: Yes! Enemy is off balance, we can retake territory...
    Foreign Minister: Or use this as leverage for negotiations from strength...
    Opposition Leader: Domestic support is fragile, risky military gambles could topple us...
  → Decision maker: President
    Calling LLM for President decision...
    ✓ Parsed action: diplomatic_visit
  ✓ Action executed: diplomatic_visit
  → Strengthening alliance with Meridian
```

---

## Future Enhancements

### Possible Extensions

1. **Voting mechanism** - agents vote on action, not just advise
2. **Backchannel coordination** - secret communications between factions
3. **Coalition formation** - external actors coordinate joint actions
4. **Veto power** - certain roles can block specific actions
5. **Learning from outcomes** - agents adjust based on past coordination effectiveness

---

## Backwards Compatibility

- Old simulations without coordination still work
- Coordination is added as a new phase, doesn't break existing functionality
- If only 1 agent in faction, coordination is skipped (no change from before)

---

## Testing

To test the new coordination feature:

```bash
Rscript run_simulation_with_actions.R
```

Watch for:
- `→ Pre-action coordination within FACTION faction...` messages
- Agent names and brief input snippets
- `→ Decision maker: [NAME]` followed by action choice
- Coordination records in `state$pre_action_coordination`

---

**Feature Status**: ✅ **IMPLEMENTED and ACTIVE**

All simulations now include pre-action coordination by default.
