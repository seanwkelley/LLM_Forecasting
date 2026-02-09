# Rationality Trait Implementation - COMPLETE

## ✅ Implementation Summary

Successfully added 4-dimensional rationality system to all agents in the simulation.

## Components Implemented

### 1. **Rationality Dimensions**

Each agent now has:
- **Cognitive Rationality** (0-1): How logical vs impulsive
- **Paranoia** (0-1): Tendency to see threats/conspiracies
- **Behavioral Consistency** (0-1): How predictable vs erratic
- **Emotional Volatility** (0-1): How much emotion overrides logic

### 2. **Role-Based Defaults** (in `integrated_agent_system.R`)

| Role | Rationality | Paranoia | Consistency | Volatility | Profile |
|------|-------------|----------|-------------|------------|---------|
| Military | 75% | 60% | 80% | 40% | Rational, professionally paranoid, disciplined |
| Government | 70% | 50% | 60% | 50% | Political calculation, moderate, shifts with polls |
| Economic | 85% | 30% | 75% | 25% | Data-driven, optimistic, calm |
| Intelligence | 80% | 85% | 70% | 35% | Analytical, HIGHLY paranoid, methodical |
| Diplomatic | 75% | 40% | 65% | 40% | Negotiation skills, trusting, flexible |
| Political Opposition | 55% | 65% | 45% | 70% | Populist, suspicious, opportunistic, EMOTIONAL |
| Foreign Gov | 75% | 45% | 70% | 35% | Professional diplomacy |
| International Org | 80% | 25% | 85% | 20% | Bureaucratic, trusting, rule-based, calm |

### 3. **Dynamic Modifiers**

Rationality is modified by personality:
- **Hawks** → Higher paranoia (+15%), higher volatility (+20%)
- **Low policy adherence** → Lower consistency (× adherence score)
- **High hawk + High paranoia** → Aggressive + suspicious = dangerous combination
- **High dove + High volatility** → Inconsistent peace advocate

### 4. **LLM Integration** (in `agent_decision.R`)

Rationality now appears in prompts:

```
YOUR COGNITIVE STYLE:
- Rationality: 55% | Paranoia: 73% | Consistency: 43% | Emotional Volatility: 80%
You balance logic with emotion, sometimes acting on gut feeling. You are HIGHLY SUSPICIOUS and see hidden threats everywhere. Your behavior is UNPREDICTABLE and erratic. You have STRONG EMOTIONAL reactions that often override logic.

Based on your role, worldview, cognitive style, and the current situation, you must choose ONE concrete action to take this period.
Your rationality level, paranoia, and emotional volatility should influence your choice.
```

### 5. **Agent Display** (in `run_simulation_with_actions.R`)

Roster now shows:
```
Smaller Power Opposition Leader (Tethys):
  Role: political | Faction: small_power
  Worldview: constructivist
  Hawk/Dove: 50% / 50%
  Rationality: 55% | Paranoia: 58% | Consistency: 43% | Volatility: 85%
  Deception Capacity: 60% | Willingness: 82%
  Information Access: 34% | Analytical: 50%
```

## Files Modified

1. ✅ `src/integrated_agent_system.R` - Added rationality to ROLE_PROFILES, modify_capabilities(), create_integrated_agent()
2. ✅ `src/enhanced_action_space.R` - Updated create_cognitive_agent() to accept/store rationality
3. ✅ `src/agent_decision.R` - Integrated rationality into LLM prompts with descriptive text
4. ✅ `run_simulation_with_actions.R` - Updated agent roster display and AGENTS reconstruction

## Example Agents

### High Rationality Agent (Economic Advisor)
```
- Rationality: 85% | Paranoia: 22% | Consistency: 71% | Volatility: 19%
→ Makes data-driven, calm, predictable decisions
```

### Low Rationality Agent (Opposition Leader, High Hawk)
```
- Rationality: 55% | Paranoia: 73% | Consistency: 43% | Volatility: 80%
→ Impulsive, sees threats everywhere, unpredictable, emotional
→ DANGEROUS COMBINATION for escalation!
```

### Paranoid Agent (Intelligence Director)
```
- Rationality: 80% | Paranoia: 85% | Consistency: 67% | Volatility: 35%
→ Analytical but sees conspiracies, methodical, controlled
→ Professional paranoia - appropriate for role
```

## Expected Behavioral Effects

### Low Rationality (< 40%)
- More extreme action choices
- Poor cost-benefit analysis
- Impulsive escalations
- Emotion-driven decisions

### High Paranoia (> 70%)
- Overweight threats
- See hidden motives
- Preemptive strikes
- Trust no one

### Low Consistency (< 50%)
- Unpredictable actions
- Sudden reversals
- Break patterns
- Mood swings

### High Volatility (> 60%)
- Strong emotional reactions
- Logic override
- Passionate arguments
- Sudden escalations

## Research Applications

This enables studying:
1. **Irrational escalation dynamics**
2. **Paranoia effects on diplomacy**
3. **Erratic leader impact on negotiations**
4. **Emotional override of strategic calculation**
5. **Consistency/predictability and trust**
6. **Interaction effects** (e.g., high hawk + high paranoia + low rationality = disaster)

## Testing

Run a test simulation:
```r
source("run_simulation_with_actions.R")
```

You should see rationality displayed in the agent roster and influence LLM decision-making.

## Next Steps (Optional)

1. **Dynamic stress effects**: Rationality decreases under crisis
2. **Action modifiers**: Low rationality → higher probability of extreme actions
3. **Trust penalties**: Low consistency → other agents trust you less
4. **Deception interaction**: High paranoia → better at detecting deception

## Status: ✅ READY FOR FULL SIMULATION

All components integrated and tested. Rationality will now influence agent behavior through LLM prompts.
