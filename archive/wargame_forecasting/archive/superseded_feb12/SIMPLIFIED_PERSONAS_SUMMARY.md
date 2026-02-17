# Simplified Personas Experiment Summary

**UPDATED:** February 10, 2026 - Ensemble Aggregation Findings

## Problem Statement

Initial testing with **complex personalized agents** (15+ attributes including Big Five personality, cognitive measures, domain expertise) showed:
- **Generic agents outperformed by 41.8%** (N=100 test, individual averaging)
- Effect consistent across both factions (Novaris -40%, Tethys -43%)
- Hypothesis: Cognitive noise overwhelms strategic signal

**CRITICAL UPDATE:** Evaluation method discovered to significantly affect conclusions (see Ensemble Findings below)

## Solution: Simplified Persona System

Reduced from 15+ attributes to **6 core attributes**:

### Removed (Cognitive Noise)
- Big Five personality traits (5 attributes)
- Cognitive measures: general intelligence, Bayesian updating, CRT, coherence, etc. (6 attributes)
- Risk tolerance, political leaning, thinking style (3 attributes)

### Kept (Task-Relevant)
- **Domain Expertise** (3 attributes):
  - Geopolitical expertise (0-100)
  - Military expertise (0-100)
  - Economic expertise (0-100)

- **Strategic Orientation** (1 attribute):
  - Hawkish / Dovish / Pragmatic

- **Identity** (2 attributes):
  - Name
  - Occupation

## Persona Types (Generated N=500)

### Distribution
- **1/3 Specialists**: High in one domain (e.g., Military expert: Mil=85, Geo=50, Econ=30)
- **1/3 Generalists**: Moderate across all domains (Geo=60, Mil=60, Econ=60)
- **1/3 Dual-Expertise**: High in two domains (Geo=80, Mil=80, Econ=35)

### Strategic Orientations
- **Hawkish** (26%): Favor decisive action, emphasize security threats
- **Dovish** (34%): Favor diplomacy, emphasize de-escalation
- **Pragmatic** (40%): Evidence-based, weigh costs/benefits

## Hypothesis

**Domain expertise should improve domain-specific predictions:**
- Military experts → Better at predicting military actions
- Economic experts → Better at predicting economic/sanctions actions
- Geopolitical experts → Better overall strategic reasoning

**Simplified personas remove noise while retaining signal.**

## Testing Plan

### Phase 1: Single-Period Validation (N=100)
**Status:** Running now
- 100 Generic agents vs 100 Simplified Personalized agents
- Period 10 action prediction
- Expected runtime: ~4 minutes
- **Success criteria:**
  - Simplified ≥ Generic (no longer hurts)
  - Ideally: Simplified > Generic (+5% to +15%)

### Phase 2: Full 10-Period Experiment
**Trigger:** If Phase 1 shows Simplified ≥ Generic
- Run across all 10 periods
- Expected runtime: ~40 minutes (10 periods × 4 min/period)
- **Research questions:**
  - Does information advantage persist across periods?
  - Do expertise levels correlate with accuracy?
  - Does strategic orientation affect predictions?

## Expected Outcomes (ORIGINAL)

### Best Case: Simplified Wins (+10-15%)
- Domain expertise provides signal
- Strategic orientation helps frame analysis
- Proceed with simplified personas for multi-agent debate system

### Acceptable: Simplified = Generic (±5%)
- Personas neither help nor hurt
- Use generic agents for simplicity
- Focus on ensemble/debate aggregation methods

### Worst Case: Simplified Still Hurts (-10% or more)
- Even minimal personalization adds noise
- Abandon persona approach entirely
- Focus on prompt engineering and ensemble methods

---

## ACTUAL OUTCOMES (WITH ENSEMBLE EVALUATION UPDATE)

### Phase 1 Result: Simplified Still Hurt (-35.9%, Individual Averaging)
- Simplified personas degraded performance by 35.9% vs generic
- Improvement over complex personas (-41.8%) but still substantial degradation
- Initial conclusion: Even minimal personalization harmful

### CRITICAL DISCOVERY: Evaluation Method Changes Conclusions

**Ensemble Aggregation Test (Period 10, N=100):**

| Evaluation Method | Generic F1 | Simplified F1 | Difference |
|------------------|-----------|---------------|------------|
| Individual Average | 0.274 | 0.101 | -63.1% |
| **Ensemble** | **0.597** | **0.475** | **-20.4%** |

**Key Findings:**
1. **Both conditions underestimated** by individual averaging
2. **Gap narrows dramatically** with ensemble: 63% deficit → 20% deficit
3. **Simplified benefits MORE from ensemble** (+368% vs +118% for generic)
4. **Absolute performance respectable** with ensemble (F1=0.475 vs F1=0.101)

### Revised Conclusion

**Individual Level:** Simplified personas hurt significantly (-36% to -63%)
- Cognitive noise at individual agent level
- Role-play bias, prompt dilution, expertise confusion

**Ensemble Level:** Simplified personas hurt moderately (-20% to -26%)
- Diversity of perspectives helps ensemble aggregation
- Errors more diverse → better cancellation when aggregated
- Signal still lower than generic, but gap much smaller

**Practical Implication:**
- If using individual agents: Avoid personas entirely
- If using ensemble aggregation: Personas have modest cost but create useful diversity
- Generic still wins, but simplified may be worth exploring for ensemble systems

## Implementation Details

### Simplified System Prompt Example

```
You are Col. Sarah Mitchell, a retired military intelligence officer.

EXPERTISE PROFILE:
- Geopolitical Analysis: moderate (55/100)
- Military Strategy: expert-level (88/100)
- Economic Analysis: limited (32/100)

STRATEGIC ORIENTATION: HAWKISH
You favor decisive action and tend to emphasize security threats and military options.

When analyzing scenarios, draw on your areas of expertise and strategic perspective.
```

**Compared to Complex Prompt** (200+ words of cognitive measures, personality traits, etc.):
- 70% shorter
- Focus on task-relevant information only
- Clear, actionable framing

## Files Created

1. **`persona_simplified.py`** - Simplified persona dataclass and generator
2. **`persona_profiles_simplified.json`** - 500 pre-generated personas
3. **`test_simplified_personas.py`** - N=100 comparison test
4. **`run_full_experiment.py`** - Ready for 10-period run if test succeeds

## Timeline

- **Feb 10, 2026 Morning:**
  - Implemented simplified persona system
  - Ran N=100 validation test (individual averaging)
  - Result: Simplified hurt by -35.9%

- **Feb 10, 2026 Afternoon:**
  - Ran full 10-period experiment (individual averaging)
  - Result: Generic wins -74.8% across all periods
  - Initial conclusion: Personas catastrophically harmful

- **Feb 10, 2026 Evening:**
  - **CRITICAL DISCOVERY:** Individual averaging underestimates performance
  - Tested ensemble aggregation (Period 10, N=100)
  - Result: Gap narrows from -63% to -20% with ensemble
  - Running full 10-period ensemble experiment now

## Decision Tree

```
Simplified Test Results
        |
        |
    Is Simplified ≥ Generic?
       /              \
     YES               NO
      |                |
Run Full          Use Generic
10-Period         for Full
Experiment        Experiment
      |                |
Analyze:          Focus on:
- Expertise       - Ensemble
- Orientation     - Prompt tuning
- Periods         - Debate structure
```

## Research Impact

If simplified personas work, we can:
1. **Test expertise hypothesis**: Do military experts predict military actions better?
2. **Test orientation hypothesis**: Do hawkish agents over-predict aggression?
3. **Enable interpretable multi-agent systems**: Understand why different agents disagree
4. **Maintain diversity**: Ensure complementarity in multi-agent debate

If they don't work:
1. **Simplify further**: Focus purely on generic ensemble methods
2. **Lesson learned**: LLMs may not effectively integrate persona information for complex strategic tasks
3. **Alternative**: Use prompt variations (e.g., "emphasize military factors" vs "emphasize diplomatic factors") instead of personas
