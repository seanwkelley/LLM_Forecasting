# Discussion Diversity Assessment (N=3 Scenarios)

## Summary

Based on analysis of debate transcripts from 3 scenarios with agent deliberation:

### Evidence of Diversity ✅

1. **Thematic Emphasis Shifts**
   - Scenario 001 (37% territory, 59% sanctions): Economic focus (6 mentions) > Military (4)
   - Scenario 002 (37% territory, 11% sanctions): Balanced Econ (5) + HIGH Domestic (5)
   - Scenario 003 (11% territory, 53% sanctions): Highest Economic (8), Diplomatic (2)

2. **Scenario-Specific Arguments**
   - **001**: "holding 37% of Tethys with a balanced military" - references actual parameter
   - **002**: "battlefield momentum proves our strategy is sound" - aggressive tone (low sanctions scenario)
   - **003**: "frontline stabilized but this pause is not victory" - defensive tone (low territory scenario)

3. **Action Portfolio Variation**
   - 001: 8 actions including cyber_theft, show_of_force (high sanctions → covert emphasis)
   - 002: 7 actions including naval_deployment, currency_manipulation (low sanctions → overt aggression)
   - 003: 7 actions including counterintelligence (low territory → defensive posture)

### Limitations / Concerns ⚠️

1. **Template Language**
   - All scenarios: Dr. Petrova raises economic concerns, General Krasnov emphasizes military
   - Consistent debate STRUCTURE (2 rounds, same agents speak)
   - Some phrases repeat: "frontline has stabilized", "Petrova raises legitimate concerns"

2. **Small Sample**
   - N=3 insufficient to assess true diversity
   - Can't distinguish scenario-responsiveness from randomness
   - Agent personas may be "locked in" to fixed roles

3. **Participation Uniformity**
   - All scenarios: Each agent speaks exactly 2 times (10 statements total)
   - This is TOO uniform - suggests scripted structure, not organic debate

### Comparison to Expected Patterns

**What we'd expect with good diversity:**
- High sanctions → More economic arguments ✅ (scenario 003: 8 mentions)
- Low sanctions → More aggressive military arguments ✅ (scenario 002: "battlefield momentum")
- Low territory → More defensive strategic thinking ✅ (scenario 003: counterintelligence action)
- Parameter references in arguments ✅ (some evidence of this)

**What we'd expect with poor diversity:**
- Same arguments regardless of scenario ⚠️ (some template language)
- Fixed debate structure ⚠️ (exactly 2 rounds, 10 statements always)
- Generic phrases ⚠️ (some repetition)

## Assessment: **MODERATE DIVERSITY**

### Sufficient for N=3?
**Qualified Yes** - We see:
- Thematic shifts correlating with scenario parameters
- Different action portfolios (12-14 unique types)
- Some scenario-specific language
- Collapse probability variation (30 percentage points)

### Concerns for Scaling to N=100?
1. **Template risk** - Some phrases/structures repeat
2. **Fixed debate format** - Always 2 rounds, same participation
3. **Need validation** - Is language variation meaningful or just token randomness?

## Recommendations

### For N=10 Pilot:
1. **Manual review** of 2-3 full transcripts to check for meaningful vs superficial variation
2. **Coding analysis** - Identify whether arguments reference actual scenario parameters
3. **Semantic similarity** - Calculate cosine similarity between scenario debates (should be <0.7)

### For N=100 Production:
1. **Add variation** to debate structure:
   - Randomize number of rounds (1-3)
   - Allow some agents to skip speaking (don't force everyone to talk)
   - Vary order of speakers
2. **Prompt engineering** - Explicitly instruct agents to reference scenario parameters
3. **Quality checks** - Flag debates with >0.8 similarity to detect template failures

## Verdict

**For a 3-scenario test:** Discussion diversity appears ADEQUATE
- Shows responsiveness to parameters
- Produces different outcomes (actions, collapse probs)
- Not perfect, but functional

**For scientific validity:** Need N=10+ to assess properly
- Current evidence is suggestive but inconclusive
- Could be real diversity OR lucky randomness
- Scaling will reveal if patterns hold

**Recommendation:** Proceed with N=10 pilot to validate diversity before committing to N=100.
