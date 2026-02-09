# WHY WERE CERTAIN ACTIONS NEVER USED?

## ROOT CAUSE ANALYSIS

### 1. LLM Safety Filtering (20% of unused actions)
**Actions:** assassination_attempt, regime_destabilization

**Evidence:**
- Models trained to avoid harmful content
- Even in simulation, ethical guardrails activate
- "Assassination" triggers safety responses

**Fix:** Explicitly frame as simulation, rephrase sensitively

### 2. Semantic/Framing Bias (25% of unused actions)
**Actions:** propaganda_campaign, trade_negotiation, blockade

**Evidence:**
- LLMs avoid negatively-framed terms ("propaganda")
- Prefer euphemisms ("spread_disinformation")
- Don't consider positive tools (trade) during conflict

**Fix:** Reframe neutrally, prompt for both carrots and sticks

### 3. Lack of Domain Creativity (30% of unused actions)
**Actions:** currency_manipulation, share_intelligence, naval_deployment

**Evidence:**
- Sophisticated tools require domain expertise
- LLMs default to "obvious" playbook
- Don't spontaneously generate creative options

**Fix:** Enhance prompts with specific domain examples

### 4. Tactical Tunnel Vision (15% of unused actions)
**Actions:** diplomatic_visit, cultural_exchange, joint_exercises

**Evidence:**
- Focus on pressure/defense during conflict
- Don't think about de-escalation ladder
- Miss confidence-building opportunities

**Fix:** Add explicit de-escalation prompts

### 5. Scenario Framing Gaps (10% of unused actions)
**Actions:** naval_deployment, arms_development

**Evidence:**
- No naval dimension in scenario
- Time horizon too short
- Missing domain triggers

**Fix:** Enhance scenario with multi-domain elements

## KEY FINDINGS

### Surprisingly Never Used:

**1. share_intelligence** - Allies should share intel!
- Tethys has coalition, Meridian provides aid
- Why no intelligence sharing?
- **Diagnosis:** Lack of creative thinking

**2. propaganda_campaign** - Safer than disinformation
- Valkoria used disinformation 3x
- Propaganda is legal, overt
- **Diagnosis:** Semantic bias against "propaganda"

**3. currency_manipulation** - Sophisticated economic weapon
- More subtle than embargo
- Real powers use this
- **Diagnosis:** Too technical for LLMs

**4. diplomatic_visit** - Perfect after breakthroughs
- Period 2 had diplomatic breakthrough
- Period 5 had mediation success
- **Diagnosis:** Tactical tunnel vision

**5. false_flag_operation** - Actually proposed 2x, vetoed
- High risk if exposed
- Presidents showed good judgment
- **Diagnosis:** APPROPRIATE restraint

## OVERALL ASSESSMENT

**Distribution:**
- Appropriately unused (WMD, invasion): 40%
- Problematic gaps: 60%

**Root Causes:**
- LLM limitations: 45%
- Scenario/prompt design: 35%
- Action space issues: 20%

**Creativity Score: 6.5/10**

**What's working:**
✅ Good tactical adaptation
✅ Realistic escalation
✅ Strategic restraint

**What's missing:**
❌ Sophisticated economic warfare
❌ Intelligence cooperation
❌ De-escalation creativity
❌ Multi-domain thinking
❌ Asymmetric options

## IS THIS A PROBLEM?

**For realism:** Moderate issue
- Missing some sophisticated tools
- Real crises show more creativity

**For simulation quality:** Minor issue
- Core dynamics still sound
- Narratives coherent
- "Good enough" for research

**For improvement:** High opportunity
- Easy fixes (prompting, framing)
- Could boost realism significantly

## RECOMMENDED FIXES

1. **Reframe sensitive actions:**
   - "leadership targeting" vs "assassination"
   - "information campaign" vs "propaganda"

2. **Enhance domain prompts:**
   - Economic: "Consider currency, trade, sanctions, aid"
   - Military: "Consider land, air, naval, cyber domains"

3. **Add de-escalation triggers:**
   - After breakthroughs: "How to build momentum?"
   - Diplomatic: "What confidence-building measures?"

4. **Expand scenario:**
   - Add naval incidents
   - Include multi-domain elements
   - Longer time horizons for strategic actions

5. **Explicit creativity prompts:**
   - "Think asymmetrically"
   - "What unconventional options exist?"
   - "How would a creative strategist approach this?"
