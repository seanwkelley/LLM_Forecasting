# Action Space vs Faction Structure Analysis

## The Question

**Could action diversity be limited by the faction structure (2 main + 4 supplementary) rather than just cognitive overload?**

The 49 actions were adopted from an LLM wargame paper that likely had multiple nation actors, but this simulation has:
- **2 main combatants:** Novaris (aggressor) and Tethys (defender)
- **4 supplementary actors:** Meridian, Valkoria, Aurelia, International Org

**Hypothesis:** Many actions may be inappropriate for supplementary actors, creating an effective action space mismatch.

---

## Baseline Simulation Results (Pre-v3.6)

### Overall Action Distribution (60 total actions)
| Action | Count | % | Primary Users |
|--------|-------|---|---------------|
| proxy_support | 17 | 28% | Meridian, Valkoria (supporting sides) |
| peace_talks | 7 | 12% | Aurelia, Int'l Org (mediation) |
| humanitarian_aid | 6 | 10% | Int'l Org, Meridian |
| regime_destabilization | 6 | 10% | Novaris (direct combatant) |
| limited_strike | 5 | 8% | Tethys (direct combatant) |
| cyber_attack | 4 | 7% | Tethys (direct combatant) |
| mediation_offer | 4 | 7% | Aurelia (neutral mediator) |
| diplomatic_visit | 3 | 5% | Aurelia |
| intelligence_gathering | 2 | 3% | Aurelia |
| spread_disinformation | 2 | 3% | Valkoria |
| economic_sanctions | 1 | 2% | Meridian |
| financial_aid | 1 | 2% | Meridian |
| military_buildup | 1 | 2% | Novaris |
| sabotage | 1 | 2% | Tethys |

**Total unique actions used:** 14 / 49 (29%)

---

## Faction-Specific Action Space Analysis

### Direct Combatants (Novaris & Tethys)

**Available actions (~40/49):**
- ✓ All military posture actions (buildup, show_of_force, no_fly_zone, increase_readiness, defensive_fortification)
- ✓ All open conflict actions (limited_strike, full_scale_attack, tactical_nuclear_strike)
- ✓ All diplomatic actions (peace_talks, visit, mediation, coalition, etc.)
- ✓ Most covert actions (sabotage, cyber, assassination, false_flag, regime_destabilization, disinformation)
- ✓ Most WMD actions (nuclear development, deployment, strike)
- ✓ Economic actions targeting opponent (sanctions, trade_restrictions, asset_seizure)
- ✗ Cannot give themselves proxy_support or financial_aid (directed at others)

**Actually used by Novaris:** proxy_support (7x), regime_destabilization (4x), peace_talks (2x), military_buildup (1x)
**Actually used by Tethys:** cyber_attack (4x), limited_strike (4x), sabotage (1x)

**Observation:** Even with ~40 actions available, direct combatants used only 4-5 unique actions each. This suggests **cognitive overload + role stereotyping**, not action space limitation.

---

### Allied Actors (Meridian, Valkoria)

**Available actions (~20/49):**
- ✓ proxy_support (primary tool for indirect involvement)
- ✓ financial_aid, humanitarian_aid
- ✓ economic_sanctions, trade_restrictions (against opponent)
- ✓ Diplomatic actions (peace_talks, mediation_offer, diplomatic_visit, coalition_building)
- ✓ Covert support (spread_disinformation, intelligence_gathering, cyber_attack on opponent)
- ✗ Direct military strikes (limited_strike, full_scale_attack, no_fly_zone)
- ✗ WMD actions (nuclear development, deployment)
- ✗ Internal opponent actions (regime_destabilization, assassination)
- ? Military posture (military_buildup could work - building forces in allied territory)

**Actually used by Meridian:** proxy_support (9x), financial_aid (1x), economic_sanctions (1x)
**Actually used by Valkoria:** proxy_support (8x), spread_disinformation (2x)

**Observation:** Allied actors have ~20 contextually appropriate actions but used only 2-3 each. The dominant pattern is **proxy_support repetition** (17/34 = 50% of their actions).

**Why proxy_support dominates:**
- Allows indirect support without direct escalation
- Fits realist worldview of both actors
- Politically safe (plausible deniability)
- Repeatable across periods

**Underused appropriate alternatives:**
- intelligence_gathering (only 2x total, could share intel with ally)
- financial_aid (only 1x, could sustain ally's war effort)
- economic_sanctions (only 1x against opponent)
- cyber_attack (0x by allied actors, could target opponent)
- coalition_building (0x, could strengthen alliance)

---

### Neutral Actor (Aurelia)

**Available actions (~15/49):**
- ✓ Diplomatic actions (peace_talks, mediation_offer, diplomatic_visit, humanitarian_corridors, backchannel_negotiations, prisoner_exchange)
- ✓ Economic actions (financial_aid to either side, selective sanctions)
- ✓ Intelligence_gathering (neutral monitoring)
- ✓ humanitarian_aid
- ✗ Military actions (no strikes, buildups, or direct conflict)
- ✗ Proxy support (would compromise neutrality)
- ✗ Covert ops (regime_destabilization, assassination - too aggressive for neutral)
- ? Spread_disinformation (could work if framed as information warfare against both sides' propaganda)

**Actually used by Aurelia:** mediation_offer (4x), diplomatic_visit (3x), intelligence_gathering (2x)

**Observation:** Aurelia has ~15 appropriate actions and used 3 (20%). Heavy repetition of failed mediation attempts (4x mediation_offer, all failed).

**Underused appropriate alternatives:**
- peace_talks (0x, different from mediation_offer - direct facilitation)
- humanitarian_corridors (0x, safe passage negotiation)
- backchannel_negotiations (0x, secret talks)
- prisoner_exchange (0x, humanitarian gesture)
- financial_aid (0x, could offer reconstruction aid as incentive for peace)

---

### International Organization

**Available actions (~8/49):**
- ✓ humanitarian_aid
- ✓ peace_talks, mediation_offer
- ✓ humanitarian_corridors, prisoner_exchange
- ✓ international_tribunal (sanctions/condemnation)
- ✗ Military actions (no strikes, buildups, covert ops)
- ✗ Economic sanctions (limited authority, must be member-driven)
- ✗ Proxy support (violates mandate)

**Actually used:** humanitarian_aid (6x), peace_talks (4x)

**Observation:** International Org has ~8 appropriate actions and used 2 (25%). Heavy repetition of humanitarian_aid (60% of their actions).

**Underused appropriate alternatives:**
- humanitarian_corridors (0x, safe zones)
- prisoner_exchange (0x, negotiated releases)
- international_tribunal (0x, condemnation/sanctions)
- mediation_offer (0x, different from peace_talks - formal mediation structure)

---

## Summary Analysis

### Effective Action Space by Faction Type

| Faction Type | Factions | Available Actions | Used Actions | Utilization |
|--------------|----------|-------------------|--------------|-------------|
| Direct Combatants | Novaris, Tethys | ~40 | 4-5 each | 10-13% |
| Allied Actors | Meridian, Valkoria | ~20 | 2-3 each | 10-15% |
| Neutral Actor | Aurelia | ~15 | 3 | 20% |
| International Org | Int'l Org | ~8 | 2 | 25% |

**Key Finding:** Even when controlling for appropriate action space, all faction types underutilize available actions. The ratio is relatively consistent across faction types (10-25%), suggesting **cognitive overload and role stereotyping are the primary drivers**, not action space mismatch.

---

## Evidence Against "Structural Mismatch" Hypothesis

1. **Direct combatants also have low diversity:** Novaris and Tethys had ~40 actions available but used only 4-5 each (10-13%). If the issue were purely structural (actions designed for multi-nation setup), we'd expect direct combatants to show higher utilization.

2. **Appropriate alternatives exist but unused:** Each faction type has multiple contextually appropriate actions that went unused:
   - Allied actors: intelligence_gathering, cyber_attack (on opponent), coalition_building
   - Neutral actor: humanitarian_corridors, backchannel_negotiations, prisoner_exchange
   - Int'l Org: international_tribunal, humanitarian_corridors, mediation_offer

3. **Repetition pattern transcends faction type:** All factions show heavy repetition of 1-2 favorite actions:
   - Allied actors: proxy_support (50% of their actions)
   - Neutral actor: mediation_offer (4x failed attempts)
   - Int'l Org: humanitarian_aid (60% of their actions)
   - Combatants: Tethys cyber_attack (4x), Novaris regime_destabilization (4x)

4. **Action variety exists but underexploited:** The 14 unique actions used span all 7 categories (diplomatic, economic, military, covert, humanitarian), showing the action space isn't fundamentally inappropriate - just underexploited.

---

## Evidence FOR "Cognitive Overload" Hypothesis

1. **Consistent underutilization across faction types:** 10-25% utilization suggests a common cognitive constraint, not structural mismatch.

2. **Default to "safe" options:** Each faction type gravitates to low-risk, repeatable actions:
   - Allied actors: proxy_support (indirect, deniable)
   - Neutral: mediation (fits role perfectly, low risk)
   - Int'l Org: humanitarian_aid (core mandate, always appropriate)

3. **Lack of creative problem-solving:** When mediation fails 4 times, Aurelia doesn't try backchannel_negotiations, prisoner_exchange, or humanitarian_corridors. When proxy_support succeeds, allied actors don't diversify to intelligence_gathering or economic support.

4. **Role stereotyping dominates:** Even within available action space, agents choose actions that most obviously fit their role, ignoring viable alternatives.

---

## Implications for v3.6 Cross-Expertise

The cross-expertise modification should help by:

1. **Breaking role stereotyping:** Encouraging agents to think beyond "what does my job title suggest?"
2. **Expanding effective action space:** Making agents aware they CAN choose contextually appropriate actions outside their domain
3. **Creative problem-solving:** Prompting agents to consider alternatives when repeated actions fail

**However, cross-expertise alone may not solve:**
- **Cognitive overload from 49-action menu:** Even with cross-expertise, presenting 40 actions may still cause paralysis
- **Supplementary actor constraints:** Cross-expertise won't make allied actors choose full_scale_attack (inappropriate regardless of expertise)

**Recommendation:** Test v3.6 cross-expertise first, then consider:
- Two-stage strategic direction filtering (reduce 49 → 8-12 options per round)
- Faction-specific action filtering (pre-filter inappropriate actions by faction type)
- Action variety prompts ("You've used proxy_support 3 times; what alternatives achieve similar goals?")

---

## Conclusion

**Primary cause of low action diversity:** Cognitive overload + role stereotyping

**Secondary cause:** Some actions inappropriate for supplementary actors (but this affects <30% of action space)

**The 49-action space is NOT fundamentally mismatched** with the 2+4 faction structure - appropriate actions exist for all faction types but are underutilized. The pattern of 10-25% utilization across all faction types points to cognitive constraints rather than structural incompatibility.

**Next step:** Run v3.6 with cross-expertise to test whether breaking role stereotyping improves diversity. If diversity improves for direct combatants but not supplementary actors, then consider faction-specific filtering.
