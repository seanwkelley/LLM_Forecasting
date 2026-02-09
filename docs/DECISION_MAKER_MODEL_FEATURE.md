# Decision Maker Model Configuration

**Date:** February 1, 2026
**Status:** ✅ Implemented
**Version:** v3.8.2

---

## Overview

The simulation now supports using a **different LLM model** for presidential approval decisions compared to other agent interactions. This allows you to:

1. **Optimize costs** - Use cheaper models for routine coordination, premium models for critical decisions
2. **Optimize quality** - Use more powerful reasoning models for the most important strategic choices
3. **Test model differences** - Compare how different models make high-stakes decisions

---

## Configuration

### In `config.R` (Lines 7-13)

```r
# Model selection
AGENT_MODEL <- "qwen/qwen3-235b-a22b-2507"  # For agent interactions and coordination
DECISION_MAKER_MODEL <- "qwen/qwen3-235b-a22b-2507"  # For presidential approval decisions
AGGREGATOR_MODEL <- "qwen/qwen3-235b-a22b-2507"  # For probability assessment
```

### Example Configurations

**Scenario 1: Premium reasoning for critical decisions**
```r
AGENT_MODEL <- "qwen/qwen3-235b-a22b-2507"  # Standard for coordination
DECISION_MAKER_MODEL <- "anthropic/claude-opus-4"  # Premium for approvals
AGGREGATOR_MODEL <- "qwen/qwen3-235b-a22b-2507"  # Standard for aggregation
```

**Scenario 2: Balanced performance**
```r
AGENT_MODEL <- "anthropic/claude-haiku-4"  # Fast/cheap for coordination
DECISION_MAKER_MODEL <- "anthropic/claude-sonnet-4"  # Balanced for approvals
AGGREGATOR_MODEL <- "anthropic/claude-haiku-4"  # Fast for aggregation
```

**Scenario 3: Mixed providers**
```r
AGENT_MODEL <- "qwen/qwen3-235b-a22b-2507"  # Qwen for coordination
DECISION_MAKER_MODEL <- "openai/gpt-4"  # OpenAI for approvals
AGGREGATOR_MODEL <- "anthropic/claude-sonnet-4"  # Claude for aggregation
```

**Scenario 4: Cost optimization**
```r
AGENT_MODEL <- "qwen/qwen3-70b"  # Smaller/cheaper for coordination
DECISION_MAKER_MODEL <- "qwen/qwen3-235b-a22b-2507"  # Larger for approvals
AGGREGATOR_MODEL <- "qwen/qwen3-70b"  # Smaller for aggregation
```

---

## How It Works

### Decision Maker LLM Calls (3 per period per faction)

1. **Pre-Action Coordination Round 1** → Uses `AGENT_MODEL`
   - Strategic discussion among domain experts

2. **Pre-Action Coordination Round 2** → Uses `AGENT_MODEL`
   - Debate and refinement of strategic priorities

3. **Presidential Approval Decision** → Uses `DECISION_MAKER_MODEL` ⭐
   - Final approve/veto/counter-propose decisions
   - Most critical decision point

### Implementation

**File:** `src/multi_action_system.R`
**Function:** `presidential_approval()`
**Line:** 268

```r
# Call LLM for approval decisions
response <- call_llm(system_prompt, approval_prompt, DECISION_MAKER_MODEL, api_key)
```

---

## When to Use Different Models

### Use Same Model (All three identical)
- **Testing purposes** - Isolate behavioral differences
- **Budget constraints** - Stick with one model tier
- **Simplicity** - Easier to interpret results

### Use Different Models

#### Higher Quality for Decision Maker
**When:** Critical decisions with high stakes
**Example:** Approval decisions that could trigger war escalation
**Benefit:** Better reasoning at the most important decision point

```r
AGENT_MODEL <- "qwen/qwen3-70b"  # $X per token
DECISION_MAKER_MODEL <- "anthropic/claude-opus-4"  # $XXX per token (10x cost, 10x reasoning)
```

#### Lower Cost for Coordination
**When:** Running many periods, need to optimize costs
**Example:** 50+ period simulations
**Benefit:** Save 2/3 of LLM costs (coordination is 2 of 3 calls)

```r
AGENT_MODEL <- "qwen/qwen3-70b"  # Cheap for discussion
DECISION_MAKER_MODEL <- "qwen/qwen3-235b-a22b-2507"  # Premium for decisions
```

---

## Cost Analysis Example

### Scenario: 10-period simulation, 2 factions

**Call breakdown:**
- Coordination calls: 10 periods × 2 factions × 2 rounds = **40 calls** (AGENT_MODEL)
- Approval calls: 10 periods × 2 factions × 1 decision = **20 calls** (DECISION_MAKER_MODEL)
- Aggregation calls: 10 periods × 1 per period = **10 calls** (AGGREGATOR_MODEL)

**Cost comparison:**

| Configuration | Coordination Cost | Approval Cost | Total Cost | Notes |
|--------------|------------------|---------------|------------|-------|
| All Qwen-235B | 40 × $0.X | 20 × $0.X | $Y | Baseline |
| Qwen-70B + Opus-4 | 40 × $0.05 | 20 × $5.00 | $102 | 10x reasoning where it matters |
| All Haiku | 40 × $0.02 | 20 × $0.02 | $1.20 | Ultra-cheap testing |
| Haiku + Sonnet | 40 × $0.02 | 20 × $0.50 | $10.80 | Balanced approach |

---

## Testing the Feature

### 1. Verify Configuration is Loaded

```r
source("config.R")
cat(sprintf("Agent model: %s\n", AGENT_MODEL))
cat(sprintf("Decision maker model: %s\n", DECISION_MAKER_MODEL))
cat(sprintf("Aggregator model: %s\n", AGGREGATOR_MODEL))
```

### 2. Check Console Output During Simulation

Look for the approval decision log:
```
    Calling LLM for approval decisions...
```

This line should now be using `DECISION_MAKER_MODEL`.

### 3. Compare Decision Quality

Run two simulations with different configurations:

**Test A:**
```r
AGENT_MODEL <- "qwen/qwen3-70b"
DECISION_MAKER_MODEL <- "qwen/qwen3-70b"
```

**Test B:**
```r
AGENT_MODEL <- "qwen/qwen3-70b"
DECISION_MAKER_MODEL <- "anthropic/claude-opus-4"
```

Compare the approval decisions in `period_XX_actions.csv`:
- Does Opus-4 show better strategic reasoning?
- Are counter-proposals more sophisticated?
- Do veto rationales reflect deeper analysis?

---

## Expected Behavior

### Same Model (No Difference)
- Consistent reasoning style across all phases
- Homogeneous decision quality
- Simplest to interpret

### Different Model (Quality Upgrade)
- Coordination discussions reflect AGENT_MODEL style
- Approval decisions reflect DECISION_MAKER_MODEL style
- You may see:
  - More nuanced counter-proposals
  - Deeper strategic rationales
  - Better recognition of risks/opportunities
  - More sophisticated game-theoretic reasoning

### Different Model (Cost Optimization)
- Coordination uses faster/cheaper model
- Approval uses standard/premium model
- Significant cost savings on high-volume simulations

---

## Files Modified

### 1. `config.R` (Lines 7-13)
Added `DECISION_MAKER_MODEL` configuration variable.

### 2. `src/multi_action_system.R` (Line 268)
Changed `presidential_approval()` to use `DECISION_MAKER_MODEL`:
```r
# Before:
response <- call_llm(system_prompt, approval_prompt, AGENT_MODEL, api_key)

# After:
response <- call_llm(system_prompt, approval_prompt, DECISION_MAKER_MODEL, api_key)
```

---

## Real-World Analogy

Think of this like organizational decision-making:

**AGENT_MODEL** = Department staff meetings
- Military staff discussing tactical options
- Economic advisors debating trade policy
- Intelligence analysts sharing assessments
- Standard professional competence required

**DECISION_MAKER_MODEL** = Presidential Cabinet meeting
- President/Prime Minister making final calls
- Highest stakes, most critical decisions
- May want your "best people" at this level
- Worth paying premium for superior judgment

**AGGREGATOR_MODEL** = Intelligence analysis fusion
- Combining multiple data sources
- Probability estimation and forecasting
- Can use specialized analytical capability

---

## Troubleshooting

### Issue: Same behavior despite different models

**Check:**
1. Did you restart R session after changing config.R?
2. Is the correct API key configured for the new model?
3. Are both models actually different, or same underlying model?

**Verify:**
```r
source("config.R")
print(DECISION_MAKER_MODEL)  # Should show the model you set
```

### Issue: API errors with new model

**Possible causes:**
- Model name typo (check OpenRouter model list)
- API key lacks permission for that model
- Model requires different provider (OpenAI vs Anthropic)

**Solution:**
```bash
# Test the model directly
curl https://openrouter.ai/api/v1/models | grep "your-model-name"
```

---

## Future Enhancements

Potential extensions of this feature:

1. **Domain-specific models**
   - Military proposals use military-tuned model
   - Economic proposals use economics-tuned model

2. **Faction-specific models**
   - Major power uses sophisticated model
   - Small power uses resource-constrained model

3. **Period-specific models**
   - Early periods use fast model (exploration)
   - Late periods use premium model (critical decisions)

4. **Dynamic model selection**
   - Escalation threshold triggers premium model
   - Routine decisions use standard model

---

## Summary

✅ **Implemented:** Decision maker can use different LLM model
✅ **Configured:** `DECISION_MAKER_MODEL` variable in config.R
✅ **Updated:** `presidential_approval()` function uses new model
✅ **Benefit:** Optimize cost/quality for most critical decisions

**Use this feature to:**
- Save money on coordination calls, spend on approval calls
- Test whether premium models make better strategic decisions
- Mix providers (Qwen coordination, Claude approvals, GPT aggregation)

---

**Version:** v3.8.2
**Date:** February 1, 2026
**Feature:** Separate LLM model for decision maker approval decisions
