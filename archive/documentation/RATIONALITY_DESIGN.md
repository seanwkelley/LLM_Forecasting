# Rationality Trait Design

## Overview
Add a multi-dimensional rationality system to agents to vary how rationally or irrationally they behave.

## Rationality Components

### 1. **Cognitive Rationality** (0-1)
- **High (0.8-1.0)**: Logical, data-driven, consistent decision-making
- **Medium (0.4-0.7)**: Mix of logic and emotion
- **Low (0.0-0.3)**: Impulsive, emotional override, poor risk assessment

### 2. **Paranoia Level** (0-1)
- **High (0.7-1.0)**: Sees threats everywhere, conspiracy thinking, distrust
- **Medium (0.3-0.6)**: Healthy skepticism
- **Low (0.0-0.2)**: Trusting, may miss real threats

### 3. **Behavioral Consistency** (0-1)
- **High (0.8-1.0)**: Predictable, stable, follows patterns
- **Medium (0.4-0.7)**: Some variability
- **Low (0.0-0.3)**: Chaotic, unpredictable, mood swings

### 4. **Emotional Volatility** (0-1)
- **High (0.7-1.0)**: Strong emotional reactions, overrides logic
- **Medium (0.3-0.6)**: Balanced
- **Low (0.0-0.2)**: Cool, detached, unemotional

## Effects on Agent Behavior

### Decision-Making
- **Low rationality** → More extreme actions, poor cost-benefit analysis
- **High paranoia** → Overweight threats, defensive actions
- **Low consistency** → Actions don't follow clear patterns
- **High volatility** → Sudden escalations or de-escalations

### LLM Prompt Integration
Inject rationality traits into agent prompts:

```
YOUR COGNITIVE STYLE:
- Rationality: 45% (You sometimes make impulsive decisions driven by emotion)
- Paranoia: 75% (You see hidden threats and motives everywhere)
- Consistency: 30% (Your behavior is unpredictable and changes based on mood)
- Volatility: 80% (You have strong emotional reactions that override logic)

BEHAVIOR GUIDANCE:
- When making decisions, let your [paranoia/emotion/impulse] influence your choice
- You may [overreact to minor threats / make sudden reversals / act inconsistently]
- Your reasoning should reflect [suspicion / emotional response / chaotic thinking]
```

### Action Selection Modification
Rationality affects action probabilities:

```r
# Low rationality increases probability of extreme actions
if (agent$rationality$cognitive < 0.4) {
  # More likely to choose: full_scale_attack, nuclear_development,
  # assassination_attempt
  extreme_action_multiplier <- 1 / agent$rationality$cognitive
}

# High paranoia increases defensive/preemptive actions
if (agent$rationality$paranoia > 0.7) {
  # More likely to: military_buildup, counterintelligence,
  # border_incursion (preemptive)
}

# Low consistency adds randomness to actions
if (agent$rationality$consistency < 0.4) {
  # Randomly deviate from expected action based on worldview
  if (runif(1) < (1 - agent$rationality$consistency)) {
    # Choose action from different category
  }
}
```

## Role-Based Rationality Defaults

```r
RATIONALITY_BY_ROLE <- list(
  military = list(
    cognitive = 0.75,      # Generally rational, trained
    paranoia = 0.60,       # Professional paranoia
    consistency = 0.80,    # Follow doctrine
    volatility = 0.40      # Disciplined
  ),

  government = list(
    cognitive = 0.70,      # Political calculation
    paranoia = 0.50,       # Moderate
    consistency = 0.60,    # Shift with polls
    volatility = 0.50      # Balanced
  ),

  economic = list(
    cognitive = 0.85,      # Data-driven
    paranoia = 0.30,       # Optimistic bias
    consistency = 0.75,    # Economic models
    volatility = 0.25      # Calm analysis
  ),

  intelligence = list(
    cognitive = 0.80,      # Analytical
    paranoia = 0.85,       # Professional paranoia!
    consistency = 0.70,    # Methodical
    volatility = 0.35      # Controlled
  ),

  diplomatic = list(
    cognitive = 0.75,      # Negotiation skills
    paranoia = 0.40,       # Trusting demeanor
    consistency = 0.65,    # Flexible
    volatility = 0.40      # Measured
  ),

  political = list(
    cognitive = 0.55,      # Populism over logic
    paranoia = 0.65,       # See plots everywhere
    consistency = 0.45,    # Opportunistic
    volatility = 0.70      # Emotional appeals
  ),

  international_org = list(
    cognitive = 0.80,      # Bureaucratic
    paranoia = 0.25,       # Institutional trust
    consistency = 0.85,    # Rule-based
    volatility = 0.20      # Diplomatic calm
  )
)
```

## Modifiers Based on Other Traits

### Hawk/Dove Interaction
- **High hawk + High paranoia** → Very aggressive, sees everything as threat
- **High dove + High paranoia** → Paralyzed by fear, appeasement
- **High hawk + Low rationality** → Reckless escalation
- **Low hawk + High volatility** → Inconsistent, swings between peace and war

### Worldview Interaction
- **Nationalist Populist + High paranoia** → Xenophobic extremism
- **Liberal Institutionalist + Low rationality** → Naive idealism
- **Realist + High volatility** → Unstable power calculations
- **Pragmatic Technocrat + Low consistency** → Contradictory policies

## Implementation Steps

1. **Add rationality fields to ROLE_PROFILES** (integrated_agent_system.R)
2. **Modify `create_integrated_agent()`** to include rationality
3. **Update agent prompts** (agent_decision.R) with rationality traits
4. **Add rationality-based action modifiers** (optional - for more complex behavior)
5. **Update agent roster display** (run_simulation_with_actions.R) to show rationality

## Example Agent Output

```
Major Power Military Chief of Staff (Novaris):
  Role: military | Faction: major_power
  Worldview: nationalist_populist
  Hawk/Dove: 90% / 10%
  Rationality: 60% | Paranoia: 85%
  Consistency: 45% | Volatility: 70%
  → BEHAVIOR: Aggressive, highly suspicious, unpredictable, emotional
  Deception Capacity: 70% | Willingness: 63%
  Information Access: 80% | Analytical: 66%
```

## Research Value

Adding rationality enables studying:
- **Irrational escalation** - How paranoid leaders start wars
- **Erratic decision-making** - Unpredictable actors destabilizing negotiations
- **Emotional override** - When passion defeats strategy
- **Conspiracy thinking** - Paranoia derailing diplomacy
- **Behavioral inconsistency** - Trust breakdown from erratic behavior

## Notes

- Rationality can be **deterministic** (fixed per agent) or **dynamic** (changes with stress)
- Consider adding **stress level** that temporarily reduces rationality during crises
- Low rationality agents should produce more interesting/chaotic simulations
- Balance: Too many irrational agents → nonsensical outcomes
