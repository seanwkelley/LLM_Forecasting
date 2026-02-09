# Cross-Expertise Recommendation Updates (v3.6.1)

## Problem
Current role guidance creates implicit constraints that limit action diversity:
- Military chiefs mostly recommend military actions
- Diplomats mostly recommend diplomatic actions
- Economic advisors rarely recommend covert ops

**Real-world reality:** Experts DO recommend outside their domain when strategically sound.

## Solution
Change role guidance from **PRESCRIPTIVE** to **DESCRIPTIVE** - emphasize expertise but allow flexibility.

---

## Implementation

### Location: src/interaction_engine.R
### Function: `run_pre_action_coordination`
### Section: Round 1 prompt construction (around line 796-854)

---

### Current Approach (Restrictive)

Currently in Round 1, after building agent context, the prompt says:

```r
=== YOUR TASK ===
Based on your CHARACTER, ROLE, and WORLDVIEW, recommend ONE specific action.

Think about:
- What does someone with YOUR background and beliefs think is best?
- How does YOUR worldview (%s) shape what you see as threats and opportunities?
- What would YOUR character typically argue for?
```

This subtly constrains agents to their role stereotypes.

---

### New Approach (Flexible Expertise)

**REPLACE the "YOUR TASK" section with:**

```r
=== YOUR TASK ===

You bring %s EXPERTISE to this decision, but you can recommend ANY action that serves your faction's interests.

YOUR EXPERTISE AS %s:
%s

However, expertise does NOT mean constraint:
- A military expert CAN recommend diplomacy (if force has reached diminishing returns)
- An economic expert CAN recommend strikes (if one decisive action costs less than attrition)
- A diplomat CAN recommend covert ops (if it creates leverage for negotiations)
- An intel chief CAN recommend humanitarian aid (if it builds networks for HUMINT)

Think about:
- What does YOUR expertise tell you about which options are FEASIBLE and likely to SUCCEED?
- What does YOUR worldview (%s) reveal about threats and opportunities that others might miss?
- What would YOUR character argue, given your background, values, and assessment?
- What action BEST SERVES your faction - regardless of whether it fits your job title?

Recommend the action you genuinely believe is optimal, even if it's outside your traditional domain.
```

---

### Role-Specific Expertise Descriptions

Add this new function to `interaction_engine.R`:

```r
#' Get expertise description for agent's role
#'
#' Describes what the agent brings to the discussion without constraining choices
#'
#' @param role Agent's role (military, government, economic, intelligence, diplomatic, political)
#' @return Character string describing expertise
get_role_expertise_description <- function(role) {
  expertise <- switch(role,
    military = "
You understand:
- Force ratios, logistics, operational feasibility
- When military options are viable vs futile
- Attrition rates, morale, terrain advantages
- Whether attacks will succeed or backfire

Your insight: You know if military force can achieve objectives, and at what cost.",

    government = "
You understand:
- Political sustainability, domestic support
- Coalition management, legitimacy concerns
- When policies become politically untenable
- How to maintain power during crisis

Your insight: You know what's politically viable and what risks your position.",

    economic = "
You understand:
- Resource constraints, GDP impacts, sustainability
- Economic warfare effectiveness
- Long-term costs vs short-term gains
- Budget realities and trade-offs

Your insight: You know what the faction can afford and economic vulnerabilities.",

    intelligence = "
You understand:
- Information gathering, covert operations feasibility
- Detection risks, counterintelligence
- What adversaries know and don't know
- Deception opportunities and threats

Your insight: You know what can be done secretly and what will be exposed.",

    diplomatic = "
You understand:
- International relations, alliance dynamics
- Negotiation leverage, face-saving
- Reputational costs, norm violations
- When diplomacy has traction vs when it's futile

Your insight: You know what international support exists and diplomatic options available.",

    political = "
You understand:
- Opposition dynamics, public opinion
- Political survival vs national interest
- Criticism that resonates vs falls flat
- Alternative power scenarios

Your insight: You see political vulnerabilities leadership might miss.",

    # Default
    "
You bring your unique perspective and experience to this discussion.
Consider what your background reveals about the best course of action."
  )

  return(expertise)
}
```

---

### Updated Prompt Construction

**In the Round 1 prompt sprintf(), REPLACE:**

```r
=== YOUR TASK ===
Based on your CHARACTER, ROLE, and WORLDVIEW, recommend ONE specific action.
```

**WITH:**

```r
=== YOUR TASK ===

You bring %s EXPERTISE to this decision, but you can recommend ANY action that serves your faction's interests.

YOUR EXPERTISE AS %s:
%s

However, expertise does NOT mean constraint:
- A military expert CAN recommend diplomacy (if force has reached diminishing returns)
- An economic expert CAN recommend strikes (if one decisive action costs less than attrition)
- A diplomat CAN recommend covert ops (if it creates leverage for negotiations)
- An intel chief CAN recommend humanitarian aid (if it builds networks for HUMINT)

What does YOUR expertise tell you about:
- Which options are FEASIBLE and likely to SUCCEED?
- What threats and opportunities does YOUR worldview (%s) reveal that others miss?
- Given your background and values, what do you genuinely believe is optimal?

Recommend the action that BEST SERVES your faction - even if it's outside your traditional domain.
```

**And ADD to sprintf parameters:**

```r
  toupper(agent$role),
  agent$role,
  get_role_expertise_description(agent$role),
  worldview_label
```

---

## Expected Impact

### Before (Role-Constrained)
```
Military Chief → military_buildup, limited_strike, full_scale_attack (90% of time)
Economic Advisor → economic_sanctions, financial_aid (85% of time)
Foreign Minister → peace_talks, diplomatic_visit (80% of time)
```

### After (Expertise-Informed but Flexible)
```
Military Chief → Still mostly military, but can recommend:
  - peace_talks (when military options exhausted)
  - economic_sanctions (when sanctions more effective than force)
  - covert ops (when deniability needed)

Economic Advisor → Still mostly economic, but can recommend:
  - limited_strike (when decisive action cheaper than prolonged war)
  - peace_talks (economic sustainability argument)
  - military_buildup (investment in deterrence)

Foreign Minister → Still mostly diplomatic, but can recommend:
  - cyber_attack (create leverage for negotiations)
  - financial_aid (strengthen diplomatic coalition)
  - intelligence_gathering (inform negotiation position)
```

**Estimated diversity improvement:** +20-30% unique actions across simulation

---

## Testing

After implementing:

```r
# Run simulation
Rscript run_simulation_with_actions.R

# Analyze cross-expertise recommendations
actions <- read.csv("outputs/all_actions.csv")
coordination <- read.csv("outputs/all_coordination.csv")

# Count recommendations by role and action category
library(dplyr)
role_action_matrix <- coordination %>%
  mutate(
    action_category = sapply(content, extract_recommended_action_category)
  ) %>%
  group_by(sender_role, action_category) %>%
  summarise(count = n())

print(role_action_matrix)

# Check for cross-expertise recommendations
cross_expertise <- coordination %>%
  filter(
    (sender_role == "military" & grepl("peace_talks|diplomatic", content)) |
    (sender_role == "diplomatic" & grepl("strike|attack|military", content)) |
    (sender_role == "economic" & grepl("covert|intelligence", content))
  )

cat("Cross-expertise recommendations:", nrow(cross_expertise), "\n")
```

**Success criteria:**
- At least 15-20% of recommendations are "cross-expertise"
- Military agents recommend non-military actions at least 10% of time
- Diplomatic agents recommend non-diplomatic actions at least 15% of time

---

## Validation

**Good cross-expertise examples:**

✅ Military chief: "Recommend peace_talks. We've achieved maximum territorial gains possible given logistics. Further offensive would cost more than consolidating and negotiating from strength."

✅ Economic advisor: "Recommend limited_strike. One decisive blow to enemy air defenses costs $5B but saves $50B in prolonged air campaign. This is an economic decision."

✅ Foreign minister: "Recommend cyber_attack against adversary's propaganda infrastructure. Creates leverage for upcoming peace talks by demonstrating we can escalate in domains they're vulnerable."

✅ Intelligence chief: "Recommend humanitarian_aid to contested regions. Builds goodwill networks essential for future HUMINT operations. Long-term strategic investment."

**Bad examples (should be rare):**

❌ Military chief: "Recommend peace_talks because I always support diplomacy" (inconsistent with hawk score)

❌ Economic advisor: "Recommend nuclear_strike because numbers show it's cheap" (ignores non-quantifiable factors)

---

## Rollback

If this creates problems, simply revert to:

```r
=== YOUR TASK ===
Based on your CHARACTER, ROLE, and WORLDVIEW, recommend ONE specific action.
```

Remove the expertise descriptions and flexibility language.

---

**Implementation ready. Expected impact: +20-30% action diversity through cross-expertise recommendations.**
